from __future__ import annotations

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId

from markeitech.system.control import (
    ComponentFailureRule,
    SystemControlPolicy,
    SystemHealthState,
    SystemHealthStateMachine,
    component_failure_target,
)
from markeitech.system.messages import (
    COMPONENT_FAILURE_SIGNAL,
    COMPONENT_RECOVERY_SIGNAL,
    PERSISTENCE_READY_REQUEST_SIGNAL,
    PERSISTENCE_READY_SIGNAL,
    SYSTEM_HEALTH_SIGNAL,
    ComponentFailureEvent,
    ComponentRecoveryEvent,
    PersistenceReadyEvent,
    PersistenceReadyRequest,
)
from markeitech.system.resource_contracts import (
    RUNTIME_RESOURCE_HEALTH_SIGNAL,
    RUNTIME_RESOURCE_MONITOR_READY_SIGNAL,
    RuntimeResourceHealthEvent,
    RuntimeResourceMonitorReadyEvent,
)

_INITIAL_EVALUATION_ALERT = "system-control-initial-evaluation"
_INITIAL_EVALUATION_DELAY_NS = 1_000_000
_PERSISTENCE_ACTOR_ID = "OPERATIONAL-PERSISTENCE"
_RESOURCE_HEALTH_ACTOR_ID = "RUNTIME-RESOURCE-HEALTH"
_RUN_SCOPED_COMPONENTS = frozenset(
    {"operational_persistence", "runtime_resources", "runtime_resource_health"},
)


