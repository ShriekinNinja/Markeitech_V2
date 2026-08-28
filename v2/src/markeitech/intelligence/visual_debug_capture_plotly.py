# Embedded HTML, CSS, JavaScript, and Plotly hover templates are kept readable as complete lines.
# ruff: noqa: E501

from __future__ import annotations

import html
import json
from datetime import UTC, datetime
from decimal import Decimal

import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

from markeitech.intelligence.metrics import MetricValue
from markeitech.intelligence.session_measurements import COMPLETED_BAR_METRIC_IDS
from markeitech.intelligence.visual_debug_capture import FrozenVisualDebugCapture, canonical_json

_TOP_MARGIN = 30
_BOTTOM_MARGIN = 50


def _utc(value: int) -> str:
    return datetime.fromtimestamp(value / 1_000_000_000, UTC).isoformat().replace("+00:00", "Z")


def _number(value: object) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    return None


def _exact(value: object) -> str:
    return "null" if value is None else str(value)


def _metric_map(capture: FrozenVisualDebugCapture) -> dict[tuple[str, int], MetricValue]:
    return {(item.metric_id, item.effective_ts_ns): item for item in capture.metrics}


def _layout_geometry(layout: dict[str, int]) -> tuple[int, float, list[float]]:
    candle = int(layout["candle_pane_height_px"])
    volume = int(layout["volume_pane_height_px"])
    metric = int(layout["metric_pane_height_px"])
    gap = int(layout["pane_gap_px"])
    if min(candle, volume, metric, gap) <= 0:
        raise ValueError("visual-debug renderer dimensions must be positive")
    pane_total = candle + volume + metric * 2
    drawable = pane_total + gap * 3
    return (
        drawable + _TOP_MARGIN + _BOTTOM_MARGIN,
        gap / drawable,
        [candle / pane_total, volume / pane_total, metric / pane_total, metric / pane_total],
    )


