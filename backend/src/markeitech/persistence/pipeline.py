from __future__ import annotations

from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from threading import Condition, Thread
from time import monotonic
from typing import Protocol

from nautilus_trader.model.data import QuoteTick, TradeTick

from markeitech.domain.base import unix_ns_from_utc_datetime
from markeitech.domain.market_data import OneMinuteBar
from markeitech.persistence.config import PersistenceConfig
from markeitech.persistence.contracts import PersistenceEventIdentity
from markeitech.persistence.coordinator import PersistenceWriteResult
from markeitech.persistence.journal import (
    DurableIngressJournal,
    JournalCorruptionError,
    JournalEntry,
)


class PersistenceBatchWriter(Protocol):
    def persist_closed_batch(self, events: Sequence[object]) -> PersistenceWriteResult: ...


class PersistenceIdentityResolver(Protocol):
    def identify(self, events: Sequence[object]) -> tuple[PersistenceEventIdentity, ...]: ...


class PersistenceWriterStatus(StrEnum):
    STOPPED = "stopped"
    RECOVERING = "recovering"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"


class PersistenceSubmissionStatus(StrEnum):
    ACCEPTED = "accepted"
    QUEUE_FULL = "queue_full"
    NOT_RUNNING = "not_running"
    WRITER_FAILED = "writer_failed"
    UNSUPPORTED = "unsupported"
    PROVISIONAL = "provisional"


@dataclass(frozen=True)
class PersistenceWriterSnapshot:
    status: PersistenceWriterStatus
    pending_count: int
    accepted_count: int
    journaled_count: int
    recovered_count: int
    persisted_count: int
    duplicate_count: int
    committed_batch_count: int
    rejected_full_count: int
    rejected_invalid_count: int
    journal_bytes: int
    last_error: str | None


@dataclass
class _BufferedEvent:
    event: object
    identity: PersistenceEventIdentity
    journal_path: Path


