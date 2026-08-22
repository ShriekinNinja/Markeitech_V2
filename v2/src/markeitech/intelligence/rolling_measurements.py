from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from decimal import Decimal
from math import isfinite, log, sqrt
from statistics import median

from markeitech.intelligence.completed_bars import CompletedBarInput, CompletedBarSource
from markeitech.intelligence.metrics import (
    MetricCadence,
    MetricDefinition,
    MetricDependency,
    MetricFailureBehavior,
    MetricFidelity,
    MetricHealth,
    MetricParameterDefinition,
    MetricRegistry,
    MetricResourcePolicy,
    MetricRetainedState,
    MetricValue,
    MetricValueKind,
    MetricWarmupPolicy,
    ParameterMutability,
)
from markeitech.intelligence.session import SessionWindow
from markeitech.intelligence.session_measurements import (
    COMPLETED_BAR_CLOSE_METRIC_ID,
    COMPLETED_BAR_HIGH_METRIC_ID,
    COMPLETED_BAR_LOW_METRIC_ID,
    COMPLETED_BAR_TRUE_RANGE_METRIC_ID,
)

_NS_PER_SECOND = 1_000_000_000

ROLLING_METRIC_SUFFIXES = (
    "price_range",
    "realized_log_return_magnitude",
    "average_true_range",
    "directional_efficiency",
    "coverage_ratio",
    "expansion_ratio_recent",
    "range_percentile_recent",
    "recent_reference_count",
    "expansion_ratio_phase",
    "range_percentile_phase",
    "phase_reference_count",
)


@dataclass(frozen=True, slots=True)
class RollingCandidatePolicy:
    candidate_id: str
    purpose: str
    duration_seconds: int
    minimum_duration_seconds: int
    maximum_duration_seconds: int
    duration_step_seconds: int
    dynamic: bool
    active: bool

    def __post_init__(self) -> None:
        _required_text(self.candidate_id, "candidate_id")
        if self.purpose not in {"context", "expansion"}:
            raise ValueError("candidate purpose must be context or expansion")
        for field in (
            "duration_seconds",
            "minimum_duration_seconds",
            "maximum_duration_seconds",
            "duration_step_seconds",
        ):
            _positive_int(getattr(self, field), field)
        if (
            not self.minimum_duration_seconds
            <= self.duration_seconds
            <= self.maximum_duration_seconds
        ):
            raise ValueError("candidate duration is outside its configured envelope")
        if (self.duration_seconds - self.minimum_duration_seconds) % self.duration_step_seconds:
            raise ValueError("candidate duration does not align to its configured step")
        if not isinstance(self.dynamic, bool) or not isinstance(self.active, bool):
            raise ValueError("candidate dynamic and active flags must be booleans")


@dataclass(frozen=True, slots=True)
class RollingFamilyPolicy:
    family_id: str
    source_selector: str
    input_selector: str
    input_interval_seconds: int
    aggregation_policy: str
    selected_context_candidate_id: str
    candidates: tuple[RollingCandidatePolicy, ...]

    def __post_init__(self) -> None:
        for field in (
            "family_id",
            "source_selector",
            "input_selector",
            "selected_context_candidate_id",
        ):
            _required_text(getattr(self, field), field)
        _positive_int(self.input_interval_seconds, "input_interval_seconds")
        if self.aggregation_policy not in {"identity", "utc_fixed_intraday"}:
            raise ValueError("aggregation_policy must be identity or utc_fixed_intraday")
        if not isinstance(self.candidates, tuple) or not self.candidates:
            raise ValueError("rolling family candidates must be a non-empty tuple")
        candidate_ids = tuple(item.candidate_id for item in self.candidates)
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("rolling candidate IDs must be unique within a family")
        selected = next(
            (
                item
                for item in self.candidates
                if item.candidate_id == self.selected_context_candidate_id
            ),
            None,
        )
        if selected is None or selected.purpose != "context" or not selected.active:
            raise ValueError("selected context candidate must identify an active context candidate")
        for candidate in self.candidates:
            if candidate.duration_seconds % self.input_interval_seconds:
                raise ValueError("candidate duration must contain whole input intervals")


