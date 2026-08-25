from __future__ import annotations

import os
import re
import shutil
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

from markeitech.intelligence.entities import EntityRevision
from markeitech.intelligence.fvg_entities import FvgPayload
from markeitech.intelligence.market_states import ReferenceStatePayload
from markeitech.intelligence.market_structure_entities import ConfirmedSwingPayload
from markeitech.intelligence.market_structure_relationships import (
    PivotStructurePayload,
    SwingLegPayload,
)
from markeitech.intelligence.session_entities import (
    AnalyticalSessionPayload,
    ObjectiveLevelPayload,
    OpeningRangePayload,
    PreviousSessionReferencePayload,
)
from markeitech.intelligence.visual_acceptance import VisualAcceptanceSnapshot
from markeitech.intelligence.zone_entities import DerivedZonePayload

_IMAGE_WIDTH = 1800
_IMAGE_HEIGHT = 1000
_COLORS = {
    "session": "rgba(120, 144, 156, 0.12)",
    "previous": "#90a4ae",
    "opening_range": "rgba(255, 193, 7, 0.14)",
    "objective": "#ffd54f",
    "ema": "#ec407a",
    "swing_high": "#ef5350",
    "swing_low": "#26a69a",
    "leg": "#42a5f5",
    "fvg_bullish": "rgba(38, 166, 154, 0.18)",
    "fvg_bearish": "rgba(239, 83, 80, 0.18)",
    "zone": "rgba(171, 71, 188, 0.16)",
}


def render_visual_acceptance(
    snapshot: VisualAcceptanceSnapshot,
    output_directory: Path,
) -> tuple[Path, ...]:
    output_directory.mkdir(parents=True, exist_ok=True)
    staging = output_directory / f".render-{snapshot.generated_at_ns}"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    figures: list[go.Figure] = []
    staging_paths: list[Path] = []
    output_paths: list[Path] = []
    for instrument_id in snapshot.instrument_ids:
        instrument_directory = _slug(instrument_id)
        for bar_specification in snapshot.bar_specifications:
            file_name = f"{_slug(_display_selector(bar_specification))}.png"
            staged = staging / instrument_directory / file_name
            staged.parent.mkdir(parents=True, exist_ok=True)
            figures.append(_horizon_figure(snapshot, instrument_id, bar_specification))
            staging_paths.append(staged)
            output_paths.append(output_directory / instrument_directory / file_name)
    try:
        pio.write_images(
            fig=figures,
            file=[str(path) for path in staging_paths],
            format="png",
            width=_IMAGE_WIDTH,
            height=_IMAGE_HEIGHT,
            scale=1,
        )
        _publish_images(output_directory, staging, staging_paths, output_paths)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return tuple(output_paths)


