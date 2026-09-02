from __future__ import annotations

from collections import Counter

from nautilus_trader.common import DataActor, DataActorConfig
from nautilus_trader.model import ActorId, ClientId, InstrumentId

from markeitech.acquisition import FeedKind, FeedRequirement

_UNSUBSCRIBE_TIMER = "native-consumer-probe-unsubscribe"
_IB_CLIENT_ID = ClientId.from_str("IB")


class NativeConsumerProbeActorConfig(DataActorConfig):
    def __new__(
        cls,
        feeds: list[dict[str, str]],
        unsubscribe_after_seconds: int,
        actor_id: str | ActorId = "NATIVE-CONSUMER-PROBE",
    ) -> NativeConsumerProbeActorConfig:
        resolved_actor_id = (
            actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        )
        obj = super().__new__(cls, actor_id=resolved_actor_id)
        obj.feeds = tuple(feeds)
        obj.unsubscribe_after_seconds = unsubscribe_after_seconds
        return obj


class NativeConsumerProbeActor(DataActor):
    """Temporary probe for native multi-actor market-data delivery.

    Markeitech Metadata:
        architecture.component.id: actor.native-consumer-probe
        architecture.component.label: Native Consumer Probe
        architecture.component.kind: markeitech_actor
        architecture.component.boundary: boundary.system
    """

    def __init__(self, config: NativeConsumerProbeActorConfig) -> None:
        super().__init__(config)
        self._requirements = _build_probe_requirements(config.feeds)
        self._stream_keys = frozenset(item.stream_key for item in self._requirements)
        self._unsubscribe_after_seconds = config.unsubscribe_after_seconds
        self._counts: Counter[tuple[str, str, str]] = Counter()
        self._post_unsubscribe_counts: Counter[tuple[str, str, str]] = Counter()
        self._first_observed: set[tuple[str, str, str]] = set()
        self._unsubscribed = False

    def on_start(self) -> None:
        for requirement in self._requirements:
            self._subscribe(requirement)
        self.clock.set_time_alert_ns(
            _UNSUBSCRIBE_TIMER,
            self.clock.timestamp_ns() + self._unsubscribe_after_seconds * 1_000_000_000,
            callback=self._unsubscribe_probe,
        )
        self.log.info(
            "NATIVE_CONSUMER_PROBE_STARTED"
            f" | streams={len(self._requirements)}"
            f" | unsubscribe_after_seconds={self._unsubscribe_after_seconds}",
        )

    def on_quote(self, quote) -> None:  # noqa: ANN001
        self._observe((str(quote.instrument_id), FeedKind.QUOTES.value, "default"))

    def on_trade(self, trade) -> None:  # noqa: ANN001
        self._observe((str(trade.instrument_id), FeedKind.TRADES.value, "default"))

    def on_stop(self) -> None:
        if not self._unsubscribed:
            self._unsubscribe_probe(None)
        for stream_key in sorted(self._stream_keys):
            instrument_id, kind, selector = stream_key
            self.log.info(
                "NATIVE_CONSUMER_PROBE_SUMMARY"
                f" | instrument_id={instrument_id}"
                f" | feed={kind}/{selector}"
                f" | observations={self._counts[stream_key]}"
                f" | after_unsubscribe={self._post_unsubscribe_counts[stream_key]}",
            )

    def _subscribe(self, requirement: FeedRequirement) -> None:
        instrument_id = InstrumentId.from_str(requirement.instrument_id)
        if requirement.kind is FeedKind.QUOTES:
            self.subscribe_quotes(instrument_id, client_id=_IB_CLIENT_ID)
        elif requirement.kind is FeedKind.TRADES:
            self.subscribe_trades(instrument_id, client_id=_IB_CLIENT_ID)

    def _unsubscribe_probe(self, _event) -> None:  # noqa: ANN001
        if self._unsubscribed:
            return
        before = sum(self._counts.values())
        for requirement in self._requirements:
            instrument_id = InstrumentId.from_str(requirement.instrument_id)
            if requirement.kind is FeedKind.QUOTES:
                self.unsubscribe_quotes(instrument_id, client_id=_IB_CLIENT_ID)
            elif requirement.kind is FeedKind.TRADES:
                self.unsubscribe_trades(instrument_id, client_id=_IB_CLIENT_ID)
        self._unsubscribed = True
        self.log.info(
            "NATIVE_CONSUMER_PROBE_UNSUBSCRIBED"
            f" | streams={len(self._requirements)}"
            f" | observations_before={before}",
        )

    def _observe(self, stream_key: tuple[str, str, str]) -> None:
        if stream_key not in self._stream_keys:
            return
        self._counts[stream_key] += 1
        if self._unsubscribed:
            self._post_unsubscribe_counts[stream_key] += 1
        if stream_key in self._first_observed:
            return
        self._first_observed.add(stream_key)
        instrument_id, kind, selector = stream_key
        self.log.info(
            "NATIVE_CONSUMER_PROBE_FIRST_OBSERVATION"
            f" | instrument_id={instrument_id}"
            f" | feed={kind}/{selector}",
        )


def _build_probe_requirements(
    feeds: tuple[dict[str, str], ...],
) -> tuple[FeedRequirement, ...]:
    requirements = tuple(
        FeedRequirement(
            instrument_id=feed["instrument_id"],
            kind=FeedKind(feed["kind"]),
            selector=feed["selector"],
        )
        for feed in feeds
    )
    unsupported = [
        item
        for item in requirements
        if item.kind not in {FeedKind.QUOTES, FeedKind.TRADES}
    ]
    if unsupported:
        raise ValueError("native consumer probe supports quote and trade feeds only")
    return requirements