@dataclass(frozen=True, slots=True)
class RollingBaselinePolicy:
    eligible_reference_health: tuple[MetricHealth, ...]
    eligible_reference_fidelities: tuple[MetricFidelity, ...]
    recent_reference_count: int
    recent_reference_count_minimum: int
    recent_reference_count_maximum: int
    recent_reference_count_step: int
    recent_reference_count_dynamic: bool
    minimum_recent_references: int
    phase_reference_count: int
    phase_reference_count_minimum: int
    phase_reference_count_maximum: int
    phase_reference_count_step: int
    phase_reference_count_dynamic: bool
    minimum_phase_references: int

    def __post_init__(self) -> None:
        if not self.eligible_reference_health or any(
            not isinstance(item, MetricHealth) for item in self.eligible_reference_health
        ):
            raise ValueError("eligible_reference_health must contain MetricHealth values")
        if not self.eligible_reference_fidelities or any(
            not isinstance(item, MetricFidelity) for item in self.eligible_reference_fidelities
        ):
            raise ValueError(
                "eligible_reference_fidelities must contain MetricFidelity values"
            )
        if len(set(self.eligible_reference_health)) != len(self.eligible_reference_health):
            raise ValueError("eligible_reference_health values must be unique")
        if len(set(self.eligible_reference_fidelities)) != len(
            self.eligible_reference_fidelities
        ):
            raise ValueError("eligible_reference_fidelities values must be unique")
        for field in (
            "recent_reference_count",
            "recent_reference_count_minimum",
            "recent_reference_count_maximum",
            "recent_reference_count_step",
            "minimum_recent_references",
            "phase_reference_count",
            "phase_reference_count_minimum",
            "phase_reference_count_maximum",
            "phase_reference_count_step",
            "minimum_phase_references",
        ):
            _positive_int(getattr(self, field), field)
        _validate_envelope(
            self.recent_reference_count,
            self.recent_reference_count_minimum,
            self.recent_reference_count_maximum,
            self.recent_reference_count_step,
            "recent reference count",
        )
        _validate_envelope(
            self.phase_reference_count,
            self.phase_reference_count_minimum,
            self.phase_reference_count_maximum,
            self.phase_reference_count_step,
            "phase reference count",
        )
        if self.minimum_recent_references > self.recent_reference_count:
            raise ValueError("minimum recent references cannot exceed the requested count")
        if self.minimum_phase_references > self.phase_reference_count:
            raise ValueError("minimum phase references cannot exceed the requested count")
        if not isinstance(self.recent_reference_count_dynamic, bool):
            raise ValueError("recent_reference_count_dynamic must be a boolean")
        if not isinstance(self.phase_reference_count_dynamic, bool):
            raise ValueError("phase_reference_count_dynamic must be a boolean")


@dataclass(frozen=True, slots=True)
class RollingMeasurementPolicy:
    enabled: bool
    minimum_coverage_ratio: float
    minimum_coverage_ratio_floor: float
    minimum_coverage_ratio_ceiling: float
    minimum_coverage_ratio_step: float
    minimum_coverage_ratio_dynamic: bool
    maximum_retained_observations: int
    maximum_output_age_ms: int
    baseline: RollingBaselinePolicy
    families: tuple[RollingFamilyPolicy, ...]
    parameter_source: str
    priority: int

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be a boolean")
        _ratio(self.minimum_coverage_ratio, "minimum_coverage_ratio")
        _ratio(self.minimum_coverage_ratio_floor, "minimum_coverage_ratio_floor")
        _ratio(self.minimum_coverage_ratio_ceiling, "minimum_coverage_ratio_ceiling")
        if self.minimum_coverage_ratio_step <= 0:
            raise ValueError("minimum_coverage_ratio_step must be positive")
        if not (
            self.minimum_coverage_ratio_floor
            <= self.minimum_coverage_ratio
            <= self.minimum_coverage_ratio_ceiling
        ):
            raise ValueError("minimum coverage ratio is outside its configured envelope")
        if not isinstance(self.minimum_coverage_ratio_dynamic, bool):
            raise ValueError("minimum_coverage_ratio_dynamic must be a boolean")
        _positive_int(self.maximum_retained_observations, "maximum_retained_observations")
        _positive_int(self.maximum_output_age_ms, "maximum_output_age_ms")
        if not isinstance(self.baseline, RollingBaselinePolicy):
            raise ValueError("baseline must be a RollingBaselinePolicy")
        if not isinstance(self.families, tuple) or not self.families:
            raise ValueError("rolling families must be a non-empty tuple")
        family_ids = tuple(item.family_id for item in self.families)
        if len(family_ids) != len(set(family_ids)):
            raise ValueError("rolling family IDs must be unique")
        _required_text(self.parameter_source, "parameter_source")
        if not isinstance(self.priority, int) or isinstance(self.priority, bool):
            raise ValueError("priority must be an integer")
        if not 0 <= self.priority <= 100:
            raise ValueError("priority must be between 0 and 100")


