from __future__ import annotations

import asyncio
from decimal import Decimal
from pathlib import Path
from threading import Event
from uuid import UUID

import pytest
from nautilus_trader.common import Environment, ImportableActorConfig
from nautilus_trader.live import LiveNode
from nautilus_trader.model import TraderId

from markeitech.intelligence import EntityLifecycle, VolatilityStatePayload
from markeitech.system.composition import (
    StartupPrerequisites,
    _entity_definition_payload,
    build_actor_plan,
)
from markeitech.system.config import load_system_config
from tests.system.message_actor_fixtures import (
    calendar_received,
    current_state_received,
    entity_received,
    inspectable_session_state_actors,
    market_state_received,
    projection_requests_complete,
    ready_received,
    received,
    received_calendar_projections,
    received_calendar_transitions,
    received_calendar_transitions_v2,
    received_current_state_snapshots,
    received_entity_revisions,
    received_entity_snapshots,
    received_events,
    received_projection_requests,
    snapshot_received,
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
    node = LiveNode.builder(
        "MARKEITECH-V2-MESSAGE-TEST",
        TraderId.from_str("MARKEITECH-TEST-001"),
        Environment.SANDBOX,
    ).with_delay_post_stop_secs(0).build()
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
    node = LiveNode.builder(
        "MARKEITECH-V2-CALENDAR-MESSAGE-TEST",
        TraderId.from_str("MARKEITECH-TEST-001"),
        Environment.SANDBOX,
    ).with_delay_post_stop_secs(0).build()
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

    assert received_calendar_transitions
    assert received_calendar_transitions[0].source_epoch == (
        "00000000-0000-0000-0000-000000000001"
    )
    assert received_calendar_projections[0].status == "READY"
    assert received_calendar_projections[0].projections[0].definition_digest == (
        received_calendar_transitions[0].definition_digest
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
    node = LiveNode.builder(
        "MARKEITECH-V2-CURRENT-STATE-MESSAGE-TEST",
        TraderId.from_str("MARKEITECH-TEST-001"),
        Environment.SANDBOX,
    ).with_delay_post_stop_secs(0).build()
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
            config_path=(
                "tests.system.message_actor_fixtures:CalendarCurrentStateProbeConfig"
            ),
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
    assert len(received_calendar_transitions) == len(config.sessions.calendars)
    assert received_calendar_transitions_v2 == []
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
    node = LiveNode.builder(
        "MARKEITECH-V2-CURRENT-STATE-NOT-READY-TEST",
        TraderId.from_str("MARKEITECH-TEST-001"),
        Environment.SANDBOX,
    ).with_delay_post_stop_secs(0).build()
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
            config_path=(
                "tests.system.message_actor_fixtures:CalendarCurrentStateProbeConfig"
            ),
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
        actor_path=(
            "tests.system.message_actor_fixtures:FailingProjectionSessionStateActor"
        ),
        config_path=session_state.config.config_path,
        config=session_state.config.config,
    )
    node = LiveNode.builder(
        "MARKEITECH-V2-CALENDAR-FAILURE-MESSAGE-TEST",
        TraderId.from_str("MARKEITECH-TEST-001"),
        Environment.SANDBOX,
    ).with_delay_post_stop_secs(0).build()
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
    node = LiveNode.builder(
        "MARKEITECH-V2-MIXED-CALENDAR-FAILURE-TEST",
        TraderId.from_str("MARKEITECH-TEST-001"),
        Environment.SANDBOX,
    ).with_delay_post_stop_secs(0).build()
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path=(
                "tests.system.message_actor_fixtures:FailingProjectionSessionStateActor"
            ),
            config_path=session_state.config.config_path,
            config=session_state.config.config,
        ),
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="tests.system.message_actor_fixtures:MultiCalendarProjectionProbe",
            config_path=(
                "tests.system.message_actor_fixtures:MultiCalendarProjectionProbeConfig"
            ),
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
    keys = {"evidence_health", "historical_evidence_planner"}
    registrations = [item for item in plan if item.key in keys]
    requesters = [item.actor_id for item in registrations]
    node = LiveNode.builder(
        "MARKEITECH-V2-BOUNDED-CALENDAR-RETRY-TEST",
        TraderId.from_str("MARKEITECH-TEST-001"),
        Environment.SANDBOX,
    ).with_delay_post_stop_secs(0).build()
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path=(
                "tests.system.message_actor_fixtures:CalendarProjectionRequestCapture"
            ),
            config_path=(
                "tests.system.message_actor_fixtures:"
                "CalendarProjectionRequestCaptureConfig"
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
            item.request_id
            for item in received_projection_requests
            if item.requester == requester
        }
        assert len(request_ids) == 3


