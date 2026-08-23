from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from markeitech.acquisition import HistoricalWindow
from markeitech.intelligence.completed_bars import CompletedBarInput, CompletedBarSource
from markeitech.intelligence.entity_measurements import (
    BAR_VOLUME_ALLOCATED_VOLUME_METRIC_ID,
    EMA_REFERENCE_SLOPE_METRIC_ID,
    ENTITY_PREREQUISITE_METRIC_IDS,
    FVG_FILL_RATIO_METRIC_ID,
    BarVolumeAllocationPolicy,
    EmaReferencePolicy,
    EntityPrerequisiteCatalogPolicy,
    FvgDirection,
    FvgGeometryPolicy,
    SwingGeometryPolicy,
    SwingKind,
    allocate_bar_volume_to_bins,
    calculate_directional_prerequisites,
    calculate_ema_reference,
    detect_confirmed_swings,
    detect_fvg_geometries,
    entity_prerequisite_metric_definitions,
)
from markeitech.intelligence.metrics import MetricFidelity, MetricHealth, MetricRegistry
from markeitech.intelligence.session_measurements import (
    CompletedBarCatalogPolicy,
    completed_bar_metric_definitions,
)


def _catalog_policy() -> EntityPrerequisiteCatalogPolicy:
    return EntityPrerequisiteCatalogPolicy(
        parameter_source="operator-reviewed-config",
        priority=50,
        maximum_retained_observations=2_000,
        maximum_output_age_ms=120_000,
    )


def _completed_bar_policy() -> CompletedBarCatalogPolicy:
    return CompletedBarCatalogPolicy(
        live_selector="5-SECOND-LAST-EXTERNAL",
        historical_selector="1-MINUTE-LAST-EXTERNAL",
        historical_window=HistoricalWindow.RECENT_COMPLETED,
        minimum_historical_observations=2,
        maximum_historical_observations=500,
        calculation_interval_seconds=60,
        minimum_interval_seconds=5,
        maximum_interval_seconds=3_600,
        interval_step_seconds=5,
        interval_dynamic=True,
        aggregation_boundary_policy="utc_fixed_intraday",
        revision_policy="reject_revision",
        parameter_source="operator-reviewed-config",
        priority=40,
        maximum_retained_observations=2_000,
        maximum_output_age_ms=120_000,
    )


def _ema_policy(**changes: object) -> EmaReferencePolicy:
    values = {
        "period": 3,
        "minimum_period": 2,
        "maximum_period": 10,
        "period_step": 1,
        "period_dynamic": True,
        "slope_lookback_bars": 2,
        "minimum_slope_lookback_bars": 1,
        "maximum_slope_lookback_bars": 5,
        "slope_lookback_step": 1,
        "slope_lookback_dynamic": True,
        "price_source": "close",
    }
    values.update(changes)
    return EmaReferencePolicy(**values)  # type: ignore[arg-type]


def _swing_policy(**changes: object) -> SwingGeometryPolicy:
    values = {
        "left_span_bars": 1,
        "minimum_left_span_bars": 1,
        "maximum_left_span_bars": 5,
        "left_span_step": 1,
        "left_span_dynamic": True,
        "right_span_bars": 1,
        "minimum_right_span_bars": 1,
        "maximum_right_span_bars": 5,
        "right_span_step": 1,
        "right_span_dynamic": True,
        "minimum_prominence": Decimal("0.5"),
        "minimum_prominence_floor": Decimal("0"),
        "minimum_prominence_ceiling": Decimal("5"),
        "minimum_prominence_step": Decimal("0.25"),
        "minimum_prominence_dynamic": True,
        "tie_policy": "reject_ties",
    }
    values.update(changes)
    return SwingGeometryPolicy(**values)  # type: ignore[arg-type]


def _fvg_policy(**changes: object) -> FvgGeometryPolicy:
    values = {
        "pattern_length": 3,
        "minimum_width": Decimal("1"),
        "minimum_width_floor": Decimal("0"),
        "minimum_width_ceiling": Decimal("5"),
        "minimum_width_step": Decimal("0.25"),
        "minimum_width_dynamic": True,
        "price_basis": "wick",
        "fill_method": "wick_penetration",
    }
    values.update(changes)
    return FvgGeometryPolicy(**values)  # type: ignore[arg-type]


def _volume_policy(**changes: object) -> BarVolumeAllocationPolicy:
    values = {
        "bin_width": Decimal("1"),
        "minimum_bin_width": Decimal("0.5"),
        "maximum_bin_width": Decimal("5"),
        "bin_width_step": Decimal("0.5"),
        "bin_width_dynamic": True,
        "minimum_coverage_ratio": Decimal("0.75"),
        "minimum_coverage_ratio_floor": Decimal("0"),
        "minimum_coverage_ratio_ceiling": Decimal("1"),
        "minimum_coverage_ratio_step": Decimal("0.05"),
        "minimum_coverage_ratio_dynamic": True,
        "allocation_method": "uniform_intersection",
    }
    values.update(changes)
    return BarVolumeAllocationPolicy(**values)  # type: ignore[arg-type]


