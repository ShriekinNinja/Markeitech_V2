from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from markeitech.acquisition import HistoricalReadinessEvent
from markeitech.intelligence.completed_bars import CompletedBarInput, CompletedBarSource
from markeitech.intelligence.metrics import MetricFidelity, MetricHealth, MetricValue
from markeitech.intelligence.session_measurements import COMPLETED_BAR_METRIC_IDS
from markeitech.intelligence.visual_debug_capture import (
    CAPTURE_SCOPE,
    VisualDebugCaptureCollector,
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
LAYOUT = {
    "candle_pane_height_px": 720,
    "volume_pane_height_px": 130,
    "metric_pane_height_px": 110,
    "pane_gap_px": 18,
}


def _readiness(observed_count: int = 20) -> HistoricalReadinessEvent:
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


def _bar(index: int, source: CompletedBarSource, *, gap_minutes: int = 0) -> CompletedBarInput:
    start = BASE_NS + (index + gap_minutes) * MINUTE_NS
    end = start + MINUTE_NS
    historical = source in {
        CompletedBarSource.HISTORICAL_PROVIDER,
        CompletedBarSource.HISTORICAL_AGGREGATE,
    }
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
        source=source,
        observed_ts_ns=end,
        received_ts_ns=end + 1,
        normalized_ts_ns=end + 2,
        health=MetricHealth.READY,
        fidelity=MetricFidelity.REPORTED if historical else MetricFidelity.DERIVED,
        evidence_refs=("historical:request-1",) if historical else (f"live:{index}",),
        complete=True,
    )


def _metrics(bar: CompletedBarInput, index: int, revision: int = 1) -> tuple[MetricValue, ...]:
    values = {
        "completed_bar.open": (bar.open, "price"),
        "completed_bar.high": (bar.high, "price"),
        "completed_bar.low": (bar.low, "price"),
        "completed_bar.close": (bar.close, "price"),
        "completed_bar.volume": (bar.volume, "volume"),
        "completed_bar.simple_return": (Decimal("0.001") if index else None, "ratio"),
        "completed_bar.true_range": (Decimal("3") if index else None, "price"),
    }
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
                revision=revision,
            ),
        )
    return tuple(result)


def _collector(historical: int = 5, live: int = 5) -> VisualDebugCaptureCollector:
    return VisualDebugCaptureCollector(
        instrument_id="ESU6.CME",
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        bar_specification="1-MINUTE-LAST-EXTERNAL",
        parameter_version=1,
        target_historical_bars=historical,
        target_live_bars=live,
    )


def _populate(
    collector: VisualDebugCaptureCollector,
    historical: int,
    live: int,
    *,
    gap: int = 0,
) -> None:
    for index in range(historical):
        bar = _bar(index, CompletedBarSource.HISTORICAL_PROVIDER)
        assert collector.accept_bar(bar)
        for metric in _metrics(bar, index):
            assert collector.accept_metric(metric)
    for offset in range(live):
        index = historical + offset
        bar = _bar(index, CompletedBarSource.LIVE_AGGREGATE, gap_minutes=gap)
        assert collector.accept_bar(bar)
        for metric in _metrics(bar, index):
            assert collector.accept_metric(metric)


def _freeze(
    collector: VisualDebugCaptureCollector,
    readiness: HistoricalReadinessEvent | None = None,
):  # noqa: ANN202
    return collector.freeze(
        run_id="00000000-0000-0000-0000-000000000001",
        configuration_identity="test-config",
        capture_policy_version=3,
        collection_started_ns=BASE_NS,
        frozen_at_ns=BASE_NS + 100 * MINUTE_NS,
        historical_readiness=readiness,
    )


def test_mixed_selection_is_passive_and_readiness_count_is_independent() -> None:
    collector = _collector(5, 5)
    _populate(collector, 5, 5)

    capture = _freeze(collector, _readiness(55))

    assert capture.selection_mode == "HISTORICAL_PLUS_LIVE"
    assert capture.selection_state == "COMPLETE_CONTIGUOUS"
    assert capture.selected_historical_bars == 5
    assert capture.selected_live_bars == 5
    assert len(capture.metrics) == 70
    assert capture.historical_readiness.observed_count == 55


def test_historical_only_and_live_only_allow_zero_opposite_target() -> None:
    historical = _collector(3, 0)
    _populate(historical, 3, 0)
    live = _collector(0, 3)
    _populate(live, 0, 3)

    historical_capture = _freeze(historical, _readiness())
    live_capture = _freeze(live)

    assert historical_capture.selection_mode == "HISTORICAL_ONLY"
    assert live_capture.selection_mode == "LIVE_ONLY"
    with pytest.raises(ValueError, match="at least one"):
        _collector(0, 0)


def test_real_gap_is_preserved_and_declared() -> None:
    collector = _collector(2, 2)
    _populate(collector, 2, 2, gap=3)

    capture = _freeze(collector, _readiness())

    assert capture.selection_state == "COMPLETE_WITH_GAPS"
    assert len(capture.gaps) == 1
    assert capture.gaps[0].reason == "UNCLASSIFIED_TEMPORAL_GAP"


