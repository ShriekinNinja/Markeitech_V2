from __future__ import annotations

from collections import Counter

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId, InstrumentId

from markeitech.acquisition import (
    AcquisitionCoordinator,
    AcquisitionLifecycleEvent,
    DemandOwner,
    DemandOwnerKind,
    FeedKind,
    FeedRequirement,
    NautilusSubscriptionPort,
    ObservationDemand,
)
from markeitech.system.messages import (
    ACQUISITION_STATUS_REQUEST_SIGNAL,
    ACQUISITION_STATUS_SIGNAL,
    ACQUISITION_STREAM_SIGNAL,
    COMPONENT_FAILURE_SIGNAL,
    INSTRUMENTS_READY,
    INSTRUMENTS_RESOLVING,
    AcquisitionStatusEvent,
    AcquisitionStatusRequest,
    AcquisitionStreamEvent,
    ComponentFailureEvent,
)


class InstrumentDefinitionTracker:
    def __init__(self, instrument_ids: list[str] | tuple[str, ...]) -> None:
        expected = {InstrumentId.from_str(value) for value in instrument_ids}
        if not expected:
            raise ValueError("instrument acquisition requires at least one instrument")
        if len(expected) != len(instrument_ids):
            raise ValueError("instrument acquisition does not allow duplicate instruments")
        self._expected = frozenset(expected)
        self._available: set[InstrumentId] = set()
        self._requested: set[InstrumentId] = set()

    @property
    def expected(self) -> frozenset[InstrumentId]:
        return self._expected

    @property
    def available(self) -> frozenset[InstrumentId]:
        return frozenset(self._available)

    @property
    def missing(self) -> frozenset[InstrumentId]:
        return self._expected - self._available

    def observe(self, instrument_id: InstrumentId) -> bool:
        if instrument_id not in self._expected or instrument_id in self._available:
            return False
        self._available.add(instrument_id)
        return True

    def take_unrequested(self) -> tuple[InstrumentId, ...]:
        pending = tuple(sorted(self.missing - self._requested, key=str))
        self._requested.update(pending)
        return pending

    def status(self, source: str) -> AcquisitionStatusEvent:
        complete = not self.missing
        return AcquisitionStatusEvent(
            state=INSTRUMENTS_READY if complete else INSTRUMENTS_RESOLVING,
            reason=(
                "configured instrument definitions are available"
                if complete
                else "resolving configured instrument definitions"
            ),
            source=source,
            expected_instrument_ids=tuple(sorted(str(value) for value in self._expected)),
            available_instrument_ids=tuple(sorted(str(value) for value in self._available)),
        )


class DataAcquisitionActorConfig(DataActorConfig):
    def __new__(
        cls,
        instrument_ids: list[str],
        bootstrap_feeds: list[dict[str, str]] | None = None,
        actor_id: str | ActorId = "DATA-ACQUISITION",
    ) -> DataAcquisitionActorConfig:
        resolved_actor_id = (
            actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        )
        obj = super().__new__(cls, actor_id=resolved_actor_id)
        obj.instrument_ids = tuple(instrument_ids)
        obj.bootstrap_feeds = tuple(bootstrap_feeds or ())
        return obj