def _definitions():
    return entity_prerequisite_metric_definitions(
        _catalog_policy(),
        reference=_ema_policy(),
        swing=_swing_policy(),
        fvg=_fvg_policy(),
        bar_volume=_volume_policy(),
    )


def _bar(
    index: int,
    *,
    open_: str = "100",
    high: str = "101",
    low: str = "99",
    close: str = "100",
    volume: str | None = "10",
    source: CompletedBarSource = CompletedBarSource.HISTORICAL_PROVIDER,
    health: MetricHealth = MetricHealth.READY,
) -> CompletedBarInput:
    start_ns = index * 60_000_000_000
    missing_reasons = () if volume is not None else ("volume_unsupported",)
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
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal(volume) if volume is not None else None,
        source=source,
        observed_ts_ns=start_ns + 60_000_000_000,
        received_ts_ns=start_ns + 60_000_000_001,
        normalized_ts_ns=start_ns + 60_000_000_001,
        health=health,
        fidelity=MetricFidelity.REPORTED,
        evidence_refs=(f"{source.value}:bar:{index}",),
        complete=True,
        missing_reasons=missing_reasons,
    )


def test_prerequisite_catalog_registers_exact_completed_bar_dependencies() -> None:
    definitions = _definitions()
    registry = MetricRegistry(
        (*completed_bar_metric_definitions(_completed_bar_policy()), *definitions)
    )

    assert tuple(item.metric_id for item in definitions) == ENTITY_PREREQUISITE_METRIC_IDS
    slope = registry.get(EMA_REFERENCE_SLOPE_METRIC_ID, 1)
    assert slope.parameters[0].dynamic is True
    assert slope.warmup.minimum_observations == 5
    volume = registry.get(BAR_VOLUME_ALLOCATED_VOLUME_METRIC_ID, 1)
    assert volume.fidelity is MetricFidelity.INFERRED
    assert tuple(item.metric_id for item in volume.metric_inputs) == (
        "completed_bar.high",
        "completed_bar.low",
        "completed_bar.volume",
    )
    assert registry.get(FVG_FILL_RATIO_METRIC_ID, 1).formula == (
        "wick penetration / original gap width"
    )


def test_directional_prerequisites_preserve_sign_and_missing_path() -> None:
    rising = (
        _bar(0, close="100"),
        _bar(1, close="102", high="103"),
        _bar(2, close="101", high="102", low="100"),
    )

    result = calculate_directional_prerequisites(rising)

    assert result.signed_displacement == Decimal("1")
    assert result.signed_simple_return == Decimal("0.01")
    assert result.signed_path_efficiency == Decimal("1") / Decimal("3")
    assert result.health is MetricHealth.READY
    assert result.fidelity is MetricFidelity.DERIVED

    flat = calculate_directional_prerequisites((_bar(0), _bar(1)))
    assert flat.signed_path_efficiency is None
    assert flat.missing_reasons == ("zero_directional_path",)


def test_ema_reference_has_explicit_warmup_value_slope_and_separation() -> None:
    policy = _ema_policy()
    warming = calculate_ema_reference((_bar(0), _bar(1)), policy)

    assert warming.value is None
    assert warming.health is MetricHealth.WARMING
    assert warming.missing_reasons == ("ema_warmup_observations_insufficient",)

    bars = tuple(
        _bar(
            index,
            open_=str(close),
            close=str(close),
            high=str(close + 1),
            low=str(close - 1),
        )
        for index, close in enumerate((100, 102, 104, 106, 108))
    )
    ready = calculate_ema_reference(bars, policy)

    assert ready.value == Decimal("106")
    assert ready.slope_per_bar == Decimal("2")
    assert ready.price_separation == Decimal("2")
    assert ready.health is MetricHealth.READY


def test_swing_requires_right_span_and_rejects_tied_pivots() -> None:
    policy = _swing_policy()
    bars = (
        _bar(0, open_="100", high="101", low="99", close="100"),
        _bar(1, open_="101", high="105", low="100", close="102"),
        _bar(2, open_="102", high="102", low="99", close="100"),
    )

    assert detect_confirmed_swings(bars[:2], policy) == ()
    swings = detect_confirmed_swings(bars, policy)
    high = next(item for item in swings if item.kind is SwingKind.HIGH)
    assert high.pivot_price == Decimal("105")
    assert high.prominence == Decimal("3")
    assert high.confirmation_ts_ns == bars[2].interval_end_ns

    tied = replace(bars[2], high=Decimal("105"), close=Decimal("103"))
    assert not any(
        item.kind is SwingKind.HIGH for item in detect_confirmed_swings((*bars[:2], tied), policy)
    )


