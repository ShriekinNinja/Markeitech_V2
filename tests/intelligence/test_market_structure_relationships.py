from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from markeitech.intelligence import (
    SWING_PIVOT_PRICE_METRIC_ID,
    SWING_PROMINENCE_METRIC_ID,
    CompletedBarInput,
    CompletedBarSource,
    ConfirmedSwingPayload,
    EntityDefinition,
    EntityDependency,
    EntityDurability,
    EntityIdentity,
    EntityIdentityDimension,
    EntityLifecycle,
    EntityMetricDependency,
    EntityRevision,
    EntityStateBookLimits,
    LegScaleRelationship,
    MarketStructureRelationshipDefinition,
    MarketStructureRelationshipOwner,
    MetricFidelity,
    MetricHealth,
    PivotChainPolicy,
    PivotGeometryState,
    PivotRelationship,
    PivotStructureApplication,
    PivotStructurePayload,
    ResolvedRunSelection,
    ResolvedRunTieBreak,
    SameKindPivotPolicy,
    SwingKind,
    SwingLegPayload,
    SwingNormalizationEvidence,
)

MINUTE_NS = 60_000_000_000
BAR_NS = 5 * MINUTE_NS
PERMITTED_HEALTH = (MetricHealth.READY, MetricHealth.DEGRADED, MetricHealth.STALE)
PERMITTED_FIDELITY = (
    MetricFidelity.DERIVED,
    MetricFidelity.PARTIAL,
    MetricFidelity.REPORTED,
)


def _entity_dependency(entity_type: str, *, required: bool = True) -> EntityDependency:
    return EntityDependency(
        entity_type,
        1,
        required,
        PERMITTED_HEALTH,
        PERMITTED_FIDELITY,
    )


