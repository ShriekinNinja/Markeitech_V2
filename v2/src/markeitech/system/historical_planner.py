from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Protocol

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId, BarType, CustomData, DataType

from markeitech.acquisition import (
    HISTORICAL_DEPENDENCY_DEMAND_SIGNAL,
    HISTORICAL_REQUEST_PLAN_TYPE_NAME,
    CapabilityDeclaration,
    CapabilityHistoricalRequirement,
    FeedKind,
    HistoricalCapabilityBinding,
    HistoricalDependencyCompiler,
    HistoricalDependencyDemandEvent,
    HistoricalRequest,
    HistoricalRequestPlan,
    HistoricalResourcePolicy,
    HistoricalWindow,
)
from markeitech.acquisition.historical_windows import (
    HistoricalWindowParameters,
    HistoricalWindowResolver,
    HistoricalWindowUnavailable,
)
from markeitech.intelligence.calendar_messages import (
    CALENDAR_PROJECTION_REQUEST_TYPE_NAME,
    CALENDAR_PROJECTION_RESPONSE_TYPE_NAME,
    CALENDAR_TRANSITION_TYPE_NAME,
    CalendarProjectionRequest,
    CalendarProjectionResponse,
    CalendarTransition,
)
from markeitech.intelligence.session import CalendarProjectionView

_HISTORICAL_DEMAND_RETRY_ALERT = "historical-planner-window-retry"
_CALENDAR_PROJECTION_RETRY_TIMER = "historical-planner-calendar-projection-retry"


@dataclass(frozen=True, slots=True)
class DeferredHistoricalDemand:
    event: HistoricalDependencyDemandEvent
    calendar_id: str
    retry_at_ns: int


class HistoricalDemandRetryBook:
    def __init__(self) -> None:
        self._demands: dict[str, DeferredHistoricalDemand] = {}

    @property
    def next_retry_ns(self) -> int | None:
        if not self._demands:
            return None
        return min(item.retry_at_ns for item in self._demands.values())

    @property
    def demand_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._demands))

    def retain(
        self,
        event: HistoricalDependencyDemandEvent,
        *,
        calendar_id: str,
        retry_at_ns: int,
    ) -> None:
        self._demands[event.demand_id] = DeferredHistoricalDemand(
            event=event,
            calendar_id=calendar_id,
            retry_at_ns=retry_at_ns,
        )

    def discard(self, demand_id: str) -> None:
        self._demands.pop(demand_id, None)

    def release_due(self, now_ns: int) -> tuple[HistoricalDependencyDemandEvent, ...]:
        return self._release(
            demand_id for demand_id, item in self._demands.items() if item.retry_at_ns <= now_ns
        )

    def release_calendar(self, calendar_id: str) -> tuple[HistoricalDependencyDemandEvent, ...]:
        return self._release(
            demand_id
            for demand_id, item in self._demands.items()
            if item.calendar_id == calendar_id
        )

    def clear(self) -> None:
        self._demands.clear()

    def _release(self, demand_ids) -> tuple[HistoricalDependencyDemandEvent, ...]:  # noqa: ANN001
        released = []
        for demand_id in sorted(tuple(demand_ids)):
            item = self._demands.pop(demand_id, None)
            if item is not None:
                released.append(item.event)
        return tuple(released)


class HistoricalDemandRetryClock(Protocol):
    def timer_names(self) -> list[str]: ...

    def cancel_timer(self, name: str) -> None: ...

    def set_time_alert_ns(
        self,
        name: str,
        alert_time_ns: int,
        callback: Callable[[object], None],
    ) -> None: ...


