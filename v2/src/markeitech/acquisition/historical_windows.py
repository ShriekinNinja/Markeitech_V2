from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta

from markeitech.acquisition.demand import HistoricalWindow
from markeitech.acquisition.historical import HistoricalWindowBounds
from markeitech.intelligence.session import SessionCalendar, SessionWindow

_MINUTE_NS = 60 * 1_000_000_000


@dataclass(frozen=True, slots=True)
class HistoricalWindowParameters:
    phase: str | None = None
    duration_minutes: int | None = None
    start_offset_minutes: int | None = None
    end_offset_minutes: int | None = None
    session_count: int | None = None
    start_ns: int | None = None
    end_ns: int | None = None
    observation_count: int | None = None

    def __post_init__(self) -> None:
        if self.phase is not None and not self.phase.strip():
            raise ValueError("phase must be non-empty when supplied")
        if self.phase is not None:
            object.__setattr__(self, "phase", self.phase.strip())
        if self.duration_minutes is not None and (
            type(self.duration_minutes) is not int or self.duration_minutes <= 0
        ):
            raise ValueError("duration_minutes must be positive when supplied")
        if self.start_offset_minutes is not None and (
            type(self.start_offset_minutes) is not int or self.start_offset_minutes < 0
        ):
            raise ValueError("start_offset_minutes must be non-negative when supplied")
        if self.end_offset_minutes is not None and (
            type(self.end_offset_minutes) is not int or self.end_offset_minutes <= 0
        ):
            raise ValueError("end_offset_minutes must be positive when supplied")
        if self.session_count is not None and (
            type(self.session_count) is not int or self.session_count <= 0
        ):
            raise ValueError("session_count must be positive when supplied")
        for name in ("start_ns", "end_ns"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{name} must be non-negative when supplied")
        if self.observation_count is not None and (
            type(self.observation_count) is not int or self.observation_count <= 0
        ):
            raise ValueError("observation_count must be positive when supplied")


class HistoricalWindowResolutionError(ValueError):
    pass


class HistoricalWindowResolver:
    """Resolve configured historical windows against authoritative session calendars."""

    def resolve(
        self,
        window: HistoricalWindow,
        *,
        calendar: SessionCalendar | None,
        selector_interval_ns: int,
        as_of_ns: int,
        parameters: Mapping[HistoricalWindow, HistoricalWindowParameters],
    ) -> HistoricalWindowBounds:
        if selector_interval_ns <= 0:
            raise HistoricalWindowResolutionError("selector interval must be positive")
        if as_of_ns < 0:
            raise HistoricalWindowResolutionError("as_of_ns must be non-negative")
        policy = parameters.get(window)
        if policy is None:
            raise HistoricalWindowResolutionError(
                f"parameters are required for window={window.value}",
            )
        _validate_policy(window, policy)
        completed_boundary_ns = as_of_ns - (as_of_ns % selector_interval_ns)
        if completed_boundary_ns <= 0:
            raise HistoricalWindowResolutionError("no completed selector interval is available")

        if window is HistoricalWindow.RECENT_COMPLETED:
            duration_ns = (
                policy.observation_count * selector_interval_ns
                if policy.observation_count is not None
                else _required_duration(policy, window)
            )
            return _bounds(
                window,
                completed_boundary_ns - duration_ns,
                completed_boundary_ns,
                completed_boundary_ns,
            )

        if calendar is None:
            raise HistoricalWindowResolutionError("session calendar is required")

        if window in {
            HistoricalWindow.ANCHORED_INTERVAL,
            HistoricalWindow.SYNCHRONIZED_INTERVAL,
        }:
            if policy.start_ns is None:
                raise HistoricalWindowResolutionError(
                    f"start_ns is required for window={window.value}",
                )
            if policy.end_ns is None:
                raise HistoricalWindowResolutionError(
                    f"end_ns is required for window={window.value}",
                )
            end_exclusive_ns = policy.end_ns
            return _bounds(window, policy.start_ns, end_exclusive_ns, completed_boundary_ns)

        phase = _required_phase(policy, window)
        session_windows = _calendar_windows(calendar, as_of_ns)
        phase_windows = tuple(item for item in session_windows if item.phase == phase)
        if not phase_windows:
            raise HistoricalWindowResolutionError(
                f"calendar has no phase={phase!r} near as_of_ns",
            )

        if window in {
            HistoricalWindow.PREVIOUS_RTH,
            HistoricalWindow.PREVIOUS_GTH_OVERNIGHT,
        }:
            selected = _latest_completed(phase_windows, completed_boundary_ns, window)
            start_ns, end_exclusive_ns = selected.start_ns, selected.end_ns
        elif window is HistoricalWindow.PREVIOUS_SESSIONS:
            if policy.session_count is None:
                raise HistoricalWindowResolutionError("previous_sessions requires session_count")
            completed = tuple(
                item for item in phase_windows if item.end_ns <= completed_boundary_ns
            )
            if len(completed) < policy.session_count:
                raise HistoricalWindowResolutionError(
                    "not enough completed phases for previous_sessions",
                )
            selected = sorted(completed, key=lambda item: item.end_ns)[-policy.session_count :]
            start_ns, end_exclusive_ns = selected[0].start_ns, selected[-1].end_ns
        else:
            selected = _current_for_trade_date(
                calendar,
                phase_windows,
                as_of_ns,
                completed_boundary_ns,
                window,
            )
            start_ns, end_exclusive_ns = _window_shape(window, selected, policy)

        return _bounds(
            window,
            start_ns,
            end_exclusive_ns,
            completed_boundary_ns,
        )


def _calendar_windows(calendar: SessionCalendar, as_of_ns: int) -> tuple[SessionWindow, ...]:
    snapshot = calendar.evaluate(as_of_ns)
    if snapshot.trade_date is None:
        raise HistoricalWindowResolutionError("calendar has no trade date near as_of_ns")
    # A month safely crosses weekends, exchange holidays, and adjacent DST transitions.
    return calendar.windows(
        snapshot.trade_date - timedelta(days=31),
        snapshot.trade_date + timedelta(days=1),
    )


def _latest_completed(
    windows: tuple[SessionWindow, ...],
    completed_boundary_ns: int,
    window: HistoricalWindow,
) -> SessionWindow:
    eligible = tuple(item for item in windows if item.end_ns <= completed_boundary_ns)
    if not eligible:
        raise HistoricalWindowResolutionError(
            f"no completed phase is available for window={window.value}",
        )
    return max(eligible, key=lambda item: (item.end_ns, item.start_ns))


def _current_for_trade_date(
    calendar: SessionCalendar,
    windows: tuple[SessionWindow, ...],
    as_of_ns: int,
    completed_boundary_ns: int,
    window: HistoricalWindow,
) -> SessionWindow:
    trade_date = calendar.evaluate(as_of_ns).trade_date
    eligible = tuple(
        item
        for item in windows
        if item.trade_date == trade_date and item.start_ns < completed_boundary_ns
    )
    if not eligible:
        raise HistoricalWindowResolutionError(
            f"configured phase has not started for window={window.value}",
        )
    return max(eligible, key=lambda item: (item.start_ns, item.end_ns))


def _window_shape(
    window: HistoricalWindow,
    session: SessionWindow,
    policy: HistoricalWindowParameters,
) -> tuple[int, int]:
    if window in {
        HistoricalWindow.CURRENT_OVERNIGHT,
        HistoricalWindow.CURRENT_RTH,
        HistoricalWindow.CURRENT_GTH,
        HistoricalWindow.CURB,
        HistoricalWindow.PREMARKET,
        HistoricalWindow.OVERNIGHT,
        HistoricalWindow.SESSION_TO_DATE,
    }:
        return session.start_ns, session.end_ns
    if window is HistoricalWindow.OPENING_RANGE:
        duration_ns = _required_duration(policy, window)
        return session.start_ns, min(session.start_ns + duration_ns, session.end_ns)
    if window is HistoricalWindow.POWER_HOUR:
        duration_ns = _required_duration(policy, window)
        return max(session.start_ns, session.end_ns - duration_ns), session.end_ns
    if window is HistoricalWindow.NAMED_PHASE_SLICE:
        if policy.start_offset_minutes is None or policy.end_offset_minutes is None:
            raise HistoricalWindowResolutionError(
                "named_phase_slice requires start_offset_minutes and end_offset_minutes",
            )
        return (
            session.start_ns + policy.start_offset_minutes * _MINUTE_NS,
            session.start_ns + policy.end_offset_minutes * _MINUTE_NS,
        )
    raise HistoricalWindowResolutionError(f"unsupported window={window.value}")


def _required_phase(
    policy: HistoricalWindowParameters,
    window: HistoricalWindow,
) -> str:
    if policy.phase is None:
        raise HistoricalWindowResolutionError(f"phase is required for window={window.value}")
    return policy.phase


def _required_duration(
    policy: HistoricalWindowParameters,
    window: HistoricalWindow,
) -> int:
    if policy.duration_minutes is None:
        raise HistoricalWindowResolutionError(
            f"duration_minutes is required for window={window.value}",
        )
    return policy.duration_minutes * _MINUTE_NS


def _validate_policy(
    window: HistoricalWindow,
    policy: HistoricalWindowParameters,
) -> None:
    supplied = {
        name
        for name in (
            "phase",
            "duration_minutes",
            "start_offset_minutes",
            "end_offset_minutes",
            "session_count",
            "start_ns",
            "end_ns",
            "observation_count",
        )
        if getattr(policy, name) is not None
    }
    expected = {
        HistoricalWindow.RECENT_COMPLETED: (
            {"observation_count"}
            if policy.observation_count is not None
            else {"duration_minutes"}
        ),
        HistoricalWindow.PREVIOUS_RTH: {"phase"},
        HistoricalWindow.PREVIOUS_GTH_OVERNIGHT: {"phase"},
        HistoricalWindow.CURRENT_OVERNIGHT: {"phase"},
        HistoricalWindow.CURRENT_RTH: {"phase"},
        HistoricalWindow.CURRENT_GTH: {"phase"},
        HistoricalWindow.CURB: {"phase"},
        HistoricalWindow.PREMARKET: {"phase"},
        HistoricalWindow.OVERNIGHT: {"phase"},
        HistoricalWindow.SESSION_TO_DATE: {"phase"},
        HistoricalWindow.OPENING_RANGE: {"phase", "duration_minutes"},
        HistoricalWindow.POWER_HOUR: {"phase", "duration_minutes"},
        HistoricalWindow.NAMED_PHASE_SLICE: {
            "phase",
            "start_offset_minutes",
            "end_offset_minutes",
        },
        HistoricalWindow.PREVIOUS_SESSIONS: {"phase", "session_count"},
        HistoricalWindow.ANCHORED_INTERVAL: {"start_ns", "end_ns"},
        HistoricalWindow.SYNCHRONIZED_INTERVAL: {"start_ns", "end_ns"},
    }.get(window)
    if expected is None:
        raise HistoricalWindowResolutionError(f"unsupported window={window.value}")
    if supplied != expected:
        raise HistoricalWindowResolutionError(
            f"window={window.value} requires exactly parameters={sorted(expected)}; "
            f"received={sorted(supplied)}",
        )


def _bounds(
    window: HistoricalWindow,
    start_ns: int,
    end_exclusive_ns: int,
    completed_boundary_ns: int,
) -> HistoricalWindowBounds:
    clipped_end_ns = min(end_exclusive_ns, completed_boundary_ns)
    if start_ns < 0 or clipped_end_ns <= start_ns:
        raise HistoricalWindowResolutionError(
            f"window is closed, not yet started, or has invalid bounds: window={window.value}",
        )
    return HistoricalWindowBounds(
        window=window,
        start_ns=start_ns,
        end_ns=clipped_end_ns - 1,
    )
