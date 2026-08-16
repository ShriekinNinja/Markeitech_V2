from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas_market_calendars as market_calendars


@dataclass(frozen=True, slots=True)
class PhaseDefinition:
    name: str
    start: time
    end: time
    start_day_offset: int


@dataclass(frozen=True, slots=True)
class PhaseOverride:
    trade_date: date
    phase: str
    start: time
    end: time
    start_day_offset: int


@dataclass(frozen=True, slots=True)
class CalendarDefinition:
    calendar_id: str
    provider_calendar: str
    timezone: str
    schedule_version: str
    phases: tuple[PhaseDefinition, ...]
    overrides: tuple[PhaseOverride, ...]


@dataclass(frozen=True, slots=True)
class SessionSnapshot:
    calendar_id: str
    schedule_version: str
    timezone: str
    trade_date: date | None
    phase: str
    phase_open_ns: int | None
    phase_close_ns: int | None
    next_transition_ns: int | None

    @property
    def is_open(self) -> bool:
        return self.phase != "CLOSED"


@dataclass(frozen=True, slots=True)
class _Window:
    trade_date: date
    phase: str
    start: datetime
    end: datetime


class SessionCalendar:
    def __init__(self, definition: CalendarDefinition) -> None:
        self.definition = definition
        self._timezone = ZoneInfo(definition.timezone)
        self._provider = market_calendars.get_calendar(definition.provider_calendar)
        self._overrides = {(item.trade_date, item.phase): item for item in definition.overrides}

    def evaluate(self, timestamp_ns: int) -> SessionSnapshot:
        now = datetime.fromtimestamp(timestamp_ns / 1_000_000_000, UTC)
        local_now = now.astimezone(self._timezone)
        windows = self._windows(
            local_now.date() - timedelta(days=2),
            local_now.date() + timedelta(days=3),
        )
        active = next((item for item in windows if item.start <= local_now < item.end), None)
        future_boundaries = sorted(
            boundary
            for item in windows
            for boundary in (item.start, item.end)
            if boundary > local_now
        )
        next_transition = _to_ns(future_boundaries[0]) if future_boundaries else None
        if active is not None:
            return SessionSnapshot(
                calendar_id=self.definition.calendar_id,
                schedule_version=self.definition.schedule_version,
                timezone=self.definition.timezone,
                trade_date=active.trade_date,
                phase=active.phase,
                phase_open_ns=_to_ns(active.start),
                phase_close_ns=_to_ns(active.end),
                next_transition_ns=next_transition,
            )
        next_window = next((item for item in windows if item.start > local_now), None)
        return SessionSnapshot(
            calendar_id=self.definition.calendar_id,
            schedule_version=self.definition.schedule_version,
            timezone=self.definition.timezone,
            trade_date=next_window.trade_date if next_window is not None else None,
            phase="CLOSED",
            phase_open_ns=None,
            phase_close_ns=None,
            next_transition_ns=next_transition,
        )

    def _windows(self, start: date, end: date) -> tuple[_Window, ...]:
        schedule = self._provider.schedule(start_date=start, end_date=end)
        provider_rows = {index.date(): row for index, row in schedule.iterrows()}
        candidate_dates = set(provider_rows)
        candidate_dates.update(item.trade_date for item in self.definition.overrides)
        windows: list[_Window] = []
        configured_rth = next(
            (phase for phase in self.definition.phases if phase.name == "RTH"),
            None,
        )
        for trade_date in sorted(candidate_dates):
            row = provider_rows.get(trade_date)
            phases = self.definition.phases
            if not phases and row is not None:
                windows.append(
                    _Window(
                        trade_date=trade_date,
                        phase="OPEN",
                        start=row["market_open"].to_pydatetime().astimezone(self._timezone),
                        end=row["market_close"].to_pydatetime().astimezone(self._timezone),
                    ),
                )
                continue
            for phase in phases:
                override = self._overrides.get((trade_date, phase.name))
                if row is None and override is None:
                    continue
                selected = override or phase
                start_at = datetime.combine(
                    trade_date + timedelta(days=selected.start_day_offset),
                    selected.start,
                    self._timezone,
                )
                end_at = datetime.combine(trade_date, selected.end, self._timezone)
                if row is not None and phase.name == "RTH":
                    provider_open = row["market_open"].to_pydatetime().astimezone(self._timezone)
                    provider_close = row["market_close"].to_pydatetime().astimezone(self._timezone)
                    start_at = max(start_at, provider_open)
                    end_at = min(end_at, provider_close)
                if row is not None and phase.name == "CURB":
                    provider_close = row["market_close"].to_pydatetime().astimezone(self._timezone)
                    if configured_rth is not None and provider_close < datetime.combine(
                        trade_date,
                        configured_rth.end,
                        self._timezone,
                    ):
                        continue
                if end_at > start_at:
                    windows.append(_Window(trade_date, phase.name, start_at, end_at))
        return tuple(sorted(windows, key=lambda item: (item.start, item.end, item.phase)))


def definition_from_config(value: dict[str, object]) -> CalendarDefinition:
    return CalendarDefinition(
        calendar_id=str(value["calendar_id"]),
        provider_calendar=str(value["provider_calendar"]),
        timezone=str(value["timezone"]),
        schedule_version=str(value["schedule_version"]),
        phases=tuple(
            PhaseDefinition(
                name=str(item["name"]),
                start=time.fromisoformat(str(item["start"])),
                end=time.fromisoformat(str(item["end"])),
                start_day_offset=int(item["start_day_offset"]),
            )
            for item in value["phases"]  # type: ignore[union-attr]
        ),
        overrides=tuple(
            PhaseOverride(
                trade_date=date.fromisoformat(str(item["trade_date"])),
                phase=str(item["phase"]),
                start=time.fromisoformat(str(item["start"])),
                end=time.fromisoformat(str(item["end"])),
                start_day_offset=int(item["start_day_offset"]),
            )
            for item in value["overrides"]  # type: ignore[union-attr]
        ),
    )


def _to_ns(value: datetime) -> int:
    return int(value.astimezone(UTC).timestamp() * 1_000_000_000)