def test_short_and_incomplete_population_freezes_as_partial() -> None:
    collector = _collector(5, 5)
    bar = _bar(0, CompletedBarSource.HISTORICAL_PROVIDER)
    assert collector.accept_bar(bar)
    assert collector.accept_metric(_metrics(bar, 0)[0])

    capture = _freeze(collector)

    assert capture.selection_state == "PARTIAL_COUNTS_AND_METRIC_COHORTS"
    assert capture.incomplete_metric_intervals == (bar.interval_end_ns,)


def test_failed_or_mismatched_historical_lineage_cannot_look_complete() -> None:
    collector = _collector(1, 0)
    _populate(collector, 1, 0)

    capture = _freeze(collector, replace(_readiness(), state="FAILED"))

    assert capture.selection_state == "PARTIAL_HISTORICAL_LINEAGE"


def test_same_revision_unequal_metric_is_terminal_conflict() -> None:
    collector = _collector(1, 0)
    bar = _bar(0, CompletedBarSource.HISTORICAL_PROVIDER)
    metric = _metrics(bar, 0)[0]
    assert collector.accept_bar(bar)
    assert collector.accept_metric(metric)

    assert not collector.accept_metric(replace(metric, value=Decimal("9999")))
    assert collector.conflict == "PROJECTION_METRIC_CONFLICT"
    with pytest.raises(ValueError, match="PROJECTION_METRIC_CONFLICT"):
        _freeze(collector)


def test_dynamic_html_and_manifest_disclose_scope_geometry_and_non_interference() -> None:
    collector = _collector(2, 1)
    _populate(collector, 2, 1)
    capture = _freeze(collector, _readiness())

    rendered = render_visual_debug_html(capture, layout=LAYOUT)
    manifest = frozen_capture_manifest(
        capture,
        html_sha256="a" * 64,
        plotly_version="test",
        renderer_layout=LAYOUT,
    )

    assert capture.capture_scope == CAPTURE_SCOPE
    assert "ESU6.CME · 1-MINUTE-LAST-EXTERNAL · UTC" in rendered
    assert "HISTORICAL_PLUS_LIVE" in rendered
    assert "does not change normal runtime operation" in rendered
    assert "COMPLETE_CONTIGUOUS" in rendered
    assert '"height":1204' in rendered
    assert "identity and lineage" in rendered
    assert 'src="https://cdn.plot.ly' not in rendered
    assert manifest["renderer"]["layout"]["candle_pane_height_px"] == 720
    assert manifest["lineage_disclosures"]["capture_changes_upstream_runtime"] is False


def _actor_config(tmp_path) -> VisualDebugCaptureActorConfig:  # noqa: ANN001
    return VisualDebugCaptureActorConfig(
        run_id="00000000-0000-0000-0000-000000000001",
        configuration_identity="test-config",
        instrument_id="ESU6.CME",
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        bar_specification="1-MINUTE-LAST-EXTERNAL",
        parameter_version=1,
        output_directory=str(tmp_path),
        capture_policy_version=3,
        target_historical_bars=5,
        target_live_bars=5,
        quiet_period_ms=2_000,
        completion_deadline_ms=900_000,
        output_drain_timeout_ms=30_000,
        **LAYOUT,
        actor_id="VISUAL-DEBUG-CAPTURE",
    )


def test_capture_actor_accepts_readiness_without_equating_it_to_display_count(tmp_path) -> None:  # noqa: ANN001
    actor = VisualDebugCaptureActor(_actor_config(tmp_path))
    actor._evaluate_completion = lambda: None

    actor._accept_readiness(_readiness(55))

    assert actor._readiness == _readiness(55)


def test_writer_atomically_publishes_html_and_manifest(tmp_path) -> None:  # noqa: ANN001
    collector = _collector(1, 0)
    _populate(collector, 1, 0)
    capture = _freeze(collector, _readiness())
    writer = VisualDebugCaptureWriter(tmp_path, LAYOUT)
    writer.start()

    assert writer.submit(capture)
    assert writer.close(10.0)

    result = writer.results.get_nowait()
    final = tmp_path / capture.capture_id
    manifest = json.loads((final / "manifest.json").read_text())
    assert result.state == "OUTPUT_PUBLISHED"
    assert manifest["integrity"]["html_sha256"] == hashlib.sha256(
        (final / "snapshot.html").read_bytes(),
    ).hexdigest()
    assert not tuple(tmp_path.glob(".*"))


def test_writer_timeout_commit_fence_prevents_late_publication(
    tmp_path,  # noqa: ANN001
    monkeypatch,  # noqa: ANN001
) -> None:
    collector = _collector(1, 0)
    _populate(collector, 1, 0)
    capture = _freeze(collector, _readiness())
    entered = threading.Event()
    release = threading.Event()

    def blocked_render(_capture, *, layout) -> str:  # noqa: ANN001, ARG001
        entered.set()
        assert release.wait(5.0)
        return "<html>late</html>"

    monkeypatch.setattr(
        "markeitech.intelligence.visual_debug_capture_plotly.render_visual_debug_html",
        blocked_render,
    )
    writer = VisualDebugCaptureWriter(tmp_path, LAYOUT)
    writer.start()
    assert writer.submit(capture)
    assert entered.wait(2.0)

    assert not writer.close(0.0)
    release.set()
    writer._thread.join(5.0)  # noqa: SLF001

    assert not (tmp_path / capture.capture_id).exists()
