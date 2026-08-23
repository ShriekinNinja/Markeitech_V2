from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from markeitech.intelligence.market_states import (
    ScalarStateEvidence,
    StateCategoryBand,
    StateClassificationMemory,
    StateClassificationPolicy,
    classify_state,
    project_compression_expansion_state,
    project_directional_state,
    project_reference_state,
    project_trend_rotation_state,
    project_volatility_state,
)
from markeitech.intelligence.metrics import MetricFidelity, MetricHealth


def _policy(**changes: object) -> StateClassificationPolicy:
    values = {
        "definition_id": "test-state-v1",
        "definition_version": 1,
        "parameter_version": 3,
        "parameter_source": "operator-reviewed-config",
        "parameter_effective_from_ns": 1,
        "measure_id": "rolling.fast.context_1m.expansion_ratio_recent",
        "unavailable_category": "UNAVAILABLE",
        "bands": (
            StateCategoryBand("LOW", None, Decimal("0.8")),
            StateCategoryBand("BALANCED", Decimal("0.8"), Decimal("1.2")),
            StateCategoryBand("HIGH", Decimal("1.2"), None),
        ),
        "hysteresis": Decimal("0.1"),
        "confirmation_observations": 2,
        "minimum_coverage_ratio": Decimal("0.8"),
        "maximum_evidence_age_ns": 100,
        "permitted_health": (MetricHealth.READY, MetricHealth.DEGRADED),
        "permitted_fidelities": (MetricFidelity.DERIVED, MetricFidelity.PARTIAL),
    }
    values.update(changes)
    return StateClassificationPolicy(**values)  # type: ignore[arg-type]


def _evidence(
    value: str | None,
    *,
    timestamp: int,
    coverage: str = "1",
    health: MetricHealth = MetricHealth.READY,
    fidelity: MetricFidelity = MetricFidelity.DERIVED,
) -> ScalarStateEvidence:
    return ScalarStateEvidence(
        value=None if value is None else Decimal(value),
        coverage_ratio=Decimal(coverage),
        effective_ts_ns=timestamp,
        health=health,
        fidelity=fidelity,
        evidence_refs=(f"metric:{timestamp}",),
        missing_reasons=("source_unavailable",) if value is None else (),
    )


def test_policy_requires_complete_non_overlapping_configuration_owned_bands() -> None:
    assert tuple(item.category for item in _policy().bands) == ("LOW", "BALANCED", "HIGH")

    with pytest.raises(ValueError, match="contiguous"):
        _policy(
            bands=(
                StateCategoryBand("LOW", None, Decimal("0.7")),
                StateCategoryBand("HIGH", Decimal("0.8"), None),
            ),
        )
    with pytest.raises(ValueError, match="unavailable_category"):
        _policy(unavailable_category="LOW")
    with pytest.raises(ValueError, match="between zero and one"):
        _policy(minimum_coverage_ratio=Decimal("1.1"))


def test_exact_boundaries_and_initial_confirmation_are_deterministic() -> None:
    policy = _policy(hysteresis=Decimal(0))

    first, memory = classify_state(_evidence("0.8", timestamp=10), policy, None, now_ns=10)
    assert first.observed_category == "BALANCED"
    assert first.category == "UNAVAILABLE"
    assert first.candidate_observations == 1
    assert first.confirmed is False

    second, memory = classify_state(_evidence("0.8", timestamp=11), policy, memory, now_ns=11)
    assert second.category == "BALANCED"
    assert second.changed is True
    assert second.confirmed is True
    assert memory.category_since_ts_ns == 11

    upper, _ = classify_state(
        _evidence("1.2", timestamp=12),
        replace(policy, confirmation_observations=1),
        None,
        now_ns=12,
    )
    assert upper.category == "HIGH"


def test_hysteresis_and_consecutive_confirmation_prevent_boundary_churn() -> None:
    policy = _policy()
    _, memory = classify_state(_evidence("1", timestamp=10), policy, None, now_ns=10)
    current, memory = classify_state(_evidence("1", timestamp=11), policy, memory, now_ns=11)
    assert current.category == "BALANCED"

    inside_hysteresis, memory = classify_state(
        _evidence("1.25", timestamp=12),
        policy,
        memory,
        now_ns=12,
    )
    assert inside_hysteresis.observed_category == "HIGH"
    assert inside_hysteresis.category == "BALANCED"
    assert inside_hysteresis.candidate_category is None

    candidate, memory = classify_state(
        _evidence("1.3", timestamp=13),
        policy,
        memory,
        now_ns=13,
    )
    assert candidate.category == "BALANCED"
    assert candidate.candidate_category == "HIGH"
    assert candidate.candidate_observations == 1

    interrupted, memory = classify_state(
        _evidence("1", timestamp=14),
        policy,
        memory,
        now_ns=14,
    )
    assert interrupted.category == "BALANCED"
    assert interrupted.candidate_category is None

    _, memory = classify_state(_evidence("1.3", timestamp=15), policy, memory, now_ns=15)
    changed, memory = classify_state(
        _evidence("1.31", timestamp=16),
        policy,
        memory,
        now_ns=16,
    )
    assert changed.category == "HIGH"
    assert changed.changed is True
    assert memory.candidate_category is None


