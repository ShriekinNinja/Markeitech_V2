from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from threading import Lock

from markeitech.runtime.events import CommittedDomainEvent

type EventLoopScheduler = Callable[[Callable[[], None]], None]
type DomainEventPublisher = Callable[[str, object], None]


class DomainEventBridgeStatus(StrEnum):
    CREATED = "created"
    BOUND = "bound"
    CLOSED = "closed"


class DomainEventOfferStatus(StrEnum):
    ACCEPTED = "accepted"
    QUEUE_FULL = "queue_full"
    CLOSED = "closed"
    SCHEDULE_FAILED = "schedule_failed"


@dataclass(frozen=True)
class DomainEventBridgeSnapshot:
    status: DomainEventBridgeStatus
    pending_count: int
    accepted_count: int
    published_count: int
    rejected_count: int
    schedule_failure_count: int
    publish_failure_count: int
    is_scheduled: bool
    last_error: str | None


class BoundedEventLoopBridge:
    """Moves committed notices from worker threads onto one event-loop publisher."""

    def __init__(self, capacity: int, *, drain_batch_size: int | None = None) -> None:
        if capacity < 1:
            raise ValueError("domain event bridge capacity must be positive")
        if drain_batch_size is None:
            drain_batch_size = min(64, capacity)
        if drain_batch_size < 1 or drain_batch_size > capacity:
            raise ValueError("domain event drain batch size must be within bridge capacity")
        self._capacity = capacity
        self._drain_batch_size = drain_batch_size
        self._queue: deque[CommittedDomainEvent] = deque()
        self._status = DomainEventBridgeStatus.CREATED
        self._scheduler: EventLoopScheduler | None = None
        self._publisher: DomainEventPublisher | None = None
        self._is_scheduled = False
        self._accepted_count = 0
        self._published_count = 0
        self._rejected_count = 0
        self._schedule_failure_count = 0
        self._publish_failure_count = 0
        self._last_error: str | None = None
        self._lock = Lock()

    @property
    def snapshot(self) -> DomainEventBridgeSnapshot:
        with self._lock:
            return DomainEventBridgeSnapshot(
                status=self._status,
                pending_count=len(self._queue),
                accepted_count=self._accepted_count,
                published_count=self._published_count,
                rejected_count=self._rejected_count,
                schedule_failure_count=self._schedule_failure_count,
                publish_failure_count=self._publish_failure_count,
                is_scheduled=self._is_scheduled,
                last_error=self._last_error,
            )

    def bind(self, scheduler: EventLoopScheduler, publisher: DomainEventPublisher) -> None:
        schedule = False
        with self._lock:
            if self._status != DomainEventBridgeStatus.CREATED:
                raise RuntimeError("domain event bridge can only bind once")
            self._scheduler = scheduler
            self._publisher = publisher
            self._status = DomainEventBridgeStatus.BOUND
            if self._queue:
                self._is_scheduled = True
                schedule = True
        if schedule:
            self._schedule_drain()

    def offer(self, event: CommittedDomainEvent) -> DomainEventOfferStatus:
        return self.offer_batch((event,))

    def offer_batch(
        self,
        events: tuple[CommittedDomainEvent, ...],
    ) -> DomainEventOfferStatus:
        if not events:
            return DomainEventOfferStatus.ACCEPTED
        schedule = False
        with self._lock:
            if self._status == DomainEventBridgeStatus.CLOSED:
                self._rejected_count += len(events)
                return DomainEventOfferStatus.CLOSED
            if len(self._queue) + len(events) > self._capacity:
                self._rejected_count += len(events)
                return DomainEventOfferStatus.QUEUE_FULL
            self._queue.extend(events)
            self._accepted_count += len(events)
            if self._status == DomainEventBridgeStatus.BOUND and not self._is_scheduled:
                self._is_scheduled = True
                schedule = True
        if schedule and not self._schedule_drain():
            return DomainEventOfferStatus.SCHEDULE_FAILED
        return DomainEventOfferStatus.ACCEPTED

    def retry_schedule(self) -> bool:
        with self._lock:
            if (
                self._status != DomainEventBridgeStatus.BOUND
                or not self._queue
                or self._is_scheduled
            ):
                return False
            self._is_scheduled = True
        return self._schedule_drain()

    def close(self, *, discard_pending: bool = False) -> None:
        schedule = False
        with self._lock:
            if self._status == DomainEventBridgeStatus.CLOSED:
                return
            self._status = DomainEventBridgeStatus.CLOSED
            if discard_pending:
                self._rejected_count += len(self._queue)
                self._queue.clear()
            elif self._queue and self._publisher is not None and not self._is_scheduled:
                self._is_scheduled = True
                schedule = True
        if schedule:
            self._schedule_drain()

    def _schedule_drain(self) -> bool:
        assert self._scheduler is not None
        try:
            self._scheduler(self._drain_on_event_loop)
        except Exception as exc:
            with self._lock:
                self._is_scheduled = False
                self._schedule_failure_count += 1
                self._last_error = f"{type(exc).__name__}: {exc}"
            return False
        return True

    def _drain_on_event_loop(self) -> None:
        with self._lock:
            values = tuple(
                self._queue.popleft() for _ in range(min(self._drain_batch_size, len(self._queue)))
            )
            publisher = self._publisher
            self._is_scheduled = False
        assert publisher is not None
        for event in values:
            try:
                publisher(event.topic.value, event)
            except Exception as exc:
                with self._lock:
                    self._publish_failure_count += 1
                    self._last_error = f"{type(exc).__name__}: {exc}"
            else:
                with self._lock:
                    self._published_count += 1
        with self._lock:
            schedule = bool(self._queue)
            if schedule:
                self._is_scheduled = True
        if schedule:
            self._schedule_drain()