@dataclass(frozen=True, slots=True)
class RollingCandidateResult:
    instrument_id: str
    input_source: CompletedBarSource
    family_id: str
    candidate_id: str
    purpose: str
    input_interval_seconds: int
    duration_seconds: int
    session_id: str
    effective_ts_ns: int
    observed_ts_ns: int
    received_ts_ns: int
    price_range: Decimal | None
    realized_log_return_magnitude: Decimal | None
    average_true_range: Decimal | None
    directional_efficiency: Decimal | None
    coverage_ratio: Decimal
    expansion_ratio_recent: Decimal | None
    range_percentile_recent: Decimal | None
    recent_reference_count: int
    expansion_ratio_phase: Decimal | None
    range_percentile_phase: Decimal | None
    phase_reference_count: int
    current_health: MetricHealth
    recent_health: MetricHealth
    phase_health: MetricHealth
    fidelity: MetricFidelity
    evidence_refs: tuple[str, ...]
    current_missing_reasons: tuple[str, ...]
    recent_missing_reasons: tuple[str, ...]
    phase_missing_reasons: tuple[str, ...]


def rolling_metric_id(family_id: str, candidate_id: str, suffix: str) -> str:
    if suffix not in ROLLING_METRIC_SUFFIXES:
        raise ValueError(f"unsupported rolling metric suffix: {suffix}")
    return f"rolling.{family_id}.{candidate_id}.{suffix}"


def rolling_metric_definitions(policy: RollingMeasurementPolicy) -> tuple[MetricDefinition, ...]:
    if not isinstance(policy, RollingMeasurementPolicy):
        raise ValueError("policy must be a RollingMeasurementPolicy")
    definitions: list[MetricDefinition] = []
    for family in policy.families:
        for candidate in family.candidates:
            if not candidate.active:
                continue
            parameters = _parameter_definitions(policy, family, candidate)
            for suffix in ROLLING_METRIC_SUFFIXES:
                definitions.append(
                    _metric_definition(policy, family, candidate, suffix, parameters),
                )
    return tuple(definitions)


def calculate_rolling_candidates(
    bars: tuple[CompletedBarInput, ...],
    *,
    phase_windows: tuple[SessionWindow, ...],
    policy: RollingMeasurementPolicy,
) -> tuple[RollingCandidateResult, ...]:
    if not isinstance(bars, tuple) or any(not isinstance(item, CompletedBarInput) for item in bars):
        raise ValueError("bars must be a tuple of CompletedBarInput values")
    if not isinstance(phase_windows, tuple) or any(
        not isinstance(item, SessionWindow) for item in phase_windows
    ):
        raise ValueError("phase_windows must be a tuple of SessionWindow values")
    if not isinstance(policy, RollingMeasurementPolicy):
        raise ValueError("policy must be a RollingMeasurementPolicy")
    if not bars or not policy.enabled:
        return ()
    ordered = tuple(sorted(bars, key=lambda item: (item.interval_start_ns, item.interval_end_ns)))
    results: list[RollingCandidateResult] = []
    for family in policy.families:
        family_bars = _family_bars(ordered, family)
        if not family_bars:
            continue
        series = _BarSeries(
            bars=family_bars,
            starts=tuple(item.interval_start_ns for item in family_bars),
            ends=tuple(item.interval_end_ns for item in family_bars),
        )
        for candidate in family.candidates:
            if candidate.active:
                results.append(
                    _calculate_candidate(series, phase_windows, policy, family, candidate),
                )
    return tuple(results)


