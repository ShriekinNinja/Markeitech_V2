from __future__ import annotations

from queue import Queue
from types import SimpleNamespace
from uuid import UUID

from nautilus_trader.common import Signal

from markeitech.system.actor import SystemControlActor
from markeitech.system.control import ComponentFailureRule, SystemControlPolicy, SystemHealthState
from markeitech.system.messages import (
    COMPONENT_FAILURE_SIGNAL,
    COMPONENT_RECOVERY_SIGNAL,
    PERSISTENCE_READY_SIGNAL,
    ComponentFailureEvent,
    ComponentRecoveryEvent,
)
from markeitech.system.persistence import (
    OperationalPersistenceActor,
    PersistenceResult,
    _is_critical_record,
)

RUN_ID = "36a468b3-df4b-49fa-809e-c60e8d19d9a0"


def _signal(name: str, event: ComponentFailureEvent | ComponentRecoveryEvent) -> Signal:
    return Signal(name, event.to_signal_value(), 1, 1)


def test_control_clears_only_the_matching_failure_after_positive_recovery() -> None:
    transitions: list[SystemHealthState] = []
    ready_checks: list[bool] = []
    errors: list[str] = []
    requests: list[str] = []
    control = SimpleNamespace(
        actor_id="SYSTEM-CONTROL",
        _run_id=RUN_ID,
        _failure_policy=SystemControlPolicy(
            (ComponentFailureRule("operational_persistence", "FAILED", "DEGRADED"),),
        ),
        _ready_once=True,
        _health=SimpleNamespace(state=SystemHealthState.READY),
        _active_component_failures={},
        _component_failures_received=0,
        _readiness_evidence=lambda: {},
        log=SimpleNamespace(error=errors.append),
        _publish_transition=lambda target, **_kwargs: transitions.append(target),
        _publish_ready_if_complete=lambda: ready_checks.append(True),
        publish_signal=lambda name, _value: requests.append(name),
    )
    for code in ("operational_event_write_failed", "persistence_admission_rejected"):
        failure = ComponentFailureEvent(
            component="operational_persistence",
            code=code,
            reason="audit unavailable",
            evidence={"run_id": RUN_ID, "incident_id": code},
        )
        SystemControlActor.on_signal(control, _signal(COMPONENT_FAILURE_SIGNAL, failure))

    wrong = ComponentRecoveryEvent(
        component="operational_persistence",
        code="operational_event_write_failed",
        reason="writer restored",
        evidence={
            "run_id": "00000000-0000-0000-0000-000000000001",
            "incident_id": "operational_event_write_failed",
        },
    )
    SystemControlActor.on_signal(control, _signal(COMPONENT_RECOVERY_SIGNAL, wrong))
    assert len(control._active_component_failures) == 2

    stale = ComponentRecoveryEvent(
        component="operational_persistence",
        code="operational_event_write_failed",
        reason="writer restored",
        evidence={"run_id": RUN_ID, "incident_id": "earlier-incident"},
    )
    SystemControlActor.on_signal(control, _signal(COMPONENT_RECOVERY_SIGNAL, stale))
    assert len(control._active_component_failures) == 2

    for code in ("operational_event_write_failed", "persistence_admission_rejected"):
        recovered = ComponentRecoveryEvent(
            component="operational_persistence",
            code=code,
            reason="writer restored",
            evidence={"run_id": RUN_ID, "incident_id": code, "lost_event_count": 1},
        )
        SystemControlActor.on_signal(control, _signal(COMPONENT_RECOVERY_SIGNAL, recovered))
        assert len(ready_checks) == int(code == "persistence_admission_rejected")

    assert transitions == [SystemHealthState.DEGRADED, SystemHealthState.DEGRADED]
    assert not requests
    assert ready_checks == [True]
    assert any("run_id_mismatch" in value for value in errors)
    assert any("incident_id_mismatch" in value for value in errors)
    assert not control._active_component_failures


