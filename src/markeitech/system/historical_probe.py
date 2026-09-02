from __future__ import annotations

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId, CustomData, DataType

from markeitech.acquisition import (
    HISTORICAL_BATCH_TYPE_NAME,
    HISTORICAL_DEPENDENCY_DEMAND_SIGNAL,
    HISTORICAL_READINESS_SIGNAL,
    HISTORICAL_REQUEST_PLAN_TYPE_NAME,
    HistoricalBatch,
    HistoricalDependencyDemandEvent,
    HistoricalReadinessEvent,
    HistoricalRequestPlan,
)
from markeitech.intelligence.calendar_messages import (
    CALENDAR_STATE_SNAPSHOT_REQUEST_TYPE_NAME,
    CALENDAR_STATE_SNAPSHOT_RESPONSE_TYPE_NAME,
    CALENDAR_TRANSITION_V2_TYPE_NAME,
    CalendarDefinitionExpectation,
    CalendarStateSnapshotRequest,
    CalendarStateSnapshotResponse,
    CalendarTransitionV2,
)
from markeitech.intelligence.session_state_delivery import (
    SessionStateDeliveryDisposition,
    SessionStateDeliveryPhase,
    SessionStateDeliveryPolicy,
    SessionStateDeliveryState,
    begin_session_state_retry,
    current_snapshot_request,
    observe_session_snapshot,
    observe_session_transition,
    schedule_session_state_retry,
    start_session_state_cycle,
    stop_session_state_delivery,
)

_DEMAND_ALERT = "historical-dependency-probe-demand"
_DEMAND_DELAY_NS = 1_000_000
_CURRENT_STATE_RETRY_ALERT = "current-state-historical-probe-retry"


class HistoricalDependencyProbeActorConfig(DataActorConfig):
    def __new__(
        cls,
        instrument_id: str,
        selector: str,
        window: str,
        minimum_observations: int,
        maximum_observations: int,
        priority: int,
        actor_id: str | ActorId = "HISTORICAL-DEPENDENCY-PROBE",
    ) -> HistoricalDependencyProbeActorConfig:
        resolved_actor_id = (
            actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        )
        obj = super().__new__(cls, actor_id=resolved_actor_id)
        obj.instrument_id = instrument_id
        obj.selector = selector
        obj.window = window
        obj.minimum_observations = minimum_observations
        obj.maximum_observations = maximum_observations
        obj.priority = priority
        return obj