def rolling_metric_values(
    result: RollingCandidateResult,
    *,
    registry: MetricRegistry,
    parameter_version: int,
    calculated_ts_ns: int,
    published_ts_ns: int,
    source: str,
    revision: int,
) -> tuple[MetricValue, ...]:
    values: list[MetricValue] = []
    fields = {
        "price_range": (result.price_range, result.current_health, result.current_missing_reasons),
        "realized_log_return_magnitude": (
            result.realized_log_return_magnitude,
            result.current_health,
            result.current_missing_reasons,
        ),
        "average_true_range": (
            result.average_true_range,
            result.current_health,
            result.current_missing_reasons,
        ),
        "directional_efficiency": (
            result.directional_efficiency,
            result.current_health,
            (
                result.current_missing_reasons
                if result.directional_efficiency is not None
                else (*result.current_missing_reasons, "zero_directional_path")
            ),
        ),
        "coverage_ratio": (
            result.coverage_ratio,
            result.current_health,
            result.current_missing_reasons,
        ),
        "expansion_ratio_recent": (
            result.expansion_ratio_recent,
            result.recent_health,
            result.recent_missing_reasons,
        ),
        "range_percentile_recent": (
            result.range_percentile_recent,
            result.recent_health,
            result.recent_missing_reasons,
        ),
        "recent_reference_count": (
            result.recent_reference_count,
            result.recent_health,
            result.recent_missing_reasons,
        ),
        "expansion_ratio_phase": (
            result.expansion_ratio_phase,
            result.phase_health,
            result.phase_missing_reasons,
        ),
        "range_percentile_phase": (
            result.range_percentile_phase,
            result.phase_health,
            result.phase_missing_reasons,
        ),
        "phase_reference_count": (
            result.phase_reference_count,
            result.phase_health,
            result.phase_missing_reasons,
        ),
    }
    for suffix in ROLLING_METRIC_SUFFIXES:
        definition = registry.get(
            rolling_metric_id(result.family_id, result.candidate_id, suffix), 1
        )
        value, health, missing_reasons = fields[suffix]
        metric = MetricValue(
            metric_id=definition.metric_id,
            metric_version=definition.version,
            parameter_version=parameter_version,
            instrument_id=result.instrument_id,
            session_id=result.session_id,
            value=value,
            unit=definition.unit,
            effective_ts_ns=result.effective_ts_ns,
            observed_ts_ns=result.observed_ts_ns,
            received_ts_ns=result.received_ts_ns,
            calculated_ts_ns=calculated_ts_ns,
            published_ts_ns=published_ts_ns,
            health=health,
            fidelity=(result.fidelity if value is not None else MetricFidelity.UNAVAILABLE),
            source=source,
            evidence_refs=result.evidence_refs,
            missing_reasons=tuple(dict.fromkeys(missing_reasons)),
            revision=revision,
        )
        registry.validate_value(metric)
        values.append(metric)
    return tuple(values)


