from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from markeitech.analytics.contracts import (
    AnalyticsTimeframe,
    FairValueGapDirection,
    MarketContextSnapshot,
)
from markeitech.analytics.features import MarketContextFeatureSnapshot
from markeitech.domain.market_data import OneMinuteBar

_TIMEFRAME_ORDER = {
    AnalyticsTimeframe.ONE_MINUTE: 0,
    AnalyticsTimeframe.FIVE_MINUTES: 1,
    AnalyticsTimeframe.FIFTEEN_MINUTES: 2,
    AnalyticsTimeframe.THIRTY_MINUTES: 3,
    AnalyticsTimeframe.ONE_HOUR: 4,
    AnalyticsTimeframe.DAILY: 5,
}
_DEFAULT_WINDOW = timedelta(hours=4)
_MINUTE = timedelta(minutes=1)


@dataclass(frozen=True)
class AnalyticsChartDataset:
    instrument_id: str
    as_of: datetime
    window_start: datetime
    source: str
    bar_source: str
    bars: tuple[OneMinuteBar, ...]
    one_minute_history: tuple[MarketContextFeatureSnapshot, ...]
    latest_features: tuple[MarketContextFeatureSnapshot, ...]


def build_chart_dataset(
    instrument_id: str,
    bars: Sequence[OneMinuteBar],
    features: Sequence[MarketContextFeatureSnapshot],
    *,
    maximum_bars: int = 720,
    window: timedelta = _DEFAULT_WINDOW,
) -> AnalyticsChartDataset:
    if maximum_bars < 50:
        raise ValueError("analytics chart requires at least 50 bars")
    if window <= timedelta(0):
        raise ValueError("analytics chart window must be positive")
    one_minute = tuple(
        feature
        for feature in features
        if feature.snapshot.instrument_id == instrument_id
        and feature.snapshot.timeframe == AnalyticsTimeframe.ONE_MINUTE
    )
    if not one_minute:
        raise ValueError(f"no committed one-minute features for {instrument_id}")
    anchor = max(one_minute, key=lambda item: (item.snapshot.as_of, item.feature_id))
    window_start = anchor.snapshot.as_of - window
    coherent = tuple(
        feature
        for feature in features
        if feature.snapshot.instrument_id == instrument_id
        and feature.calculation_version == anchor.calculation_version
        and feature.configuration_hash == anchor.configuration_hash
        and feature.snapshot.as_of <= anchor.snapshot.as_of
    )
    history = tuple(
        sorted(
            (
                feature
                for feature in coherent
                if feature.snapshot.timeframe == AnalyticsTimeframe.ONE_MINUTE
                and feature.snapshot.as_of > window_start
            ),
            key=lambda item: (item.snapshot.as_of, item.feature_id),
        )[-maximum_bars:]
    )
    latest_by_timeframe: dict[AnalyticsTimeframe, MarketContextFeatureSnapshot] = {}
    for feature in coherent:
        current = latest_by_timeframe.get(feature.snapshot.timeframe)
        if current is None or (feature.snapshot.as_of, feature.feature_id) > (
            current.snapshot.as_of,
            current.feature_id,
        ):
            latest_by_timeframe[feature.snapshot.timeframe] = feature
    eligible_bars = tuple(
        bar
        for bar in bars
        if bar.instrument_id == instrument_id
        and bar.is_complete
        and not bar.is_revision
        and bar.close_ts > window_start
        and bar.close_ts <= anchor.snapshot.as_of
    )
    if not eligible_bars:
        raise ValueError(f"no committed bars for {instrument_id} through the latest feature")
    bars_by_source: dict[str, list[OneMinuteBar]] = {}
    for bar in eligible_bars:
        bars_by_source.setdefault(bar.source, []).append(bar)
    bar_source, source_bars = max(
        bars_by_source.items(),
        key=lambda item: (len(item[1]), item[0] == anchor.snapshot.source),
    )
    selected_bars = tuple(
        sorted(source_bars, key=lambda item: (item.open_ts, item.close_ts))[-maximum_bars:]
    )
    return AnalyticsChartDataset(
        instrument_id=instrument_id,
        as_of=anchor.snapshot.as_of,
        window_start=window_start,
        source=anchor.snapshot.source,
        bar_source=bar_source,
        bars=selected_bars,
        one_minute_history=history,
        latest_features=tuple(
            sorted(
                latest_by_timeframe.values(),
                key=lambda item: _TIMEFRAME_ORDER[item.snapshot.timeframe],
            )
        ),
    )


