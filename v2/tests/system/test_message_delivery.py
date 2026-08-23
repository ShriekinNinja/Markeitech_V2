from __future__ import annotations

from nautilus_trader.common import Environment, ImportableActorConfig
from nautilus_trader.live import LiveNode
from nautilus_trader.model import TraderId

from tests.system.message_actor_fixtures import (
    entity_received,
    ready_received,
    received,
    received_entity_revisions,
    received_events,
)


def test_health_signal_delivers_between_actors_in_one_live_node() -> None:
    received.clear()
    received_events.clear()
    node = LiveNode.builder(
        "MARKEITECH-V2-MESSAGE-TEST",
        TraderId.from_str("MARKEITECH-TEST-001"),
        Environment.SANDBOX,
    ).build()
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

    try:
        node.start()
        assert received.wait(timeout=2)
    finally:
        node.stop()

    assert len(received_events) == 1
    assert received_events[0].state == "READY"
    assert received_events[0].evidence == {"probe": True}


def test_acquisition_status_publication_advances_control_to_ready() -> None:
    received.clear()
    ready_received.clear()
    received_events.clear()
    instrument_ids = ["ESU6.CME", "SPY.ARCA"]
    node = LiveNode.builder(
        "MARKEITECH-V2-ACQUISITION-STATUS-TEST",
        TraderId.from_str("MARKEITECH-TEST-001"),
        Environment.SANDBOX,
    ).build()
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

    try:
        node.start()
        assert ready_received.wait(timeout=2)
    finally:
        node.stop()

    assert [event.state for event in received_events][:2] == ["STARTING", "READY"]


def test_metric_custom_data_projects_to_typed_entity_revision() -> None:
    entity_received.clear()
    received_entity_revisions.clear()
    node = LiveNode.builder(
        "MARKEITECH-V2-ENTITY-MESSAGE-TEST",
        TraderId.from_str("MARKEITECH-TEST-001"),
        Environment.SANDBOX,
    ).build()
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

    try:
        node.start()
        assert entity_received.wait(timeout=2)
    finally:
        node.stop()

    assert len(received_entity_revisions) == 1
    revision = received_entity_revisions[0]
    assert revision.identity.entity_type == "objective_level.previous_session_high"
    assert revision.payload.price == revision.payload.lower == revision.payload.upper


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
