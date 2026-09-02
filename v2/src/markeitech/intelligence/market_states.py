from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from markeitech.intelligence.entities import EntityPayload
from markeitech.intelligence.metrics import MetricFidelity, MetricHealth


@dataclass(frozen=True, slots=True)
class StateCategoryBand:
    """Define one contiguous, lower-inclusive scalar classification band."""

    category: str
    lower_bound: Decimal | None
    upper_bound: Decimal | None

    def __post_init__(self) -> None:
        _required_text(self.category, "category")
        if self.lower_bound is not None and not isinstance(self.lower_bound, Decimal):
            raise ValueError("lower_bound must be Decimal or None")
        if self.upper_bound is not None and not isinstance(self.upper_bound, Decimal):
            raise ValueError("upper_bound must be Decimal or None")
        if (
            self.lower_bound is not None
            and self.upper_bound is not None
            and self.lower_bound >= self.upper_bound
        ):
            raise ValueError("category lower_bound must be below upper_bound")


@dataclass(frozen=True, slots=True)
class StateClassificationPolicy:
    """Configure bounded categories, hysteresis, confirmation, and evidence gates."""

    definition_id: str
    definition_version: int
    parameter_version: int
    parameter_source: str
    parameter_effective_from_ns: int
    measure_id: str
    unavailable_category: str
    bands: tuple[StateCategoryBand, ...]
    hysteresis: Decimal
    confirmation_observations: int
    minimum_coverage_ratio: Decimal
    maximum_evidence_age_ns: int
    permitted_health: tuple[MetricHealth, ...]
    permitted_fidelities: tuple[MetricFidelity, ...]

    def __post_init__(self) -> None:
        for field in (
            "definition_id",
            "parameter_source",
            "measure_id",
            "unavailable_category",
        ):
            _required_text(getattr(self, field), field)
        _positive_int(self.definition_version, "definition_version")
        _positive_int(self.parameter_version, "parameter_version")
        _non_negative_int(self.parameter_effective_from_ns, "parameter_effective_from_ns")
        _positive_int(self.confirmation_observations, "confirmation_observations")
        _positive_int(self.maximum_evidence_age_ns, "maximum_evidence_age_ns")
        if not isinstance(self.hysteresis, Decimal) or self.hysteresis < 0:
            raise ValueError("hysteresis must be a non-negative Decimal")
        if not isinstance(self.minimum_coverage_ratio, Decimal) or not (
            Decimal(0) <= self.minimum_coverage_ratio <= Decimal(1)
        ):
            raise ValueError("minimum_coverage_ratio must be a Decimal between zero and one")
        _typed_tuple(self.bands, StateCategoryBand, "bands")
        if len(self.bands) < 2:
            raise ValueError("classification policy requires at least two category bands")
        categories = tuple(item.category for item in self.bands)
        if len(categories) != len(set(categories)):
            raise ValueError("category band names must be unique")
        if self.unavailable_category in categories:
            raise ValueError("unavailable_category must not also be a classified category")
        if self.bands[0].lower_bound is not None:
            raise ValueError("the first category band must be unbounded below")
        if self.bands[-1].upper_bound is not None:
            raise ValueError("the last category band must be unbounded above")
        for previous, current in zip(self.bands, self.bands[1:], strict=False):
            if previous.upper_bound != current.lower_bound:
                raise ValueError("category bands must be ordered, contiguous, and non-overlapping")
        _enum_tuple(self.permitted_health, MetricHealth, "permitted_health")
        _enum_tuple(self.permitted_fidelities, MetricFidelity, "permitted_fidelities")

    @property
    def identity(self) -> tuple[str, int, int]:
        return (self.definition_id, self.definition_version, self.parameter_version)


