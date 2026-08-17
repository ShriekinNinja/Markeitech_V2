from __future__ import annotations

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId, InstrumentId

from markeitech.system.control import (
    SystemHealthState,
    SystemHealthStateMachine,
    component_failure_target,
)
from markeitech.system.messages import (
    ACQUISITION_STATUS_REQUEST_SIGNAL,
    ACQUISITION_STATUS_SIGNAL,
    COMPONENT_FAILURE_SIGNAL,
    INSTRUMENTS_READY,
    PERSISTENCE_READY_REQUEST_SIGNAL,
    PERSISTENCE_READY_SIGNAL,
    SYSTEM_HEALTH_SIGNAL,
    AcquisitionStatusEvent,
    AcquisitionStatusRequest,
    ComponentFailureEvent,
    PersistenceReadyEvent,
    PersistenceReadyRequest,
)

_INITIAL_EVALUATION_ALERT = "system-control-initial-evaluation"
_INITIAL_EVALUATION_DELAY_NS = 1_000_000


class SystemControlActorConfig(DataActorConfig):
    def __new__(
        cls,
        instrument_ids: list[str],
        operational_persistence_ready: bool = False,
        actor_id: str | ActorId = "SYSTEM-CONTROL",
    ) -> SystemControlActorConfig:
        resolved_actor_id = (
            actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        )
        obj = super().__new__(cls, actor_id=resolved_actor_id)
        obj.instrument_ids = tuple(instrument_ids)
        obj.operational_persistence_ready = operational_persistence_ready
        return obj


