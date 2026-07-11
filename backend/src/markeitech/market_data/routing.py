from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import Field

from markeitech.domain.base import VersionedDomainModel
from markeitech.domain.classification import classify_trade
from markeitech.domain.market_data import (
    CanonicalQuoteTick,
    CanonicalTradeTick,
    ClassifiedTrade,
    OneMinuteBar,
)
from markeitech.market_data.bars import ActiveOneMinuteBarBuilder
from markeitech.market_data.normalization import (
    MarketDataNormalizationError,
    normalize_one_minute_bar,
    normalize_quote_tick,
    normalize_trade_tick,
)

type RoutedMarketDataEvent = (
    CanonicalTradeTick | CanonicalQuoteTick | ClassifiedTrade | OneMinuteBar
)
type MarketDataEventSink = Callable[[RoutedMarketDataEvent], None]


class InstrumentMarketDataSnapshot(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    is_active: bool
    trade_tick_count: int = Field(default=0, ge=0)
    quote_tick_count: int = Field(default=0, ge=0)
    bar_count: int = Field(default=0, ge=0)
    latest_trade: CanonicalTradeTick | None = None
    latest_quote: CanonicalQuoteTick | None = None
    latest_classified_trade: ClassifiedTrade | None = None
    latest_bar: OneMinuteBar | None = None
    active_bar: OneMinuteBar | None = None
    tick_bar_update_count: int = Field(default=0, ge=0)
    dropped_event_count: int = Field(default=0, ge=0)
    last_drop_reason: str | None = None


class LiveMarketDataRouter:
    def __init__(
        self,
        *,
        instrument_ids: set[str],
        active_instrument_id: Callable[[], str],
        on_event: MarketDataEventSink | None = None,
        source: str = "ib",
    ) -> None:
        if not instrument_ids:
            raise ValueError("live market-data router requires configured instruments")
        self._instrument_ids = frozenset(instrument_ids)
        self._active_instrument_id = active_instrument_id
        self._on_event = on_event
        self._source = source
        self._snapshots = {
            instrument_id: InstrumentMarketDataSnapshot(
                instrument_id=instrument_id,
                is_active=instrument_id == active_instrument_id(),
            )
            for instrument_id in instrument_ids
        }
        self._active_bar_builders = {
            instrument_id: ActiveOneMinuteBarBuilder(instrument_id)
            for instrument_id in instrument_ids
        }

    def snapshot(self, instrument_id: str) -> InstrumentMarketDataSnapshot:
        self._require_instrument(instrument_id)
        snapshot = self._snapshots[instrument_id]
        is_active = instrument_id == self._active_instrument_id()
        if snapshot.is_active != is_active:
            snapshot = snapshot.model_copy(update={"is_active": is_active})
            self._snapshots[instrument_id] = snapshot
        return snapshot

    def snapshots(self) -> tuple[InstrumentMarketDataSnapshot, ...]:
        return tuple(self.snapshot(instrument_id) for instrument_id in sorted(self._instrument_ids))

    def activate_instrument(self, instrument_id: str) -> None:
        self._require_instrument(instrument_id)
        self._active_bar_builders[instrument_id] = ActiveOneMinuteBarBuilder(instrument_id)
        snapshot = self.snapshot(instrument_id)
        self._snapshots[instrument_id] = snapshot.model_copy(
            update={"is_active": True, "active_bar": None}
        )

    def handle_trade_tick(self, tick: Any) -> ClassifiedTrade | None:
        try:
            trade = normalize_trade_tick(tick, source=self._source)
        except MarketDataNormalizationError as exc:
            self._record_drop(str(tick.instrument_id), str(exc))
            return None
        snapshot = self.snapshot(trade.instrument_id)
        classified = classify_trade(
            trade,
            snapshot.latest_quote,
            previous_trade=snapshot.latest_trade,
        )
        self._snapshots[trade.instrument_id] = snapshot.model_copy(
            update={
                "trade_tick_count": snapshot.trade_tick_count + 1,
                "latest_trade": trade,
                "latest_classified_trade": classified,
            }
        )
        self._emit(trade)
        self._emit(classified)
        if trade.instrument_id == self._active_instrument_id():
            self._update_active_bar(classified)
        return classified

    def handle_quote_tick(self, tick: Any) -> CanonicalQuoteTick | None:
        try:
            quote = normalize_quote_tick(tick, source=self._source)
        except MarketDataNormalizationError as exc:
            self._record_drop(str(tick.instrument_id), str(exc))
            return None
        snapshot = self.snapshot(quote.instrument_id)
        self._snapshots[quote.instrument_id] = snapshot.model_copy(
            update={
                "quote_tick_count": snapshot.quote_tick_count + 1,
                "latest_quote": quote,
            }
        )
        self._emit(quote)
        return quote

    def handle_bar(self, bar: Any) -> OneMinuteBar:
        normalized = normalize_one_minute_bar(bar, source=self._source)
        snapshot = self.snapshot(normalized.instrument_id)
        self._snapshots[normalized.instrument_id] = snapshot.model_copy(
            update={
                "bar_count": snapshot.bar_count + 1,
                "latest_bar": normalized,
            }
        )
        self._emit(normalized)
        return normalized

    def _emit(self, event: RoutedMarketDataEvent) -> None:
        if self._on_event is not None:
            self._on_event(event)

    def _update_active_bar(self, trade: ClassifiedTrade) -> None:
        update = self._active_bar_builders[trade.instrument_id].update(trade)
        snapshot = self.snapshot(trade.instrument_id)
        self._snapshots[trade.instrument_id] = snapshot.model_copy(
            update={
                "active_bar": update.active,
                "tick_bar_update_count": snapshot.tick_bar_update_count + 1,
            }
        )
        if update.completed is not None:
            self._emit(update.completed)
        self._emit(update.active)

    def _require_instrument(self, instrument_id: str) -> None:
        if instrument_id not in self._instrument_ids:
            raise ValueError(f"received market data for unconfigured instrument {instrument_id!r}")

    def _record_drop(self, instrument_id: str, reason: str) -> None:
        snapshot = self.snapshot(instrument_id)
        self._snapshots[instrument_id] = snapshot.model_copy(
            update={
                "dropped_event_count": snapshot.dropped_event_count + 1,
                "last_drop_reason": reason,
            }
        )