@dataclass(frozen=True, slots=True)
class ScalarStateEvidence:
    """Carry one scalar observation and its coverage, timing, and evidence quality."""

    value: Decimal | None
    coverage_ratio: Decimal
    effective_ts_ns: int
    health: MetricHealth
    fidelity: MetricFidelity
    evidence_refs: tuple[str, ...]
    missing_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.value is not None and not isinstance(self.value, Decimal):
            raise ValueError("state evidence value must be Decimal or None")
        if not isinstance(self.coverage_ratio, Decimal) or not (
            Decimal(0) <= self.coverage_ratio <= Decimal(1)
        ):
            raise ValueError("coverage_ratio must be a Decimal between zero and one")
        _non_negative_int(self.effective_ts_ns, "effective_ts_ns")
        if not isinstance(self.health, MetricHealth):
            raise ValueError("health must be MetricHealth")
        if not isinstance(self.fidelity, MetricFidelity):
            raise ValueError("fidelity must be MetricFidelity")
        _text_tuple(self.evidence_refs, "evidence_refs")
        _text_tuple(self.missing_reasons, "missing_reasons")
        if self.value is None and not self.missing_reasons:
            raise ValueError("missing state evidence requires a missing reason")


@dataclass(frozen=True, slots=True)
class StateClassificationMemory:
    """Retain immutable hysteresis and confirmation state between observations."""

    policy_identity: tuple[str, int, int] | None = None
    current_category: str | None = None
    candidate_category: str | None = None
    candidate_observations: int = 0
    category_since_ts_ns: int | None = None
    last_evidence_ts_ns: int | None = None

    def __post_init__(self) -> None:
        if self.policy_identity is not None:
            if (
                not isinstance(self.policy_identity, tuple)
                or len(self.policy_identity) != 3
                or not isinstance(self.policy_identity[0], str)
            ):
                raise ValueError(
                    "policy_identity must be (definition_id, version, parameter_version)",
                )
            _required_text(self.policy_identity[0], "policy_identity definition_id")
            _positive_int(self.policy_identity[1], "policy_identity definition_version")
            _positive_int(self.policy_identity[2], "policy_identity parameter_version")
        if self.current_category is not None:
            _required_text(self.current_category, "current_category")
        if self.candidate_category is not None:
            _required_text(self.candidate_category, "candidate_category")
        _non_negative_int(self.candidate_observations, "candidate_observations")
        if (self.candidate_category is None) != (self.candidate_observations == 0):
            raise ValueError("candidate category and observations must be present together")
        if self.category_since_ts_ns is not None:
            _non_negative_int(self.category_since_ts_ns, "category_since_ts_ns")
        if self.last_evidence_ts_ns is not None:
            _non_negative_int(self.last_evidence_ts_ns, "last_evidence_ts_ns")
        if self.current_category is None and self.category_since_ts_ns is not None:
            raise ValueError("category_since_ts_ns requires a current category")
        if (
            self.policy_identity is None
            and (
                self.current_category is not None
                or self.candidate_category is not None
                or self.last_evidence_ts_ns is not None
            )
        ):
            raise ValueError("classification memory with evidence requires policy_identity")


@dataclass(frozen=True, slots=True)
class StateClassification:
    """Explain one accepted, pending, unchanged, or unavailable classification."""

    definition_id: str
    definition_version: int
    parameter_version: int
    parameter_source: str
    parameter_effective_from_ns: int
    category: str
    observed_category: str | None
    candidate_category: str | None
    candidate_observations: int
    confirmation_observations: int
    confirmed: bool
    changed: bool
    accepted: bool
    category_since_ts_ns: int | None
    measure_id: str
    measure_value: Decimal | None
    coverage_ratio: Decimal
    effective_ts_ns: int
    health: MetricHealth
    fidelity: MetricFidelity
    evidence_refs: tuple[str, ...]
    missing_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VolatilityStatePayload(EntityPayload):
    """Carry volatility measures and their bounded categorical classification."""

    horizon: str
    average_true_range: Decimal | None
    realized_range: Decimal | None
    realized_return_magnitude: Decimal | None
    normalized_value: Decimal | None
    normalization: str
    baseline_coverage_ratio: Decimal
    classification: StateClassification


@dataclass(frozen=True, slots=True)
class CompressionExpansionStatePayload(EntityPayload):
    """Carry recent and phase-matched expansion evidence and classification."""

    horizon: str
    expansion_ratio_recent: Decimal | None
    expansion_ratio_phase: Decimal | None
    range_percentile_recent: Decimal | None
    range_percentile_phase: Decimal | None
    recent_reference_count: int
    phase_reference_count: int
    baseline_coverage_ratio: Decimal
    phase_duration_observations: int
    classification: StateClassification


