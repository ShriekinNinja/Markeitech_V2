from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from markeitech.analytics import (
    AnalyticsInputFidelity,
    AnalyticsTimeframe,
    ContextLevel,
    LevelKind,
    MarketContextSnapshot,
    TrendState,
    VwapPosition,
)
from markeitech.auction_pressure import (
    BarPressureDirection,
    BarPressureProxySnapshot,
)
from markeitech.notifications import (
    ApproachingLocationNotifier,
    LocationNarrativeNotifier,
    build_health_notification,
    build_market_context_notifications,
)
from markeitech.signals import (
    DirectionQualificationStatus,
    LocationEpisodeEventType,
    LocationQualificationStatus,
    LocationSourceKind,
    SignalDirection,
    SignalEvaluationEvent,
    SignalEvidenceFidelity,
    SignalLocationMatch,
    SignalLocationZone,
    SignalLocationZoneKind,
)

NOW = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)


def location_match() -> SignalLocationMatch:
    zone = SignalLocationZone(
        instrument_id="NQU6.CME",
        direction=SignalDirection.LONG,
        source_kind=LocationSourceKind.STRUCTURAL_LEVEL,
        zone_kind=SignalLocationZoneKind.SUPPORT,
        timeframe=AnalyticsTimeframe.FIVE_MINUTES,
        zone_anchor="five_minute_support",
        source_feature_id="a" * 64,
        observed_ts=NOW - timedelta(minutes=5),
        lower_price=Decimal("29950"),
        upper_price=Decimal("29955"),
        fidelity=SignalEvidenceFidelity.INFERRED,
        reason_codes=("nearest_support",),
    )
    return SignalLocationMatch(
        zone=zone,
        evaluation_feature_id="b" * 64,
        observed_ts=NOW,
        observed_price=Decimal("29952.75"),
        distance=Decimal("0"),
        tolerance=Decimal("3"),
        fidelity=SignalEvidenceFidelity.INFERRED,
        reason_codes=("matched_support",),
    )


def test_health_notification_uses_a_severity_colored_embed() -> None:
    record = build_health_notification(
        trader_id="MARKEITECH-PAPER-001",
        event="MARKET_DATA_DEGRADED",
        facts=(
            ("Source", "IB"),
            ("Feed lag", "13 ms"),
            ("Instruments", "**NQU6.CME:** Not Ready — Waiting For Trade Tick"),
        ),
        occurred_ts=NOW,
    )

    embed = record.payload["embeds"][0]
    assert "content" not in record.payload
    assert embed["title"] == "Market Data Degraded"
    assert "description" not in embed
    assert embed["color"] == 0xF39C12
    assert embed["fields"][0] == {
        "name": "Runtime",
        "value": "MARKEITECH-PAPER-001",
        "inline": True,
    }
    assert embed["fields"][1]["value"] == "IB"
    assert embed["fields"][3]["inline"] is False
    assert embed["footer"]["text"] == "No Obstacles, Only Challenges"


def test_market_context_routes_the_instrument_from_operator_lines() -> None:
    snapshot = MarketContextSnapshot(
        instrument_id="NQU6.CME",
        timeframe=AnalyticsTimeframe.ONE_MINUTE,
        as_of=NOW,
        source="classified_ticks",
        input_fidelity=AnalyticsInputFidelity.INFERRED,
        bar_count=251,
        close=Decimal("30000"),
        atr_14=Decimal("10"),
        session_open=Decimal("29900"),
        session_high=Decimal("30020"),
        session_low=Decimal("29880"),
        session_vwap=Decimal("29990"),
        session_range_position=Decimal("0.85"),
        vwap_position=VwapPosition.ABOVE,
        trend=TrendState.BULLISH,
        trend_reason_codes=("test",),
        direction_score=2,
    )

    record = build_market_context_notifications(
        (snapshot,),
        phase="live",
        active_instrument_id="NQU6.CME",
        pressure=None,
        occurred_ts=NOW,
    )[0]

    assert record.aggregate_key == "NQU6.CME"
    assert "Nasdaq 100 Futures market brief" in record.payload["content"]
    embed = record.payload["embeds"][0]
    assert embed["title"] == "Nasdaq 100 Futures — Market Brief"
    assert embed["description"] == "Primary market • Live update"
    assert embed["color"] == 0x2ECC71
    assert [field["name"] for field in embed["fields"]] == [
        "Directional bias",
        "Value location",
        "Price and value",
        "Trend map",
        "Key levels",
        "Auction structure",
        "Fair value gaps",
    ]
    assert embed["fields"][0]["value"] == "**Strong bullish alignment**\nScore: +2 of 2"