def render_analytics_chart(
    dataset: AnalyticsChartDataset,
    *,
    range_breaks: Sequence[datetime] = (),
) -> go.Figure:
    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=(0.82, 0.18),
    )
    x = [bar.close_ts for bar in dataset.bars]
    figure.add_trace(
        go.Candlestick(
            x=x,
            open=[float(bar.open) for bar in dataset.bars],
            high=[float(bar.high) for bar in dataset.bars],
            low=[float(bar.low) for bar in dataset.bars],
            close=[float(bar.close) for bar in dataset.bars],
            name="1m price",
            increasing_line_color="#d8e2e8",
            decreasing_line_color="#ef476f",
            increasing_fillcolor="#d8e2e8",
            decreasing_fillcolor="#ef476f",
        ),
        row=1,
        col=1,
    )
    volume_colors = ["#17a2b8" if bar.close >= bar.open else "#b23a59" for bar in dataset.bars]
    figure.add_trace(
        go.Bar(
            x=x,
            y=[float(bar.volume) for bar in dataset.bars],
            marker_color=volume_colors,
            name="volume",
            opacity=0.72,
        ),
        row=2,
        col=1,
    )
    _add_ema_traces(figure, dataset.one_minute_history)
    latest_one_minute = next(
        feature.snapshot
        for feature in dataset.latest_features
        if feature.snapshot.timeframe == AnalyticsTimeframe.ONE_MINUTE
    )
    visible_price_range = _visible_price_range(dataset.bars, latest_one_minute.atr_14)
    overlay_price_range = _expanded_range(visible_price_range, factor=0.25)
    _add_primary_levels(figure, latest_one_minute, overlay_price_range)
    _add_multitimeframe_levels(figure, dataset.latest_features, overlay_price_range)
    _add_fair_value_gaps(
        figure,
        dataset.latest_features,
        dataset.window_start,
        dataset.as_of,
        overlay_price_range,
    )
    trend_summary = " | ".join(
        f"{feature.snapshot.timeframe.value}:{feature.snapshot.trend.value.upper()}"
        for feature in dataset.latest_features
    )
    figure.update_layout(
        template="plotly_dark",
        title={
            "text": (
                f"{dataset.instrument_id} | committed analytics | "
                f"{dataset.as_of.isoformat()}<br><sup>{trend_summary} | "
                f"analytics={dataset.source} | candles={dataset.bar_source}</sup>"
            ),
            "x": 0.01,
            "xanchor": "left",
        },
        height=900,
        margin={"l": 70, "r": 150, "t": 90, "b": 50},
        hovermode="x unified",
        legend={"orientation": "h", "y": 1.02, "x": 0.42},
        xaxis_rangeslider_visible=False,
        paper_bgcolor="#101418",
        plot_bgcolor="#141a20",
        font={"family": "Inter, Arial, sans-serif", "size": 12, "color": "#d8e2e8"},
    )
    rangebreak_config = [{"values": list(range_breaks), "dvalue": 60_000}] if range_breaks else []
    figure.update_xaxes(
        showgrid=True,
        gridcolor="#27313a",
        range=[dataset.window_start, dataset.as_of],
        rangebreaks=rangebreak_config,
        rangeslider_visible=False,
    )
    figure.update_yaxes(
        showgrid=True,
        gridcolor="#27313a",
        range=list(visible_price_range),
        fixedrange=False,
        side="right",
        row=1,
        col=1,
    )
    figure.update_yaxes(showgrid=True, gridcolor="#27313a", side="right", row=2, col=1)
    return figure


def _add_ema_traces(
    figure: go.Figure,
    history: Sequence[MarketContextFeatureSnapshot],
) -> None:
    values = (
        ("ema_20", "EMA 20", "#8ac926", 1.3),
        ("ema_50", "EMA 50", "#ffca3a", 1.5),
        ("ema_200", "EMA 200", "#ff2e88", 2.0),
    )
    for field, label, color, width in values:
        points = [
            (feature.snapshot.as_of, getattr(feature.snapshot, field))
            for feature in history
            if getattr(feature.snapshot, field) is not None
        ]
        if not points:
            continue
        figure.add_trace(
            go.Scatter(
                x=[point[0] for point in points],
                y=[float(point[1]) for point in points],
                mode="lines",
                line={"color": color, "width": width},
                name=label,
            ),
            row=1,
            col=1,
        )


