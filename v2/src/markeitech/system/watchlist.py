from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from nautilus_trader.common import DataActor, DataActorConfig
from nautilus_trader.model import ActorId, BarType, ClientId, InstrumentId

_IB_CLIENT_ID = ClientId.from_str("IB")
_MAX_COUNTER = 2**63 - 1


class ConsumerState(StrEnum):
    DETACHED = "DETACHED"
    REGISTERED = "REGISTERED"


class ObservationState(StrEnum):
    UNOBSERVED = "UNOBSERVED"
    PARTIAL = "PARTIAL"
    OBSERVED = "OBSERVED"


@dataclass(frozen=True, slots=True)
class WatchlistInstrumentSnapshot:
    instrument_id: str
    best_bid: str | None
    best_ask: str | None
    last: str | None
    quote_ts_event_ns: int | None
    bar_ts_event_ns: int | None
    quote_observations: int
    bar_observations: int
    out_of_order_observations: int
    observation_state: ObservationState


@dataclass(frozen=True, slots=True)
class WatchlistSnapshot:
    schema_version: int
    sequence: int
    consumer_state: ConsumerState
    observation_state: ObservationState
    instruments: tuple[WatchlistInstrumentSnapshot, ...]

    @property
    def operational(self) -> bool:
        return self.consumer_state == ConsumerState.REGISTERED


@dataclass(slots=True)
class WatchlistInstrumentState:
    best_bid: str | None = None
    best_ask: str | None = None
    last: str | None = None
    quote_ts_event_ns: int | None = None
    bar_ts_event_ns: int | None = None
    quote_observations: int = 0
    bar_observations: int = 0
    out_of_order_observations: int = 0

    @property
    def observation_state(self) -> ObservationState:
        has_quote = self.best_bid is not None and self.best_ask is not None
        has_last = self.last is not None
        if has_quote and has_last:
            return ObservationState.OBSERVED
        if has_quote or has_last:
            return ObservationState.PARTIAL
        return ObservationState.UNOBSERVED

    def snapshot(self, instrument_id: str) -> WatchlistInstrumentSnapshot:
        return WatchlistInstrumentSnapshot(
            instrument_id=instrument_id,
            best_bid=self.best_bid,
            best_ask=self.best_ask,
            last=self.last,
            quote_ts_event_ns=self.quote_ts_event_ns,
            bar_ts_event_ns=self.bar_ts_event_ns,
            quote_observations=self.quote_observations,
            bar_observations=self.bar_observations,
            out_of_order_observations=self.out_of_order_observations,
            observation_state=self.observation_state,
        )


