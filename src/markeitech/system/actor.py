from __future__ import annotations

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId, InstrumentId

from markeitech.system.control import (
    ComponentFailureRule,
    SystemControlPolicy,
    SystemHealthState,
    SystemHealthStateMachine,
    component_failure_target,
)
from markeitech.system.messages import (
    ACQUISITION_STATUS_REQUEST_SIGNAL,
    ACQUISITION_STATUS_SIGNAL,
    COMPONENT_FAILURE_SIGNAL,
    COMPONENT_RECOVERY_SIGNAL,
    INSTRUMENTS_READY,
    PERSISTENCE_READY_REQUEST_SIGNAL,
    PERSISTENCE_READY_SIGNAL,
    SYSTEM_HEALTH_SIGNAL,
    AcquisitionStatusEvent,
    AcquisitionStatusRequest,
    ComponentFailureEvent,
    ComponentRecoveryEvent,
    PersistenceReadyEvent,
    PersistenceReadyRequest,
)

_INITIAL_EVALUATION_ALERT = "system-control-initial-evaluation"
_INITIAL_EVALUATION_DELAY_NS = 1_000_000
_PERSISTENCE_ACTOR_ID = "OPERATIONAL-PERSISTENCE"


class SystemControlActorConfig(DataActorConfig):
    def __new__(
        cls,
        instrument_ids: list[str],
        run_id: str,
        failure_policy: list[dict[str, str]],
        operational_persistence_ready: bool = False,
        actor_id: str | ActorId = "SYSTEM-CONTROL",
    ) -> SystemControlActorConfig:
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id must be a non-empty string")
        resolved_actor_id = (
            actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        )
        obj = super().__new__(cls, actor_id=resolved_actor_id)
        obj.instrument_ids = tuple(instrument_ids)
        obj.run_id = run_id.strip()
        rules: list[ComponentFailureRule] = []
        for item in failure_policy:
            if set(item) != {"component", "startup", "running"}:
                raise ValueError("failure_policy entries require component, startup, running")
            if item["startup"] not in {"FAILED", "DEGRADED"} or item["running"] not in {
                "FAILED",
                "DEGRADED",
            }:
                raise ValueError("failure_policy states must be FAILED or DEGRADED")
            rules.append(ComponentFailureRule(**item))
        if not rules or len({rule.component for rule in rules}) != len(rules):
            raise ValueError("failure_policy requires distinct components")
        obj.failure_policy = SystemControlPolicy(tuple(rules))
        obj.operational_persistence_ready = operational_persistence_ready
        return obj