def synchronize_historical_demand_retry_timer(
    clock: HistoricalDemandRetryClock,
    *,
    current_retry_at_ns: int | None,
    next_retry_at_ns: int | None,
    callback: Callable[[object], None],
) -> int | None:
    timer_exists = _HISTORICAL_DEMAND_RETRY_ALERT in clock.timer_names()
    if next_retry_at_ns is None:
        if timer_exists:
            clock.cancel_timer(_HISTORICAL_DEMAND_RETRY_ALERT)
        return None
    if timer_exists and current_retry_at_ns == next_retry_at_ns:
        return next_retry_at_ns
    if timer_exists:
        clock.cancel_timer(_HISTORICAL_DEMAND_RETRY_ALERT)
    clock.set_time_alert_ns(_HISTORICAL_DEMAND_RETRY_ALERT, next_retry_at_ns, callback)
    return next_retry_at_ns


class HistoricalEvidencePlannerActorConfig(DataActorConfig):
    def __new__(
        cls,
        instrument_ids: list[str],
        instrument_calendars: dict[str, str],
        expected_calendar_digests: dict[str, str],
        historical: dict[str, int],
        projection_lookback_days: int,
        projection_lookahead_days: int,
        actor_id: str | ActorId = "HISTORICAL-EVIDENCE-PLANNER",
    ) -> HistoricalEvidencePlannerActorConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        obj = super().__new__(cls, actor_id=resolved)
        obj.instrument_ids = tuple(instrument_ids)
        obj.instrument_calendars = dict(instrument_calendars)
        obj.expected_calendar_digests = dict(expected_calendar_digests)
        obj.historical = dict(historical)
        obj.projection_lookback_days = projection_lookback_days
        obj.projection_lookahead_days = projection_lookahead_days
        return obj