@dataclass(frozen=True, slots=True)
class DirectionalStatePayload(EntityPayload):
    """Carry signed price geometry and its bounded directional classification."""

    horizon: str
    signed_displacement: Decimal | None
    signed_simple_return: Decimal | None
    signed_path_efficiency: Decimal | None
    coverage_ratio: Decimal
    classification: StateClassification


@dataclass(frozen=True, slots=True)
class TrendRotationStatePayload(EntityPayload):
    """Carry composed trend-rotation evidence, conflicts, and classification."""

    horizon: str
    signed_path_efficiency: Decimal | None
    directional_category: str
    compression_expansion_category: str
    reference_slope: Decimal | None
    reference_separation: Decimal | None
    conflicting_horizons: tuple[str, ...]
    conflict_reasons: tuple[str, ...]
    classification: StateClassification


@dataclass(frozen=True, slots=True)
class ReferenceStatePayload(EntityPayload):
    """Carry reference value, slope, separation, and their classifications."""

    horizon: str
    reference_id: str
    reference_kind: str
    value: Decimal | None
    slope_per_bar: Decimal | None
    price_separation: Decimal | None
    slope_classification: StateClassification
    separation_classification: StateClassification


def classify_state(
    evidence: ScalarStateEvidence,
    policy: StateClassificationPolicy,
    prior: StateClassificationMemory | None,
    *,
    now_ns: int,
) -> tuple[StateClassification, StateClassificationMemory]:
    """Classify scalar evidence with policy-owned quality, age, and hysteresis gates.

    Non-monotonic evidence is ignored; invalid, stale, low-coverage, or otherwise
    inadmissible evidence yields an explicit unavailable classification.
    """

    if not isinstance(evidence, ScalarStateEvidence):
        raise ValueError("evidence must be ScalarStateEvidence")
    if not isinstance(policy, StateClassificationPolicy):
        raise ValueError("policy must be StateClassificationPolicy")
    if prior is not None and not isinstance(prior, StateClassificationMemory):
        raise ValueError("prior must be StateClassificationMemory or None")
    _non_negative_int(now_ns, "now_ns")
    memory = prior or StateClassificationMemory()
    if memory.policy_identity not in {None, policy.identity}:
        memory = StateClassificationMemory()

    invalid_reasons, invalid_health = _evidence_rejection(evidence, policy, memory, now_ns)
    if invalid_reasons:
        if invalid_reasons == ("non_monotonic_evidence_ignored",):
            return (
                _classification(
                    policy=policy,
                    evidence=evidence,
                    memory=memory,
                    category=memory.current_category or policy.unavailable_category,
                    observed_category=None,
                    accepted=False,
                    health=invalid_health,
                    missing_reasons=invalid_reasons,
                ),
                memory,
            )
        reset = StateClassificationMemory()
        return (
            _classification(
                policy=policy,
                evidence=evidence,
                memory=reset,
                category=policy.unavailable_category,
                observed_category=None,
                accepted=False,
                health=invalid_health,
                missing_reasons=invalid_reasons,
            ),
            reset,
        )

    assert evidence.value is not None
    observed = _category_for(evidence.value, policy)
    if memory.current_category is None:
        candidate, count = _candidate(memory, observed)
        if count >= policy.confirmation_observations:
            next_memory = StateClassificationMemory(
                policy_identity=policy.identity,
                current_category=observed,
                category_since_ts_ns=evidence.effective_ts_ns,
                last_evidence_ts_ns=evidence.effective_ts_ns,
            )
            return (
                _classification(
                    policy=policy,
                    evidence=evidence,
                    memory=next_memory,
                    category=observed,
                    observed_category=observed,
                    accepted=True,
                    changed=True,
                ),
                next_memory,
            )
        next_memory = StateClassificationMemory(
            policy_identity=policy.identity,
            candidate_category=candidate,
            candidate_observations=count,
            last_evidence_ts_ns=evidence.effective_ts_ns,
        )
        return (
            _classification(
                policy=policy,
                evidence=evidence,
                memory=next_memory,
                category=policy.unavailable_category,
                observed_category=observed,
                accepted=True,
            ),
            next_memory,
        )

    if observed == memory.current_category or not _crossed_hysteresis(
        evidence.value,
        memory.current_category,
        observed,
        policy,
    ):
        next_memory = StateClassificationMemory(
            policy_identity=policy.identity,
            current_category=memory.current_category,
            category_since_ts_ns=memory.category_since_ts_ns,
            last_evidence_ts_ns=evidence.effective_ts_ns,
        )
        return (
            _classification(
                policy=policy,
                evidence=evidence,
                memory=next_memory,
                category=memory.current_category,
                observed_category=observed,
                accepted=True,
            ),
            next_memory,
        )

    candidate, count = _candidate(memory, observed)
    if count < policy.confirmation_observations:
        next_memory = StateClassificationMemory(
            policy_identity=policy.identity,
            current_category=memory.current_category,
            candidate_category=candidate,
            candidate_observations=count,
            category_since_ts_ns=memory.category_since_ts_ns,
            last_evidence_ts_ns=evidence.effective_ts_ns,
        )
        return (
            _classification(
                policy=policy,
                evidence=evidence,
                memory=next_memory,
                category=memory.current_category,
                observed_category=observed,
                accepted=True,
            ),
            next_memory,
        )

    next_memory = StateClassificationMemory(
        policy_identity=policy.identity,
        current_category=observed,
        category_since_ts_ns=evidence.effective_ts_ns,
        last_evidence_ts_ns=evidence.effective_ts_ns,
    )
    return (
        _classification(
            policy=policy,
            evidence=evidence,
            memory=next_memory,
            category=observed,
            observed_category=observed,
            accepted=True,
            changed=True,
        ),
        next_memory,
    )


