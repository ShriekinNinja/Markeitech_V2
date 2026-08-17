from __future__ import annotations

from decimal import Decimal

import pytest

from markeitech.intelligence import (
    QUOTE_ABSOLUTE_SPREAD_METRIC_ID,
    QUOTE_MIDPOINT_METRIC_ID,
    QUOTE_RELATIVE_SPREAD_METRIC_ID,
    MetricFidelity,
    MetricHealth,
    MetricRegistry,
    QuoteMetricCatalogPolicy,
    QuoteMetricInput,
    calculate_quote_metrics,
    quote_metric_definitions,
)


def _registry() -> MetricRegistry:
    return MetricRegistry(
        quote_metric_definitions(
            QuoteMetricCatalogPolicy(
                minimum_update_interval_ms=100,
                maximum_output_age_ms=5_000,
            ),
        ),
    )


def _quote(
    *,
    bid: Decimal | None = Decimal("7520.00"),
    ask: Decimal | None = Decimal("7520.25"),
    evidence_state: str = "HEALTHY",
) -> QuoteMetricInput:
    return QuoteMetricInput(
        instrument_id="ESU6.CME",
        bid=bid,
        ask=ask,
        observed_ts_ns=100,
        received_ts_ns=101,
        session_id="CME-2026-08-17-GTH",
        evidence_state=evidence_state,
        evidence_ref="quote:ESU6.CME:100",
    )


def _calculate(quote: QuoteMetricInput) -> dict[str, object]:
    values = calculate_quote_metrics(
        quote,
        registry=_registry(),
        parameter_version=1,
        calculated_ts_ns=102,
        published_ts_ns=103,
        source="QUOTE-METRICS",
        revision=1,
    )
    return {value.metric_id: value for value in values}


def test_catalog_requires_explicit_resource_policy() -> None:
    definitions = quote_metric_definitions(
        QuoteMetricCatalogPolicy(
            minimum_update_interval_ms=250,
            maximum_output_age_ms=10_000,
        ),
    )

    assert tuple(item.metric_id for item in definitions) == (
        QUOTE_MIDPOINT_METRIC_ID,
        QUOTE_ABSOLUTE_SPREAD_METRIC_ID,
        QUOTE_RELATIVE_SPREAD_METRIC_ID,
    )
    assert all(item.parameters == () for item in definitions)
    assert all(item.resources.minimum_update_interval_ms == 250 for item in definitions)
    assert all(item.resources.maximum_output_age_ms == 10_000 for item in definitions)
    assert all(item.acquisition_capability() is not None for item in definitions)


