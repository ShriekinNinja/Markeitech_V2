from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable

from nautilus_trader.common.actor import Actor

from markeitech.runtime.event_bus import BoundedEventLoopBridge
from markeitech.runtime.events import CommittedDomainEvent, MarkeitechBusTopic


class BoundedEventIdentityWindow:
    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError("event identity window capacity must be positive")
        self._capacity = capacity
        self._seen: OrderedDict[str, None] = OrderedDict()
        self._duplicate_count = 0

    @property
    def duplicate_count(self) -> int:
        return self._duplicate_count

    def observe(self, dedupe_key: str) -> bool:
        if dedupe_key in self._seen:
            self._seen.move_to_end(dedupe_key)
            self._duplicate_count += 1
            return False
        self._seen[dedupe_key] = None
        if len(self._seen) > self._capacity:
            self._seen.popitem(last=False)
        return True


class OperatorEventProjectionActor(Actor):
    """Minimal proof consumer for committed Markeitech domain notices."""

    def __init__(
        self,
        bridge: BoundedEventLoopBridge,
        scheduler: Callable[[Callable[[], None]], None],
        *,
        dedupe_size: int,
    ) -> None:
        super().__init__()
        if dedupe_size < 1:
            raise ValueError("operator event projection dedupe size must be positive")
        self._bridge = bridge
        self._scheduler = scheduler
        self._identities = BoundedEventIdentityWindow(dedupe_size)

    def on_start(self) -> None:
        self.msgbus.subscribe(
            MarkeitechBusTopic.FEATURE_COMMITTED.value,
            self._on_feature_committed,
        )
        self._bridge.bind(self._scheduler, self.msgbus.publish)

    def on_stop(self) -> None:
        self.msgbus.unsubscribe(
            MarkeitechBusTopic.FEATURE_COMMITTED.value,
            self._on_feature_committed,
        )
        self._bridge.close(discard_pending=True)
        snapshot = self._bridge.snapshot
        message = (
            "MARKET_EVENT_RUNTIME | event=STOPPED "
            f"| accepted={snapshot.accepted_count} | published={snapshot.published_count} "
            f"| rejected={snapshot.rejected_count} "
            f"| schedule_failures={snapshot.schedule_failure_count} "
            f"| publish_failures={snapshot.publish_failure_count} "
            f"| duplicates={self._identities.duplicate_count}"
        )
        unhealthy = (
            snapshot.rejected_count
            or snapshot.schedule_failure_count
            or snapshot.publish_failure_count
        )
        if unhealthy:
            self.log.warning(message)
        else:
            self.log.info(message)

    def _on_feature_committed(self, event: CommittedDomainEvent) -> None:
        if not self._identities.observe(event.dedupe_key):
            return
        self.log.info(
            "MARKET_EVENT | event=FEATURE_COMMITTED "
            f"| instrument={event.instrument_id} | aggregate={event.aggregate_id} "
            f"| sequence={event.commit_sequence} | payload_id={event.payload_id}"
        )
