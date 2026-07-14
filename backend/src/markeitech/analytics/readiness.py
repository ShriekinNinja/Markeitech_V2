from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timedelta
from enum import StrEnum
from math import ceil
from typing import Any, Protocol

from pydantic import Field, field_validator

from markeitech.analytics.contracts import AnalysisBar, AnalyticsTimeframe
from markeitech.analytics.normalization import analysis_bar_from_nautilus
from markeitech.domain.base import VersionedDomainModel, require_utc

_MINUTE = timedelta(minutes=1)
_EXPECTED_BAR_QUERY_WINDOW = timedelta(days=30)
_FULL_INDICATOR_DEPTH = 200
_DIRECTIONAL_DEPTH = 50


class AnalyticsFreshnessStatus(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


class AnalyticsDepthStatus(StrEnum):
    FULL = "full"
    PARTIAL = "partial"
    INSUFFICIENT = "insufficient"


class AnalyticsReadinessStatus(StrEnum):
    READY = "ready"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


class TimeframeAnalyticsReadiness(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    timeframe: AnalyticsTimeframe
    evaluated_ts: datetime
    expected_latest_close: datetime | None = None
    observed_latest_close: datetime | None = None
    lookback_sessions: int = Field(ge=1)
    bar_count: int = Field(ge=0)
    freshness: AnalyticsFreshnessStatus
    lag_intervals: int = Field(ge=0)
    depth: AnalyticsDepthStatus
    required_full_depth_bars: int = Field(default=_FULL_INDICATOR_DEPTH, ge=1)
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator("evaluated_ts", "expected_latest_close", "observed_latest_close")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)


class InstrumentAnalyticsReadiness(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    status: AnalyticsReadinessStatus
    timeframes: tuple[TimeframeAnalyticsReadiness, ...] = Field(min_length=1)
    reason_codes: tuple[str, ...] = Field(min_length=1)


class AnalyticsReadinessSnapshot(VersionedDomainModel):
    status: AnalyticsReadinessStatus
    evaluated_ts: datetime
    instruments: tuple[InstrumentAnalyticsReadiness, ...] = Field(min_length=1)
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator("evaluated_ts")
    @classmethod
    def _evaluated_ts_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)


class AnalyticsCalendar(Protocol):
    def expected_minute_opens(
        self,
        instrument_id: str,
        start_ts: datetime,
        end_ts: datetime,
    ) -> tuple[datetime, ...]: ...

    def session_window(
        self,
        instrument_id: str,
        timestamp: datetime,
    ) -> tuple[datetime, datetime]: ...


class AnalyticsReadinessEvaluator:
    def __init__(
        self,
        calendar: AnalyticsCalendar,
        requirements: Mapping[str, Mapping[AnalyticsTimeframe, int]],
    ) -> None:
        if not requirements or any(not timeframes for timeframes in requirements.values()):
            raise ValueError("analytics readiness requires configured instrument timeframes")
        self._calendar = calendar
        self._requirements = {
            instrument_id: dict(timeframes) for instrument_id, timeframes in requirements.items()
        }
        if any(
            sessions < 1
            for timeframes in self._requirements.values()
            for sessions in timeframes.values()
        ):
            raise ValueError("analytics readiness lookbacks must be positive")

    def evaluate(
        self,
        data_by_bar_type: Mapping[str, Sequence[Any]],
        *,
        evaluated_ts: datetime,
    ) -> AnalyticsReadinessSnapshot:
        evaluated_ts = require_utc(evaluated_ts)
        bars: dict[tuple[str, AnalyticsTimeframe], list[AnalysisBar]] = defaultdict(list)
        for values in data_by_bar_type.values():
            for value in values:
                normalized = analysis_bar_from_nautilus(value)
                bars[(normalized.instrument_id, normalized.timeframe)].append(normalized)

        return self.evaluate_bars(
            tuple(bar for values in bars.values() for bar in values),
            evaluated_ts=evaluated_ts,
        )

    def evaluate_bars(
        self,
        values: Sequence[AnalysisBar],
        *,
        evaluated_ts: datetime,
    ) -> AnalyticsReadinessSnapshot:
        evaluated_ts = require_utc(evaluated_ts)
        bars: dict[tuple[str, AnalyticsTimeframe], list[AnalysisBar]] = defaultdict(list)
        for bar in values:
            bars[(bar.instrument_id, bar.timeframe)].append(bar)

        instruments: list[InstrumentAnalyticsReadiness] = []
        for instrument_id in sorted(self._requirements):
            timeframe_results = tuple(
                self._evaluate_timeframe(
                    instrument_id,
                    timeframe,
                    self._requirements[instrument_id][timeframe],
                    bars.get((instrument_id, timeframe), []),
                    evaluated_ts,
                )
                for timeframe in _ordered_timeframes(self._requirements[instrument_id])
            )
            status, reasons = _instrument_status(timeframe_results)
            instruments.append(
                InstrumentAnalyticsReadiness(
                    instrument_id=instrument_id,
                    status=status,
                    timeframes=timeframe_results,
                    reason_codes=reasons,
                )
            )
        status = _worst_status(item.status for item in instruments)
        return AnalyticsReadinessSnapshot(
            status=status,
            evaluated_ts=evaluated_ts,
            instruments=tuple(instruments),
            reason_codes=(f"instrument_status_{status.value}",),
        )

    def _evaluate_timeframe(
        self,
        instrument_id: str,
        timeframe: AnalyticsTimeframe,
        lookback_sessions: int,
        bars: Sequence[AnalysisBar],
        evaluated_ts: datetime,
    ) -> TimeframeAnalyticsReadiness:
        ordered = sorted(bars, key=lambda bar: bar.open_ts)
        has_future_bar = any(
            bar.open_ts > evaluated_ts or bar.close_ts > evaluated_ts + timeframe.duration
            for bar in ordered
        )
        completed = [bar for bar in ordered if bar.close_ts <= evaluated_ts]
        expected_close = _expected_latest_close(
            self._calendar,
            instrument_id,
            timeframe,
            evaluated_ts,
        )
        observed = completed[-1] if completed else None
        if has_future_bar:
            freshness = AnalyticsFreshnessStatus.UNAVAILABLE
            lag = 0
            freshness_reason = "future_dated_historical_bar"
        else:
            freshness, lag, freshness_reason = _freshness(
                timeframe,
                observed,
                expected_close,
                evaluated_ts,
            )
        depth, depth_reason = _depth(len(completed))
        return TimeframeAnalyticsReadiness(
            instrument_id=instrument_id,
            timeframe=timeframe,
            evaluated_ts=evaluated_ts,
            expected_latest_close=expected_close,
            observed_latest_close=None if observed is None else observed.close_ts,
            lookback_sessions=lookback_sessions,
            bar_count=len(completed),
            freshness=freshness,
            lag_intervals=lag,
            depth=depth,
            reason_codes=(freshness_reason, depth_reason),
        )


def _expected_latest_close(
    calendar: AnalyticsCalendar,
    instrument_id: str,
    timeframe: AnalyticsTimeframe,
    evaluated_ts: datetime,
) -> datetime | None:
    expected_opens = calendar.expected_minute_opens(
        instrument_id,
        evaluated_ts - _EXPECTED_BAR_QUERY_WINDOW,
        evaluated_ts,
    )
    completed_minutes = [value for value in expected_opens if value + _MINUTE <= evaluated_ts]
    if not completed_minutes:
        return None
    if timeframe == AnalyticsTimeframe.DAILY:
        return _latest_completed_session_close(
            calendar,
            instrument_id,
            completed_minutes,
            evaluated_ts,
        )
    return _latest_completed_intraday_close(
        calendar,
        instrument_id,
        completed_minutes,
        timeframe.duration,
        evaluated_ts,
    )


def _latest_completed_session_close(
    calendar: AnalyticsCalendar,
    instrument_id: str,
    minute_opens: Sequence[datetime],
    evaluated_ts: datetime,
) -> datetime | None:
    session_open, session_close = calendar.session_window(instrument_id, minute_opens[-1])
    if session_close <= evaluated_ts:
        return session_close
    prior = [value for value in minute_opens if value < session_open]
    if not prior:
        return None
    _, prior_close = calendar.session_window(instrument_id, prior[-1])
    return prior_close


def _latest_completed_intraday_close(
    calendar: AnalyticsCalendar,
    instrument_id: str,
    minute_opens: Sequence[datetime],
    duration: timedelta,
    evaluated_ts: datetime,
) -> datetime | None:
    remaining = list(minute_opens)
    while remaining:
        latest_minute = remaining[-1]
        session_open, session_close = calendar.session_window(instrument_id, latest_minute)
        elapsed = latest_minute - session_open
        bucket_start = session_open + (elapsed // duration) * duration
        bucket_close = bucket_start + duration
        limit = min(session_close, evaluated_ts)
        while bucket_close > limit:
            bucket_start -= duration
            bucket_close -= duration
        if bucket_start >= session_open:
            return bucket_close
        remaining = [value for value in remaining if value < session_open]
    return None


def _freshness(
    timeframe: AnalyticsTimeframe,
    observed: AnalysisBar | None,
    expected_close: datetime | None,
    evaluated_ts: datetime,
) -> tuple[AnalyticsFreshnessStatus, int, str]:
    if observed is None:
        return AnalyticsFreshnessStatus.UNAVAILABLE, 0, "historical_bars_unavailable"
    if observed.open_ts > evaluated_ts or observed.close_ts > evaluated_ts + timeframe.duration:
        return AnalyticsFreshnessStatus.UNAVAILABLE, 0, "future_dated_historical_bar"
    if expected_close is None:
        return AnalyticsFreshnessStatus.UNAVAILABLE, 0, "expected_close_unavailable"
    if timeframe == AnalyticsTimeframe.DAILY:
        expected_date = expected_close.date()
        observed_dates = {observed.open_ts.date(), observed.close_ts.date()}
        if expected_date in observed_dates or max(observed_dates) >= expected_date:
            return AnalyticsFreshnessStatus.CURRENT, 0, "latest_completed_session_present"
        lag = max(1, (expected_date - max(observed_dates)).days)
        return AnalyticsFreshnessStatus.STALE, lag, "latest_completed_session_missing"
    lag_duration = expected_close - observed.close_ts
    if lag_duration <= timedelta(0):
        return AnalyticsFreshnessStatus.CURRENT, 0, "latest_completed_interval_present"
    lag = max(1, ceil(lag_duration / timeframe.duration))
    return AnalyticsFreshnessStatus.STALE, lag, "completed_intervals_missing"


def _depth(bar_count: int) -> tuple[AnalyticsDepthStatus, str]:
    if bar_count >= _FULL_INDICATOR_DEPTH:
        return AnalyticsDepthStatus.FULL, "ema200_depth_available"
    if bar_count >= _DIRECTIONAL_DEPTH:
        return AnalyticsDepthStatus.PARTIAL, "ema50_depth_available"
    return AnalyticsDepthStatus.INSUFFICIENT, "fewer_than_50_bars"


def _instrument_status(
    timeframes: Sequence[TimeframeAnalyticsReadiness],
) -> tuple[AnalyticsReadinessStatus, tuple[str, ...]]:
    if any(item.freshness == AnalyticsFreshnessStatus.UNAVAILABLE for item in timeframes):
        return AnalyticsReadinessStatus.BLOCKED, ("required_timeframe_unavailable",)
    one_minute = next(
        (item for item in timeframes if item.timeframe == AnalyticsTimeframe.ONE_MINUTE),
        None,
    )
    if one_minute is None or one_minute.freshness != AnalyticsFreshnessStatus.CURRENT:
        return AnalyticsReadinessStatus.BLOCKED, ("one_minute_not_current",)
    if any(
        item.freshness == AnalyticsFreshnessStatus.STALE or item.depth != AnalyticsDepthStatus.FULL
        for item in timeframes
    ):
        return AnalyticsReadinessStatus.DEGRADED, ("timeframe_context_degraded",)
    return AnalyticsReadinessStatus.READY, ("all_timeframes_current_and_full_depth",)


def _worst_status(statuses: Iterable[AnalyticsReadinessStatus]) -> AnalyticsReadinessStatus:
    rank = {
        AnalyticsReadinessStatus.READY: 0,
        AnalyticsReadinessStatus.DEGRADED: 1,
        AnalyticsReadinessStatus.BLOCKED: 2,
    }
    return max(tuple(statuses), key=rank.__getitem__)


def _ordered_timeframes(
    timeframes: Mapping[AnalyticsTimeframe, Any],
) -> tuple[AnalyticsTimeframe, ...]:
    order = (
        AnalyticsTimeframe.DAILY,
        AnalyticsTimeframe.ONE_HOUR,
        AnalyticsTimeframe.FIFTEEN_MINUTES,
        AnalyticsTimeframe.FIVE_MINUTES,
        AnalyticsTimeframe.THIRTY_MINUTES,
        AnalyticsTimeframe.ONE_MINUTE,
    )
    return tuple(timeframe for timeframe in order if timeframe in timeframes)