class HistoricalEvidencePlannerActor(DataActor):
    """Resolves semantic evidence demand; it never calls a provider or owns pacing."""

    def __init__(self, config: HistoricalEvidencePlannerActorConfig) -> None:
        super().__init__(config)
        self._instrument_ids = frozenset(config.instrument_ids)
        self._instrument_calendars = dict(config.instrument_calendars)
        self._expected_calendar_digests = dict(config.expected_calendar_digests)
        self._calendar_ids = tuple(sorted(set(self._instrument_calendars.values())))
        self._calendars: dict[str, CalendarProjectionView] = {}
        historical = config.historical
        self._compiler = HistoricalDependencyCompiler(
            HistoricalResourcePolicy(
                maximum_requests=historical["maximum_plan_requests"],
                maximum_observations_per_request=historical[
                    "maximum_observations_per_request"
                ],
                maximum_total_observations=historical["maximum_total_observations"],
            ),
        )
        self._resolver = HistoricalWindowResolver()
        self._projection_lookback_ns = config.projection_lookback_days * 86_400_000_000_000
        self._projection_lookahead_ns = config.projection_lookahead_days * 86_400_000_000_000
        self._projection_retry_interval_ns = historical["poll_interval_ms"] * 1_000_000
        self._projection_request_type = DataType(CALENDAR_PROJECTION_REQUEST_TYPE_NAME)
        self._projection_response_type = DataType(CALENDAR_PROJECTION_RESPONSE_TYPE_NAME)
        self._transition_type = DataType(CALENDAR_TRANSITION_TYPE_NAME)
        self._plan_type = DataType(HISTORICAL_REQUEST_PLAN_TYPE_NAME)
        self._pending: dict[str, HistoricalDependencyDemandEvent] = {}
        self._deferred = HistoricalDemandRetryBook()
        self._calendar_refresh_ids: set[str] = set()
        self._retry_at_ns: int | None = None
        self._counts: dict[str, int] = {"planned": 0, "rejected": 0, "deferred": 0}

    def on_start(self) -> None:
        self.subscribe_signal(HISTORICAL_DEPENDENCY_DEMAND_SIGNAL)
        self.subscribe_data(self._projection_response_type)
        self.subscribe_data(self._transition_type)
        self._request_projections(None)
        self.clock.set_timer_ns(
            _CALENDAR_PROJECTION_RETRY_TIMER,
            self._projection_retry_interval_ns,
            callback=self._request_projections,
        )

    def on_signal(self, signal: Signal) -> None:
        if signal.name != HISTORICAL_DEPENDENCY_DEMAND_SIGNAL:
            return
        try:
            event = HistoricalDependencyDemandEvent.from_signal_value(signal.value)
            if event.instrument_id not in self._instrument_ids:
                raise ValueError("historical demand instrument is outside planner scope")
        except ValueError as exc:
            self._counts["rejected"] += 1
            self.log.error(
                f"HISTORICAL_PLAN_DEMAND_REJECTED | error={type(exc).__name__}",
            )
            return
        self._deferred.discard(event.demand_id)
        self._pending[event.demand_id] = event
        self._plan_pending()

    def on_data(self, data) -> None:  # noqa: ANN001
        payload = data.data if isinstance(data, CustomData) else data
        if isinstance(payload, CalendarProjectionResponse):
            self._retain_projections(payload)
        elif isinstance(payload, CalendarTransition):
            expected = self._expected_calendar_digests.get(payload.calendar_id)
            if expected is None:
                return
            if payload.definition_digest != expected:
                self._counts["rejected"] += 1
                self.log.error(
                    "HISTORICAL_PLAN_CALENDAR_DEFINITION_CONFLICT"
                    f" | calendar_id={payload.calendar_id}",
                )
                return
            self._calendar_refresh_ids.add(payload.calendar_id)
            self._ensure_projection_retry_timer()
            self._request_projections(None)
            for event in self._deferred.release_calendar(payload.calendar_id):
                self._pending[event.demand_id] = replace(
                    event,
                    as_of_ns=self.clock.timestamp_ns(),
                )
            self._plan_pending()

    def on_stop(self) -> None:
        self.unsubscribe_signal(HISTORICAL_DEPENDENCY_DEMAND_SIGNAL)
        self.unsubscribe_data(self._projection_response_type)
        self.unsubscribe_data(self._transition_type)
        for timer_name in (_CALENDAR_PROJECTION_RETRY_TIMER, _HISTORICAL_DEMAND_RETRY_ALERT):
            if timer_name in self.clock.timer_names():
                self.clock.cancel_timer(timer_name)
        self._deferred.clear()
        self.log.info(
            "HISTORICAL_EVIDENCE_PLANNER_STOPPED"
            f" | planned={self._counts['planned']}"
            f" | deferred={self._counts['deferred']}"
            f" | rejected={self._counts['rejected']}",
        )

    def _request_projections(self, _event) -> None:  # noqa: ANN001
        requested = tuple(
            calendar_id
            for calendar_id in self._calendar_ids
            if calendar_id not in self._calendars or calendar_id in self._calendar_refresh_ids
        )
        if not requested:
            if _CALENDAR_PROJECTION_RETRY_TIMER in self.clock.timer_names():
                self.clock.cancel_timer(_CALENDAR_PROJECTION_RETRY_TIMER)
            return
        now_ns = self.clock.timestamp_ns()
        request = CalendarProjectionRequest(
            request_id=f"calendar-projection:{self.actor_id}:{now_ns}",
            requester=str(self.actor_id),
            calendar_ids=requested,
            start_ns=max(0, now_ns - self._projection_lookback_ns),
            end_ns=now_ns + self._projection_lookahead_ns,
            requested_ts_ns=now_ns,
        )
        self.publish_data(
            self._projection_request_type,
            CustomData(self._projection_request_type, request),
        )

    def _retain_projections(self, response: CalendarProjectionResponse) -> None:
        accepted_status = response.status in {"READY", "INCOMPLETE"}
        if response.requester != str(self.actor_id) or not accepted_status:
            return
        for projection in response.projections:
            expected = self._expected_calendar_digests.get(projection.calendar_id)
            if expected is None or projection.definition_digest != expected:
                self._counts["rejected"] += 1
                continue
            self._calendars[projection.calendar_id] = CalendarProjectionView(projection)
            self._calendar_refresh_ids.discard(projection.calendar_id)
        self._plan_pending()

    def _ensure_projection_retry_timer(self) -> None:
        if _CALENDAR_PROJECTION_RETRY_TIMER not in self.clock.timer_names():
            self.clock.set_timer_ns(
                _CALENDAR_PROJECTION_RETRY_TIMER,
                self._projection_retry_interval_ns,
                callback=self._request_projections,
            )

    def _plan_pending(self) -> None:
        for demand_id in sorted(tuple(self._pending)):
            event = self._pending[demand_id]
            calendar_id = self._instrument_calendars[event.instrument_id]
            window = HistoricalWindow(event.window)
            calendar = self._calendars.get(calendar_id)
            if calendar is None and window is not HistoricalWindow.RECENT_COMPLETED:
                continue
            try:
                request = compile_historical_demand(
                    event,
                    self._compiler,
                    resolver=self._resolver,
                    calendar=calendar,
                )
            except HistoricalWindowUnavailable as exc:
                self._pending.pop(demand_id, None)
                self._deferred.retain(event, calendar_id=calendar_id, retry_at_ns=exc.retry_at_ns)
                self._counts["deferred"] += 1
                continue
            except ValueError as exc:
                self._pending.pop(demand_id, None)
                self._counts["rejected"] += 1
                self.log.error(
                    "HISTORICAL_PLAN_REJECTED"
                    f" | demand_id={demand_id} | error={type(exc).__name__}: {exc}",
                )
                continue
            self._pending.pop(demand_id, None)
            plan = HistoricalRequestPlan(
                demand_id=event.demand_id,
                calendar_id=calendar_id,
                calendar_definition_digest=self._expected_calendar_digests[calendar_id],
                request=request,
                planned_at_ns=self.clock.timestamp_ns(),
            )
            self.publish_data(self._plan_type, CustomData(self._plan_type, plan))
            self._counts["planned"] += 1
        self._schedule_retry()

    def _schedule_retry(self) -> None:
        self._retry_at_ns = synchronize_historical_demand_retry_timer(
            self.clock,
            current_retry_at_ns=self._retry_at_ns,
            next_retry_at_ns=self._deferred.next_retry_ns,
            callback=self._retry_deferred,
        )

    def _retry_deferred(self, _event) -> None:  # noqa: ANN001
        now_ns = self.clock.timestamp_ns()
        self._retry_at_ns = None
        for event in self._deferred.release_due(now_ns):
            self._pending[event.demand_id] = replace(event, as_of_ns=now_ns)
        self._plan_pending()


