from __future__ import annotations

from threading import Event
from uuid import uuid4

from markeitech.system.messages import SystemHealthEvent
from markeitech.system.persistence import HealthEventRecord, PersistenceWorker


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


def test_persistence_worker_rejects_when_bounded_queue_is_full() -> None:
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
    assert worker.submit(_record(3)) is False
    release.set()
    assert worker.close()
    stats = worker.snapshot()
    assert stats.accepted == 2
    assert stats.stored == 2
    assert stats.rejected == 1
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
