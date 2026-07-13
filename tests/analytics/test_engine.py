from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from markeitech.analytics import (
    AnalysisBar,
    AnalyticsInputFidelity,
    AnalyticsTimeframe,
    MarketContextEngine,
    TrendState,
    VwapPosition,
)
from markeitech.domain import OneMinuteBar

START = datetime(2026, 7, 13, 8, tzinfo=UTC)


class DailySessions:
    def session_window(
        self,
        instrument_id: str,
        timestamp: datetime,
    ) -> tuple[datetime, datetime]:
        del instrument_id
        start = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=1)


class OffsetSessions:
    def session_window(
        self,
        instrument_id: str,
        timestamp: datetime,
    ) -> tuple[datetime, datetime]:
        del instrument_id
        start = timestamp.replace(hour=13, minute=30, second=0, microsecond=0)
        return start, start + timedelta(hours=6, minutes=30)


def analysis_bar(
    index: int,
    *,
    timeframe: AnalyticsTimeframe = AnalyticsTimeframe.ONE_MINUTE,
    start: datetime = START,
    close: Decimal | None = None,
    volume: Decimal = Decimal("10"),
) -> AnalysisBar:
    open_ts = start + index * timeframe.duration
    price = close if close is not None else Decimal("100") + Decimal(index) / Decimal("4")
    return AnalysisBar(
        instrument_id="NQU6.CME",
        timeframe=timeframe,
        open_ts=open_ts,
        close_ts=open_ts + timeframe.duration,
        open=price - Decimal("0.25"),
        high=price + Decimal("0.5"),
        low=price - Decimal("0.5"),
        close=price,
        volume=volume,
        source="ib",
        input_fidelity=AnalyticsInputFidelity.REPORTED,
    )


def canonical_bar(index: int, *, start: datetime) -> OneMinuteBar:
    source = analysis_bar(index, start=start)
    return OneMinuteBar(
        instrument_id=source.instrument_id,
        event_ts=source.close_ts,
        ts_init=source.close_ts,
        open_ts=source.open_ts,
        close_ts=source.close_ts,
        open=source.open,
        high=source.high,
        low=source.low,
        close=source.close,
        volume=source.volume,
        buy_volume=Decimal("0"),
        sell_volume=Decimal("0"),
        unknown_volume=source.volume,
        source=source.source,
    )


def test_warmup_builds_direction_location_and_nautilus_indicators() -> None:
    engine = MarketContextEngine(DailySessions())

    snapshots = engine.initialize_bars(tuple(analysis_bar(index) for index in range(220)))
    snapshot = snapshots[0]

    assert snapshot.trend == TrendState.BULLISH
    assert snapshot.input_fidelity == AnalyticsInputFidelity.REPORTED
    assert snapshot.trend_reason_codes == ("close_above_ema_stack", "ema20_rising")
    assert snapshot.ema_20 is not None
    assert snapshot.ema_50 is not None
    assert snapshot.ema_200 is not None
    assert snapshot.ema_20 > snapshot.ema_50 > snapshot.ema_200
    assert snapshot.atr_14 is not None
    assert snapshot.session_vwap is not None
    assert snapshot.vwap_position == VwapPosition.ABOVE
    assert Decimal("0") <= snapshot.session_range_position <= Decimal("1")
    assert snapshot.nearest_support is not None
    assert snapshot.nearest_support.price <= snapshot.close
    assert snapshot.nearest_resistance is not None
    assert snapshot.nearest_resistance.price >= snapshot.close


def test_short_warmup_is_explicitly_insufficient_not_directional() -> None:
    snapshot = MarketContextEngine(DailySessions()).initialize_bars(
        tuple(analysis_bar(index) for index in range(10))
    )[0]

    assert snapshot.trend == TrendState.INSUFFICIENT_DATA
    assert snapshot.trend_reason_codes == ("fewer_than_50_bars",)
    assert snapshot.ema_20 is None
    assert snapshot.atr_14 is None