def render_visual_debug_html(
    capture: FrozenVisualDebugCapture,
    *,
    layout: dict[str, int],
) -> str:
    height, spacing, row_heights = _layout_geometry(layout)
    metrics = _metric_map(capture)
    times = [_utc(bar.interval_end_ns) for bar in capture.bars]
    figure = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=spacing,
        row_heights=row_heights,
    )
    trace_indices: dict[str, list[int]] = {"overview": []}
    context_trace_indices: list[int] = []
    if capture.bars:
        custom = [
            [
                _utc(bar.interval_start_ns),
                _utc(bar.interval_end_ns),
                _exact(bar.open),
                _exact(bar.high),
                _exact(bar.low),
                _exact(bar.close),
                _exact(bar.volume),
                bar.source.value,
                bar.health.value,
                bar.fidelity.value,
                bar.revision,
                ", ".join(bar.missing_reasons) or "none",
            ]
            for bar in capture.bars
        ]
        figure.add_trace(
            go.Candlestick(
                x=times,
                open=[float(bar.open) for bar in capture.bars],
                high=[float(bar.high) for bar in capture.bars],
                low=[float(bar.low) for bar in capture.bars],
                close=[float(bar.close) for bar in capture.bars],
                customdata=custom,
                name="Canonical completed bar",
                hovertemplate=(
                    "[%{customdata[0]}, %{customdata[1]}) UTC<br>"
                    "O %{customdata[2]} · H %{customdata[3]} · L %{customdata[4]} · C %{customdata[5]} · V %{customdata[6]}<br>"
                    "source %{customdata[7]} · health %{customdata[8]} · fidelity %{customdata[9]} · revision %{customdata[10]}<br>"
                    "missing %{customdata[11]}<extra></extra>"
                ),
            ),
            row=1,
            col=1,
        )
        trace_indices["overview"].append(0)
        context_trace_indices.append(0)
        for timestamp, bar in zip(times, capture.bars, strict=True):
            historical = bar.source.value.startswith("historical")
            figure.add_annotation(
                x=timestamp,
                y=0.997,
                xref="x",
                yref="paper",
                text="H □" if historical else "L ◇",
                hovertext=bar.source.value,
                showarrow=False,
                font={"size": 9, "color": "#dbeafe" if historical else "#fef3c7"},
            )
        for gap in capture.gaps:
            figure.add_vrect(
                x0=_utc(gap.preceding_interval_end_ns),
                x1=_utc(gap.following_interval_start_ns),
                fillcolor="#94a3b8",
                opacity=0.14,
                line={"color": "#cbd5e1", "dash": "dash", "width": 1},
                annotation_text="GAP — no captured canonical bar",
                annotation_position="top",
                row="all",
                col=1,
            )
    else:
        figure.add_annotation(
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            text="No compatible canonical completed bars were observed before the receive cut.",
            showarrow=False,
            font={"size": 16, "color": "#fbbf24"},
        )

    for metric_id, row, mode in (
        ("completed_bar.volume", 2, "bar"),
        ("completed_bar.simple_return", 3, "line"),
        ("completed_bar.true_range", 4, "line"),
    ):
        values = [metrics.get((metric_id, bar.interval_end_ns)) for bar in capture.bars]
        y = [_number(item.value) if item is not None else None for item in values]
        hover = [
            (
                [_exact(item.value), item.unit, item.health.value, item.fidelity.value, item.revision, ", ".join(item.missing_reasons) or "none", _utc(item.effective_ts_ns), _utc(item.published_ts_ns)]
                if item is not None
                else ["missing", "unknown", "UNAVAILABLE", "UNAVAILABLE", 0, "metric cohort not observed", timestamp, "unknown"]
            )
            for item, timestamp in zip(values, times, strict=True)
        ]
        trace = (
            go.Bar(x=times, y=y, customdata=hover, name=metric_id)
            if mode == "bar"
            else go.Scatter(x=times, y=y, customdata=hover, mode="lines+markers", connectgaps=False, name=metric_id)
        )
        trace.hovertemplate = "%{customdata[6]}<br>value %{customdata[0]} %{customdata[1]}<br>health %{customdata[2]} · fidelity %{customdata[3]} · revision %{customdata[4]}<br>missing %{customdata[5]} · published %{customdata[7]}<extra></extra>"
        figure.add_trace(trace, row=row, col=1)
        index = len(figure.data) - 1
        trace_indices[metric_id.removeprefix("completed_bar.")] = [index]
        trace_indices["overview"].append(index)

    for metric_id in ("completed_bar.open", "completed_bar.high", "completed_bar.low", "completed_bar.close"):
        values = [metrics.get((metric_id, bar.interval_end_ns)) for bar in capture.bars]
        figure.add_trace(
            go.Scatter(
                x=times,
                y=[_number(item.value) if item is not None else None for item in values],
                customdata=[
                    [_exact(item.value), item.revision, item.health.value]
                    if item is not None
                    else ["missing", 0, "UNAVAILABLE"]
                    for item in values
                ],
                mode="markers",
                marker={"size": 11, "symbol": "circle-open", "line": {"width": 2}},
                name=f"Metric focus: {metric_id.removeprefix('completed_bar.')}",
                visible=False,
                hovertemplate="%{x}<br>exact %{customdata[0]} · revision %{customdata[1]} · %{customdata[2]}<extra></extra>",
            ),
            row=1,
            col=1,
        )
        trace_indices[metric_id.removeprefix("completed_bar.")] = [len(figure.data) - 1]

    figure.update_layout(
        template="plotly_dark",
        height=height,
        margin={"l": 70, "r": 30, "t": _TOP_MARGIN, "b": _BOTTOM_MARGIN},
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
        legend={"orientation": "h", "y": 1.015, "x": 0},
        uirevision=capture.capture_id,
    )
    figure.update_yaxes(title_text="Price", row=1, col=1)
    figure.update_yaxes(title_text="Volume", row=2, col=1)
    figure.update_yaxes(title_text="Return", row=3, col=1)
    figure.update_yaxes(title_text="TR", row=4, col=1)
    div_id = f"markeitech-capture-{capture.capture_id}"
    plot = pio.to_html(
        figure,
        include_plotlyjs=True,
        full_html=False,
        auto_play=False,
        validate=True,
        div_id=div_id,
        config={"responsive": True, "displaylogo": False},
    )
    rows = []
    for bar in capture.bars:
        values = [metrics.get((metric_id, bar.interval_end_ns)) for metric_id in COMPLETED_BAR_METRIC_IDS]
        rows.append(
            "<tr>"
            f"<th scope='row'>{html.escape(_utc(bar.interval_end_ns))}</th>"
            f"<td>{html.escape(bar.source.value)}</td>"
            + "".join(
                (
                    f"<td title='{html.escape('; '.join(value.missing_reasons))}'>{html.escape(_exact(value.value))}<small>{html.escape(value.health.value)} r{value.revision}</small></td>"
                    if value is not None
                    else "<td><span class='missing'>not observed</span></td>"
                )
                for value in values
            )
            + "<td><details><summary>identity and lineage</summary><pre>"
            + html.escape(canonical_json({"bar": bar, "metrics": tuple(value for value in values if value is not None)}))
            + "</pre></details></td></tr>"
        )
    gap_rows = "".join(
        f"<tr><th scope='row'>{html.escape(_utc(gap.preceding_interval_end_ns))} → {html.escape(_utc(gap.following_interval_start_ns))}</th><td colspan='9'>GAP · {html.escape(gap.reason)} · {gap.duration_ns} ns · {html.escape(gap.preceding_source)} → {html.escape(gap.following_source)}</td></tr>"
        for gap in capture.gaps
    )
    trace_map = json.dumps(trace_indices, sort_keys=True)
    review_items = ("overview", "open", "high", "low", "close", "volume", "simple_return", "true_range")
    options = "".join(f"<option value='{name}'>{name.replace('_', ' ').title()}</option>" for name in review_items)
    complete = capture.selection_state.startswith("COMPLETE")
    banner_class = "complete" if complete else "partial"
    banner_symbol = "■" if complete else "▲"
    expected = capture.target_historical_bars + capture.target_live_bars
    exact_spec = html.escape(capture.bar_specification)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(capture.instrument_id)} {exact_spec} completed-bar review</title><style>
