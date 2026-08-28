from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import replace
from datetime import date
from decimal import Decimal

from markeitech.acquisition import HistoricalReadinessEvent
from markeitech.intelligence.completed_bars import CompletedBarInput, CompletedBarSource
from markeitech.intelligence.metrics import MetricFidelity, MetricHealth, MetricValue
from markeitech.intelligence.session_measurements import COMPLETED_BAR_METRIC_IDS
from markeitech.intelligence.visual_debug_capture import (
    CAPTURE_COMPLETENESS,
    CompletedBarFoundationSnapshot,
    CompletedBarFoundationSnapshotRequest,
    CompletedBarFoundationSnapshotResponse,
    VisualDebugCaptureCollector,
    build_completed_bar_foundation_snapshot,
    frozen_capture_manifest,
)
from markeitech.intelligence.visual_debug_capture_actor import (
    VisualDebugCaptureActor,
    VisualDebugCaptureActorConfig,
    VisualDebugCaptureWriter,
)
from markeitech.intelligence.visual_debug_capture_plotly import render_visual_debug_html

MINUTE_NS = 60_000_000_000
BASE_NS = 1_777_286_400_000_000_000


def _readiness(observed_count: int = 5) -> HistoricalReadinessEvent:
    return HistoricalReadinessEvent(
        event_id="readiness-1",
        request_id="request-1",
        consumer_id="SESSION-METRICS",
        capability_id="metric:completed-bar-foundation",
        capability_version=1,
        state="READY",
        instrument_id="ESU6.CME",
        selector="1-MINUTE-LAST-EXTERNAL",
        window="recent_completed",
        minimum_observations=2,
        observed_count=observed_count,
        completed_at_ns=BASE_NS,
        source="DATA-ACQUISITION",
        reason="complete",
    )


def _bar(index: int, historical_bar_count: int = 5) -> CompletedBarInput:
    start = BASE_NS + index * MINUTE_NS
    end = start + MINUTE_NS
    return CompletedBarInput(
        instrument_id="ESU6.CME",
        bar_specification="1-MINUTE-LAST-EXTERNAL",
        calendar_id="cme_equity",
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        trade_date=date(2026, 8, 27),
        session_id="cme_equity:2026-08-27:OPEN",
        window_id="OPEN",
        interval_start_ns=start,
        interval_end_ns=end,
        open=Decimal("6500") + index,
        high=Decimal("6502") + index,
        low=Decimal("6499") + index,
        close=Decimal("6501") + index,
        volume=Decimal("1000") + index,
        source=(
            CompletedBarSource.HISTORICAL_PROVIDER
            if index < historical_bar_count
            else CompletedBarSource.LIVE_AGGREGATE
        ),
        observed_ts_ns=end,
        received_ts_ns=end + 1,
        normalized_ts_ns=end + 2,
        health=MetricHealth.READY,
        fidelity=(
            MetricFidelity.REPORTED
            if index < historical_bar_count
            else MetricFidelity.DERIVED
        ),
        evidence_refs=(
            ("historical:request-1",)
            if index < historical_bar_count
            else (f"bar:{index}",)
        ),
        complete=True,
    )


def _metrics(
    bar: CompletedBarInput, index: int, revision: int | None = None
) -> tuple[MetricValue, ...]:
    prior_close = Decimal("6501") + index - 1 if index else None
    values = {
        "completed_bar.open": (bar.open, "price"),
        "completed_bar.high": (bar.high, "price"),
        "completed_bar.low": (bar.low, "price"),
        "completed_bar.close": (bar.close, "price"),
        "completed_bar.volume": (bar.volume, "volume"),
        "completed_bar.simple_return": (
            None if prior_close is None else bar.close / prior_close - 1,
            "ratio",
        ),
        "completed_bar.true_range": (
            None
            if prior_close is None
            else max(bar.high - bar.low, abs(bar.high - prior_close), abs(bar.low - prior_close)),
            "price",
        ),
    }
    cohort_revision = revision or index + 1
    result = []
    for metric_id in COMPLETED_BAR_METRIC_IDS:
        value, unit = values[metric_id]
        warming = value is None
        result.append(
            MetricValue(
                metric_id=metric_id,
                metric_version=1,
                parameter_version=1,
                instrument_id=bar.instrument_id,
                session_id=bar.session_id,
                value=value,
                unit=unit,
                effective_ts_ns=bar.interval_end_ns,
                observed_ts_ns=bar.observed_ts_ns,
                received_ts_ns=bar.received_ts_ns,
                calculated_ts_ns=bar.normalized_ts_ns + 1,
                published_ts_ns=bar.normalized_ts_ns + 2,
                health=MetricHealth.WARMING if warming else bar.health,
                fidelity=MetricFidelity.UNAVAILABLE if warming else bar.fidelity,
                source="SESSION-METRICS",
                evidence_refs=bar.evidence_refs,
                missing_reasons=("prior_compatible_close_missing",) if warming else (),
                revision=cohort_revision,
            ),
        )
    return tuple(result)


