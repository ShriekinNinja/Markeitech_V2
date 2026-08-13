from __future__ import annotations

from threading import Event, Thread
from uuid import uuid4

import pytest
from nautilus_trader.common import Signal

from markeitech.system.messages import (
    ACQUISITION_STATUS_REQUEST_SIGNAL,
    ACQUISITION_STREAM_SIGNAL,
    WATCHLIST_DEMAND_SIGNAL,
    WATCHLIST_LIFECYCLE_SIGNAL,
    WATCHLIST_MEMBERSHIP_SIGNAL,
    AcquisitionStatusRequest,
    AcquisitionStreamEvent,
    SystemHealthEvent,
    WatchlistDemandEvent,
    WatchlistLifecycleEvent,
    WatchlistMember,
    WatchlistMembershipEvent,
)
from markeitech.system.persistence import (
    HealthEventRecord,
    OperationalEventRecord,
    PersistenceWorker,
    _record_from_signal,
)


def test_operational_event_record_validates_durable_identity_and_timestamps() -> None:
    record = OperationalEventRecord(
        event_id=" watchlist-membership:1 ",
        run_id=uuid4(),
        sequence=1,
        signal_name=" markeitech.watchlist.membership ",
        event_type=" watchlist.membership ",
        source=" WATCHLIST ",
        correlation_id=" baseline:config ",
        causation_id=None,
        payload={"membership_revision": 1},
        ts_event_ns=10,
        ts_init_ns=11,
        schema_version=1,
    )

    assert record.event_id == "watchlist-membership:1"
    assert record.signal_name == "markeitech.watchlist.membership"
    assert record.correlation_id == "baseline:config"
    with pytest.raises(TypeError):
        record.payload["membership_revision"] = 2  # type: ignore[index]

    with pytest.raises(ValueError, match="sequence must be a positive integer"):
        OperationalEventRecord(
            event_id="watchlist-membership:2",
            run_id=uuid4(),
            sequence=0,
            signal_name="markeitech.watchlist.membership",
            event_type="watchlist.membership",
            source="WATCHLIST",
            payload={},
            ts_event_ns=10,
            ts_init_ns=11,
            schema_version=1,
        )


def test_worker_preserves_order_across_health_and_generic_operational_records() -> None:
    run_id = uuid4()
    stored: list[tuple[int, str]] = []
    worker = PersistenceWorker(
        lambda record: stored.append((record.sequence, type(record).__name__)),
        queue_capacity=4,
        shutdown_timeout_seconds=1,
        write_max_attempts=1,
        write_retry_backoff_ms=0,
    )
    worker.start()

    assert worker.submit(_record(1, "STARTING"))
    assert worker.submit(
        OperationalEventRecord(
            event_id="watchlist-membership:1",
            run_id=run_id,
            sequence=2,
            signal_name=WATCHLIST_MEMBERSHIP_SIGNAL,
            event_type="watchlist.membership",
            source="WATCHLIST",
            payload={"membership_revision": 1},
            ts_event_ns=2,
            ts_init_ns=2,
            schema_version=1,
        ),
    )
    assert worker.close()

    assert stored == [
        (1, "HealthEventRecord"),
        (2, "OperationalEventRecord"),
    ]


def test_watchlist_signals_convert_to_auditable_records_without_market_payloads() -> None:
    run_id = uuid4()
    membership = WatchlistMembershipEvent(
        event_id="watchlist-membership:1",
        membership_revision=1,
        source="WATCHLIST",
        reason="static baseline",
        members=(
            WatchlistMember(
                instrument_id="ESU6.CME",
                capabilities=("top_of_book", "watchlist_last"),
                owner_ids=("config:system",),
            ),
        ),
    )
    membership_record = _record_from_signal(
        run_id,
        1,
        Signal(
            name=WATCHLIST_MEMBERSHIP_SIGNAL,
            value=membership.to_signal_value(),
            ts_event=10,
            ts_init=11,
        ),
    )
    lifecycle = WatchlistLifecycleEvent(
        event_id="watchlist-lifecycle:1",
        membership_revision=1,
        state="CONFIGURED",
        source="WATCHLIST",
        reason="static baseline",
        owner_id="config:system",
        correlation_id="watchlist-membership:1",
    )
    lifecycle_record = _record_from_signal(
        run_id,
        2,
        Signal(
            name=WATCHLIST_LIFECYCLE_SIGNAL,
            value=lifecycle.to_signal_value(),
            ts_event=12,
            ts_init=13,
        ),
    )
    demand = WatchlistDemandEvent(
        demand_id="watchlist:1:ESU6.CME/quotes/default",
        action="REQUEST",
        instrument_id="ESU6.CME",
        capability="top_of_book",
        feed_kind="quotes",
        selector="default",
        owner_id="config:system",
        purpose="static watchlist top_of_book",
    )
    demand_record = _record_from_signal(
        run_id,
        3,
        Signal(
            name=WATCHLIST_DEMAND_SIGNAL,
            value=demand.to_signal_value(),
            ts_event=14,
            ts_init=15,
        ),
    )

    assert isinstance(membership_record, OperationalEventRecord)
    assert membership_record.event_type == "watchlist.membership"
    assert membership_record.correlation_id == membership.event_id
    assert "best_bid" not in membership_record.payload
    assert isinstance(lifecycle_record, OperationalEventRecord)
    assert lifecycle_record.event_type == "watchlist.lifecycle"
    assert lifecycle_record.correlation_id == membership.event_id
    assert isinstance(demand_record, OperationalEventRecord)
    assert demand_record.event_type == "watchlist.demand"
    assert demand_record.correlation_id == demand.demand_id
    assert "best_bid" not in demand_record.payload


