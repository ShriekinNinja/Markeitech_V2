from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from markeitech.acquisition import HistoricalWindow
from markeitech.intelligence import (
    CompletedBarInput,
    CompletedBarSource,
    MetricFidelity,
    MetricHealth,
    MetricRegistry,
    ParameterMutability,
)
from markeitech.intelligence.session import CalendarProjectionView
from markeitech.intelligence.session_measurements import (
    COMPLETED_BAR_CLOSE_METRIC_ID,
    COMPLETED_BAR_METRIC_IDS,
    COMPLETED_BAR_SIMPLE_RETURN_METRIC_ID,
    COMPLETED_BAR_TRUE_RANGE_METRIC_ID,
    COMPLETED_BAR_VOLUME_METRIC_ID,
    CompletedBarCatalogPolicy,
    calculate_completed_bar_metrics,
    completed_bar_metric_definitions,
)
from markeitech.intelligence.session_metric_actor import (
    _active_reference_attempt_ns,
    _recalculation_contexts,
)
from tests.calendar_fixtures import projection_view


def _us_equities_calendar() -> CalendarProjectionView:
    return projection_view("us_equities")


def _timestamp_ns(value: str) -> int:
    return int(datetime.fromisoformat(value).astimezone(UTC).timestamp() * 1_000_000_000)


def test_active_reference_waits_for_first_completed_selector_interval() -> None:
    attempt_ns = _active_reference_attempt_ns(
        _us_equities_calendar(),
        "EXCHANGE_SESSION",
        _timestamp_ns("2026-08-21T09:31:34-04:00"),
        15 * 60 * 1_000_000_000,
    )

    assert attempt_ns == _timestamp_ns("2026-08-21T09:45:00-04:00") + 1_000_000


def test_active_reference_is_immediately_eligible_after_completed_interval() -> None:
    now_ns = _timestamp_ns("2026-08-21T09:46:00-04:00")

    assert (
        _active_reference_attempt_ns(
            _us_equities_calendar(),
            "EXCHANGE_SESSION",
            now_ns,
            15 * 60 * 1_000_000_000,
        )
        == now_ns
    )


def test_primary_globex_reference_remains_eligible_during_overlapping_region_phase() -> None:
    now_ns = _timestamp_ns("2026-08-24T10:00:00-04:00")

    assert (
        _active_reference_attempt_ns(
            projection_view("cme_equity", date(2026, 8, 24), date(2026, 8, 24)),
            "GLOBEX",
            now_ns,
            15 * 60 * 1_000_000_000,
        )
        == now_ns
    )


def test_active_reference_is_not_scheduled_outside_primary_phase() -> None:
    assert (
        _active_reference_attempt_ns(
            _us_equities_calendar(),
            "EXCHANGE_SESSION",
            _timestamp_ns("2026-08-21T08:00:00-04:00"),
            15 * 60 * 1_000_000_000,
        )
        is None
    )


def _policy(**changes: object) -> CompletedBarCatalogPolicy:
    values = {
        "live_selector": "5-SECOND-LAST-EXTERNAL",
        "historical_selector": "1-MINUTE-LAST-EXTERNAL",
        "historical_window": HistoricalWindow.RECENT_COMPLETED,
        "minimum_historical_observations": 2,
        "maximum_historical_observations": 4,
        "calculation_interval_seconds": 60,
        "minimum_interval_seconds": 5,
        "maximum_interval_seconds": 3600,
        "interval_step_seconds": 5,
        "interval_dynamic": True,
        "aggregation_boundary_policy": "utc_fixed_intraday",
        "revision_policy": "reject_revision",
        "parameter_source": "operator-reviewed-config",
        "priority": 40,
        "maximum_retained_observations": 2000,
        "maximum_output_age_ms": 120_000,
    }
    values.update(changes)
    return CompletedBarCatalogPolicy(**values)  # type: ignore[arg-type]


def test_completed_bar_catalog_declares_exact_configured_dependencies() -> None:
    definitions = completed_bar_metric_definitions(_policy())
    registry = MetricRegistry(definitions)

    assert tuple(definition.metric_id for definition in definitions) == COMPLETED_BAR_METRIC_IDS
    volume = registry.get(COMPLETED_BAR_VOLUME_METRIC_ID, 1)
    assert volume.live_inputs[0].selector == "5-SECOND-LAST-EXTERNAL"
    assert volume.historical_inputs[0].selector == "1-MINUTE-LAST-EXTERNAL"
    assert volume.historical_inputs[0].window is HistoricalWindow.RECENT_COMPLETED
    assert volume.historical_inputs[0].parameters == {
        "aggregation_boundary_policy": "utc_fixed_intraday",
        "calculation_interval_seconds": 60,
        "purpose": "completed_bar_foundation",
        "revision_policy": "reject_revision",
    }
    assert volume.formula == "completed_bar.volume"
    assert volume.normalization == "none"
    assert volume.priority == 40
    assert volume.allowed_fidelities == (
        volume.fidelity.__class__.REPORTED,
        volume.fidelity.__class__.DERIVED,
        volume.fidelity.__class__.PARTIAL,
        volume.fidelity.__class__.UNAVAILABLE,
    )
    assert volume.parameters[0].dynamic is True
    assert volume.parameters[0].mutability is ParameterMutability.POLICY_CONTROLLED_RUNTIME
    assert registry.get(COMPLETED_BAR_SIMPLE_RETURN_METRIC_ID, 1).warmup.minimum_observations == 2