def _definitions(
    *,
    same_kind_policy: SameKindPivotPolicy = SameKindPivotPolicy.MORE_EXTREME_TERMINAL,
    equality_tolerance: str = "0.5",
    minimum_leg_displacement: str = "0",
    maximum_retained_pivots: int = 20,
    maximum_selected_pivots: int = 10,
    detector_ids: tuple[str, ...] = ("tactical",),
    horizons: tuple[str, ...] = ("intraday_5m",),
) -> MarketStructureRelationshipDefinition:
    confirmed = EntityDefinition(
        entity_type="confirmed_swing",
        version=1,
        decision_question="Which strict pivots are confirmed?",
        implementation_id="markeitech.entities.confirmed_swing",
        payload_type=ConfirmedSwingPayload,
        identity_dimensions=(
            "bar_specification",
            "definition_id",
            "detector_id",
            "detector_version",
            "horizon",
            "pivot_timestamp",
            "swing_kind",
        ),
        metric_inputs=tuple(
            EntityMetricDependency(
                item,
                1,
                True,
                PERMITTED_HEALTH,
                PERMITTED_FIDELITY,
            )
            for item in (SWING_PIVOT_PRICE_METRIC_ID, SWING_PROMINENCE_METRIC_ID)
        ),
        entity_inputs=(),
        permitted_health=PERMITTED_HEALTH,
        permitted_fidelities=PERMITTED_FIDELITY,
        durability=EntityDurability.TRANSIENT,
        completion_rule="right-span confirmation",
        invalidation_rule="identity conflict",
        expiry_rule="bounded retention",
    )
    leg = EntityDefinition(
        entity_type="swing_leg",
        version=1,
        decision_question="How are compatible alternating pivots geometrically related?",
        implementation_id="markeitech.entities.swing_leg",
        payload_type=SwingLegPayload,
        identity_dimensions=(
            "bar_specification",
            "chain_policy_id",
            "chain_policy_version",
            "definition_id",
            "destination_entity_id",
            "horizon",
            "origin_entity_id",
        ),
        metric_inputs=(
            EntityMetricDependency(
                "atr-normalization",
                1,
                False,
                PERMITTED_HEALTH,
                PERMITTED_FIDELITY,
            ),
        ),
        entity_inputs=(_entity_dependency("confirmed_swing"),),
        permitted_health=PERMITTED_HEALTH,
        permitted_fidelities=PERMITTED_FIDELITY,
        durability=EntityDurability.TRANSIENT,
        completion_rule="two compatible alternating confirmed pivots",
        invalidation_rule="endpoint or chain identity conflict",
        expiry_rule="bounded relationship retention",
    )
    structure = EntityDefinition(
        entity_type="pivot_structure_state",
        version=1,
        decision_question="What relationships do confirmed pivots describe on one horizon?",
        implementation_id="markeitech.entities.pivot_structure",
        payload_type=PivotStructurePayload,
        identity_dimensions=(
            "bar_specification",
            "chain_policy_id",
            "chain_policy_version",
            "definition_id",
            "detector_id",
            "detector_version",
            "horizon",
        ),
        metric_inputs=(),
        entity_inputs=(
            _entity_dependency("confirmed_swing"),
            _entity_dependency("swing_leg", required=False),
        ),
        permitted_health=PERMITTED_HEALTH,
        permitted_fidelities=PERMITTED_FIDELITY,
        durability=EntityDurability.TRANSIENT,
        completion_rule="current bounded chain projection",
        invalidation_rule="chain identity conflict",
        expiry_rule="application removal or bounded retention",
    )
    return MarketStructureRelationshipDefinition(
        definition_id="pivot-relationships-v1",
        confirmed_swing_definition=confirmed,
        swing_leg_definition=leg,
        pivot_structure_definition=structure,
        applications=(
            PivotStructureApplication(
                application_id="cme-intraday-structure",
                analytical_profile_ids=("cme_equity_primary",),
                instrument_ids=(),
                confirmed_swing_definition_ids=("confirmed-swing-v1",),
                detector_ids=detector_ids,
                horizons=horizons,
                bar_specifications=("5-MINUTE-LAST-EXTERNAL",),
                parameter_version=1,
                policy=PivotChainPolicy(
                    policy_id="alternating-more-extreme",
                    version=1,
                    source_interval_ns=BAR_NS,
                    same_kind_policy=same_kind_policy,
                    resolved_run_selection=ResolvedRunSelection.MORE_EXTREME,
                    resolved_run_tie_break=ResolvedRunTieBreak.LATEST,
                    equality_tolerance=Decimal(equality_tolerance),
                    equality_tolerance_floor=Decimal("0"),
                    equality_tolerance_ceiling=Decimal("10"),
                    equality_tolerance_step=Decimal("0.25"),
                    equality_tolerance_dynamic=True,
                    minimum_leg_displacement=Decimal(minimum_leg_displacement),
                    minimum_leg_displacement_floor=Decimal("0"),
                    minimum_leg_displacement_ceiling=Decimal("100"),
                    minimum_leg_displacement_step=Decimal("0.25"),
                    minimum_leg_displacement_dynamic=True,
                    leg_scale_ratio_tolerance=Decimal("0.10"),
                    leg_scale_ratio_tolerance_floor=Decimal("0"),
                    leg_scale_ratio_tolerance_ceiling=Decimal("1"),
                    leg_scale_ratio_tolerance_step=Decimal("0.01"),
                    leg_scale_ratio_tolerance_dynamic=True,
                    maximum_retained_pivots=maximum_retained_pivots,
                    maximum_retained_bars=100,
                    maximum_retained_normalizations=20,
                    maximum_selected_pivots=maximum_selected_pivots,
                ),
                volatility_metric_id="atr-normalization",
                volatility_metric_version=1,
                volatility_max_age_ns=6 * BAR_NS,
            ),
        ),
    )


def _owner(definition: MarketStructureRelationshipDefinition) -> MarketStructureRelationshipOwner:
    return MarketStructureRelationshipOwner(
        definitions=(definition,),
        limits=EntityStateBookLimits(100, 100, 100),
        maximum_publications_per_cycle=100,
        source="TEST-RELATIONSHIPS",
        schema_version=1,
    )


