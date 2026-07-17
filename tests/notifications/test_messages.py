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
    SignalEvaluationEvent,
)

NOW = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)


def test_health_notification_uses_a_severity_colored_embed() -> None:
    record = build_health_notification(
        trader_id="MARKEITECH-PAPER-001",
        event="MARKET_DATA_DEGRADED",
        detail="NQU6.CME=degraded(stale_trade_tick)",
        occurred_ts=NOW,
    )

    embed = record.payload["embeds"][0]
    assert embed["title"] == "Markeitech System Health"
    assert embed["color"] == 0xF39C12
    assert embed["fields"][0] == {
        "name": "Status",
        "value": "MARKET_DATA_DEGRADED",
        "inline": True,
    }
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
    )
    notifier = LocationNarrativeNotifier()

    assert notifier.observe(event, role="ACTIVE") is not None
    assert notifier.observe(event, role="ACTIVE") is None
