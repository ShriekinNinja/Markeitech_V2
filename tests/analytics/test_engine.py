from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from markeitech.analytics import (
    AnalysisBar,
    AnalyticsInputFidelity,
    AnalyticsTimeframe,
    FairValueGapDirection,
    MarketContextEngine,
    ProfileLocation,
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


def canonical_bar(
    index: int,
    *,
    start: datetime,
    source_name: str = "ib",
) -> OneMinuteBar:
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
        source=source_name,
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
    assert snapshot.prior_session_high == Decimal("100.5")
    assert snapshot.prior_session_low == Decimal("99.5")


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


def test_named_session_and_opening_ranges_use_timezone_aware_windows() -> None:
    new_york_open = datetime(2026, 7, 13, 13, 30, tzinfo=UTC)
    snapshot = MarketContextEngine(DailySessions()).initialize_bars(
        tuple(analysis_bar(index, start=new_york_open) for index in range(31))
    )[0]

    assert snapshot.new_york_range is not None
    assert snapshot.new_york_range.is_complete is False
    assert snapshot.new_york_opening_range_15 is not None
    assert snapshot.new_york_opening_range_15.is_complete is True
    assert snapshot.new_york_opening_range_30 is not None
    assert snapshot.new_york_opening_range_30.is_complete is True
    assert snapshot.new_york_opening_range_30.start_ts == new_york_open
    assert snapshot.new_york_opening_range_30.end_ts == new_york_open + timedelta(minutes=30)


def test_confirmed_unfilled_fair_value_gap_is_exposed() -> None:
    bars = (
        analysis_bar(0, close=Decimal("100")),
        analysis_bar(1, close=Decimal("101")),
        analysis_bar(2, close=Decimal("103")),
    )

    snapshot = MarketContextEngine(DailySessions()).initialize_bars(bars)[0]

    assert len(snapshot.fair_value_gaps) == 1
    gap = snapshot.fair_value_gaps[0]
    assert gap.direction == FairValueGapDirection.BULLISH
    assert gap.lower == Decimal("100.5")
    assert gap.upper == Decimal("102.5")
    assert gap.is_filled is False


def test_inferred_volume_profile_uses_configured_bins_and_classifies_location() -> None:
    bars = (
        analysis_bar(0, close=Decimal("100"), volume=Decimal("10")),
        analysis_bar(1, close=Decimal("105"), volume=Decimal("100")),
        analysis_bar(2, close=Decimal("110"), volume=Decimal("10")),
    )
    engine = MarketContextEngine(
        DailySessions(),
        profile_bin_sizes={"NQU6.CME": Decimal("5")},
    )

    snapshot = engine.initialize_bars(bars)[0]

    assert snapshot.volume_profile is not None
    assert snapshot.volume_profile.bin_size == Decimal("5")
    assert snapshot.volume_profile.poc == Decimal("105")
    assert snapshot.volume_profile.value_area_low == Decimal("100")
    assert snapshot.volume_profile.value_area_high == Decimal("110")
    assert snapshot.volume_profile.input_fidelity == AnalyticsInputFidelity.INFERRED
    assert snapshot.profile_location == ProfileLocation.UPPER_VALUE
    assert snapshot.location_reason_codes == ("close_in_upper_value",)
    assert snapshot.direction_score == 1
    assert "above_session_vwap" in snapshot.direction_location_reason_codes


def test_higher_timeframe_profile_does_not_look_ahead_into_newer_minute_bars() -> None:
    bars = (
        *tuple(analysis_bar(index, volume=Decimal("10")) for index in range(10)),
        analysis_bar(
            0,
            timeframe=AnalyticsTimeframe.FIVE_MINUTES,
            volume=Decimal("50"),
        ),
    )

    snapshots = MarketContextEngine(DailySessions()).initialize_bars(bars)
    five_minute = next(
        snapshot for snapshot in snapshots if snapshot.timeframe == AnalyticsTimeframe.FIVE_MINUTES
    )

    assert five_minute.volume_profile is not None
    assert five_minute.volume_profile.total_volume == Decimal("50")


def test_composite_profiles_require_exact_resolved_session_counts() -> None:
    bars = tuple(
        analysis_bar(
            minute,
            start=START + timedelta(days=day),
            close=Decimal("100") + day,
        )
        for day in range(5)
        for minute in range(2)
    )
    engine = MarketContextEngine(
        DailySessions(),
        profile_bin_sizes={"NQU6.CME": Decimal("1")},
        profile_composite_sessions={"NQU6.CME": (2, 5)},
    )

    snapshot = engine.initialize_bars(bars)[0]

    assert [value.session_count for value in snapshot.composite_volume_profiles] == [2, 5]
    two_session, five_session = snapshot.composite_volume_profiles
    assert two_session.start_ts == START.replace(hour=0) + timedelta(days=3)
    assert two_session.end_ts == START + timedelta(days=4, minutes=2)
    assert two_session.is_complete is False
    assert two_session.profile.total_volume == Decimal("40")
    assert five_session.start_ts == START.replace(hour=0)
    assert five_session.profile.total_volume == Decimal("100")


def test_composite_profile_omits_periods_without_enough_sessions() -> None:
    bars = tuple(analysis_bar(0, start=START + timedelta(days=day)) for day in range(3))
    engine = MarketContextEngine(
        DailySessions(),
        profile_composite_sessions={"NQU6.CME": (2, 5)},
    )

    snapshot = engine.initialize_bars(bars)[0]

    assert [value.session_count for value in snapshot.composite_volume_profiles] == [2]


def test_composite_profile_does_not_include_structure_bars_after_snapshot() -> None:
    current = analysis_bar(0, start=START + timedelta(days=1))
    future = analysis_bar(0, start=START + timedelta(days=2), volume=Decimal("1000"))
    higher_timeframe = analysis_bar(
        0,
        timeframe=AnalyticsTimeframe.FIVE_MINUTES,
        start=START + timedelta(days=1),
    )
    engine = MarketContextEngine(
        DailySessions(),
        profile_composite_sessions={"NQU6.CME": (2,)},
    )

    snapshots = engine.initialize_bars((analysis_bar(0), current, future, higher_timeframe))
    five_minute = next(
        snapshot for snapshot in snapshots if snapshot.timeframe == AnalyticsTimeframe.FIVE_MINUTES
    )

    assert len(five_minute.composite_volume_profiles) == 1
    assert five_minute.composite_volume_profiles[0].profile.total_volume == Decimal("20")
    feature = engine.feature_for(five_minute)
    one_minute_lineage = next(
        item
        for item in feature.input_lineage
        if item.timeframe == AnalyticsTimeframe.ONE_MINUTE
    )
    assert one_minute_lineage.event_count == 2
    assert one_minute_lineage.end_ts <= five_minute.as_of


def test_warmup_context_is_emitted_in_top_down_analysis_order() -> None:
    bars = (
        analysis_bar(0),
        analysis_bar(0, timeframe=AnalyticsTimeframe.FIVE_MINUTES),
        analysis_bar(0, timeframe=AnalyticsTimeframe.FIFTEEN_MINUTES),
        analysis_bar(0, timeframe=AnalyticsTimeframe.THIRTY_MINUTES),
        analysis_bar(0, timeframe=AnalyticsTimeframe.ONE_HOUR),
        analysis_bar(0, timeframe=AnalyticsTimeframe.DAILY),
    )

    snapshots = MarketContextEngine(DailySessions()).initialize_bars(bars)

    assert [snapshot.timeframe for snapshot in snapshots] == [
        AnalyticsTimeframe.DAILY,
        AnalyticsTimeframe.ONE_HOUR,
        AnalyticsTimeframe.FIFTEEN_MINUTES,
        AnalyticsTimeframe.FIVE_MINUTES,
        AnalyticsTimeframe.THIRTY_MINUTES,
        AnalyticsTimeframe.ONE_MINUTE,
    ]


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


def test_restart_seeds_forming_bucket_and_preserves_mixed_lineage() -> None:
    live_start = datetime(2026, 7, 13, 10, tzinfo=UTC)
    engine = MarketContextEngine(DailySessions())
    engine.initialize_bars(
        (
            analysis_bar(0, start=live_start - timedelta(minutes=1)),
            *(analysis_bar(index, start=live_start) for index in range(3)),
            analysis_bar(
                0,
                timeframe=AnalyticsTimeframe.FIVE_MINUTES,
                start=live_start - timedelta(minutes=5),
            ),
        )
    )

    engine.update_one_minute(canonical_bar(3, start=live_start, source_name="classified_ticks"))
    engine.update_one_minute(canonical_bar(4, start=live_start, source_name="classified_ticks"))
    updates = engine.update_one_minute(
        canonical_bar(5, start=live_start, source_name="classified_ticks")
    )

    five_minute = next(
        item for item in updates if item.timeframe == AnalyticsTimeframe.FIVE_MINUTES
    )
    assert five_minute.as_of == live_start + timedelta(minutes=5)
    assert five_minute.source == "mixed"
    assert five_minute.input_fidelity == AnalyticsInputFidelity.MIXED


def test_missing_seeded_minute_still_prevents_aggregate_fabrication() -> None:
    live_start = datetime(2026, 7, 13, 10, tzinfo=UTC)
    engine = MarketContextEngine(DailySessions())
    engine.initialize_bars(
        (
            analysis_bar(0, start=live_start - timedelta(minutes=1)),
            analysis_bar(0, start=live_start),
            analysis_bar(2, start=live_start),
            analysis_bar(
                0,
                timeframe=AnalyticsTimeframe.FIVE_MINUTES,
                start=live_start - timedelta(minutes=5),
            ),
        )
    )

    for index in (3, 4):
        engine.update_one_minute(canonical_bar(index, start=live_start))
    updates = engine.update_one_minute(canonical_bar(5, start=live_start))

    assert [item.timeframe for item in updates] == [AnalyticsTimeframe.ONE_MINUTE]


def test_completed_warmup_bucket_is_not_emitted_again_after_restart() -> None:
    live_start = datetime(2026, 7, 13, 10, tzinfo=UTC)
    engine = MarketContextEngine(DailySessions())
    engine.initialize_bars(
        (
            *(analysis_bar(index, start=live_start) for index in range(5)),
            analysis_bar(
                0,
                timeframe=AnalyticsTimeframe.FIVE_MINUTES,
                start=live_start,
            ),
        )
    )

    first_updates = engine.update_one_minute(canonical_bar(5, start=live_start))
    for index in range(6, 10):
        engine.update_one_minute(canonical_bar(index, start=live_start))
    boundary_updates = engine.update_one_minute(canonical_bar(10, start=live_start))

    assert [item.timeframe for item in first_updates] == [AnalyticsTimeframe.ONE_MINUTE]
    assert {item.timeframe for item in boundary_updates} == {
        AnalyticsTimeframe.ONE_MINUTE,
        AnalyticsTimeframe.FIVE_MINUTES,
    }


def test_restarted_aggregate_matches_uninterrupted_market_values() -> None:
    historical_start = datetime(2026, 7, 13, 9, tzinfo=UTC)
    live_start = datetime(2026, 7, 13, 10, tzinfo=UTC)
    baseline = (
        analysis_bar(0, start=historical_start),
        analysis_bar(
            0,
            timeframe=AnalyticsTimeframe.FIVE_MINUTES,
            start=historical_start,
        ),
    )
    uninterrupted = MarketContextEngine(DailySessions())
    uninterrupted.initialize_bars(baseline)
    for index in range(6):
        uninterrupted.update_one_minute(
            canonical_bar(index, start=live_start, source_name="classified_ticks")
        )

    restarted = MarketContextEngine(DailySessions())
    restarted.initialize_bars(
        (
            *baseline,
            *(analysis_bar(index, start=live_start) for index in range(3)),
        )
    )
    for index in range(3, 6):
        restarted.update_one_minute(
            canonical_bar(index, start=live_start, source_name="classified_ticks")
        )

    uninterrupted_snapshot = next(
        item
        for item in uninterrupted.snapshots
        if item.timeframe == AnalyticsTimeframe.FIVE_MINUTES
    )
    restarted_snapshot = next(
        item for item in restarted.snapshots if item.timeframe == AnalyticsTimeframe.FIVE_MINUTES
    )
    assert restarted_snapshot.close == uninterrupted_snapshot.close
    assert restarted_snapshot.session_high == uninterrupted_snapshot.session_high
    assert restarted_snapshot.session_low == uninterrupted_snapshot.session_low
    assert restarted_snapshot.session_vwap == uninterrupted_snapshot.session_vwap
    assert restarted_snapshot.source == "mixed"
    assert uninterrupted_snapshot.source == "classified_ticks"


def test_restart_seeding_continues_forming_hour_without_extra_hour_delay() -> None:
    live_start = datetime(2026, 7, 13, 10, tzinfo=UTC)
    engine = MarketContextEngine(DailySessions())
    engine.initialize_bars(
        (
            analysis_bar(0, start=live_start - timedelta(minutes=1)),
            *(analysis_bar(index, start=live_start) for index in range(23)),
            analysis_bar(
                0,
                timeframe=AnalyticsTimeframe.ONE_HOUR,
                start=live_start - timedelta(hours=1),
            ),
        )
    )

    for index in range(23, 60):
        engine.update_one_minute(
            canonical_bar(index, start=live_start, source_name="classified_ticks")
        )
    updates = engine.update_one_minute(
        canonical_bar(60, start=live_start, source_name="classified_ticks")
    )

    one_hour = next(item for item in updates if item.timeframe == AnalyticsTimeframe.ONE_HOUR)
    assert one_hour.as_of == live_start + timedelta(hours=1)
    assert one_hour.input_fidelity == AnalyticsInputFidelity.MIXED
