from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from threading import Condition, Thread
from typing import Protocol

from markeitech.analytics.features import MarketContextFeatureSnapshot
from markeitech.domain.base import require_utc
from markeitech.persistence.feature_catalog import ParquetFeatureStore


@dataclass(frozen=True)
class CommittedFeatureRevision:
    feature: MarketContextFeatureSnapshot
    committed_ts: datetime
    commit_sequence: int

    def __post_init__(self) -> None:
        require_utc(self.committed_ts)
        if self.commit_sequence < 1:
            raise ValueError("feature commit sequence must be positive")


class FeatureCommitMetadata(Protocol):
    def committed_feature_revisions(
        self,
        features: tuple[MarketContextFeatureSnapshot, ...],
    ) -> tuple[CommittedFeatureRevision, ...]: ...

    def commit_feature_snapshots(
        self,
        features: tuple[MarketContextFeatureSnapshot, ...],
        *,
        committed_ts: datetime,
    ) -> tuple[CommittedFeatureRevision, ...]: ...


@dataclass(frozen=True)
class FeaturePersistenceResult:
    committed_count: int
    duplicate_count: int
    revisions: tuple[CommittedFeatureRevision, ...] = ()


class FeaturePersistenceCoordinator:
    """Commits feature payloads to Parquet before advancing SQLite metadata."""

    def __init__(
        self,
        catalog: ParquetFeatureStore,
        metadata: FeatureCommitMetadata,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._catalog = catalog
        self._metadata = metadata
        self._clock = clock

    def persist(
        self,
        features: Sequence[MarketContextFeatureSnapshot],
    ) -> FeaturePersistenceResult:
        values = tuple(features)
        if not values:
            return FeaturePersistenceResult(0, 0)
        unique: dict[str, MarketContextFeatureSnapshot] = {}
        for value in values:
            existing = unique.get(value.feature_id)
            if existing is not None and existing != value:
                raise ValueError("feature id conflicts within submitted batch")
            unique[value.feature_id] = value
        unique_values = tuple(unique.values())
        committed = self._metadata.committed_feature_revisions(unique_values)
        committed_ids = {item.feature.feature_id for item in committed}
        pending = tuple(value for value in unique_values if value.feature_id not in committed_ids)
        if pending:
            self._catalog.write(pending)
            self._metadata.commit_feature_snapshots(pending, committed_ts=self._clock())
        revisions = self._metadata.committed_feature_revisions(unique_values)
        if len(revisions) != len(unique_values):
            raise RuntimeError("feature metadata did not verify the complete committed batch")
        return FeaturePersistenceResult(
            committed_count=len(pending),
            duplicate_count=len(values) - len(pending),
            revisions=revisions,
        )


class FeatureSubmissionStatus(StrEnum):
    ACCEPTED = "accepted"
    QUEUE_FULL = "queue_full"
    NOT_RUNNING = "not_running"
    WRITER_FAILED = "writer_failed"


class FeatureWriterStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass(frozen=True)
class FeatureWriterSnapshot:
    status: FeatureWriterStatus
    pending_count: int
    accepted_count: int
    committed_count: int
    duplicate_count: int
    handed_off_count: int
    rejected_count: int
    last_error: str | None


class BoundedFeatureWriter:
    def __init__(
        self,
        coordinator: FeaturePersistenceCoordinator,
        *,
        queue_size: int,
        batch_size: int,
        poll_seconds: float,
        commit_sink: Callable[[tuple[CommittedFeatureRevision, ...]], bool] | None = None,
    ) -> None:
        if queue_size < 1 or batch_size < 1 or batch_size > queue_size:
            raise ValueError("feature writer requires valid bounded queue and batch sizes")
        if poll_seconds <= 0:
            raise ValueError("feature writer poll interval must be positive")
        self._coordinator = coordinator
        self._queue_size = queue_size
        self._batch_size = batch_size
        self._poll_seconds = poll_seconds
        self._commit_sink = commit_sink
        self._condition = Condition()
        self._queue: deque[MarketContextFeatureSnapshot] = deque()
        self._status = FeatureWriterStatus.CREATED
        self._pending_count = 0
        self._accepted_count = 0
        self._committed_count = 0
        self._duplicate_count = 0
        self._handed_off_count = 0
        self._rejected_count = 0
        self._last_error: str | None = None
        self._thread: Thread | None = None

    @property
    def snapshot(self) -> FeatureWriterSnapshot:
        with self._condition:
            return self._snapshot_unlocked()

    def set_commit_sink(
        self,
        sink: Callable[[tuple[CommittedFeatureRevision, ...]], bool],
    ) -> None:
        with self._condition:
            if self._status != FeatureWriterStatus.CREATED:
                raise RuntimeError("feature commit sink must be configured before start")
            if self._commit_sink is not None:
                raise RuntimeError("feature commit sink is already configured")
            self._commit_sink = sink

    def start(self) -> None:
        with self._condition:
            if self._status != FeatureWriterStatus.CREATED:
                raise RuntimeError("feature writer can only start once")
            self._status = FeatureWriterStatus.RUNNING
            self._thread = Thread(
                target=self._run,
                name="markeitech-feature-writer",
                daemon=True,
            )
            self._thread.start()

    def submit(self, feature: MarketContextFeatureSnapshot) -> FeatureSubmissionStatus:
        with self._condition:
            if self._status == FeatureWriterStatus.FAILED:
                self._rejected_count += 1
                return FeatureSubmissionStatus.WRITER_FAILED
            if self._status != FeatureWriterStatus.RUNNING:
                self._rejected_count += 1
                return FeatureSubmissionStatus.NOT_RUNNING
            if self._pending_count >= self._queue_size:
                self._rejected_count += 1
                return FeatureSubmissionStatus.QUEUE_FULL
            self._queue.append(feature)
            self._pending_count += 1
            self._accepted_count += 1
            self._condition.notify_all()
            return FeatureSubmissionStatus.ACCEPTED

    def flush(self, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        with self._condition:
            self._condition.notify_all()
            while self._pending_count:
                if self._status == FeatureWriterStatus.FAILED:
                    return False
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._condition.wait(remaining)
            return True

    def stop(self, timeout: float) -> bool:
        with self._condition:
            if self._status == FeatureWriterStatus.STOPPED:
                return True
            if self._status == FeatureWriterStatus.CREATED:
                self._status = FeatureWriterStatus.STOPPED
                return True
            if self._status != FeatureWriterStatus.FAILED:
                self._status = FeatureWriterStatus.STOPPING
            thread = self._thread
            self._condition.notify_all()
        if thread is not None:
            thread.join(timeout)
        return thread is None or not thread.is_alive()

    def _run(self) -> None:
        while True:
            with self._condition:
                while not self._queue and self._status == FeatureWriterStatus.RUNNING:
                    self._condition.wait(self._poll_seconds)
                if not self._queue and self._status == FeatureWriterStatus.STOPPING:
                    self._status = FeatureWriterStatus.STOPPED
                    self._condition.notify_all()
                    return
                batch = tuple(
                    self._queue.popleft() for _ in range(min(len(self._queue), self._batch_size))
                )
            try:
                result = self._coordinator.persist(batch)
            except Exception as exc:
                with self._condition:
                    self._queue.extendleft(reversed(batch))
                    self._status = FeatureWriterStatus.FAILED
                    self._last_error = f"{type(exc).__name__}: {exc}"
                    self._condition.notify_all()
                return
            with self._condition:
                self._committed_count += result.committed_count
                self._duplicate_count += result.duplicate_count
            try:
                if self._commit_sink is not None and not self._commit_sink(result.revisions):
                    raise RuntimeError("feature commit handoff rejected batch")
            except Exception as exc:
                with self._condition:
                    self._queue.extendleft(reversed(batch))
                    self._status = FeatureWriterStatus.FAILED
                    self._last_error = f"{type(exc).__name__}: {exc}"
                    self._condition.notify_all()
                return
            with self._condition:
                self._pending_count -= len(batch)
                if self._commit_sink is not None:
                    self._handed_off_count += len(result.revisions)
                self._condition.notify_all()

    def _snapshot_unlocked(self) -> FeatureWriterSnapshot:
        return FeatureWriterSnapshot(
            status=self._status,
            pending_count=self._pending_count,
            accepted_count=self._accepted_count,
            committed_count=self._committed_count,
            duplicate_count=self._duplicate_count,
            handed_off_count=self._handed_off_count,
            rejected_count=self._rejected_count,
            last_error=self._last_error,
        )