def test_acquisition_status_publication_advances_control_to_ready() -> None:
    received.clear()
    ready_received.clear()
    received_events.clear()
    instrument_ids = ["ESU6.CME", "SPY.ARCA"]
    node = LiveNode.builder(
        "MARKEITECH-V2-ACQUISITION-STATUS-TEST",
        TraderId.from_str("MARKEITECH-TEST-001"),
        Environment.SANDBOX,
    ).with_delay_post_stop_secs(0).build()
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


def test_metric_custom_data_projects_to_typed_entity_revision() -> None:
    entity_received.clear()
    received_entity_revisions.clear()
    node = LiveNode.builder(
        "MARKEITECH-V2-ENTITY-MESSAGE-TEST",
        TraderId.from_str("MARKEITECH-TEST-001"),
        Environment.SANDBOX,
    ).with_delay_post_stop_secs(0).build()
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="tests.system.message_actor_fixtures:EntityRevisionSubscriber",
            config_path="tests.system.message_actor_fixtures:EntityRevisionSubscriberConfig",
            config={"actor_id": "ENTITY-REVISION-SUBSCRIBER"},
        ),
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path=(
                "markeitech.intelligence.session_entity_actor:SessionReferenceEntityActor"
            ),
            config_path=(
                "markeitech.intelligence.session_entity_actor:"
                "SessionReferenceEntityActorConfig"
            ),
            config={
                "actor_id": "SESSION-REFERENCE-ENTITIES",
                "instrument_profiles": {
                    "ESU6.CME": {
                        "profile_id": "cme_equity_primary",
                        "profile_version": 1,
                    },
                },
                "definitions": [_objective_level_definition()],
                "maximum_entities_global": 10,
                "maximum_entities_per_instrument": 10,
                "maximum_entities_per_type": 10,
                "maximum_metric_values": 10,
                "minimum_snapshot_interval_ms": 0,
                "maximum_publications_per_cycle": 10,
                "schema_version": 1,
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
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="tests.system.message_actor_fixtures:EntityMetricPublisher",
            config_path="tests.system.message_actor_fixtures:EntityMetricPublisherConfig",
            config={"actor_id": "ENTITY-METRIC-PUBLISHER"},
        ),
    )

    asyncio.run(_run_node_until(node, entity_received))

    assert len(received_entity_revisions) == 1
    revision = received_entity_revisions[0]
    assert revision.identity.entity_type == "objective_level.previous_session_high"
    assert revision.payload.price == revision.payload.lower == revision.payload.upper


def test_rolling_metrics_project_to_typed_volatility_state_revision() -> None:
    market_state_received.clear()
    received_entity_revisions.clear()
    node = LiveNode.builder(
        "MARKEITECH-V2-MARKET-STATE-MESSAGE-TEST",
        TraderId.from_str("MARKEITECH-TEST-001"),
        Environment.SANDBOX,
    ).with_delay_post_stop_secs(0).build()
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="tests.system.message_actor_fixtures:EntityRevisionSubscriber",
            config_path="tests.system.message_actor_fixtures:EntityRevisionSubscriberConfig",
            config={"actor_id": "ENTITY-REVISION-SUBSCRIBER"},
        ),
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="markeitech.intelligence.market_state_actor:MarketStateEntityActor",
            config_path=(
                "markeitech.intelligence.market_state_actor:MarketStateEntityActorConfig"
            ),
            config={
                "actor_id": "MARKET-STATE-ENTITIES",
                "instrument_profiles": {
                    "ESU6.CME": {
                        "profile_id": "cme_equity_primary",
                        "profile_version": 1,
                    },
                },
                "definitions": [_volatility_state_definition()],
                "maximum_entities_global": 10,
                "maximum_entities_per_instrument": 10,
                "maximum_entities_per_type": 10,
                "maximum_metric_values": 10,
                "reconciliation_interval_ms": 1000,
                "minimum_snapshot_interval_ms": 0,
                "maximum_publications_per_cycle": 10,
                "schema_version": 2,
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
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="tests.system.message_actor_fixtures:MarketStateMetricPublisher",
            config_path="tests.system.message_actor_fixtures:MarketStateMetricPublisherConfig",
            config={"actor_id": "MARKET-STATE-METRIC-PUBLISHER"},
        ),
    )

    asyncio.run(_run_node_until(node, market_state_received))

    revision = next(
        item
        for item in received_entity_revisions
        if item.identity.entity_type == "volatility_state"
        and item.lifecycle is EntityLifecycle.ACTIVE
    )
    assert isinstance(revision.payload, VolatilityStatePayload)
    assert revision.payload.normalized_value == revision.payload.classification.measure_value
    assert revision.payload.classification.category == "HIGH"
    assert revision.payload.classification.confirmed is True