def test_completed_bar_catalog_keeps_resolution_policy_configurable() -> None:
    definitions = completed_bar_metric_definitions(
        _policy(
            live_selector="1-MINUTE-LAST-EXTERNAL",
            historical_selector="1-HOUR-LAST-EXTERNAL",
            calculation_interval_seconds=3600,
            interval_dynamic=False,
        ),
    )

    definition = definitions[0]
    assert definition.live_inputs[0].selector == "1-MINUTE-LAST-EXTERNAL"
    assert definition.historical_inputs[0].selector == "1-HOUR-LAST-EXTERNAL"
    assert definition.parameters[0].default == 3600
    assert definition.parameters[0].mutability is ParameterMutability.STARTUP_ONLY


def test_completed_bar_catalog_rejects_invalid_resolution_envelopes() -> None:
    with pytest.raises(ValueError, match="inside its configured envelope"):
        _policy(calculation_interval_seconds=1)
    with pytest.raises(ValueError, match="align"):
        _policy(calculation_interval_seconds=62)
    with pytest.raises(ValueError, match="divide one UTC day"):
        _policy(
            calculation_interval_seconds=70,
            minimum_interval_seconds=10,
            interval_step_seconds=10,
        )
    with pytest.raises(ValueError, match="reject_revision"):
        _policy(revision_policy="replace")


def test_calculates_foundation_values_with_explicit_warmup() -> None:
    registry = MetricRegistry(completed_bar_metric_definitions(_policy()))
    first = _bar(0, close="100")

    warming = calculate_completed_bar_metrics(
        first,
        prior_bar=None,
        registry=registry,
        parameter_version=3,
        calculated_ts_ns=61_000_000_001,
        published_ts_ns=61_000_000_001,
        source="SESSION-METRICS",
        revision=1,
    )
    by_id = {value.metric_id: value for value in warming}

    assert by_id[COMPLETED_BAR_CLOSE_METRIC_ID].value == Decimal("100")
    assert by_id[COMPLETED_BAR_SIMPLE_RETURN_METRIC_ID].value is None
    assert by_id[COMPLETED_BAR_SIMPLE_RETURN_METRIC_ID].health is MetricHealth.WARMING
    assert by_id[COMPLETED_BAR_TRUE_RANGE_METRIC_ID].missing_reasons == (
        "prior_compatible_close_missing",
    )

    second = _bar(1, close="105", high="107", low="99")
    values = calculate_completed_bar_metrics(
        second,
        prior_bar=first,
        registry=registry,
        parameter_version=3,
        calculated_ts_ns=121_000_000_001,
        published_ts_ns=121_000_000_001,
        source="SESSION-METRICS",
        revision=2,
    )
    by_id = {value.metric_id: value for value in values}

    assert by_id[COMPLETED_BAR_SIMPLE_RETURN_METRIC_ID].value == Decimal("0.05")
    assert by_id[COMPLETED_BAR_TRUE_RANGE_METRIC_ID].value == Decimal("8")
    assert by_id[COMPLETED_BAR_TRUE_RANGE_METRIC_ID].fidelity is MetricFidelity.DERIVED


def test_unsupported_volume_isolated_from_price_metrics() -> None:
    registry = MetricRegistry(completed_bar_metric_definitions(_policy()))
    bar = replace(_bar(0), volume=None, missing_reasons=("volume_unsupported",))

    values = calculate_completed_bar_metrics(
        bar,
        prior_bar=None,
        registry=registry,
        parameter_version=1,
        calculated_ts_ns=61_000_000_001,
        published_ts_ns=61_000_000_001,
        source="SESSION-METRICS",
        revision=1,
    )
    by_id = {value.metric_id: value for value in values}

    assert by_id[COMPLETED_BAR_VOLUME_METRIC_ID].health is MetricHealth.UNSUPPORTED
    assert by_id[COMPLETED_BAR_VOLUME_METRIC_ID].value is None
    assert by_id[COMPLETED_BAR_CLOSE_METRIC_ID].health is MetricHealth.READY


def test_late_predecessor_recalculates_successor_without_sequencing() -> None:
    first = _bar(0, close="100")
    second = _bar(1, close="105", high="106")

    live_first = _recalculation_contexts((second,), second.key)
    after_warmup = _recalculation_contexts((first, second), first.key)

    assert live_first == ((second, None),)
    assert after_warmup == ((first, None), (second, first))


def _bar(
    index: int,
    *,
    close: str = "100",
    high: str = "101",
    low: str = "99",
) -> CompletedBarInput:
    start_ns = index * 60_000_000_000
    return CompletedBarInput(
        instrument_id="ESU6.CME",
        bar_specification="1-MINUTE-LAST-EXTERNAL",
        calendar_id="cme_equity",
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        trade_date=date(2026, 8, 21),
        session_id="cme_equity:2026-08-21:OPEN",
        window_id="primary",
        interval_start_ns=start_ns,
        interval_end_ns=start_ns + 60_000_000_000,
        open=Decimal("100"),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("10"),
        source=CompletedBarSource.HISTORICAL_PROVIDER,
        observed_ts_ns=start_ns + 60_000_000_000,
        received_ts_ns=start_ns + 60_000_000_001,
        normalized_ts_ns=start_ns + 60_000_000_001,
        health=MetricHealth.READY,
        fidelity=MetricFidelity.REPORTED,
        evidence_refs=(f"bar:{index}",),
        complete=True,
    )
