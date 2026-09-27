from __future__ import annotations

from types import SimpleNamespace

from nautilus_trader.common import Signal

from markeitech.system.actor import SystemControlActor
from markeitech.system.control import SystemHealthState, SystemHealthStateMachine
from markeitech.system.resource_contracts import (
    RUNTIME_RESOURCE_HEALTH_SIGNAL,
    RUNTIME_RESOURCE_MONITOR_READY_SIGNAL,
    RuntimeResourceHealthEvent,
    RuntimeResourceMonitorReadyEvent,
)

RUN_ID = "36a468b3-df4b-49fa-809e-c60e8d19d9a0"


def _control() -> tuple[SimpleNamespace, list[str]]:
    machine = SystemHealthStateMachine()
    machine.transition(SystemHealthState.STARTING, reason="boot", source="SYSTEM-CONTROL")
    requests: list[str] = []
    control = SimpleNamespace(
        actor_id="SYSTEM-CONTROL",
        _run_id=RUN_ID,
        _resource_threshold_version="test-v1",
        _resource_monitor_ready=False,
        _resource_health_state="NORMAL",
        _resource_monitor_observed_ns=0,
        _health=machine,
        _persistence_ready=True,
        _evaluation_started=True,
        _active_component_failures={},
        _ready_once=False,
        _readiness_evidence=lambda: {},
        _publish_transition=lambda target, *, reason, evidence: machine.transition(
            target,
            reason=reason,
            source="SYSTEM-CONTROL",
            evidence=evidence,
        ),
        publish_signal=lambda name, _value: requests.append(name),
        log=SimpleNamespace(error=lambda _message: None),
    )
    control._publish_ready_if_complete = lambda: SystemControlActor._publish_ready_if_complete(
        control,
    )
    control._handle_resource_monitor_ready = lambda signal: (
        SystemControlActor._handle_resource_monitor_ready(control, signal)
    )
    control._handle_resource_health = lambda signal: SystemControlActor._handle_resource_health(
        control, signal,
    )
    return control, requests


def _ready(run_id: str = RUN_ID, state: str = "NORMAL") -> RuntimeResourceMonitorReadyEvent:
    return RuntimeResourceMonitorReadyEvent(
        run_id=run_id,
        source="RUNTIME-RESOURCE-HEALTH",
        sample_event_id="runtime-resource:RUNTIME-RESOURCES:1",
        sample_sequence=1,
        observed_ts_ns=1,
        state=state,
        threshold_version="test-v1",
    )


def _health(state: str, reason: str = "disk_free_bytes") -> RuntimeResourceHealthEvent:
    return RuntimeResourceHealthEvent(
        event_id=f"runtime-resource-health:RUNTIME-RESOURCE-HEALTH:2:{state}",
        source="RUNTIME-RESOURCE-HEALTH",
        observed_ts_ns=2,
        state=state,
        previous_state="NORMAL" if state == "CRITICAL" else "CRITICAL",
        reason_codes=(reason,),
        observations={"disk_free_bytes": 1},
        thresholds={"disk_free_bytes": 2},
        notification_eligible=True,
        threshold_version="test-v1",
    )


def test_ready_waits_for_current_run_first_assessment() -> None:
    control, _ = _control()
    control._publish_ready_if_complete()
    assert control._health.state is SystemHealthState.STARTING

    SystemControlActor.on_signal(
        control,
        Signal(RUNTIME_RESOURCE_MONITOR_READY_SIGNAL, _ready("other-run").to_signal_value(), 1, 1),
    )
    assert control._health.state is SystemHealthState.STARTING

    SystemControlActor.on_signal(
        control,
        Signal(RUNTIME_RESOURCE_MONITOR_READY_SIGNAL, _ready().to_signal_value(), 1, 1),
    )
    assert control._resource_monitor_ready
    assert control._health.state is SystemHealthState.READY


def test_critical_degrades_and_recovery_rechecks_other_gate() -> None:
    control, requests = _control()
    SystemControlActor.on_signal(
        control,
        Signal(RUNTIME_RESOURCE_MONITOR_READY_SIGNAL, _ready().to_signal_value(), 1, 1),
    )
    control._ready_once = True
    SystemControlActor.on_signal(
        control,
        Signal(RUNTIME_RESOURCE_HEALTH_SIGNAL, _health("CRITICAL").to_signal_value(), 2, 2),
    )
    assert control._health.state is SystemHealthState.DEGRADED

    SystemControlActor.on_signal(
        control,
        Signal(RUNTIME_RESOURCE_HEALTH_SIGNAL, _health("WARNING").to_signal_value(), 3, 3),
    )
    assert control._health.state is SystemHealthState.READY
    assert not requests


def test_confirmed_critical_first_assessment_blocks_ready() -> None:
    control, _ = _control()
    SystemControlActor.on_signal(
        control,
        Signal(
            RUNTIME_RESOURCE_MONITOR_READY_SIGNAL,
            _ready(state="CRITICAL").to_signal_value(),
            1,
            1,
        ),
    )
    assert control._resource_monitor_ready
    assert control._health.state is SystemHealthState.DEGRADED
    control._publish_ready_if_complete()
    assert control._health.state is SystemHealthState.DEGRADED


def test_critical_stale_samples_before_first_assessment_fail_startup() -> None:
    control, _ = _control()
    SystemControlActor.on_signal(
        control,
        Signal(
            RUNTIME_RESOURCE_HEALTH_SIGNAL,
            _health("CRITICAL", "resource_samples_stale").to_signal_value(),
            2,
            2,
        ),
    )
    assert control._health.state is SystemHealthState.FAILED
    SystemControlActor.on_signal(
        control,
        Signal(RUNTIME_RESOURCE_MONITOR_READY_SIGNAL, _ready().to_signal_value(), 3, 3),
    )
    assert not control._resource_monitor_ready
