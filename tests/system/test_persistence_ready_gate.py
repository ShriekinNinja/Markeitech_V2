from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from nautilus_trader.common import Signal

from markeitech.system.actor import SystemControlActor, SystemControlActorConfig
from markeitech.system.composition import StartupPrerequisites, build_actor_plan
from markeitech.system.control import SystemHealthState
from markeitech.system.messages import (
    PERSISTENCE_READY_REQUEST_SIGNAL,
    PERSISTENCE_READY_SIGNAL,
    PersistenceReadyEvent,
    PersistenceReadyRequest,
)
from markeitech.system.persistence import OperationalPersistenceActor
from tests.system.config_fixtures import minimal_calendar_config

RUN_ID = "36a468b3-df4b-49fa-809e-c60e8d19d9a0"


@pytest.mark.parametrize(
    ("source", "run_id", "accepted"),
    [
        ("OPERATIONAL-PERSISTENCE", RUN_ID, True),
        ("OTHER-ACTOR", RUN_ID, False),
        ("OPERATIONAL-PERSISTENCE", "00000000-0000-0000-0000-000000000001", False),
    ],
)
def test_control_accepts_persistence_ready_only_from_current_run(
    source: str,
    run_id: str,
    accepted: bool,
) -> None:
    releases: list[bool] = []
    errors: list[str] = []
    control = SimpleNamespace(
        _run_id=RUN_ID,
        _health=SimpleNamespace(state=None),
        _persistence_ready=False,
        _release_startup=lambda: releases.append(True),
        log=SimpleNamespace(error=errors.append),
    )
    ready = PersistenceReadyEvent(source=source, run_id=run_id)

    SystemControlActor.on_signal(
        control,
        Signal(PERSISTENCE_READY_SIGNAL, ready.to_signal_value(), 1, 1),
    )

    assert control._persistence_ready is accepted
    assert releases == ([True] if accepted else [])
    assert bool(errors) is not accepted


def test_control_requires_a_run_id_in_its_config() -> None:
    with pytest.raises(ValueError, match="run_id must be a non-empty string"):
        SystemControlActorConfig(
            run_id=" ",
            resource_threshold_version="test-v1",
            failure_policy=[
                {
                    "component": "operational_persistence",
                    "startup": "FAILED",
                    "running": "DEGRADED",
                },
            ],
        )


def test_terminal_startup_failure_cannot_be_released_by_late_persistence_ready() -> None:
    releases: list[bool] = []
    errors: list[str] = []
    control = SimpleNamespace(
        _run_id=RUN_ID,
        _health=SimpleNamespace(state=SystemHealthState.FAILED),
        _persistence_ready=False,
        _release_startup=lambda: releases.append(True),
        log=SimpleNamespace(error=errors.append),
    )
    ready = PersistenceReadyEvent(source="OPERATIONAL-PERSISTENCE", run_id=RUN_ID)

    SystemControlActor.on_signal(
        control,
        Signal(PERSISTENCE_READY_SIGNAL, ready.to_signal_value(), 1, 1),
    )

    assert not releases
    assert not control._persistence_ready
    assert errors == ["PERSISTENCE_READY_REJECTED | reason=terminal_state"]


def test_composition_passes_the_current_run_to_control() -> None:
    run_id = uuid4()
    plan = build_actor_plan(
        minimal_calendar_config(),
        StartupPrerequisites(run_id=run_id, operational_persistence_ready=True),
    )
    assert [item.key for item in plan] == [
        "system_control",
        "operational_persistence",
        "runtime_resources",
        "runtime_resource_health",
    ]

    control = next(item for item in plan if item.key == "system_control")
    assert control.config.config["run_id"] == str(run_id)
    assert {item["component"] for item in control.config.config["failure_policy"]} == {
        "operational_persistence", "runtime_resources", "runtime_resource_health",
    }
    assert control.config.config["resource_threshold_version"] == (
        minimal_calendar_config().runtime_resources.health.threshold_version
    )
    assert all(
        item.config.config["run_id"] == str(run_id)
        for item in plan
    )


def test_persistence_does_not_reply_ready_after_reported_failure() -> None:
    published: list[tuple[str, str]] = []
    persistence = SimpleNamespace(
        _subscribed_signals={PERSISTENCE_READY_REQUEST_SIGNAL},
        _active=True,
        _worker=object(),
        _active_failures={},
        _run_id=UUID(RUN_ID),
        actor_id="OPERATIONAL-PERSISTENCE",
        publish_signal=lambda name, value: published.append((name, value)),
    )
    persistence._publish_ready = lambda: OperationalPersistenceActor._publish_ready(persistence)
    request = Signal(
        PERSISTENCE_READY_REQUEST_SIGNAL,
        PersistenceReadyRequest(requester="SYSTEM-CONTROL").to_signal_value(),
        1,
        1,
    )

    OperationalPersistenceActor.on_signal(persistence, request)
    assert len(published) == 1
    assert published[0][0] == PERSISTENCE_READY_SIGNAL

    persistence._active_failures = {"operational_event_write_failed": "OperationalError"}
    OperationalPersistenceActor.on_signal(persistence, request)
    assert len(published) == 1
