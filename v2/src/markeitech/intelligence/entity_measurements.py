from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from enum import StrEnum

from markeitech.intelligence.completed_bars import CompletedBarInput
from markeitech.intelligence.metrics import (
    MetricCadence,
    MetricDefinition,
    MetricDependency,
    MetricFailureBehavior,
    MetricFidelity,
    MetricHealth,
    MetricParameterDefinition,
    MetricResourcePolicy,
    MetricRetainedState,
    MetricValueKind,
    MetricWarmupPolicy,
    ParameterMutability,
)
from markeitech.intelligence.session_measurements import (
    COMPLETED_BAR_CLOSE_METRIC_ID,
    COMPLETED_BAR_HIGH_METRIC_ID,
    COMPLETED_BAR_LOW_METRIC_ID,
    COMPLETED_BAR_VOLUME_METRIC_ID,
)

SIGNED_DISPLACEMENT_METRIC_ID = "entity_input.direction.signed_displacement"
SIGNED_SIMPLE_RETURN_METRIC_ID = "entity_input.direction.signed_simple_return"
SIGNED_PATH_EFFICIENCY_METRIC_ID = "entity_input.direction.signed_path_efficiency"
EMA_REFERENCE_VALUE_METRIC_ID = "entity_input.reference.ema.value"
EMA_REFERENCE_SLOPE_METRIC_ID = "entity_input.reference.ema.slope"
EMA_REFERENCE_SEPARATION_METRIC_ID = "entity_input.reference.ema.separation"
SWING_PIVOT_PRICE_METRIC_ID = "entity_input.swing.pivot_price"
SWING_PROMINENCE_METRIC_ID = "entity_input.swing.prominence"
FVG_LOWER_BOUND_METRIC_ID = "entity_input.fvg.lower_bound"
FVG_UPPER_BOUND_METRIC_ID = "entity_input.fvg.upper_bound"
FVG_WIDTH_METRIC_ID = "entity_input.fvg.width"
FVG_FILL_RATIO_METRIC_ID = "entity_input.fvg.fill_ratio"
BAR_VOLUME_ALLOCATED_VOLUME_METRIC_ID = "entity_input.bar_volume.allocated_volume"

ENTITY_PREREQUISITE_METRIC_IDS = (
    SIGNED_DISPLACEMENT_METRIC_ID,
    SIGNED_SIMPLE_RETURN_METRIC_ID,
    SIGNED_PATH_EFFICIENCY_METRIC_ID,
    EMA_REFERENCE_VALUE_METRIC_ID,
    EMA_REFERENCE_SLOPE_METRIC_ID,
    EMA_REFERENCE_SEPARATION_METRIC_ID,
    SWING_PIVOT_PRICE_METRIC_ID,
    SWING_PROMINENCE_METRIC_ID,
    FVG_LOWER_BOUND_METRIC_ID,
    FVG_UPPER_BOUND_METRIC_ID,
    FVG_WIDTH_METRIC_ID,
    FVG_FILL_RATIO_METRIC_ID,
    BAR_VOLUME_ALLOCATED_VOLUME_METRIC_ID,
)


class SwingKind(StrEnum):
    HIGH = "HIGH"
    LOW = "LOW"


