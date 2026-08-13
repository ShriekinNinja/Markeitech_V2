from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId, BarType, ClientId, InstrumentId

from markeitech.system.messages import (
    ACQUISITION_STREAM_SIGNAL,
    PERSISTENCE_READY_REQUEST_SIGNAL,
    PERSISTENCE_READY_SIGNAL,
    WATCHLIST_DEMAND_SIGNAL,
    WATCHLIST_LIFECYCLE_SIGNAL,
    WATCHLIST_MEMBERSHIP_SIGNAL,
    AcquisitionStreamEvent,
    PersistenceReadyEvent,
    PersistenceReadyRequest,
    WatchlistDemandEvent,
    WatchlistLifecycleEvent,
    WatchlistMember,
    WatchlistMembershipEvent,
)

_IB_CLIENT_ID = ClientId.from_str("IB")
_MAX_COUNTER = 2**63 - 1
_STATIC_MEMBERSHIP_REVISION = 1
_STATIC_MEMBERSHIP_EVENT_ID = "watchlist-membership:1"
_STATIC_OWNER_ID = "config:system"


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
        members: list[dict[str, object]],
        actor_id: str | ActorId = "WATCHLIST",
    ) -> WatchlistActorConfig:
        resolved_actor_id = (
            actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        )
        obj = super().__new__(cls, actor_id=resolved_actor_id)
        obj.members = tuple(members)
        return obj


class WatchlistActor(DataActor):
    """Bounded owner of latest watchlist observation state."""

    def __init__(self, config: WatchlistActorConfig) -> None:
        super().__init__(config)
        self._members = tuple(
            WatchlistMember(
                instrument_id=str(member["instrument_id"]),
                owner_ids=tuple(str(value) for value in member["owner_ids"]),
                capabilities=tuple(str(value) for value in member["capabilities"]),
            )
            for member in config.members
        )
        self._state = WatchlistState(tuple(member.instrument_id for member in self._members))
        self._watchlist_observed_logged = False
        self._audit_started = False
        self._lifecycle_sequence = 0
        self._observed_before_audit: set[str] = set()
        self._startup_released = False
        self._demands = _watchlist_demands(self._members)
        self._subscribed_demand_ids: set[str] = set()
        self._attached_demand_ids: set[str] = set()
        self._degraded_demand_ids: set[str] = set()

    def on_start(self) -> None:
        self.subscribe_signal(PERSISTENCE_READY_SIGNAL)
        self.subscribe_signal(ACQUISITION_STREAM_SIGNAL)
        self.publish_signal(
            PERSISTENCE_READY_REQUEST_SIGNAL,
            PersistenceReadyRequest(requester=str(self.actor_id)).to_signal_value(),
        )

    def on_signal(self, signal: Signal) -> None:
        if signal.name == ACQUISITION_STREAM_SIGNAL:
            self._handle_acquisition_outcome(signal.value)
            return
        if signal.name != PERSISTENCE_READY_SIGNAL:
            return
        try:
            PersistenceReadyEvent.from_signal_value(signal.value)
        except ValueError as exc:
            self.log.error(
                f"PERSISTENCE_READY_REJECTED | reason=invalid_event | error={type(exc).__name__}",
            )
            return
        self._release_startup()

    def _release_startup(self) -> None:
        if self._startup_released:
            return
        self._startup_released = True
        self._publish_initial_audit(None)
        for demand in self._demands:
            self.publish_signal(WATCHLIST_DEMAND_SIGNAL, demand.to_signal_value())
        self.log.info(
            f"WATCHLIST_DEMANDS_PUBLISHED | instruments={len(self._state.instrument_ids)}"
            f" | demands={len(self._demands)}",
        )

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
        self.unsubscribe_signal(PERSISTENCE_READY_SIGNAL)
        self.unsubscribe_signal(ACQUISITION_STREAM_SIGNAL)
        if self._startup_released:
            for demand in reversed(self._demands):
                if demand.demand_id in self._attached_demand_ids:
                    self._detach_consumer(demand)
                self.publish_signal(
                    WATCHLIST_DEMAND_SIGNAL,
                    WatchlistDemandEvent(
                        demand_id=demand.demand_id,
                        action="RELEASE",
                        instrument_id=demand.instrument_id,
                        capability=demand.capability,
                        feed_kind=demand.feed_kind,
                        selector=demand.selector,
                        owner_id=demand.owner_id,
                        purpose="static watchlist shutdown",
                        priority=demand.priority,
                    ).to_signal_value(),
                )
            self._state.detach_consumers()
            self._publish_lifecycle(
                "CONSUMERS_DETACHED",
                reason="static watchlist native consumers detached",
            )
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
            if self._audit_started:
                self._publish_instrument_observed(instrument_id)
            else:
                self._observed_before_audit.add(instrument_id)
        if self._state.is_observed and not self._watchlist_observed_logged:
            self._watchlist_observed_logged = True
            self.log.info(
                f"WATCHLIST_OBSERVED | instruments={len(self._state.instrument_ids)}",
            )

    def _publish_initial_audit(self, _event) -> None:  # noqa: ANN001
        if self._audit_started:
            return
        self._audit_started = True
        membership = WatchlistMembershipEvent(
            event_id=_STATIC_MEMBERSHIP_EVENT_ID,
            membership_revision=_STATIC_MEMBERSHIP_REVISION,
            source=str(self.actor_id),
            reason="static configuration baseline established",
            members=self._members,
        )
        self.publish_signal(WATCHLIST_MEMBERSHIP_SIGNAL, membership.to_signal_value())
        self._publish_lifecycle(
            "CONFIGURED",
            reason="static configuration baseline established",
        )
        for instrument_id in sorted(self._observed_before_audit):
            self._publish_instrument_observed(instrument_id)
        self._observed_before_audit.clear()

    def _publish_instrument_observed(self, instrument_id: str) -> None:
        self._publish_lifecycle(
            "INSTRUMENT_OBSERVED",
            reason="required quote and bar-derived last observed",
            instrument_id=instrument_id,
        )

    def _publish_lifecycle(
        self,
        state: str,
        *,
        reason: str,
        instrument_id: str | None = None,
    ) -> None:
        self._lifecycle_sequence += 1
        event = WatchlistLifecycleEvent(
            event_id=f"watchlist-lifecycle:{self._lifecycle_sequence}",
            membership_revision=_STATIC_MEMBERSHIP_REVISION,
            state=state,
            source=str(self.actor_id),
            reason=reason,
            instrument_id=instrument_id,
            owner_id=_STATIC_OWNER_ID,
            correlation_id=_STATIC_MEMBERSHIP_EVENT_ID,
        )
        self.publish_signal(WATCHLIST_LIFECYCLE_SIGNAL, event.to_signal_value())

    def _handle_acquisition_outcome(self, value: str) -> None:
        try:
            event = AcquisitionStreamEvent.from_signal_value(value)
        except ValueError as exc:
            self.log.error(
                f"ACQUISITION_OUTCOME_REJECTED | reason=invalid_event | error={type(exc).__name__}",
            )
            return
        demand_ids = set(event.consumer_ids)
        if event.demand_id is not None:
            demand_ids.add(event.demand_id)
        relevant = [demand for demand in self._demands if demand.demand_id in demand_ids]
        if not relevant:
            return
        if event.state == "SUBSCRIBED":
            for demand in relevant:
                self._subscribed_demand_ids.add(demand.demand_id)
                if demand.demand_id not in self._attached_demand_ids:
                    self._attach_consumer(demand)
                    self._attached_demand_ids.add(demand.demand_id)
            if len(self._subscribed_demand_ids) == len(self._demands):
                if self._state.register_consumers():
                    self._publish_lifecycle(
                        "CONSUMERS_REGISTERED",
                        reason="all static watchlist acquisition demands subscribed",
                    )
                    self.log.info(
                        f"WATCHLIST_OPERATIONAL | instruments={len(self._state.instrument_ids)}",
                    )
            return
        if event.state in {"REJECTED", "FAILED", "EXPIRED"}:
            for demand in relevant:
                if demand.demand_id in self._degraded_demand_ids:
                    continue
                self._degraded_demand_ids.add(demand.demand_id)
                self._publish_lifecycle(
                    "OBSERVATION_DEGRADED",
                    reason=(
                        f"required {demand.capability} acquisition outcome was "
                        f"{event.state.lower()}"
                    ),
                    instrument_id=demand.instrument_id,
                )
            return
        if event.state == "ACTIVE":
            for demand in relevant:
                if demand.demand_id not in self._degraded_demand_ids:
                    continue
                self._degraded_demand_ids.remove(demand.demand_id)
                self._publish_lifecycle(
                    "OBSERVATION_RECOVERED",
                    reason=f"required {demand.capability} stream produced an observation",
                    instrument_id=demand.instrument_id,
                )

    def _attach_consumer(self, demand: WatchlistDemandEvent) -> None:
        instrument_id = InstrumentId.from_str(demand.instrument_id)
        if demand.feed_kind == "quotes":
            self.subscribe_quotes(instrument_id, client_id=_IB_CLIENT_ID)
            return
        if demand.feed_kind == "bars":
            self.subscribe_bars(_watchlist_bar_type(instrument_id), client_id=_IB_CLIENT_ID)
            return
        raise ValueError(f"unsupported watchlist feed: {demand.feed_kind}")

    def _detach_consumer(self, demand: WatchlistDemandEvent) -> None:
        instrument_id = InstrumentId.from_str(demand.instrument_id)
        if demand.feed_kind == "quotes":
            self.unsubscribe_quotes(instrument_id, client_id=_IB_CLIENT_ID)
            return
        if demand.feed_kind == "bars":
            self.unsubscribe_bars(_watchlist_bar_type(instrument_id), client_id=_IB_CLIENT_ID)
            return
        raise ValueError(f"unsupported watchlist feed: {demand.feed_kind}")


