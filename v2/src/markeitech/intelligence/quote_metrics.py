from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from markeitech.acquisition import CapabilityFeedRequirement, FeedKind
from markeitech.intelligence.metrics import (
    MetricCadence,
    MetricDefinition,
    MetricFailureBehavior,
    MetricFidelity,
    MetricHealth,
    MetricRegistry,
    MetricResourcePolicy,
    MetricRetainedState,
    MetricValue,
    MetricValueKind,
    MetricWarmupPolicy,
)

QUOTE_MIDPOINT_METRIC_ID = "quote.midpoint"
QUOTE_ABSOLUTE_SPREAD_METRIC_ID = "quote.spread.absolute"
QUOTE_RELATIVE_SPREAD_METRIC_ID = "quote.spread.relative"
QUOTE_METRIC_IDS = (
    QUOTE_MIDPOINT_METRIC_ID,
    QUOTE_ABSOLUTE_SPREAD_METRIC_ID,
    QUOTE_RELATIVE_SPREAD_METRIC_ID,
)

_VALUE_EVIDENCE_STATES = {"HEALTHY", "DEGRADED"}
_NULL_HEALTH_BY_EVIDENCE_STATE = {
    "NOT_EVALUATED": MetricHealth.WARMING,
    "DORMANT": MetricHealth.UNAVAILABLE,
    "STALE": MetricHealth.STALE,
    "UNAVAILABLE": MetricHealth.UNAVAILABLE,
    "UNSUPPORTED": MetricHealth.UNSUPPORTED,
}


@dataclass(frozen=True, slots=True)
class QuoteMetricCatalogPolicy:
    minimum_update_interval_ms: int
    maximum_output_age_ms: int
    priority: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.minimum_update_interval_ms, int)
            or isinstance(self.minimum_update_interval_ms, bool)
            or self.minimum_update_interval_ms < 0
        ):
            raise ValueError("minimum_update_interval_ms must be a non-negative integer")
        if (
            not isinstance(self.maximum_output_age_ms, int)
            or isinstance(self.maximum_output_age_ms, bool)
            or self.maximum_output_age_ms <= 0
        ):
            raise ValueError("maximum_output_age_ms must be a positive integer")
        if not isinstance(self.priority, int) or isinstance(self.priority, bool):
            raise ValueError("priority must be an integer")
        if not 0 <= self.priority <= 100:
            raise ValueError("priority must be between 0 and 100")


