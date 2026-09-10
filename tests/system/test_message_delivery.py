from __future__ import annotations

import asyncio
from pathlib import Path
from threading import Event
from uuid import UUID

import pytest
from nautilus_trader.common import Environment, ImportableActorConfig
from nautilus_trader.live import LiveNode
from nautilus_trader.model import TraderId

from markeitech.system.composition import (
    StartupPrerequisites,
    build_actor_plan,
)
from markeitech.system.config import load_system_config
from tests.system.message_actor_fixtures import (
    calendar_received,
    current_state_received,
    inspectable_session_state_actors,
    projection_requests_complete,
    ready_received,
    received,
    received_calendar_projections,
    received_calendar_transitions,
    received_calendar_transitions_v2,
    received_current_state_snapshots,
    received_events,
    received_projection_requests,
)


@pytest.fixture(autouse=True)
def _write_calendar_catalog(tmp_path: Path) -> None:
    source = Path(__file__).parents[2] / "config/market-calendars.toml"
    (tmp_path / "market-calendars.toml").write_text(source.read_text())


async def _run_node_until(node: LiveNode, *events: Event) -> None:
    handle = node.handle()
    run_task = asyncio.create_task(node.run_async())
    try:
        observed = await asyncio.gather(
            *(asyncio.to_thread(event.wait, 2) for event in events),
        )
        assert all(observed)
    finally:
        handle.stop()
        await run_task


async def _run_node_until_then_hold(node: LiveNode, event: Event, hold_seconds: float) -> None:
    handle = node.handle()
    run_task = asyncio.create_task(node.run_async())
    try:
        assert await asyncio.to_thread(event.wait, 2)
        await asyncio.sleep(hold_seconds)
    finally:
        handle.stop()
        await run_task


def test_health_signal_delivers_between_actors_in_one_live_node() -> None:
    received.clear()
    received_events.clear()
    node = (
        LiveNode.builder(
            "MARKEITECH-V2-MESSAGE-TEST",
            TraderId.from_str("MARKEITECH-TEST-001"),
            Environment.SANDBOX,
        )
        .with_delay_post_stop_secs(0)
        .build()
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="tests.system.message_actor_fixtures:HealthSubscriber",
            config_path="tests.system.message_actor_fixtures:HealthSubscriberConfig",
            config={"actor_id": "HEALTH-SUBSCRIBER"},
        ),
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="tests.system.message_actor_fixtures:HealthPublisher",
            config_path="tests.system.message_actor_fixtures:HealthPublisherConfig",
            config={"actor_id": "HEALTH-PUBLISHER"},
        ),
    )

    asyncio.run(_run_node_until(node, received))

    assert len(received_events) == 1
    assert received_events[0].state == "READY"
    assert received_events[0].evidence == {"probe": True}


def test_session_state_delivers_typed_transition_and_projection() -> None:
    calendar_received.clear()
    received_calendar_transitions.clear()
    received_calendar_transitions_v2.clear()
    received_calendar_projections.clear()
    root = Path(__file__).parents[2]
    config = load_system_config(root / "config/system.v3-es-minimal.toml")
    session_state = next(
        item
        for item in build_actor_plan(
            config,
            StartupPrerequisites(
                run_id=UUID("00000000-0000-0000-0000-000000000001"),
                operational_persistence_ready=True,
            ),
        )
        if item.key == "session_state"
    )
    node = (
        LiveNode.builder(
            "MARKEITECH-V2-CALENDAR-MESSAGE-TEST",
            TraderId.from_str("MARKEITECH-TEST-001"),
            Environment.SANDBOX,
        )
        .with_delay_post_stop_secs(0)
        .build()
    )
    node.add_actor_from_config(session_state.config)
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="tests.system.message_actor_fixtures:CalendarProjectionProbe",
            config_path="tests.system.message_actor_fixtures:CalendarProjectionProbeConfig",
            config={
                "actor_id": "CALENDAR-PROJECTION-PROBE",
                "calendar_id": "cme_equity",
            },
        ),
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="tests.system.message_actor_fixtures:PersistenceReadyFixture",
            config_path="tests.system.message_actor_fixtures:PersistenceReadyFixtureConfig",
            config={"actor_id": "PERSISTENCE-READY-FIXTURE"},
        ),
    )

    asyncio.run(_run_node_until(node, calendar_received))

    assert received_calendar_transitions == []
    assert received_calendar_transitions_v2
    assert received_calendar_transitions_v2[0].source_epoch == (
        "00000000-0000-0000-0000-000000000001"
    )
    assert received_calendar_projections[0].status == "READY"
    assert received_calendar_projections[0].projections[0].definition_digest == (
        received_calendar_transitions_v2[0].definition_digest
    )