def _calculate_candidate(
    series: _BarSeries,
    phase_windows: tuple[SessionWindow, ...],
    policy: RollingMeasurementPolicy,
    family: RollingFamilyPolicy,
    candidate: RollingCandidatePolicy,
) -> RollingCandidateResult:
    bars = series.bars
    latest = bars[-1]
    end_ns = latest.interval_end_ns
    duration_ns = candidate.duration_seconds * _NS_PER_SECOND
    current = _window_observation(series, end_ns - duration_ns, end_ns, duration_ns)
    recent_observations: list[_WindowObservation] = []
    cursor = end_ns - duration_ns
    for _ in range(policy.baseline.recent_reference_count):
        observation = _window_observation(series, cursor - duration_ns, cursor, duration_ns)
        if _eligible_reference(observation, policy):
            recent_observations.append(observation)
        cursor -= duration_ns

    current_phase = next(
        (item for item in phase_windows if item.start_ns <= end_ns - 1 < item.end_ns),
        None,
    )
    phase_observations: list[_WindowObservation] = []
    phase_reason: tuple[str, ...] = ()
    if current_phase is None:
        phase_reason = ("authoritative_phase_window_missing",)
    else:
        offset_ns = end_ns - current_phase.start_ns
        prior = tuple(
            item
            for item in phase_windows
            if item.phase == current_phase.phase
            and item.trade_date < current_phase.trade_date
            and item.start_ns + offset_ns <= item.end_ns
        )
        for session in sorted(prior, key=lambda item: item.trade_date, reverse=True):
            reference_end = session.start_ns + offset_ns
            observation = _window_observation(
                series,
                reference_end - duration_ns,
                reference_end,
                duration_ns,
            )
            if _eligible_reference(observation, policy):
                phase_observations.append(observation)
            if len(phase_observations) >= policy.baseline.phase_reference_count:
                break

    current_ready = current.coverage_ratio >= Decimal(str(policy.minimum_coverage_ratio))
    current_health = _least_healthy(tuple(item.health for item in current.bars))
    if not current_ready:
        current_health = _least_healthy((current_health, MetricHealth.WARMING))
    current_missing = () if current_ready else ("current_window_coverage_insufficient",)
    recent_ranges = tuple(item.price_range for item in recent_observations)
    phase_ranges = tuple(item.price_range for item in phase_observations)
    recent_ratio, recent_percentile, recent_health, recent_missing = _baseline_values(
        current.price_range if current_ready else None,
        recent_ranges,
        policy.baseline.minimum_recent_references,
        "recent",
    )
    phase_ratio, phase_percentile, phase_health, phase_missing = _baseline_values(
        current.price_range if current_ready else None,
        phase_ranges,
        policy.baseline.minimum_phase_references,
        "phase",
    )
    if recent_health is MetricHealth.READY:
        recent_health = current_health
    if phase_health is MetricHealth.READY:
        phase_health = current_health
    phase_missing = tuple(dict.fromkeys((*phase_reason, *phase_missing)))
    fidelity = (
        MetricFidelity.DERIVED
        if current_ready and current_health is MetricHealth.READY
        else MetricFidelity.PARTIAL
    )
    current_sessions = tuple(dict.fromkeys(item.session_id for item in current.bars))
    evidence_refs = tuple(
        dict.fromkeys(
            (
                f"instrument:{latest.instrument_id}",
                (
                    f"rolling-window:{family.family_id}:{candidate.candidate_id}:"
                    f"{end_ns - duration_ns}:{end_ns}"
                ),
                f"rolling-input:{family.input_selector}:{family.input_interval_seconds}s",
                *(f"rolling-session:{session_id}" for session_id in current_sessions),
                f"rolling-boundary-crossing:{str(len(current_sessions) > 1).lower()}",
                *(
                    f"rolling-reference:recent:{item.bars[0].interval_start_ns}:"
                    f"{item.bars[-1].interval_end_ns}"
                    for item in recent_observations
                ),
                *(
                    f"rolling-reference:phase:{item.bars[0].session_id}:"
                    f"{item.bars[0].interval_start_ns}:{item.bars[-1].interval_end_ns}"
                    for item in phase_observations
                ),
                *(reference for item in current.bars for reference in item.evidence_refs),
                *(
                    reference
                    for observation in (*recent_observations, *phase_observations)
                    for item in observation.bars
                    for reference in item.evidence_refs
                ),
            ),
        ),
    )
    return RollingCandidateResult(
        instrument_id=latest.instrument_id,
        input_source=latest.source,
        family_id=family.family_id,
        candidate_id=candidate.candidate_id,
        purpose=candidate.purpose,
        input_interval_seconds=family.input_interval_seconds,
        duration_seconds=candidate.duration_seconds,
        session_id=latest.session_id,
        effective_ts_ns=end_ns,
        observed_ts_ns=max(
            (item.observed_ts_ns for item in current.bars), default=latest.observed_ts_ns
        ),
        received_ts_ns=max(
            (item.received_ts_ns for item in current.bars), default=latest.received_ts_ns
        ),
        price_range=current.price_range if current_ready else None,
        realized_log_return_magnitude=(
            _realized_log_return_magnitude(current.bars) if current_ready else None
        ),
        average_true_range=_average_true_range(current.bars) if current_ready else None,
        directional_efficiency=_directional_efficiency(current.bars) if current_ready else None,
        coverage_ratio=current.coverage_ratio,
        expansion_ratio_recent=recent_ratio,
        range_percentile_recent=recent_percentile,
        recent_reference_count=len(recent_observations),
        expansion_ratio_phase=phase_ratio,
        range_percentile_phase=phase_percentile,
        phase_reference_count=len(phase_observations),
        current_health=current_health,
        recent_health=recent_health,
        phase_health=phase_health,
        fidelity=fidelity,
        evidence_refs=evidence_refs,
        current_missing_reasons=current_missing,
        recent_missing_reasons=recent_missing,
        phase_missing_reasons=phase_missing,
    )


@dataclass(frozen=True, slots=True)
class _BarSeries:
    bars: tuple[CompletedBarInput, ...]
    starts: tuple[int, ...]
    ends: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class _WindowObservation:
    bars: tuple[CompletedBarInput, ...]
    coverage_ratio: Decimal
    price_range: Decimal


def _eligible_reference(
    observation: _WindowObservation,
    policy: RollingMeasurementPolicy,
) -> bool:
    return (
        observation.coverage_ratio >= Decimal(str(policy.minimum_coverage_ratio))
        and bool(observation.bars)
        and all(
            item.health in policy.baseline.eligible_reference_health
            and item.fidelity in policy.baseline.eligible_reference_fidelities
            for item in observation.bars
        )
    )


def _window_observation(
    series: _BarSeries,
    start_ns: int,
    end_ns: int,
    duration_ns: int,
) -> _WindowObservation:
    left = bisect_left(series.starts, start_ns)
    right = bisect_right(series.ends, end_ns)
    selected = series.bars[left:right]
    covered_ns = sum(item.interval_ns for item in selected)
    coverage = min(Decimal(1), Decimal(covered_ns) / Decimal(duration_ns))
    price_range = max((item.high for item in selected), default=Decimal(0)) - min(
        (item.low for item in selected),
        default=Decimal(0),
    )
    return _WindowObservation(selected, coverage, price_range)