def project_volatility_state(
    *,
    horizon: str,
    average_true_range: Decimal | None,
    realized_range: Decimal | None,
    realized_return_magnitude: Decimal | None,
    normalization: str,
    evidence: ScalarStateEvidence,
    policy: StateClassificationPolicy,
    prior: StateClassificationMemory | None,
    now_ns: int,
) -> tuple[VolatilityStatePayload, StateClassificationMemory]:
    """Project volatility measures and scalar classification into a payload."""

    classification, memory = classify_state(evidence, policy, prior, now_ns=now_ns)
    return (
        VolatilityStatePayload(
            horizon=_required_text(horizon, "horizon"),
            average_true_range=average_true_range,
            realized_range=realized_range,
            realized_return_magnitude=realized_return_magnitude,
            normalized_value=evidence.value,
            normalization=_required_text(normalization, "normalization"),
            baseline_coverage_ratio=evidence.coverage_ratio,
            classification=classification,
        ),
        memory,
    )


def project_compression_expansion_state(
    *,
    horizon: str,
    expansion_ratio_recent: Decimal | None,
    expansion_ratio_phase: Decimal | None,
    range_percentile_recent: Decimal | None,
    range_percentile_phase: Decimal | None,
    recent_reference_count: int,
    phase_reference_count: int,
    phase_duration_observations: int,
    evidence: ScalarStateEvidence,
    policy: StateClassificationPolicy,
    prior: StateClassificationMemory | None,
    now_ns: int,
) -> tuple[CompressionExpansionStatePayload, StateClassificationMemory]:
    """Project expansion evidence and scalar classification into a payload."""

    for field, value in (
        ("recent_reference_count", recent_reference_count),
        ("phase_reference_count", phase_reference_count),
        ("phase_duration_observations", phase_duration_observations),
    ):
        _non_negative_int(value, field)
    classification, memory = classify_state(evidence, policy, prior, now_ns=now_ns)
    return (
        CompressionExpansionStatePayload(
            horizon=_required_text(horizon, "horizon"),
            expansion_ratio_recent=expansion_ratio_recent,
            expansion_ratio_phase=expansion_ratio_phase,
            range_percentile_recent=range_percentile_recent,
            range_percentile_phase=range_percentile_phase,
            recent_reference_count=recent_reference_count,
            phase_reference_count=phase_reference_count,
            baseline_coverage_ratio=evidence.coverage_ratio,
            phase_duration_observations=phase_duration_observations,
            classification=classification,
        ),
        memory,
    )


