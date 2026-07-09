from datetime import UTC, datetime, timedelta
from decimal import Decimal

from markeitech.domain import CanonicalQuoteTick, CanonicalTradeTick, TradeSide, classify_trade


def utc_now() -> datetime:
    return datetime(2026, 7, 9, 12, 0, tzinfo=UTC)


def trade(price: str, *, event_ts: datetime | None = None) -> CanonicalTradeTick:
    ts = event_ts or utc_now()
    return CanonicalTradeTick(
        instrument_id="NQU6.CME",
        event_ts=ts,
        ts_init=ts,
        price=Decimal(price),
        size=Decimal("2"),
    )


def quote(*, event_ts: datetime | None = None) -> CanonicalQuoteTick:
    ts = event_ts or utc_now()
    return CanonicalQuoteTick(
        instrument_id="NQU6.CME",
        event_ts=ts,
        ts_init=ts,
        bid_price=Decimal("20000.00"),
        ask_price=Decimal("20000.50"),
        bid_size=Decimal("10"),
        ask_size=Decimal("12"),
    )


def test_classifies_trade_at_or_above_ask_as_buy() -> None:
    classified = classify_trade(trade("20000.50"), quote())

    assert classified.side == TradeSide.BUY
    assert classified.buy_volume == Decimal("2")
    assert classified.delta == Decimal("2")
    assert classified.classification_reason == "at_or_above_ask"


def test_classifies_trade_at_or_below_bid_as_sell() -> None:
    classified = classify_trade(trade("20000.00"), quote())

    assert classified.side == TradeSide.SELL
    assert classified.sell_volume == Decimal("2")
    assert classified.delta == Decimal("-2")
    assert classified.classification_reason == "at_or_below_bid"


def test_inside_spread_uses_tick_rule_up() -> None:
    previous = trade("20000.10", event_ts=utc_now() - timedelta(milliseconds=100))
    classified = classify_trade(trade("20000.25"), quote(), previous_trade=previous)

    assert classified.side == TradeSide.BUY
    assert classified.classification_reason == "inside_spread_tick_rule_up"


def test_inside_spread_uses_tick_rule_down() -> None:
    previous = trade("20000.40", event_ts=utc_now() - timedelta(milliseconds=100))
    classified = classify_trade(trade("20000.25"), quote(), previous_trade=previous)

    assert classified.side == TradeSide.SELL
    assert classified.classification_reason == "inside_spread_tick_rule_down"


def test_inside_spread_without_tick_rule_reference_is_unknown() -> None:
    classified = classify_trade(trade("20000.25"), quote())

    assert classified.side == TradeSide.UNKNOWN
    assert classified.unknown_volume == Decimal("2")
    assert classified.classified_volume_ratio == Decimal("0")


def test_future_quote_is_not_valid_for_trade() -> None:
    classified = classify_trade(trade("20000.50"), quote(event_ts=utc_now() + timedelta(seconds=1)))

    assert classified.side == TradeSide.UNKNOWN
    assert classified.quote is None
    assert classified.classification_reason == "no_valid_quote"


def test_stale_quote_is_not_valid_for_trade() -> None:
    classified = classify_trade(
        trade("20000.50"),
        quote(event_ts=utc_now() - timedelta(seconds=3)),
        max_quote_age=timedelta(seconds=2),
    )

    assert classified.side == TradeSide.UNKNOWN
    assert classified.quote is None
    assert classified.classification_reason == "no_valid_quote"
