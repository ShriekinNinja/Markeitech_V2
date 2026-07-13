from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from threading import Lock
from typing import Protocol

from markeitech.domain.market_data import OneMinuteBar
from markeitech.persistence.catalog import NautilusParquetTimeSeriesStore
from markeitech.persistence.config import PersistenceConfig
from markeitech.persistence.coordinator import IdempotentPersistenceCoordinator
from markeitech.persistence.pipeline import (
    BoundedPersistenceWriter,
    PersistenceSubmissionStatus,
    PersistenceWriterSnapshot,
    PersistenceWriterStatus,
)
from markeitech.persistence.sqlite import SQLiteMetadataStore


class PersistenceIngressStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


class PersistenceSubmissionWriter(Protocol):
    def submit(self, event: object) -> PersistenceSubmissionStatus: ...


@dataclass(frozen=True)
class PersistenceIngressSnapshot:
    status: PersistenceIngressStatus
    accepted_native_count: int
    accepted_bar_count: int
    ignored_canonical_count: int
    rejected_count: int
    tick_gap_count: int
    bar_recovery_required_count: int
    reason_codes: tuple[str, ...]
    last_submission_status: PersistenceSubmissionStatus | None


class LivePersistenceIngress:
    """Non-blocking actor-facing adapter with explicit persistence damage state."""

    def __init__(self, writer: PersistenceSubmissionWriter) -> None:
        self._writer = writer
        self._lock = Lock()
        self._accepted_native_count = 0
        self._accepted_bar_count = 0
        self._ignored_canonical_count = 0
        self._rejected_count = 0
        self._tick_gap_count = 0
        self._bar_recovery_required_count = 0
        self._reason_codes: list[str] = []
        self._last_submission_status: PersistenceSubmissionStatus | None = None

    @property
    def snapshot(self) -> PersistenceIngressSnapshot:
        with self._lock:
            if self._last_submission_status in {
                PersistenceSubmissionStatus.WRITER_FAILED,
                PersistenceSubmissionStatus.NOT_RUNNING,
            }:
                status = PersistenceIngressStatus.FAILED
            elif self._reason_codes:
                status = PersistenceIngressStatus.DEGRADED
            else:
                status = PersistenceIngressStatus.HEALTHY
            return PersistenceIngressSnapshot(
                status=status,
                accepted_native_count=self._accepted_native_count,
                accepted_bar_count=self._accepted_bar_count,
                ignored_canonical_count=self._ignored_canonical_count,
                rejected_count=self._rejected_count,
                tick_gap_count=self._tick_gap_count,
                bar_recovery_required_count=self._bar_recovery_required_count,
                reason_codes=tuple(self._reason_codes),
                last_submission_status=self._last_submission_status,
            )

    def submit_native(self, event: object) -> PersistenceSubmissionStatus:
        result = self._writer.submit(event)
        with self._lock:
            self._last_submission_status = result
            if result == PersistenceSubmissionStatus.ACCEPTED:
                self._accepted_native_count += 1
            else:
                self._record_rejection(result, is_bar=False)
        return result

    def submit_canonical(self, event: object) -> PersistenceSubmissionStatus | None:
        if not isinstance(event, OneMinuteBar) or not event.is_complete:
            with self._lock:
                self._ignored_canonical_count += 1
            return None
        result = self._writer.submit(event)
        with self._lock:
            self._last_submission_status = result
            if result == PersistenceSubmissionStatus.ACCEPTED:
                self._accepted_bar_count += 1
            else:
                self._record_rejection(result, is_bar=True)
        return result

    def _record_rejection(
        self,
        result: PersistenceSubmissionStatus,
        *,
        is_bar: bool,
    ) -> None:
        self._rejected_count += 1
        if is_bar:
            self._bar_recovery_required_count += 1
        elif result in {
            PersistenceSubmissionStatus.QUEUE_FULL,
            PersistenceSubmissionStatus.WRITER_FAILED,
            PersistenceSubmissionStatus.NOT_RUNNING,
        }:
            self._tick_gap_count += 1
        reason = f"persistence_{result.value}"
        if reason not in self._reason_codes:
            self._reason_codes.append(reason)


class PersistenceRuntimeStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


class PersistenceRuntime:
    def __init__(
        self,
        config: PersistenceConfig,
        catalog: NautilusParquetTimeSeriesStore,
        metadata: SQLiteMetadataStore,
        writer: BoundedPersistenceWriter,
    ) -> None:
        self.config = config
        self.catalog = catalog
        self.metadata = metadata
        self.writer = writer
        self.ingress = LivePersistenceIngress(writer)
        self._status = PersistenceRuntimeStatus.CREATED
        self._lock = Lock()

    @classmethod
    def build(cls, config: PersistenceConfig) -> PersistenceRuntime:
        catalog = NautilusParquetTimeSeriesStore(config)
        metadata = SQLiteMetadataStore(config)
        coordinator = IdempotentPersistenceCoordinator(config, catalog, metadata)
        writer = BoundedPersistenceWriter(config, coordinator, catalog)
        return cls(config, catalog, metadata, writer)

    @property
    def status(self) -> PersistenceRuntimeStatus:
        with self._lock:
            return self._status

    @property
    def writer_snapshot(self) -> PersistenceWriterSnapshot:
        return self.writer.snapshot

    def start(self) -> None:
        with self._lock:
            if self._status != PersistenceRuntimeStatus.CREATED:
                raise RuntimeError("persistence runtime can only start once")
        try:
            self.writer.start()
            ready = self.writer.wait_until_ready(self.config.runtime_startup_timeout_seconds)
            if not ready:
                raise RuntimeError("persistence writer failed or timed out during startup recovery")
        except Exception:
            with self._lock:
                self._status = PersistenceRuntimeStatus.FAILED
            stopped = self.writer.stop(self.config.runtime_shutdown_timeout_seconds)
            if stopped:
                self.metadata.close()
            raise
        with self._lock:
            self._status = PersistenceRuntimeStatus.RUNNING

    def stop(self) -> None:
        with self._lock:
            if self._status == PersistenceRuntimeStatus.STOPPED:
                return
            if self._status == PersistenceRuntimeStatus.STOPPING:
                return
            status = self._status
            self._status = PersistenceRuntimeStatus.STOPPING
        if status == PersistenceRuntimeStatus.RUNNING:
            stopped = self.writer.stop(self.config.runtime_shutdown_timeout_seconds)
            if not stopped:
                with self._lock:
                    self._status = PersistenceRuntimeStatus.FAILED
                raise RuntimeError("persistence writer did not stop within timeout")
        elif self.writer.snapshot.status not in {
            PersistenceWriterStatus.STOPPED,
            PersistenceWriterStatus.FAILED,
        }:
            self.writer.stop(self.config.runtime_shutdown_timeout_seconds)
        self.metadata.close()
        with self._lock:
            self._status = PersistenceRuntimeStatus.STOPPED
