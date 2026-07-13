from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from markeitech.domain.base import require_utc, unix_ns_from_utc_datetime, utc_datetime_from_unix_ns
from markeitech.domain.market_data import (
    CanonicalQuoteTick,
    CanonicalTradeTick,
    OneMinuteBar,
)

ONE_MINUTE_NS = 60_000_000_000


class MarketDataNormalizationError(ValueError):
    pass


def normalize_trade_tick(tick: Any, *, source: str = "ib") -> CanonicalTradeTick:
    price = tick.price.as_decimal()
    size = tick.size.as_decimal()
    if price <= 0 or size <= 0:
        raise MarketDataNormalizationError(
            f"invalid trade tick values for {tick.instrument_id}: price={price}, size={size}"
        )
    return CanonicalTradeTick(
        instrument_id=str(tick.instrument_id),
        event_ts=utc_datetime_from_unix_ns(tick.ts_event),
        ts_init=utc_datetime_from_unix_ns(tick.ts_init),
        event_ts_ns=tick.ts_event,
        ts_init_ns=tick.ts_init,
        price=price,
        size=size,
        source_trade_id=str(tick.trade_id),
        source=source,
    )


def normalize_quote_tick(tick: Any, *, source: str = "ib") -> CanonicalQuoteTick:
    bid_price = tick.bid_price.as_decimal()
    ask_price = tick.ask_price.as_decimal()
    bid_size = tick.bid_size.as_decimal()
    ask_size = tick.ask_size.as_decimal()
    if bid_price <= 0 or ask_price <= 0 or bid_price > ask_price or bid_size < 0 or ask_size < 0:
        raise MarketDataNormalizationError(
            f"invalid quote tick values for {tick.instrument_id}: "
            f"bid={bid_price}, ask={ask_price}, bid_size={bid_size}, ask_size={ask_size}"
        )
    return CanonicalQuoteTick(
        instrument_id=str(tick.instrument_id),
        event_ts=utc_datetime_from_unix_ns(tick.ts_event),
        ts_init=utc_datetime_from_unix_ns(tick.ts_init),
        event_ts_ns=tick.ts_event,
        ts_init_ns=tick.ts_init,
        bid_price=bid_price,
        ask_price=ask_price,
        bid_size=bid_size,
        ask_size=ask_size,
        source=source,
    )


def normalize_one_minute_bar(
    bar: Any,
    *,
    source: str = "ib",
    received_ts: datetime | None = None,
) -> OneMinuteBar:
    duration = bar.bar_type.spec.timedelta
    if duration != timedelta(minutes=1):
        raise ValueError(f"expected a one-minute bar, received {bar.bar_type}")

    open_ts_ns = bar.ts_event
    close_ts_ns = open_ts_ns + ONE_MINUTE_NS
    init_ts_ns = (
        bar.ts_init if received_ts is None else unix_ns_from_utc_datetime(require_utc(received_ts))
    )
    volume = bar.volume.as_decimal()
    return OneMinuteBar(
        instrument_id=str(bar.bar_type.instrument_id),
        event_ts=utc_datetime_from_unix_ns(close_ts_ns),
        ts_init=utc_datetime_from_unix_ns(init_ts_ns),
        event_ts_ns=close_ts_ns,
        ts_init_ns=init_ts_ns,
        open_ts=utc_datetime_from_unix_ns(open_ts_ns),
        close_ts=utc_datetime_from_unix_ns(close_ts_ns),
        open=bar.open.as_decimal(),
        high=bar.high.as_decimal(),
        low=bar.low.as_decimal(),
        close=bar.close.as_decimal(),
        volume=volume,
        buy_volume=0,
        sell_volume=0,
        unknown_volume=volume,
        source=source,
        is_revision=bool(getattr(bar, "is_revision", False)),
    )