class SystemControlActor(DataActor):
    """Coordinate system startup and health state.

    Markeitech Metadata:
        architecture.component.id: actor.system-control
        architecture.component.label: System Control
        architecture.component.kind: markeitech_actor
        architecture.component.boundary: boundary.system
    """

    def __init__(self, config: SystemControlActorConfig) -> None:
        super().__init__(config)
        self._expected = {InstrumentId.from_str(value) for value in config.instrument_ids}
        self._run_id = config.run_id
        self._failure_policy = config.failure_policy
        self._available: set[InstrumentId] = set()
        self._acquisition_ready = False
        self._health = SystemHealthStateMachine()
        self._evaluation_started = False
        self._persistence_preflight_ready = config.operational_persistence_ready
        self._persistence_ready = False
        self._startup_released = False
        self._active_component_failures: dict[tuple[str, str], ComponentFailureEvent] = {}
        self._ready_once = False
        self._component_failures_received = 0
        self._malformed_failure_reports = 0
        self._acquisition_statuses_received = 0
        self._malformed_acquisition_statuses = 0
        self._transitions_published = 0
        self._duplicate_transitions_suppressed = 0

    def on_start(self) -> None:
        self.subscribe_signal(COMPONENT_FAILURE_SIGNAL)
        self.subscribe_signal(COMPONENT_RECOVERY_SIGNAL)
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
        self.unsubscribe_signal(COMPONENT_RECOVERY_SIGNAL)
        self.unsubscribe_signal(ACQUISITION_STATUS_SIGNAL)
        self.unsubscribe_signal(PERSISTENCE_READY_SIGNAL)
        self.log.debug(
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
                ready = PersistenceReadyEvent.from_signal_value(signal.value)
            except ValueError as exc:
                self.log.error(
                    "PERSISTENCE_READY_REJECTED"
                    f" | reason=invalid_event | error={type(exc).__name__}",
                )
                return
            # A valid payload from another actor or run cannot release this startup gate.
            if ready.source != _PERSISTENCE_ACTOR_ID or ready.run_id != self._run_id:
                self.log.error("PERSISTENCE_READY_REJECTED | reason=identity_mismatch")
                return
            if self._health.state in {SystemHealthState.FAILED, SystemHealthState.STOPPING}:
                self.log.error("PERSISTENCE_READY_REJECTED | reason=terminal_state")
                return
            self._persistence_ready = True
            self._release_startup()
            return
        if signal.name == ACQUISITION_STATUS_SIGNAL:
            if not self._startup_released:
                return
            self._handle_acquisition_status(signal)
            return
        if signal.name == COMPONENT_RECOVERY_SIGNAL:
            try:
                recovery = ComponentRecoveryEvent.from_signal_value(signal.value)
            except ValueError as exc:
                self.log.error(
                    "COMPONENT_RECOVERY_REJECTED"
                    f" | reason=invalid_event | error={type(exc).__name__}",
                )
                return
            key = (recovery.component, recovery.code)
            if (
                recovery.component == "operational_persistence"
                and recovery.evidence.get("run_id") != self._run_id
            ):
                self.log.error("COMPONENT_RECOVERY_REJECTED | reason=run_id_mismatch")
                return
            if key not in self._active_component_failures:
                self.log.error("COMPONENT_RECOVERY_REJECTED | reason=no_matching_failure")
                return
            failure = self._active_component_failures[key]
            if recovery.component == "operational_persistence" and recovery.evidence.get(
                "incident_id"
            ) != failure.evidence.get("incident_id"):
                self.log.error("COMPONENT_RECOVERY_REJECTED | reason=incident_id_mismatch")
                return
            del self._active_component_failures[key]
            # Recovery clears current loss of capability; any earlier audit gap remains a fact.
            if not self._active_component_failures and self._health.state not in {
                SystemHealthState.FAILED,
                SystemHealthState.STOPPING,
            }:
                if self._ready_once:
                    # A prior acquisition acknowledgement may be stale after a degraded period.
                    self._acquisition_ready = False
                    self.publish_signal(
                        ACQUISITION_STATUS_REQUEST_SIGNAL,
                        AcquisitionStatusRequest(requester=str(self.actor_id)).to_signal_value(),
                    )
                else:
                    self._publish_ready_if_complete()
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
        if failure.component == "operational_persistence" and (
            failure.evidence.get("run_id") != self._run_id
            or not failure.evidence.get("incident_id")
        ):
            self.log.error("COMPONENT_FAILURE_REJECTED | reason=identity_mismatch")
            return
        target = component_failure_target(
            failure,
            self._health.state,
            self._failure_policy,
            ready_once=self._ready_once,
        )
        if target is None:
            self.log.error("COMPONENT_FAILURE_REJECTED | reason=unconfigured_component")
            return
        self._active_component_failures[(failure.component, failure.code)] = failure
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
        self.log.debug(
            f"ACQUISITION_STATUS_ACCEPTED | state={status.state}"
            f" | available={len(self._available)}/{len(self._expected)}",
        )
        self._acquisition_ready = status.state == INSTRUMENTS_READY
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
            self._health.state in {SystemHealthState.FAILED, SystemHealthState.STOPPING}
            or self._health.state == SystemHealthState.READY
            or not self._evaluation_started
            or not self._persistence_ready
            or not self._acquisition_ready
            or self._available != self._expected
            or self._active_component_failures
        ):
            return
        self._publish_transition(
            SystemHealthState.READY,
            reason=(
                "no instruments configured; operational acquisition is idle"
                if not self._expected
                else "configured instrument definitions are available"
            ),
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
        if target == SystemHealthState.READY:
            self._ready_once = True
        self._transitions_published += 1
        self.publish_signal(SYSTEM_HEALTH_SIGNAL, event.to_signal_value())
        message = (
            f"SYSTEM_HEALTH | state={event.state} | reason={event.reason}"
            f" | available={len(self._available)}/{len(self._expected)}"
        )
        if target == SystemHealthState.DEGRADED:
            self.log.warning(message)
        elif target == SystemHealthState.FAILED:
            self.log.error(message)
        else:
            self.log.info(message)

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