def _swing(
    index: int,
    kind: SwingKind,
    price: str,
    *,
    detector_id: str = "tactical",
    horizon: str = "intraday_5m",
) -> EntityRevision:
    pivot_ts_ns = (index + 1) * BAR_NS
    confirmation_ts_ns = pivot_ts_ns + BAR_NS
    identity = EntityIdentity(
        entity_type="confirmed_swing",
        entity_version=1,
        instrument_id="ESU6.CME",
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        dimensions=(
            EntityIdentityDimension("bar_specification", "5-MINUTE-LAST-EXTERNAL"),
            EntityIdentityDimension("definition_id", "confirmed-swing-v1"),
            EntityIdentityDimension("detector_id", detector_id),
            EntityIdentityDimension("detector_version", "1"),
            EntityIdentityDimension("horizon", horizon),
            EntityIdentityDimension("pivot_timestamp", str(pivot_ts_ns)),
            EntityIdentityDimension("swing_kind", kind.value),
        ),
    )
    value = Decimal(price)
    return EntityRevision(
        identity=identity,
        revision=1,
        parameter_version=1,
        payload=ConfirmedSwingPayload(
            definition_id="confirmed-swing-v1",
            detector_id=detector_id,
            detector_version=1,
            horizon=horizon,
            bar_specification="5-MINUTE-LAST-EXTERNAL",
            kind=kind,
            pivot_price=value,
            prominence=Decimal("1"),
            confirmation_close=value,
            confirmation_displacement=Decimal("0"),
            pivot_bar_volume=Decimal("10"),
            pivot_ts_ns=pivot_ts_ns,
            confirmation_ts_ns=confirmation_ts_ns,
            left_span_bars=1,
            right_span_bars=1,
            evidence_bar_refs=(f"bar:{index}",),
        ),
        lifecycle=EntityLifecycle.COMPLETE,
        effective_ts_ns=confirmation_ts_ns,
        observed_ts_ns=confirmation_ts_ns,
        calculated_ts_ns=confirmation_ts_ns,
        published_ts_ns=confirmation_ts_ns,
        health=MetricHealth.READY,
        fidelity=MetricFidelity.DERIVED,
        evidence_refs=(),
        missing_reasons=(),
        conflict_reasons=(),
        source="TEST-SWING",
        schema_version=1,
    )


def _bar(index: int, close: str, *, volume: str | None = "10") -> CompletedBarInput:
    end_ns = (index + 1) * BAR_NS
    value = Decimal(close)
    return CompletedBarInput(
        instrument_id="ESU6.CME",
        bar_specification="5-MINUTE-LAST-EXTERNAL",
        calendar_id="cme_equity",
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        trade_date=date(2026, 8, 24),
        session_id="cme_equity:2026-08-24:OPEN",
        window_id="primary",
        interval_start_ns=end_ns - BAR_NS,
        interval_end_ns=end_ns,
        open=value,
        high=value + Decimal("1"),
        low=value - Decimal("1"),
        close=value,
        volume=None if volume is None else Decimal(volume),
        source=CompletedBarSource.LIVE_AGGREGATE,
        observed_ts_ns=end_ns,
        received_ts_ns=end_ns + 1,
        normalized_ts_ns=end_ns + 2,
        health=MetricHealth.READY,
        fidelity=MetricFidelity.REPORTED,
        evidence_refs=(f"bar:{index}",),
        complete=True,
        missing_reasons=() if volume is not None else ("volume_unsupported",),
    )


def _latest_structure(owner: MarketStructureRelationshipOwner) -> EntityRevision:
    revisions = owner.snapshot(100 * BAR_NS, entity_type="pivot_structure_state").revisions
    assert len(revisions) == 1
    return revisions[0]


def test_pivot_chain_policy_rejects_values_outside_optimization_envelopes() -> None:
    policy = _definitions().applications[0].policy

    with pytest.raises(ValueError, match="outside its configured envelope"):
        replace(policy, equality_tolerance=Decimal("10.25"))
    with pytest.raises(ValueError, match="does not align to its configured step"):
        replace(policy, minimum_leg_displacement=Decimal("0.10"))
    with pytest.raises(ValueError, match="leg_scale_ratio_tolerance_dynamic must be a boolean"):
        replace(policy, leg_scale_ratio_tolerance_dynamic="yes")