body{{margin:0;background:#111820;color:#e5e7eb;font:14px system-ui,sans-serif}}main{{max-width:1600px;margin:auto;padding:18px}}h1{{font-size:20px;margin:0 0 6px}}.meta{{color:#bac5d1;margin-bottom:10px}}label{{font-weight:650}}select,button{{margin-left:8px;padding:6px;background:#1b2733;color:#fff;border:1px solid #94a3b8;border-radius:4px}}.banner{{padding:10px 12px;margin:12px 0}}.complete{{border:2px solid #86efac;background:#163323}}.partial{{border:3px dashed #fbbf24;background:#33270d}}.notice{{border-left:4px solid #60a5fa;padding:8px 12px;background:#17263a;margin:12px 0}}.scroll{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;margin-top:18px}}caption{{text-align:left;font-weight:700;padding:8px 0}}th,td{{border:1px solid #475569;padding:6px;text-align:right}}th:first-child,td:first-child{{text-align:left}}small{{display:block;color:#bac5d1}}.missing{{color:#fbbf24}}pre{{white-space:pre-wrap;text-align:left}}:focus{{outline:3px solid #fbbf24;outline-offset:2px}}@media(max-width:600px){{main{{padding:10px}}select,button{{margin:6px 0;width:100%}}}}@media(prefers-reduced-motion:reduce){{*{{scroll-behavior:auto!important;animation:none!important;transition:none!important}}}}
</style></head><body><main>
<h1>{html.escape(capture.instrument_id)} · {exact_spec} · UTC · FROZEN REVIEW PROJECTION</h1>
<div class="meta">Selection: {html.escape(capture.selection_mode)} · historical {capture.selected_historical_bars}/{capture.target_historical_bars} · live {capture.selected_live_bars}/{capture.target_live_bars} · frozen {_utc(capture.frozen_at_ns)}</div>
<div class="banner {banner_class}" role="status">{banner_symbol} {html.escape(capture.selection_state)} · {len(capture.bars)}/{expected} bars · {len(capture.metrics)} metric records · {len(capture.gaps)} declared gaps. This is a bounded observer receive cut, not global final truth and not review acceptance.</div>
<div class="notice">Selection mode describes records included in this frozen projection. It does not change normal runtime operation, provider demand, subscriptions, calculations, retention, persistence, or lifecycle. Startup replay is unavailable; bar-conflict evidence is NOT SUPPLIED; five-second constituent records are not captured.</div>
<label for="focus">Review item <span id="review-index">context preview</span></label><select id="focus">{options}</select><button id="reset" type="button">Reset view</button><span id="focus-status" role="status" aria-live="polite">Context preview — not an individual review outcome</span>
{plot}
<div class="scroll"><table><caption>Exact captured canonical bars and completed-bar metric records; UTC intervals use [start, end).</caption><thead><tr><th scope="col">Interval end UTC</th><th scope="col">Source</th><th scope="col">Open</th><th scope="col">High</th><th scope="col">Low</th><th scope="col">Close</th><th scope="col">Volume</th><th scope="col">Simple return</th><th scope="col">True range</th><th scope="col">Details</th></tr></thead><tbody>{"".join(rows)}{gap_rows}</tbody></table></div>
<script>
const chart=document.getElementById({json.dumps(div_id)}),groups={trace_map},context={json.dumps(context_trace_indices)},items={json.dumps(review_items)};
document.getElementById('focus').addEventListener('change',e=>{{const visible=Array(chart.data.length).fill(false);context.forEach(i=>visible[i]=true);(groups[e.target.value]||[]).forEach(i=>visible[i]=true);Plotly.restyle(chart,{{visible}});const i=items.indexOf(e.target.value);document.getElementById('review-index').textContent=e.target.value==='overview'?'context preview':`${{i}} of 7`;document.getElementById('focus-status').textContent=e.target.value==='overview'?'Context preview — not an individual review outcome':`Selected completed_bar.${{e.target.value}}; unrelated metric traces are hidden`;}});
document.getElementById('reset').addEventListener('click',()=>Plotly.relayout(chart,{{'xaxis.autorange':true,'xaxis2.autorange':true,'xaxis3.autorange':true,'xaxis4.autorange':true}}));
</script></main></body></html>"""
