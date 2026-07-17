from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from markeitech.auction_pressure.contracts import (
    AuctionPressureFidelity,
    SessionAuctionPressureSnapshot,
)
from markeitech.domain.market_data import ClassifiedTrade


class ProductSessionResolver(Protocol):
    def session_window(
        self,
        instrument_id: str,
        timestamp: datetime,
    ) -> tuple[datetime, datetime]: ...


class SessionAuctionPressureAccumulator:
    def __init__(
        self,
        instrument_id: str,
        session_resolver: ProductSessionResolver,
        *,
        source: str = "ib",
        identity: Callable[[ClassifiedTrade], str] = lambda item: item.trade.dedupe_key,
    ) -> None:
        if not instrument_id:
            raise ValueError("auction-pressure accumulator requires an instrument")
        self._instrument_id = instrument_id
        self._session_resolver = session_resolver
        self._source = source
        self._identity = identity
        self._session_start: datetime | None = None
        self._session_end: datetime | None = None
        self._as_of: datetime | None = None
        self._trade_count = 0
        self._classified_trade_count = 0
        self._unknown_trade_count = 0
        self._buy_volume = Decimal("0")
        self._sell_volume = Decimal("0")
        self._unknown_volume = Decimal("0")
        self._sequence_gap_count = 0
        self._duplicate_count = 0
        self._stale_count = 0
        self._reason_counts: dict[str, int] = {}
        self._seen: set[str] = set()
        self._last_sequence: int | None = None

    def observe(self, trade: ClassifiedTrade) -> SessionAuctionPressureSnapshot:
        if trade.instrument_id != self._instrument_id:
            raise ValueError("classified trade does not match auction-pressure instrument")
        if trade.trade.source != self._source:
            raise ValueError("classified trade does not match auction-pressure source")
        session_start, session_end = self._session_resolver.session_window(
            trade.instrument_id,
            trade.event_ts,
        )
        if not session_start <= trade.event_ts < session_end:
            raise ValueError("session resolver returned a window that excludes the trade")

        if self._session_start is None or session_start > self._session_start:
            self._reset(session_start, session_end)
        elif session_start < self._session_start:
            self._stale_count += 1
            return self.snapshot()
        elif session_end != self._session_end:
            raise ValueError("session resolver changed the current session boundary")

        identity = self._identity(trade)
        if identity in self._seen:
            self._duplicate_count += 1
            return self.snapshot()
        if self._as_of is not None and trade.event_ts < self._as_of:
            self._stale_count += 1
            return self.snapshot()

        self._seen.add(identity)
        self._record_sequence(trade.trade.sequence)
        self._as_of = trade.event_ts
        self._trade_count += 1
        self._buy_volume += trade.buy_volume
        self._sell_volume += trade.sell_volume
        self._unknown_volume += trade.unknown_volume
        if trade.side.value == "unknown":
            self._unknown_trade_count += 1
        else:
            self._classified_trade_count += 1
        self._reason_counts[trade.classification_reason] = (
            self._reason_counts.get(trade.classification_reason, 0) + 1
        )
        return self.snapshot()

    def snapshot(self) -> SessionAuctionPressureSnapshot:
        if self._session_start is None or self._session_end is None or self._as_of is None:
            raise RuntimeError("auction-pressure accumulator has not observed a trade")
        classified_volume = self._buy_volume + self._sell_volume
        fidelity = AuctionPressureFidelity.INFERRED
        if classified_volume == 0:
            fidelity = AuctionPressureFidelity.UNAVAILABLE
        elif self._unknown_volume > 0 or self._sequence_gap_count > 0:
            fidelity = AuctionPressureFidelity.PARTIAL
        return SessionAuctionPressureSnapshot(
            instrument_id=self._instrument_id,
            session_start=self._session_start,
            session_end=self._session_end,
            as_of=self._as_of,
            source=self._source,
            fidelity=fidelity,
            trade_count=self._trade_count,
            classified_trade_count=self._classified_trade_count,
            unknown_trade_count=self._unknown_trade_count,
            buy_volume=self._buy_volume,
            sell_volume=self._sell_volume,
            unknown_volume=self._unknown_volume,
            sequence_gap_count=self._sequence_gap_count,
            duplicate_count=self._duplicate_count,
            stale_count=self._stale_count,
            classification_reason_counts=dict(self._reason_counts),
        )

    def _reset(self, session_start: datetime, session_end: datetime) -> None:
        self._session_start = session_start
        self._session_end = session_end
        self._as_of = None
        self._trade_count = 0
        self._classified_trade_count = 0
        self._unknown_trade_count = 0
        self._buy_volume = Decimal("0")
        self._sell_volume = Decimal("0")
        self._unknown_volume = Decimal("0")
        self._sequence_gap_count = 0
        self._duplicate_count = 0
        self._stale_count = 0
        self._reason_counts = {}
        self._seen = set()
        self._last_sequence = None

    def _record_sequence(self, sequence: int | None) -> None:
        if sequence is None:
            return
        if self._last_sequence is not None and sequence > self._last_sequence + 1:
            self._sequence_gap_count += sequence - self._last_sequence - 1
        if self._last_sequence is None or sequence > self._last_sequence:
            self._last_sequence = sequence