def test_session_state_delivers_one_cut_snapshot_and_replays_exact_duplicate() -> None:
    current_state_received.clear()
    received_calendar_transitions.clear()
    received_calendar_transitions_v2.clear()
    received_current_state_snapshots.clear()
    inspectable_session_state_actors.clear()
    root = Path(__file__).parents[2]
    config = load_system_config(root / "config/system.example.toml")
    source_epoch = "00000000-0000-0000-0000-000000000001"
    session_state = next(
        item
        for item in build_actor_plan(
            config,
            StartupPrerequisites(
                run_id=UUID(source_epoch),
                operational_persistence_ready=True,
            ),
        )
        if item.key == "session_state"
    )
    producer_config = dict(session_state.config.config)
    producer_config["allowed_current_state_requesters"] = [
        *producer_config["allowed_current_state_requesters"],
        "CURRENT-STATE-PROBE",
    ]
    calendar = config.sessions.calendars[0]
    node = (
        LiveNode.builder(
            "MARKEITECH-V2-CURRENT-STATE-MESSAGE-TEST",
            TraderId.from_str("MARKEITECH-TEST-001"),
            Environment.SANDBOX,
        )
        .with_delay_post_stop_secs(0)
        .build()
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="tests.system.message_actor_fixtures:InspectableSessionStateActor",
            config_path=session_state.config.config_path,
            config=producer_config,
        ),
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="tests.system.message_actor_fixtures:CalendarCurrentStateProbe",
            config_path=("tests.system.message_actor_fixtures:CalendarCurrentStateProbeConfig"),
            config={
                "actor_id": "CURRENT-STATE-PROBE",
                "calendar_id": calendar.calendar_id,
                "definition_version": calendar.definition_version,
                "definition_digest": calendar.definition_digest,
                "definition_effective_from_ns": calendar.effective_from_ns,
                "source_epoch": source_epoch,
                "additional_expectations": [
                    {
                        "calendar_id": item.calendar_id,
                        "definition_version": item.definition_version,
                        "definition_digest": item.definition_digest,
                        "definition_effective_from_ns": item.effective_from_ns,
                    }
                    for item in config.sessions.calendars[1:]
                ],
            },
        ),
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="tests.system.message_actor_fixtures:PersistenceReadyFixture",
            config_path="tests.system.message_actor_fixtures:PersistenceReadyFixtureConfig",
            config={"actor_id": "PERSISTENCE-READY-FIXTURE"},
        ),
    )
    asyncio.run(_run_node_until(node, current_state_received))

    assert len(received_current_state_snapshots) == 2
    assert received_current_state_snapshots[0] == received_current_state_snapshots[1]
    response = received_current_state_snapshots[0]
    assert response.status == "READY"
    assert len(response.states) == len(config.sessions.calendars)
    assert {state.evaluated_as_of_ns for state in response.states} == {
        response.evaluated_as_of_ns,
    }
    assert all(
        state.state_effective_from_ns <= state.state_revision_evaluated_as_of_ns
        for state in response.states
    )
    assert all(
        state.state_revision_evaluated_as_of_ns <= state.evaluated_as_of_ns
        for state in response.states
    )
    assert received_calendar_transitions == []
    assert len(received_calendar_transitions_v2) == len(config.sessions.calendars)
    actor = inspectable_session_state_actors[-1]
    revisions = dict(actor._revisions)
    actor._evaluate(None)
    assert dict(actor._revisions) == revisions
    assert actor._active is False
    assert actor._terminal is True
    assert actor._snapshot_cycles == {}
    assert "session-state-evaluation" not in actor.clock.timer_names()
    assert "session-state-next-boundary" not in actor.clock.timer_names()
    with pytest.raises(RuntimeError, match="cannot restart"):
        actor.on_start()