def test_fvg_geometry_tracks_wick_bounds_and_later_fill() -> None:
    bars = (
        _bar(0, open_="100", high="101", low="99", close="100"),
        _bar(1, open_="101", high="103", low="100", close="102"),
        _bar(2, open_="102.5", high="104", low="102.5", close="103"),
        _bar(3, open_="102", high="103", low="101.75", close="102"),
    )

    fvgs = detect_fvg_geometries(bars, _fvg_policy())
    bullish = next(
        item
        for item in fvgs
        if item.direction is FvgDirection.BULLISH and item.lower_bound == Decimal("101")
    )

    assert bullish.upper_bound == Decimal("102.5")
    assert bullish.width == Decimal("1.5")
    assert bullish.fill_ratio == Decimal("0.5")
    assert bullish.formation_ts_ns == bars[2].interval_end_ns

    bearish_bars = (
        _bar(0, open_="106", high="107", low="105", close="106"),
        _bar(1, open_="105", high="106", low="102", close="103"),
        _bar(2, open_="103", high="103.5", low="101", close="102"),
        _bar(3, open_="104", high="104.25", low="102", close="103"),
    )
    bearish = next(
        item
        for item in detect_fvg_geometries(bearish_bars, _fvg_policy())
        if item.direction is FvgDirection.BEARISH and item.lower_bound == Decimal("103.5")
    )
    assert bearish.upper_bound == Decimal("105")
    assert bearish.fill_ratio == Decimal("0.5")


def test_bar_volume_allocation_conserves_volume_and_reports_coverage() -> None:
    bars = (
        _bar(0, open_="101", high="102.5", low="100.5", close="102", volume="100"),
        _bar(1, open_="103", high="103", low="103", close="103", volume="10"),
    )

    result = allocate_bar_volume_to_bins(bars, _volume_policy())

    assert result.input_volume == Decimal("110")
    assert result.allocated_volume == Decimal("110")
    assert result.coverage_ratio == Decimal("1")
    assert {item.lower_bound: item.estimated_volume for item in result.bins} == {
        Decimal("100"): Decimal("25"),
        Decimal("101"): Decimal("50"),
        Decimal("102"): Decimal("25"),
        Decimal("103"): Decimal("10"),
    }
    assert result.fidelity is MetricFidelity.INFERRED

    partial = allocate_bar_volume_to_bins(
        (bars[0], replace(bars[1], volume=None, missing_reasons=("volume_partial",))),
        _volume_policy(),
    )
    assert partial.coverage_ratio == Decimal("0.5")
    assert partial.health is MetricHealth.WARMING
    assert partial.fidelity is MetricFidelity.PARTIAL

    sufficient_partial = allocate_bar_volume_to_bins(
        (bars[0], replace(bars[1], volume=None, missing_reasons=("volume_partial",))),
        _volume_policy(minimum_coverage_ratio=Decimal("0.5")),
    )
    assert sufficient_partial.health is MetricHealth.DEGRADED
    assert sufficient_partial.fidelity is MetricFidelity.PARTIAL
    assert sufficient_partial.missing_reasons == ("bar_volume_partial_coverage",)

    unsupported = allocate_bar_volume_to_bins(
        (replace(bars[0], volume=None, missing_reasons=("volume_unsupported",)),),
        _volume_policy(),
    )
    assert unsupported.health is MetricHealth.UNSUPPORTED
    assert unsupported.fidelity is MetricFidelity.UNAVAILABLE


def test_historical_and_live_bars_converge_numerically() -> None:
    historical = tuple(
        _bar(
            index,
            open_=str(close),
            close=str(close),
            high=str(close + 1),
            low=str(close - 1),
        )
        for index, close in enumerate((100, 101, 103, 102, 105))
    )
    live = tuple(
        replace(
            item,
            source=CompletedBarSource.LIVE_NATIVE,
            evidence_refs=(f"live:bar:{index}",),
        )
        for index, item in enumerate(historical)
    )

    assert calculate_directional_prerequisites(historical).signed_path_efficiency == (
        calculate_directional_prerequisites(live).signed_path_efficiency
    )
    assert calculate_ema_reference(historical, _ema_policy()).value == (
        calculate_ema_reference(live, _ema_policy()).value
    )
    assert [
        (item.direction, item.lower_bound, item.upper_bound, item.fill_ratio)
        for item in detect_fvg_geometries(historical, _fvg_policy())
    ] == [
        (item.direction, item.lower_bound, item.upper_bound, item.fill_ratio)
        for item in detect_fvg_geometries(live, _fvg_policy())
    ]


def test_prerequisite_policy_envelopes_reject_invalid_values() -> None:
    with pytest.raises(ValueError, match="align"):
        _ema_policy(period=4, minimum_period=3, period_step=2)
    with pytest.raises(ValueError, match="align"):
        _fvg_policy(minimum_width=Decimal("0.3"), minimum_width_step=Decimal("0.25"))
    with pytest.raises(ValueError, match="close price only"):
        _ema_policy(price_source="typical")
