from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from markeitech.domain import (
    BarInterval,
    CanonicalQuoteTick,
    CanonicalTradeTick,
    OneMinuteBar,
)
from pydantic import ValidationError


def utc_now() -> datetime:
    return datetime(2026, 7, 9, 12, 0, tzinfo=UTC)


def trade(**overrides: object) -> CanonicalTradeTick:
    values = {
        "instrument_id": "NQU6.CME",
        "event_ts": utc_now(),
        "ts_init": utc_now(),
        "price": Decimal("20000.25"),
        "size": Decimal("3"),
        "sequence": 10,
    }
    values.update(overrides)
    return CanonicalTradeTick(**values)


def quote(**overrides: object) -> CanonicalQuoteTick:
    values = {
        "instrument_id": "NQU6.CME",
        "event_ts": utc_now(),
        "ts_init": utc_now(),
        "bid_price": Decimal("20000.00"),
        "ask_price": Decimal("20000.50"),
        "bid_size": Decimal("4"),
        "ask_size": Decimal("6"),
        "sequence": 20,
    }
    values.update(overrides)
    return CanonicalQuoteTick(**values)


def test_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError, match="timezone-aware UTC"):
        trade(event_ts=datetime(2026, 7, 9, 12, 0))


def test_rejects_non_utc_timestamp() -> None:
    with pytest.raises(ValidationError, match="timestamp must be UTC"):
        trade(event_ts=datetime(2026, 7, 9, 8, 0, tzinfo=timezone(timedelta(hours=-4))))


def test_trade_dedupe_key_is_stable() -> None:
    first = trade()
    second = trade()

    assert first.dedupe_key == second.dedupe_key


def test_quote_rejects_crossed_market() -> None:
    with pytest.raises(ValidationError, match="ask price"):
        quote(bid_price=Decimal("20001.00"), ask_price=Decimal("20000.50"))


def test_one_minute_bar_volume_and_delta() -> None:
    bar = OneMinuteBar(
        instrument_id="NQU6.CME",
        event_ts=utc_now() + timedelta(minutes=1),
        ts_init=utc_now() + timedelta(minutes=1),
        open_ts=utc_now(),
        close_ts=utc_now() + timedelta(minutes=1),
        interval=BarInterval.ONE_MINUTE,
        open=Decimal("20000.00"),
        high=Decimal("20010.00"),
        low=Decimal("19990.00"),
        close=Decimal("20005.00"),
        volume=Decimal("10"),
        buy_volume=Decimal("6"),
        sell_volume=Decimal("3"),
        unknown_volume=Decimal("1"),
    )

    assert bar.delta == Decimal("3")
    assert bar.classified_volume_ratio == Decimal("0.9")
    assert bar.dedupe_key == "bar:NQU6.CME:1m:2026-07-09T12:00:00+00:00"


def test_bar_rejects_volume_mismatch() -> None:
    with pytest.raises(ValidationError, match="classified volumes"):
        OneMinuteBar(
            instrument_id="NQU6.CME",
            event_ts=utc_now() + timedelta(minutes=1),
            ts_init=utc_now() + timedelta(minutes=1),
            open_ts=utc_now(),
            close_ts=utc_now() + timedelta(minutes=1),
            open=Decimal("20000.00"),
            high=Decimal("20010.00"),
            low=Decimal("19990.00"),
            close=Decimal("20005.00"),
            volume=Decimal("10"),
            buy_volume=Decimal("6"),
            sell_volume=Decimal("3"),
            unknown_volume=Decimal("0"),
        )