def test_session_state_returns_and_replays_complete_not_ready_snapshot() -> None:
    current_state_received.clear()
    received_calendar_transitions.clear()
    received_calendar_transitions_v2.clear()
    received_current_state_snapshots.clear()
    root = Path(__file__).parents[2]
    config = load_system_config(root / "config/system.v3-es-minimal.toml")
    source_epoch = "00000000-0000-0000-0000-000000000001"
    session_state = next(
        item
        for item in build_actor_plan(
            config,
            StartupPrerequisites(
                run_id=UUID(source_epoch),
                operational_persistence_ready=True,
            ),
        )
        if item.key == "session_state"
    )
    producer_config = dict(session_state.config.config)
    producer_config["allowed_current_state_requesters"] = ["CURRENT-STATE-PROBE"]
    calendar = config.sessions.calendars[0]
    node = (
        LiveNode.builder(
            "MARKEITECH-V2-CURRENT-STATE-NOT-READY-TEST",
            TraderId.from_str("MARKEITECH-TEST-001"),
            Environment.SANDBOX,
        )
        .with_delay_post_stop_secs(0)
        .build()
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path=session_state.config.actor_path,
            config_path=session_state.config.config_path,
            config=producer_config,
        ),
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="tests.system.message_actor_fixtures:CalendarCurrentStateProbe",
            config_path=("tests.system.message_actor_fixtures:CalendarCurrentStateProbeConfig"),
            config={
                "actor_id": "CURRENT-STATE-PROBE",
                "calendar_id": calendar.calendar_id,
                "definition_version": calendar.definition_version,
                "definition_digest": calendar.definition_digest,
                "definition_effective_from_ns": calendar.effective_from_ns,
                "source_epoch": source_epoch,
                "request_on_start": True,
            },
        ),
    )
    asyncio.run(_run_node_until(node, current_state_received))

    assert len(received_current_state_snapshots) == 2
    assert received_current_state_snapshots[0] == received_current_state_snapshots[1]
    response = received_current_state_snapshots[0]
    assert response.status == "NOT_READY"
    assert response.states == ()
    assert len(response.failures) == 1
    assert response.failures[0].code == "source_not_ready"
    assert response.failures[0].retryable is True
    assert response.retry_at_ns == response.failures[0].retry_at_ns


def test_session_state_contains_projection_failure_and_publishes_typed_response() -> None:
    calendar_received.clear()
    received_calendar_transitions.clear()
    received_calendar_projections.clear()
    root = Path(__file__).parents[2]
    config = load_system_config(root / "config/system.v3-es-minimal.toml")
    session_state = next(
        item
        for item in build_actor_plan(
            config,
            StartupPrerequisites(
                run_id=UUID("00000000-0000-0000-0000-000000000001"),
                operational_persistence_ready=True,
            ),
        )
        if item.key == "session_state"
    )
    failing_state = ImportableActorConfig(
        actor_path=("tests.system.message_actor_fixtures:FailingProjectionSessionStateActor"),
        config_path=session_state.config.config_path,
        config=session_state.config.config,
    )
    node = (
        LiveNode.builder(
            "MARKEITECH-V2-CALENDAR-FAILURE-MESSAGE-TEST",
            TraderId.from_str("MARKEITECH-TEST-001"),
            Environment.SANDBOX,
        )
        .with_delay_post_stop_secs(0)
        .build()
    )
    node.add_actor_from_config(failing_state)
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="tests.system.message_actor_fixtures:CalendarProjectionProbe",
            config_path="tests.system.message_actor_fixtures:CalendarProjectionProbeConfig",
            config={
                "actor_id": "CALENDAR-PROJECTION-PROBE",
                "calendar_id": "cme_equity",
                "projection_days": 20,
            },
        ),
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="tests.system.message_actor_fixtures:PersistenceReadyFixture",
            config_path="tests.system.message_actor_fixtures:PersistenceReadyFixtureConfig",
            config={"actor_id": "PERSISTENCE-READY-FIXTURE"},
        ),
    )

    asyncio.run(_run_node_until(node, calendar_received))

    response = received_calendar_projections[0]
    assert response.status == "FAILED"
    assert response.schema_version == 2
    assert response.failures[0].calendar_id == "cme_equity"
    assert response.failures[0].code == "projection_construction_failed"
    assert response.failures[0].retryable is False


def test_session_state_preserves_successful_calendar_in_mixed_failure_response() -> None:
    calendar_received.clear()
    received_calendar_transitions.clear()
    received_calendar_projections.clear()
    root = Path(__file__).parents[2]
    config = load_system_config(root / "config/system.example.toml")
    session_state = next(
        item
        for item in build_actor_plan(
            config,
            StartupPrerequisites(
                run_id=UUID("00000000-0000-0000-0000-000000000001"),
                operational_persistence_ready=True,
            ),
        )
        if item.key == "session_state"
    )
    node = (
        LiveNode.builder(
            "MARKEITECH-V2-MIXED-CALENDAR-FAILURE-TEST",
            TraderId.from_str("MARKEITECH-TEST-001"),
            Environment.SANDBOX,
        )
        .with_delay_post_stop_secs(0)
        .build()
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path=("tests.system.message_actor_fixtures:FailingProjectionSessionStateActor"),
            config_path=session_state.config.config_path,
            config=session_state.config.config,
        ),
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="tests.system.message_actor_fixtures:MultiCalendarProjectionProbe",
            config_path=("tests.system.message_actor_fixtures:MultiCalendarProjectionProbeConfig"),
            config={
                "actor_id": "CALENDAR-PROJECTION-PROBE",
                "calendar_ids": ["cme_equity", "us_equities"],
                "projection_days": 20,
            },
        ),
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="tests.system.message_actor_fixtures:PersistenceReadyFixture",
            config_path="tests.system.message_actor_fixtures:PersistenceReadyFixtureConfig",
            config={"actor_id": "PERSISTENCE-READY-FIXTURE"},
        ),
    )

    asyncio.run(_run_node_until(node, calendar_received))

    response = received_calendar_projections[0]
    assert response.status == "INCOMPLETE"
    assert [item.calendar_id for item in response.projections] == ["us_equities"]
    assert [item.calendar_id for item in response.failures] == ["cme_equity"]


