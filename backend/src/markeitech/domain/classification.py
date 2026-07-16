from __future__ import annotations

from collections.abc import Sequence
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
    matched_quote, unmatched_reason = _match_quote_for_trade(
        trade,
        () if quote is None else (quote,),
        max_quote_age,
    )
    return _classify_with_quote(
        trade,
        matched_quote,
        previous_trade,
        unmatched_reason=unmatched_reason,
    )


def classify_trade_with_quote_history(
    trade: CanonicalTradeTick,
    quotes: Sequence[CanonicalQuoteTick],
    previous_trade: CanonicalTradeTick | None = None,
    *,
    max_quote_age: timedelta = DEFAULT_QUOTE_FRESHNESS,
) -> ClassifiedTrade:
    """Classify against received quotes without using event-time lookahead."""
    matched_quote, unmatched_reason = _match_quote_for_trade(trade, quotes, max_quote_age)
    return _classify_with_quote(
        trade,
        matched_quote,
        previous_trade,
        unmatched_reason=unmatched_reason,
    )


def _classify_with_quote(
    trade: CanonicalTradeTick,
    matched_quote: CanonicalQuoteTick | None,
    previous_trade: CanonicalTradeTick | None,
    *,
    unmatched_reason: str,
) -> ClassifiedTrade:
    side = TradeSide.UNKNOWN
    reason = unmatched_reason

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


def _match_quote_for_trade(
    trade: CanonicalTradeTick,
    quotes: Sequence[CanonicalQuoteTick],
    max_quote_age: timedelta,
) -> tuple[CanonicalQuoteTick | None, str]:
    if not quotes:
        return None, "no_quote_available"
    found_instrument = False
    for quote in reversed(quotes):
        if quote.instrument_id != trade.instrument_id:
            continue
        found_instrument = True
        if quote.event_ts > trade.event_ts:
            continue
        if trade.event_ts - quote.event_ts > max_quote_age:
            return None, "quote_stale"
        return quote, "matched_quote"
    if not found_instrument:
        return None, "quote_instrument_mismatch"
    return None, "no_quote_at_or_before_trade"


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
