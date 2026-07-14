from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from markeitech.analytics import (
    AnalysisBar,
    AnalyticsDepthStatus,
    AnalyticsFreshnessStatus,
    AnalyticsInputFidelity,
    AnalyticsReadinessEvaluator,
    AnalyticsReadinessStatus,
    AnalyticsTimeframe,
)
from markeitech.market_data.actor import format_analytics_readiness

INSTRUMENT = "NQU6.CME"
EVALUATED = datetime(2026, 7, 14, 12, 7, 30, tzinfo=UTC)


class ContinuousSessions:
    def expected_minute_opens(
        self,
        instrument_id: str,
        start_ts: datetime,
        end_ts: datetime,
    ) -> tuple[datetime, ...]:
        del instrument_id
        cursor = start_ts.replace(second=0, microsecond=0)
        if cursor < start_ts:
            cursor += timedelta(minutes=1)
        values: list[datetime] = []
        while cursor < end_ts:
            values.append(cursor)
            cursor += timedelta(minutes=1)
        return tuple(values)

    def session_window(
        self,
        instrument_id: str,
        timestamp: datetime,
    ) -> tuple[datetime, datetime]:
        del instrument_id
        start = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=1)


class CmeLikeSessions(ContinuousSessions):
    def expected_minute_opens(
        self,
        instrument_id: str,
        start_ts: datetime,
        end_ts: datetime,
    ) -> tuple[datetime, ...]:
        values = super().expected_minute_opens(instrument_id, start_ts, end_ts)
        return tuple(value for value in values if value.hour != 21)

    def session_window(
        self,
        instrument_id: str,
        timestamp: datetime,
    ) -> tuple[datetime, datetime]:
        del instrument_id
        if timestamp.hour >= 22:
            start = timestamp.replace(hour=22, minute=0, second=0, microsecond=0)
        else:
            start = timestamp.replace(hour=22, minute=0, second=0, microsecond=0) - timedelta(
                days=1
            )
        return start, start + timedelta(hours=23)


def bars_ending_at(
    timeframe: AnalyticsTimeframe,
    close_ts: datetime,
    *,
    count: int = 200,
) -> tuple[AnalysisBar, ...]:
    return tuple(
        AnalysisBar(
            instrument_id=INSTRUMENT,
            timeframe=timeframe,
            open_ts=close_ts - (count - index) * timeframe.duration,
            close_ts=close_ts - (count - index - 1) * timeframe.duration,
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            volume=Decimal("10"),
            source="ib",
            input_fidelity=AnalyticsInputFidelity.REPORTED,
        )
        for index in range(count)
    )


def evaluator(*timeframes: AnalyticsTimeframe) -> AnalyticsReadinessEvaluator:
    return AnalyticsReadinessEvaluator(
        ContinuousSessions(),
        {INSTRUMENT: {timeframe: 5 for timeframe in timeframes}},
    )


def test_all_current_full_depth_timeframes_are_ready() -> None:
    values = (
        *bars_ending_at(AnalyticsTimeframe.ONE_MINUTE, EVALUATED.replace(second=0)),
        *bars_ending_at(
            AnalyticsTimeframe.FIVE_MINUTES,
            EVALUATED.replace(minute=5, second=0),
        ),
        *bars_ending_at(
            AnalyticsTimeframe.ONE_HOUR,
            EVALUATED.replace(minute=0, second=0),
        ),
        *bars_ending_at(
            AnalyticsTimeframe.DAILY,
            EVALUATED.replace(hour=0, minute=0, second=0),
        ),
    )

    snapshot = evaluator(
        AnalyticsTimeframe.ONE_MINUTE,
        AnalyticsTimeframe.FIVE_MINUTES,
        AnalyticsTimeframe.ONE_HOUR,
        AnalyticsTimeframe.DAILY,
    ).evaluate_bars(values, evaluated_ts=EVALUATED)

    assert snapshot.status == AnalyticsReadinessStatus.READY
    assert [item.timeframe for item in snapshot.instruments[0].timeframes] == [
        AnalyticsTimeframe.DAILY,
        AnalyticsTimeframe.ONE_HOUR,
        AnalyticsTimeframe.FIVE_MINUTES,
        AnalyticsTimeframe.ONE_MINUTE,
    ]
    assert all(
        item.freshness == AnalyticsFreshnessStatus.CURRENT
        and item.depth == AnalyticsDepthStatus.FULL
        for item in snapshot.instruments[0].timeframes
    )
    message = format_analytics_readiness(snapshot.instruments[0])
    assert message.startswith(f"ANALYTICS_READY | {INSTRUMENT} | status=READY")
    assert message.index("1d=current") < message.index("1h=current")
    assert message.index("1h=current") < message.index("5m=current")


