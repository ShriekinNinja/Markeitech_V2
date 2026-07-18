from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from statistics import median

from markeitech.auction_pressure.contracts import (
    BarPressureDirection,
    BarPressureProxySnapshot,
)
from markeitech.domain.base import require_utc
from markeitech.domain.market_data import OneMinuteBar


def build_bar_pressure_proxy(
    instrument_id: str,
    bars: Sequence[OneMinuteBar],
    *,
    as_of: datetime,
    atr: Decimal | None,
    window_bars: int = 3,
    minimum_baseline_bars: int = 10,
) -> BarPressureProxySnapshot | None:
    """Summarize reported OHLCV pressure without claiming classified order flow."""
    as_of = require_utc(as_of)
    if window_bars < 1:
        raise ValueError("bar-pressure window must be positive")
    if minimum_baseline_bars < 1:
        raise ValueError("bar-pressure baseline must be positive")
    eligible = tuple(
        sorted(
            (
                bar
                for bar in bars
                if bar.instrument_id == instrument_id
                and bar.source == "ib"
                and bar.is_complete
                and not bar.is_revision
                and bar.close_ts <= as_of
            ),
            key=lambda bar: bar.open_ts,
        )
    )
    contiguous = _latest_contiguous(eligible)
    if len(contiguous) < window_bars:
        return None
    selected = contiguous[-window_bars:]
    up_count = sum(bar.close > bar.open for bar in selected)
    down_count = sum(bar.close < bar.open for bar in selected)
    flat_count = window_bars - up_count - down_count
    price_change = selected[-1].close - selected[0].open
    direction = BarPressureDirection.MIXED
    if price_change > 0 and up_count > down_count:
        direction = BarPressureDirection.UPWARD
    elif price_change < 0 and down_count > up_count:
        direction = BarPressureDirection.DOWNWARD
    window_high = max(bar.high for bar in selected)
    window_low = min(bar.low for bar in selected)
    window_range = window_high - window_low
    close_location = (
        Decimal("0.5")
        if window_range == 0
        else (selected[-1].close - window_low) / window_range
    )
    baseline = tuple(
        bar.volume
        for bar in eligible
        if bar.close_ts <= selected[0].open_ts and bar.volume > 0
    )
    pace_ratio = None
    if len(baseline) >= minimum_baseline_bars:
        baseline_volume = Decimal(median(baseline[-minimum_baseline_bars:]))
        if baseline_volume > 0:
            observed_volume = sum((bar.volume for bar in selected), Decimal("0"))
            pace_ratio = observed_volume / Decimal(window_bars) / baseline_volume
    return BarPressureProxySnapshot(
        instrument_id=instrument_id,
        start_ts=selected[0].open_ts,
        end_ts=selected[-1].close_ts,
        as_of=as_of,
        direction=direction,
        window_bars=window_bars,
        up_bar_count=up_count,
        down_bar_count=down_count,
        flat_bar_count=flat_count,
        price_change=price_change,
        atr_fraction=None if atr is None or atr <= 0 else price_change / atr,
        close_location=close_location,
        total_volume=sum((bar.volume for bar in selected), Decimal("0")),
        pace_ratio=pace_ratio,
    )


def _latest_contiguous(bars: Sequence[OneMinuteBar]) -> tuple[OneMinuteBar, ...]:
    if not bars:
        return ()
    latest = [bars[-1]]
    for bar in reversed(bars[:-1]):
        if bar.close_ts != latest[0].open_ts:
            break
        latest.insert(0, bar)
    return tuple(latest)