def _watchlist_bar_type(instrument_id: InstrumentId) -> BarType:
    return BarType.from_str(f"{instrument_id}-5-SECOND-LAST-EXTERNAL")


def _watchlist_demands(
    members: tuple[WatchlistMember, ...],
) -> tuple[WatchlistDemandEvent, ...]:
    demands: list[WatchlistDemandEvent] = []
    for member in members:
        for capability in member.capabilities:
            feed_kind, selector = {
                "top_of_book": ("quotes", "default"),
                "watchlist_last": ("bars", "5-SECOND-LAST-EXTERNAL"),
            }[capability]
            demands.append(
                WatchlistDemandEvent(
                    demand_id=(
                        f"watchlist:{_STATIC_MEMBERSHIP_REVISION}:"
                        f"{member.instrument_id}/{feed_kind}/{selector}"
                    ),
                    action="REQUEST",
                    instrument_id=member.instrument_id,
                    capability=capability,
                    feed_kind=feed_kind,
                    selector=selector,
                    owner_id=_STATIC_OWNER_ID,
                    purpose=f"static watchlist {capability}",
                ),
            )
    return tuple(sorted(demands, key=lambda item: item.demand_id))


def _timestamp_ns(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("ts_event_ns must be a non-negative integer")
    return value


def _is_out_of_order(value: int, current: int | None) -> bool:
    return current is not None and value < current


def _bounded_increment(value: int) -> int:
    return min(value + 1, _MAX_COUNTER)
