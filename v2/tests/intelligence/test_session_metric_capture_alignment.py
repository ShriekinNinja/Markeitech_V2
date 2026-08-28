from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from markeitech.acquisition import (
    HISTORICAL_DEPENDENCY_DEMAND_SIGNAL,
    HistoricalDependencyCompiler,
    HistoricalDependencyDemandEvent,
    HistoricalResourcePolicy,
)
from markeitech.intelligence.completed_bars import CompletedBarInput, CompletedBarSource
from markeitech.intelligence.metrics import MetricFidelity, MetricHealth
from markeitech.intelligence.session_metric_actor import (
    SessionMetricsActor,
    SessionMetricsActorConfig,
    _completed_bar_foundation_historical_demand,
)
from markeitech.system.acquisition import _compile_historical_demand
from markeitech.system.composition import StartupPrerequisites, build_actor_plan
from markeitech.system.config import load_system_config

_MINUTE_NS = 60_000_000_000
_BASE_NS = 1_777_286_400_000_000_000


@pytest.mark.parametrize("startup_offset_seconds", [0, 1, 25, 59])
def test_visual_review_defers_one_history_demand_to_first_complete_live_boundary(
    startup_offset_seconds: int,
) -> None:
    actor = _v3_session_metrics_actor()
    published: list[tuple[str, str]] = []
    actor.publish_signal = lambda name, value: published.append((name, value))
    first_full_start_ns = _BASE_NS + (
        (10 if startup_offset_seconds == 0 else 11) * _MINUTE_NS
    )
    bar = _live_aggregate(first_full_start_ns)

    actor._publish_capture_aligned_foundation_history(bar)
    actor._publish_capture_aligned_foundation_history(bar)

    assert len(published) == 1
    assert published[0][0] == HISTORICAL_DEPENDENCY_DEMAND_SIGNAL
    demand = HistoricalDependencyDemandEvent.from_signal_value(published[0][1])
    assert demand.as_of_ns == first_full_start_ns
    assert demand.maximum_observations == 55
    assert demand.parameters == {
        "calculation_interval_seconds": 60,
        "capture_aligned": True,
        "capture_alignment_interval_start_ns": first_full_start_ns,
        "parameter_version": 1,
    }
    request = _compile_historical_demand(
        demand,
        HistoricalDependencyCompiler(HistoricalResourcePolicy(1, 55, 55)),
    )
    assert request.start_ns == first_full_start_ns - 55 * _MINUTE_NS
    assert request.end_ns == first_full_start_ns - 1
    assert request.limit == 55
    assert actor._counts["foundation_history_demands"] == 1
    assert actor._counts["capture_aligned_history_demands"] == 1


def test_visual_review_does_not_align_history_to_non_aggregate_live_input() -> None:
    actor = _v3_session_metrics_actor()
    published: list[tuple[str, str]] = []
    actor.publish_signal = lambda name, value: published.append((name, value))
    native = _live_aggregate(10 * _MINUTE_NS)
    native = replace(native, source=CompletedBarSource.LIVE_NATIVE)

    actor._publish_capture_aligned_foundation_history(native)

    assert published == []
    assert actor._foundation_history_requested == set()


def test_ordinary_foundation_history_demand_remains_immediate_and_unaligned() -> None:
    demand = _completed_bar_foundation_historical_demand(
        demand_id="session-metrics:ESU6.CME:completed-bars:v1",
        consumer_id="SESSION-METRICS",
        instrument_id="ESU6.CME",
        selector="1-MINUTE-LAST-EXTERNAL",
        window="recent_completed",
        minimum_observations=2,
        maximum_observations=5,
        priority=40,
        as_of_ns=10 * _MINUTE_NS + 25_000_000_000,
        calculation_interval_seconds=60,
        parameter_version=1,
        capture_aligned=False,
    )

    assert demand.as_of_ns == 10 * _MINUTE_NS + 25_000_000_000
    assert demand.purpose == "warm completed-bar foundation metrics"
    assert demand.parameters == {
        "calculation_interval_seconds": 60,
        "parameter_version": 1,
    }


def _v3_session_metrics_actor() -> SessionMetricsActor:
    system = load_system_config("v2/config/system.v3-es-minimal.toml")
    plan = build_actor_plan(
        system,
        StartupPrerequisites(
            run_id=UUID("00000000-0000-0000-0000-000000000001"),
            operational_persistence_ready=True,
        ),
    )
    registration = next(item for item in plan if item.key == "session_metrics")
    config = SessionMetricsActorConfig(**registration.config.config)
    return SessionMetricsActor(config)


def _live_aggregate(interval_start_ns: int) -> CompletedBarInput:
    interval_end_ns = interval_start_ns + _MINUTE_NS
    return CompletedBarInput(
        instrument_id="ESU6.CME",
        bar_specification="1-MINUTE-LAST-EXTERNAL",
        calendar_id="cme_equity",
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        trade_date=date(2026, 8, 27),
        session_id="cme_equity:2026-08-27:OPEN",
        window_id="primary",
        interval_start_ns=interval_start_ns,
        interval_end_ns=interval_end_ns,
        open=Decimal("7720.00"),
        high=Decimal("7721.00"),
        low=Decimal("7719.75"),
        close=Decimal("7720.50"),
        volume=Decimal("1200"),
        source=CompletedBarSource.LIVE_AGGREGATE,
        observed_ts_ns=interval_end_ns,
        received_ts_ns=interval_end_ns,
        normalized_ts_ns=interval_end_ns,
        health=MetricHealth.READY,
        fidelity=MetricFidelity.DERIVED,
        evidence_refs=("live:test",),
        complete=True,
    )
