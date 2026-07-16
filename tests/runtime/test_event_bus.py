from __future__ import annotations

from datetime import UTC, datetime
from threading import Thread

import pytest
from markeitech.runtime import BoundedEventLoopBridge, DomainEventOfferStatus
from markeitech.runtime.events import CommittedDomainEvent, MarkeitechBusTopic

NOW = datetime(2026, 7, 16, 9, 0, tzinfo=UTC)


def event(sequence: int) -> CommittedDomainEvent:
    return CommittedDomainEvent(
        topic=MarkeitechBusTopic.FEATURE_COMMITTED,
        event_id=f"feature-{sequence}",
        occurred_ts=NOW,
        aggregate_id="NQU6.CME:market_context",
        payload_type="MarketContextFeatureSnapshot",
        payload_id=f"feature-{sequence}",
        instrument_id="NQU6.CME",
        commit_sequence=sequence,
    )


def test_committed_event_requires_sequence() -> None:
    payload = event(1).model_dump(exclude_computed_fields=True)
    payload["commit_sequence"] = None
    with pytest.raises(ValueError, match="durable commit sequence"):
        CommittedDomainEvent.model_validate(payload)


def test_worker_offer_publishes_only_through_scheduled_callback() -> None:
    callbacks = []
    published = []
    bridge = BoundedEventLoopBridge(4, drain_batch_size=2)
    bridge.bind(callbacks.append, lambda topic, value: published.append((topic, value)))

    worker = Thread(target=lambda: bridge.offer(event(1)))
    worker.start()
    worker.join()

    assert published == []
    assert len(callbacks) == 1
    callbacks.pop(0)()
    assert published == [(MarkeitechBusTopic.FEATURE_COMMITTED.value, event(1))]
    assert bridge.snapshot.published_count == 1


def test_bridge_preserves_order_across_bounded_batches() -> None:
    callbacks = []
    published = []
    bridge = BoundedEventLoopBridge(5, drain_batch_size=2)
    for sequence in range(1, 6):
        assert bridge.offer(event(sequence)) == DomainEventOfferStatus.ACCEPTED
    bridge.bind(callbacks.append, lambda _topic, value: published.append(value.commit_sequence))

    while callbacks:
        callbacks.pop(0)()

    assert published == [1, 2, 3, 4, 5]
    assert bridge.snapshot.pending_count == 0


def test_bridge_reports_saturation_and_closed_rejection() -> None:
    bridge = BoundedEventLoopBridge(1)

    assert bridge.offer(event(1)) == DomainEventOfferStatus.ACCEPTED
    assert bridge.offer(event(2)) == DomainEventOfferStatus.QUEUE_FULL
    bridge.close(discard_pending=True)
    assert bridge.offer(event(3)) == DomainEventOfferStatus.CLOSED

    snapshot = bridge.snapshot
    assert snapshot.pending_count == 0
    assert snapshot.rejected_count == 3


def test_batch_offer_is_all_or_nothing() -> None:
    bridge = BoundedEventLoopBridge(2)

    assert bridge.offer_batch((event(1), event(2))) == DomainEventOfferStatus.ACCEPTED
    assert bridge.offer_batch((event(3), event(4))) == DomainEventOfferStatus.QUEUE_FULL

    snapshot = bridge.snapshot
    assert snapshot.pending_count == 2
    assert snapshot.accepted_count == 2
    assert snapshot.rejected_count == 2


def test_schedule_failure_retains_event_for_explicit_retry() -> None:
    callbacks = []
    attempts = 0

    def schedule(callback) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("event loop unavailable")
        callbacks.append(callback)

    bridge = BoundedEventLoopBridge(2)
    bridge.bind(schedule, lambda _topic, _value: None)

    assert bridge.offer(event(1)) == DomainEventOfferStatus.SCHEDULE_FAILED
    assert bridge.snapshot.pending_count == 1
    assert bridge.retry_schedule()
    callbacks.pop()()
    assert bridge.snapshot.published_count == 1


def test_publish_failure_isolated_without_reordering_later_events() -> None:
    callbacks = []
    published = []

    def publish(_topic, value) -> None:
        if value.commit_sequence == 1:
            raise RuntimeError("subscriber failed")
        published.append(value.commit_sequence)

    bridge = BoundedEventLoopBridge(2)
    bridge.bind(callbacks.append, publish)
    bridge.offer(event(1))
    bridge.offer(event(2))
    callbacks.pop()()

    assert published == [2]
    assert bridge.snapshot.publish_failure_count == 1
    assert bridge.snapshot.last_error == "RuntimeError: subscriber failed"


def test_graceful_close_drains_all_accepted_batches() -> None:
    callbacks = []
    published = []
    bridge = BoundedEventLoopBridge(3, drain_batch_size=1)
    bridge.bind(callbacks.append, lambda _topic, value: published.append(value.commit_sequence))
    for sequence in range(1, 4):
        assert bridge.offer(event(sequence)) == DomainEventOfferStatus.ACCEPTED

    bridge.close()
    while callbacks:
        callbacks.pop(0)()

    assert published == [1, 2, 3]
    assert bridge.snapshot.pending_count == 0
