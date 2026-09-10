from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from markeitech.dashboard.config import DashboardConfig


@dataclass(slots=True)
class _Instrument:
    instrument_id: str
    capabilities: tuple[str, ...]
    bid: str | None = None
    ask: str | None = None
    last: str | None = None
    quote_ts_event_ns: int | None = None
    bar_ts_event_ns: int | None = None
    quote_ts_init_ns: int | None = None
    bar_ts_init_ns: int | None = None
    candles: deque = field(default_factory=deque)
    feed_states: dict[str, str] = field(default_factory=dict)
    rejected_bars: int = 0


class DashboardState:
    """Actor-thread display state, retaining native identities and decimal strings.

    Completed bars are immutable within this runtime. Duplicate or late bars do
    not overwrite a candle. No aggregation, gap filling, or durable storage occurs.
    """

    def __init__(self, config: DashboardConfig, market_data_type: str = "unknown") -> None:
        self.config = config
        self.market_data_type = market_data_type
        self.instruments: dict[str, _Instrument] = {}
        self.sequence = 0
        self.status = "WAITING_FOR_MEMBERSHIP"

    def set_members(self, members: list[dict]) -> None:
        if len(members) > self.config.maximum_instruments:
            raise ValueError("dashboard instrument limit exceeded")
        if len({m["instrument_id"] for m in members}) != len(members):
            raise ValueError("duplicate dashboard membership")
        self.instruments = {
            m["instrument_id"]: self.instruments.get(m["instrument_id"])
            or _Instrument(
                m["instrument_id"],
                tuple(m["capabilities"]),
                candles=deque(maxlen=self.config.candles_per_instrument),
            )
            for m in members
        }
        self.status = "RUNNING"
        self.sequence += 1

    def observe_quote(self, quote) -> None:  # noqa: ANN001
        item = self.instruments.get(str(quote.instrument_id))
        if item is None or "top_of_book" not in item.capabilities:
            return
        if item.quote_ts_event_ns is not None and quote.ts_event < item.quote_ts_event_ns:
            return
        item.bid, item.ask = str(quote.bid_price), str(quote.ask_price)
        item.quote_ts_event_ns, item.quote_ts_init_ns = quote.ts_event, quote.ts_init
        item.feed_states["quotes"] = "OBSERVED"
        self.sequence += 1

    def observe_bar(self, bar) -> None:  # noqa: ANN001
        instrument_id = str(bar.bar_type.instrument_id)
        item = self.instruments.get(instrument_id)
        if item is None or "watchlist_last" not in item.capabilities:
            return
        if str(bar.bar_type) != f"{instrument_id}-5-SECOND-LAST-EXTERNAL":
            return
        values = {key: str(getattr(bar, key)) for key in ("open", "high", "low", "close", "volume")}
        try:
            prices = {key: Decimal(value) for key, value in values.items()}
            valid = all(value.is_finite() for value in prices.values())
            valid = valid and prices["low"] <= min(prices["open"], prices["close"])
            valid = valid and prices["high"] >= max(prices["open"], prices["close"])
            valid = valid and prices["volume"] >= 0
        except InvalidOperation:
            valid = False
        if not valid or (item.bar_ts_event_ns is not None and bar.ts_event <= item.bar_ts_event_ns):
            item.rejected_bars += 1
            self.sequence += 1
            return
        item.candles.append(
            {
                **values,
                "ts_event_ns": str(bar.ts_event),
                "ts_init_ns": str(bar.ts_init),
                "time": bar.ts_event // 1_000_000_000,
            }
        )
        item.last = values["close"]
        item.bar_ts_event_ns, item.bar_ts_init_ns = bar.ts_event, bar.ts_init
        item.feed_states["bars"] = "OBSERVED"
        self.sequence += 1

    def feed_state(self, instrument_id: str, feed_kind: str, state: str) -> None:
        if instrument_id in self.instruments:
            self.instruments[instrument_id].feed_states[feed_kind] = state
            self.sequence += 1

    def snapshot(self) -> dict:
        """Return a detached JSON-ready projection; nanoseconds remain exact strings."""
        rows = []
        candles = {}
        for item in self.instruments.values():
            rows.append(
                {
                    "instrument_id": item.instrument_id,
                    "capabilities": item.capabilities,
                    "bid": item.bid,
                    "ask": item.ask,
                    "last": item.last,
                    "quote_ts_event_ns": _ns(item.quote_ts_event_ns),
                    "bar_ts_event_ns": _ns(item.bar_ts_event_ns),
                    "quote_ts_init_ns": _ns(item.quote_ts_init_ns),
                    "bar_ts_init_ns": _ns(item.bar_ts_init_ns),
                    "feed_states": dict(item.feed_states),
                    "rejected_bars": item.rejected_bars,
                }
            )
            candles[item.instrument_id] = list(item.candles)
        return deepcopy(
            {
                "schema_version": 1,
                "sequence": self.sequence,
                "status": self.status,
                "provider": "IB",
                "requested_market_data_type": self.market_data_type,
                "received_market_data_type": "unknown",
                "bar_selector": "5-SECOND-LAST-EXTERNAL",
                "last_source": "5s_bar_close",
                "timestamp_basis": "provider_bar_event_time",
                "maximum_candles": self.config.candles_per_instrument,
                "instruments": rows,
                "candles": candles,
            }
        )


def _ns(value: int | None) -> str | None:
    return None if value is None else str(value)
