from __future__ import annotations

from dataclasses import dataclass

from markeitech.acquisition import (
    CapabilityFeedRequirement,
    CapabilityHistoricalRequirement,
    FeedKind,
    HistoricalWindow,
)
from markeitech.intelligence.metrics import (
    MetricCadence,
    MetricDefinition,
    MetricFailureBehavior,
    MetricFidelity,
    MetricParameterDefinition,
    MetricResourcePolicy,
    MetricRetainedState,
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
    maximum_retained_observations: int
    maximum_output_age_ms: int

    def __post_init__(self) -> None:
        for field in ("live_selector", "historical_selector"):
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
            "calculation_interval_seconds": policy.calculation_interval_seconds,
            "purpose": "completed_bar_foundation",
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
        source="operator-reviewed-config",
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
            "price",
            one_bar_warmup,
            common,
        ),
        _definition(
            COMPLETED_BAR_HIGH_METRIC_ID,
            "What high did the completed calculation interval report?",
            "price",
            one_bar_warmup,
            common,
        ),
        _definition(
            COMPLETED_BAR_LOW_METRIC_ID,
            "What low did the completed calculation interval report?",
            "price",
            one_bar_warmup,
            common,
        ),
        _definition(
            COMPLETED_BAR_CLOSE_METRIC_ID,
            "What close did the completed calculation interval report?",
            "price",
            one_bar_warmup,
            common,
        ),
        _definition(
            COMPLETED_BAR_VOLUME_METRIC_ID,
            "What supported volume did the completed calculation interval report?",
            "volume",
            one_bar_warmup,
            common,
        ),
        _definition(
            COMPLETED_BAR_SIMPLE_RETURN_METRIC_ID,
            "How far did close move from the preceding compatible close?",
            "ratio",
            two_bar_warmup,
            common,
        ),
        _definition(
            COMPLETED_BAR_TRUE_RANGE_METRIC_ID,
            "What range did the interval realize including a compatible prior-close gap?",
            "price",
            two_bar_warmup,
            common,
        ),
    )


def _definition(
    metric_id: str,
    decision_question: str,
    unit: str,
    warmup: MetricWarmupPolicy,
    common: dict[str, object],
) -> MetricDefinition:
    return MetricDefinition(
        metric_id=metric_id,
        decision_question=decision_question,
        implementation_id=f"markeitech.{metric_id}.v1",
        value_kind=MetricValueKind.NUMBER,
        unit=unit,
        warmup=warmup,
        **common,  # type: ignore[arg-type]
    )


def _positive_int(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