def _family_bars(
    source: tuple[CompletedBarInput, ...],
    family: RollingFamilyPolicy,
) -> tuple[CompletedBarInput, ...]:
    source_interval_ns = source[-1].interval_ns
    target_interval_ns = family.input_interval_seconds * _NS_PER_SECOND
    if target_interval_ns < source_interval_ns:
        raise ValueError("rolling input interval cannot be smaller than its source interval")
    if target_interval_ns == source_interval_ns:
        return source
    if family.aggregation_policy != "utc_fixed_intraday":
        raise ValueError("a wider rolling input interval requires utc_fixed_intraday aggregation")
    buckets: dict[int, list[CompletedBarInput]] = {}
    for bar in source:
        bucket_start = bar.interval_start_ns - bar.interval_start_ns % target_interval_ns
        buckets.setdefault(bucket_start, []).append(bar)
    aggregated: list[CompletedBarInput] = []
    expected = target_interval_ns // source_interval_ns
    for bucket_start, values in sorted(buckets.items()):
        ordered = tuple(sorted(values, key=lambda item: item.interval_start_ns))
        bucket_end = bucket_start + target_interval_ns
        if (
            len(ordered) != expected
            or ordered[0].interval_start_ns != bucket_start
            or ordered[-1].interval_end_ns != bucket_end
            or any(
                previous.interval_end_ns != current.interval_start_ns
                for previous, current in zip(ordered, ordered[1:], strict=False)
            )
            or len({item.session_id for item in ordered}) != 1
        ):
            continue
        volumes = tuple(item.volume for item in ordered)
        volume = sum(volumes, Decimal(0)) if all(item is not None for item in volumes) else None
        missing = tuple(
            dict.fromkeys(reason for item in ordered for reason in item.missing_reasons)
        )
        if volume is None and not any(reason.startswith("volume_") for reason in missing):
            missing = (*missing, "volume_partial")
        first, last = ordered[0], ordered[-1]
        sources = {item.source for item in ordered}
        aggregate_source = (
            CompletedBarSource.HISTORICAL_AGGREGATE
            if sources
            <= {
                CompletedBarSource.HISTORICAL_PROVIDER,
                CompletedBarSource.HISTORICAL_AGGREGATE,
            }
            else CompletedBarSource.LIVE_AGGREGATE
        )
        aggregated.append(
            CompletedBarInput(
                instrument_id=first.instrument_id,
                bar_specification=family.input_selector,
                calendar_id=first.calendar_id,
                analytical_profile_id=first.analytical_profile_id,
                analytical_profile_version=first.analytical_profile_version,
                trade_date=first.trade_date,
                session_id=first.session_id,
                window_id=first.window_id,
                interval_start_ns=bucket_start,
                interval_end_ns=bucket_end,
                open=first.open,
                high=max(item.high for item in ordered),
                low=min(item.low for item in ordered),
                close=last.close,
                volume=volume,
                source=aggregate_source,
                observed_ts_ns=max(item.observed_ts_ns for item in ordered),
                received_ts_ns=max(item.received_ts_ns for item in ordered),
                normalized_ts_ns=max(item.normalized_ts_ns for item in ordered),
                health=_least_healthy(tuple(item.health for item in ordered)),
                fidelity=MetricFidelity.DERIVED,
                evidence_refs=tuple(
                    dict.fromkeys(
                        reference for item in ordered for reference in item.evidence_refs
                    ),
                ),
                complete=True,
                missing_reasons=missing,
            ),
        )
    return tuple(aggregated)


def _baseline_values(
    current: Decimal | None,
    references: tuple[Decimal, ...],
    minimum_references: int,
    identity: str,
) -> tuple[Decimal | None, Decimal | None, MetricHealth, tuple[str, ...]]:
    if current is None:
        return None, None, MetricHealth.WARMING, ("current_window_unavailable",)
    if len(references) < minimum_references:
        return (
            None,
            None,
            MetricHealth.WARMING,
            (f"{identity}_reference_count_insufficient",),
        )
    baseline = median(references)
    percentile = _midrank(current, references)
    if baseline == 0:
        return None, percentile, MetricHealth.UNAVAILABLE, (f"{identity}_baseline_median_zero",)
    return current / baseline, percentile, MetricHealth.READY, ()


def _midrank(current: Decimal, references: tuple[Decimal, ...]) -> Decimal:
    below = sum(item < current for item in references)
    equal = sum(item == current for item in references)
    return (Decimal(below) + Decimal(equal) / Decimal(2)) / Decimal(len(references))