def _horizon_figure(
    snapshot: VisualAcceptanceSnapshot,
    instrument_id: str,
    bar_specification: str,
) -> go.Figure:
    view_windows_ms = dict(snapshot.view_windows_ms)
    duration_ms = view_windows_ms.get(bar_specification)
    context = "" if duration_ms is None else f" · {_display_duration(duration_ms)} view"
    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.035,
        row_heights=[0.82, 0.18],
        subplot_titles=(f"{_display_selector(bar_specification)}{context}", "Volume"),
    )
    all_bars = sorted(
        (
            bar
            for bar in snapshot.bars
            if bar.instrument_id == instrument_id
            and bar.bar_specification == bar_specification
        ),
        key=lambda item: item.interval_start_ns,
    )
    bars = all_bars
    range_start_ns = None
    latest_end_ns = snapshot.generated_at_ns
    if all_bars:
        latest_end_ns = max(bar.interval_end_ns for bar in all_bars)
        if duration_ms is not None:
            range_start_ns = latest_end_ns - duration_ms * 1_000_000
            bars = [bar for bar in all_bars if bar.interval_end_ns > range_start_ns]
    if bars:
        x = [_timestamp(bar.interval_start_ns) for bar in bars]
        figure.add_trace(
            go.Candlestick(
                x=x,
                open=[float(bar.open) for bar in bars],
                high=[float(bar.high) for bar in bars],
                low=[float(bar.low) for bar in bars],
                close=[float(bar.close) for bar in bars],
                name=_display_selector(bar_specification),
                increasing_line_color="#eceff1",
                decreasing_line_color="#ef5350",
                showlegend=False,
                customdata=[
                    [
                        bar.source.value,
                        bar.health.value,
                        bar.fidelity.value,
                        bar.session_id,
                    ]
                    for bar in bars
                ],
                hovertemplate=(
                    "%{x}<br>O %{open}<br>H %{high}<br>L %{low}<br>C %{close}"
                    "<br>Source %{customdata[0]}<br>Health %{customdata[1]}"
                    "<br>Fidelity %{customdata[2]}<br>Session %{customdata[3]}<extra></extra>"
                ),
            ),
            row=1,
            col=1,
        )
        figure.add_trace(
            go.Bar(
                x=x,
                y=[None if bar.volume is None else float(bar.volume) for bar in bars],
                marker_color="rgba(120, 144, 156, 0.55)",
                name="Volume",
                showlegend=False,
                hovertemplate="%{x}<br>Volume %{y}<extra></extra>",
            ),
            row=2,
            col=1,
        )
        _add_overlays(
            figure,
            snapshot,
            instrument_id,
            bar_specification,
            1,
            latest_end_ns,
        )
        price_range = _visible_price_range(bars)
        figure.update_yaxes(range=price_range, row=1, col=1)
        if range_start_ns is not None:
            visible_range = [_timestamp(range_start_ns), _timestamp(latest_end_ns)]
            figure.update_xaxes(range=visible_range, row=1, col=1)
            figure.update_xaxes(range=visible_range, row=2, col=1)
    else:
        figure.add_annotation(
            text="No canonical completed bars observed for this horizon",
            x=0.5,
            y=0.5,
            xref="x domain",
            yref="y domain",
            showarrow=False,
            font={"color": "#90a4ae", "size": 18},
        )
    evidence_panel = _evidence_panel(
        snapshot,
        instrument_id,
        bar_specification,
        visible_bars=len(bars),
        retained_bars=len(all_bars),
    )
    figure.update_layout(
        title={
            "text": (
                f"{instrument_id} · {_display_selector(bar_specification)}"
                " · Sir Loke canonical evidence"
                f"<br><sup>{_timestamp(snapshot.generated_at_ns).isoformat()}"
                f" · readiness {snapshot.readiness.system_state}</sup>"
            ),
            "x": 0.01,
        },
        template="plotly_dark",
        paper_bgcolor="#0f1419",
        plot_bgcolor="#131a20",
        width=_IMAGE_WIDTH,
        height=_IMAGE_HEIGHT,
        margin={"l": 60, "r": 430, "t": 100, "b": 55},
        hovermode=False,
        showlegend=False,
    )
    figure.add_annotation(
        text=evidence_panel,
        x=1.015,
        y=0.99,
        xref="paper",
        yref="paper",
        xanchor="left",
        yanchor="top",
        align="left",
        showarrow=False,
        font={"color": "#cfd8dc", "size": 12},
        bordercolor="#37474f",
        borderwidth=1,
        borderpad=12,
        bgcolor="#10171d",
    )
    figure.update_xaxes(rangeslider_visible=False, showgrid=True, gridcolor="#263238")
    figure.update_yaxes(showgrid=True, gridcolor="#263238", side="right")
    return figure


