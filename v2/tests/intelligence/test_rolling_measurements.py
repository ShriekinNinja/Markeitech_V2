from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

from markeitech.acquisition import HistoricalWindow
from markeitech.intelligence.completed_bars import CompletedBarInput, CompletedBarSource
from markeitech.intelligence.metrics import MetricFidelity, MetricHealth, MetricRegistry
from markeitech.intelligence.rolling_measurements import (
    RollingBaselinePolicy,
    RollingCandidatePolicy,
    RollingFamilyPolicy,
    RollingMeasurementPolicy,
    calculate_rolling_candidates,
    rolling_metric_definitions,
    rolling_metric_id,
    rolling_metric_values,
)
from markeitech.intelligence.session import SessionWindow
from markeitech.intelligence.session_measurements import (
    CompletedBarCatalogPolicy,
    completed_bar_metric_definitions,
)

MINUTE_NS = 60 * 1_000_000_000


def _candidate(candidate_id: str = "context_2m") -> RollingCandidatePolicy:
    return RollingCandidatePolicy(
        candidate_id=candidate_id,
        purpose="context",
        duration_seconds=120,
        minimum_duration_seconds=60,
        maximum_duration_seconds=600,
        duration_step_seconds=60,
        dynamic=True,
        active=True,
    )


def _policy(*, minimum_recent: int = 2, minimum_phase: int = 1) -> RollingMeasurementPolicy:
    candidate = _candidate()
    return RollingMeasurementPolicy(
        enabled=True,
        minimum_coverage_ratio=1.0,
        minimum_coverage_ratio_floor=0.5,
        minimum_coverage_ratio_ceiling=1.0,
        minimum_coverage_ratio_step=0.1,
        minimum_coverage_ratio_dynamic=True,
        maximum_retained_observations=100,
        maximum_output_age_ms=120_000,
        baseline=RollingBaselinePolicy(
            eligible_reference_health=(MetricHealth.READY,),
            eligible_reference_fidelities=(MetricFidelity.REPORTED, MetricFidelity.DERIVED),
            recent_reference_count=2,
            recent_reference_count_minimum=1,
            recent_reference_count_maximum=4,
            recent_reference_count_step=1,
            recent_reference_count_dynamic=True,
            minimum_recent_references=minimum_recent,
            phase_reference_count=1,
            phase_reference_count_minimum=1,
            phase_reference_count_maximum=3,
            phase_reference_count_step=1,
            phase_reference_count_dynamic=True,
            minimum_phase_references=minimum_phase,
        ),
        families=(
            RollingFamilyPolicy(
                family_id="fast",
                source_selector="1-MINUTE-LAST-EXTERNAL",
                input_selector="1-MINUTE-LAST-EXTERNAL",
                input_interval_seconds=60,
                aggregation_policy="identity",
                selected_context_candidate_id=candidate.candidate_id,
                candidates=(candidate,),
            ),
        ),
        parameter_source="test",
        priority=40,
    )


def _bar(index: int, *, session_id: str = "calendar:2026-08-21:OPEN") -> CompletedBarInput:
    close = Decimal(100 + index)
    return CompletedBarInput(
        instrument_id="ESU6.CME",
        bar_specification="1-MINUTE-LAST-EXTERNAL",
        calendar_id="calendar",
        analytical_profile_id="profile",
        analytical_profile_version=1,
        trade_date=date(2026, 8, 21),
        session_id=session_id,
        window_id="primary",
        interval_start_ns=index * MINUTE_NS,
        interval_end_ns=(index + 1) * MINUTE_NS,
        open=close,
        high=close + 1,
        low=close - 1,
        close=close,
        volume=Decimal(10),
        source=CompletedBarSource.HISTORICAL_PROVIDER,
        observed_ts_ns=(index + 1) * MINUTE_NS,
        received_ts_ns=(index + 1) * MINUTE_NS,
        normalized_ts_ns=(index + 1) * MINUTE_NS,
        health=MetricHealth.READY,
        fidelity=MetricFidelity.REPORTED,
        evidence_refs=(f"bar:{index}",),
        complete=True,
    )