def test_session_vwap_uses_only_latest_resolved_session() -> None:
    first_day = tuple(
        analysis_bar(index, close=Decimal("100"), volume=Decimal("100")) for index in range(5)
    )
    second_start = START + timedelta(days=1)
    second_day = tuple(
        analysis_bar(
            index,
            start=second_start,
            close=Decimal("200"),
            volume=Decimal("1"),
        )
        for index in range(5)
    )

    snapshot = MarketContextEngine(DailySessions()).initialize_bars(first_day + second_day)[0]

    assert snapshot.session_open == Decimal("199.75")
    assert snapshot.session_vwap == Decimal("200")


def test_daily_context_treats_daily_bar_as_session_summary() -> None:
    midnight = datetime(2026, 7, 13, tzinfo=UTC)
    snapshot = MarketContextEngine(OffsetSessions()).initialize_bars(
        (
            analysis_bar(
                0,
                timeframe=AnalyticsTimeframe.DAILY,
                start=midnight,
            ),
        )
    )[0]

    assert snapshot.timeframe == AnalyticsTimeframe.DAILY
    assert snapshot.session_open == Decimal("99.75")
    assert snapshot.session_vwap == Decimal("100")


def test_live_one_minute_bars_update_context_and_complete_configured_aggregates() -> None:
    engine = MarketContextEngine(DailySessions())
    engine.initialize_bars(
        (
            *tuple(analysis_bar(index) for index in range(60)),
            analysis_bar(0, timeframe=AnalyticsTimeframe.FIVE_MINUTES),
        )
    )
    live_start = datetime(2026, 7, 13, 10, tzinfo=UTC)

    for index in range(5):
        updates = engine.update_one_minute(canonical_bar(index, start=live_start))
        assert len(updates) == 1
    boundary_updates = engine.update_one_minute(canonical_bar(5, start=live_start))

    assert {item.timeframe for item in boundary_updates} == {
        AnalyticsTimeframe.ONE_MINUTE,
        AnalyticsTimeframe.FIVE_MINUTES,
    }
    five_minute = next(
        item for item in engine.snapshots if item.timeframe == AnalyticsTimeframe.FIVE_MINUTES
    )
    assert five_minute.bar_count == 2


def test_missing_minute_prevents_higher_timeframe_fabrication() -> None:
    engine = MarketContextEngine(DailySessions())
    engine.initialize_bars(
        (
            *tuple(analysis_bar(index) for index in range(60)),
            analysis_bar(0, timeframe=AnalyticsTimeframe.FIVE_MINUTES),
        )
    )
    live_start = datetime(2026, 7, 13, 10, tzinfo=UTC)

    for index in (0, 1, 3, 4):
        engine.update_one_minute(canonical_bar(index, start=live_start))
    boundary_updates = engine.update_one_minute(canonical_bar(5, start=live_start))

    assert [item.timeframe for item in boundary_updates] == [AnalyticsTimeframe.ONE_MINUTE]
    five_minute = next(
        item for item in engine.snapshots if item.timeframe == AnalyticsTimeframe.FIVE_MINUTES
    )
    assert five_minute.bar_count == 1


def test_live_aggregates_align_to_product_session_open() -> None:
    live_start = datetime(2026, 7, 13, 13, 30, tzinfo=UTC)
    engine = MarketContextEngine(OffsetSessions())
    engine.initialize_bars(
        (
            analysis_bar(0, start=live_start),
            analysis_bar(
                0,
                timeframe=AnalyticsTimeframe.ONE_HOUR,
                start=live_start,
            ),
        )
    )

    for index in range(60):
        engine.update_one_minute(canonical_bar(index, start=live_start))
    updates = engine.update_one_minute(canonical_bar(60, start=live_start))

    one_hour = next(item for item in updates if item.timeframe == AnalyticsTimeframe.ONE_HOUR)
    assert one_hour.as_of == datetime(2026, 7, 13, 14, 30, tzinfo=UTC)
