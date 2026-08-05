from __future__ import annotations

import pytest

from markeitech.system.control import SystemHealthState, SystemHealthStateMachine


def test_control_plane_follows_the_approved_startup_and_stop_path() -> None:
    machine = SystemHealthStateMachine()

    starting = machine.transition(
        SystemHealthState.STARTING,
        reason="evaluating prerequisites",
        source="SYSTEM-CONTROL",
        evidence={"available_instrument_count": 0},
    )
    ready = machine.transition(
        SystemHealthState.READY,
        reason="instrument definitions available",
        source="SYSTEM-CONTROL",
        evidence={"available_instrument_count": 2},
    )
    stopping = machine.transition(
        SystemHealthState.STOPPING,
        reason="actor stopping",
        source="SYSTEM-CONTROL",
    )

    assert starting is not None and starting.state == "STARTING"
    assert ready is not None and ready.evidence["previous_state"] == "STARTING"
    assert stopping is not None and stopping.evidence["previous_state"] == "READY"
    assert machine.state is SystemHealthState.STOPPING


def test_control_plane_deduplicates_the_current_state() -> None:
    machine = SystemHealthStateMachine()
    machine.transition(
        SystemHealthState.STARTING,
        reason="evaluating prerequisites",
        source="SYSTEM-CONTROL",
    )

    duplicate = machine.transition(
        SystemHealthState.STARTING,
        reason="still evaluating",
        source="SYSTEM-CONTROL",
    )

    assert duplicate is None


def test_control_plane_rejects_invalid_transitions() -> None:
    machine = SystemHealthStateMachine()

    with pytest.raises(ValueError, match="UNINITIALIZED -> READY"):
        machine.transition(
            SystemHealthState.READY,
            reason="not established",
            source="SYSTEM-CONTROL",
        )


def test_control_plane_can_report_fault_before_stopping() -> None:
    machine = SystemHealthStateMachine()
    machine.transition(
        SystemHealthState.STARTING,
        reason="evaluating prerequisites",
        source="SYSTEM-CONTROL",
    )

    failed = machine.transition(
        SystemHealthState.FAILED,
        reason="actor faulted",
        source="SYSTEM-CONTROL",
    )
    stopping = machine.transition(
        SystemHealthState.STOPPING,
        reason="actor stopping",
        source="SYSTEM-CONTROL",
    )

    assert failed is not None and failed.state == "FAILED"
    assert stopping is not None and stopping.evidence["previous_state"] == "FAILED"


def test_control_plane_can_report_fault_before_initial_evaluation() -> None:
    machine = SystemHealthStateMachine()

    failed = machine.transition(
        SystemHealthState.FAILED,
        reason="actor faulted",
        source="SYSTEM-CONTROL",
    )

    assert failed is not None and failed.state == "FAILED"


def test_control_plane_does_not_advance_when_event_validation_fails() -> None:
    machine = SystemHealthStateMachine()

    with pytest.raises(ValueError, match="reason must be a non-empty string"):
        machine.transition(
            SystemHealthState.STARTING,
            reason="",
            source="SYSTEM-CONTROL",
        )

    assert machine.state is None