class DataAcquisitionActor(DataActor):
    def __init__(self, config: DataAcquisitionActorConfig) -> None:
        super().__init__(config)
        self._tracker = InstrumentDefinitionTracker(config.instrument_ids)
        self._bootstrap_demands = _build_bootstrap_demands(config.bootstrap_feeds)
        self._bootstrap_stream_keys = frozenset(
            demand.requirement.stream_key for demand in self._bootstrap_demands
        )
        self._coordinator = AcquisitionCoordinator(NautilusSubscriptionPort(self))
        self._feeds_started = False
        self._observation_counts: Counter[tuple[str, str, str]] = Counter()
        self._lifecycle_counts: Counter[str] = Counter()
        self._instrument_requests = 0
        self._instruments_received = 0
        self._duplicate_instruments = 0
        self._status_requests = 0
        self._malformed_status_requests = 0
        self._statuses_published = 0
        self._failure_published = False

    def on_start(self) -> None:
        self.subscribe_signal(ACQUISITION_STATUS_REQUEST_SIGNAL)
        for instrument_id in sorted(self._tracker.expected, key=str):
            if self.cache.instrument(instrument_id) is not None:
                self._tracker.observe(instrument_id)
        for instrument_id in self._tracker.take_unrequested():
            self.request_instrument(instrument_id)
            self._instrument_requests += 1
        self._publish_status()
        self._start_bootstrap_feeds_if_ready()

    def on_instrument(self, instrument) -> None:  # noqa: ANN001
        if self._tracker.observe(instrument.id):
            self._instruments_received += 1
            self.log.info(f"INSTRUMENT_ACQUIRED | instrument_id={instrument.id}")
            self._publish_status()
            self._start_bootstrap_feeds_if_ready()
        elif instrument.id in self._tracker.expected:
            self._duplicate_instruments += 1

    def on_signal(self, signal: Signal) -> None:
        if signal.name != ACQUISITION_STATUS_REQUEST_SIGNAL:
            return
        self._status_requests += 1
        try:
            AcquisitionStatusRequest.from_signal_value(signal.value)
        except ValueError as exc:
            self._malformed_status_requests += 1
            self.log.error(
                "ACQUISITION_STATUS_REQUEST_REJECTED"
                f" | reason=invalid_request | error={type(exc).__name__}",
            )
            return
        self._publish_status()

    def on_quote(self, quote) -> None:  # noqa: ANN001
        self._observe(str(quote.instrument_id), FeedKind.QUOTES)

    def on_trade(self, trade) -> None:  # noqa: ANN001
        self._observe(str(trade.instrument_id), FeedKind.TRADES)

    def on_bar(self, bar) -> None:  # noqa: ANN001
        instrument_id = str(bar.bar_type.instrument_id)
        selector = str(bar.bar_type).removeprefix(f"{instrument_id}-")
        self._observe(instrument_id, FeedKind.BARS, selector)

    def on_instrument_status(self, status) -> None:  # noqa: ANN001
        self._observe(str(status.instrument_id), FeedKind.INSTRUMENT_STATUS)

    def on_stop(self) -> None:
        for demand in self._bootstrap_demands:
            self._publish_lifecycle_events(
                self._coordinator.cancel(demand.demand_id, now=self.clock.utc_now()),
            )
        self.unsubscribe_signal(ACQUISITION_STATUS_REQUEST_SIGNAL)
        self.log.info(
            "DATA_ACQUISITION_SUMMARY"
            f" | instrument_requests={self._instrument_requests}"
            f" | instruments_received={self._instruments_received}"
            f" | duplicate_instruments={self._duplicate_instruments}"
            f" | status_requests={self._status_requests}"
            f" | malformed_status_requests={self._malformed_status_requests}"
            f" | statuses_published={self._statuses_published}"
            f" | streams_subscribed={self._lifecycle_counts['SUBSCRIBED']}"
            f" | streams_active={self._lifecycle_counts['ACTIVE']}"
            f" | observations={sum(self._observation_counts.values())}",
        )

    def on_fault(self) -> None:
        if self._failure_published:
            return
        self._failure_published = True
        self.publish_signal(
            COMPONENT_FAILURE_SIGNAL,
            ComponentFailureEvent(
                component="data_acquisition",
                code="actor_faulted",
                reason="data acquisition actor entered fault state",
                evidence={
                    "available_instrument_count": len(self._tracker.available),
                    "expected_instrument_count": len(self._tracker.expected),
                },
            ).to_signal_value(),
        )

    def _publish_status(self) -> None:
        status = self._tracker.status(str(self.actor_id))
        self.publish_signal(ACQUISITION_STATUS_SIGNAL, status.to_signal_value())
        self._statuses_published += 1
        self.log.info(
            f"ACQUISITION_STATUS | state={status.state}"
            f" | available={len(status.available_instrument_ids)}"
            f"/{len(status.expected_instrument_ids)}",
        )

    def _start_bootstrap_feeds_if_ready(self) -> None:
        if self._feeds_started or self._tracker.missing:
            return
        self._feeds_started = True
        for demand in self._bootstrap_demands:
            self._publish_lifecycle_events(
                self._coordinator.request(demand, now=self.clock.utc_now()),
            )

    def _observe(
        self,
        instrument_id: str,
        kind: FeedKind,
        selector: str = "default",
    ) -> None:
        stream_key = (instrument_id, kind.value, selector)
        if stream_key not in self._bootstrap_stream_keys:
            return
        self._observation_counts[stream_key] += 1
        event = self._coordinator.observe(stream_key)
        if event is not None:
            self._publish_lifecycle_events((event,))

    def _publish_lifecycle_events(
        self,
        events: tuple[AcquisitionLifecycleEvent, ...],
    ) -> None:
        for event in events:
            self._lifecycle_counts[event.state.value] += 1
            instrument_id, feed_kind, selector = event.stream_key
            message = AcquisitionStreamEvent(
                state=event.state.value,
                instrument_id=instrument_id,
                feed_kind=feed_kind,
                selector=selector,
                source=str(self.actor_id),
                demand_id=event.demand_id,
                consumer_ids=event.consumer_ids,
                detail=event.detail,
            )
            self.publish_signal(ACQUISITION_STREAM_SIGNAL, message.to_signal_value())
            self.log.info(
                f"ACQUISITION_STREAM | state={message.state}"
                f" | instrument_id={message.instrument_id}"
                f" | feed={message.feed_kind}/{message.selector}"
                f" | consumers={len(message.consumer_ids)}"
                f" | detail={message.detail}",
            )


def _build_bootstrap_demands(
    feeds: tuple[dict[str, str], ...],
) -> tuple[ObservationDemand, ...]:
    demands: list[ObservationDemand] = []
    for index, feed in enumerate(feeds):
        kind = FeedKind(feed["kind"])
        requirement = FeedRequirement(
            instrument_id=feed["instrument_id"],
            kind=kind,
            selector=feed["selector"],
        )
        demands.append(
            ObservationDemand(
                demand_id=f"bootstrap:{index}:{'/'.join(requirement.stream_key)}",
                owner=DemandOwner(DemandOwnerKind.BOOTSTRAP, "system-config"),
                requirement=requirement,
                priority=50,
                purpose="configured bootstrap native stream",
            ),
        )
    return tuple(demands)