def project_directional_state(
    *,
    horizon: str,
    signed_displacement: Decimal | None,
    signed_simple_return: Decimal | None,
    signed_path_efficiency: Decimal | None,
    evidence: ScalarStateEvidence,
    policy: StateClassificationPolicy,
    prior: StateClassificationMemory | None,
    now_ns: int,
) -> tuple[DirectionalStatePayload, StateClassificationMemory]:
    """Project signed directional evidence and classification into a payload."""

    classification, memory = classify_state(evidence, policy, prior, now_ns=now_ns)
    return (
        DirectionalStatePayload(
            horizon=_required_text(horizon, "horizon"),
            signed_displacement=signed_displacement,
            signed_simple_return=signed_simple_return,
            signed_path_efficiency=signed_path_efficiency,
            coverage_ratio=evidence.coverage_ratio,
            classification=classification,
        ),
        memory,
    )


def project_trend_rotation_state(
    *,
    horizon: str,
    signed_path_efficiency: Decimal | None,
    directional_category: str,
    compression_expansion_category: str,
    reference_slope: Decimal | None,
    reference_separation: Decimal | None,
    conflicting_horizons: tuple[str, ...],
    conflict_reasons: tuple[str, ...],
    evidence: ScalarStateEvidence,
    policy: StateClassificationPolicy,
    prior: StateClassificationMemory | None,
    now_ns: int,
) -> tuple[TrendRotationStatePayload, StateClassificationMemory]:
    """Project composed directional, expansion, reference, and conflict evidence."""

    classification, memory = classify_state(evidence, policy, prior, now_ns=now_ns)
    return (
        TrendRotationStatePayload(
            horizon=_required_text(horizon, "horizon"),
            signed_path_efficiency=signed_path_efficiency,
            directional_category=_required_text(directional_category, "directional_category"),
            compression_expansion_category=_required_text(
                compression_expansion_category,
                "compression_expansion_category",
            ),
            reference_slope=reference_slope,
            reference_separation=reference_separation,
            conflicting_horizons=_text_tuple(conflicting_horizons, "conflicting_horizons"),
            conflict_reasons=_text_tuple(conflict_reasons, "conflict_reasons"),
            classification=classification,
        ),
        memory,
    )


def project_reference_state(
    *,
    horizon: str,
    reference_id: str,
    reference_kind: str,
    value: Decimal | None,
    slope_per_bar: Decimal | None,
    price_separation: Decimal | None,
    slope_evidence: ScalarStateEvidence,
    separation_evidence: ScalarStateEvidence,
    slope_policy: StateClassificationPolicy,
    separation_policy: StateClassificationPolicy,
    prior_slope: StateClassificationMemory | None,
    prior_separation: StateClassificationMemory | None,
    now_ns: int,
) -> tuple[ReferenceStatePayload, StateClassificationMemory, StateClassificationMemory]:
    """Project reference value, slope, and separation classifications into a payload."""

    slope, slope_memory = classify_state(
        slope_evidence,
        slope_policy,
        prior_slope,
        now_ns=now_ns,
    )
    separation, separation_memory = classify_state(
        separation_evidence,
        separation_policy,
        prior_separation,
        now_ns=now_ns,
    )
    return (
        ReferenceStatePayload(
            horizon=_required_text(horizon, "horizon"),
            reference_id=_required_text(reference_id, "reference_id"),
            reference_kind=_required_text(reference_kind, "reference_kind"),
            value=value,
            slope_per_bar=slope_per_bar,
            price_separation=price_separation,
            slope_classification=slope,
            separation_classification=separation,
        ),
        slope_memory,
        separation_memory,
    )