def test_alternating_pivots_publish_leg_with_complete_geometry_and_lineage() -> None:
    owner = _owner(_definitions())
    low = _swing(0, SwingKind.LOW, "100")
    high = _swing(3, SwingKind.HIGH, "112")
    for bar in (_bar(0, "100"), _bar(1, "104"), _bar(2, "108"), _bar(3, "112")):
        owner.ingest_bar(bar, now_ns=bar.normalized_ts_ns)
    owner.ingest_normalization(
        SwingNormalizationEvidence(
            metric_id="atr-normalization",
            metric_version=1,
            revision=1,
            instrument_id="ESU6.CME",
            analytical_profile_id="cme_equity_primary",
            analytical_profile_version=1,
            bar_specification="5-MINUTE-LAST-EXTERNAL",
            horizon="intraday_5m",
            effective_ts_ns=high.payload.pivot_ts_ns,
            value=Decimal("4"),
            health=MetricHealth.READY,
            fidelity=MetricFidelity.DERIVED,
            reference_id="atr:es:4",
        ),
        now_ns=high.published_ts_ns,
    )
    owner.ingest_swing(low, now_ns=low.published_ts_ns)
    owner.ingest_swing(high, now_ns=high.published_ts_ns)

    legs = owner.snapshot(100 * BAR_NS, entity_type="swing_leg").revisions
    assert len(legs) == 1
    payload = legs[0].payload
    assert isinstance(payload, SwingLegPayload)
    assert payload.price_change == Decimal("12")
    assert payload.percentage_change == Decimal("12")
    assert payload.elapsed_bars == 3
    assert payload.slope_per_bar == Decimal("4")
    assert payload.volatility_normalized_displacement == Decimal("3")
    assert payload.volatility_normalized_slope_per_bar == Decimal("1")
    assert payload.path_efficiency == Decimal("1")
    assert payload.path_volume == Decimal("40")
    assert payload.missing_context == ()
    assert {item.reference_id for item in legs[0].evidence_refs} == {
        low.entity_id,
        high.entity_id,
        "atr:es:4",
    }


def test_each_selected_same_kind_pivot_owns_explicit_comparison_to_previous() -> None:
    owner = _owner(_definitions(equality_tolerance="1"))
    swings = (
        _swing(0, SwingKind.LOW, "100"),
        _swing(1, SwingKind.HIGH, "110"),
        _swing(2, SwingKind.LOW, "101"),
        _swing(3, SwingKind.HIGH, "111"),
        _swing(4, SwingKind.LOW, "98"),
    )
    for swing in swings:
        owner.ingest_swing(swing, now_ns=swing.published_ts_ns)

    payload = _latest_structure(owner).payload
    assert isinstance(payload, PivotStructurePayload)
    assert len(payload.same_kind_comparisons) == 3
    high_comparison = next(
        item for item in payload.same_kind_comparisons if item.current.kind is SwingKind.HIGH
    )
    assert high_comparison.relationship is PivotRelationship.EQUAL
    assert high_comparison.price_change == Decimal("1")
    assert high_comparison.elapsed_bars == 2
    assert high_comparison.slope_per_bar == Decimal("0.5")
    latest_low = payload.same_kind_comparisons[-1]
    assert latest_low.relationship is PivotRelationship.LOWER
    assert latest_low.percentage_change == (Decimal("-3") / Decimal("101") * Decimal("100"))
    assert payload.geometry_state is PivotGeometryState.MIXED


def test_more_extreme_same_kind_terminal_revises_chain_without_deleting_swings() -> None:
    owner = _owner(_definitions())
    low = _swing(0, SwingKind.LOW, "100")
    first_high = _swing(1, SwingKind.HIGH, "110")
    higher_high = _swing(2, SwingKind.HIGH, "114")
    for swing in (low, first_high, higher_high):
        owner.ingest_swing(swing, now_ns=swing.published_ts_ns)

    payload = _latest_structure(owner).payload
    assert isinstance(payload, PivotStructurePayload)
    assert tuple(item.entity_id for item in payload.selected_pivots) == (
        low.entity_id,
        higher_high.entity_id,
    )
    assert payload.superseded_pivot_entity_ids == (first_high.entity_id,)
    comparison = payload.same_kind_comparisons[0]
    assert comparison.previous.entity_id == first_high.entity_id
    assert comparison.current.entity_id == higher_high.entity_id
    assert comparison.relationship is PivotRelationship.HIGHER
    assert owner.retained_swings == 3