def _complete_collector(
    historical_bar_count: int = 5,
    live_bar_count: int = 5,
) -> VisualDebugCaptureCollector:
    collector = VisualDebugCaptureCollector(
        instrument_id="ESU6.CME",
        bar_specification="1-MINUTE-LAST-EXTERNAL",
        parameter_version=1,
        historical_bar_count=historical_bar_count,
        live_bar_count=live_bar_count,
    )
    for index in range(historical_bar_count + live_bar_count):
        bar = _bar(index, historical_bar_count)
        assert collector.accept_bar(bar)
        for metric in _metrics(bar, index):
            assert collector.accept_metric(metric)
    return collector


def test_snapshot_contract_round_trip_and_bounded_collection() -> None:
    bars = tuple(_bar(index) for index in range(10))
    metrics = tuple(metric for index, bar in enumerate(bars) for metric in _metrics(bar, index))
    request = CompletedBarFoundationSnapshotRequest(
        request_id="request-1",
        requester="VISUAL-DEBUG-CAPTURE",
        requested_ts_ns=BASE_NS,
        instrument_id="ESU6.CME",
        bar_specification="1-MINUTE-LAST-EXTERNAL",
        parameter_version=1,
        maximum_intervals=10,
    )
    snapshot = CompletedBarFoundationSnapshot(BASE_NS, "SESSION-METRICS", bars, metrics)
    response = CompletedBarFoundationSnapshotResponse(
        request.request_id, request.requester, snapshot
    )
    collector = VisualDebugCaptureCollector(
        instrument_id=request.instrument_id,
        bar_specification=request.bar_specification,
        parameter_version=request.parameter_version,
    )

    collector.accept_snapshot(response.snapshot)
    selected = collector.selected_records()

    assert selected is not None
    assert len(selected[0]) == 10
    assert len(selected[1]) == 70


def test_producer_snapshot_selects_bounded_existing_values_without_recalculation() -> None:
    bars = tuple(_bar(index) for index in range(12))
    request = CompletedBarFoundationSnapshotRequest(
        request_id="request-1",
        requester="VISUAL-DEBUG-CAPTURE",
        requested_ts_ns=BASE_NS,
        instrument_id="ESU6.CME",
        bar_specification="1-MINUTE-LAST-EXTERNAL",
        parameter_version=1,
        maximum_intervals=10,
    )
    cohorts = {
        (bar.instrument_id, bar.interval_end_ns): _metrics(bar, index)
        for index, bar in enumerate(bars)
    }

    snapshot = build_completed_bar_foundation_snapshot(
        request,
        generated_ts_ns=BASE_NS + 20 * MINUTE_NS,
        producer_id="SESSION-METRICS",
        bars=bars,
        metric_cohorts=cohorts,
    )

    assert snapshot.bars == bars[-10:]
    assert len(snapshot.metrics) == 70
    assert snapshot.metrics[0] is cohorts[(bars[2].instrument_id, bars[2].interval_end_ns)][0]


def test_higher_incomplete_metric_cohort_blocks_freeze() -> None:
    collector = _complete_collector()
    bar = _bar(9)
    assert collector.accept_metric(replace(_metrics(bar, 9)[0], revision=99))

    assert collector.selected_records() is None


def test_complete_higher_cohort_replaces_older_cohort_without_mixing() -> None:
    collector = _complete_collector()
    bar = _bar(9)
    for metric in _metrics(bar, 9, revision=99):
        assert collector.accept_metric(metric)
    assert not collector.accept_metric(_metrics(bar, 9)[0])

    selected = collector.selected_records()

    assert selected is not None
    latest = [item for item in selected[1] if item.effective_ts_ns == bar.interval_end_ns]
    assert {item.revision for item in latest} == {99}


def test_same_revision_unequal_metric_is_a_terminal_conflict() -> None:
    collector = _complete_collector()
    original = _metrics(_bar(9), 9)[0]

    assert not collector.accept_metric(replace(original, value=Decimal("9999")))
    assert collector.conflict == "PROJECTION_METRIC_CONFLICT"


def test_freeze_and_interactive_html_preserve_exact_values_and_disclosures() -> None:
    capture = _complete_collector().freeze(
        run_id="00000000-0000-0000-0000-000000000001",
        configuration_identity="test-config",
        capture_policy_version=1,
        frozen_at_ns=BASE_NS + 11 * MINUTE_NS,
        historical_readiness=_readiness(),
    )

    rendered = render_visual_debug_html(capture)

    assert capture.capture_completeness == CAPTURE_COMPLETENESS
    assert len(capture.bars) == 10
    assert len(capture.metrics) == 70
    assert "FROZEN LIVE CAPTURE" in rendered
    assert "Bar-conflict evidence: NOT SUPPLIED" in rendered
    assert "6501" in rendered
    assert "connectgaps" in rendered
    assert "W · WARMING · prior_compatible_close_missing" in rendered
    assert "identity and lineage" in rendered
    assert 'src="https://cdn.plot.ly' not in rendered
    assert "kaleido" not in rendered.lower()
    assert render_visual_debug_html(capture) == rendered