class SystemControlActorConfig(DataActorConfig):
    def __new__(
        cls,
        run_id: str,
        failure_policy: list[dict[str, str]],
        resource_threshold_version: str,
        operational_persistence_ready: bool = False,
        actor_id: str | ActorId = "SYSTEM-CONTROL",
    ) -> SystemControlActorConfig:
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id must be a non-empty string")
        resolved_actor_id = (
            actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        )
        obj = super().__new__(cls, actor_id=resolved_actor_id)
        obj.run_id = run_id.strip()
        if (
            not isinstance(resource_threshold_version, str)
            or not resource_threshold_version.strip()
        ):
            raise ValueError("resource_threshold_version must be a non-empty string")
        obj.resource_threshold_version = resource_threshold_version.strip()
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
        self._run_id = config.run_id
        self._failure_policy = config.failure_policy
        self._resource_threshold_version = config.resource_threshold_version
        self._resource_monitor_ready = False
        self._resource_health_state = "NORMAL"
        self._resource_monitor_observed_ns = 0
        self._health = SystemHealthStateMachine()
        self._evaluation_started = False
        self._persistence_preflight_ready = config.operational_persistence_ready
        self._persistence_ready = False
        self._startup_released = False
        self._active_component_failures: dict[tuple[str, str], ComponentFailureEvent] = {}
        self._ready_once = False
        self._component_failures_received = 0
        self._malformed_failure_reports = 0
        self._transitions_published = 0
        self._duplicate_transitions_suppressed = 0

    def on_start(self) -> None:
        # Nautilus connects data clients and prepares their startup instruments before actors start.
        # Each data consumer validates the instrument contract it needs independently.
        self.subscribe_signal(COMPONENT_FAILURE_SIGNAL)
        self.subscribe_signal(COMPONENT_RECOVERY_SIGNAL)
        self.subscribe_signal(PERSISTENCE_READY_SIGNAL)
        self.subscribe_signal(RUNTIME_RESOURCE_MONITOR_READY_SIGNAL)
        self.subscribe_signal(RUNTIME_RESOURCE_HEALTH_SIGNAL)
        self.publish_signal(
            PERSISTENCE_READY_REQUEST_SIGNAL,
            PersistenceReadyRequest(requester=str(self.actor_id)).to_signal_value(),
        )

    def on_stop(self) -> None:
        self._publish_transition(
            SystemHealthState.STOPPING,
            reason="system control actor is stopping",
            evidence=self._readiness_evidence(),
        )
        self.unsubscribe_signal(COMPONENT_FAILURE_SIGNAL)
        self.unsubscribe_signal(COMPONENT_RECOVERY_SIGNAL)
        self.unsubscribe_signal(PERSISTENCE_READY_SIGNAL)
        self.unsubscribe_signal(RUNTIME_RESOURCE_MONITOR_READY_SIGNAL)
        self.unsubscribe_signal(RUNTIME_RESOURCE_HEALTH_SIGNAL)
        self.log.debug(
            "SYSTEM_CONTROL_SUMMARY"
            f" | component_failures={self._component_failures_received}"
            f" | malformed={self._malformed_failure_reports}"
            f" | transitions={self._transitions_published}"
            f" | duplicates={self._duplicate_transitions_suppressed}",
        )

    def on_signal(self, signal: Signal) -> None:
        if signal.name == RUNTIME_RESOURCE_MONITOR_READY_SIGNAL:
            self._handle_resource_monitor_ready(signal)
            return
        if signal.name == RUNTIME_RESOURCE_HEALTH_SIGNAL:
            self._handle_resource_health(signal)
            return
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
                # Recovery recomputes only the global operational gates still owned here.
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
        if failure.component in _RUN_SCOPED_COMPONENTS and (
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
                **self._readiness_evidence(),
                "failed_component": failure.component,
                "failure_code": failure.code,
                **dict(failure.evidence),
            },
        )

    def _handle_resource_monitor_ready(self, signal: Signal) -> None:
        try:
            ready = RuntimeResourceMonitorReadyEvent.from_signal_value(signal.value)
        except ValueError as exc:
            self.log.error(f"RESOURCE_MONITOR_READY_REJECTED | error={type(exc).__name__}")
            return
        if (
            ready.run_id != self._run_id
            or ready.source != _RESOURCE_HEALTH_ACTOR_ID
            or ready.threshold_version != self._resource_threshold_version
        ):
            self.log.error("RESOURCE_MONITOR_READY_REJECTED | reason=identity_mismatch")
            return
        if self._health.state in {SystemHealthState.FAILED, SystemHealthState.STOPPING}:
            return
        if self._resource_monitor_ready:
            return
        # This acknowledgement proves both required actors completed the first sample handoff.
        self._resource_monitor_ready = True
        self._resource_monitor_observed_ns = ready.observed_ts_ns
        self._resource_health_state = ready.state
        if ready.state == "CRITICAL":
            self._publish_transition(
                SystemHealthState.DEGRADED,
                reason="confirmed critical runtime resource health",
                evidence=self._readiness_evidence(),
            )
        else:
            self._publish_ready_if_complete()

    def _handle_resource_health(self, signal: Signal) -> None:
        try:
            health = RuntimeResourceHealthEvent.from_signal_value(signal.value)
        except ValueError as exc:
            self.log.error(f"RESOURCE_HEALTH_REJECTED | error={type(exc).__name__}")
            return
        if (
            health.source != _RESOURCE_HEALTH_ACTOR_ID
            or health.threshold_version != self._resource_threshold_version
            or (
                self._resource_monitor_ready
                and health.observed_ts_ns < self._resource_monitor_observed_ns
            )
        ):
            self.log.error("RESOURCE_HEALTH_REJECTED | reason=identity_mismatch")
            return
        if self._health.state in {SystemHealthState.FAILED, SystemHealthState.STOPPING}:
            return
        if not self._resource_monitor_ready and health.state != "CRITICAL":
            # The first-sample acknowledgement carries the initial confirmed state.
            return
        previous = self._resource_health_state
        self._resource_health_state = health.state
        if health.state == "CRITICAL":
            # No first sample by the stale threshold means mandatory monitoring never started.
            target = (
                SystemHealthState.FAILED
                if not self._resource_monitor_ready
                and "resource_samples_stale" in health.reason_codes
                else SystemHealthState.DEGRADED
            )
            self._publish_transition(
                target,
                reason="confirmed critical runtime resource health",
                evidence={
                    **self._readiness_evidence(),
                    "resource_reasons": ",".join(health.reason_codes),
                },
            )
        elif previous == "CRITICAL" and not self._active_component_failures:
            # Resource recovery can restore READY only when the other global gates still hold.
            self._publish_ready_if_complete()

    def _release_startup(self) -> None:
        if self._startup_released:
            return
        self._startup_released = True
        self.clock.set_time_alert_ns(
            _INITIAL_EVALUATION_ALERT,
            self.clock.timestamp_ns() + _INITIAL_EVALUATION_DELAY_NS,
            callback=self._begin_evaluation,
        )

    def on_fault(self) -> None:
        self._publish_transition(
            SystemHealthState.FAILED,
            reason="system control actor entered fault state",
            evidence=self._readiness_evidence(),
        )

    def _begin_evaluation(self, _event) -> None:  # noqa: ANN001
        if self._evaluation_started:
            return
        self._evaluation_started = True
        if self._health.state is None:
            self._publish_transition(
                SystemHealthState.STARTING,
                reason="evaluating runtime prerequisites",
                evidence=self._readiness_evidence(),
            )
        self._publish_ready_if_complete()

    def _publish_ready_if_complete(self) -> None:
        if (
            self._health.state in {SystemHealthState.FAILED, SystemHealthState.STOPPING}
            or self._health.state == SystemHealthState.READY
            or not self._evaluation_started
            or not self._persistence_ready
            or not self._resource_monitor_ready
            or self._resource_health_state == "CRITICAL"
            or self._active_component_failures
        ):
            return
        self._publish_transition(
            SystemHealthState.READY,
            reason="operational prerequisites are ready",
            evidence=self._readiness_evidence(),
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
        message = f"SYSTEM_HEALTH | state={event.state} | reason={event.reason}"
        if target == SystemHealthState.DEGRADED:
            self.log.warning(message)
        elif target == SystemHealthState.FAILED:
            self.log.error(message)
        else:
            self.log.info(message)

    def _readiness_evidence(self) -> dict[str, str | int]:
        # Keep global health evidence about operational prerequisites, not market inputs.
        return {
            "operational_persistence_ready": self._persistence_ready,
            "operational_persistence_preflight_ready": self._persistence_preflight_ready,
            "resource_monitor_ready": self._resource_monitor_ready,
            "resource_health_state": self._resource_health_state,
        }