def compile_historical_demand(
    event: HistoricalDependencyDemandEvent,
    compiler: HistoricalDependencyCompiler,
    *,
    resolver: HistoricalWindowResolver | None = None,
    calendar: CalendarProjectionView | None = None,
) -> HistoricalRequest:
    window = HistoricalWindow(event.window)
    interval_ns = BarType.from_str(
        f"{event.instrument_id}-{event.selector}",
    ).spec.get_interval_ns()
    resolved_parameters = dict(event.window_parameters or {})
    if window is HistoricalWindow.RECENT_COMPLETED and not resolved_parameters:
        resolved_parameters = {"observation_count": event.maximum_observations}
    try:
        policy = HistoricalWindowParameters(**resolved_parameters)
    except TypeError as exc:
        raise ValueError("invalid historical window parameters") from exc
    bounds = (resolver or HistoricalWindowResolver()).resolve(
        window,
        calendar=calendar,
        selector_interval_ns=interval_ns,
        as_of_ns=event.as_of_ns,
        parameters={window: policy},
    )
    capability = CapabilityDeclaration(
        capability_id=event.capability_id,
        version=event.capability_version,
        historical_requirements=(
            CapabilityHistoricalRequirement(
                kind=FeedKind.BARS,
                selector=event.selector,
                window=window,
                minimum_observations=event.minimum_observations,
                maximum_observations=event.maximum_observations,
                window_parameters=event.window_parameters,
                parameters=event.parameters,
            ),
        ),
    )
    requests = compiler.compile(
        (
            HistoricalCapabilityBinding(
                consumer_id=event.consumer_id,
                instrument_id=event.instrument_id,
                capability=capability,
                purpose=event.purpose,
                priority=event.priority,
            ),
        ),
        {(event.instrument_id, window): bounds},
    )
    return requests[0]
