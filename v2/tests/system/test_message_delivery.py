from __future__ import annotations

from nautilus_trader.common import Environment, ImportableActorConfig
from nautilus_trader.live import LiveNode
from nautilus_trader.model import TraderId

from markeitech.intelligence import EntityLifecycle, VolatilityStatePayload
from tests.system.message_actor_fixtures import (
    entity_received,
    market_state_received,
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


def test_rolling_metrics_project_to_typed_volatility_state_revision() -> None:
    market_state_received.clear()
    received_entity_revisions.clear()
    node = LiveNode.builder(
        "MARKEITECH-V2-MARKET-STATE-MESSAGE-TEST",
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

    try:
        node.start()
        assert market_state_received.wait(timeout=2)
    finally:
        node.stop()

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