class WatchlistState:
    SCHEMA_VERSION = 1

    def __init__(self, instrument_ids: tuple[str, ...]) -> None:
        if not instrument_ids:
            raise ValueError("watchlist requires at least one instrument")
        if len(set(instrument_ids)) != len(instrument_ids):
            raise ValueError("watchlist instruments must be unique")
        self._instruments = {
            instrument_id: WatchlistInstrumentState() for instrument_id in instrument_ids
        }
        self._consumer_state = ConsumerState.DETACHED
        self._sequence = 0

    @property
    def instrument_ids(self) -> tuple[str, ...]:
        return tuple(self._instruments)

    @property
    def observed_count(self) -> int:
        return sum(
            state.observation_state == ObservationState.OBSERVED
            for state in self._instruments.values()
        )

    @property
    def is_observed(self) -> bool:
        return self.observed_count == len(self._instruments)

    def register_consumers(self) -> bool:
        if self._consumer_state == ConsumerState.REGISTERED:
            return False
        self._consumer_state = ConsumerState.REGISTERED
        self._advance_sequence()
        return True

    def detach_consumers(self) -> bool:
        if self._consumer_state == ConsumerState.DETACHED:
            return False
        self._consumer_state = ConsumerState.DETACHED
        self._advance_sequence()
        return True

    def observe_quote(
        self,
        instrument_id: str,
        best_bid: str,
        best_ask: str,
        ts_event_ns: int,
    ) -> bool:
        state = self._state(instrument_id)
        timestamp = _timestamp_ns(ts_event_ns)
        was_observed = state.observation_state == ObservationState.OBSERVED
        state.quote_observations = _bounded_increment(state.quote_observations)
        if _is_out_of_order(timestamp, state.quote_ts_event_ns):
            state.out_of_order_observations = _bounded_increment(
                state.out_of_order_observations,
            )
        else:
            state.best_bid = best_bid
            state.best_ask = best_ask
            state.quote_ts_event_ns = timestamp
        self._advance_sequence()
        return not was_observed and state.observation_state == ObservationState.OBSERVED

    def observe_bar(self, instrument_id: str, last: str, ts_event_ns: int) -> bool:
        state = self._state(instrument_id)
        timestamp = _timestamp_ns(ts_event_ns)
        was_observed = state.observation_state == ObservationState.OBSERVED
        state.bar_observations = _bounded_increment(state.bar_observations)
        if _is_out_of_order(timestamp, state.bar_ts_event_ns):
            state.out_of_order_observations = _bounded_increment(
                state.out_of_order_observations,
            )
        else:
            state.last = last
            state.bar_ts_event_ns = timestamp
        self._advance_sequence()
        return not was_observed and state.observation_state == ObservationState.OBSERVED

    def snapshot(self) -> WatchlistSnapshot:
        instruments = tuple(
            self._instruments[instrument_id].snapshot(instrument_id)
            for instrument_id in sorted(self._instruments)
        )
        states = {instrument.observation_state for instrument in instruments}
        if states == {ObservationState.OBSERVED}:
            observation_state = ObservationState.OBSERVED
        elif states == {ObservationState.UNOBSERVED}:
            observation_state = ObservationState.UNOBSERVED
        else:
            observation_state = ObservationState.PARTIAL
        return WatchlistSnapshot(
            schema_version=self.SCHEMA_VERSION,
            sequence=self._sequence,
            consumer_state=self._consumer_state,
            observation_state=observation_state,
            instruments=instruments,
        )

    def _state(self, instrument_id: str) -> WatchlistInstrumentState:
        try:
            return self._instruments[instrument_id]
        except KeyError as exc:
            raise ValueError(f"unexpected watchlist instrument: {instrument_id}") from exc

    def _advance_sequence(self) -> None:
        self._sequence = _bounded_increment(self._sequence)


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
    """Bounded owner of latest watchlist observation state."""

    def __init__(self, config: WatchlistActorConfig) -> None:
        super().__init__(config)
        self._state = WatchlistState(config.instrument_ids)
        self._watchlist_observed_logged = False

    def on_start(self) -> None:
        for value in self._state.instrument_ids:
            instrument_id = InstrumentId.from_str(value)
            self.subscribe_quotes(instrument_id, client_id=_IB_CLIENT_ID)
            self.subscribe_bars(_watchlist_bar_type(instrument_id), client_id=_IB_CLIENT_ID)
        self._state.register_consumers()
        self.log.info(f"WATCHLIST_OPERATIONAL | instruments={len(self._state.instrument_ids)}")

    def on_quote(self, quote) -> None:  # noqa: ANN001
        instrument_id = str(quote.instrument_id)
        became_observed = self._state.observe_quote(
            instrument_id,
            str(quote.bid_price),
            str(quote.ask_price),
            quote.ts_event,
        )
        self._log_observation(instrument_id, became_observed)

    def on_bar(self, bar) -> None:  # noqa: ANN001
        instrument_id = str(bar.bar_type.instrument_id)
        became_observed = self._state.observe_bar(
            instrument_id,
            str(bar.close),
            bar.ts_event,
        )
        self._log_observation(instrument_id, became_observed)

    def on_stop(self) -> None:
        for value in self._state.instrument_ids:
            instrument_id = InstrumentId.from_str(value)
            self.unsubscribe_quotes(instrument_id, client_id=_IB_CLIENT_ID)
            self.unsubscribe_bars(_watchlist_bar_type(instrument_id), client_id=_IB_CLIENT_ID)
        self._state.detach_consumers()
        snapshot = self._state.snapshot()
        for state in snapshot.instruments:
            self.log.info(
                "WATCHLIST_SUMMARY"
                f" | instrument_id={state.instrument_id}"
                f" | best_bid={state.best_bid}"
                f" | best_ask={state.best_ask}"
                f" | last={state.last}"
                f" | quote_ts_event_ns={state.quote_ts_event_ns}"
                f" | bar_ts_event_ns={state.bar_ts_event_ns}"
                f" | quotes={state.quote_observations}"
                f" | bars={state.bar_observations}"
                f" | out_of_order={state.out_of_order_observations}"
                " | last_source=5s_bar_close"
                f" | observation_state={state.observation_state}",
            )
        self.log.info(
            "WATCHLIST_STOPPED"
            f" | observed={self._state.observed_count}/{len(self._state.instrument_ids)}",
        )

    def _log_observation(self, instrument_id: str, became_observed: bool) -> None:
        if became_observed:
            snapshot = self._state.snapshot()
            state = next(
                item for item in snapshot.instruments if item.instrument_id == instrument_id
            )
            self.log.info(
                "WATCHLIST_INSTRUMENT_OBSERVED"
                f" | instrument_id={instrument_id}"
                f" | best_bid={state.best_bid}"
                f" | best_ask={state.best_ask}"
                f" | last={state.last}"
                " | last_source=5s_bar_close"
                f" | observed={self._state.observed_count}/{len(self._state.instrument_ids)}",
            )
        if self._state.is_observed and not self._watchlist_observed_logged:
            self._watchlist_observed_logged = True
            self.log.info(
                f"WATCHLIST_OBSERVED | instruments={len(self._state.instrument_ids)}",
            )


def _watchlist_bar_type(instrument_id: InstrumentId) -> BarType:
    return BarType.from_str(f"{instrument_id}-5-SECOND-LAST-EXTERNAL")


def _timestamp_ns(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("ts_event_ns must be a non-negative integer")
    return value


def _is_out_of_order(value: int, current: int | None) -> bool:
    return current is not None and value < current


def _bounded_increment(value: int) -> int:
    return min(value + 1, _MAX_COUNTER)