class SystemControlActor(DataActor):
    def __init__(self, config: SystemControlActorConfig) -> None:
        super().__init__(config)
        self._expected = {InstrumentId.from_str(value) for value in config.instrument_ids}
        self._available: set[InstrumentId] = set()
        self._health = SystemHealthStateMachine()
        self._evaluation_started = False
        self._persistence_preflight_ready = config.operational_persistence_ready
        self._persistence_ready = False
        self._startup_released = False
        self._unresolved_component_failure = False
        self._component_failures_received = 0
        self._malformed_failure_reports = 0
        self._acquisition_statuses_received = 0
        self._malformed_acquisition_statuses = 0
        self._transitions_published = 0
        self._duplicate_transitions_suppressed = 0

    def on_start(self) -> None:
        self.subscribe_signal(COMPONENT_FAILURE_SIGNAL)
        self.subscribe_signal(ACQUISITION_STATUS_SIGNAL)
        self.subscribe_signal(PERSISTENCE_READY_SIGNAL)
        self.publish_signal(
            PERSISTENCE_READY_REQUEST_SIGNAL,
            PersistenceReadyRequest(requester=str(self.actor_id)).to_signal_value(),
        )

    def on_stop(self) -> None:
        self._publish_transition(
            SystemHealthState.STOPPING,
            reason="system control actor is stopping",
            evidence=self._instrument_evidence(),
        )
        self.unsubscribe_signal(COMPONENT_FAILURE_SIGNAL)
        self.unsubscribe_signal(ACQUISITION_STATUS_SIGNAL)
        self.unsubscribe_signal(PERSISTENCE_READY_SIGNAL)
        self.log.info(
            "SYSTEM_CONTROL_SUMMARY"
            f" | component_failures={self._component_failures_received}"
            f" | malformed={self._malformed_failure_reports}"
            f" | acquisition_statuses={self._acquisition_statuses_received}"
            f" | malformed_acquisition={self._malformed_acquisition_statuses}"
            f" | transitions={self._transitions_published}"
            f" | duplicates={self._duplicate_transitions_suppressed}",
        )

    def on_signal(self, signal: Signal) -> None:
        if signal.name == PERSISTENCE_READY_SIGNAL:
            try:
                PersistenceReadyEvent.from_signal_value(signal.value)
            except ValueError as exc:
                self.log.error(
                    "PERSISTENCE_READY_REJECTED"
                    f" | reason=invalid_event | error={type(exc).__name__}",
                )
                return
            self._persistence_ready = True
            self._release_startup()
            return
        if signal.name == ACQUISITION_STATUS_SIGNAL:
            if not self._startup_released:
                return
            self._handle_acquisition_status(signal)
            return
        if signal.name != COMPONENT_FAILURE_SIGNAL:
            return
        self._component_failures_received += 1
        try:
            failure = ComponentFailureEvent.from_signal_value(signal.value)
        except ValueError as exc:
            self._malformed_failure_reports += 1
            self.log.error(
                f"COMPONENT_FAILURE_REJECTED | reason=invalid_event | error={type(exc).__name__}",
            )
            return
        target = component_failure_target(failure, self._health.state)
        self._unresolved_component_failure = True
        self._publish_transition(
            target,
            reason=failure.reason,
            evidence={
                **self._instrument_evidence(),
                "failed_component": failure.component,
                "failure_code": failure.code,
                **dict(failure.evidence),
            },
        )

    def _release_startup(self) -> None:
        if self._startup_released:
            return
        self._startup_released = True
        self.publish_signal(
            ACQUISITION_STATUS_REQUEST_SIGNAL,
            AcquisitionStatusRequest(requester=str(self.actor_id)).to_signal_value(),
        )
        self.clock.set_time_alert_ns(
            _INITIAL_EVALUATION_ALERT,
            self.clock.timestamp_ns() + _INITIAL_EVALUATION_DELAY_NS,
            callback=self._begin_evaluation,
        )

    def _handle_acquisition_status(self, signal: Signal) -> None:
        self._acquisition_statuses_received += 1
        try:
            status = AcquisitionStatusEvent.from_signal_value(signal.value)
        except ValueError as exc:
            self._malformed_acquisition_statuses += 1
            self.log.error(
                f"ACQUISITION_STATUS_REJECTED | reason=invalid_event | error={type(exc).__name__}",
            )
            return
        reported_expected = {
            InstrumentId.from_str(value) for value in status.expected_instrument_ids
        }
        if reported_expected != self._expected:
            self._malformed_acquisition_statuses += 1
            self.log.error(
                "ACQUISITION_STATUS_REJECTED | reason=instrument_set_mismatch",
            )
            return
        self._available = {
            InstrumentId.from_str(value) for value in status.available_instrument_ids
        }
        self.log.info(
            f"ACQUISITION_STATUS_ACCEPTED | state={status.state}"
            f" | available={len(self._available)}/{len(self._expected)}",
        )
        if not self._evaluation_started:
            self._begin_evaluation(None)
        if status.state == INSTRUMENTS_READY:
            self._publish_ready_if_complete()

    def on_fault(self) -> None:
        self._publish_transition(
            SystemHealthState.FAILED,
            reason="system control actor entered fault state",
            evidence=self._instrument_evidence(),
        )

    def _begin_evaluation(self, _event) -> None:  # noqa: ANN001
        if self._evaluation_started:
            return
        self._evaluation_started = True
        if self._health.state is None:
            self._publish_transition(
                SystemHealthState.STARTING,
                reason="evaluating runtime prerequisites",
                evidence=self._instrument_evidence(),
            )
        self.publish_signal(
            ACQUISITION_STATUS_REQUEST_SIGNAL,
            AcquisitionStatusRequest(requester=str(self.actor_id)).to_signal_value(),
        )
        self._publish_ready_if_complete()

    def _publish_ready_if_complete(self) -> None:
        if (
            not self._evaluation_started
            or not self._persistence_ready
            or self._available != self._expected
            or self._unresolved_component_failure
        ):
            return
        self._publish_transition(
            SystemHealthState.READY,
            reason="configured instrument definitions are available",
            evidence=self._instrument_evidence(),
        )

    def _publish_transition(
        self,
        target: SystemHealthState,
        *,
        reason: str,
        evidence: dict[str, str | int],
    ) -> None:
        event = self._health.transition(
            target,
            reason=reason,
            source=str(self.actor_id),
            evidence=evidence,
        )
        if event is None:
            self._duplicate_transitions_suppressed += 1
            return
        self._transitions_published += 1
        self.publish_signal(SYSTEM_HEALTH_SIGNAL, event.to_signal_value())
        self.log.info(
            f"SYSTEM_HEALTH | state={event.state} | reason={event.reason}"
            f" | available={len(self._available)}/{len(self._expected)}",
        )

    def _instrument_evidence(self) -> dict[str, str | int]:
        available = sorted(str(value) for value in self._available)
        expected = sorted(str(value) for value in self._expected)
        return {
            "available_instrument_count": len(available),
            "available_instruments": ",".join(available),
            "expected_instrument_count": len(expected),
            "expected_instruments": ",".join(expected),
            "operational_persistence_ready": self._persistence_ready,
            "operational_persistence_preflight_ready": self._persistence_preflight_ready,
        }