def test_recent_equal_duration_baseline_uses_midrank_and_excludes_current() -> None:
    result = calculate_rolling_candidates(
        tuple(_bar(index) for index in range(6)),
        phase_windows=(),
        policy=_policy(),
    )[0]

    assert result.price_range == Decimal(3)
    assert result.realized_log_return_magnitude is not None
    assert result.average_true_range == Decimal(2)
    assert result.directional_efficiency == Decimal(1)
    assert result.coverage_ratio == Decimal(1)
    assert result.recent_reference_count == 2
    assert result.expansion_ratio_recent == Decimal(1)
    assert result.range_percentile_recent == Decimal("0.5")
    assert result.recent_health is MetricHealth.READY
    assert result.phase_health is MetricHealth.WARMING
    assert result.expansion_ratio_phase is None


def test_phase_baseline_matches_authoritative_phase_offset_independently() -> None:
    prior = tuple(_bar(index, session_id="calendar:2026-08-20:OPEN") for index in range(2))
    current = tuple(_bar(index, session_id="calendar:2026-08-21:OPEN") for index in range(10, 12))
    windows = (
        SessionWindow(date(2026, 8, 20), "OPEN", 0, 4 * MINUTE_NS),
        SessionWindow(date(2026, 8, 21), "OPEN", 10 * MINUTE_NS, 14 * MINUTE_NS),
    )

    result = calculate_rolling_candidates(
        (*prior, *current),
        phase_windows=windows,
        policy=_policy(minimum_recent=1),
    )[0]

    assert result.phase_reference_count == 1
    assert result.expansion_ratio_phase == Decimal(1)
    assert result.range_percentile_phase == Decimal("0.5")
    assert result.phase_health is MetricHealth.READY
    assert result.recent_health is MetricHealth.WARMING


def test_recent_baseline_excludes_ineligible_health_without_hiding_current_value() -> None:
    bars = tuple(_bar(index) for index in range(6))
    bars = (*bars[:2], replace(bars[2], health=MetricHealth.DEGRADED), *bars[3:])

    result = calculate_rolling_candidates(
        bars,
        phase_windows=(),
        policy=_policy(),
    )[0]

    assert result.price_range == Decimal(3)
    assert result.current_health is MetricHealth.READY
    assert result.recent_reference_count == 1
    assert result.recent_health is MetricHealth.WARMING
    assert result.expansion_ratio_recent is None


def test_current_window_evidence_reports_session_boundary_composition() -> None:
    bars = tuple(_bar(index) for index in range(6))
    bars = (
        *bars[:5],
        replace(bars[5], session_id="calendar:2026-08-21:AFTER_HOURS"),
    )

    result = calculate_rolling_candidates(
        bars,
        phase_windows=(),
        policy=_policy(),
    )[0]

    assert "rolling-session:calendar:2026-08-21:OPEN" in result.evidence_refs
    assert "rolling-session:calendar:2026-08-21:AFTER_HOURS" in result.evidence_refs
    assert "rolling-boundary-crossing:true" in result.evidence_refs


def test_metric_catalog_and_values_preserve_candidate_and_baseline_identity() -> None:
    policy = _policy()
    completed_policy = CompletedBarCatalogPolicy(
        live_selector="5-SECOND-LAST-EXTERNAL",
        historical_selector="1-MINUTE-LAST-EXTERNAL",
        historical_window=HistoricalWindow.RECENT_COMPLETED,
        minimum_historical_observations=2,
        maximum_historical_observations=10,
        calculation_interval_seconds=60,
        minimum_interval_seconds=5,
        maximum_interval_seconds=3600,
        interval_step_seconds=5,
        interval_dynamic=True,
        aggregation_boundary_policy="utc_fixed_intraday",
        revision_policy="reject_revision",
        parameter_source="test",
        priority=40,
        maximum_retained_observations=100,
        maximum_output_age_ms=120_000,
    )
    registry = MetricRegistry(
        (*completed_bar_metric_definitions(completed_policy), *rolling_metric_definitions(policy)),
    )
    result = calculate_rolling_candidates(
        tuple(_bar(index) for index in range(6)),
        phase_windows=(),
        policy=policy,
    )[0]

    values = rolling_metric_values(
        result,
        registry=registry,
        parameter_version=1,
        calculated_ts_ns=7 * MINUTE_NS,
        published_ts_ns=7 * MINUTE_NS,
        source="TEST",
        revision=1,
    )
    by_id = {value.metric_id: value for value in values}

    assert len(values) == 11
    price_range = by_id[rolling_metric_id("fast", "context_2m", "price_range")]
    assert price_range.instrument_id == "ESU6.CME"
    assert price_range.value == Decimal(3)
    phase_count = by_id[rolling_metric_id("fast", "context_2m", "phase_reference_count")]
    assert phase_count.value == 0
    assert phase_count.health is MetricHealth.WARMING


