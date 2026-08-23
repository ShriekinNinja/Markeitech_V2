from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from markeitech.intelligence.entities import (
    EntityDefinition,
    EntityDurability,
    EntityLifecycle,
    EntityMetricDependency,
    EntityStateBookLimits,
)
from markeitech.intelligence.market_state_entities import (
    DIRECTION_STATE_GROUP,
    VOLATILITY_STATE_GROUP,
    MarketStateApplication,
    MarketStateDefinition,
    MarketStatePolicyBinding,
    MarketStateProjectionOwner,
    payload_type_for_market_state,
)
from markeitech.intelligence.market_states import (
    CompressionExpansionStatePayload,
    DirectionalStatePayload,
    ReferenceStatePayload,
    StateCategoryBand,
    StateClassificationPolicy,
    VolatilityStatePayload,
)
from markeitech.intelligence.metrics import MetricFidelity, MetricHealth, MetricValue

SESSION_ID = "cme_equity:2026-08-23:OPEN"
HEALTH = (
    MetricHealth.READY,
    MetricHealth.WARMING,
    MetricHealth.DEGRADED,
    MetricHealth.STALE,
    MetricHealth.UNAVAILABLE,
)
FIDELITY = (MetricFidelity.DERIVED, MetricFidelity.PARTIAL)


def _policy(
    measure_id: str,
    *,
    definition_id: str = "primary-policy",
    confirmation: int = 1,
    maximum_age_ns: int = 10,
) -> StateClassificationPolicy:
    return StateClassificationPolicy(
        definition_id=definition_id,
        definition_version=1,
        parameter_version=1,
        parameter_source="TEST-CONFIG",
        parameter_effective_from_ns=1,
        measure_id=measure_id,
        unavailable_category="UNAVAILABLE",
        bands=(
            StateCategoryBand("LOW", None, Decimal("-0.25")),
            StateCategoryBand("BALANCED", Decimal("-0.25"), Decimal("0.25")),
            StateCategoryBand("HIGH", Decimal("0.25"), None),
        ),
        hysteresis=Decimal("0.05"),
        confirmation_observations=confirmation,
        minimum_coverage_ratio=Decimal("0.8"),
        maximum_evidence_age_ns=maximum_age_ns,
        permitted_health=HEALTH,
        permitted_fidelities=FIDELITY,
    )


def _spec(
    entity_type: str,
    roles: tuple[tuple[str, str, bool], ...],
    bindings: tuple[MarketStatePolicyBinding, ...],
    *,
    normalization: str | None = None,
    reference_id: str | None = None,
    reference_kind: str | None = None,
) -> MarketStateDefinition:
    dependencies = tuple(
        EntityMetricDependency(metric_id, 1, required, HEALTH, FIDELITY)
        for role, metric_id, required in roles
    )
    group = (
        VOLATILITY_STATE_GROUP
        if entity_type in {"volatility_state", "compression_expansion_state"}
        else DIRECTION_STATE_GROUP
    )
    return MarketStateDefinition(
        definition_id=f"{entity_type}-v1",
        group=group,
        definition=EntityDefinition(
            entity_type=entity_type,
            version=1,
            decision_question="What is the current market state?",
            implementation_id=f"test.{entity_type}",
            payload_type=payload_type_for_market_state(entity_type),
            identity_dimensions=("definition_id", "horizon", "parameter_set_id"),
            metric_inputs=dependencies,
            entity_inputs=(),
            permitted_health=HEALTH,
            permitted_fidelities=FIDELITY,
            durability=EntityDurability.TRANSIENT,
            completion_rule="never completes while active",
            invalidation_rule="dependency identity conflict",
            expiry_rule="configured maximum input age",
        ),
        metric_roles={
            dependency.key: role
            for (role, _, _), dependency in zip(roles, dependencies, strict=True)
        },
        parameter_set_id="baseline-v1",
        parameter_version=1,
        policy_bindings=bindings,
        applications=(
            MarketStateApplication(
                "cme-fast",
                ("cme_equity_primary",),
                (),
                ("OPEN",),
                "fast",
            ),
        ),
        normalization=normalization,
        reference_id=reference_id,
        reference_kind=reference_kind,
    )


def _volatility_spec(*, confirmation: int = 1) -> MarketStateDefinition:
    policy = _policy("rolling.fast.atr", confirmation=confirmation)
    return _spec(
        "volatility_state",
        (
            ("average_true_range", "rolling.fast.atr", True),
            ("realized_range", "rolling.fast.range", False),
            ("coverage_ratio", "rolling.fast.coverage", True),
        ),
        (MarketStatePolicyBinding("primary", "average_true_range", "coverage_ratio", policy),),
        normalization="points",
    )


def _directional_spec() -> MarketStateDefinition:
    policy = _policy("rolling.fast.signed_path_efficiency")
    return _spec(
        "directional_state",
        (
            ("signed_displacement", "rolling.fast.signed_displacement", False),
            ("signed_simple_return", "rolling.fast.signed_return", False),
            ("signed_path_efficiency", "rolling.fast.signed_path_efficiency", True),
            ("coverage_ratio", "rolling.fast.coverage", True),
        ),
        (
            MarketStatePolicyBinding(
                "primary",
                "signed_path_efficiency",
                "coverage_ratio",
                policy,
            ),
        ),
    )