def test_calendar_consumers_stop_after_bounded_correlated_timeouts() -> None:
    projection_requests_complete.clear()
    received_projection_requests.clear()
    root = Path(__file__).parents[2]
    config = load_system_config(root / "config/system.v3-es-minimal.toml")
    plan = build_actor_plan(
        config,
        StartupPrerequisites(
            run_id=UUID("00000000-0000-0000-0000-000000000001"),
            operational_persistence_ready=True,
        ),
    )
    keys = {"historical_evidence_planner"}
    registrations = [item for item in plan if item.key in keys]
    requesters = [item.actor_id for item in registrations]
    node = (
        LiveNode.builder(
            "MARKEITECH-V2-BOUNDED-CALENDAR-RETRY-TEST",
            TraderId.from_str("MARKEITECH-TEST-001"),
            Environment.SANDBOX,
        )
        .with_delay_post_stop_secs(0)
        .build()
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path=("tests.system.message_actor_fixtures:CalendarProjectionRequestCapture"),
            config_path=(
                "tests.system.message_actor_fixtures:CalendarProjectionRequestCaptureConfig"
            ),
            config={
                "actor_id": "CALENDAR-PROJECTION-REQUEST-CAPTURE",
                "expected_requesters": requesters,
                "target_per_requester": 3,
            },
        ),
    )
    for registration in registrations:
        node.add_actor_from_config(
            ImportableActorConfig(
                actor_path=registration.config.actor_path,
                config_path=registration.config.config_path,
                config={
                    **registration.config.config,
                    "projection_retry": {
                        "response_timeout_ms": 10,
                        "maximum_attempts": 3,
                        "retry_backoff_ms": 1,
                        "maximum_elapsed_ms": 100,
                    },
                },
            ),
        )

    asyncio.run(_run_node_until_then_hold(node, projection_requests_complete, 0.05))

    counts = {
        requester: sum(item.requester == requester for item in received_projection_requests)
        for requester in requesters
    }
    assert counts == {requester: 3 for requester in requesters}
    for requester in requesters:
        request_ids = {
            item.request_id for item in received_projection_requests if item.requester == requester
        }
        assert len(request_ids) == 3


def test_acquisition_status_publication_advances_control_to_ready() -> None:
    received.clear()
    ready_received.clear()
    received_events.clear()
    instrument_ids = ["ESU6.CME", "SPY.ARCA"]
    node = (
        LiveNode.builder(
            "MARKEITECH-V2-ACQUISITION-STATUS-TEST",
            TraderId.from_str("MARKEITECH-TEST-001"),
            Environment.SANDBOX,
        )
        .with_delay_post_stop_secs(0)
        .build()
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="tests.system.message_actor_fixtures:HealthSubscriber",
            config_path="tests.system.message_actor_fixtures:HealthSubscriberConfig",
            config={"actor_id": "HEALTH-SUBSCRIBER"},
        ),
    )
    control = ImportableActorConfig(
        actor_path="markeitech.system.actor:SystemControlActor",
        config_path="markeitech.system.actor:SystemControlActorConfig",
        config={
            "actor_id": "SYSTEM-CONTROL",
            "instrument_ids": instrument_ids,
            "operational_persistence_ready": True,
        },
    )
    acquisition = ImportableActorConfig(
        actor_path="tests.system.message_actor_fixtures:AcquisitionReadyFixture",
        config_path="tests.system.message_actor_fixtures:AcquisitionReadyFixtureConfig",
        config={
            "actor_id": "ACQUISITION-READY-FIXTURE",
            "instrument_ids": instrument_ids,
        },
    )
    persistence = ImportableActorConfig(
        actor_path="tests.system.message_actor_fixtures:PersistenceReadyFixture",
        config_path="tests.system.message_actor_fixtures:PersistenceReadyFixtureConfig",
        config={"actor_id": "PERSISTENCE-READY-FIXTURE"},
    )
    for actor in [control, acquisition, persistence]:
        node.add_actor_from_config(actor)

    asyncio.run(_run_node_until(node, ready_received))

    assert [event.state for event in received_events][:2] == ["STARTING", "READY"]