class BoundedPersistenceWriter:
    """Owns bounded buffering and all blocking persistence work on one thread."""

    def __init__(
        self,
        config: PersistenceConfig,
        coordinator: PersistenceBatchWriter,
        catalog: PersistenceIdentityResolver,
        *,
        journal: DurableIngressJournal | None = None,
        clock: Callable[[], datetime] | None = None,
        on_health_change: Callable[[PersistenceWriterSnapshot], None] | None = None,
    ) -> None:
        self._config = config
        self._coordinator = coordinator
        self._catalog = catalog
        self._journal = journal or DurableIngressJournal(config)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._on_health_change = on_health_change
        self._condition = Condition()
        self._ingress: deque[object] = deque()
        self._recovery: deque[JournalEntry] = deque()
        self._buckets: dict[tuple[str, str, str, int], list[_BufferedEvent]] = {}
        self._status = PersistenceWriterStatus.STOPPED
        self._thread: Thread | None = None
        self._force_flush = False
        self._pending_count = 0
        self._accepted_count = 0
        self._journaled_count = 0
        self._recovered_count = 0
        self._persisted_count = 0
        self._duplicate_count = 0
        self._committed_batch_count = 0
        self._rejected_full_count = 0
        self._rejected_invalid_count = 0
        self._last_error: str | None = None

    @property
    def snapshot(self) -> PersistenceWriterSnapshot:
        with self._condition:
            return self._snapshot_unlocked()

    def start(self) -> None:
        with self._condition:
            if self._status != PersistenceWriterStatus.STOPPED:
                raise RuntimeError("persistence writer can only start from stopped state")
            if self._pending_count != 0:
                raise RuntimeError("stopped persistence writer has pending events")
        try:
            recovered = self._journal.recover()
        except Exception as exc:
            with self._condition:
                self._status = PersistenceWriterStatus.FAILED
                self._last_error = f"{type(exc).__name__}: {exc}"
                snapshot = self._snapshot_unlocked()
            self._publish(snapshot)
            raise
        with self._condition:
            if self._status != PersistenceWriterStatus.STOPPED:
                raise RuntimeError("persistence writer start raced with another lifecycle call")
            self._recovery.extend(recovered)
            self._pending_count = len(recovered)
            self._recovered_count += len(recovered)
            self._status = (
                PersistenceWriterStatus.RECOVERING if recovered else PersistenceWriterStatus.RUNNING
            )
            self._last_error = None
            self._thread = Thread(
                target=self._run,
                name="markeitech-persistence-writer",
                daemon=False,
            )
            self._thread.start()
            snapshot = self._snapshot_unlocked()
        self._publish(snapshot)

    def submit(self, event: object) -> PersistenceSubmissionStatus:
        invalid = self._invalid_submission(event)
        if invalid is not None:
            with self._condition:
                self._rejected_invalid_count += 1
                snapshot = self._snapshot_unlocked()
            self._publish(snapshot)
            return invalid

        with self._condition:
            if self._status == PersistenceWriterStatus.FAILED:
                return PersistenceSubmissionStatus.WRITER_FAILED
            if self._status != PersistenceWriterStatus.RUNNING:
                return PersistenceSubmissionStatus.NOT_RUNNING
            if self._pending_count >= self._config.catalog_writer_queue_size:
                self._rejected_full_count += 1
                snapshot = self._snapshot_unlocked()
                result = PersistenceSubmissionStatus.QUEUE_FULL
            else:
                self._ingress.append(event)
                self._pending_count += 1
                self._accepted_count += 1
                self._condition.notify()
                snapshot = self._snapshot_unlocked()
                result = PersistenceSubmissionStatus.ACCEPTED
        self._publish(snapshot)
        return result

    def flush(self, timeout: float | None = None) -> bool:
        deadline = None if timeout is None else monotonic() + timeout
        with self._condition:
            if self._status == PersistenceWriterStatus.FAILED:
                return False
            if self._status not in {
                PersistenceWriterStatus.RECOVERING,
                PersistenceWriterStatus.RUNNING,
                PersistenceWriterStatus.STOPPING,
            }:
                return self._pending_count == 0
            self._force_flush = True
            self._condition.notify()
            while self._pending_count:
                if self._status == PersistenceWriterStatus.FAILED:
                    return False
                remaining = None if deadline is None else deadline - monotonic()
                if remaining is not None and remaining <= 0:
                    return False
                self._condition.wait(remaining)
            return True

    def wait_until_ready(self, timeout: float | None = None) -> bool:
        deadline = None if timeout is None else monotonic() + timeout
        with self._condition:
            while self._status == PersistenceWriterStatus.RECOVERING:
                remaining = None if deadline is None else deadline - monotonic()
                if remaining is not None and remaining <= 0:
                    return False
                self._condition.wait(remaining)
            return self._status == PersistenceWriterStatus.RUNNING

    def stop(self, timeout: float | None = None) -> bool:
        with self._condition:
            if self._status == PersistenceWriterStatus.STOPPED:
                return True
            if self._status == PersistenceWriterStatus.FAILED:
                thread = self._thread
            else:
                self._status = PersistenceWriterStatus.STOPPING
                self._force_flush = True
                self._condition.notify()
                thread = self._thread
                snapshot = self._snapshot_unlocked()
                self._publish(snapshot)
        if thread is not None:
            thread.join(timeout)
        return thread is None or not thread.is_alive()

    def _run(self) -> None:
        inflight_events: tuple[object, ...] = ()
        try:
            if self._recovery:
                recovered = tuple(self._recovery)
                self._recovery.clear()
                for entry in recovered:
                    identity = self._catalog.identify([entry.event])[0]
                    if self._journal.path_for(identity) != entry.path:
                        raise JournalCorruptionError(
                            f"journal payload does not match bucket path: {entry.path.name}"
                        )
                    self._buffer(entry.event, identity, entry.path)
                self._flush_ready(force=True)
                with self._condition:
                    if self._status == PersistenceWriterStatus.RECOVERING:
                        self._status = PersistenceWriterStatus.RUNNING
                    self._condition.notify_all()
                    snapshot = self._snapshot_unlocked()
                self._publish(snapshot)
            while True:
                with self._condition:
                    if not self._ingress and not self._force_flush:
                        if self._status == PersistenceWriterStatus.STOPPING:
                            self._force_flush = True
                        else:
                            self._condition.wait(self._config.catalog_flush_poll_seconds)
                    events = tuple(self._ingress)
                    self._ingress.clear()
                    force_flush = self._force_flush
                    self._force_flush = False

                if events:
                    inflight_events = events
                    identities = self._catalog.identify(events)
                    entries = self._journal.append(tuple(zip(events, identities, strict=True)))
                    with self._condition:
                        self._journaled_count += len(entries)
                        snapshot = self._snapshot_unlocked()
                    self._publish(snapshot)
                    for entry, identity in zip(entries, identities, strict=True):
                        self._buffer(entry.event, identity, entry.path)
                    inflight_events = ()
                self._flush_ready(force=force_flush)

                with self._condition:
                    if (
                        self._status == PersistenceWriterStatus.STOPPING
                        and self._pending_count == 0
                    ):
                        self._status = PersistenceWriterStatus.STOPPED
                        self._thread = None
                        self._condition.notify_all()
                        snapshot = self._snapshot_unlocked()
                        break
            self._publish(snapshot)
        except Exception as exc:
            with self._condition:
                self._ingress.extendleft(reversed(inflight_events))
                self._status = PersistenceWriterStatus.FAILED
                self._last_error = f"{type(exc).__name__}: {exc}"
                self._thread = None
                self._condition.notify_all()
                snapshot = self._snapshot_unlocked()
            self._publish(snapshot)

    def _buffer(
        self,
        event: object,
        identity: PersistenceEventIdentity,
        journal_path: Path,
    ) -> None:
        init_ns = identity.init_ts_ns
        if init_ns is None:
            raise ValueError("persistence event requires nanosecond initialization time")
        interval_ns = self._config.persistence_batch_interval_seconds * 1_000_000_000
        bucket = init_ns // interval_ns
        key = (identity.source, identity.instrument_id, identity.event_kind.value, bucket)
        self._buckets.setdefault(key, []).append(_BufferedEvent(event, identity, journal_path))

    def _flush_ready(self, *, force: bool) -> None:
        interval_ns = self._config.persistence_batch_interval_seconds * 1_000_000_000
        now_ns = unix_ns_from_utc_datetime(self._clock())
        ready_keys = [
            key for key in self._buckets if force or ((key[3] + 1) * interval_ns <= now_ns)
        ]
        for key in sorted(ready_keys):
            buffered = self._buckets.pop(key)
            journal_paths = {item.journal_path for item in buffered}
            buffered.sort(key=lambda item: (item.identity.init_ts_ns, item.identity.dedupe_key))
            offset = 0
            while offset < len(buffered):
                chunk_end = min(offset + self._config.catalog_batch_size, len(buffered))
                if (
                    chunk_end < len(buffered)
                    and buffered[chunk_end - 1].identity.init_ts_ns
                    == buffered[chunk_end].identity.init_ts_ns
                ):
                    shared_init_ns = buffered[chunk_end].identity.init_ts_ns
                    group_start = chunk_end - 1
                    while (
                        group_start > offset
                        and buffered[group_start - 1].identity.init_ts_ns == shared_init_ns
                    ):
                        group_start -= 1
                    if group_start > offset:
                        chunk_end = group_start
                    else:
                        while (
                            chunk_end < len(buffered)
                            and buffered[chunk_end].identity.init_ts_ns == shared_init_ns
                        ):
                            chunk_end += 1
                chunk = buffered[offset:chunk_end]
                try:
                    result = self._coordinator.persist_closed_batch([item.event for item in chunk])
                except Exception:
                    self._buckets[key] = buffered[offset:]
                    raise
                with self._condition:
                    self._pending_count -= len(chunk)
                    self._persisted_count += result.persisted_count
                    self._duplicate_count += result.duplicate_count
                    if result.batch is not None and result.persisted_count:
                        self._committed_batch_count += 1
                    self._condition.notify_all()
                    snapshot = self._snapshot_unlocked()
                self._publish(snapshot)
                offset = chunk_end
            for path in journal_paths:
                self._journal.acknowledge(path)
            with self._condition:
                snapshot = self._snapshot_unlocked()
            self._publish(snapshot)

    @staticmethod
    def _invalid_submission(event: object) -> PersistenceSubmissionStatus | None:
        if not isinstance(event, TradeTick | QuoteTick | OneMinuteBar):
            return PersistenceSubmissionStatus.UNSUPPORTED
        if isinstance(event, OneMinuteBar) and not event.is_complete:
            return PersistenceSubmissionStatus.PROVISIONAL
        return None

    def _snapshot_unlocked(self) -> PersistenceWriterSnapshot:
        return PersistenceWriterSnapshot(
            status=self._status,
            pending_count=self._pending_count,
            accepted_count=self._accepted_count,
            journaled_count=self._journaled_count,
            recovered_count=self._recovered_count,
            persisted_count=self._persisted_count,
            duplicate_count=self._duplicate_count,
            committed_batch_count=self._committed_batch_count,
            rejected_full_count=self._rejected_full_count,
            rejected_invalid_count=self._rejected_invalid_count,
            journal_bytes=self._journal.total_bytes,
            last_error=self._last_error,
        )

    def _publish(self, snapshot: PersistenceWriterSnapshot) -> None:
        if self._on_health_change is not None:
            self._on_health_change(snapshot)