def test_completed_bars_project_to_market_structure_revisions(tmp_path: Path) -> None:
    entity_received.clear()
    received_entity_revisions.clear()
    snapshot_received.clear()
    received_entity_snapshots.clear()
    root = Path(__file__).parents[2]
    source = (root / "config/system.example.toml").read_text()
    definitions = (Path(__file__).with_name("entity-analysis-definitions.toml")).read_text()
    config_path = tmp_path / "market-structure-message-config.toml"
    config_path.write_text(
        source.replace(
            "[metrics.session_measurements]\nenabled = false",
            "[metrics.session_measurements]\nenabled = true",
            1,
        ).replace(
            "[metrics.entity_analysis]\nenabled = false",
            "[metrics.entity_analysis]\nenabled = true",
        ).replace("definitions = []", definitions),
    )
    try:
        system_config = load_system_config(config_path)
    finally:
        config_path.unlink(missing_ok=True)
    definitions = tuple(
        item
        for item in system_config.metrics.entity_analysis.definitions
        if item.group == "swing_fvg_zone"
    )
    node = LiveNode.builder(
        "MARKEITECH-V2-MARKET-STRUCTURE-MESSAGE-TEST",
        TraderId.from_str("MARKEITECH-TEST-001"),
        Environment.SANDBOX,
    ).with_delay_post_stop_secs(0).build()
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="tests.system.message_actor_fixtures:EntityRevisionSubscriber",
            config_path="tests.system.message_actor_fixtures:EntityRevisionSubscriberConfig",
            config={"actor_id": "ENTITY-REVISION-SUBSCRIBER"},
        ),
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path=(
                "markeitech.intelligence.market_structure_actor:MarketStructureEntityActor"
            ),
            config_path=(
                "markeitech.intelligence.market_structure_actor:"
                "MarketStructureEntityActorConfig"
            ),
            config={
                "actor_id": "MARKET-STRUCTURE-ENTITIES",
                "instrument_profiles": {
                    "ESU6.CME": {
                        "profile_id": "cme_equity_primary",
                        "profile_version": 1,
                    },
                },
                "definitions": [_entity_definition_payload(item) for item in definitions],
                "maximum_entities_global": 100,
                "maximum_entities_per_instrument": 100,
                "maximum_entities_per_type": 100,
                "minimum_snapshot_interval_ms": 0,
                "maximum_publications_per_cycle": 100,
                "schema_version": 2,
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
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="tests.system.message_actor_fixtures:CompletedBarPublisher",
            config_path="tests.system.message_actor_fixtures:CompletedBarPublisherConfig",
            config={"actor_id": "COMPLETED-BAR-PUBLISHER"},
        ),
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="tests.system.message_actor_fixtures:EntitySnapshotRequester",
            config_path="tests.system.message_actor_fixtures:EntitySnapshotRequesterConfig",
            config={"actor_id": "ENTITY-SNAPSHOT-REQUESTER"},
        ),
    )

    asyncio.run(_run_node_until(node, entity_received, snapshot_received))

    swing = next(
        item
        for item in received_entity_revisions
        if item.identity.entity_type == "confirmed_swing"
    )
    assert swing.lifecycle is EntityLifecycle.COMPLETE
    assert swing.payload.pivot_price == Decimal("106")
    assert {
        "confirmed_swing",
        "swing_leg",
        "pivot_structure_state",
        "fair_value_gap",
        "derived_zone",
    } <= {item.identity.entity_type for item in received_entity_revisions}
    snapshot = received_entity_snapshots[0]
    assert snapshot.request_id == "market-structure-fixture-snapshot"
    assert snapshot.snapshot.revisions
    assert {
        item.identity.entity_type for item in snapshot.snapshot.revisions
    } == {"confirmed_swing"}


