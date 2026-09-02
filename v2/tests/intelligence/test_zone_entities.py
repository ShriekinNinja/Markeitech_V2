from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from markeitech.intelligence.entities import (
    EntityDefinition,
    EntityDependency,
    EntityDurability,
    EntityEvidenceKind,
    EntityEvidenceReference,
    EntityIdentity,
    EntityIdentityDimension,
    EntityLifecycle,
    EntityMetricDependency,
    EntityRevision,
    EntityStateBookLimits,
)
from markeitech.intelligence.entity_measurements import FvgDirection, SwingKind
from markeitech.intelligence.fvg_entities import FvgPayload
from markeitech.intelligence.market_structure_entities import ConfirmedSwingPayload
from markeitech.intelligence.metrics import MetricFidelity, MetricHealth
from markeitech.intelligence.session_entities import ObjectiveLevelPayload
from markeitech.intelligence.zone_entities import (
    DERIVED_ZONE_ENTITY_TYPE,
    DerivedZoneDefinition,
    DerivedZonePayload,
    DerivedZoneProjectionOwner,
    ZoneApplication,
    ZoneHorizonPolicy,
    ZonePartitionMethod,
    ZonePolicy,
    ZoneSourcePolicy,
    ZoneWeightingMethod,
)

HEALTH = (MetricHealth.READY, MetricHealth.DEGRADED, MetricHealth.STALE)
FIDELITY = (MetricFidelity.DERIVED, MetricFidelity.PARTIAL, MetricFidelity.REPORTED)


def _source_definition(
    entity_type: str,
    payload_type: type,
    metric_id: str,
) -> EntityDefinition:
    return EntityDefinition(
        entity_type=entity_type,
        version=1,
        decision_question=f"What is the objective {entity_type} geometry?",
        implementation_id=f"test.{entity_type}",
        payload_type=payload_type,
        identity_dimensions=("source_id",),
        metric_inputs=(EntityMetricDependency(metric_id, 1, True, HEALTH, FIDELITY),),
        entity_inputs=(),
        permitted_health=HEALTH,
        permitted_fidelities=FIDELITY,
        durability=EntityDurability.TRANSIENT,
        completion_rule="objective source completes",
        invalidation_rule="objective source invalidates",
        expiry_rule="objective source expires",
    )


def _source_definitions() -> tuple[EntityDefinition, ...]:
    return (
        _source_definition("objective_level", ObjectiveLevelPayload, "objective.metric"),
        _source_definition("confirmed_swing", ConfirmedSwingPayload, "swing.metric"),
        _source_definition("fair_value_gap", FvgPayload, "fvg.metric"),
    )


def _policy(
    *,
    merge_distance: str = "4",
    maximum_width: str = "20",
    maximum_age_ns: int = 1_000,
    minimum_constituents: int = 2,
    horizon_policy: ZoneHorizonPolicy = ZoneHorizonPolicy.SAME_HORIZON,
) -> ZonePolicy:
    return ZonePolicy(
        policy_id="nearby-geometry-v1",
        version=1,
        sources=(
            ZoneSourcePolicy(
                "objective_level",
                1,
                ("intraday_15m",),
                (EntityLifecycle.ACTIVE, EntityLifecycle.COMPLETE),
                False,
            ),
            ZoneSourcePolicy(
                "confirmed_swing",
                1,
                ("intraday_15m",),
                (EntityLifecycle.COMPLETE,),
                False,
            ),
            ZoneSourcePolicy(
                "fair_value_gap",
                1,
                ("intraday_15m",),
                (EntityLifecycle.ACTIVE,),
                False,
            ),
        ),
        horizon_policy=horizon_policy,
        partition_method=ZonePartitionMethod.ORDERED_CONNECTED,
        weighting_method=ZoneWeightingMethod.EQUAL,
        withdrawn_outcome=EntityLifecycle.INVALIDATED,
        merge_distance=Decimal(merge_distance),
        merge_distance_floor=Decimal("0"),
        merge_distance_ceiling=Decimal("20"),
        merge_distance_step=Decimal("0.25"),
        merge_distance_dynamic=True,
        padding=Decimal("1"),
        padding_floor=Decimal("0"),
        padding_ceiling=Decimal("5"),
        padding_step=Decimal("0.25"),
        padding_dynamic=True,
        maximum_width=Decimal(maximum_width),
        maximum_width_floor=Decimal("1"),
        maximum_width_ceiling=Decimal("50"),
        maximum_width_step=Decimal("0.25"),
        maximum_width_dynamic=True,
        minimum_constituents=minimum_constituents,
        minimum_constituents_floor=1,
        minimum_constituents_ceiling=5,
        minimum_constituents_step=1,
        minimum_constituents_dynamic=True,
        maximum_constituent_age_ns=maximum_age_ns,
        maximum_constituent_age_floor_ns=100,
        maximum_constituent_age_ceiling_ns=10_000,
        maximum_constituent_age_step_ns=100,
        maximum_constituent_age_dynamic=True,
        maximum_retained_sources=20,
    )


