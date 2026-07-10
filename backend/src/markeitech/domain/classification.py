from __future__ import annotations

from datetime import timedelta

from markeitech.domain.market_data import (
    CanonicalQuoteTick,
    CanonicalTradeTick,
    ClassifiedTrade,
    TradeSide,
)

DEFAULT_QUOTE_FRESHNESS = timedelta(seconds=2)


def classify_trade(
    trade: CanonicalTradeTick,
    quote: CanonicalQuoteTick | None,
    previous_trade: CanonicalTradeTick | None = None,
    *,
    max_quote_age: timedelta = DEFAULT_QUOTE_FRESHNESS,
) -> ClassifiedTrade:
    matched_quote = _valid_quote_for_trade(trade, quote, max_quote_age)
    side = TradeSide.UNKNOWN
    reason = "no_valid_quote"

    if matched_quote is not None:
        if trade.price >= matched_quote.ask_price:
            side = TradeSide.BUY
            reason = "at_or_above_ask"
        elif trade.price <= matched_quote.bid_price:
            side = TradeSide.SELL
            reason = "at_or_below_bid"
        else:
            side, reason = _tick_rule_side(trade, previous_trade)

    return ClassifiedTrade(
        instrument_id=trade.instrument_id,
        event_ts=trade.event_ts,
        ts_init=trade.ts_init,
        event_ts_ns=trade.event_ts_ns,
        ts_init_ns=trade.ts_init_ns,
        trade=trade,
        quote=matched_quote,
        side=side,
        classification_reason=reason,
    )


def _valid_quote_for_trade(
    trade: CanonicalTradeTick,
    quote: CanonicalQuoteTick | None,
    max_quote_age: timedelta,
) -> CanonicalQuoteTick | None:
    if quote is None:
        return None
    if quote.instrument_id != trade.instrument_id:
        return None
    if quote.event_ts > trade.event_ts:
        return None
    if trade.event_ts - quote.event_ts > max_quote_age:
        return None
    return quote


def _tick_rule_side(
    trade: CanonicalTradeTick,
    previous_trade: CanonicalTradeTick | None,
) -> tuple[TradeSide, str]:
    if previous_trade is None or previous_trade.instrument_id != trade.instrument_id:
        return TradeSide.UNKNOWN, "inside_spread_no_tick_rule_reference"
    if trade.price > previous_trade.price:
        return TradeSide.BUY, "inside_spread_tick_rule_up"
    if trade.price < previous_trade.price:
        return TradeSide.SELL, "inside_spread_tick_rule_down"
    return TradeSide.UNKNOWN, "inside_spread_tick_rule_unchanged"