def _realized_log_return_magnitude(bars: tuple[CompletedBarInput, ...]) -> Decimal | None:
    if len(bars) < 2:
        return None
    squared = sum(
        log(float(current.close / previous.close)) ** 2
        for previous, current in zip(bars, bars[1:], strict=False)
    )
    result = sqrt(squared)
    return Decimal(str(result)) if isfinite(result) else None


def _average_true_range(bars: tuple[CompletedBarInput, ...]) -> Decimal | None:
    if not bars:
        return None
    values = [bars[0].high - bars[0].low]
    values.extend(
        max(
            current.high - current.low,
            abs(current.high - previous.close),
            abs(current.low - previous.close),
        )
        for previous, current in zip(bars, bars[1:], strict=False)
    )
    return sum(values, Decimal(0)) / Decimal(len(values))


def _directional_efficiency(bars: tuple[CompletedBarInput, ...]) -> Decimal | None:
    if len(bars) < 2:
        return None
    path = sum(
        (
            abs(current.close - previous.close)
            for previous, current in zip(bars, bars[1:], strict=False)
        ),
        Decimal(0),
    )
    if path == 0:
        return None
    return abs(bars[-1].close - bars[0].close) / path


def _parameter_definitions(
    policy: RollingMeasurementPolicy,
    family: RollingFamilyPolicy,
    candidate: RollingCandidatePolicy,
) -> tuple[MetricParameterDefinition, ...]:
    mutability = (
        ParameterMutability.POLICY_CONTROLLED_RUNTIME
        if candidate.dynamic
        else ParameterMutability.STARTUP_ONLY
    )
    baseline = policy.baseline
    return (
        MetricParameterDefinition(
            parameter_id="duration_seconds",
            meaning="Exact rolling candidate duration",
            value_kind=MetricValueKind.INTEGER,
            unit="seconds",
            default=candidate.duration_seconds,
            scope=f"instrument+{family.family_id}+{candidate.candidate_id}",
            dynamic=candidate.dynamic,
            mutability=mutability,
            source=policy.parameter_source,
            minimum=candidate.minimum_duration_seconds,
            maximum=candidate.maximum_duration_seconds,
            step=candidate.duration_step_seconds,
        ),
        _count_parameter(
            "recent_reference_count",
            baseline.recent_reference_count,
            baseline.recent_reference_count_minimum,
            baseline.recent_reference_count_maximum,
            baseline.recent_reference_count_step,
            baseline.recent_reference_count_dynamic,
            policy.parameter_source,
        ),
        _count_parameter(
            "phase_reference_count",
            baseline.phase_reference_count,
            baseline.phase_reference_count_minimum,
            baseline.phase_reference_count_maximum,
            baseline.phase_reference_count_step,
            baseline.phase_reference_count_dynamic,
            policy.parameter_source,
        ),
        MetricParameterDefinition(
            parameter_id="minimum_coverage_ratio",
            meaning="Minimum eligible time coverage for a rolling window",
            value_kind=MetricValueKind.NUMBER,
            unit="ratio",
            default=policy.minimum_coverage_ratio,
            scope=f"instrument+{family.family_id}",
            dynamic=policy.minimum_coverage_ratio_dynamic,
            mutability=(
                ParameterMutability.POLICY_CONTROLLED_RUNTIME
                if policy.minimum_coverage_ratio_dynamic
                else ParameterMutability.STARTUP_ONLY
            ),
            source=policy.parameter_source,
            minimum=policy.minimum_coverage_ratio_floor,
            maximum=policy.minimum_coverage_ratio_ceiling,
            step=policy.minimum_coverage_ratio_step,
        ),
    )


def _count_parameter(
    parameter_id: str,
    default: int,
    minimum: int,
    maximum: int,
    step: int,
    dynamic: bool,
    source: str,
) -> MetricParameterDefinition:
    return MetricParameterDefinition(
        parameter_id=parameter_id,
        meaning=f"Requested eligible {parameter_id.replace('_', ' ')}",
        value_kind=MetricValueKind.INTEGER,
        unit="count",
        default=default,
        scope="instrument+rolling-candidate",
        dynamic=dynamic,
        mutability=(
            ParameterMutability.POLICY_CONTROLLED_RUNTIME
            if dynamic
            else ParameterMutability.STARTUP_ONLY
        ),
        source=source,
        minimum=minimum,
        maximum=maximum,
        step=step,
    )