def test_one_hour_capture_freezes_and_declares_exact_55_plus_5_population() -> None:
    capture = _complete_collector(55, 5).freeze(
        run_id="00000000-0000-0000-0000-000000000001",
        configuration_identity="one-hour-test-config",
        capture_policy_version=2,
        frozen_at_ns=BASE_NS + 61 * MINUTE_NS,
        historical_readiness=_readiness(55),
    )

    rendered = render_visual_debug_html(capture)
    manifest = frozen_capture_manifest(
        capture,
        html_sha256="a" * 64,
        plotly_version="test",
    )

    assert capture.historical_bar_count == 55
    assert capture.live_bar_count == 5
    assert len(capture.bars) == 60
    assert len(capture.metrics) == 420
    assert manifest["expected_population"] == {
        "bars": 60,
        "historical_bars": 55,
        "live_bars": 5,
        "metric_records": 420,
        "metric_ids": list(COMPLETED_BAR_METRIC_IDS),
    }
    assert "FROZEN LIVE CAPTURE" in rendered


def test_capture_actor_accepts_configured_55_bar_readiness(tmp_path) -> None:  # noqa: ANN001
    actor = VisualDebugCaptureActor(
        VisualDebugCaptureActorConfig(
            run_id="00000000-0000-0000-0000-000000000001",
            configuration_identity="one-hour-test-config",
            instrument_id="ESU6.CME",
            analytical_profile_id="cme_equity_primary",
            analytical_profile_version=1,
            bar_specification="1-MINUTE-LAST-EXTERNAL",
            parameter_version=1,
            output_directory=str(tmp_path),
            capture_policy_version=2,
            historical_bar_count=55,
            live_bar_count=5,
            quiet_period_ms=2_000,
            snapshot_retry_interval_ms=1_000,
            completion_deadline_ms=900_000,
            output_drain_timeout_ms=30_000,
            actor_id="VISUAL-DEBUG-CAPTURE",
        ),
    )
    actor._evaluate_completion = lambda: None

    actor._accept_readiness(_readiness(5))
    assert actor._readiness is None

    actor._accept_readiness(_readiness(55))
    assert actor._readiness == _readiness(55)


def test_writer_atomically_publishes_html_and_manifest(tmp_path) -> None:  # noqa: ANN001
    capture = _complete_collector().freeze(
        run_id="00000000-0000-0000-0000-000000000001",
        configuration_identity="test-config",
        capture_policy_version=1,
        frozen_at_ns=BASE_NS + 11 * MINUTE_NS,
        historical_readiness=_readiness(),
    )
    writer = VisualDebugCaptureWriter(tmp_path)
    writer.start()

    assert writer.submit(capture)
    assert writer.close(10.0)

    result = writer.results.get_nowait()
    final = tmp_path / capture.capture_id
    manifest = json.loads((final / "manifest.json").read_text())
    assert result.state == "OUTPUT_PUBLISHED"
    assert (final / "snapshot.html").exists()
    assert (
        manifest["integrity"]["html_sha256"]
        == hashlib.sha256(
            (final / "snapshot.html").read_bytes(),
        ).hexdigest()
    )
    assert not tuple(tmp_path.glob(".*"))


def test_writer_closes_cleanly_without_a_capture(tmp_path) -> None:  # noqa: ANN001
    writer = VisualDebugCaptureWriter(tmp_path)
    writer.start()

    assert writer.close(1.0)
    assert not tuple(tmp_path.iterdir())


def test_writer_timeout_commit_fence_prevents_late_publication(
    tmp_path,  # noqa: ANN001
    monkeypatch,  # noqa: ANN001
) -> None:
    capture = _complete_collector().freeze(
        run_id="00000000-0000-0000-0000-000000000001",
        configuration_identity="test-config",
        capture_policy_version=1,
        frozen_at_ns=BASE_NS + 11 * MINUTE_NS,
        historical_readiness=_readiness(),
    )
    entered = threading.Event()
    release = threading.Event()

    def blocked_render(_capture) -> str:  # noqa: ANN001
        entered.set()
        assert release.wait(5.0)
        return "<html>late</html>"

    monkeypatch.setattr(
        "markeitech.intelligence.visual_debug_capture_plotly.render_visual_debug_html",
        blocked_render,
    )
    writer = VisualDebugCaptureWriter(tmp_path)
    writer.start()
    assert writer.submit(capture)
    assert entered.wait(2.0)

    assert not writer.close(0.0)
    release.set()
    writer._thread.join(5.0)  # noqa: SLF001 - exact worker lifecycle invariant

    assert not (tmp_path / capture.capture_id).exists()