def _objective_level_definition() -> dict[str, object]:
    return {
        "definition_id": "previous-session-high-v1",
        "group": "objective_session_reference_level",
        "entity_type": "objective_level.previous_session_high",
        "entity_version": 1,
        "decision_question": "Where is the prior-session high objective reference?",
        "implementation_id": "markeitech.entity.objective_level.previous_session_high.v1",
        "identity_dimensions": [
            "definition_id",
            "horizon",
            "session_id",
            "source_metric",
            "trade_date",
        ],
        "durability": "FINALIZED_SESSION",
        "completion_rule": "source prior session completes",
        "invalidation_rule": "source metric identity conflict",
        "expiry_rule": "configured completed-session retention",
        "permitted_health": ["READY", "DEGRADED", "WARMING"],
        "permitted_fidelities": ["DERIVED", "PARTIAL"],
        "applications": [
            {
                "application_id": "cme-open",
                "analytical_profile_ids": ["cme_equity_primary"],
                "instrument_ids": [],
                "session_phases": ["OPEN"],
                "horizon": "previous_session",
            },
        ],
        "metric_inputs": [
            {
                "role": "price",
                "metric_id": "previous_session.high",
                "metric_version": 1,
                "parameter_version": 1,
                "required": True,
                "permitted_health": ["READY", "DEGRADED"],
                "permitted_fidelities": ["DERIVED", "PARTIAL"],
            },
        ],
        "entity_inputs": [],
    }


def _volatility_state_definition() -> dict[str, object]:
    return {
        "definition_id": "volatility-state-v1",
        "group": "volatility_compression_expansion",
        "entity_type": "volatility_state",
        "entity_version": 1,
        "decision_question": "What is the current numerical volatility state?",
        "implementation_id": "markeitech.entity.volatility_state.v1",
        "identity_dimensions": ["horizon", "definition_id"],
        "durability": "TRANSIENT",
        "completion_rule": "never completes while active",
        "invalidation_rule": "dependency identity conflict",
        "expiry_rule": "configured maximum input age",
        "permitted_health": ["READY", "DEGRADED", "WARMING", "STALE", "UNAVAILABLE"],
        "permitted_fidelities": ["DERIVED", "PARTIAL"],
        "applications": [
            {
                "application_id": "cme-fast",
                "analytical_profile_ids": ["cme_equity_primary"],
                "instrument_ids": [],
                "session_phases": ["OPEN"],
                "horizon": "fast",
            },
        ],
        "metric_inputs": [
            {
                "role": "normalized_volatility",
                "metric_id": "rolling.fast.context_45m.range_percentile_recent",
                "metric_version": 1,
                "parameter_version": 1,
                "required": True,
                "permitted_health": ["READY", "DEGRADED"],
                "permitted_fidelities": ["DERIVED", "PARTIAL"],
            },
            {
                "role": "coverage_ratio",
                "metric_id": "rolling.fast.context_45m.coverage_ratio",
                "metric_version": 1,
                "parameter_version": 1,
                "required": True,
                "permitted_health": ["READY", "DEGRADED"],
                "permitted_fidelities": ["DERIVED", "PARTIAL"],
            },
        ],
        "entity_inputs": [],
        "parameter_sets": [
            {
                "parameter_set_id": "volatility-test",
                "parameter_version": 1,
                "effective_from_ns": 1,
                "source": "TEST-CONFIG",
                "values": {
                    "low_upper": 0.25,
                    "typical_upper": 0.75,
                    "hysteresis": 0.05,
                    "confirmation": 1,
                    "minimum_coverage": 0.8,
                    "maximum_age_ms": 120000,
                },
            },
        ],
        "market_state": {
            "parameter_set_id": "volatility-test",
            "normalization": "recent_range_percentile",
            "policies": [
                {
                    "axis": "primary",
                    "policy_id": "volatility-primary",
                    "policy_version": 1,
                    "measure_role": "normalized_volatility",
                    "coverage_role": "coverage_ratio",
                    "unavailable_category": "UNAVAILABLE",
                    "bands": [
                        {"category": "LOW", "upper_bound_parameter_id": "low_upper"},
                        {
                            "category": "TYPICAL",
                            "lower_bound_parameter_id": "low_upper",
                            "upper_bound_parameter_id": "typical_upper",
                        },
                        {"category": "HIGH", "lower_bound_parameter_id": "typical_upper"},
                    ],
                    "hysteresis_parameter_id": "hysteresis",
                    "confirmation_observations_parameter_id": "confirmation",
                    "minimum_coverage_ratio_parameter_id": "minimum_coverage",
                    "maximum_evidence_age_ms_parameter_id": "maximum_age_ms",
                    "permitted_health": ["READY", "DEGRADED"],
                    "permitted_fidelities": ["DERIVED", "PARTIAL"],
                },
            ],
        },
    }