def _metric_definition(
    policy: RollingMeasurementPolicy,
    family: RollingFamilyPolicy,
    candidate: RollingCandidatePolicy,
    suffix: str,
    parameters: tuple[MetricParameterDefinition, ...],
) -> MetricDefinition:
    metric_id = rolling_metric_id(family.family_id, candidate.candidate_id, suffix)
    integer = suffix.endswith("reference_count")
    unit = (
        "price"
        if suffix in {"price_range", "average_true_range"}
        else "count"
        if integer
        else "ratio"
    )
    formulas = {
        "price_range": "max(high) - min(low)",
        "realized_log_return_magnitude": "sqrt(sum(log(close_t / close_t-1)^2))",
        "average_true_range": "mean(true_range)",
        "directional_efficiency": "abs(last_close - first_close) / sum(abs(close_change))",
        "coverage_ratio": "covered_interval_ns / configured_duration_ns",
        "expansion_ratio_recent": "current_price_range / median(recent_equal_duration_ranges)",
        "range_percentile_recent": "empirical midrank against recent equal-duration ranges",
        "recent_reference_count": "count(eligible recent equal-duration ranges)",
        "expansion_ratio_phase": "current_price_range / median(phase_matched_ranges)",
        "range_percentile_phase": "empirical midrank against phase-matched ranges",
        "phase_reference_count": "count(eligible phase-matched ranges)",
    }
    return MetricDefinition(
        metric_id=metric_id,
        version=1,
        decision_question=(
            f"What numerical {suffix.replace('_', ' ')} does this rolling candidate report?"
        ),
        implementation_id=f"markeitech.{metric_id}.v1",
        formula=formulas[suffix],
        normalization="none",
        applicability="instruments with validated completed OHLC bars",
        value_kind=MetricValueKind.INTEGER if integer else MetricValueKind.NUMBER,
        unit=unit,
        cadence=MetricCadence.COMPLETED_BAR,
        horizon=f"{candidate.duration_seconds}s on {family.input_interval_seconds}s inputs",
        nullable=not integer,
        retained_state=MetricRetainedState.ROLLING_WINDOW,
        fidelity=MetricFidelity.DERIVED,
        allowed_fidelities=(
            MetricFidelity.DERIVED,
            MetricFidelity.PARTIAL,
            *((MetricFidelity.UNAVAILABLE,) if not integer else ()),
        ),
        failure_behavior=(
            MetricFailureBehavior.HOLD_LAST_STALE if integer else MetricFailureBehavior.EMIT_NULL
        ),
        failure_modes=(
            "insufficient current-window coverage",
            "insufficient eligible baseline observations",
            "missing authoritative phase alignment",
            "zero baseline median",
        ),
        priority=policy.priority,
        warmup=MetricWarmupPolicy(
            minimum_observations=candidate.duration_seconds // family.input_interval_seconds,
            minimum_elapsed_ns=candidate.duration_seconds * _NS_PER_SECOND,
            require_all_dependencies=True,
        ),
        resources=MetricResourcePolicy(
            maximum_retained_observations=policy.maximum_retained_observations,
            minimum_update_interval_ms=0,
            maximum_output_age_ms=policy.maximum_output_age_ms,
        ),
        metric_inputs=(
            MetricDependency(COMPLETED_BAR_HIGH_METRIC_ID, 1),
            MetricDependency(COMPLETED_BAR_LOW_METRIC_ID, 1),
            MetricDependency(COMPLETED_BAR_CLOSE_METRIC_ID, 1),
            MetricDependency(COMPLETED_BAR_TRUE_RANGE_METRIC_ID, 1),
        ),
        parameters=parameters,
    )


def _least_healthy(values: tuple[MetricHealth, ...]) -> MetricHealth:
    if not values:
        return MetricHealth.WARMING
    order = {
        MetricHealth.READY: 0,
        MetricHealth.WARMING: 1,
        MetricHealth.DEGRADED: 2,
        MetricHealth.STALE: 3,
        MetricHealth.UNAVAILABLE: 4,
        MetricHealth.UNSUPPORTED: 5,
        MetricHealth.FAILED: 6,
    }
    return max(values, key=order.__getitem__)


def _validate_envelope(value: int, minimum: int, maximum: int, step: int, label: str) -> None:
    if not minimum <= value <= maximum:
        raise ValueError(f"{label} is outside its configured envelope")
    if (value - minimum) % step:
        raise ValueError(f"{label} does not align to its configured step")


def _ratio(value: object, label: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1:
        raise ValueError(f"{label} must be a ratio between zero and one")


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _positive_int(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