class HistoricalDependencyProbeActor(DataActor):
    """Config-disabled acceptance consumer for the Stage 9B historical path.

    Markeitech Metadata:
        architecture.component.id: actor.historical-probe
        architecture.component.label: Historical Dependency Probe
        architecture.component.kind: markeitech_actor
        architecture.component.boundary: boundary.acquisition
    """

    def __init__(self, config: HistoricalDependencyProbeActorConfig) -> None:
        super().__init__(config)
        self._instrument_id = config.instrument_id
        self._selector = config.selector
        self._window = config.window
        self._minimum_observations = config.minimum_observations
        self._maximum_observations = config.maximum_observations
        self._priority = config.priority
        self._consumer_id = str(self.actor_id)
        self._demand_id = f"probe:{self._consumer_id}:{self._instrument_id}:{self._selector}"
        self._batch_type = DataType(HISTORICAL_BATCH_TYPE_NAME)
        self._batches = 0
        self._observations = 0
        self._readiness: str | None = None

    def on_start(self) -> None:
        self.subscribe_signal(HISTORICAL_READINESS_SIGNAL)
        self.subscribe_data(self._batch_type)
        self.clock.set_time_alert_ns(
            _DEMAND_ALERT,
            self.clock.timestamp_ns() + _DEMAND_DELAY_NS,
            callback=self._publish_demand,
        )

    def on_signal(self, signal: Signal) -> None:
        if signal.name != HISTORICAL_READINESS_SIGNAL:
            return
        try:
            event = HistoricalReadinessEvent.from_signal_value(signal.value)
        except ValueError:
            return
        if event.consumer_id != self._consumer_id:
            return
        self._readiness = event.state
        self.log.info(
            f"HISTORICAL_PROBE_READINESS | state={event.state}"
            f" | request_id={event.request_id}"
            f" | observations={event.observed_count}/{event.minimum_observations}",
        )

    def on_data(self, data) -> None:  # noqa: ANN001
        payload = data.data if isinstance(data, CustomData) else data
        if not isinstance(payload, HistoricalBatch):
            return
        if not any(
            dependency.consumer_id == self._consumer_id
            for dependency in payload.request.dependencies
        ):
            return
        self._batches += 1
        self._observations += payload.observation_count
        self.log.info(
            "HISTORICAL_PROBE_BATCH"
            f" | request_id={payload.request.request_id}"
            f" | instrument_id={payload.request.instrument_id}"
            f" | selector={payload.request.selector}"
            f" | observations={payload.observation_count}",
        )

    def on_stop(self) -> None:
        if _DEMAND_ALERT in self.clock.timer_names():
            self.clock.cancel_timer(_DEMAND_ALERT)
        self.unsubscribe_signal(HISTORICAL_READINESS_SIGNAL)
        self.unsubscribe_data(self._batch_type)
        self.log.info(
            "HISTORICAL_PROBE_SUMMARY"
            f" | batches={self._batches} | observations={self._observations}"
            f" | readiness={self._readiness or 'PENDING'}",
        )

    def _publish_demand(self, _event) -> None:  # noqa: ANN001
        demand = HistoricalDependencyDemandEvent(
            demand_id=self._demand_id,
            consumer_id=self._consumer_id,
            capability_id="historical.acceptance_probe",
            capability_version=1,
            instrument_id=self._instrument_id,
            selector=self._selector,
            window=self._window,
            minimum_observations=self._minimum_observations,
            maximum_observations=self._maximum_observations,
            priority=self._priority,
            purpose="Stage 9B end-to-end historical dependency acceptance",
            as_of_ns=self.clock.timestamp_ns(),
        )
        self.publish_signal(HISTORICAL_DEPENDENCY_DEMAND_SIGNAL, demand.to_signal_value())
        self.log.info(
            f"HISTORICAL_PROBE_DEMAND | demand_id={demand.demand_id}"
            f" | instrument_id={demand.instrument_id} | selector={demand.selector}"
            f" | observations={demand.minimum_observations}-{demand.maximum_observations}",
        )


class CurrentStateHistoricalDemandProbeActorConfig(DataActorConfig):
    """Configure an opt-in current-state-gated historical acceptance probe.

    Args:
        calendar_expectations: Exact calendar definitions required in the snapshot.
        source_epoch: Expected Session State runtime-run identity.
        current_state_delivery: Bounded snapshot delivery policy in configuration units.
        instrument_id: Instrument used by the symbolic historical demand.
        selector: Historical bar selector requested through the planner.
        window: Symbolic historical window resolved by the planner.
        minimum_observations: Minimum acceptable observations.
        maximum_observations: Maximum requested observations.
        priority: Historical demand priority from zero through one hundred.
        omit_initial_snapshot_request: Whether to deliberately omit attempt one so an
            acceptance run exercises consumer retry without changing the producer.
        actor_id: Unique runtime actor identity and snapshot requester identity.
    """

    def __new__(
        cls,
        calendar_expectations: list[dict[str, object]],
        source_epoch: str,
        current_state_delivery: dict[str, int],
        instrument_id: str,
        selector: str,
        window: str,
        minimum_observations: int,
        maximum_observations: int,
        priority: int,
        omit_initial_snapshot_request: bool,
        actor_id: str | ActorId = "CURRENT-STATE-HISTORICAL-PROBE",
    ) -> CurrentStateHistoricalDemandProbeActorConfig:
        resolved_actor_id = (
            actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        )
        obj = super().__new__(cls, actor_id=resolved_actor_id)
        obj.calendar_expectations = tuple(calendar_expectations)
        obj.source_epoch = source_epoch
        obj.current_state_delivery = dict(current_state_delivery)
        obj.instrument_id = instrument_id
        obj.selector = selector
        obj.window = window
        obj.minimum_observations = minimum_observations
        obj.maximum_observations = maximum_observations
        obj.priority = priority
        obj.omit_initial_snapshot_request = omit_initial_snapshot_request
        return obj