def _definition(policy: ZonePolicy | None = None) -> DerivedZoneDefinition:
    sources = _source_definitions()
    definition = EntityDefinition(
        entity_type=DERIVED_ZONE_ENTITY_TYPE,
        version=1,
        decision_question="Which compatible objective entities form geometric zones?",
        implementation_id="markeitech.entities.derived_zone",
        payload_type=DerivedZonePayload,
        identity_dimensions=(
            "application_id",
            "constituent_set_id",
            "definition_id",
            "policy_id",
            "policy_version",
        ),
        metric_inputs=(),
        entity_inputs=tuple(
            EntityDependency(item.entity_type, item.version, False, HEALTH, FIDELITY)
            for item in sources
        ),
        permitted_health=HEALTH,
        permitted_fidelities=FIDELITY,
        durability=EntityDurability.TRANSIENT,
        completion_rule="configured compatible constituents form a bounded interval",
        invalidation_rule="constituent composition no longer satisfies policy",
        expiry_rule="configured source age removes the final eligible composition",
    )
    return DerivedZoneDefinition(
        definition_id="objective-zone-v1",
        definition=definition,
        source_definitions=sources,
        applications=(
            ZoneApplication(
                application_id="cme-equity-zones",
                analytical_profile_ids=("cme_equity_primary",),
                instrument_ids=(),
                parameter_version=1,
                policy=policy or _policy(),
            ),
        ),
    )


def _owner(policy: ZonePolicy | None = None) -> DerivedZoneProjectionOwner:
    return DerivedZoneProjectionOwner(
        definitions=(_definition(policy),),
        limits=EntityStateBookLimits(100, 100, 100),
        maximum_publications_per_cycle=100,
        source="TEST-ZONE",
        schema_version=1,
    )


def _objective(
    source_id: str,
    price: str,
    effective_ts_ns: int,
    *,
    horizon: str = "intraday_15m",
    developing: bool = False,
    revision: int = 1,
    previous_revision: int | None = None,
) -> EntityRevision:
    value = Decimal(price)
    return _source_revision(
        "objective_level",
        source_id,
        ObjectiveLevelPayload(value, value, value, "session", horizon, "high", developing),
        effective_ts_ns,
        EntityLifecycle.ACTIVE,
        revision,
        previous_revision,
    )


def _swing(source_id: str, price: str, effective_ts_ns: int) -> EntityRevision:
    value = Decimal(price)
    return _source_revision(
        "confirmed_swing",
        source_id,
        ConfirmedSwingPayload(
            "swing-v1",
            "pivot-v1",
            1,
            "intraday_15m",
            "15-MINUTE-LAST-EXTERNAL",
            SwingKind.HIGH,
            value,
            Decimal("2"),
            value - Decimal("1"),
            Decimal("-1"),
            Decimal("100"),
            effective_ts_ns - 10,
            effective_ts_ns,
            2,
            2,
            (f"bar:{source_id}",),
        ),
        effective_ts_ns,
        EntityLifecycle.COMPLETE,
        1,
        None,
    )


