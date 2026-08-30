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
from markeitech.intelligence.calendar_delivery import (
    ProjectionRequestPhase,
    ProjectionRequestState,
    ProjectionRetryPolicy,
    begin_projection_retry,
    classify_projection_response,
    ready_projection_state,
    retain_pending_calendars,
    schedule_projection_retry,
    start_projection_cycle,
    stop_projection_state,
    terminal_projection_state,
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
_CALENDAR_PROJECTION_RETRY_ALERT = "historical-planner-calendar-projection-retry"


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
        calendar_source: str,
        calendar_source_epoch: str,
        projection_retry: dict[str, int],
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
        obj.calendar_source = calendar_source
        obj.calendar_source_epoch = calendar_source_epoch
        obj.projection_retry = dict(projection_retry)
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
        self._projection_policy = ProjectionRetryPolicy.from_config(config.projection_retry)
        self._projection_state = ProjectionRequestState.idle(
            requester=str(self.actor_id),
            expected_source=config.calendar_source,
            expected_source_epoch=config.calendar_source_epoch,
        )
        self._projection_request_type = DataType(CALENDAR_PROJECTION_REQUEST_TYPE_NAME)
        self._projection_response_type = DataType(CALENDAR_PROJECTION_RESPONSE_TYPE_NAME)
        self._transition_type = DataType(CALENDAR_TRANSITION_TYPE_NAME)
        self._plan_type = DataType(HISTORICAL_REQUEST_PLAN_TYPE_NAME)
        self._pending: dict[str, HistoricalDependencyDemandEvent] = {}
        self._deferred = HistoricalDemandRetryBook()
        self._calendar_refresh_ids: set[str] = set()
        self._retry_at_ns: int | None = None
        self._counts: dict[str, int] = {
            "planned": 0,
            "rejected": 0,
            "deferred": 0,
            "projection_requests": 0,
            "projection_timeouts": 0,
            "projection_retries": 0,
            "projection_stale": 0,
            "projection_conflicts": 0,
            "projection_terminal": 0,
        }

    def on_start(self) -> None:
        self.subscribe_signal(HISTORICAL_DEPENDENCY_DEMAND_SIGNAL)
        self.subscribe_data(self._projection_response_type)
        self.subscribe_data(self._transition_type)
        self._begin_projection_cycle()

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
            if (
                payload.definition_digest != expected
                or payload.source != self._projection_state.expected_source
                or payload.source_epoch != self._projection_state.expected_source_epoch
            ):
                self._counts["rejected"] += 1
                self.log.error(
                    "HISTORICAL_PLAN_CALENDAR_DEFINITION_CONFLICT"
                    f" | calendar_id={payload.calendar_id}",
                )
                return
            self._calendar_refresh_ids.add(payload.calendar_id)
            self._begin_projection_cycle()
            for event in self._deferred.release_calendar(payload.calendar_id):
                self._pending[event.demand_id] = replace(
                    event,
                    as_of_ns=self.clock.timestamp_ns(),
                )
            self._plan_pending()

    def on_stop(self) -> None:
        self._projection_state = stop_projection_state(self._projection_state)
        self.unsubscribe_signal(HISTORICAL_DEPENDENCY_DEMAND_SIGNAL)
        self.unsubscribe_data(self._projection_response_type)
        self.unsubscribe_data(self._transition_type)
        for timer_name in (_CALENDAR_PROJECTION_RETRY_ALERT, _HISTORICAL_DEMAND_RETRY_ALERT):
            if timer_name in self.clock.timer_names():
                self.clock.cancel_timer(timer_name)
        self._deferred.clear()
        self.log.info(
            "HISTORICAL_EVIDENCE_PLANNER_STOPPED"
            f" | planned={self._counts['planned']}"
            f" | deferred={self._counts['deferred']}"
            f" | rejected={self._counts['rejected']}"
            f" | projection_state={self._projection_state.phase.value}"
            f" | projection_requests={self._counts['projection_requests']}"
            f" | projection_timeouts={self._counts['projection_timeouts']}"
            f" | projection_terminal={self._counts['projection_terminal']}",
        )

    def _begin_projection_cycle(self) -> None:
        requested = tuple(
            calendar_id
            for calendar_id in self._calendar_ids
            if calendar_id not in self._calendars or calendar_id in self._calendar_refresh_ids
        )
        if not requested:
            return
        now_ns = self.clock.timestamp_ns()
        self._projection_state = start_projection_cycle(
            self._projection_state,
            calendar_ids=requested,
            start_ns=max(0, now_ns - self._projection_lookback_ns),
            end_ns=now_ns + self._projection_lookahead_ns,
            now_ns=now_ns,
            policy=self._projection_policy,
        )
        if self._projection_state.phase is ProjectionRequestPhase.WAITING:
            self._publish_projection_request()

    def _publish_projection_request(self) -> None:
        state = self._projection_state
        if (
            state.phase is not ProjectionRequestPhase.WAITING
            or state.request_id is None
            or state.start_ns is None
            or state.end_ns is None
        ):
            return
        self._set_projection_alert()
        request = CalendarProjectionRequest(
            request_id=state.request_id,
            requester=state.requester,
            calendar_ids=state.pending_calendar_ids,
            start_ns=state.start_ns,
            end_ns=state.end_ns,
            requested_ts_ns=self.clock.timestamp_ns(),
        )
        self._counts["projection_requests"] += 1
        self.publish_data(
            self._projection_request_type,
            CustomData(self._projection_request_type, request),
        )

    def _retain_projections(self, response: CalendarProjectionResponse) -> None:
        disposition = classify_projection_response(self._projection_state, response)
        if disposition != "ACCEPT":
            key = (
                "projection_conflicts" if disposition == "CONFLICT" else "projection_stale"
            )
            self._counts[key] += 1
            return
        self._cancel_projection_alert()
        state = self._projection_state
        accepted_ids: set[str] = set()
        for projection in response.projections:
            expected = self._expected_calendar_digests.get(projection.calendar_id)
            if (
                expected is None
                or projection.definition_digest != expected
                or state.start_ns is None
                or state.end_ns is None
                or projection.coverage_start_ns > state.start_ns
                or projection.coverage_end_ns < state.end_ns
            ):
                self._counts["rejected"] += 1
                self._counts["projection_conflicts"] += 1
                self._projection_state = terminal_projection_state(
                    state,
                    "projection_identity_conflict",
                )
                self._counts["projection_terminal"] += 1
                self.log.error(
                    "HISTORICAL_PLAN_CALENDAR_PROJECTION_CONFLICT"
                    f" | calendar_id={projection.calendar_id}",
                )
                return
            self._calendars[projection.calendar_id] = CalendarProjectionView(projection)
            self._calendar_refresh_ids.discard(projection.calendar_id)
            accepted_ids.add(projection.calendar_id)
        self._plan_pending()
        remaining = tuple(
            item for item in state.pending_calendar_ids if item not in accepted_ids
        )
        if not remaining:
            self._projection_state = ready_projection_state(state)
            self._begin_projection_cycle()
            return
        failures = {item.calendar_id: item for item in response.failures}
        retryable = bool(remaining) and all(
            calendar_id in failures and failures[calendar_id].retryable
            for calendar_id in remaining
        )
        if response.status == "NOT_READY" or retryable:
            self._projection_state = retain_pending_calendars(state, remaining)
            self._projection_state = schedule_projection_retry(
                self._projection_state,
                now_ns=self.clock.timestamp_ns(),
                policy=self._projection_policy,
                retry_at_ns=response.retry_at_ns,
            )
            self._finish_projection_transition()
            return
        self._projection_state = terminal_projection_state(
            state,
            "projection_rejected" if response.status == "REJECTED" else "projection_unavailable",
            rejected=response.status == "REJECTED",
        )
        self._counts["projection_terminal"] += 1
        self.log.error(
            f"HISTORICAL_PLAN_CALENDAR_PROJECTION_TERMINAL | status={response.status}"
            f" | pending={','.join(remaining)}",
        )

    def _on_projection_alert(self, _event) -> None:  # noqa: ANN001
        state = self._projection_state
        if state.phase is ProjectionRequestPhase.STOPPED:
            return
        now_ns = self.clock.timestamp_ns()
        if state.alert_at_ns is None or now_ns < state.alert_at_ns:
            return
        if state.phase is ProjectionRequestPhase.WAITING:
            self._counts["projection_timeouts"] += 1
            self._projection_state = schedule_projection_retry(
                state,
                now_ns=now_ns,
                policy=self._projection_policy,
                retry_at_ns=None,
            )
            self._finish_projection_transition()
            return
        if state.phase is ProjectionRequestPhase.BACKOFF:
            self._projection_state = begin_projection_retry(
                state,
                now_ns=now_ns,
                policy=self._projection_policy,
            )
            self._publish_projection_request()

    def _finish_projection_transition(self) -> None:
        if self._projection_state.phase is ProjectionRequestPhase.BACKOFF:
            self._counts["projection_retries"] += 1
            self._set_projection_alert()
            return
        if self._projection_state.phase in {
            ProjectionRequestPhase.FAILED,
            ProjectionRequestPhase.REJECTED,
        }:
            self._counts["projection_terminal"] += 1
            self.log.error(
                "HISTORICAL_PLAN_CALENDAR_PROJECTION_EXHAUSTED"
                f" | code={self._projection_state.terminal_code}",
            )

    def _set_projection_alert(self) -> None:
        self._cancel_projection_alert()
        alert_at_ns = self._projection_state.alert_at_ns
        if alert_at_ns is not None:
            self.clock.set_time_alert_ns(
                _CALENDAR_PROJECTION_RETRY_ALERT,
                alert_at_ns,
                callback=self._on_projection_alert,
            )

    def _cancel_projection_alert(self) -> None:
        if _CALENDAR_PROJECTION_RETRY_ALERT in self.clock.timer_names():
            self.clock.cancel_timer(_CALENDAR_PROJECTION_RETRY_ALERT)

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
