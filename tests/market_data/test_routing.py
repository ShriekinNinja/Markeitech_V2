from __future__ import annotations

from typing import Any

import pytest
from markeitech.domain import (
    CanonicalQuoteTick,
    CanonicalTradeTick,
    ClassifiedTrade,
    OneMinuteBar,
    TradeSide,
)
from markeitech.market_data import LiveMarketDataRouter
from nautilus_trader.model.data import Bar, BarType, QuoteTick, TradeTick
from nautilus_trader.model.enums import AggressorSide
from nautilus_trader.model.identifiers import InstrumentId, TradeId
from nautilus_trader.model.objects import Price, Quantity

EVENT_NS = 1_786_360_123_456_789_123
INIT_NS = 1_786_360_123_500_000_000


def trade_tick(
    instrument_id: str = "NQU6.CME",
    *,
    event_ns: int = EVENT_NS,
) -> TradeTick:
    return TradeTick(
        instrument_id=InstrumentId.from_str(instrument_id),
        price=Price.from_str("20000.25"),
        size=Quantity.from_str("3"),
        aggressor_side=AggressorSide.BUYER,
        trade_id=TradeId("trade-123"),
        ts_event=event_ns,
        ts_init=max(INIT_NS, event_ns + 1_000_000),
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


def one_minute_bar() -> Bar:
    return Bar(
        bar_type=BarType.from_str("ESU6.CME-1-MINUTE-LAST-EXTERNAL"),
        open=Price.from_str("6000.00"),
        high=Price.from_str("6002.00"),
        low=Price.from_str("5999.00"),
        close=Price.from_str("6001.25"),
        volume=Quantity.from_str("20"),
        ts_event=EVENT_NS,
        ts_init=EVENT_NS + 60_000_000_000,
    )


def test_router_tracks_instruments_and_emits_normalized_events() -> None:
    active = ["NQU6.CME"]
    events: list[Any] = []
    router = LiveMarketDataRouter(
        instrument_ids={"NQU6.CME", "ESU6.CME"},
        active_instrument_id=lambda: active[0],
        on_event=events.append,
    )

    quote = router.handle_quote_tick(quote_tick())
    classified = router.handle_trade_tick(trade_tick())
    bar = router.handle_bar(one_minute_bar())

    assert isinstance(quote, CanonicalQuoteTick)
    assert isinstance(classified, ClassifiedTrade)
    assert classified.side == TradeSide.UNKNOWN
    assert router.snapshot("NQU6.CME").trade_tick_count == 1
    assert router.snapshot("NQU6.CME").quote_tick_count == 1
    assert router.snapshot("ESU6.CME").bar_count == 1
    assert router.snapshot("ESU6.CME").latest_bar == bar
    assert [type(event) for event in events] == [
        CanonicalQuoteTick,
        CanonicalTradeTick,
        ClassifiedTrade,
        OneMinuteBar,
        type(bar),
    ]
    assert router.snapshot("NQU6.CME").active_bar is not None
    assert router.snapshot("NQU6.CME").active_bar.is_complete is False


def test_router_reflects_runtime_active_instrument_change() -> None:
    active = ["NQU6.CME"]
    router = LiveMarketDataRouter(
        instrument_ids={"NQU6.CME", "ESU6.CME"},
        active_instrument_id=lambda: active[0],
    )

    active[0] = "ESU6.CME"

    assert router.snapshot("NQU6.CME").is_active is False
    assert router.snapshot("ESU6.CME").is_active is True


def test_promoting_instrument_resets_only_its_partial_tick_bar() -> None:
    active = ["NQU6.CME"]
    router = LiveMarketDataRouter(
        instrument_ids={"NQU6.CME", "ESU6.CME"},
        active_instrument_id=lambda: active[0],
    )
    router.handle_quote_tick(quote_tick())
    router.handle_trade_tick(trade_tick())
    assert router.snapshot("NQU6.CME").active_bar is not None

    active[0] = "ESU6.CME"
    router.activate_instrument("ESU6.CME")

    assert router.snapshot("ESU6.CME").active_bar is None
    assert router.snapshot("NQU6.CME").active_bar is not None


def test_router_rejects_unconfigured_instrument_data() -> None:
    router = LiveMarketDataRouter(
        instrument_ids={"NQU6.CME"},
        active_instrument_id=lambda: "NQU6.CME",
    )

    with pytest.raises(ValueError, match="unconfigured instrument"):
        router.handle_trade_tick(trade_tick("ESU6.CME"))


def test_active_tick_bar_rolls_to_completed_bar_at_next_minute() -> None:
    events: list[Any] = []
    router = LiveMarketDataRouter(
        instrument_ids={"NQU6.CME"},
        active_instrument_id=lambda: "NQU6.CME",
        on_event=events.append,
    )
    router.handle_quote_tick(quote_tick())
    router.handle_trade_tick(trade_tick())

    router.handle_trade_tick(trade_tick(event_ns=EVENT_NS + 61_000_000_000))

    tick_bars = [
        event
        for event in events
        if isinstance(event, OneMinuteBar) and event.source == "classified_ticks"
    ]
    assert [bar.is_complete for bar in tick_bars] == [False, True, False]
    assert tick_bars[1].volume == 3
    assert tick_bars[1].unknown_volume == 3
    assert tick_bars[1].ts_init > tick_bars[1].event_ts
    assert tick_bars[2].volume == 3


def test_router_records_and_drops_ib_sentinel_quote() -> None:
    router = LiveMarketDataRouter(
        instrument_ids={"NQU6.CME"},
        active_instrument_id=lambda: "NQU6.CME",
    )
    sentinel = QuoteTick(
        instrument_id=InstrumentId.from_str("NQU6.CME"),
        bid_price=Price.from_str("-1"),
        ask_price=Price.from_str("-1"),
        bid_size=Quantity.from_str("0"),
        ask_size=Quantity.from_str("0"),
        ts_event=EVENT_NS,
        ts_init=INIT_NS,
    )

    assert router.handle_quote_tick(sentinel) is None
    snapshot = router.snapshot("NQU6.CME")
    assert snapshot.quote_tick_count == 0
    assert snapshot.dropped_event_count == 1
    assert "bid=-1" in snapshot.last_drop_reason