def _reference_spec() -> MarketStateDefinition:
    return _spec(
        "reference_state.ema",
        (
            ("reference_value", "reference.ema.value", False),
            ("slope_per_bar", "reference.ema.slope", True),
            ("price_separation", "reference.ema.separation", True),
            ("coverage_ratio", "reference.ema.coverage", True),
        ),
        (
            MarketStatePolicyBinding(
                "slope",
                "slope_per_bar",
                "coverage_ratio",
                _policy("reference.ema.slope", definition_id="slope-policy"),
            ),
            MarketStatePolicyBinding(
                "separation",
                "price_separation",
                "coverage_ratio",
                _policy("reference.ema.separation", definition_id="separation-policy"),
            ),
        ),
        reference_id="ema-dynamic-10",
        reference_kind="EMA",
    )


def _compression_spec() -> MarketStateDefinition:
    return _spec(
        "compression_expansion_state",
        (
            ("expansion_ratio_recent", "rolling.fast.expansion", True),
            ("coverage_ratio", "rolling.fast.coverage", True),
            ("recent_reference_count", "rolling.fast.recent_count", True),
            ("phase_reference_count", "rolling.fast.phase_count", True),
            ("phase_duration_observations", "rolling.fast.phase_duration", True),
        ),
        (
            MarketStatePolicyBinding(
                "primary",
                "expansion_ratio_recent",
                "coverage_ratio",
                _policy("rolling.fast.expansion"),
            ),
        ),
    )


def _owner(
    *definitions: MarketStateDefinition,
    maximum_metric_values: int = 100,
    maximum_publications: int = 100,
) -> MarketStateProjectionOwner:
    return MarketStateProjectionOwner(
        definitions=definitions,
        instrument_profiles={"ESU6.CME": ("cme_equity_primary", 1)},
        limits=EntityStateBookLimits(100, 50, 20),
        maximum_metric_values=maximum_metric_values,
        maximum_publications_per_cycle=maximum_publications,
        source="TEST-MARKET-STATE",
        schema_version=1,
    )


def _metric(
    metric_id: str,
    value: object,
    *,
    revision: int = 1,
    parameter_version: int = 1,
    effective_ts_ns: int | None = None,
) -> MetricValue:
    timestamp = effective_ts_ns if effective_ts_ns is not None else 100 + revision
    return MetricValue(
        metric_id=metric_id,
        metric_version=1,
        parameter_version=parameter_version,
        instrument_id="ESU6.CME",
        session_id=SESSION_ID,
        value=value,
        unit="test",
        effective_ts_ns=timestamp,
        observed_ts_ns=timestamp,
        received_ts_ns=timestamp,
        calculated_ts_ns=timestamp,
        published_ts_ns=timestamp,
        health=MetricHealth.READY,
        fidelity=MetricFidelity.DERIVED,
        source="TEST-METRICS",
        evidence_refs=(f"source:{metric_id}:{revision}",),
        missing_reasons=(),
        revision=revision,
    )


def test_volatility_projection_is_role_order_independent_and_confirms() -> None:
    forward = _owner(_volatility_spec(confirmation=2))
    reverse = _owner(_volatility_spec(confirmation=2))
    first_measure = _metric("rolling.fast.atr", Decimal("0.5"))
    coverage = _metric("rolling.fast.coverage", Decimal("1"))

    forward.ingest(first_measure, now_ns=101)
    forward.ingest(coverage, now_ns=101)
    reverse.ingest(coverage, now_ns=101)
    reverse.ingest(first_measure, now_ns=101)

    forward_payload = forward.snapshot(102).revisions[0].payload
    reverse_payload = reverse.snapshot(102).revisions[0].payload
    assert isinstance(forward_payload, VolatilityStatePayload)
    assert forward_payload == reverse_payload
    assert forward.snapshot(102).revisions[0].lifecycle is EntityLifecycle.WARMING

    revision = forward.ingest(
        _metric("rolling.fast.atr", Decimal("0.6"), revision=2),
        now_ns=102,
    )[-1]
    assert revision.lifecycle is EntityLifecycle.ACTIVE
    assert isinstance(revision.payload, VolatilityStatePayload)
    assert revision.payload.classification.category == "HIGH"
    assert revision.payload.classification.confirmed is True


def test_duplicate_conflict_stale_and_parameter_mismatch_are_contained() -> None:
    owner = _owner(_volatility_spec())
    measure = _metric("rolling.fast.atr", Decimal("0.5"))
    owner.ingest(measure, now_ns=101)

    assert owner.ingest(measure, now_ns=101) == ()
    assert owner.ingest(replace(measure, value=Decimal("0.75")), now_ns=101) == ()
    assert owner.ingest(
        replace(
            measure,
            revision=2,
            effective_ts_ns=100,
            observed_ts_ns=100,
            received_ts_ns=100,
            calculated_ts_ns=100,
            published_ts_ns=100,
        ),
        now_ns=102,
    ) == ()
    assert owner.ingest(
        _metric("rolling.fast.coverage", Decimal("1"), parameter_version=2),
        now_ns=101,
    ) == ()

    assert owner.counts.metrics_duplicate == 1
    assert owner.counts.metrics_conflict == 1
    assert owner.counts.metrics_stale == 1
    assert owner.retained_metric_values == 1