class CurrentStateHistoricalDemandProbeActor(DataActor):
    """Exercise current-state delivery before one real historical dependency request.

    This actor is an explicitly enabled acceptance harness. It owns no calendar, provider,
    acquisition, or persistence behavior: it synchronizes through the production session-state
    protocol and publishes one normal symbolic demand only after reconciliation reaches ``LIVE``.

    Markeitech Metadata:
        architecture.component.id: actor.current-state-historical-probe
        architecture.component.label: Current-State Historical Demand Probe
        architecture.component.kind: markeitech_actor
        architecture.component.boundary: boundary.acquisition
        architecture.component.responsibilities:
            - Gate one acceptance-only historical demand on reconciled current session state.
            - Observe the correlated plan, readiness, and transient historical batches.
            - Exercise one bounded snapshot retry when explicitly configured.
    """

    def __init__(self, config: CurrentStateHistoricalDemandProbeActorConfig) -> None:
        super().__init__(config)
        delivery = config.current_state_delivery
        self._policy = SessionStateDeliveryPolicy(
            policy_version=delivery["policy_version"],
            response_timeout_ns=delivery["response_timeout_ms"] * 1_000_000,
            maximum_attempts=delivery["maximum_attempts"],
            retry_backoff_ns=delivery["retry_backoff_ms"] * 1_000_000,
            maximum_elapsed_ns=delivery["maximum_elapsed_ms"] * 1_000_000,
            maximum_buffered_transitions_per_calendar=delivery[
                "maximum_buffered_transitions_per_calendar"
            ],
            maximum_total_buffered_transitions=delivery[
                "maximum_total_buffered_transitions"
            ],
            boundary_delivery_grace_ns=delivery["boundary_delivery_grace_ms"] * 1_000_000,
        )
        self._expectations = tuple(
            CalendarDefinitionExpectation(
                calendar_id=str(item["calendar_id"]),
                definition_version=int(item["definition_version"]),
                definition_digest=str(item["definition_digest"]),
                definition_effective_from_ns=int(item["definition_effective_from_ns"]),
            )
            for item in config.calendar_expectations
        )
        self._session_state = SessionStateDeliveryState.idle(
            requester=str(self.actor_id),
            expected_source="SESSION-STATE",
            expected_source_epoch=config.source_epoch,
            delivery_policy_version=self._policy.policy_version,
        )
        self._instrument_id = config.instrument_id
        self._selector = config.selector
        self._window = config.window
        self._minimum_observations = config.minimum_observations
        self._maximum_observations = config.maximum_observations
        self._priority = config.priority
        self._omit_initial_snapshot_request = config.omit_initial_snapshot_request
        self._consumer_id = str(self.actor_id)
        self._demand_id = (
            f"current-state-probe:{self._consumer_id}:{self._instrument_id}:{self._selector}"
        )
        self._snapshot_request_type = DataType(CALENDAR_STATE_SNAPSHOT_REQUEST_TYPE_NAME)
        self._snapshot_response_type = DataType(CALENDAR_STATE_SNAPSHOT_RESPONSE_TYPE_NAME)
        self._transition_type = DataType(CALENDAR_TRANSITION_V2_TYPE_NAME)
        self._plan_type = DataType(HISTORICAL_REQUEST_PLAN_TYPE_NAME)
        self._batch_type = DataType(HISTORICAL_BATCH_TYPE_NAME)
        self._active = False
        self._demand_published = False
        self._initial_request_omitted = False
        self._last_request: CalendarStateSnapshotRequest | None = None
        self._plans = 0
        self._batches = 0
        self._observations = 0
        self._readiness: str | None = None

    def on_start(self) -> None:
        self._active = True
        self._session_state = start_session_state_cycle(
            self._session_state,
            calendar_expectations=self._expectations,
            now_ns=self.clock.timestamp_ns(),
            policy=self._policy,
        )
        self.subscribe_data(self._snapshot_response_type)
        self.subscribe_data(self._transition_type)
        self.subscribe_data(self._plan_type)
        self.subscribe_data(self._batch_type)
        self.subscribe_signal(HISTORICAL_READINESS_SIGNAL)
        self._publish_snapshot_request()

    def on_signal(self, signal: Signal) -> None:
        if not self._active or signal.name != HISTORICAL_READINESS_SIGNAL:
            return
        try:
            event = HistoricalReadinessEvent.from_signal_value(signal.value)
        except ValueError:
            return
        if event.consumer_id != self._consumer_id:
            return
        self._readiness = event.state
        self.log.info(
            f"CURRENT_STATE_HISTORICAL_PROBE_READINESS | state={event.state}"
            f" | request_id={event.request_id}"
            f" | observations={event.observed_count}/{event.minimum_observations}",
        )

    def on_data(self, data) -> None:  # noqa: ANN001
        if not self._active:
            return
        payload = data.data if isinstance(data, CustomData) else data
        if isinstance(payload, CalendarTransitionV2):
            update = observe_session_transition(
                self._session_state,
                payload,
                policy=self._policy,
            )
            self._session_state = update.state
            self._maybe_publish_demand()
            return
        if isinstance(payload, CalendarStateSnapshotResponse):
            update = observe_session_snapshot(
                self._session_state,
                payload,
                now_ns=self.clock.timestamp_ns(),
            )
            self._session_state = update.state
            if self._session_state.phase is SessionStateDeliveryPhase.DEGRADED:
                self._schedule_retry(
                    self._session_state.terminal_code or "snapshot_degraded",
                )
            self._maybe_publish_demand()
            return
        if isinstance(payload, HistoricalRequestPlan):
            if payload.demand_id != self._demand_id:
                return
            self._plans += 1
            self.log.info(
                f"CURRENT_STATE_HISTORICAL_PROBE_PLAN | demand_id={payload.demand_id}"
                f" | request_id={payload.request.request_id}"
                f" | start_ns={payload.request.start_ns} | end_ns={payload.request.end_ns}",
            )
            return
        if not isinstance(payload, HistoricalBatch):
            return
        if not any(
            dependency.consumer_id == self._consumer_id
            for dependency in payload.request.dependencies
        ):
            return
        self._batches += 1
        self._observations += payload.observation_count
        self.log.info(
            "CURRENT_STATE_HISTORICAL_PROBE_BATCH"
            f" | request_id={payload.request.request_id}"
            f" | observations={payload.observation_count}",
        )

    def on_stop(self) -> None:
        self._active = False
        self._session_state = stop_session_state_delivery(self._session_state)
        self.unsubscribe_data(self._snapshot_response_type)
        self.unsubscribe_data(self._transition_type)
        self.unsubscribe_data(self._plan_type)
        self.unsubscribe_data(self._batch_type)
        self.unsubscribe_signal(HISTORICAL_READINESS_SIGNAL)
        if _CURRENT_STATE_RETRY_ALERT in self.clock.timer_names():
            self.clock.cancel_timer(_CURRENT_STATE_RETRY_ALERT)
        self.log.info(
            "CURRENT_STATE_HISTORICAL_PROBE_SUMMARY"
            f" | snapshot_attempt={self._last_request.attempt if self._last_request else 0}"
            f" | plans={self._plans} | batches={self._batches}"
            f" | observations={self._observations}"
            f" | readiness={self._readiness or 'PENDING'}",
        )

    def _publish_snapshot_request(self) -> None:
        if (
            not self._active
            or self._session_state.phase is not SessionStateDeliveryPhase.WAITING
        ):
            return
        self._last_request = current_snapshot_request(self._session_state)
        self._set_retry_alert()
        if (
            self._omit_initial_snapshot_request
            and self._last_request.attempt == 1
            and not self._initial_request_omitted
        ):
            self._initial_request_omitted = True
            self.log.info(
                "CURRENT_STATE_HISTORICAL_PROBE_FAULT"
                " | action=omit_initial_snapshot_request | attempt=1",
            )
            return
        self.publish_data(
            self._snapshot_request_type,
            CustomData(self._snapshot_request_type, self._last_request),
        )
        self.log.info(
            "CURRENT_STATE_HISTORICAL_PROBE_SNAPSHOT_REQUEST"
            f" | request_id={self._last_request.request_id}"
            f" | attempt={self._last_request.attempt}",
        )

    def _on_retry_alert(self, _event) -> None:  # noqa: ANN001
        if not self._active:
            return
        now_ns = self.clock.timestamp_ns()
        if self._session_state.phase is SessionStateDeliveryPhase.WAITING:
            self._schedule_retry("response_timeout")
            return
        update = begin_session_state_retry(
            self._session_state,
            now_ns=now_ns,
            policy=self._policy,
        )
        self._session_state = update.state
        if update.disposition is SessionStateDeliveryDisposition.RETRY_STARTED:
            self._publish_snapshot_request()

    def _schedule_retry(self, code: str) -> None:
        update = schedule_session_state_retry(
            self._session_state,
            now_ns=self.clock.timestamp_ns(),
            policy=self._policy,
            code=code,
        )
        self._session_state = update.state
        self._set_retry_alert()

    def _set_retry_alert(self) -> None:
        if not self._active:
            return
        if _CURRENT_STATE_RETRY_ALERT in self.clock.timer_names():
            self.clock.cancel_timer(_CURRENT_STATE_RETRY_ALERT)
        if self._session_state.alert_at_ns is not None:
            self.clock.set_time_alert_ns(
                _CURRENT_STATE_RETRY_ALERT,
                self._session_state.alert_at_ns,
                callback=self._on_retry_alert,
            )

    def _maybe_publish_demand(self) -> None:
        if (
            not self._active
            or self._demand_published
            or self._session_state.phase is not SessionStateDeliveryPhase.LIVE
        ):
            return
        self._demand_published = True
        self._session_state = stop_session_state_delivery(self._session_state)
        if _CURRENT_STATE_RETRY_ALERT in self.clock.timer_names():
            self.clock.cancel_timer(_CURRENT_STATE_RETRY_ALERT)
        demand = HistoricalDependencyDemandEvent(
            demand_id=self._demand_id,
            consumer_id=self._consumer_id,
            capability_id="current_state.historical_acceptance_probe",
            capability_version=1,
            instrument_id=self._instrument_id,
            selector=self._selector,
            window=self._window,
            minimum_observations=self._minimum_observations,
            maximum_observations=self._maximum_observations,
            priority=self._priority,
            purpose="V3-02 current-state-gated historical acceptance",
            as_of_ns=self.clock.timestamp_ns(),
            window_parameters={"observation_count": self._maximum_observations},
        )
        self.publish_signal(HISTORICAL_DEPENDENCY_DEMAND_SIGNAL, demand.to_signal_value())
        self.log.info(
            f"CURRENT_STATE_HISTORICAL_PROBE_DEMAND | demand_id={demand.demand_id}"
            f" | instrument_id={demand.instrument_id} | selector={demand.selector}"
            f" | observations={demand.minimum_observations}-{demand.maximum_observations}",
        )