def _add_overlays(
    figure: go.Figure,
    snapshot: VisualAcceptanceSnapshot,
    instrument_id: str,
    bar_specification: str,
    row: int,
    latest_end_ns: int,
) -> None:
    horizon_selectors = dict(snapshot.horizon_selectors)
    revisions = [
        revision
        for revision in snapshot.entity_revisions
        if revision.identity.instrument_id == instrument_id
    ]
    latest = _latest_revisions(revisions)
    for revision in latest:
        payload = revision.payload
        if payload is None or not _applies_to_selector(
            payload,
            bar_specification,
            horizon_selectors,
        ):
            continue
        if isinstance(payload, AnalyticalSessionPayload):
            figure.add_vrect(
                x0=_timestamp(payload.start_ns),
                x1=_timestamp(payload.end_ns),
                fillcolor=_COLORS["session"],
                line_width=0,
                row=row,
                col=1,
            )
        elif isinstance(payload, PreviousSessionReferencePayload):
            for name, price in (
                ("Prior high", payload.high),
                ("Prior low", payload.low),
                ("Prior close", payload.close),
            ):
                _add_level(figure, row, float(price), name, _COLORS["previous"])
        elif isinstance(payload, OpeningRangePayload):
            figure.add_shape(
                type="rect",
                x0=_timestamp(payload.start_ns),
                x1=_timestamp(latest_end_ns),
                y0=float(payload.low),
                y1=float(payload.high),
                fillcolor=_COLORS["opening_range"],
                line={"color": "#ffc107", "width": 1},
                row=row,
                col=1,
            )
            figure.add_annotation(
                x=_timestamp(latest_end_ns),
                y=float(payload.high),
                text="Opening Range",
                showarrow=False,
                xanchor="right",
                yanchor="bottom",
                font={"color": "#ffc107", "size": 10},
                row=row,
                col=1,
            )
        elif isinstance(payload, ObjectiveLevelPayload):
            _add_level(
                figure,
                row,
                float(payload.price),
                _objective_label(payload),
                _COLORS["objective"],
            )
        elif isinstance(payload, ConfirmedSwingPayload):
            color = _COLORS["swing_high"] if payload.kind.value == "HIGH" else _COLORS["swing_low"]
            symbol = "triangle-down" if payload.kind.value == "HIGH" else "triangle-up"
            figure.add_trace(
                go.Scatter(
                    x=[_timestamp(payload.pivot_ts_ns)],
                    y=[float(payload.pivot_price)],
                    mode="markers+text",
                    marker={"color": color, "size": 11, "symbol": symbol},
                    text=[f"{payload.kind.value[0]} {payload.pivot_price}"],
                    textposition=(
                        "top center" if payload.kind.value == "HIGH" else "bottom center"
                    ),
                    textfont={"color": color, "size": 9},
                    name=f"Confirmed swing {payload.kind.value.lower()}",
                    customdata=[
                        f"Confirmed {_timestamp(payload.confirmation_ts_ns).isoformat()}"
                        f"<br>Prominence {payload.prominence}"
                    ],
                    hovertemplate="%{x}<br>%{y}<br>%{customdata}<extra></extra>",
                    showlegend=False,
                ),
                row=row,
                col=1,
            )
        elif isinstance(payload, SwingLegPayload):
            origin_ts = _timestamp(payload.origin.pivot_ts_ns)
            destination_ts = _timestamp(payload.destination.pivot_ts_ns)
            figure.add_trace(
                go.Scatter(
                    x=[origin_ts, destination_ts],
                    y=[float(payload.origin.pivot_price), float(payload.destination.pivot_price)],
                    mode="lines",
                    line={"color": _COLORS["leg"], "width": 2},
                    name="Swing leg",
                    text=[
                        f"Δ {payload.price_change} · {payload.percentage_change}%"
                        f" · {payload.elapsed_bars} bars"
                    ] * 2,
                    hovertemplate="%{x}<br>%{y}<br>%{text}<extra></extra>",
                    showlegend=False,
                ),
                row=row,
                col=1,
            )
            figure.add_annotation(
                x=origin_ts + (destination_ts - origin_ts) / 2,
                y=(float(payload.origin.pivot_price) + float(payload.destination.pivot_price)) / 2,
                text=(
                    f"Δ {payload.price_change} · {payload.percentage_change}%"
                    f" · {payload.elapsed_bars} bars · slope {payload.slope_per_bar}/bar"
                ),
                showarrow=False,
                font={"color": _COLORS["leg"], "size": 8},
                bgcolor="rgba(15, 20, 25, 0.72)",
                row=row,
                col=1,
            )
        elif isinstance(payload, FvgPayload):
            color = (
                _COLORS["fvg_bullish"]
                if payload.direction.value == "BULLISH"
                else _COLORS["fvg_bearish"]
            )
            figure.add_shape(
                type="rect",
                x0=_timestamp(payload.formation_start_ts_ns),
                x1=_timestamp(payload.terminal_ts_ns or latest_end_ns),
                y0=float(payload.lower_bound),
                y1=float(payload.upper_bound),
                fillcolor=color,
                line={"color": color, "width": 1},
                row=row,
                col=1,
            )
            figure.add_annotation(
                x=_timestamp(payload.formation_ts_ns),
                y=float(payload.upper_bound),
                text=(
                    f"{payload.direction.value.title()} FVG"
                    f" · fill {float(payload.fill_ratio) * 100:.0f}%"
                    f" · {revision.lifecycle.value}"
                ),
                showarrow=False,
                xanchor="left",
                yanchor="bottom",
                font={"color": "#cfd8dc", "size": 8},
                bgcolor="rgba(15, 20, 25, 0.72)",
                row=row,
                col=1,
            )
        elif isinstance(payload, DerivedZonePayload):
            figure.add_shape(
                type="rect",
                x0=_timestamp(payload.created_ts_ns),
                x1=_timestamp(payload.terminal_ts_ns or latest_end_ns),
                y0=float(payload.lower),
                y1=float(payload.upper),
                fillcolor=_COLORS["zone"],
                line={"color": "#ab47bc", "width": 1},
                row=row,
                col=1,
            )
            figure.add_annotation(
                x=_timestamp(payload.created_ts_ns),
                y=float(payload.upper),
                text=(
                    f"Zone · {len(payload.constituents)} constituents"
                    f" · {revision.lifecycle.value}"
                ),
                showarrow=False,
                xanchor="left",
                yanchor="bottom",
                font={"color": "#ce93d8", "size": 8},
                bgcolor="rgba(15, 20, 25, 0.72)",
                row=row,
                col=1,
            )
        elif isinstance(payload, PivotStructurePayload) and payload.selected_pivots:
            figure.add_trace(
                go.Scatter(
                    x=[_timestamp(item.pivot_ts_ns) for item in payload.selected_pivots],
                    y=[float(item.pivot_price) for item in payload.selected_pivots],
                    mode="lines+markers",
                    line={"color": "#29b6f6", "width": 1, "dash": "dot"},
                    marker={"size": 6},
                    name=f"Pivot structure {payload.geometry_state.value}",
                    hovertemplate="%{x}<br>%{y}<extra></extra>",
                    showlegend=False,
                ),
                row=row,
                col=1,
            )
    reference_series: dict[str, list[tuple[int, float, str]]] = defaultdict(list)
    for revision in revisions:
        payload = revision.payload
        if not isinstance(payload, ReferenceStatePayload) or payload.value is None:
            continue
        if not _applies_to_selector(payload, bar_specification, horizon_selectors):
            continue
        reference_series[payload.reference_id].append(
            (revision.effective_ts_ns, float(payload.value), payload.slope_classification.category),
        )
    for reference_id, values in sorted(reference_series.items()):
        values.sort()
        figure.add_trace(
            go.Scatter(
                x=[_timestamp(item[0]) for item in values],
                y=[item[1] for item in values],
                mode="lines",
                line={"color": _COLORS["ema"], "width": 1.5},
                name=reference_id,
                text=[item[2] for item in values],
                hovertemplate="%{x}<br>%{y}<br>%{text}<extra></extra>",
                showlegend=False,
            ),
            row=row,
            col=1,
        )
        latest = values[-1]
        figure.add_annotation(
            x=_timestamp(latest[0]),
            y=latest[1],
            text=f"{reference_id} · {latest[2]}",
            showarrow=False,
            xanchor="left",
            font={"color": _COLORS["ema"], "size": 8},
            bgcolor="rgba(15, 20, 25, 0.72)",
            row=row,
            col=1,
        )


