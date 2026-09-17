from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation

from markeitech.acquisition.minute_candles import INTRADAY_TIMEFRAMES, MinuteCandleUpdate
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
    live_bar_ts_event_ns: int | None = None
    candles: deque = field(default_factory=deque)
    timeframe_candles: dict[str, deque] = field(default_factory=dict)
    feed_states: dict[str, str] = field(default_factory=dict)
    rejected_bars: int = 0
    candle_conflicts: int = 0
    candle_rejected_inputs: int = 0


class DashboardState:
    """Actor-thread display state, retaining native identities and decimal strings.

    Source bars supply the latest price. Acquisition-owned intraday projections
    supply the chart. No aggregation, gap filling, or durable storage occurs here.
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
        if not valid or (
            item.live_bar_ts_event_ns is not None and bar.ts_event <= item.live_bar_ts_event_ns
        ):
            item.rejected_bars += 1
            self.sequence += 1
            return
        item.live_bar_ts_event_ns = bar.ts_event
        if item.bar_ts_event_ns is None or bar.ts_event >= item.bar_ts_event_ns:
            item.last = values["close"]
            item.bar_ts_event_ns, item.bar_ts_init_ns = bar.ts_event, bar.ts_init
        item.feed_states["bars"] = "OBSERVED"
        self.sequence += 1

    def observe_candles(self, update: MinuteCandleUpdate) -> None:
        """Replace a detached chart projection produced by acquisition, including repairs."""
        item = self.instruments.get(update.instrument_id)
        if (
            item is None
            or "watchlist_last" not in item.capabilities
            or update.source != "DATA-ACQUISITION"
            or update.schema_version != 1
            or update.provider != "IB"
            or update.selector != "5-SECOND-LAST-EXTERNAL"
            or update.timeframe not in INTRADAY_TIMEFRAMES
        ):
            return
        projection = deque(
            (asdict(candle) for candle in update.candles[-self.config.candles_per_instrument :]),
            maxlen=self.config.candles_per_instrument,
        )
        item.timeframe_candles[update.timeframe] = projection
        if update.timeframe == "1m":
            item.candles = projection
        item.candle_conflicts = update.conflicts
        item.candle_rejected_inputs = update.rejected_inputs
        if update.candles and (
            item.bar_ts_event_ns is None or update.ts_event > item.bar_ts_event_ns
        ):
            item.last = update.candles[-1].close
            item.bar_ts_event_ns = update.ts_event
            item.bar_ts_init_ns = int(update.candles[-1].ts_init_ns)
        self.sequence += 1

    def feed_state(self, instrument_id: str, feed_kind: str, state: str) -> None:
        if instrument_id in self.instruments:
            self.instruments[instrument_id].feed_states[feed_kind] = state
            self.sequence += 1

    def snapshot(self) -> dict:
        """Return a detached JSON-ready projection; nanoseconds remain exact strings."""
        rows = []
        candles = {}
        timeframes = {}
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
                    "candle_conflicts": item.candle_conflicts,
                    "candle_rejected_inputs": item.candle_rejected_inputs,
                }
            )
            candles[item.instrument_id] = list(item.candles)
            timeframes[item.instrument_id] = {
                frame: list(values) for frame, values in item.timeframe_candles.items()
            }
        return deepcopy(
            {
                "schema_version": 2,
                "sequence": self.sequence,
                "status": self.status,
                "provider": "IB",
                "requested_market_data_type": self.market_data_type,
                "received_market_data_type": "unknown",
                "bar_selector": "1-MINUTE-LAST-DERIVED",
                "source_bar_selector": "5-SECOND-LAST-EXTERNAL",
                "timeframe": "1m",
                "last_source": "5s_bar_close",
                "timestamp_basis": "UTC_minute_open_from_provider_5s_close",
                "maximum_candles": self.config.candles_per_instrument,
                "instruments": rows,
                "candles": candles,
                "candles_by_timeframe": timeframes,
                "available_timeframes": list(INTRADAY_TIMEFRAMES),
            }
        )


def _ns(value: int | None) -> str | None:
    return None if value is None else str(value)
