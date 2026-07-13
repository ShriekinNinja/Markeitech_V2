from __future__ import annotations

from typing import Any

from markeitech.analytics.contracts import (
    AnalysisBar,
    AnalyticsInputFidelity,
    AnalyticsTimeframe,
)
from markeitech.domain.base import utc_datetime_from_unix_ns
from markeitech.domain.market_data import OneMinuteBar


def analysis_bar_from_nautilus(bar: Any, *, source: str = "ib") -> AnalysisBar:
    timeframe = AnalyticsTimeframe.from_duration(bar.bar_type.spec.timedelta)
    open_ts = utc_datetime_from_unix_ns(bar.ts_event)
    return AnalysisBar(
        instrument_id=str(bar.bar_type.instrument_id),
        timeframe=timeframe,
        open_ts=open_ts,
        close_ts=open_ts + timeframe.duration,
        open=bar.open.as_decimal(),
        high=bar.high.as_decimal(),
        low=bar.low.as_decimal(),
        close=bar.close.as_decimal(),
        volume=bar.volume.as_decimal(),
        source=source,
        input_fidelity=AnalyticsInputFidelity.REPORTED,
    )


def analysis_bar_from_one_minute(bar: OneMinuteBar) -> AnalysisBar:
    if not bar.is_complete:
        raise ValueError("analytics requires a completed one-minute bar")
    return AnalysisBar(
        instrument_id=bar.instrument_id,
        timeframe=AnalyticsTimeframe.ONE_MINUTE,
        open_ts=bar.open_ts,
        close_ts=bar.close_ts,
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
        volume=bar.volume,
        source=bar.source,
        input_fidelity=(
            AnalyticsInputFidelity.INFERRED
            if bar.source == "classified_ticks"
            else AnalyticsInputFidelity.REPORTED
        ),
    )