def test_recovery_does_not_revive_a_terminal_startup_failure() -> None:
    failure = ComponentFailureEvent(
        component="operational_persistence",
        code="operational_event_write_failed",
        reason="audit unavailable",
        evidence={"run_id": RUN_ID, "incident_id": "startup-incident"},
    )
    published: list[str] = []
    control = SimpleNamespace(
        _run_id=RUN_ID,
        _health=SimpleNamespace(state=SystemHealthState.FAILED),
        _active_component_failures={(failure.component, failure.code): failure},
        log=SimpleNamespace(error=lambda _message: None),
        publish_signal=lambda name, _value: published.append(name),
        _publish_ready_if_complete=lambda: published.append("READY"),
    )
    recovery = ComponentRecoveryEvent(
        component=failure.component,
        code=failure.code,
        reason="writer restored",
        evidence={"run_id": RUN_ID, "incident_id": "startup-incident"},
    )

    SystemControlActor.on_signal(control, _signal(COMPONENT_RECOVERY_SIGNAL, recovery))

    assert not control._active_component_failures
    assert not published


def test_persistence_publishes_recovery_only_after_recovery_fact_commits() -> None:
    results: Queue[PersistenceResult] = Queue()
    submitted = []
    published: list[tuple[str, str]] = []
    worker = SimpleNamespace(
        results=results,
        submit=lambda record, *, critical=False: submitted.append((record, critical)) or True,
    )
    persistence = SimpleNamespace(
        _worker=worker,
        _active=True,
        _run_id=UUID(RUN_ID),
        actor_id="OPERATIONAL-PERSISTENCE",
        _sequence=2,
        _active_failures={},
        _recovery_pending={},
        _lost_event_count=0,
        _first_lost_sequence=None,
        _last_lost_sequence=None,
        _write_retry_backoff_ms=0,
        _next_recovery_attempt_at=0.0,
        _ready_announced=False,
        log=SimpleNamespace(
            debug=lambda _message: None,
            error=lambda _message: None,
            info=lambda _message: None,
        ),
        publish_signal=lambda name, value: published.append((name, value)),
    )
    persistence._mark_lost = lambda sequence: OperationalPersistenceActor._mark_lost(
        persistence,
        sequence,
    )
    persistence._report_failure = lambda *args, **kwargs: (
        OperationalPersistenceActor._report_failure(persistence, *args, **kwargs)
    )
    persistence._queue_recovery_records = lambda: (
        OperationalPersistenceActor._queue_recovery_records(persistence)
    )
    persistence._publish_ready = lambda: OperationalPersistenceActor._publish_ready(persistence)

    results.put(PersistenceResult(1, "READY", False, 3, "OperationalError"))
    OperationalPersistenceActor._drain_results(persistence, None)
    assert [name for name, _ in published] == [COMPONENT_FAILURE_SIGNAL]
    marker, critical = submitted[0]
    assert marker.event_type == "component.recovery"
    assert marker.payload["evidence"]["lost_event_count"] == 1
    failure = ComponentFailureEvent.from_signal_value(published[0][1])
    assert marker.payload["evidence"]["incident_id"] == failure.evidence["incident_id"]
    assert critical and _is_critical_record(marker)

    results.put(PersistenceResult(marker.sequence, "RECOVERED", False, 3, "OperationalError"))
    OperationalPersistenceActor._drain_results(persistence, None)
    assert [name for name, _ in published] == [COMPONENT_FAILURE_SIGNAL]
    retry_marker, critical = submitted[1]
    assert retry_marker.payload["evidence"]["lost_event_count"] == 2
    assert critical

    results.put(PersistenceResult(retry_marker.sequence, "RECOVERED", True, 1))
    OperationalPersistenceActor._drain_results(persistence, None)
    assert [name for name, _ in published] == [
        COMPONENT_FAILURE_SIGNAL,
        COMPONENT_RECOVERY_SIGNAL,
        PERSISTENCE_READY_SIGNAL,
    ]
    assert not persistence._active_failures