def test_more_extreme_terminal_uses_explicit_tie_break_for_equal_prices() -> None:
    owner = _owner(_definitions())
    low = _swing(0, SwingKind.LOW, "100")
    first_high = _swing(1, SwingKind.HIGH, "110")
    equal_high = _swing(2, SwingKind.HIGH, "110")
    for swing in (low, first_high, equal_high):
        owner.ingest_swing(swing, now_ns=swing.published_ts_ns)

    payload = _latest_structure(owner).payload
    assert isinstance(payload, PivotStructurePayload)
    assert payload.selected_pivots[-1].entity_id == equal_high.entity_id
    assert payload.same_kind_comparisons[0].relationship is PivotRelationship.EQUAL


def test_late_path_and_normalization_evidence_revise_existing_leg_honestly() -> None:
    owner = _owner(_definitions())
    low = _swing(0, SwingKind.LOW, "100")
    high = _swing(3, SwingKind.HIGH, "112")
    owner.ingest_swing(low, now_ns=low.published_ts_ns)
    owner.ingest_swing(high, now_ns=high.published_ts_ns)

    initial = owner.snapshot(100 * BAR_NS, entity_type="swing_leg").revisions[0]
    initial_payload = initial.payload
    assert isinstance(initial_payload, SwingLegPayload)
    assert initial_payload.path_efficiency is None
    assert initial_payload.missing_context == (
        "path_bars_unavailable",
        "volatility_normalization_unavailable",
    )

    for bar in (_bar(0, "100"), _bar(1, "104"), _bar(2, "108"), _bar(3, "112")):
        owner.ingest_bar(bar, now_ns=10 * BAR_NS)
    owner.ingest_normalization(
        SwingNormalizationEvidence(
            metric_id="atr-normalization",
            metric_version=1,
            revision=1,
            instrument_id="ESU6.CME",
            analytical_profile_id="cme_equity_primary",
            analytical_profile_version=1,
            bar_specification="5-MINUTE-LAST-EXTERNAL",
            horizon="intraday_5m",
            effective_ts_ns=high.payload.pivot_ts_ns,
            value=Decimal("4"),
            health=MetricHealth.READY,
            fidelity=MetricFidelity.DERIVED,
            reference_id="atr:es:late",
        ),
        now_ns=10 * BAR_NS,
    )

    enriched = owner.snapshot(100 * BAR_NS, entity_type="swing_leg").revisions[0]
    enriched_payload = enriched.payload
    assert isinstance(enriched_payload, SwingLegPayload)
    assert enriched.revision > initial.revision
    assert enriched_payload.path_efficiency == Decimal("1")
    assert enriched_payload.volatility_normalized_displacement == Decimal("3")
    assert enriched_payload.missing_context == ()


def test_minimum_leg_displacement_is_explicit_structure_conflict() -> None:
    owner = _owner(_definitions(minimum_leg_displacement="5"))
    low = _swing(0, SwingKind.LOW, "100")
    high = _swing(1, SwingKind.HIGH, "103")
    owner.ingest_swing(low, now_ns=low.published_ts_ns)
    owner.ingest_swing(high, now_ns=high.published_ts_ns)

    assert owner.snapshot(100 * BAR_NS, entity_type="swing_leg").revisions == ()
    structure = _latest_structure(owner)
    payload = structure.payload
    assert isinstance(payload, PivotStructurePayload)
    assert payload.selected_legs == ()
    assert payload.relationship_conflicts == (
        f"minimum_leg_displacement:{low.entity_id}:{high.entity_id}",
    )