@pytest.mark.parametrize(
    ("minimum_update_interval_ms", "maximum_output_age_ms", "message"),
    [
        (-1, 5_000, "minimum_update_interval_ms"),
        (0, 0, "maximum_output_age_ms"),
    ],
)
def test_catalog_policy_rejects_invalid_bounds(
    minimum_update_interval_ms: int,
    maximum_output_age_ms: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        QuoteMetricCatalogPolicy(minimum_update_interval_ms, maximum_output_age_ms)


def test_healthy_two_sided_quote_produces_exact_decimal_metrics() -> None:
    values = _calculate(_quote())

    midpoint = values[QUOTE_MIDPOINT_METRIC_ID]
    spread = values[QUOTE_ABSOLUTE_SPREAD_METRIC_ID]
    relative = values[QUOTE_RELATIVE_SPREAD_METRIC_ID]
    assert midpoint.value == Decimal("7520.125")
    assert spread.value == Decimal("0.25")
    assert relative.value == Decimal("0.25") / Decimal("7520.125")
    assert all(value.health is MetricHealth.READY for value in values.values())
    assert all(value.fidelity is MetricFidelity.DERIVED for value in values.values())
    assert all(value.evidence_refs == ("quote:ESU6.CME:100",) for value in values.values())
    assert all(value.missing_reasons == () for value in values.values())


def test_locked_quote_is_valid_and_has_zero_spread() -> None:
    values = _calculate(_quote(bid=Decimal("10.25"), ask=Decimal("10.25")))

    assert values[QUOTE_MIDPOINT_METRIC_ID].value == Decimal("10.25")
    assert values[QUOTE_ABSOLUTE_SPREAD_METRIC_ID].value == Decimal(0)
    assert values[QUOTE_RELATIVE_SPREAD_METRIC_ID].value == Decimal(0)


def test_degraded_but_usable_evidence_carries_partial_fidelity() -> None:
    values = _calculate(_quote(evidence_state="DEGRADED"))

    assert all(value.value is not None for value in values.values())
    assert all(value.health is MetricHealth.DEGRADED for value in values.values())
    assert all(value.fidelity is MetricFidelity.PARTIAL for value in values.values())


@pytest.mark.parametrize(
    ("state", "health"),
    [
        ("NOT_EVALUATED", MetricHealth.WARMING),
        ("DORMANT", MetricHealth.UNAVAILABLE),
        ("STALE", MetricHealth.STALE),
        ("UNAVAILABLE", MetricHealth.UNAVAILABLE),
        ("UNSUPPORTED", MetricHealth.UNSUPPORTED),
    ],
)
def test_unusable_evidence_emits_explained_nulls(state: str, health: MetricHealth) -> None:
    values = _calculate(_quote(evidence_state=state))

    assert all(value.value is None for value in values.values())
    assert all(value.health is health for value in values.values())
    assert all(value.fidelity is MetricFidelity.UNAVAILABLE for value in values.values())
    assert all(value.missing_reasons == (f"evidence_{state.lower()}",) for value in values.values())


def test_unusable_evidence_preserves_quote_completeness_reasons() -> None:
    values = _calculate(_quote(bid=None, evidence_state="STALE"))

    assert all(
        value.missing_reasons == ("evidence_stale", "bid_missing")
        for value in values.values()
    )


@pytest.mark.parametrize(
    ("bid", "ask", "reason"),
    [
        (None, Decimal("10.25"), "bid_missing"),
        (Decimal("10.00"), None, "ask_missing"),
        (Decimal("NaN"), Decimal("10.25"), "bid_non_finite"),
        (Decimal("10.00"), Decimal("Infinity"), "ask_non_finite"),
        (Decimal("0"), Decimal("10.25"), "bid_non_positive"),
        (Decimal("10.00"), Decimal("0"), "ask_non_positive"),
        (Decimal("10.50"), Decimal("10.25"), "crossed_quote"),
    ],
)
def test_invalid_quote_emits_failed_explained_nulls(
    bid: Decimal | None,
    ask: Decimal | None,
    reason: str,
) -> None:
    values = _calculate(_quote(bid=bid, ask=ask))

    assert all(value.value is None for value in values.values())
    assert all(value.health is MetricHealth.FAILED for value in values.values())
    assert all(value.fidelity is MetricFidelity.PARTIAL for value in values.values())
    assert all(value.missing_reasons == (reason,) for value in values.values())


def test_quote_input_rejects_processing_time_before_event_time() -> None:
    with pytest.raises(ValueError, match="cannot precede"):
        QuoteMetricInput(
            instrument_id="ESU6.CME",
            bid=Decimal("10"),
            ask=Decimal("10.25"),
            observed_ts_ns=101,
            received_ts_ns=100,
            session_id=None,
            evidence_state="HEALTHY",
            evidence_ref="quote:ESU6.CME:101",
        )


def test_calculation_rejects_processing_timestamp_regression() -> None:
    with pytest.raises(ValueError, match="observed <= received <= calculated <= published"):
        calculate_quote_metrics(
            _quote(),
            registry=_registry(),
            parameter_version=1,
            calculated_ts_ns=99,
            published_ts_ns=103,
            source="QUOTE-METRICS",
            revision=1,
        )