def test_market_context_exposes_reported_bar_pressure_without_claiming_delta() -> None:
    snapshot = MarketContextSnapshot(
        instrument_id="ESU6.CME",
        timeframe=AnalyticsTimeframe.ONE_MINUTE,
        as_of=NOW,
        source="ib",
        input_fidelity=AnalyticsInputFidelity.REPORTED,
        bar_count=251,
        close=Decimal("7517.50"),
        atr_14=Decimal("10"),
        session_open=Decimal("7491.25"),
        session_high=Decimal("7575"),
        session_low=Decimal("7491.25"),
        session_range_position=Decimal("0.31"),
        vwap_position=VwapPosition.BELOW,
        trend=TrendState.BEARISH,
        trend_reason_codes=("test",),
        direction_score=-1,
    )
    proxy = BarPressureProxySnapshot(
        instrument_id="ESU6.CME",
        start_ts=NOW - timedelta(minutes=3),
        end_ts=NOW,
        as_of=NOW,
        direction=BarPressureDirection.DOWNWARD,
        window_bars=3,
        up_bar_count=1,
        down_bar_count=2,
        flat_bar_count=0,
        price_change=Decimal("-4.25"),
        atr_fraction=Decimal("-0.425"),
        close_location=Decimal("0.2"),
        total_volume=Decimal("600"),
        pace_ratio=Decimal("1.25"),
    )

    record = build_market_context_notifications(
        (snapshot,),
        phase="live",
        active_instrument_id="NQU6.CME",
        pressure=None,
        bar_pressure={"ESU6.CME": proxy},
        occurred_ts=NOW,
    )[0]

    field = record.payload["embeds"][0]["fields"][-1]
    assert field["name"] == "1m Bar Pressure Proxy"
    assert "Downward price pressure" in field["value"]
    assert "-0.42 ATR" in field["value"]
    assert "1.25x baseline" in field["value"]
    assert "Not bid/ask delta" in field["value"]


@pytest.mark.parametrize(
    ("score", "expected_color"),
    ((-2, 0xE74C3C), (-1, 0xE74C3C), (0, 0xFFFFFF), (1, 0x2ECC71), (2, 0x2ECC71)),
)
def test_market_context_color_tracks_direction_score(
    score: int,
    expected_color: int,
) -> None:
    snapshot = MarketContextSnapshot(
        instrument_id="NQU6.CME",
        timeframe=AnalyticsTimeframe.ONE_MINUTE,
        as_of=NOW,
        source="classified_ticks",
        input_fidelity=AnalyticsInputFidelity.INFERRED,
        bar_count=251,
        close=Decimal("30000"),
        session_open=Decimal("29900"),
        session_high=Decimal("30020"),
        session_low=Decimal("29880"),
        session_range_position=Decimal("0.85"),
        vwap_position=VwapPosition.ABOVE,
        trend=TrendState.RANGE,
        trend_reason_codes=("test",),
        direction_score=score,
    )

    record = build_market_context_notifications(
        (snapshot,),
        phase="live",
        active_instrument_id="NQU6.CME",
        pressure=None,
        occurred_ts=NOW,
    )[0]

    assert record.payload["embeds"][0]["color"] == expected_color


def test_approaching_location_is_deduplicated_until_price_leaves() -> None:
    snapshot = MarketContextSnapshot(
        instrument_id="NQU6.CME",
        timeframe=AnalyticsTimeframe.ONE_MINUTE,
        as_of=NOW,
        source="classified_ticks",
        input_fidelity=AnalyticsInputFidelity.INFERRED,
        bar_count=251,
        close=Decimal("29999"),
        atr_14=Decimal("10"),
        session_open=Decimal("29900"),
        session_high=Decimal("30020"),
        session_low=Decimal("29880"),
        session_range_position=Decimal("0.85"),
        vwap_position=VwapPosition.ABOVE,
        trend=TrendState.BULLISH,
        trend_reason_codes=("test",),
        nearest_resistance=ContextLevel(
            kind=LevelKind.SWING_RESISTANCE,
            price=Decimal("30000"),
            observed_ts=NOW - timedelta(minutes=5),
        ),
        direction_score=1,
    )
    notifier = ApproachingLocationNotifier()

    assert notifier.observe(snapshot) is not None
    assert notifier.observe(snapshot) is None


def test_repeated_holding_narrative_is_suppressed() -> None:
    event = SignalEvaluationEvent(
        instrument_id="NQU6.CME",
        definition_id="intraday_context",
        evaluation_ts=NOW,
        direction_status=DirectionQualificationStatus.QUALIFIED,
        location_status=LocationQualificationStatus.QUALIFIED,
        episode_event=LocationEpisodeEventType.ACTIVE,
        signal_id="signal-1",
        signal_status=None,
        signal_direction=SignalDirection.LONG,
        observed_price=Decimal("30000"),
        location_matches=(location_match(),),
    )
    notifier = LocationNarrativeNotifier()

    record = notifier.observe(event, role="ACTIVE")
    assert record is not None
    assert record.payload["embeds"][0]["title"] == (
        "Holding 5m Support — Nasdaq 100 Futures"
    )
    assert record.payload["embeds"][0]["description"] == (
        "Price remains engaged with 5m Support at 29,950.00 – 29,955.00."
    )
    assert "content" not in record.payload
    assert [field["name"] for field in record.payload["embeds"][0]["fields"]] == [
        "Direction",
        "Instrument role",
        "Observed price",
        "Location",
        "Evidence",
    ]
    assert record.payload["embeds"][0]["fields"][0]["value"] == "Long"
    assert notifier.observe(event, role="ACTIVE") is None