@dataclass(frozen=True, slots=True)
class QuoteMetricInput:
    instrument_id: str
    bid: Decimal | None
    ask: Decimal | None
    observed_ts_ns: int
    received_ts_ns: int
    session_id: str | None
    evidence_state: str
    evidence_ref: str

    def __post_init__(self) -> None:
        for field in ("instrument_id", "evidence_state", "evidence_ref"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be a non-empty string")
        if self.session_id is not None and (
            not isinstance(self.session_id, str) or not self.session_id.strip()
        ):
            raise ValueError("session_id must be a non-empty string when provided")
        for field in ("observed_ts_ns", "received_ts_ns"):
            value = getattr(self, field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field} must be a non-negative integer")
        if self.received_ts_ns < self.observed_ts_ns:
            raise ValueError("received_ts_ns cannot precede observed_ts_ns")
        for field in ("bid", "ask"):
            value = getattr(self, field)
            if value is not None and not isinstance(value, Decimal):
                raise ValueError(f"{field} must be Decimal or None")


def quote_metric_definitions(policy: QuoteMetricCatalogPolicy) -> tuple[MetricDefinition, ...]:
    if not isinstance(policy, QuoteMetricCatalogPolicy):
        raise ValueError("policy must be a QuoteMetricCatalogPolicy")
    input_requirement = CapabilityFeedRequirement(kind=FeedKind.QUOTES)
    common = {
        "version": 1,
        "normalization": "none",
        "applicability": "instruments with a valid two-sided top-of-book quote",
        "cadence": MetricCadence.OBSERVATION,
        "horizon": "current top-of-book observation",
        "nullable": True,
        "retained_state": MetricRetainedState.LATEST,
        "fidelity": MetricFidelity.DERIVED,
        "allowed_fidelities": (
            MetricFidelity.DERIVED,
            MetricFidelity.PARTIAL,
            MetricFidelity.UNAVAILABLE,
        ),
        "failure_behavior": MetricFailureBehavior.EMIT_NULL,
        "failure_modes": (
            "missing bid or ask",
            "crossed or non-positive quote",
            "stale or unavailable quote evidence",
        ),
        "priority": policy.priority,
        "warmup": MetricWarmupPolicy(
            minimum_observations=1,
            minimum_elapsed_ns=0,
            require_all_dependencies=True,
        ),
        "resources": MetricResourcePolicy(
            maximum_retained_observations=1,
            minimum_update_interval_ms=policy.minimum_update_interval_ms,
            maximum_output_age_ms=policy.maximum_output_age_ms,
        ),
        "live_inputs": (input_requirement,),
    }
    return (
        MetricDefinition(
            metric_id=QUOTE_MIDPOINT_METRIC_ID,
            decision_question="What is the center of the current valid two-sided quote?",
            implementation_id="markeitech.quote.midpoint.v1",
            formula="(bid + ask) / 2",
            value_kind=MetricValueKind.NUMBER,
            unit="price",
            **common,
        ),
        MetricDefinition(
            metric_id=QUOTE_ABSOLUTE_SPREAD_METRIC_ID,
            decision_question="How wide is the current valid quote in price units?",
            implementation_id="markeitech.quote.absolute_spread.v1",
            formula="ask - bid",
            value_kind=MetricValueKind.NUMBER,
            unit="price",
            **common,
        ),
        MetricDefinition(
            metric_id=QUOTE_RELATIVE_SPREAD_METRIC_ID,
            decision_question="How wide is the current valid quote relative to its midpoint?",
            implementation_id="markeitech.quote.relative_spread.v1",
            formula="(ask - bid) / midpoint",
            value_kind=MetricValueKind.NUMBER,
            unit="ratio",
            **common,
        ),
    )


def calculate_quote_metrics(
    quote: QuoteMetricInput,
    *,
    registry: MetricRegistry,
    parameter_version: int,
    calculated_ts_ns: int,
    published_ts_ns: int,
    source: str,
    revision: int,
) -> tuple[MetricValue, ...]:
    if not isinstance(quote, QuoteMetricInput):
        raise ValueError("quote must be a QuoteMetricInput")
    if not isinstance(registry, MetricRegistry):
        raise ValueError("registry must be a MetricRegistry")
    definitions = tuple(registry.get(metric_id, 1) for metric_id in QUOTE_METRIC_IDS)
    reasons = _unavailable_reasons(quote)
    if reasons:
        values = _null_values(quote.evidence_state)
        results = tuple(
            _metric_value(
                definition,
                quote,
                value=None,
                health=values[0],
                fidelity=values[1],
                missing_reasons=reasons,
                parameter_version=parameter_version,
                calculated_ts_ns=calculated_ts_ns,
                published_ts_ns=published_ts_ns,
                source=source,
                revision=revision,
            )
            for definition in definitions
        )
    else:
        assert quote.bid is not None
        assert quote.ask is not None
        midpoint = (quote.bid + quote.ask) / Decimal(2)
        spread = quote.ask - quote.bid
        health = MetricHealth.READY if quote.evidence_state == "HEALTHY" else MetricHealth.DEGRADED
        fidelity = (
            MetricFidelity.DERIVED if quote.evidence_state == "HEALTHY" else MetricFidelity.PARTIAL
        )
        calculated = (midpoint, spread, spread / midpoint)
        results = tuple(
            _metric_value(
                definition,
                quote,
                value=value,
                health=health,
                fidelity=fidelity,
                missing_reasons=(),
                parameter_version=parameter_version,
                calculated_ts_ns=calculated_ts_ns,
                published_ts_ns=published_ts_ns,
                source=source,
                revision=revision,
            )
            for definition, value in zip(definitions, calculated, strict=True)
        )
    for value in results:
        registry.validate_value(value)
    return results


def _unavailable_reasons(quote: QuoteMetricInput) -> tuple[str, ...]:
    reasons: list[str] = []
    if quote.evidence_state not in _VALUE_EVIDENCE_STATES:
        reasons.append(f"evidence_{quote.evidence_state.lower()}")
    if quote.bid is None:
        reasons.append("bid_missing")
    elif not quote.bid.is_finite():
        reasons.append("bid_non_finite")
    elif quote.bid <= 0:
        reasons.append("bid_non_positive")
    if quote.ask is None:
        reasons.append("ask_missing")
    elif not quote.ask.is_finite():
        reasons.append("ask_non_finite")
    elif quote.ask <= 0:
        reasons.append("ask_non_positive")
    if (
        quote.bid is not None
        and quote.ask is not None
        and quote.bid.is_finite()
        and quote.ask.is_finite()
        and quote.bid > 0
        and quote.ask > 0
        and quote.ask < quote.bid
    ):
        reasons.append("crossed_quote")
    return tuple(reasons)


def _null_values(evidence_state: str) -> tuple[MetricHealth, MetricFidelity]:
    health = _NULL_HEALTH_BY_EVIDENCE_STATE.get(evidence_state, MetricHealth.FAILED)
    fidelity = (
        MetricFidelity.PARTIAL
        if evidence_state in _VALUE_EVIDENCE_STATES
        else MetricFidelity.UNAVAILABLE
    )
    return health, fidelity


def _metric_value(
    definition: MetricDefinition,
    quote: QuoteMetricInput,
    *,
    value: Decimal | None,
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
        instrument_id=quote.instrument_id,
        session_id=quote.session_id,
        value=value,
        unit=definition.unit,
        effective_ts_ns=quote.observed_ts_ns,
        observed_ts_ns=quote.observed_ts_ns,
        received_ts_ns=quote.received_ts_ns,
        calculated_ts_ns=calculated_ts_ns,
        published_ts_ns=published_ts_ns,
        health=health,
        fidelity=fidelity,
        source=source,
        evidence_refs=(quote.evidence_ref,),
        missing_reasons=missing_reasons,
        revision=revision,
    )
