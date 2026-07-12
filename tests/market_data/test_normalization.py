from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from markeitech.market_data import (
    MarketDataNormalizationError,
    normalize_one_minute_bar,
    normalize_quote_tick,
    normalize_trade_tick,
)
from nautilus_trader.model.data import Bar, BarType, QuoteTick, TradeTick
from nautilus_trader.model.enums import AggressorSide
from nautilus_trader.model.identifiers import InstrumentId, TradeId
from nautilus_trader.model.objects import Price, Quantity

EVENT_NS = 1_786_360_123_456_789_123
INIT_NS = 1_786_360_123_500_000_000


def trade_tick(instrument_id: str = "NQU6.CME") -> TradeTick:
    return TradeTick(
        instrument_id=InstrumentId.from_str(instrument_id),
        price=Price.from_str("20000.25"),
        size=Quantity.from_str("3"),
        aggressor_side=AggressorSide.BUYER,
        trade_id=TradeId("trade-123"),
        ts_event=EVENT_NS,
        ts_init=INIT_NS,
    )


def quote_tick(instrument_id: str = "NQU6.CME") -> QuoteTick:
    return QuoteTick(
        instrument_id=InstrumentId.from_str(instrument_id),
        bid_price=Price.from_str("20000.00"),
        ask_price=Price.from_str("20000.50"),
        bid_size=Quantity.from_str("4"),
        ask_size=Quantity.from_str("6"),
        ts_event=EVENT_NS,
        ts_init=INIT_NS,
    )


def one_minute_bar(instrument_id: str = "ESU6.CME") -> Bar:
    return Bar(
        bar_type=BarType.from_str(f"{instrument_id}-1-MINUTE-LAST-EXTERNAL"),
        open=Price.from_str("6000.00"),
        high=Price.from_str("6002.00"),
        low=Price.from_str("5999.00"),
        close=Price.from_str("6001.25"),
        volume=Quantity.from_str("20"),
        ts_event=EVENT_NS,
        ts_init=EVENT_NS + 60_000_000_000,
    )


def test_normalizes_trade_and_preserves_nanosecond_identity() -> None:
    normalized = normalize_trade_tick(trade_tick())

    assert normalized.instrument_id == "NQU6.CME"
    assert normalized.price == Decimal("20000.25")
    assert normalized.size == Decimal("3")
    assert normalized.source_trade_id == "trade-123"
    assert normalized.event_ts_ns == EVENT_NS
    assert normalized.event_ts == datetime(2026, 8, 10, 11, 8, 43, 456789, tzinfo=UTC)
    assert str(EVENT_NS) in normalized.dedupe_key


def test_normalizes_quote_values_without_float_conversion() -> None:
    normalized = normalize_quote_tick(quote_tick())

    assert normalized.bid_price == Decimal("20000.00")
    assert normalized.ask_price == Decimal("20000.50")
    assert normalized.bid_size == Decimal("4")
    assert normalized.ask_size == Decimal("6")
    assert normalized.event_ts_ns == EVENT_NS


def test_normalizes_external_bar_from_open_timestamp_to_explicit_interval() -> None:
    normalized = normalize_one_minute_bar(one_minute_bar())

    assert normalized.instrument_id == "ESU6.CME"
    assert normalized.open_ts == datetime(2026, 8, 10, 11, 8, 43, 456789, tzinfo=UTC)
    assert normalized.close_ts == datetime(2026, 8, 10, 11, 9, 43, 456789, tzinfo=UTC)
    assert normalized.event_ts == normalized.close_ts
    assert normalized.volume == Decimal("20")
    assert normalized.buy_volume == 0
    assert normalized.sell_volume == 0
    assert normalized.unknown_volume == Decimal("20")


def test_rejects_non_one_minute_bar() -> None:
    bar = Bar(
        bar_type=BarType.from_str("ESU6.CME-5-MINUTE-LAST-EXTERNAL"),
        open=Price.from_str("6000.00"),
        high=Price.from_str("6002.00"),
        low=Price.from_str("5999.00"),
        close=Price.from_str("6001.25"),
        volume=Quantity.from_str("20"),
        ts_event=EVENT_NS,
        ts_init=INIT_NS,
    )

    with pytest.raises(ValueError, match="expected a one-minute bar"):
        normalize_one_minute_bar(bar)


def test_rejects_ib_closed_market_sentinel_quote() -> None:
    tick = QuoteTick(
        instrument_id=InstrumentId.from_str("NQU6.CME"),
        bid_price=Price.from_str("-1"),
        ask_price=Price.from_str("-1"),
        bid_size=Quantity.from_str("0"),
        ask_size=Quantity.from_str("0"),
        ts_event=EVENT_NS,
        ts_init=INIT_NS,
    )

    with pytest.raises(MarketDataNormalizationError, match="invalid quote tick values"):
        normalize_quote_tick(tick)


def test_rejects_crossed_ib_quote() -> None:
    tick = QuoteTick(
        instrument_id=InstrumentId.from_str("BTC/USD.PAXOS"),
        bid_price=Price.from_str("63695.50"),
        ask_price=Price.from_str("63693.00"),
        bid_size=Quantity.from_str("0"),
        ask_size=Quantity.from_str("0"),
        ts_event=EVENT_NS,
        ts_init=INIT_NS,
    )

    with pytest.raises(MarketDataNormalizationError, match="invalid quote tick values"):
        normalize_quote_tick(tick)