def _fvg(source_id: str, lower: str, upper: str, effective_ts_ns: int) -> EntityRevision:
    low = Decimal(lower)
    high = Decimal(upper)
    return _source_revision(
        "fair_value_gap",
        source_id,
        FvgPayload(
            "fvg-v1",
            "fill-v1",
            1,
            "intraday_15m",
            "15-MINUTE-LAST-EXTERNAL",
            FvgDirection.BULLISH,
            low,
            high,
            high - low,
            None,
            None,
            None,
            Decimal("0"),
            low,
            high,
            effective_ts_ns - 30,
            effective_ts_ns - 20,
            effective_ts_ns - 10,
            None,
            None,
            0,
            ("bar:1", "bar:2", "bar:3"),
            (),
            ("width_normalization_not_configured",),
        ),
        effective_ts_ns,
        EntityLifecycle.ACTIVE,
        1,
        None,
    )


def _source_revision(
    entity_type: str,
    source_id: str,
    payload,
    effective_ts_ns: int,
    lifecycle: EntityLifecycle,
    revision: int,
    previous_revision: int | None,
) -> EntityRevision:
    identity = EntityIdentity(
        entity_type,
        1,
        "ESU6.CME",
        "cme_equity_primary",
        1,
        (EntityIdentityDimension("source_id", source_id),),
    )
    metric_id = {
        "objective_level": "objective.metric",
        "confirmed_swing": "swing.metric",
        "fair_value_gap": "fvg.metric",
    }[entity_type]
    return EntityRevision(
        identity,
        revision,
        1,
        payload,
        lifecycle,
        effective_ts_ns,
        effective_ts_ns,
        effective_ts_ns + 1,
        effective_ts_ns + 2,
        MetricHealth.READY,
        MetricFidelity.DERIVED,
        (
            EntityEvidenceReference(
                EntityEvidenceKind.METRIC,
                metric_id,
                f"metric:{metric_id}:{source_id}",
                1,
                revision,
                effective_ts_ns,
                MetricHealth.READY,
                MetricFidelity.DERIVED,
            ),
        ),
        (),
        (),
        "TEST-SOURCE",
        1,
        previous_revision,
    )


def _active(owner: DerivedZoneProjectionOwner) -> tuple[EntityRevision, ...]:
    return tuple(
        item
        for item in owner.snapshot(100_000).revisions
        if item.lifecycle is EntityLifecycle.ACTIVE
    )


def test_zone_policy_rejects_out_of_envelope_values() -> None:
    policy = _policy()
    with pytest.raises(ValueError, match="merge_distance is outside"):
        replace(policy, merge_distance=Decimal("21"))
    with pytest.raises(ValueError, match="minimum_constituents is outside"):
        replace(policy, minimum_constituents=6)


def test_nearby_objective_entities_form_one_lineage_complete_zone() -> None:
    owner = _owner()
    first = _objective("a", "100", 100)
    second = _objective("b", "103", 200)
    assert owner.ingest(first, now_ns=102) == ()
    published = owner.ingest(second, now_ns=202)
    assert len(published) == 1
    zone = _active(owner)[0]
    payload = zone.payload
    assert isinstance(payload, DerivedZonePayload)
    assert (payload.lower, payload.upper, payload.width, payload.center) == (
        Decimal("99"),
        Decimal("104"),
        Decimal("5"),
        Decimal("101.5"),
    )
    assert tuple(item.entity_id for item in payload.constituents) == tuple(
        sorted((first.entity_id, second.entity_id))
    )
    assert {(item.reference_id, item.revision) for item in zone.evidence_refs} == {
        (first.entity_id, 1),
        (second.entity_id, 1),
    }


def test_developing_and_wrong_horizon_sources_are_not_zone_constituents() -> None:
    owner = _owner()
    owner.ingest(_objective("developing", "100", 100, developing=True), now_ns=102)
    owner.ingest(_objective("wrong-horizon", "101", 200, horizon="intraday_1h"), now_ns=202)
    owner.ingest(_objective("eligible", "102", 300), now_ns=302)
    assert _active(owner) == ()


def test_swing_and_fvg_payloads_can_form_a_zone_without_semantic_labels() -> None:
    owner = _owner()
    swing = _swing("swing", "100", 100)
    fvg = _fvg("fvg", "101", "103", 200)
    owner.ingest(swing, now_ns=102)
    owner.ingest(fvg, now_ns=202)
    payload = _active(owner)[0].payload
    assert isinstance(payload, DerivedZonePayload)
    assert {item.entity_type for item in payload.constituents} == {
        "confirmed_swing",
        "fair_value_gap",
    }
    assert not hasattr(payload, "support")
    assert not hasattr(payload, "score")


