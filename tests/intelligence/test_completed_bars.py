from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from markeitech.intelligence.completed_bars import (
    BarAdmissionStatus,
    CompletedBarInput,
    CompletedBarLedger,
    CompletedBarSource,
    aggregate_completed_bars,
)
from markeitech.intelligence.metrics import MetricFidelity, MetricHealth

SECOND_NS = 1_000_000_000


def _bar(
    index: int = 0,
    *,
    source: CompletedBarSource = CompletedBarSource.LIVE_NATIVE,
    volume: Decimal | None = Decimal("10"),
) -> CompletedBarInput:
    start_ns = index * 5 * SECOND_NS
    missing_reasons = () if volume is not None else ("volume_unsupported",)
    return CompletedBarInput(
        instrument_id="ESU6.CME",
        bar_specification="5-SECOND-LAST-EXTERNAL",
        calendar_id="cme_equity",
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        trade_date=date(2026, 8, 19),
        session_id="cme_equity:2026-08-19:OPEN",
        window_id="primary",
        interval_start_ns=start_ns,
        interval_end_ns=start_ns + 5 * SECOND_NS,
        open=Decimal("100") + index,
        high=Decimal("101") + index,
        low=Decimal("99") + index,
        close=Decimal("100.5") + index,
        volume=volume,
        source=source,
        observed_ts_ns=start_ns + 5 * SECOND_NS,
        received_ts_ns=start_ns + 5 * SECOND_NS + 1,
        normalized_ts_ns=start_ns + 5 * SECOND_NS + 2,
        health=MetricHealth.READY,
        fidelity=MetricFidelity.REPORTED,
        evidence_refs=(f"bar:{index}",),
        complete=True,
        missing_reasons=missing_reasons,
    )


def test_completed_bar_rejects_invalid_prices_timestamps_and_unexplained_volume() -> None:
    with pytest.raises(ValueError, match="low <= open/close <= high"):
        replace(_bar(), low=Decimal("101"))
    with pytest.raises(ValueError, match="observed <= received <= normalized"):
        replace(_bar(), received_ts_ns=1, normalized_ts_ns=0)
    with pytest.raises(ValueError, match="report why volume"):
        replace(_bar(), volume=None)


def test_aggregation_builds_exact_completed_interval_with_lineage() -> None:
    bars = tuple(_bar(index) for index in range(12))

    result = aggregate_completed_bars(
        bars,
        target_bar_specification="1-MINUTE-LAST-EXTERNAL",
        target_interval_seconds=60,
        normalized_ts_ns=61 * SECOND_NS,
    )

    assert result.interval_start_ns == 0
    assert result.interval_end_ns == 60 * SECOND_NS
    assert result.open == Decimal("100")
    assert result.high == Decimal("112")
    assert result.low == Decimal("99")
    assert result.close == Decimal("111.5")
    assert result.volume == Decimal("120")
    assert result.source is CompletedBarSource.LIVE_AGGREGATE
    assert result.fidelity is MetricFidelity.DERIVED
    assert result.evidence_refs == tuple(f"bar:{index}" for index in range(12))


def test_aggregation_requires_one_contiguous_bucket_and_preserves_missing_volume() -> None:
    bars = tuple(_bar(index) for index in range(12))
    with pytest.raises(ValueError, match="contiguous"):
        aggregate_completed_bars(
            bars[:5] + bars[6:],
            target_bar_specification="1-MINUTE-LAST-EXTERNAL",
            target_interval_seconds=60,
            normalized_ts_ns=61 * SECOND_NS,
        )

    with pytest.raises(ValueError, match="share analytical identity"):
        aggregate_completed_bars(
            (bars[0], replace(bars[1], bar_specification="10-SECOND-LAST-EXTERNAL")),
            target_bar_specification="1-MINUTE-LAST-EXTERNAL",
            target_interval_seconds=60,
            normalized_ts_ns=61 * SECOND_NS,
            require_full_coverage=False,
        )

    result = aggregate_completed_bars(
        tuple(_bar(index, volume=None) for index in range(12)),
        target_bar_specification="1-MINUTE-LAST-EXTERNAL",
        target_interval_seconds=60,
        normalized_ts_ns=61 * SECOND_NS,
    )

    assert result.volume is None
    assert result.missing_reasons == ("volume_unsupported",)


def test_ledger_is_idempotent_rejects_conflicts_and_retains_a_bound() -> None:
    ledger = CompletedBarLedger(maximum_observations=2)
    first = _bar(0)

    assert ledger.admit(first).status is BarAdmissionStatus.ACCEPTED
    assert ledger.admit(first).status is BarAdmissionStatus.DUPLICATE

    historical_copy = replace(
        first,
        source=CompletedBarSource.HISTORICAL_PROVIDER,
        received_ts_ns=first.received_ts_ns + 10,
        normalized_ts_ns=first.normalized_ts_ns + 10,
        health=MetricHealth.DEGRADED,
        fidelity=MetricFidelity.PARTIAL,
        evidence_refs=("historical:0",),
    )
    assert ledger.admit(historical_copy).status is BarAdmissionStatus.DUPLICATE

    conflict = replace(first, close=Decimal("100.75"))
    admission = ledger.admit(conflict)
    assert admission.status is BarAdmissionStatus.CONFLICT
    assert admission.accepted == first

    ledger.admit(_bar(1))
    ledger.admit(_bar(2))
    assert tuple(bar.interval_end_ns for bar in ledger.bars) == (
        10 * SECOND_NS,
        15 * SECOND_NS,
    )