def test_reconcile_publishes_stale_revision_without_new_metric() -> None:
    owner = _owner(_volatility_spec())
    owner.ingest(_metric("rolling.fast.atr", Decimal("0.5")), now_ns=101)
    active = owner.ingest(_metric("rolling.fast.coverage", Decimal("1")), now_ns=101)[-1]
    assert active.lifecycle is EntityLifecycle.ACTIVE

    stale = owner.reconcile(now_ns=112)

    assert len(stale) == 1
    assert stale[0].lifecycle is EntityLifecycle.STALE
    assert isinstance(stale[0].payload, VolatilityStatePayload)
    assert stale[0].payload.classification.category == "UNAVAILABLE"
    assert stale[0].payload.classification.missing_reasons == ("evidence_stale",)
    assert owner.reconcile(now_ns=113) == ()
    assert owner.counts.staleness_reconciliations == 1


def test_directional_state_remains_exactly_horizon_scoped_and_queryable() -> None:
    owner = _owner(_directional_spec())
    values = (
        _metric("rolling.fast.signed_displacement", Decimal("12")),
        _metric("rolling.fast.signed_return", Decimal("0.01")),
        _metric("rolling.fast.signed_path_efficiency", Decimal("0.7")),
        _metric("rolling.fast.coverage", Decimal("1")),
    )
    for value in values:
        owner.ingest(value, now_ns=101)

    snapshot = owner.snapshot(
        200,
        instrument_id="ESU6.CME",
        entity_type="directional_state",
        dimensions={"horizon": "fast"},
        lifecycles=(EntityLifecycle.ACTIVE,),
    )

    assert len(snapshot.revisions) == 1
    payload = snapshot.revisions[0].payload
    assert isinstance(payload, DirectionalStatePayload)
    assert payload.signed_displacement == Decimal("12")
    assert payload.signed_path_efficiency == Decimal("0.7")
    assert payload.classification.category == "HIGH"


def test_reference_axes_classify_independently() -> None:
    owner = _owner(_reference_spec())
    values = (
        _metric("reference.ema.value", Decimal("6500")),
        _metric("reference.ema.slope", Decimal("0.4")),
        _metric("reference.ema.separation", Decimal("-0.6")),
        _metric("reference.ema.coverage", Decimal("1")),
    )
    for value in values:
        owner.ingest(value, now_ns=101)

    revision = owner.snapshot(200).revisions[0]
    payload = revision.payload
    assert isinstance(payload, ReferenceStatePayload)
    assert payload.slope_classification.category == "HIGH"
    assert payload.separation_classification.category == "LOW"
    assert payload.reference_id == "ema-dynamic-10"
    assert revision.lifecycle is EntityLifecycle.ACTIVE


def test_compression_payload_retains_baseline_counts() -> None:
    owner = _owner(_compression_spec())
    values = (
        _metric("rolling.fast.expansion", Decimal("0.5")),
        _metric("rolling.fast.coverage", Decimal("0.9")),
        _metric("rolling.fast.recent_count", 20),
        _metric("rolling.fast.phase_count", 12),
        _metric("rolling.fast.phase_duration", 8),
    )
    for value in values:
        owner.ingest(value, now_ns=101)

    payload = owner.snapshot(200).revisions[0].payload
    assert isinstance(payload, CompressionExpansionStatePayload)
    assert payload.expansion_ratio_recent == Decimal("0.5")
    assert payload.recent_reference_count == 20
    assert payload.phase_reference_count == 12
    assert payload.phase_duration_observations == 8


def test_publication_overflow_is_deferred_and_metric_retention_is_bounded() -> None:
    owner = _owner(
        _volatility_spec(),
        _directional_spec(),
        maximum_metric_values=3,
        maximum_publications=1,
    )
    owner.ingest(_metric("rolling.fast.atr", Decimal("0.5")), now_ns=101)
    first = owner.ingest(_metric("rolling.fast.coverage", Decimal("1")), now_ns=101)
    second = owner.ingest(
        _metric("rolling.fast.signed_path_efficiency", Decimal("0.5")),
        now_ns=101,
    )
    third = owner.ingest(_metric("unrelated.metric", Decimal("1")), now_ns=101)

    assert len(first) == len(second) == len(third) == 1
    assert first[0].entity_id != second[0].entity_id
    assert second[0].entity_id == third[0].entity_id
    assert owner.pending_publications == 0
    assert owner.counts.publications_deferred >= 1
    assert owner.retained_metric_values == 3


def test_trend_rotation_waits_for_cross_entity_reconciliation() -> None:
    with pytest.raises(ValueError, match="cross-entity reconciliation"):
        payload_type_for_market_state("trend_rotation_state")
