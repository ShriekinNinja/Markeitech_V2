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
from markeitech.intelligence.visual_debug_capture import FrozenVisualDebugCapture, canonical_json


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


def render_visual_debug_html(capture: FrozenVisualDebugCapture) -> str:
    metrics = _metric_map(capture)
    times = [_utc(bar.interval_end_ns) for bar in capture.bars]
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
    figure = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.025,
        row_heights=[0.60, 0.15, 0.125, 0.125],
    )
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
                "O %{customdata[2]} · H %{customdata[3]} · L %{customdata[4]} · C %{customdata[5]}"
                " · V %{customdata[6]}<br>source %{customdata[7]} · health %{customdata[8]}"
                " · fidelity %{customdata[9]} · revision %{customdata[10]}<br>"
                "missing %{customdata[11]}<extra></extra>"
            ),
        ),
        row=1,
        col=1,
    )
    lineage_symbols = [
        "square" if bar.source.value.startswith("historical") else "diamond" for bar in capture.bars
    ]
    lineage_text = [
        "H" if bar.source.value.startswith("historical") else "L" for bar in capture.bars
    ]
    figure.add_trace(
        go.Scatter(
            x=times,
            y=[min(float(bar.low) for bar in capture.bars)] * len(times),
            mode="markers+text",
            marker={"symbol": lineage_symbols, "size": 10, "color": "#7aa2f7"},
            text=lineage_text,
            textposition="bottom center",
            name="Lineage H/L",
            hovertext=[bar.source.value for bar in capture.bars],
            hovertemplate="%{x}<br>%{hovertext}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    trace_indices: dict[str, list[int]] = {"overview": [0, 1]}
    for metric_id, row, mode in (
        ("completed_bar.volume", 2, "bar"),
        ("completed_bar.simple_return", 3, "line"),
        ("completed_bar.true_range", 4, "line"),
    ):
        values = [metrics[(metric_id, bar.interval_end_ns)] for bar in capture.bars]
        y = [_number(item.value) for item in values]
        hover = [
            [
                _exact(item.value),
                item.unit,
                item.health.value,
                item.fidelity.value,
                item.revision,
                ", ".join(item.missing_reasons) or "none",
                _utc(item.effective_ts_ns),
                _utc(item.published_ts_ns),
            ]
            for item in values
        ]
        trace = (
            go.Bar(x=times, y=y, customdata=hover, name=metric_id)
            if mode == "bar"
            else go.Scatter(
                x=times,
                y=y,
                customdata=hover,
                mode="lines+markers",
                connectgaps=False,
                name=metric_id,
            )
        )
        trace.hovertemplate = (
            "%{customdata[6]}<br>value %{customdata[0]} %{customdata[1]}<br>"
            "health %{customdata[2]} · fidelity %{customdata[3]} · revision %{customdata[4]}<br>"
            "missing %{customdata[5]} · published %{customdata[7]}<extra></extra>"
        )
        figure.add_trace(trace, row=row, col=1)
        index = len(figure.data) - 1
        trace_indices[metric_id.removeprefix("completed_bar.")] = [index]
        trace_indices["overview"].append(index)
        paper_y = {2: 0.28, 3: 0.13, 4: 0.01}[row]
        for timestamp, item in zip(times, values, strict=True):
            if item.value is None:
                figure.add_annotation(
                    x=timestamp,
                    y=paper_y,
                    xref="x4",
                    yref="paper",
                    text=(
                        f"W · {item.health.value} · "
                        f"{html.escape(', '.join(item.missing_reasons))}"
                    ),
                    showarrow=False,
                    font={"size": 10, "color": "#fbbf24"},
                )
    for metric_id in (
        "completed_bar.open",
        "completed_bar.high",
        "completed_bar.low",
        "completed_bar.close",
    ):
        values = [metrics[(metric_id, bar.interval_end_ns)] for bar in capture.bars]
        figure.add_trace(
            go.Scatter(
                x=times,
                y=[_number(item.value) for item in values],
                customdata=[
                    [_exact(item.value), item.revision, item.health.value] for item in values
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
        height=860,
        margin={"l": 70, "r": 30, "t": 30, "b": 50},
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
        legend={"orientation": "h", "y": 1.02, "x": 0},
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
    )
    rows = []
    for bar in capture.bars:
        values = [
            metrics[(metric_id, bar.interval_end_ns)]
            for metric_id in (
                "completed_bar.open",
                "completed_bar.high",
                "completed_bar.low",
                "completed_bar.close",
                "completed_bar.volume",
                "completed_bar.simple_return",
                "completed_bar.true_range",
            )
        ]
        rows.append(
            "<tr>"
            f"<td>{html.escape(_utc(bar.interval_end_ns))}</td>"
            f"<td>{html.escape(bar.source.value)}</td>"
            + "".join(
                f"<td title='{html.escape('; '.join(value.missing_reasons))}'>{html.escape(_exact(value.value))}"
                f"<small>{html.escape(value.health.value)} r{value.revision}</small></td>"
                for value in values
            )
            + "<td><details><summary>identity and lineage</summary><pre>"
            + html.escape(canonical_json({"bar": bar, "metrics": tuple(values)}))
            + "</pre></details></td>"
            + "</tr>"
        )
    trace_map = json.dumps(trace_indices, sort_keys=True)
    options = "".join(
        f"<option value='{name}'>{name.replace('_', ' ').title()}</option>"
        for name in (
            "overview",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "simple_return",
            "true_range",
        )
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ESU6.CME completed-bar review</title><style>
body{{margin:0;background:#111820;color:#e5e7eb;font:14px system-ui,sans-serif}}main{{max-width:1500px;margin:auto;padding:18px}}
h1{{font-size:20px;margin:0 0 6px}}.meta{{color:#aab4c0;margin-bottom:14px}}label{{font-weight:650}}
select,button{{margin-left:8px;padding:6px;background:#1b2733;color:#fff;border:1px solid #718096;border-radius:4px}}
table{{width:100%;border-collapse:collapse;margin-top:18px}}th,td{{border:1px solid #334155;padding:6px;text-align:right}}th:first-child,td:first-child{{text-align:left}}small{{display:block;color:#9ca3af}}
.notice{{border-left:4px solid #f59e0b;padding:8px 12px;background:#2a2418;margin:12px 0}}:focus{{outline:3px solid #fbbf24;outline-offset:2px}}
</style></head><body><main>
<h1>ESU6.CME · 1-minute · UTC · FROZEN LIVE CAPTURE</h1>
<div class="meta">capture {html.escape(capture.capture_id)} · frozen {_utc(capture.frozen_at_ns)} · {html.escape(capture.capture_completeness)}</div>
<div class="notice">Bar-conflict evidence: NOT SUPPLIED to this projection. Constituent five-second records are not captured.</div>
<label for="focus">Metric focus</label><select id="focus">{options}</select><button id="reset" type="button">Reset view</button>
{plot}
<h2>Exact captured records</h2><table><thead><tr><th>Interval end UTC</th><th>Source</th><th>Open</th><th>High</th><th>Low</th><th>Close</th><th>Volume</th><th>Simple return</th><th>True range</th><th>Details</th></tr></thead><tbody>{"".join(rows)}</tbody></table>
<script>
const chart=document.getElementById({json.dumps(div_id)}), groups={trace_map};
document.getElementById('focus').addEventListener('change',e=>{{const visible=Array(chart.data.length).fill(false);[0,1].forEach(i=>visible[i]=true);(groups[e.target.value]||[]).forEach(i=>visible[i]=true);Plotly.restyle(chart,{{visible}});}});
document.getElementById('reset').addEventListener('click',()=>Plotly.relayout(chart,{{'xaxis.autorange':true,'xaxis2.autorange':true,'xaxis3.autorange':true,'xaxis4.autorange':true}}));
</script></main></body></html>"""
