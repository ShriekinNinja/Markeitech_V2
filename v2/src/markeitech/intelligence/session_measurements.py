from __future__ import annotations

from dataclasses import dataclass

from markeitech.acquisition import (
    CapabilityFeedRequirement,
    CapabilityHistoricalRequirement,
    FeedKind,
    HistoricalWindow,
)
from markeitech.intelligence.completed_bars import CompletedBarInput
from markeitech.intelligence.metrics import (
    MetricCadence,
    MetricDefinition,
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

COMPLETED_BAR_OPEN_METRIC_ID = "completed_bar.open"
COMPLETED_BAR_HIGH_METRIC_ID = "completed_bar.high"
COMPLETED_BAR_LOW_METRIC_ID = "completed_bar.low"
COMPLETED_BAR_CLOSE_METRIC_ID = "completed_bar.close"
COMPLETED_BAR_VOLUME_METRIC_ID = "completed_bar.volume"
COMPLETED_BAR_SIMPLE_RETURN_METRIC_ID = "completed_bar.simple_return"
COMPLETED_BAR_TRUE_RANGE_METRIC_ID = "completed_bar.true_range"

COMPLETED_BAR_METRIC_IDS = (
    COMPLETED_BAR_OPEN_METRIC_ID,
    COMPLETED_BAR_HIGH_METRIC_ID,
    COMPLETED_BAR_LOW_METRIC_ID,
    COMPLETED_BAR_CLOSE_METRIC_ID,
    COMPLETED_BAR_VOLUME_METRIC_ID,
    COMPLETED_BAR_SIMPLE_RETURN_METRIC_ID,
    COMPLETED_BAR_TRUE_RANGE_METRIC_ID,
)


@dataclass(frozen=True, slots=True)
class CompletedBarCatalogPolicy:
    live_selector: str
    historical_selector: str
    historical_window: HistoricalWindow
    minimum_historical_observations: int
    maximum_historical_observations: int
    calculation_interval_seconds: int
    minimum_interval_seconds: int
    maximum_interval_seconds: int
    interval_step_seconds: int
    interval_dynamic: bool
    aggregation_boundary_policy: str
    revision_policy: str
    parameter_source: str
    priority: int
    maximum_retained_observations: int
    maximum_output_age_ms: int

    def __post_init__(self) -> None:
        for field in (
            "live_selector",
            "historical_selector",
            "aggregation_boundary_policy",
            "revision_policy",
            "parameter_source",
        ):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be a non-empty string")
        if not isinstance(self.historical_window, HistoricalWindow):
            raise ValueError("historical_window must be a HistoricalWindow")
        for field in (
            "minimum_historical_observations",
            "maximum_historical_observations",
            "calculation_interval_seconds",
            "minimum_interval_seconds",
            "maximum_interval_seconds",
            "interval_step_seconds",
            "maximum_retained_observations",
            "maximum_output_age_ms",
        ):
            _positive_int(getattr(self, field), field)
        if self.maximum_historical_observations < self.minimum_historical_observations:
            raise ValueError("maximum historical observations cannot be below the minimum")
        if (
            not self.minimum_interval_seconds
            <= self.calculation_interval_seconds
            <= (self.maximum_interval_seconds)
        ):
            raise ValueError("calculation interval must be inside its configured envelope")
        if (
            self.calculation_interval_seconds - self.minimum_interval_seconds
        ) % self.interval_step_seconds:
            raise ValueError("calculation interval must align to interval_step_seconds")
        if not isinstance(self.interval_dynamic, bool):
            raise ValueError("interval_dynamic must be a boolean")
        if self.aggregation_boundary_policy != "utc_fixed_intraday":
            raise ValueError("aggregation_boundary_policy must be utc_fixed_intraday")
        if 86_400 % self.calculation_interval_seconds:
            raise ValueError("UTC-fixed interval must divide one UTC day exactly")
        if self.revision_policy != "reject_revision":
            raise ValueError("revision_policy must be reject_revision")
        if not isinstance(self.priority, int) or isinstance(self.priority, bool):
            raise ValueError("priority must be an integer")
        if not 0 <= self.priority <= 100:
            raise ValueError("priority must be between 0 and 100")


def completed_bar_metric_definitions(
    policy: CompletedBarCatalogPolicy,
) -> tuple[MetricDefinition, ...]:
    if not isinstance(policy, CompletedBarCatalogPolicy):
        raise ValueError("policy must be a CompletedBarCatalogPolicy")
    live_input = CapabilityFeedRequirement(
        kind=FeedKind.BARS,
        selector=policy.live_selector,
    )
    historical_input = CapabilityHistoricalRequirement(
        kind=FeedKind.BARS,
        selector=policy.historical_selector,
        window=policy.historical_window,
        minimum_observations=policy.minimum_historical_observations,
        maximum_observations=policy.maximum_historical_observations,
        parameters={
            "aggregation_boundary_policy": policy.aggregation_boundary_policy,
            "calculation_interval_seconds": policy.calculation_interval_seconds,
            "purpose": "completed_bar_foundation",
            "revision_policy": policy.revision_policy,
        },
    )
    interval = MetricParameterDefinition(
        parameter_id="calculation_interval_seconds",
        meaning="Completed calculation interval represented by this metric",
        value_kind=MetricValueKind.INTEGER,
        unit="seconds",
        default=policy.calculation_interval_seconds,
        scope="instrument+analytical_profile+dependency",
        dynamic=policy.interval_dynamic,
        mutability=(
            ParameterMutability.POLICY_CONTROLLED_RUNTIME
            if policy.interval_dynamic
            else ParameterMutability.STARTUP_ONLY
        ),
        source=policy.parameter_source,
        minimum=policy.minimum_interval_seconds,
        maximum=policy.maximum_interval_seconds,
        step=policy.interval_step_seconds,
    )
    common = {
        "version": 1,
        "cadence": MetricCadence.COMPLETED_BAR,
        "horizon": "declared completed-bar dependency",
        "nullable": True,
        "retained_state": MetricRetainedState.ROLLING_WINDOW,
        "fidelity": MetricFidelity.DERIVED,
        "failure_behavior": MetricFailureBehavior.EMIT_NULL,
        "priority": policy.priority,
        "resources": MetricResourcePolicy(
            maximum_retained_observations=policy.maximum_retained_observations,
            minimum_update_interval_ms=0,
            maximum_output_age_ms=policy.maximum_output_age_ms,
        ),
        "live_inputs": (live_input,),
        "historical_inputs": (historical_input,),
        "parameters": (interval,),
    }
    one_bar_warmup = MetricWarmupPolicy(
        minimum_observations=1,
        minimum_elapsed_ns=0,
        require_all_dependencies=True,
    )
    two_bar_warmup = MetricWarmupPolicy(
        minimum_observations=2,
        minimum_elapsed_ns=0,
        require_all_dependencies=True,
    )
    return (
        _definition(
            COMPLETED_BAR_OPEN_METRIC_ID,
            "What open did the completed calculation interval report?",
            "completed_bar.open",
            "none",
            "price",
            one_bar_warmup,
            common,
        ),
        _definition(
            COMPLETED_BAR_HIGH_METRIC_ID,
            "What high did the completed calculation interval report?",
            "completed_bar.high",
            "none",
            "price",
            one_bar_warmup,
            common,
        ),
        _definition(
            COMPLETED_BAR_LOW_METRIC_ID,
            "What low did the completed calculation interval report?",
            "completed_bar.low",
            "none",
            "price",
            one_bar_warmup,
            common,
        ),
        _definition(
            COMPLETED_BAR_CLOSE_METRIC_ID,
            "What close did the completed calculation interval report?",
            "completed_bar.close",
            "none",
            "price",
            one_bar_warmup,
            common,
        ),
        _definition(
            COMPLETED_BAR_VOLUME_METRIC_ID,
            "What supported volume did the completed calculation interval report?",
            "completed_bar.volume",
            "none",
            "volume",
            one_bar_warmup,
            common,
        ),
        _definition(
            COMPLETED_BAR_SIMPLE_RETURN_METRIC_ID,
            "How far did close move from the preceding compatible close?",
            "(completed_bar.close / prior_compatible_close) - 1",
            "dimensionless simple return",
            "ratio",
            two_bar_warmup,
            common,
        ),
        _definition(
            COMPLETED_BAR_TRUE_RANGE_METRIC_ID,
            "What range did the interval realize including a compatible prior-close gap?",
            "max(high - low, abs(high - prior_close), abs(low - prior_close))",
            "none",
            "price",
            two_bar_warmup,
            common,
        ),
    )


def calculate_completed_bar_metrics(
    bar: CompletedBarInput,
    *,
    prior_bar: CompletedBarInput | None,
    registry: MetricRegistry,
    parameter_version: int,
    calculated_ts_ns: int,
    published_ts_ns: int,
    source: str,
    revision: int,
) -> tuple[MetricValue, ...]:
    """Calculate the Stage 9C-S1 metric family from one admitted completed bar."""
    if not isinstance(bar, CompletedBarInput):
        raise ValueError("bar must be a CompletedBarInput")
    if prior_bar is not None and not isinstance(prior_bar, CompletedBarInput):
        raise ValueError("prior_bar must be a CompletedBarInput or None")
    if not isinstance(registry, MetricRegistry):
        raise ValueError("registry must be a MetricRegistry")
    if prior_bar is not None and (
        prior_bar.instrument_id != bar.instrument_id
        or prior_bar.bar_specification != bar.bar_specification
        or prior_bar.calendar_id != bar.calendar_id
        or prior_bar.analytical_profile_id != bar.analytical_profile_id
        or prior_bar.analytical_profile_version != bar.analytical_profile_version
        or prior_bar.interval_end_ns >= bar.interval_end_ns
    ):
        raise ValueError("prior_bar is not compatible with bar")

    prior_close = prior_bar.close if prior_bar is not None else None
    calculated: dict[str, tuple[object | None, MetricHealth, MetricFidelity, tuple[str, ...]]] = {
        COMPLETED_BAR_OPEN_METRIC_ID: (bar.open, bar.health, bar.fidelity, ()),
        COMPLETED_BAR_HIGH_METRIC_ID: (bar.high, bar.health, bar.fidelity, ()),
        COMPLETED_BAR_LOW_METRIC_ID: (bar.low, bar.health, bar.fidelity, ()),
        COMPLETED_BAR_CLOSE_METRIC_ID: (bar.close, bar.health, bar.fidelity, ()),
    }
    if bar.volume is None:
        volume_reason = next(
            (
                reason
                for reason in bar.missing_reasons
                if reason in {"volume_missing", "volume_unsupported", "volume_partial"}
            ),
            "volume_missing",
        )
        volume_health = (
            MetricHealth.UNSUPPORTED
            if volume_reason == "volume_unsupported"
            else MetricHealth.UNAVAILABLE
        )
        calculated[COMPLETED_BAR_VOLUME_METRIC_ID] = (
            None,
            volume_health,
            MetricFidelity.UNAVAILABLE,
            (volume_reason,),
        )
    else:
        calculated[COMPLETED_BAR_VOLUME_METRIC_ID] = (
            bar.volume,
            bar.health,
            bar.fidelity,
            (),
        )
    if prior_close is None:
        missing = ("prior_compatible_close_missing",)
        calculated[COMPLETED_BAR_SIMPLE_RETURN_METRIC_ID] = (
            None,
            MetricHealth.WARMING,
            MetricFidelity.UNAVAILABLE,
            missing,
        )
        calculated[COMPLETED_BAR_TRUE_RANGE_METRIC_ID] = (
            None,
            MetricHealth.WARMING,
            MetricFidelity.UNAVAILABLE,
            missing,
        )
    else:
        derived_fidelity = (
            MetricFidelity.DERIVED
            if bar.health is MetricHealth.READY
            else MetricFidelity.PARTIAL
        )
        calculated[COMPLETED_BAR_SIMPLE_RETURN_METRIC_ID] = (
            bar.close / prior_close - 1,
            bar.health,
            derived_fidelity,
            (),
        )
        calculated[COMPLETED_BAR_TRUE_RANGE_METRIC_ID] = (
            max(bar.high - bar.low, abs(bar.high - prior_close), abs(bar.low - prior_close)),
            bar.health,
            derived_fidelity,
            (),
        )

    values = tuple(
        _completed_bar_metric_value(
            registry.get(metric_id, 1),
            bar,
            value=calculated[metric_id][0],
            health=calculated[metric_id][1],
            fidelity=calculated[metric_id][2],
            missing_reasons=calculated[metric_id][3],
            parameter_version=parameter_version,
            calculated_ts_ns=calculated_ts_ns,
            published_ts_ns=published_ts_ns,
            source=source,
            revision=revision,
        )
        for metric_id in COMPLETED_BAR_METRIC_IDS
    )
    for value in values:
        registry.validate_value(value)
    return values


def _completed_bar_metric_value(
    definition: MetricDefinition,
    bar: CompletedBarInput,
    *,
    value: object | None,
    health: MetricHealth,
    fidelity: MetricFidelity,
    missing_reasons: tuple[str, ...],
    parameter_version: int,
    calculated_ts_ns: int,
    published_ts_ns: int,
    source: str,
    revision: int,
) -> MetricValue:
    return MetricValue(
        metric_id=definition.metric_id,
        metric_version=definition.version,
        parameter_version=parameter_version,
        instrument_id=bar.instrument_id,
        session_id=bar.session_id,
        value=value,  # type: ignore[arg-type]
        unit=definition.unit,
        effective_ts_ns=bar.interval_end_ns,
        observed_ts_ns=bar.observed_ts_ns,
        received_ts_ns=bar.received_ts_ns,
        calculated_ts_ns=calculated_ts_ns,
        published_ts_ns=published_ts_ns,
        health=health,
        fidelity=fidelity,
        source=source,
        evidence_refs=bar.evidence_refs,
        missing_reasons=missing_reasons,
        revision=revision,
    )


def _definition(
    metric_id: str,
    decision_question: str,
    formula: str,
    normalization: str,
    unit: str,
    warmup: MetricWarmupPolicy,
    common: dict[str, object],
) -> MetricDefinition:
    direct_metrics = {
        COMPLETED_BAR_OPEN_METRIC_ID,
        COMPLETED_BAR_HIGH_METRIC_ID,
        COMPLETED_BAR_LOW_METRIC_ID,
        COMPLETED_BAR_CLOSE_METRIC_ID,
        COMPLETED_BAR_VOLUME_METRIC_ID,
    }
    failure_modes = [
        "incomplete or non-contiguous interval",
        "missing or unhealthy evidence",
        "historical/live observation conflict",
    ]
    if metric_id == COMPLETED_BAR_VOLUME_METRIC_ID:
        failure_modes.append("unsupported or missing volume")
    if metric_id in {
        COMPLETED_BAR_SIMPLE_RETURN_METRIC_ID,
        COMPLETED_BAR_TRUE_RANGE_METRIC_ID,
    }:
        failure_modes.append("missing compatible prior close")
    return MetricDefinition(
        metric_id=metric_id,
        decision_question=decision_question,
        implementation_id=f"markeitech.{metric_id}.v1",
        formula=formula,
        normalization=normalization,
        applicability=(
            "instruments with validated completed OHLCV bars and a volume-supporting profile"
            if metric_id == COMPLETED_BAR_VOLUME_METRIC_ID
            else "instruments with validated completed OHLC bars"
        ),
        value_kind=MetricValueKind.NUMBER,
        unit=unit,
        warmup=warmup,
        allowed_fidelities=(
            *((MetricFidelity.REPORTED,) if metric_id in direct_metrics else ()),
            MetricFidelity.DERIVED,
            MetricFidelity.PARTIAL,
            MetricFidelity.UNAVAILABLE,
        ),
        failure_modes=tuple(failure_modes),
        **common,  # type: ignore[arg-type]
    )


def _positive_int(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
