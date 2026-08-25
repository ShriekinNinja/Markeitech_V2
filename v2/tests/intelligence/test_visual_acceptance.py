from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

from markeitech.intelligence.completed_bars import (
    CompletedBarInput,
    CompletedBarSource,
)
from markeitech.intelligence.metrics import MetricFidelity, MetricHealth, MetricValue
from markeitech.intelligence.session_entities import ObjectiveLevelPayload
from markeitech.intelligence.visual_acceptance import (
    AnnotationExpectation,
    VisualAcceptanceCollector,
)
from markeitech.intelligence.visual_acceptance_plotly import (
    _horizon_figure,
    _objective_label,
    render_visual_acceptance,
)
from markeitech.system.discord import OperationalReadinessSnapshot

SECOND_NS = 1_000_000_000


def _bar(index: int, selector: str = "1-MINUTE-LAST-EXTERNAL") -> CompletedBarInput:
    interval_seconds = int(selector.split("-", maxsplit=1)[0]) * 60
    start_ns = index * interval_seconds * SECOND_NS
    end_ns = start_ns + interval_seconds * SECOND_NS
    return CompletedBarInput(
        instrument_id="ESU6.CME",
        bar_specification=selector,
        calendar_id="cme_equity",
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        trade_date=date(2026, 8, 24),
        session_id="cme_equity:2026-08-24:OPEN",
        window_id="primary",
        interval_start_ns=start_ns,
        interval_end_ns=end_ns,
        open=Decimal("100") + index,
        high=Decimal("101") + index,
        low=Decimal("99") + index,
        close=Decimal("100.5") + index,
        volume=Decimal("10") + index,
        source=CompletedBarSource.LIVE_AGGREGATE,
        observed_ts_ns=end_ns,
        received_ts_ns=end_ns + 1,
        normalized_ts_ns=end_ns + 2,
        health=MetricHealth.READY,
        fidelity=MetricFidelity.DERIVED,
        evidence_refs=(f"bar:{selector}:{index}",),
        complete=True,
    )


def _metric(revision: int = 1) -> MetricValue:
    timestamp = 100 + revision
    return MetricValue(
        metric_id="rolling.fast.context_20m.average_true_range",
        metric_version=1,
        parameter_version=1,
        instrument_id="ESU6.CME",
        session_id="cme_equity:2026-08-24:OPEN",
        value=Decimal("1.25") + revision,
        unit="price",
        effective_ts_ns=timestamp,
        observed_ts_ns=timestamp,
        received_ts_ns=timestamp + 1,
        calculated_ts_ns=timestamp + 2,
        published_ts_ns=timestamp + 3,
        health=MetricHealth.READY,
        fidelity=MetricFidelity.DERIVED,
        source="SESSION-METRICS",
        evidence_refs=(f"metric:{revision}",),
        missing_reasons=(),
        revision=revision,
    )


def _collector(maximum_bars: int = 2) -> VisualAcceptanceCollector:
    return VisualAcceptanceCollector(
        instrument_ids=("ESU6.CME",),
        bar_specifications=(
            "1-MINUTE-LAST-EXTERNAL",
            "5-MINUTE-LAST-EXTERNAL",
            "15-MINUTE-LAST-EXTERNAL",
        ),
        maximum_bars_per_series=maximum_bars,
        maximum_metric_values=2,
        maximum_entity_revisions=2,
    )


def _readiness() -> OperationalReadinessSnapshot:
    return OperationalReadinessSnapshot(
        system_state="READY",
        observed_watchlist_count=1,
        expected_watchlist_count=1,
        historical_state_counts={"READY": 3},
        completed_at_ns=1_000,
    )


def test_collector_retains_bounded_series_and_latest_metric_revision() -> None:
    collector = _collector()

    for index in range(3):
        assert collector.accept_bar(_bar(index)) is True
    assert collector.accept_metric(_metric(1)) is True
    assert collector.accept_metric(_metric(2)) is True
    assert collector.accept_metric(replace(_metric(1), revision=1)) is False

    snapshot = collector.snapshot(
        runtime_name="TEST",
        generated_at_ns=2_000,
        refresh_interval_ms=60000,
        readiness=_readiness(),
        instrument_ids=("ESU6.CME",),
        bar_specifications=(
            "1-MINUTE-LAST-EXTERNAL",
            "5-MINUTE-LAST-EXTERNAL",
            "15-MINUTE-LAST-EXTERNAL",
        ),
        view_windows_ms=(("1-MINUTE-LAST-EXTERNAL", 60_000),),
        horizon_selectors=(("fast", "1-MINUTE-LAST-EXTERNAL"),),
        selected_metric_prefixes=(
            ("1-MINUTE-LAST-EXTERNAL", ("rolling.fast.context_20m.",)),
        ),
        annotation_expectations=(),
    )

    assert [bar.interval_start_ns for bar in snapshot.bars] == [60 * SECOND_NS, 120 * SECOND_NS]
    assert len(snapshot.metrics) == 1
    assert snapshot.metrics[0].revision == 2