def _add_primary_levels(
    figure: go.Figure,
    snapshot: MarketContextSnapshot,
    visible_range: tuple[float, float],
) -> None:
    _horizontal_level(
        figure,
        snapshot.session_vwap,
        "VWAP",
        "#ff2e88",
        visible_range,
        width=2,
    )
    profile = snapshot.volume_profile
    if profile is not None:
        _horizontal_level(figure, profile.value_area_low, "VAL", "#ffca3a", visible_range)
        _horizontal_level(figure, profile.poc, "POC", "#ff9f1c", visible_range, width=2)
        _horizontal_level(figure, profile.value_area_high, "VAH", "#ffca3a", visible_range)
    _horizontal_level(
        figure,
        snapshot.prior_session_low,
        "Prior low",
        "#4cc9f0",
        visible_range,
        annotate=False,
    )
    _horizontal_level(
        figure,
        snapshot.prior_session_high,
        "Prior high",
        "#4cc9f0",
        visible_range,
        annotate=False,
    )


def _add_multitimeframe_levels(
    figure: go.Figure,
    features: Sequence[MarketContextFeatureSnapshot],
    visible_range: tuple[float, float],
) -> None:
    seen: set[tuple[str, Decimal]] = set()
    for feature in features:
        snapshot = feature.snapshot
        for level, side, color in (
            (snapshot.nearest_support, "support", "#2ec4b6"),
            (snapshot.nearest_resistance, "resistance", "#ef476f"),
        ):
            if level is None:
                continue
            key = (side, level.price)
            if key in seen:
                continue
            seen.add(key)
            _horizontal_level(
                figure,
                level.price,
                f"{snapshot.timeframe.value} {side}",
                color,
                visible_range,
                dash="dot",
                annotate=False,
            )


def _add_fair_value_gaps(
    figure: go.Figure,
    features: Sequence[MarketContextFeatureSnapshot],
    chart_start: datetime,
    chart_end: datetime,
    visible_range: tuple[float, float],
) -> None:
    seen: set[tuple[AnalyticsTimeframe, FairValueGapDirection, Decimal, Decimal]] = set()
    for feature in features:
        snapshot = feature.snapshot
        for gap in snapshot.fair_value_gaps:
            if gap.is_filled:
                continue
            if not _intersects(visible_range, (float(gap.lower), float(gap.upper))):
                continue
            key = (gap.timeframe, gap.direction, gap.lower, gap.upper)
            if key in seen:
                continue
            seen.add(key)
            bullish = gap.direction == FairValueGapDirection.BULLISH
            figure.add_shape(
                type="rect",
                x0=max(chart_start, gap.detected_ts),
                x1=chart_end,
                y0=float(gap.lower),
                y1=float(gap.upper),
                fillcolor="rgba(46,196,182,0.12)" if bullish else "rgba(239,71,111,0.12)",
                line={
                    "color": "rgba(46,196,182,0.55)" if bullish else "rgba(239,71,111,0.55)",
                    "width": 1,
                },
                layer="below",
                row=1,
                col=1,
            )


def _horizontal_level(
    figure: go.Figure,
    value: Decimal | None,
    label: str,
    color: str,
    visible_range: tuple[float, float],
    *,
    width: float = 1,
    dash: str = "solid",
    annotate: bool = True,
) -> None:
    if value is None:
        return
    numeric_value = float(value)
    if not visible_range[0] <= numeric_value <= visible_range[1]:
        return
    annotation = (
        {
            "annotation_text": f"{label} {_format_price(value)}",
            "annotation_position": "right",
        }
        if annotate
        else {}
    )
    figure.add_hline(
        y=numeric_value,
        line={"color": color, "width": width, "dash": dash},
        row=1,
        col=1,
        **annotation,
    )


def market_closed_minutes(
    start: datetime,
    end: datetime,
    expected_minute_opens: Sequence[datetime],
) -> tuple[datetime, ...]:
    """Return calendar-known closures without hiding unexpected data gaps."""
    expected = set(expected_minute_opens)
    cursor = start.replace(second=0, microsecond=0)
    if cursor < start:
        cursor += _MINUTE
    closed: list[datetime] = []
    while cursor < end:
        if cursor not in expected:
            closed.append(cursor)
        cursor += _MINUTE
    return tuple(closed)


def _visible_price_range(
    bars: Sequence[OneMinuteBar],
    atr_14: Decimal | None,
) -> tuple[float, float]:
    low = min(float(bar.low) for bar in bars)
    high = max(float(bar.high) for bar in bars)
    span = max(high - low, abs(high) * 0.0001, 1e-9)
    atr_padding = float(atr_14) * 0.5 if atr_14 is not None else 0.0
    padding = max(span * 0.05, atr_padding)
    return low - padding, high + padding


def _expanded_range(price_range: tuple[float, float], *, factor: float) -> tuple[float, float]:
    span = price_range[1] - price_range[0]
    return price_range[0] - span * factor, price_range[1] + span * factor


def _intersects(first: tuple[float, float], second: tuple[float, float]) -> bool:
    return first[0] <= second[1] and second[0] <= first[1]


def _format_price(value: Decimal) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")