def test_maximum_width_splits_ordered_components_deterministically() -> None:
    owner = _owner(_policy(merge_distance="10", maximum_width="6"))
    for source in (
        _objective("a", "100", 100),
        _objective("b", "103", 200),
        _objective("c", "107", 300),
    ):
        owner.ingest(source, now_ns=source.published_ts_ns)
    zones = _active(owner)
    assert len(zones) == 1
    payload = zones[0].payload
    assert isinstance(payload, DerivedZonePayload)
    assert tuple(item.entity_id for item in payload.constituents) == tuple(
        sorted((_objective("a", "100", 100).entity_id, _objective("b", "103", 200).entity_id))
    )


def test_merge_then_split_preserves_terminal_and_current_zone_history() -> None:
    owner = _owner()
    first = _objective("a", "100", 100)
    second = _objective("b", "103", 200)
    third = _objective("c", "106", 300)
    owner.ingest(first, now_ns=102)
    owner.ingest(second, now_ns=202)
    first_zone_id = _active(owner)[0].entity_id

    owner.ingest(third, now_ns=302)
    active = _active(owner)
    assert len(active) == 1
    merged_zone_id = active[0].entity_id
    assert merged_zone_id != first_zone_id
    by_id = {item.entity_id: item for item in owner.snapshot(1_000).revisions}
    assert by_id[first_zone_id].lifecycle is EntityLifecycle.INVALIDATED
    assert by_id[first_zone_id].effective_ts_ns == third.effective_ts_ns
    assert isinstance(by_id[first_zone_id].payload, DerivedZonePayload)
    assert by_id[first_zone_id].payload.terminal_ts_ns == third.effective_ts_ns

    moved = _objective("c", "120", 400, revision=2, previous_revision=1)
    owner.ingest(moved, now_ns=402)
    active = _active(owner)
    assert len(active) == 1
    assert active[0].entity_id == first_zone_id
    assert active[0].revision == 3
    by_id = {item.entity_id: item for item in owner.snapshot(1_000).revisions}
    assert by_id[merged_zone_id].lifecycle is EntityLifecycle.INVALIDATED
    assert by_id[merged_zone_id].effective_ts_ns == moved.effective_ts_ns
    assert isinstance(by_id[merged_zone_id].payload, DerivedZonePayload)
    assert by_id[merged_zone_id].payload.terminal_ts_ns == moved.effective_ts_ns


def test_late_distinct_source_arrival_converges_on_same_active_zone() -> None:
    sources = (
        _objective("a", "100", 100),
        _objective("b", "103", 200),
        _objective("c", "106", 300),
    )
    ordered = _owner()
    late = _owner()
    for source in sources:
        ordered.ingest(source, now_ns=400)
    for source in (sources[2], sources[0], sources[1]):
        late.ingest(source, now_ns=400)
    expected = _active(ordered)
    actual = _active(late)
    assert len(expected) == len(actual) == 1
    assert actual[0].identity == expected[0].identity
    assert actual[0].payload == expected[0].payload


def test_constituent_age_withdraws_zone_using_configured_terminal_outcome() -> None:
    owner = _owner(_policy(maximum_age_ns=100))
    owner.ingest(_objective("a", "100", 100), now_ns=102)
    owner.ingest(_objective("b", "103", 150), now_ns=152)
    zone_id = _active(owner)[0].entity_id
    owner.ingest(_objective("future", "200", 300), now_ns=302)
    by_id = {item.entity_id: item for item in owner.snapshot(1_000).revisions}
    assert by_id[zone_id].lifecycle is EntityLifecycle.INVALIDATED
    assert _active(owner) == ()


def test_zone_source_retention_is_bounded_by_policy() -> None:
    owner = _owner(replace(_policy(), maximum_retained_sources=2))
    for source in (
        _objective("a", "100", 100),
        _objective("b", "120", 200),
        _objective("c", "140", 300),
    ):
        owner.ingest(source, now_ns=source.published_ts_ns)
    assert owner.retained_sources == 2
    assert owner.counts.sources_evicted == 1