def _add_level(figure: go.Figure, row: int, price: float, label: str, color: str) -> None:
    figure.add_hline(
        y=price,
        line={"color": color, "width": 1, "dash": "dot"},
        annotation_text=label.replace("_", " ").title(),
        annotation_position="right",
        row=row,
        col=1,
    )


def _objective_label(payload: ObjectiveLevelPayload) -> str:
    source = payload.source_kind
    if source.startswith("previous_session."):
        return f"Previous Session {source.rsplit('.', maxsplit=1)[-1].title()}"
    if source.startswith("opening_range."):
        return f"Opening Range {source.rsplit('.', maxsplit=1)[-1].title()}"
    return payload.role.replace("_", " ").title()


def _applies_to_selector(
    payload: object,
    bar_specification: str,
    horizon_selectors: dict[str, str],
) -> bool:
    payload_selector = getattr(payload, "bar_specification", None)
    if payload_selector is not None:
        return payload_selector == bar_specification
    horizon = getattr(payload, "horizon", None)
    if horizon in horizon_selectors:
        return horizon_selectors[horizon] == bar_specification
    horizons = getattr(payload, "horizons", ())
    if horizons:
        return any(
            horizon_selectors.get(item) == bar_specification
            for item in horizons
        )
    return isinstance(
        payload,
        (
            AnalyticalSessionPayload,
            PreviousSessionReferencePayload,
            OpeningRangePayload,
            ObjectiveLevelPayload,
        ),
    )


def _latest_revisions(revisions: list[EntityRevision]) -> tuple[EntityRevision, ...]:
    latest: dict[str, EntityRevision] = {}
    for revision in revisions:
        existing = latest.get(revision.entity_id)
        if existing is None or revision.revision > existing.revision:
            latest[revision.entity_id] = revision
    return tuple(
        sorted(
            latest.values(),
            key=lambda item: (item.identity.entity_type, item.entity_id),
        ),
    )