def _evidence_rejection(
    evidence: ScalarStateEvidence,
    policy: StateClassificationPolicy,
    memory: StateClassificationMemory,
    now_ns: int,
) -> tuple[tuple[str, ...], MetricHealth]:
    if now_ns < evidence.effective_ts_ns:
        return ("evidence_timestamp_is_in_the_future",), MetricHealth.UNAVAILABLE
    if (
        memory.last_evidence_ts_ns is not None
        and evidence.effective_ts_ns <= memory.last_evidence_ts_ns
    ):
        return ("non_monotonic_evidence_ignored",), MetricHealth.STALE
    if now_ns - evidence.effective_ts_ns > policy.maximum_evidence_age_ns:
        return ("evidence_stale",), MetricHealth.STALE
    if evidence.health not in policy.permitted_health:
        return (f"health_not_permitted:{evidence.health.value}",), evidence.health
    if evidence.fidelity not in policy.permitted_fidelities:
        return (f"fidelity_not_permitted:{evidence.fidelity.value}",), MetricHealth.DEGRADED
    if evidence.coverage_ratio < policy.minimum_coverage_ratio:
        return ("minimum_coverage_not_met",), MetricHealth.WARMING
    if evidence.value is None:
        return evidence.missing_reasons, evidence.health
    return (), evidence.health


def _category_for(value: Decimal, policy: StateClassificationPolicy) -> str:
    for band in policy.bands:
        if (band.lower_bound is None or value >= band.lower_bound) and (
            band.upper_bound is None or value < band.upper_bound
        ):
            return band.category
    raise RuntimeError("validated category bands did not contain the evidence value")


def _crossed_hysteresis(
    value: Decimal,
    current_category: str,
    observed_category: str,
    policy: StateClassificationPolicy,
) -> bool:
    categories = tuple(item.category for item in policy.bands)
    try:
        current_index = categories.index(current_category)
        observed_index = categories.index(observed_category)
    except ValueError:
        return True
    current = policy.bands[current_index]
    if observed_index > current_index:
        assert current.upper_bound is not None
        return value >= current.upper_bound + policy.hysteresis
    assert current.lower_bound is not None
    return value <= current.lower_bound - policy.hysteresis


def _candidate(memory: StateClassificationMemory, observed: str) -> tuple[str, int]:
    if memory.candidate_category == observed:
        return observed, memory.candidate_observations + 1
    return observed, 1


def _classification(
    *,
    policy: StateClassificationPolicy,
    evidence: ScalarStateEvidence,
    memory: StateClassificationMemory,
    category: str,
    observed_category: str | None,
    accepted: bool,
    changed: bool = False,
    health: MetricHealth | None = None,
    missing_reasons: tuple[str, ...] = (),
) -> StateClassification:
    return StateClassification(
        definition_id=policy.definition_id,
        definition_version=policy.definition_version,
        parameter_version=policy.parameter_version,
        parameter_source=policy.parameter_source,
        parameter_effective_from_ns=policy.parameter_effective_from_ns,
        category=category,
        observed_category=observed_category,
        candidate_category=memory.candidate_category,
        candidate_observations=memory.candidate_observations,
        confirmation_observations=policy.confirmation_observations,
        confirmed=memory.current_category is not None,
        changed=changed,
        accepted=accepted,
        category_since_ts_ns=memory.category_since_ts_ns,
        measure_id=policy.measure_id,
        measure_value=evidence.value,
        coverage_ratio=evidence.coverage_ratio,
        effective_ts_ns=evidence.effective_ts_ns,
        health=health or evidence.health,
        fidelity=evidence.fidelity,
        evidence_refs=evidence.evidence_refs,
        missing_reasons=missing_reasons,
    )


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _positive_int(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _non_negative_int(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _typed_tuple(values: object, expected_type: type[object], field: str) -> None:
    if not isinstance(values, tuple) or not all(isinstance(item, expected_type) for item in values):
        raise ValueError(f"{field} must be a tuple of {expected_type.__name__}")


def _enum_tuple(values: object, expected_type: type[object], field: str) -> None:
    _typed_tuple(values, expected_type, field)
    assert isinstance(values, tuple)
    if not values:
        raise ValueError(f"{field} must not be empty")
    if len(values) != len(set(values)):
        raise ValueError(f"{field} must not contain duplicates")


def _text_tuple(values: object, field: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ValueError(f"{field} must be a tuple")
    normalized = tuple(_required_text(item, field) for item in values)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field} must not contain duplicates")
    return normalized
