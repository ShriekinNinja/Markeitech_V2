from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from markeitech.domain.base import unix_ns_from_utc_datetime, utc_datetime_from_unix_ns
from markeitech.domain.market_data import ClassifiedTrade, OneMinuteBar, TradeSide
from markeitech.market_data.normalization import ONE_MINUTE_NS


@dataclass(frozen=True)
class TickBarUpdate:
    active: OneMinuteBar
    completed: OneMinuteBar | None = None


class ActiveOneMinuteBarBuilder:
    def __init__(self, instrument_id: str) -> None:
        self._instrument_id = instrument_id
        self._open_ns: int | None = None
        self._open = Decimal(0)
        self._high = Decimal(0)
        self._low = Decimal(0)
        self._close = Decimal(0)
        self._volume = Decimal(0)
        self._buy_volume = Decimal(0)
        self._sell_volume = Decimal(0)
        self._unknown_volume = Decimal(0)
        self._last_event_ns = 0
        self._last_init_ns = 0

    def update(self, trade: ClassifiedTrade) -> TickBarUpdate:
        if trade.instrument_id != self._instrument_id:
            raise ValueError("classified trade does not match tick bar instrument")
        event_ns = _event_ns(trade)
        bucket_open_ns = event_ns - (event_ns % ONE_MINUTE_NS)

        completed = None
        if self._open_ns is None:
            self._start(bucket_open_ns, trade)
        elif bucket_open_ns > self._open_ns:
            completed = self._bar(is_complete=True, ts_init_ns=_init_ns(trade))
            self._start(bucket_open_ns, trade)
        elif bucket_open_ns < self._open_ns:
            return TickBarUpdate(active=self._bar(is_complete=False))
        else:
            self._apply(trade)

        return TickBarUpdate(active=self._bar(is_complete=False), completed=completed)

    def _start(self, bucket_open_ns: int, trade: ClassifiedTrade) -> None:
        price = trade.trade.price
        self._open_ns = bucket_open_ns
        self._open = price
        self._high = price
        self._low = price
        self._close = price
        self._volume = Decimal(0)
        self._buy_volume = Decimal(0)
        self._sell_volume = Decimal(0)
        self._unknown_volume = Decimal(0)
        self._last_event_ns = _event_ns(trade)
        self._last_init_ns = _init_ns(trade)
        self._add_volume(trade)

    def _apply(self, trade: ClassifiedTrade) -> None:
        price = trade.trade.price
        self._high = max(self._high, price)
        self._low = min(self._low, price)
        self._close = price
        self._last_event_ns = max(self._last_event_ns, _event_ns(trade))
        self._last_init_ns = max(self._last_init_ns, _init_ns(trade))
        self._add_volume(trade)

    def _add_volume(self, trade: ClassifiedTrade) -> None:
        size = trade.trade.size
        self._volume += size
        if trade.side == TradeSide.BUY:
            self._buy_volume += size
        elif trade.side == TradeSide.SELL:
            self._sell_volume += size
        else:
            self._unknown_volume += size

    def _bar(self, *, is_complete: bool, ts_init_ns: int | None = None) -> OneMinuteBar:
        if self._open_ns is None:
            raise RuntimeError("tick bar has not started")
        close_ns = self._open_ns + ONE_MINUTE_NS
        event_ns = close_ns if is_complete else self._last_event_ns
        initialized_ns = ts_init_ns or self._last_init_ns
        return OneMinuteBar(
            instrument_id=self._instrument_id,
            event_ts=utc_datetime_from_unix_ns(event_ns),
            ts_init=utc_datetime_from_unix_ns(initialized_ns),
            event_ts_ns=event_ns,
            ts_init_ns=initialized_ns,
            open_ts=utc_datetime_from_unix_ns(self._open_ns),
            close_ts=utc_datetime_from_unix_ns(close_ns),
            open=self._open,
            high=self._high,
            low=self._low,
            close=self._close,
            volume=self._volume,
            buy_volume=self._buy_volume,
            sell_volume=self._sell_volume,
            unknown_volume=self._unknown_volume,
            source="classified_ticks",
            is_complete=is_complete,
        )


def _event_ns(trade: ClassifiedTrade) -> int:
    if trade.event_ts_ns is not None:
        return trade.event_ts_ns
    return unix_ns_from_utc_datetime(trade.event_ts)


def _init_ns(trade: ClassifiedTrade) -> int:
    if trade.ts_init_ns is not None:
        return trade.ts_init_ns
    return unix_ns_from_utc_datetime(trade.ts_init)