def _evidence_panel(
    snapshot: VisualAcceptanceSnapshot,
    instrument_id: str,
    bar_specification: str,
    *,
    visible_bars: int,
    retained_bars: int,
) -> str:
    prefixes = dict(snapshot.selected_metric_prefixes).get(bar_specification, ())
    latest_metrics = {}
    for metric in snapshot.metrics:
        if metric.instrument_id != instrument_id:
            continue
        if not any(metric.metric_id.startswith(prefix) for prefix in prefixes):
            continue
        existing = latest_metrics.get(metric.metric_id)
        if existing is None or metric.effective_ts_ns > existing.effective_ts_ns:
            latest_metrics[metric.metric_id] = metric
    revisions = _latest_revisions(
        [
            item
            for item in snapshot.entity_revisions
            if item.identity.instrument_id == instrument_id
            and item.payload is not None
            and _applies_to_selector(
                item.payload,
                bar_specification,
                dict(snapshot.horizon_selectors),
            )
        ],
    )
    entity_counts = Counter(item.identity.entity_type for item in revisions)
    lifecycle_counts = Counter(item.lifecycle.value for item in revisions)
    expected = set()
    horizon_selectors = dict(snapshot.horizon_selectors)
    for expectation in snapshot.annotation_expectations:
        selector = expectation.bar_specification or horizon_selectors.get(expectation.horizon)
        if expectation.instrument_id == instrument_id and selector == bar_specification:
            expected.update(expectation.entity_types)
    observed = set(entity_counts)
    metric_lines = []
    for metric_id, metric in sorted(latest_metrics.items()):
        label = next(
            (
                metric_id.removeprefix(prefix).replace("_", " ").title()
                for prefix in prefixes
                if metric_id.startswith(prefix)
            ),
            metric_id,
        )
        metric_lines.append(
            f"{label}: <b>{_scalar(metric.value)}</b> {metric.unit}"
            f" · {metric.health.value}/{metric.fidelity.value}",
        )
    entity_lines = [
        f"{entity_type.replace('_', ' ').title()}: <b>{count}</b>"
        for entity_type, count in sorted(entity_counts.items())
    ]
    coverage = (
        "Not configured"
        if not expected
        else f"{len(observed & expected)}/{len(expected)} configured types observed"
    )
    sources = Counter(
        bar.source.value
        for bar in snapshot.bars
        if bar.instrument_id == instrument_id and bar.bar_specification == bar_specification
    )
    sections = [
        "<b>Canonical coverage</b>",
        f"Bars: <b>{visible_bars}</b> visible / {retained_bars} retained",
        "Sources: " + (", ".join(f"{key} {value}" for key, value in sorted(sources.items())) or "none"),
        f"Annotations: {coverage}",
        "Lifecycle: "
        + (", ".join(f"{key} {value}" for key, value in sorted(lifecycle_counts.items())) or "none"),
        "",
        "<b>Latest selected-context metrics</b>",
        *(metric_lines or ["No matching canonical metric values"]),
        "",
        "<b>Latest entity revisions</b>",
        *(entity_lines or ["No canonical entities for this horizon"]),
        "",
        "<i>No display-derived analysis</i>",
    ]
    return "<br>".join(sections)


def _visible_price_range(bars) -> list[float]:  # noqa: ANN001
    low = min(float(bar.low) for bar in bars)
    high = max(float(bar.high) for bar in bars)
    span = high - low
    padding = max(span * 0.08, max(abs(high), abs(low), 1.0) * 0.0002)
    return [low - padding, high + padding]


def _publish_images(
    output_directory: Path,
    staging: Path,
    staging_paths: list[Path],
    output_paths: list[Path],
) -> None:
    desired = {path.relative_to(output_directory) for path in output_paths}
    for legacy in (*output_directory.glob("*.html"), output_directory / "plotly.min.js"):
        if legacy.exists():
            legacy.unlink()
    for legacy in output_directory.glob("*.html.tmp"):
        legacy.unlink()
    for existing in output_directory.rglob("*.png"):
        if staging in existing.parents:
            continue
        if existing.relative_to(output_directory) not in desired:
            existing.unlink()
    for staged, output in zip(staging_paths, output_paths, strict=True):
        output.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staged, output)
    shutil.rmtree(staging, ignore_errors=True)


def _scalar(value: object) -> str:
    if value is None:
        return "n/a"
    return str(value)


def _timestamp(timestamp_ns: int) -> datetime:
    return datetime.fromtimestamp(timestamp_ns / 1_000_000_000, UTC)


def _display_selector(selector: str) -> str:
    return selector.replace("-LAST-EXTERNAL", "").replace("-", " ").title()


def _display_duration(duration_ms: int) -> str:
    minutes = duration_ms // 60_000
    if minutes >= 60 and minutes % 60 == 0:
        return f"{minutes // 60}h"
    return f"{minutes}m"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "instrument"