def test_unresolved_terminal_run_waits_for_opposite_then_resolves_deterministically() -> None:
    owner = _owner(_definitions(same_kind_policy=SameKindPivotPolicy.UNRESOLVED_UNTIL_OPPOSITE))
    low = _swing(0, SwingKind.LOW, "100")
    high_one = _swing(1, SwingKind.HIGH, "110")
    high_two = _swing(2, SwingKind.HIGH, "114")
    for swing in (low, high_one, high_two):
        owner.ingest_swing(swing, now_ns=swing.published_ts_ns)
    unresolved = _latest_structure(owner).payload
    assert isinstance(unresolved, PivotStructurePayload)
    assert unresolved.selected_pivots == (unresolved.selected_pivots[0],)
    assert unresolved.unresolved_pivot_entity_ids == tuple(
        sorted((high_one.entity_id, high_two.entity_id))
    )

    next_low = _swing(3, SwingKind.LOW, "102")
    owner.ingest_swing(next_low, now_ns=next_low.published_ts_ns)
    resolved = _latest_structure(owner).payload
    assert isinstance(resolved, PivotStructurePayload)
    assert tuple(item.entity_id for item in resolved.selected_pivots) == (
        low.entity_id,
        high_two.entity_id,
        next_low.entity_id,
    )
    assert resolved.unresolved_pivot_entity_ids == ()


def test_leg_scale_and_geometry_state_are_explicit_but_not_direction_scores() -> None:
    owner = _owner(_definitions())
    swings = (
        _swing(0, SwingKind.LOW, "100"),
        _swing(1, SwingKind.HIGH, "110"),
        _swing(2, SwingKind.LOW, "104"),
        _swing(3, SwingKind.HIGH, "118"),
        _swing(4, SwingKind.LOW, "108"),
    )
    for swing in swings:
        owner.ingest_swing(swing, now_ns=swing.published_ts_ns)

    payload = _latest_structure(owner).payload
    assert isinstance(payload, PivotStructurePayload)
    assert payload.geometry_state is PivotGeometryState.UPWARD
    assert payload.leg_scale_comparisons[-1].relationship is LegScaleRelationship.CONTRACTING
    assert payload.lower_bound == Decimal("100")
    assert payload.upper_bound == Decimal("118")


def test_late_arrival_converges_to_same_current_structure_payload() -> None:
    definition = _definitions()
    chronological = _owner(definition)
    late = _owner(definition)
    swings = (
        _swing(0, SwingKind.LOW, "100"),
        _swing(1, SwingKind.HIGH, "110"),
        _swing(2, SwingKind.LOW, "102"),
        _swing(3, SwingKind.HIGH, "116"),
    )
    for swing in swings:
        chronological.ingest_swing(swing, now_ns=10 * BAR_NS)
    for swing in (swings[3], swings[1], swings[0], swings[2]):
        late.ingest_swing(swing, now_ns=10 * BAR_NS)

    chronological_payload = _latest_structure(chronological).payload
    late_payload = _latest_structure(late).payload
    assert chronological_payload == late_payload


def test_detector_horizon_and_retention_are_isolated_and_bounded() -> None:
    definition = _definitions(
        detector_ids=("tactical", "structural"),
        horizons=("intraday_5m", "structural_5m"),
        maximum_retained_pivots=3,
        maximum_selected_pivots=3,
    )
    owner = _owner(definition)
    tactical = (
        _swing(0, SwingKind.LOW, "100"),
        _swing(1, SwingKind.HIGH, "110"),
        _swing(2, SwingKind.LOW, "102"),
        _swing(3, SwingKind.HIGH, "114"),
    )
    structural = (
        _swing(0, SwingKind.LOW, "98", detector_id="structural", horizon="structural_5m"),
        _swing(3, SwingKind.HIGH, "116", detector_id="structural", horizon="structural_5m"),
    )
    for swing in (*tactical, *structural):
        owner.ingest_swing(swing, now_ns=10 * BAR_NS)

    structures = owner.snapshot(100 * BAR_NS, entity_type="pivot_structure_state").revisions
    assert len(structures) == 2
    assert owner.retained_swings == 5
    by_detector = {
        item.payload.detector_id: item.payload
        for item in structures
        if isinstance(item.payload, PivotStructurePayload)
    }
    assert len(by_detector["tactical"].selected_pivots) == 3
    assert len(by_detector["structural"].selected_pivots) == 2