class FvgDirection(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"


@dataclass(frozen=True, slots=True)
class EntityPrerequisiteCatalogPolicy:
    parameter_source: str
    priority: int
    maximum_retained_observations: int
    maximum_output_age_ms: int

    def __post_init__(self) -> None:
        _required_text(self.parameter_source, "parameter_source")
        if not isinstance(self.priority, int) or isinstance(self.priority, bool):
            raise ValueError("priority must be an integer")
        if not 0 <= self.priority <= 100:
            raise ValueError("priority must be between zero and 100")
        _positive_int(self.maximum_retained_observations, "maximum_retained_observations")
        _positive_int(self.maximum_output_age_ms, "maximum_output_age_ms")


@dataclass(frozen=True, slots=True)
class EmaReferencePolicy:
    period: int
    minimum_period: int
    maximum_period: int
    period_step: int
    period_dynamic: bool
    slope_lookback_bars: int
    minimum_slope_lookback_bars: int
    maximum_slope_lookback_bars: int
    slope_lookback_step: int
    slope_lookback_dynamic: bool
    price_source: str

    def __post_init__(self) -> None:
        _integer_envelope(
            self.period,
            self.minimum_period,
            self.maximum_period,
            self.period_step,
            "EMA period",
        )
        _integer_envelope(
            self.slope_lookback_bars,
            self.minimum_slope_lookback_bars,
            self.maximum_slope_lookback_bars,
            self.slope_lookback_step,
            "EMA slope lookback",
        )
        if not isinstance(self.period_dynamic, bool):
            raise ValueError("period_dynamic must be a boolean")
        if not isinstance(self.slope_lookback_dynamic, bool):
            raise ValueError("slope_lookback_dynamic must be a boolean")
        if self.price_source != "close":
            raise ValueError("the first EMA prerequisite supports close price only")


@dataclass(frozen=True, slots=True)
class SwingGeometryPolicy:
    left_span_bars: int
    minimum_left_span_bars: int
    maximum_left_span_bars: int
    left_span_step: int
    left_span_dynamic: bool
    right_span_bars: int
    minimum_right_span_bars: int
    maximum_right_span_bars: int
    right_span_step: int
    right_span_dynamic: bool
    minimum_prominence: Decimal
    minimum_prominence_floor: Decimal
    minimum_prominence_ceiling: Decimal
    minimum_prominence_step: Decimal
    minimum_prominence_dynamic: bool
    tie_policy: str

    def __post_init__(self) -> None:
        _integer_envelope(
            self.left_span_bars,
            self.minimum_left_span_bars,
            self.maximum_left_span_bars,
            self.left_span_step,
            "left swing span",
        )
        _integer_envelope(
            self.right_span_bars,
            self.minimum_right_span_bars,
            self.maximum_right_span_bars,
            self.right_span_step,
            "right swing span",
        )
        _decimal_envelope(
            self.minimum_prominence,
            self.minimum_prominence_floor,
            self.minimum_prominence_ceiling,
            self.minimum_prominence_step,
            "minimum swing prominence",
        )
        for field in (
            "left_span_dynamic",
            "right_span_dynamic",
            "minimum_prominence_dynamic",
        ):
            if not isinstance(getattr(self, field), bool):
                raise ValueError(f"{field} must be a boolean")
        if self.tie_policy != "reject_ties":
            raise ValueError("the first swing geometry supports reject_ties only")


@dataclass(frozen=True, slots=True)
class FvgGeometryPolicy:
    pattern_length: int
    minimum_width: Decimal
    minimum_width_floor: Decimal
    minimum_width_ceiling: Decimal
    minimum_width_step: Decimal
    minimum_width_dynamic: bool
    price_basis: str
    fill_method: str

    def __post_init__(self) -> None:
        if self.pattern_length != 3:
            raise ValueError("the first FVG geometry requires exactly three bars")
        _decimal_envelope(
            self.minimum_width,
            self.minimum_width_floor,
            self.minimum_width_ceiling,
            self.minimum_width_step,
            "minimum FVG width",
        )
        if not isinstance(self.minimum_width_dynamic, bool):
            raise ValueError("minimum_width_dynamic must be a boolean")
        if self.price_basis != "wick":
            raise ValueError("the first FVG geometry supports wick boundaries only")
        if self.fill_method != "wick_penetration":
            raise ValueError("the first FVG fill method must be wick_penetration")


@dataclass(frozen=True, slots=True)
class BarVolumeAllocationPolicy:
    bin_width: Decimal
    minimum_bin_width: Decimal
    maximum_bin_width: Decimal
    bin_width_step: Decimal
    bin_width_dynamic: bool
    minimum_coverage_ratio: Decimal
    minimum_coverage_ratio_floor: Decimal
    minimum_coverage_ratio_ceiling: Decimal
    minimum_coverage_ratio_step: Decimal
    minimum_coverage_ratio_dynamic: bool
    allocation_method: str

    def __post_init__(self) -> None:
        _decimal_envelope(
            self.bin_width,
            self.minimum_bin_width,
            self.maximum_bin_width,
            self.bin_width_step,
            "bar-volume bin width",
        )
        _decimal_envelope(
            self.minimum_coverage_ratio,
            self.minimum_coverage_ratio_floor,
            self.minimum_coverage_ratio_ceiling,
            self.minimum_coverage_ratio_step,
            "bar-volume minimum coverage",
        )
        if not Decimal(0) <= self.minimum_coverage_ratio <= Decimal(1):
            raise ValueError("bar-volume minimum coverage must be between zero and one")
        if not isinstance(self.bin_width_dynamic, bool):
            raise ValueError("bin_width_dynamic must be a boolean")
        if not isinstance(self.minimum_coverage_ratio_dynamic, bool):
            raise ValueError("minimum_coverage_ratio_dynamic must be a boolean")
        if self.allocation_method != "uniform_intersection":
            raise ValueError("the first bar-volume allocation must be uniform_intersection")


@dataclass(frozen=True, slots=True)
class DirectionalPrerequisiteResult:
    signed_displacement: Decimal | None
    signed_simple_return: Decimal | None
    signed_path_efficiency: Decimal | None
    health: MetricHealth
    fidelity: MetricFidelity
    evidence_refs: tuple[str, ...]
    missing_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReferencePrerequisiteResult:
    value: Decimal | None
    slope_per_bar: Decimal | None
    price_separation: Decimal | None
    health: MetricHealth
    fidelity: MetricFidelity
    evidence_refs: tuple[str, ...]
    missing_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConfirmedSwingGeometry:
    kind: SwingKind
    pivot_price: Decimal
    prominence: Decimal
    pivot_ts_ns: int
    confirmation_ts_ns: int
    left_span_bars: int
    right_span_bars: int
    health: MetricHealth
    fidelity: MetricFidelity
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FvgGeometry:
    direction: FvgDirection
    lower_bound: Decimal
    upper_bound: Decimal
    width: Decimal
    fill_ratio: Decimal
    formation_ts_ns: int
    confirmation_ts_ns: int
    health: MetricHealth
    fidelity: MetricFidelity
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BarVolumeBinEstimate:
    lower_bound: Decimal
    upper_bound: Decimal
    estimated_volume: Decimal


@dataclass(frozen=True, slots=True)
class BarVolumeAllocationResult:
    bins: tuple[BarVolumeBinEstimate, ...]
    input_volume: Decimal
    allocated_volume: Decimal
    coverage_ratio: Decimal
    health: MetricHealth
    fidelity: MetricFidelity
    evidence_refs: tuple[str, ...]
    missing_reasons: tuple[str, ...]


def entity_prerequisite_metric_definitions(
    catalog: EntityPrerequisiteCatalogPolicy,
    *,
    reference: EmaReferencePolicy,
    swing: SwingGeometryPolicy,
    fvg: FvgGeometryPolicy,
    bar_volume: BarVolumeAllocationPolicy,
) -> tuple[MetricDefinition, ...]:
    if not isinstance(catalog, EntityPrerequisiteCatalogPolicy):
        raise ValueError("catalog must be an EntityPrerequisiteCatalogPolicy")
    groups = (
        (
            (
                SIGNED_DISPLACEMENT_METRIC_ID,
                "last_close - first_close",
                "price",
                "What is signed price displacement over this exact configured horizon?",
            ),
            (),
            (COMPLETED_BAR_CLOSE_METRIC_ID,),
            MetricFidelity.DERIVED,
            2,
        ),
        (
            (
                SIGNED_SIMPLE_RETURN_METRIC_ID,
                "(last_close - first_close) / first_close",
                "ratio",
                "What is signed simple return over this exact configured horizon?",
            ),
            (),
            (COMPLETED_BAR_CLOSE_METRIC_ID,),
            MetricFidelity.DERIVED,
            2,
        ),
        (
            (
                SIGNED_PATH_EFFICIENCY_METRIC_ID,
                "(last_close - first_close) / sum(abs(close_change))",
                "ratio",
                "How directionally efficient is the path with sign preserved?",
            ),
            (),
            (COMPLETED_BAR_CLOSE_METRIC_ID,),
            MetricFidelity.DERIVED,
            2,
        ),
    )
    definitions = [
        _metric_definition(catalog, descriptor, parameters, inputs, fidelity, warmup)
        for descriptor, parameters, inputs, fidelity, warmup in groups
    ]
    reference_parameters = _reference_parameters(catalog, reference)
    for descriptor in (
        (
            EMA_REFERENCE_VALUE_METRIC_ID,
            "EMA(close, period) seeded by SMA(period)",
            "price",
            "What is the configured EMA reference value?",
        ),
        (
            EMA_REFERENCE_SLOPE_METRIC_ID,
            "(ema_now - ema_lookback) / slope_lookback_bars",
            "price_per_bar",
            "What is the configured EMA slope per completed bar?",
        ),
        (
            EMA_REFERENCE_SEPARATION_METRIC_ID,
            "last_close - ema_now",
            "price",
            "How far is price from the configured EMA in price units?",
        ),
    ):
        warmup = reference.period
        if descriptor[0] == EMA_REFERENCE_SLOPE_METRIC_ID:
            warmup += reference.slope_lookback_bars
        definitions.append(
            _metric_definition(
                catalog,
                descriptor,
                reference_parameters,
                (COMPLETED_BAR_CLOSE_METRIC_ID,),
                MetricFidelity.DERIVED,
                warmup,
            ),
        )
    swing_parameters = _swing_parameters(catalog, swing)
    for descriptor in (
        (
            SWING_PIVOT_PRICE_METRIC_ID,
            "confirmed strict pivot high or low after configured right span",
            "price",
            "What is the price of this confirmed pivot geometry?",
        ),
        (
            SWING_PROMINENCE_METRIC_ID,
            "pivot distance beyond the most extreme neighboring wick",
            "price",
            "How prominent is this confirmed pivot against its configured neighbors?",
        ),
    ):
        definitions.append(
            _metric_definition(
                catalog,
                descriptor,
                swing_parameters,
                (COMPLETED_BAR_HIGH_METRIC_ID, COMPLETED_BAR_LOW_METRIC_ID),
                MetricFidelity.DERIVED,
                swing.left_span_bars + swing.right_span_bars + 1,
            ),
        )
    fvg_parameters = _fvg_parameters(catalog, fvg)
    for metric_id, formula, unit, question in (
        (
            FVG_LOWER_BOUND_METRIC_ID,
            "lower three-bar wick-gap bound",
            "price",
            "What is the lower bound of this configured FVG geometry?",
        ),
        (
            FVG_UPPER_BOUND_METRIC_ID,
            "upper three-bar wick-gap bound",
            "price",
            "What is the upper bound of this configured FVG geometry?",
        ),
        (
            FVG_WIDTH_METRIC_ID,
            "upper_bound - lower_bound",
            "price",
            "How wide is this configured FVG geometry?",
        ),
        (
            FVG_FILL_RATIO_METRIC_ID,
            "wick penetration / original gap width",
            "ratio",
            "How much of this FVG geometry has later price filled?",
        ),
    ):
        definitions.append(
            _metric_definition(
                catalog,
                (metric_id, formula, unit, question),
                fvg_parameters,
                (COMPLETED_BAR_HIGH_METRIC_ID, COMPLETED_BAR_LOW_METRIC_ID),
                MetricFidelity.DERIVED,
                fvg.pattern_length,
            ),
        )
    definitions.append(
        _metric_definition(
            catalog,
            (
                BAR_VOLUME_ALLOCATED_VOLUME_METRIC_ID,
                "bar_volume * intersected_bin_width / bar_range",
                "volume",
                "What candle-derived volume is allocated to this exact configured price bin?",
            ),
            _bar_volume_parameters(catalog, bar_volume),
            (
                COMPLETED_BAR_HIGH_METRIC_ID,
                COMPLETED_BAR_LOW_METRIC_ID,
                COMPLETED_BAR_VOLUME_METRIC_ID,
            ),
            MetricFidelity.INFERRED,
            1,
        ),
    )
    return tuple(definitions)


def calculate_directional_prerequisites(
    bars: tuple[CompletedBarInput, ...],
) -> DirectionalPrerequisiteResult:
    ordered = _ordered_bars(bars)
    evidence_refs = _evidence_refs(ordered)
    if len(ordered) < 2:
        return DirectionalPrerequisiteResult(
            None,
            None,
            None,
            MetricHealth.WARMING,
            MetricFidelity.UNAVAILABLE,
            evidence_refs,
            ("minimum_two_completed_bars_required",),
        )
    displacement = ordered[-1].close - ordered[0].close
    path = sum(
        (
            abs(current.close - previous.close)
            for previous, current in zip(ordered, ordered[1:], strict=False)
        ),
        Decimal(0),
    )
    missing = () if path else ("zero_directional_path",)
    return DirectionalPrerequisiteResult(
        signed_displacement=displacement,
        signed_simple_return=displacement / ordered[0].close,
        signed_path_efficiency=displacement / path if path else None,
        health=_least_healthy(tuple(item.health for item in ordered)),
        fidelity=_derived_fidelity(ordered),
        evidence_refs=evidence_refs,
        missing_reasons=missing,
    )


def calculate_ema_reference(
    bars: tuple[CompletedBarInput, ...],
    policy: EmaReferencePolicy,
) -> ReferencePrerequisiteResult:
    ordered = _ordered_bars(bars)
    if not isinstance(policy, EmaReferencePolicy):
        raise ValueError("policy must be an EmaReferencePolicy")
    evidence_refs = _evidence_refs(ordered)
    if len(ordered) < policy.period:
        return ReferencePrerequisiteResult(
            None,
            None,
            None,
            MetricHealth.WARMING,
            MetricFidelity.UNAVAILABLE,
            evidence_refs,
            ("ema_warmup_observations_insufficient",),
        )
    closes = tuple(item.close for item in ordered)
    ema_values = _ema_values(closes, policy.period)
    value = ema_values[-1]
    slope = None
    missing: tuple[str, ...] = ()
    if len(ema_values) <= policy.slope_lookback_bars:
        missing = ("ema_slope_lookback_insufficient",)
    else:
        slope = (value - ema_values[-1 - policy.slope_lookback_bars]) / Decimal(
            policy.slope_lookback_bars
        )
    return ReferencePrerequisiteResult(
        value=value,
        slope_per_bar=slope,
        price_separation=closes[-1] - value,
        health=_least_healthy(tuple(item.health for item in ordered)),
        fidelity=_derived_fidelity(ordered),
        evidence_refs=evidence_refs,
        missing_reasons=missing,
    )


def detect_confirmed_swings(
    bars: tuple[CompletedBarInput, ...],
    policy: SwingGeometryPolicy,
) -> tuple[ConfirmedSwingGeometry, ...]:
    ordered = _ordered_bars(bars)
    if not isinstance(policy, SwingGeometryPolicy):
        raise ValueError("policy must be a SwingGeometryPolicy")
    if len(ordered) < policy.left_span_bars + policy.right_span_bars + 1:
        return ()
    results: list[ConfirmedSwingGeometry] = []
    for pivot_index in range(
        policy.left_span_bars,
        len(ordered) - policy.right_span_bars,
    ):
        pivot = ordered[pivot_index]
        neighbors = (
            ordered[pivot_index - policy.left_span_bars : pivot_index]
            + ordered[pivot_index + 1 : pivot_index + policy.right_span_bars + 1]
        )
        high_prominence = pivot.high - max(item.high for item in neighbors)
        low_prominence = min(item.low for item in neighbors) - pivot.low
        if high_prominence >= policy.minimum_prominence and high_prominence > 0:
            results.append(
                _swing_result(SwingKind.HIGH, high_prominence, ordered, pivot_index, policy)
            )
        if low_prominence >= policy.minimum_prominence and low_prominence > 0:
            results.append(
                _swing_result(SwingKind.LOW, low_prominence, ordered, pivot_index, policy)
            )
    return tuple(results)


def detect_fvg_geometries(
    bars: tuple[CompletedBarInput, ...],
    policy: FvgGeometryPolicy,
) -> tuple[FvgGeometry, ...]:
    ordered = _ordered_bars(bars)
    if not isinstance(policy, FvgGeometryPolicy):
        raise ValueError("policy must be an FvgGeometryPolicy")
    results: list[FvgGeometry] = []
    for index in range(2, len(ordered)):
        first, third = ordered[index - 2], ordered[index]
        if third.low - first.high >= policy.minimum_width and third.low > first.high:
            results.append(
                _fvg_result(
                    FvgDirection.BULLISH,
                    first.high,
                    third.low,
                    ordered,
                    index,
                ),
            )
        if first.low - third.high >= policy.minimum_width and third.high < first.low:
            results.append(
                _fvg_result(
                    FvgDirection.BEARISH,
                    third.high,
                    first.low,
                    ordered,
                    index,
                ),
            )
    return tuple(results)


def allocate_bar_volume_to_bins(
    bars: tuple[CompletedBarInput, ...],
    policy: BarVolumeAllocationPolicy,
) -> BarVolumeAllocationResult:
    ordered = _ordered_bars(bars)
    if not isinstance(policy, BarVolumeAllocationPolicy):
        raise ValueError("policy must be a BarVolumeAllocationPolicy")
    evidence_refs = _evidence_refs(ordered)
    if not ordered:
        return BarVolumeAllocationResult(
            (),
            Decimal(0),
            Decimal(0),
            Decimal(0),
            MetricHealth.WARMING,
            MetricFidelity.UNAVAILABLE,
            evidence_refs,
            ("completed_bars_unavailable",),
        )
    eligible = tuple(item for item in ordered if item.volume is not None)
    coverage = Decimal(len(eligible)) / Decimal(len(ordered))
    if not eligible:
        return BarVolumeAllocationResult(
            (),
            Decimal(0),
            Decimal(0),
            coverage,
            MetricHealth.UNSUPPORTED,
            MetricFidelity.UNAVAILABLE,
            evidence_refs,
            ("volume_unavailable_for_all_bars",),
        )
    allocations: dict[int, Decimal] = {}
    input_volume = sum((item.volume for item in eligible if item.volume is not None), Decimal(0))
    for bar in eligible:
        assert bar.volume is not None
        _allocate_bar(bar, policy.bin_width, allocations)
    allocated_volume = sum(allocations.values(), Decimal(0))
    if allocated_volume != input_volume:
        raise RuntimeError("bar-volume allocation failed conservation")
    bins = tuple(
        BarVolumeBinEstimate(
            lower_bound=Decimal(index) * policy.bin_width,
            upper_bound=Decimal(index + 1) * policy.bin_width,
            estimated_volume=volume,
        )
        for index, volume in sorted(allocations.items())
    )
    if coverage < policy.minimum_coverage_ratio:
        health = MetricHealth.WARMING
        fidelity = MetricFidelity.PARTIAL
        missing = ("bar_volume_coverage_insufficient",)
    elif coverage < 1:
        health = _least_healthy(
            (*tuple(item.health for item in eligible), MetricHealth.DEGRADED),
        )
        fidelity = MetricFidelity.PARTIAL
        missing = ("bar_volume_partial_coverage",)
    else:
        health = _least_healthy(tuple(item.health for item in eligible))
        fidelity = (
            MetricFidelity.INFERRED if health is MetricHealth.READY else MetricFidelity.PARTIAL
        )
        missing = ()
    return BarVolumeAllocationResult(
        bins=bins,
        input_volume=input_volume,
        allocated_volume=allocated_volume,
        coverage_ratio=coverage,
        health=health,
        fidelity=fidelity,
        evidence_refs=evidence_refs,
        missing_reasons=missing,
    )


def _metric_definition(
    catalog: EntityPrerequisiteCatalogPolicy,
    descriptor: tuple[str, str, str, str],
    parameters: tuple[MetricParameterDefinition, ...],
    inputs: tuple[str, ...],
    fidelity: MetricFidelity,
    minimum_observations: int,
) -> MetricDefinition:
    metric_id, formula, unit, decision_question = descriptor
    return MetricDefinition(
        metric_id=metric_id,
        version=1,
        decision_question=decision_question,
        implementation_id=f"markeitech.{metric_id}.v1",
        formula=formula,
        normalization="none; downstream normalization must name its baseline",
        applicability="configured completed OHLCV bars with exact analytical profile and horizon",
        value_kind=MetricValueKind.NUMBER,
        unit=unit,
        cadence=MetricCadence.COMPLETED_BAR,
        horizon="exact configured application horizon",
        nullable=True,
        retained_state=MetricRetainedState.ROLLING_WINDOW,
        fidelity=fidelity,
        allowed_fidelities=(fidelity, MetricFidelity.PARTIAL, MetricFidelity.UNAVAILABLE),
        failure_behavior=MetricFailureBehavior.EMIT_NULL,
        failure_modes=(
            "insufficient completed-bar warmup",
            "unsupported input applicability",
            "missing or partial evidence",
            "stale or conflicting input identity",
        ),
        priority=catalog.priority,
        warmup=MetricWarmupPolicy(minimum_observations, 0, True),
        resources=MetricResourcePolicy(
            maximum_retained_observations=catalog.maximum_retained_observations,
            minimum_update_interval_ms=0,
            maximum_output_age_ms=catalog.maximum_output_age_ms,
        ),
        metric_inputs=tuple(MetricDependency(item, 1) for item in inputs),
        parameters=parameters,
    )


def _reference_parameters(
    catalog: EntityPrerequisiteCatalogPolicy,
    policy: EmaReferencePolicy,
) -> tuple[MetricParameterDefinition, ...]:
    return (
        _integer_parameter(
            "period",
            "EMA lookback in completed bars",
            policy.period,
            policy.minimum_period,
            policy.maximum_period,
            policy.period_step,
            policy.period_dynamic,
            catalog.parameter_source,
        ),
        _integer_parameter(
            "slope_lookback_bars",
            "Completed EMA observations used for slope",
            policy.slope_lookback_bars,
            policy.minimum_slope_lookback_bars,
            policy.maximum_slope_lookback_bars,
            policy.slope_lookback_step,
            policy.slope_lookback_dynamic,
            catalog.parameter_source,
        ),
        MetricParameterDefinition(
            parameter_id="price_source",
            meaning="Completed-bar price source used by the EMA",
            value_kind=MetricValueKind.TEXT,
            unit="category",
            default=policy.price_source,
            scope="analytical_profile+instrument+horizon+reference_definition",
            dynamic=False,
            mutability=ParameterMutability.STARTUP_ONLY,
            source=catalog.parameter_source,
            allowed_values=("close",),
        ),
    )


def _swing_parameters(
    catalog: EntityPrerequisiteCatalogPolicy,
    policy: SwingGeometryPolicy,
) -> tuple[MetricParameterDefinition, ...]:
    return (
        _integer_parameter(
            "left_span_bars",
            "Bars left of the pivot",
            policy.left_span_bars,
            policy.minimum_left_span_bars,
            policy.maximum_left_span_bars,
            policy.left_span_step,
            policy.left_span_dynamic,
            catalog.parameter_source,
        ),
        _integer_parameter(
            "right_span_bars",
            "Bars required after the pivot",
            policy.right_span_bars,
            policy.minimum_right_span_bars,
            policy.maximum_right_span_bars,
            policy.right_span_step,
            policy.right_span_dynamic,
            catalog.parameter_source,
        ),
        _decimal_parameter(
            "minimum_prominence",
            "Minimum strict wick prominence",
            "price",
            policy.minimum_prominence,
            policy.minimum_prominence_floor,
            policy.minimum_prominence_ceiling,
            policy.minimum_prominence_step,
            policy.minimum_prominence_dynamic,
            catalog.parameter_source,
        ),
        MetricParameterDefinition(
            parameter_id="tie_policy",
            meaning="Policy for equal neighboring pivot prices",
            value_kind=MetricValueKind.TEXT,
            unit="category",
            default=policy.tie_policy,
            scope="analytical_profile+instrument+horizon+swing_definition",
            dynamic=False,
            mutability=ParameterMutability.STARTUP_ONLY,
            source=catalog.parameter_source,
            allowed_values=("reject_ties",),
        ),
    )


def _fvg_parameters(
    catalog: EntityPrerequisiteCatalogPolicy,
    policy: FvgGeometryPolicy,
) -> tuple[MetricParameterDefinition, ...]:
    return (
        _integer_parameter(
            "pattern_length",
            "Completed bars in the FVG geometry",
            policy.pattern_length,
            3,
            3,
            1,
            False,
            catalog.parameter_source,
        ),
        _decimal_parameter(
            "minimum_width",
            "Minimum wick-gap width",
            "price",
            policy.minimum_width,
            policy.minimum_width_floor,
            policy.minimum_width_ceiling,
            policy.minimum_width_step,
            policy.minimum_width_dynamic,
            catalog.parameter_source,
        ),
        MetricParameterDefinition(
            parameter_id="price_basis",
            meaning="Bar geometry used for FVG bounds",
            value_kind=MetricValueKind.TEXT,
            unit="category",
            default=policy.price_basis,
            scope="analytical_profile+instrument+horizon+fvg_definition",
            dynamic=False,
            mutability=ParameterMutability.STARTUP_ONLY,
            source=catalog.parameter_source,
            allowed_values=("wick",),
        ),
        MetricParameterDefinition(
            parameter_id="fill_method",
            meaning="Price evidence used to measure later fill",
            value_kind=MetricValueKind.TEXT,
            unit="category",
            default=policy.fill_method,
            scope="analytical_profile+instrument+horizon+fvg_definition",
            dynamic=False,
            mutability=ParameterMutability.STARTUP_ONLY,
            source=catalog.parameter_source,
            allowed_values=("wick_penetration",),
        ),
    )


def _bar_volume_parameters(
    catalog: EntityPrerequisiteCatalogPolicy,
    policy: BarVolumeAllocationPolicy,
) -> tuple[MetricParameterDefinition, ...]:
    return (
        _decimal_parameter(
            "bin_width",
            "Price width of one inferred volume bin",
            "price",
            policy.bin_width,
            policy.minimum_bin_width,
            policy.maximum_bin_width,
            policy.bin_width_step,
            policy.bin_width_dynamic,
            catalog.parameter_source,
        ),
        _decimal_parameter(
            "minimum_coverage_ratio",
            "Minimum fraction of bars with usable volume",
            "ratio",
            policy.minimum_coverage_ratio,
            policy.minimum_coverage_ratio_floor,
            policy.minimum_coverage_ratio_ceiling,
            policy.minimum_coverage_ratio_step,
            policy.minimum_coverage_ratio_dynamic,
            catalog.parameter_source,
        ),
        MetricParameterDefinition(
            parameter_id="allocation_method",
            meaning="Deterministic candle-volume allocation formula",
            value_kind=MetricValueKind.TEXT,
            unit="category",
            default=policy.allocation_method,
            scope="analytical_profile+instrument+horizon+bar_volume_definition",
            dynamic=False,
            mutability=ParameterMutability.STARTUP_ONLY,
            source=catalog.parameter_source,
            allowed_values=("uniform_intersection",),
        ),
    )


def _integer_parameter(
    parameter_id: str,
    meaning: str,
    default: int,
    minimum: int,
    maximum: int,
    step: int,
    dynamic: bool,
    source: str,
) -> MetricParameterDefinition:
    return MetricParameterDefinition(
        parameter_id=parameter_id,
        meaning=meaning,
        value_kind=MetricValueKind.INTEGER,
        unit="bars",
        default=default,
        scope="analytical_profile+instrument+horizon+formula_definition",
        dynamic=dynamic,
        mutability=_mutability(dynamic),
        source=source,
        minimum=minimum,
        maximum=maximum,
        step=step,
    )


def _decimal_parameter(
    parameter_id: str,
    meaning: str,
    unit: str,
    default: Decimal,
    minimum: Decimal,
    maximum: Decimal,
    step: Decimal,
    dynamic: bool,
    source: str,
) -> MetricParameterDefinition:
    return MetricParameterDefinition(
        parameter_id=parameter_id,
        meaning=meaning,
        value_kind=MetricValueKind.NUMBER,
        unit=unit,
        default=default,
        scope="analytical_profile+instrument+horizon+formula_definition",
        dynamic=dynamic,
        mutability=_mutability(dynamic),
        source=source,
        minimum=minimum,
        maximum=maximum,
        step=step,
    )


def _mutability(dynamic: bool) -> ParameterMutability:
    return (
        ParameterMutability.POLICY_CONTROLLED_RUNTIME
        if dynamic
        else ParameterMutability.STARTUP_ONLY
    )


def _ordered_bars(bars: tuple[CompletedBarInput, ...]) -> tuple[CompletedBarInput, ...]:
    if not isinstance(bars, tuple) or any(not isinstance(item, CompletedBarInput) for item in bars):
        raise ValueError("bars must be a tuple of CompletedBarInput values")
    ordered = tuple(sorted(bars, key=lambda item: (item.interval_start_ns, item.interval_end_ns)))
    if not ordered:
        return ()
    identity = (
        ordered[0].instrument_id,
        ordered[0].bar_specification,
        ordered[0].analytical_profile_id,
        ordered[0].analytical_profile_version,
    )
    if any(
        (
            item.instrument_id,
            item.bar_specification,
            item.analytical_profile_id,
            item.analytical_profile_version,
        )
        != identity
        for item in ordered
    ):
        raise ValueError("bars must share instrument, specification, and analytical profile")
    if any(
        previous.interval_end_ns > current.interval_start_ns
        for previous, current in zip(ordered, ordered[1:], strict=False)
    ):
        raise ValueError("bars must not overlap")
    if any(not item.complete for item in ordered):
        raise ValueError("entity prerequisites require completed bars")
    return ordered


def _ema_values(closes: tuple[Decimal, ...], period: int) -> tuple[Decimal, ...]:
    seed = sum(closes[:period], Decimal(0)) / Decimal(period)
    multiplier = Decimal(2) / Decimal(period + 1)
    values = [seed]
    for close in closes[period:]:
        values.append((close - values[-1]) * multiplier + values[-1])
    return tuple(values)


def _swing_result(
    kind: SwingKind,
    prominence: Decimal,
    bars: tuple[CompletedBarInput, ...],
    pivot_index: int,
    policy: SwingGeometryPolicy,
) -> ConfirmedSwingGeometry:
    pivot = bars[pivot_index]
    confirmation = bars[pivot_index + policy.right_span_bars]
    evidence = bars[pivot_index - policy.left_span_bars : pivot_index + policy.right_span_bars + 1]
    return ConfirmedSwingGeometry(
        kind=kind,
        pivot_price=pivot.high if kind is SwingKind.HIGH else pivot.low,
        prominence=prominence,
        pivot_ts_ns=pivot.interval_end_ns,
        confirmation_ts_ns=confirmation.interval_end_ns,
        left_span_bars=policy.left_span_bars,
        right_span_bars=policy.right_span_bars,
        health=_least_healthy(tuple(item.health for item in evidence)),
        fidelity=_derived_fidelity(evidence),
        evidence_refs=_evidence_refs(evidence),
    )


def _fvg_result(
    direction: FvgDirection,
    lower_bound: Decimal,
    upper_bound: Decimal,
    bars: tuple[CompletedBarInput, ...],
    confirmation_index: int,
) -> FvgGeometry:
    width = upper_bound - lower_bound
    later = bars[confirmation_index + 1 :]
    if direction is FvgDirection.BULLISH:
        deepest = min((item.low for item in later), default=upper_bound)
        fill = min(Decimal(1), max(Decimal(0), (upper_bound - deepest) / width))
    else:
        highest = max((item.high for item in later), default=lower_bound)
        fill = min(Decimal(1), max(Decimal(0), (highest - lower_bound) / width))
    evidence = bars[confirmation_index - 2 :]
    confirmation = bars[confirmation_index]
    return FvgGeometry(
        direction=direction,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        width=width,
        fill_ratio=fill,
        formation_ts_ns=confirmation.interval_end_ns,
        confirmation_ts_ns=confirmation.interval_end_ns,
        health=_least_healthy(tuple(item.health for item in evidence)),
        fidelity=_derived_fidelity(evidence),
        evidence_refs=_evidence_refs(evidence),
    )


def _allocate_bar(
    bar: CompletedBarInput,
    bin_width: Decimal,
    allocations: dict[int, Decimal],
) -> None:
    assert bar.volume is not None
    if bar.high == bar.low:
        index = int((bar.low / bin_width).to_integral_value(rounding=ROUND_FLOOR))
        allocations[index] = allocations.get(index, Decimal(0)) + bar.volume
        return
    start = int((bar.low / bin_width).to_integral_value(rounding=ROUND_FLOOR))
    end = int((bar.high / bin_width).to_integral_value(rounding=ROUND_CEILING)) - 1
    bar_range = bar.high - bar.low
    distributed = Decimal(0)
    touched: list[int] = []
    for index in range(start, end + 1):
        lower = Decimal(index) * bin_width
        upper = Decimal(index + 1) * bin_width
        overlap = min(bar.high, upper) - max(bar.low, lower)
        if overlap <= 0:
            continue
        allocation = bar.volume * overlap / bar_range
        allocations[index] = allocations.get(index, Decimal(0)) + allocation
        distributed += allocation
        touched.append(index)
    if touched and distributed != bar.volume:
        allocations[touched[-1]] += bar.volume - distributed


def _evidence_refs(bars: tuple[CompletedBarInput, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(reference for item in bars for reference in item.evidence_refs))


def _derived_fidelity(bars: tuple[CompletedBarInput, ...]) -> MetricFidelity:
    if all(
        item.health is MetricHealth.READY
        and item.fidelity in {MetricFidelity.REPORTED, MetricFidelity.DERIVED}
        for item in bars
    ):
        return MetricFidelity.DERIVED
    return MetricFidelity.PARTIAL


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


def _integer_envelope(value: int, minimum: int, maximum: int, step: int, label: str) -> None:
    for candidate in (value, minimum, maximum, step):
        _positive_int(candidate, label)
    if not minimum <= value <= maximum:
        raise ValueError(f"{label} is outside its configured envelope")
    if (value - minimum) % step:
        raise ValueError(f"{label} does not align to its configured step")


def _decimal_envelope(
    value: Decimal,
    minimum: Decimal,
    maximum: Decimal,
    step: Decimal,
    label: str,
) -> None:
    for candidate in (value, minimum, maximum, step):
        if not isinstance(candidate, Decimal) or not candidate.is_finite():
            raise ValueError(f"{label} values must be finite Decimal values")
    if minimum < 0 or maximum < minimum or step <= 0:
        raise ValueError(f"{label} envelope is invalid")
    if not minimum <= value <= maximum:
        raise ValueError(f"{label} is outside its configured envelope")
    if (value - minimum) % step:
        raise ValueError(f"{label} does not align to its configured step")


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _positive_int(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