def test_wider_input_family_aggregates_only_complete_utc_buckets() -> None:
    candidate = RollingCandidatePolicy(
        candidate_id="context_10m",
        purpose="context",
        duration_seconds=600,
        minimum_duration_seconds=300,
        maximum_duration_seconds=1200,
        duration_step_seconds=300,
        dynamic=True,
        active=True,
    )
    policy = _policy()
    policy = RollingMeasurementPolicy(
        enabled=True,
        minimum_coverage_ratio=1.0,
        minimum_coverage_ratio_floor=0.5,
        minimum_coverage_ratio_ceiling=1.0,
        minimum_coverage_ratio_step=0.1,
        minimum_coverage_ratio_dynamic=True,
        maximum_retained_observations=100,
        maximum_output_age_ms=120_000,
        baseline=policy.baseline,
        families=(
            RollingFamilyPolicy(
                family_id="tactical",
                source_selector="1-MINUTE-LAST-EXTERNAL",
                input_selector="5-MINUTE-LAST-EXTERNAL",
                input_interval_seconds=300,
                aggregation_policy="utc_fixed_intraday",
                selected_context_candidate_id=candidate.candidate_id,
                candidates=(candidate,),
            ),
        ),
        parameter_source="test",
        priority=40,
    )

    result = calculate_rolling_candidates(
        tuple(_bar(index) for index in range(10)),
        phase_windows=(),
        policy=policy,
    )[0]

    assert result.coverage_ratio == Decimal(1)
    assert result.price_range == Decimal(11)


def test_wider_input_family_preserves_aggregate_source_lineage() -> None:
    candidate = RollingCandidatePolicy(
        candidate_id="context_5m",
        purpose="context",
        duration_seconds=300,
        minimum_duration_seconds=300,
        maximum_duration_seconds=600,
        duration_step_seconds=300,
        dynamic=True,
        active=True,
    )
    base = _policy(minimum_recent=1)
    policy = RollingMeasurementPolicy(
        enabled=True,
        minimum_coverage_ratio=1.0,
        minimum_coverage_ratio_floor=0.5,
        minimum_coverage_ratio_ceiling=1.0,
        minimum_coverage_ratio_step=0.1,
        minimum_coverage_ratio_dynamic=True,
        maximum_retained_observations=100,
        maximum_output_age_ms=120_000,
        baseline=base.baseline,
        families=(
            RollingFamilyPolicy(
                family_id="tactical",
                source_selector="1-MINUTE-LAST-EXTERNAL",
                input_selector="5-MINUTE-LAST-EXTERNAL",
                input_interval_seconds=300,
                aggregation_policy="utc_fixed_intraday",
                selected_context_candidate_id=candidate.candidate_id,
                candidates=(candidate,),
            ),
        ),
        parameter_source="test",
        priority=40,
    )

    historical = calculate_rolling_candidates(
        tuple(_bar(index) for index in range(5)),
        phase_windows=(),
        policy=policy,
    )[0]
    live_bar = replace(_bar(4), source=CompletedBarSource.LIVE_AGGREGATE)
    mixed = calculate_rolling_candidates(
        (*tuple(_bar(index) for index in range(4)), live_bar),
        phase_windows=(),
        policy=policy,
    )[0]

    assert historical.input_source is CompletedBarSource.HISTORICAL_AGGREGATE
    assert mixed.input_source is CompletedBarSource.LIVE_AGGREGATE
    assert "instrument:ESU6.CME" in historical.evidence_refs