def test_existing_acquisition_intent_and_outcome_convert_to_audit_records() -> None:
    run_id = uuid4()
    request = AcquisitionStatusRequest(requester="SYSTEM-CONTROL")
    request_record = _record_from_signal(
        run_id,
        1,
        Signal(
            name=ACQUISITION_STATUS_REQUEST_SIGNAL,
            value=request.to_signal_value(),
            ts_event=10,
            ts_init=11,
        ),
    )
    stream = AcquisitionStreamEvent(
        state="SUBSCRIBED",
        instrument_id="ESU6.CME",
        feed_kind="quotes",
        selector="default",
        source="DATA-ACQUISITION",
        demand_id="watchlist:1:ESU6.CME/quotes/default",
        consumer_ids=("watchlist:1:ESU6.CME/quotes/default",),
        detail="native subscription command issued",
    )
    stream_record = _record_from_signal(
        run_id,
        2,
        Signal(
            name=ACQUISITION_STREAM_SIGNAL,
            value=stream.to_signal_value(),
            ts_event=12,
            ts_init=13,
        ),
    )

    assert isinstance(request_record, OperationalEventRecord)
    assert request_record.event_type == "acquisition.status_request"
    assert request_record.source == "SYSTEM-CONTROL"
    assert isinstance(stream_record, OperationalEventRecord)
    assert stream_record.event_type == "acquisition.stream"
    assert stream_record.correlation_id == stream.demand_id
    assert "bid_price" not in stream_record.payload


def _record(sequence: int, state: str = "READY") -> HealthEventRecord:
    return HealthEventRecord(
        run_id=uuid4(),
        sequence=sequence,
        event=SystemHealthEvent(
            state=state,
            reason="test transition",
            source="SYSTEM-CONTROL",
            evidence={"probe": True},
        ),
        ts_event_ns=sequence,
        ts_init_ns=sequence + 1,
    )


def test_persistence_worker_preserves_accepted_order_and_drains_on_close() -> None:
    stored: list[int] = []
    worker = PersistenceWorker(
        lambda record: stored.append(record.sequence),
        queue_capacity=4,
        shutdown_timeout_seconds=1,
        write_max_attempts=3,
        write_retry_backoff_ms=0,
    )
    worker.start()

    assert worker.submit(_record(1, "STARTING"))
    assert worker.submit(_record(2, "READY"))
    assert worker.close()

    assert stored == [1, 2]
    assert worker.results.get_nowait().stored is True
    assert worker.results.get_nowait().stored is True


def test_persistence_worker_reports_write_failure_without_dying() -> None:
    attempted: list[int] = []

    def write(record: HealthEventRecord) -> None:
        attempted.append(record.sequence)
        if record.sequence == 1:
            raise RuntimeError("database unavailable")

    worker = PersistenceWorker(
        write,
        queue_capacity=4,
        shutdown_timeout_seconds=1,
        write_max_attempts=1,
        write_retry_backoff_ms=0,
    )
    worker.start()
    assert worker.submit(_record(1, "READY"))
    assert worker.submit(_record(2, "DEGRADED"))
    assert worker.close()

    first = worker.results.get_nowait()
    second = worker.results.get_nowait()
    assert attempted == [1, 2]
    assert first.stored is False and first.error_code == "RuntimeError"
    assert first.attempts == 1
    assert second.stored is True


def test_persistence_worker_retries_a_write_within_the_configured_bound() -> None:
    attempts = 0

    def eventually_write(_record: HealthEventRecord) -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("temporary database failure")

    worker = PersistenceWorker(
        eventually_write,
        queue_capacity=1,
        shutdown_timeout_seconds=1,
        write_max_attempts=3,
        write_retry_backoff_ms=0,
    )
    worker.start()
    assert worker.submit(_record(1))
    assert worker.close()

    result = worker.results.get_nowait()
    stats = worker.snapshot()
    assert result.stored is True and result.attempts == 3
    assert stats.accepted == 1
    assert stats.stored == 1
    assert stats.retry_attempts == 2
    assert stats.failed == 0
    assert stats.rejected == 0
    assert stats.pending == 0


def test_persistence_worker_applies_backpressure_when_bounded_queue_is_full() -> None:
    release = Event()
    entered = Event()

    def blocked_write(_record: HealthEventRecord) -> None:
        entered.set()
        release.wait(timeout=2)

    worker = PersistenceWorker(
        blocked_write,
        queue_capacity=1,
        shutdown_timeout_seconds=2,
        write_max_attempts=1,
        write_retry_backoff_ms=0,
    )
    worker.start()
    assert worker.submit(_record(1))
    assert entered.wait(timeout=1)
    assert worker.submit(_record(2))

    submitted = Event()

    def submit_third() -> None:
        assert worker.submit(_record(3))
        submitted.set()

    submitter = Thread(target=submit_third)
    submitter.start()
    assert not submitted.wait(timeout=0.05)
    release.set()
    submitter.join(timeout=1)
    assert submitted.is_set()
    assert worker.close()
    stats = worker.snapshot()
    assert stats.accepted == 3
    assert stats.stored == 3
    assert stats.rejected == 0
    assert stats.pending == 0


def test_persistence_worker_can_finish_after_an_initial_close_timeout() -> None:
    release = Event()
    entered = Event()

    def blocked_write(_record: HealthEventRecord) -> None:
        entered.set()
        release.wait(timeout=2)

    worker = PersistenceWorker(
        blocked_write,
        queue_capacity=1,
        shutdown_timeout_seconds=0.05,
        write_max_attempts=1,
        write_retry_backoff_ms=0,
    )
    worker.start()
    assert worker.submit(_record(1))
    assert entered.wait(timeout=1)

    assert worker.close() is False
    release.set()
    assert worker.close() is True
    assert worker.snapshot().pending == 0