def test_plotly_bundle_renders_every_horizon_and_truthful_coverage(tmp_path) -> None:  # noqa: ANN001
    collector = _collector(maximum_bars=10)
    for selector in (
        "1-MINUTE-LAST-EXTERNAL",
        "5-MINUTE-LAST-EXTERNAL",
        "15-MINUTE-LAST-EXTERNAL",
    ):
        collector.accept_bar(_bar(1, selector))
    snapshot = collector.snapshot(
        runtime_name="TEST",
        generated_at_ns=2_000,
        refresh_interval_ms=60000,
        readiness=_readiness(),
        instrument_ids=("ESU6.CME",),
        bar_specifications=(
            "1-MINUTE-LAST-EXTERNAL",
            "5-MINUTE-LAST-EXTERNAL",
            "15-MINUTE-LAST-EXTERNAL",
        ),
        view_windows_ms=(
            ("1-MINUTE-LAST-EXTERNAL", 2_700_000),
            ("5-MINUTE-LAST-EXTERNAL", 14_400_000),
            ("15-MINUTE-LAST-EXTERNAL", 28_800_000),
        ),
        horizon_selectors=(("intraday_5m", "5-MINUTE-LAST-EXTERNAL"),),
        selected_metric_prefixes=(
            ("1-MINUTE-LAST-EXTERNAL", ("rolling.fast.context_20m.",)),
        ),
        annotation_expectations=(
            AnnotationExpectation(
                instrument_id="ESU6.CME",
                horizon="intraday_5m",
                bar_specification="5-MINUTE-LAST-EXTERNAL",
                entity_types=("confirmed_swing", "fair_value_gap"),
            ),
        ),
    )

    paths = render_visual_acceptance(snapshot, tmp_path)

    assert paths == (
        tmp_path / "esu6-cme" / "1-minute.png",
        tmp_path / "esu6-cme" / "5-minute.png",
        tmp_path / "esu6-cme" / "15-minute.png",
    )
    assert all(path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n") for path in paths)
    assert not list(tmp_path.rglob("*.html"))
    assert not (tmp_path / "plotly.min.js").exists()


def test_plotly_uses_each_configured_viewport_independently() -> None:
    collector = _collector(maximum_bars=10)
    for index in range(4):
        collector.accept_bar(_bar(index, "1-MINUTE-LAST-EXTERNAL"))
        collector.accept_bar(_bar(index, "5-MINUTE-LAST-EXTERNAL"))
    snapshot = collector.snapshot(
        runtime_name="TEST",
        generated_at_ns=2_000,
        refresh_interval_ms=60000,
        readiness=_readiness(),
        instrument_ids=("ESU6.CME",),
        bar_specifications=(
            "1-MINUTE-LAST-EXTERNAL",
            "5-MINUTE-LAST-EXTERNAL",
            "15-MINUTE-LAST-EXTERNAL",
        ),
        view_windows_ms=(
            ("1-MINUTE-LAST-EXTERNAL", 2 * 60_000),
            ("5-MINUTE-LAST-EXTERNAL", 10 * 60_000),
            ("15-MINUTE-LAST-EXTERNAL", 15 * 60_000),
        ),
        horizon_selectors=(),
        selected_metric_prefixes=(),
        annotation_expectations=(),
    )

    one_minute = _horizon_figure(snapshot, "ESU6.CME", "1-MINUTE-LAST-EXTERNAL")
    five_minute = _horizon_figure(snapshot, "ESU6.CME", "5-MINUTE-LAST-EXTERNAL")

    assert len(one_minute.data[0].x) == 2
    assert len(five_minute.data[0].x) == 2
    assert one_minute.layout.xaxis.range != five_minute.layout.xaxis.range
    assert one_minute.layout.xaxis.range == one_minute.layout.xaxis2.range
    assert five_minute.layout.xaxis.range == five_minute.layout.xaxis2.range


def test_objective_labels_preserve_their_canonical_source() -> None:
    previous = ObjectiveLevelPayload(
        price=Decimal("100"),
        lower=Decimal("100"),
        upper=Decimal("100"),
        source_kind="previous_session.high",
        horizon="previous_session",
        role="OBJECTIVE_REFERENCE",
        developing=False,
    )
    opening_range = replace(
        previous,
        source_kind="opening_range.cme_equity_primary.opening_range_fast.low",
    )

    assert _objective_label(previous) == "Previous Session High"
    assert _objective_label(opening_range) == "Opening Range Low"
