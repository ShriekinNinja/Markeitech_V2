from __future__ import annotations

from dataclasses import dataclass

from nautilus_trader.common import DataActor, DataActorConfig
from nautilus_trader.model import ActorId, BarType, ClientId, InstrumentId

_IB_CLIENT_ID = ClientId.from_str("IB")


@dataclass(slots=True)
class WatchlistInstrumentState:
    best_bid: str | None = None
    best_ask: str | None = None
    last: str | None = None
    quotes: int = 0
    bars: int = 0

    @property
    def ready(self) -> bool:
        return self.best_bid is not None and self.best_ask is not None and self.last is not None


class WatchlistState:
    def __init__(self, instrument_ids: tuple[str, ...]) -> None:
        if len(instrument_ids) < 8:
            raise ValueError("watchlist proof requires at least eight instruments")
        if len(set(instrument_ids)) != len(instrument_ids):
            raise ValueError("watchlist instruments must be unique")
        self._instruments = {
            instrument_id: WatchlistInstrumentState() for instrument_id in instrument_ids
        }

    @property
    def instrument_ids(self) -> tuple[str, ...]:
        return tuple(self._instruments)

    @property
    def ready_count(self) -> int:
        return sum(state.ready for state in self._instruments.values())

    @property
    def is_ready(self) -> bool:
        return self.ready_count == len(self._instruments)

    def observe_quote(self, instrument_id: str, best_bid: str, best_ask: str) -> bool:
        state = self._state(instrument_id)
        was_ready = state.ready
        state.best_bid = best_bid
        state.best_ask = best_ask
        state.quotes += 1
        return not was_ready and state.ready

    def observe_bar(self, instrument_id: str, last: str) -> bool:
        state = self._state(instrument_id)
        was_ready = state.ready
        state.last = last
        state.bars += 1
        return not was_ready and state.ready

    def snapshot(self) -> tuple[tuple[str, WatchlistInstrumentState], ...]:
        return tuple(sorted(self._instruments.items()))

    def _state(self, instrument_id: str) -> WatchlistInstrumentState:
        try:
            return self._instruments[instrument_id]
        except KeyError as exc:
            raise ValueError(f"unexpected watchlist instrument: {instrument_id}") from exc


class WatchlistActorConfig(DataActorConfig):
    def __new__(
        cls,
        instrument_ids: list[str],
        actor_id: str | ActorId = "WATCHLIST",
    ) -> WatchlistActorConfig:
        resolved_actor_id = (
            actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        )
        obj = super().__new__(cls, actor_id=resolved_actor_id)
        obj.instrument_ids = tuple(instrument_ids)
        return obj


class WatchlistActor(DataActor):
    """Bounded proof consumer for native quotes and five-second bar closes."""

    def __init__(self, config: WatchlistActorConfig) -> None:
        super().__init__(config)
        self._state = WatchlistState(config.instrument_ids)
        self._watchlist_ready_logged = False

    def on_start(self) -> None:
        for value in self._state.instrument_ids:
            instrument_id = InstrumentId.from_str(value)
            self.subscribe_quotes(instrument_id, client_id=_IB_CLIENT_ID)
            self.subscribe_bars(_watchlist_bar_type(instrument_id), client_id=_IB_CLIENT_ID)
        self.log.info(f"WATCHLIST_STARTED | instruments={len(self._state.instrument_ids)}")

    def on_quote(self, quote) -> None:  # noqa: ANN001
        instrument_id = str(quote.instrument_id)
        became_ready = self._state.observe_quote(
            instrument_id,
            str(quote.bid_price),
            str(quote.ask_price),
        )
        self._log_readiness(instrument_id, became_ready)

    def on_bar(self, bar) -> None:  # noqa: ANN001
        instrument_id = str(bar.bar_type.instrument_id)
        became_ready = self._state.observe_bar(instrument_id, str(bar.close))
        self._log_readiness(instrument_id, became_ready)

    def on_stop(self) -> None:
        for value in self._state.instrument_ids:
            instrument_id = InstrumentId.from_str(value)
            self.unsubscribe_quotes(instrument_id, client_id=_IB_CLIENT_ID)
            self.unsubscribe_bars(_watchlist_bar_type(instrument_id), client_id=_IB_CLIENT_ID)
        for instrument_id, state in self._state.snapshot():
            self.log.info(
                "WATCHLIST_SUMMARY"
                f" | instrument_id={instrument_id}"
                f" | best_bid={state.best_bid}"
                f" | best_ask={state.best_ask}"
                f" | last={state.last}"
                f" | quotes={state.quotes}"
                f" | bars={state.bars}"
                " | last_source=5s_bar_close"
                f" | ready={str(state.ready).lower()}",
            )
        self.log.info(
            "WATCHLIST_STOPPED"
            f" | ready={self._state.ready_count}/{len(self._state.instrument_ids)}",
        )

    def _log_readiness(self, instrument_id: str, became_ready: bool) -> None:
        if became_ready:
            state = dict(self._state.snapshot())[instrument_id]
            self.log.info(
                "WATCHLIST_INSTRUMENT_READY"
                f" | instrument_id={instrument_id}"
                f" | best_bid={state.best_bid}"
                f" | best_ask={state.best_ask}"
                f" | last={state.last}"
                " | last_source=5s_bar_close"
                f" | ready={self._state.ready_count}/{len(self._state.instrument_ids)}",
            )
        if self._state.is_ready and not self._watchlist_ready_logged:
            self._watchlist_ready_logged = True
            self.log.info(
                f"WATCHLIST_READY | instruments={len(self._state.instrument_ids)}",
            )


def _watchlist_bar_type(instrument_id: InstrumentId) -> BarType:
    return BarType.from_str(f"{instrument_id}-5-SECOND-LAST-EXTERNAL")