def test_stale_higher_timeframe_degrades_but_does_not_block() -> None:
    values = (
        *bars_ending_at(AnalyticsTimeframe.ONE_MINUTE, EVALUATED.replace(second=0)),
        *bars_ending_at(
            AnalyticsTimeframe.FIVE_MINUTES,
            EVALUATED.replace(minute=0, second=0),
        ),
    )

    snapshot = evaluator(
        AnalyticsTimeframe.ONE_MINUTE,
        AnalyticsTimeframe.FIVE_MINUTES,
    ).evaluate_bars(values, evaluated_ts=EVALUATED)

    assert snapshot.status == AnalyticsReadinessStatus.DEGRADED
    five_minute = snapshot.instruments[0].timeframes[0]
    assert five_minute.freshness == AnalyticsFreshnessStatus.STALE
    assert five_minute.lag_intervals == 1


def test_one_interval_stale_one_minute_context_is_tolerated_at_startup() -> None:
    values = bars_ending_at(
        AnalyticsTimeframe.ONE_MINUTE,
        EVALUATED.replace(minute=6, second=0),
    )

    snapshot = evaluator(AnalyticsTimeframe.ONE_MINUTE).evaluate_bars(
        values,
        evaluated_ts=EVALUATED,
    )

    assert snapshot.status == AnalyticsReadinessStatus.DEGRADED
    assert snapshot.instruments[0].reason_codes == ("one_minute_startup_lag_tolerated",)


def test_two_interval_stale_one_minute_context_blocks_live_readiness() -> None:
    values = bars_ending_at(
        AnalyticsTimeframe.ONE_MINUTE,
        EVALUATED.replace(minute=5, second=0),
    )

    snapshot = evaluator(AnalyticsTimeframe.ONE_MINUTE).evaluate_bars(
        values,
        evaluated_ts=EVALUATED,
    )

    assert snapshot.status == AnalyticsReadinessStatus.BLOCKED
    assert snapshot.instruments[0].reason_codes == ("one_minute_not_current",)


def test_current_but_shallow_history_is_degraded_not_stale() -> None:
    values = bars_ending_at(
        AnalyticsTimeframe.ONE_MINUTE,
        EVALUATED.replace(second=0),
        count=49,
    )

    snapshot = evaluator(AnalyticsTimeframe.ONE_MINUTE).evaluate_bars(
        values,
        evaluated_ts=EVALUATED,
    )
    result = snapshot.instruments[0].timeframes[0]

    assert snapshot.status == AnalyticsReadinessStatus.DEGRADED
    assert result.freshness == AnalyticsFreshnessStatus.CURRENT
    assert result.depth == AnalyticsDepthStatus.INSUFFICIENT


def test_future_dated_history_is_unavailable_and_blocks() -> None:
    values = bars_ending_at(
        AnalyticsTimeframe.ONE_MINUTE,
        EVALUATED + timedelta(minutes=2),
        count=200,
    )

    snapshot = evaluator(AnalyticsTimeframe.ONE_MINUTE).evaluate_bars(
        values,
        evaluated_ts=EVALUATED,
    )
    result = snapshot.instruments[0].timeframes[0]

    assert snapshot.status == AnalyticsReadinessStatus.BLOCKED
    assert result.freshness == AnalyticsFreshnessStatus.UNAVAILABLE
    assert "future_dated_historical_bar" in result.reason_codes


def test_currently_forming_bar_is_ignored_for_freshness_and_depth() -> None:
    completed = bars_ending_at(
        AnalyticsTimeframe.ONE_MINUTE,
        EVALUATED.replace(second=0),
        count=200,
    )
    forming = bars_ending_at(
        AnalyticsTimeframe.ONE_MINUTE,
        EVALUATED.replace(second=0) + timedelta(minutes=1),
        count=1,
    )[0]

    snapshot = evaluator(AnalyticsTimeframe.ONE_MINUTE).evaluate_bars(
        (*completed, forming),
        evaluated_ts=EVALUATED,
    )
    result = snapshot.instruments[0].timeframes[0]

    assert result.freshness == AnalyticsFreshnessStatus.CURRENT
    assert result.observed_latest_close == EVALUATED.replace(second=0)
    assert result.bar_count == 200


def test_maintenance_break_uses_last_completed_session_minute() -> None:
    evaluated = datetime(2026, 7, 14, 21, 30, tzinfo=UTC)
    evaluator = AnalyticsReadinessEvaluator(
        CmeLikeSessions(),
        {INSTRUMENT: {AnalyticsTimeframe.ONE_MINUTE: 5}},
    )
    values = bars_ending_at(
        AnalyticsTimeframe.ONE_MINUTE,
        datetime(2026, 7, 14, 21, 0, tzinfo=UTC),
    )

    snapshot = evaluator.evaluate_bars(values, evaluated_ts=evaluated)
    result = snapshot.instruments[0].timeframes[0]

    assert result.expected_latest_close == datetime(2026, 7, 14, 21, 0, tzinfo=UTC)
    assert result.freshness == AnalyticsFreshnessStatus.CURRENT