def test_parameter_revision_rewarms_instead_of_reusing_old_confirmation() -> None:
    first_policy = _policy(confirmation_observations=1)
    first, memory = classify_state(
        _evidence("1", timestamp=10),
        first_policy,
        None,
        now_ns=10,
    )
    assert first.category == "BALANCED"
    assert first.parameter_version == 3

    revised_policy = replace(first_policy, parameter_version=4, confirmation_observations=2)
    revised, memory = classify_state(
        _evidence("1", timestamp=11),
        revised_policy,
        memory,
        now_ns=11,
    )

    assert revised.category == "UNAVAILABLE"
    assert revised.candidate_observations == 1
    assert revised.parameter_version == 4
    assert memory.policy_identity == revised_policy.identity


def test_evidence_envelope_staleness_and_late_values_are_explicit() -> None:
    policy = _policy(confirmation_observations=1)
    ready, memory = classify_state(_evidence("1", timestamp=10), policy, None, now_ns=10)
    assert ready.category == "BALANCED"

    late, unchanged = classify_state(_evidence("2", timestamp=9), policy, memory, now_ns=11)
    assert late.accepted is False
    assert late.category == "BALANCED"
    assert late.missing_reasons == ("non_monotonic_evidence_ignored",)
    assert unchanged == memory

    stale, reset = classify_state(_evidence("1", timestamp=20), policy, memory, now_ns=121)
    assert stale.category == "UNAVAILABLE"
    assert stale.health is MetricHealth.STALE
    assert stale.missing_reasons == ("evidence_stale",)
    assert reset == StateClassificationMemory()

    insufficient, _ = classify_state(
        _evidence("1", timestamp=200, coverage="0.79"),
        policy,
        None,
        now_ns=200,
    )
    assert insufficient.category == "UNAVAILABLE"
    assert insufficient.health is MetricHealth.WARMING
    assert insufficient.missing_reasons == ("minimum_coverage_not_met",)

    unsupported, _ = classify_state(
        _evidence(
            "1",
            timestamp=201,
            fidelity=MetricFidelity.INFERRED,
        ),
        policy,
        None,
        now_ns=201,
    )
    assert unsupported.missing_reasons == ("fidelity_not_permitted:INFERRED",)


def test_family_payloads_retain_exact_numerical_inputs_and_horizon_identity() -> None:
    policy = _policy(confirmation_observations=1)
    evidence = _evidence("1.4", timestamp=10)

    volatility, _ = project_volatility_state(
        horizon="fast:context_1m",
        average_true_range=Decimal("2.5"),
        realized_range=Decimal("8"),
        realized_return_magnitude=Decimal("0.01"),
        normalization="recent_equal_duration_ratio",
        evidence=evidence,
        policy=policy,
        prior=None,
        now_ns=10,
    )
    assert volatility.classification.category == "HIGH"
    assert volatility.average_true_range == Decimal("2.5")

    compression, _ = project_compression_expansion_state(
        horizon="intraday:context_5m",
        expansion_ratio_recent=Decimal("1.4"),
        expansion_ratio_phase=Decimal("1.1"),
        range_percentile_recent=Decimal("0.9"),
        range_percentile_phase=Decimal("0.7"),
        recent_reference_count=8,
        phase_reference_count=4,
        phase_duration_observations=3,
        evidence=evidence,
        policy=policy,
        prior=None,
        now_ns=10,
    )
    assert compression.horizon == "intraday:context_5m"
    assert compression.phase_reference_count == 4

    direction, _ = project_directional_state(
        horizon="structural:context_15m",
        signed_displacement=Decimal("-12"),
        signed_simple_return=Decimal("-0.002"),
        signed_path_efficiency=Decimal("-0.7"),
        evidence=replace(evidence, value=Decimal("-0.7")),
        policy=policy,
        prior=None,
        now_ns=10,
    )
    assert direction.signed_path_efficiency == Decimal("-0.7")
    assert direction.horizon == "structural:context_15m"


def test_reference_axes_and_cross_horizon_conflicts_remain_separate() -> None:
    direction_policy = _policy(
        confirmation_observations=1,
        bands=(
            StateCategoryBand("DOWN", None, Decimal("-0.2")),
            StateCategoryBand("NEUTRAL", Decimal("-0.2"), Decimal("0.2")),
            StateCategoryBand("UP", Decimal("0.2"), None),
        ),
    )
    trend, _ = project_trend_rotation_state(
        horizon="fast:context_1m",
        signed_path_efficiency=Decimal("0.6"),
        directional_category="UP",
        compression_expansion_category="EXPANDING",
        reference_slope=Decimal("-0.5"),
        reference_separation=Decimal("2"),
        conflicting_horizons=("intraday:context_5m",),
        conflict_reasons=("fast_up_intraday_down",),
        evidence=replace(_evidence("0.6", timestamp=20), evidence_refs=("metric:trend",)),
        policy=direction_policy,
        prior=None,
        now_ns=20,
    )
    assert trend.classification.category == "UP"
    assert trend.conflicting_horizons == ("intraday:context_5m",)
    assert trend.conflict_reasons == ("fast_up_intraday_down",)

    reference, _, _ = project_reference_state(
        horizon="fast:context_1m",
        reference_id="ema-dynamic-10",
        reference_kind="EMA",
        value=Decimal("100"),
        slope_per_bar=Decimal("-0.5"),
        price_separation=Decimal("2"),
        slope_evidence=_evidence("-0.5", timestamp=20),
        separation_evidence=_evidence("2", timestamp=20),
        slope_policy=direction_policy,
        separation_policy=direction_policy,
        prior_slope=None,
        prior_separation=None,
        now_ns=20,
    )
    assert reference.slope_classification.category == "DOWN"
    assert reference.separation_classification.category == "UP"
    assert reference.value == Decimal("100")
