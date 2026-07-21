from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from threading import Lock
from typing import Protocol

from markeitech.domain.market_data import OneMinuteBar
from markeitech.persistence.catalog import NautilusParquetTimeSeriesStore
from markeitech.persistence.config import PersistenceConfig
from markeitech.persistence.coordinator import IdempotentPersistenceCoordinator
from markeitech.persistence.feature_catalog import ParquetFeatureStore
from markeitech.persistence.feature_pipeline import (
    BoundedFeatureWriter,
    CommittedFeatureRevision,
    FeaturePersistenceCoordinator,
    FeatureWriterSnapshot,
    FeatureWriterStatus,
)
from markeitech.persistence.pipeline import (
    BoundedPersistenceWriter,
    PersistenceSubmissionStatus,
    PersistenceWriterSnapshot,
    PersistenceWriterStatus,
)
from markeitech.persistence.retention import (
    CatalogRetentionMaintenance,
    RetentionCalendar,
    RetentionReport,
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
        maintenance: CatalogRetentionMaintenance | None = None,
        feature_catalog: ParquetFeatureStore | None = None,
        feature_writer: BoundedFeatureWriter | None = None,
    ) -> None:
        self.config = config
        self.catalog = catalog
        self.metadata = metadata
        self.writer = writer
        self.maintenance = maintenance
        self.feature_catalog = feature_catalog
        self.feature_writer = feature_writer
        self.ingress = LivePersistenceIngress(writer)
        self.retention_report: RetentionReport | None = None
        self._status = PersistenceRuntimeStatus.CREATED
        self._lock = Lock()

    @classmethod
    def build(
        cls,
        config: PersistenceConfig,
        *,
        retention_calendar: RetentionCalendar | None = None,
        feature_commit_sink: Callable[[tuple[CommittedFeatureRevision, ...]], bool] | None = None,
        market_data_commit_sink: Callable[[tuple[object, ...]], bool] | None = None,
    ) -> PersistenceRuntime:
        if config.retention_maintenance_enabled and retention_calendar is None:
            raise ValueError("enabled retention maintenance requires a session calendar")
        catalog = NautilusParquetTimeSeriesStore(config)
        metadata = SQLiteMetadataStore(config)
        coordinator = IdempotentPersistenceCoordinator(config, catalog, metadata)
        writer = BoundedPersistenceWriter(
            config,
            coordinator,
            catalog,
            post_commit_sink=market_data_commit_sink,
        )
        feature_catalog = ParquetFeatureStore(config)
        feature_coordinator = FeaturePersistenceCoordinator(feature_catalog, metadata)
        feature_writer = BoundedFeatureWriter(
            feature_coordinator,
            queue_size=config.feature_writer_queue_size,
            batch_size=config.feature_batch_size,
            poll_seconds=config.feature_flush_poll_seconds,
            commit_sink=feature_commit_sink,
        )
        maintenance = (
            CatalogRetentionMaintenance(config, retention_calendar, metadata)
            if retention_calendar is not None
            else None
        )
        return cls(
            config,
            catalog,
            metadata,
            writer,
            maintenance,
            feature_catalog,
            feature_writer,
        )

    @property
    def status(self) -> PersistenceRuntimeStatus:
        with self._lock:
            return self._status

    @property
    def writer_snapshot(self) -> PersistenceWriterSnapshot:
        return self.writer.snapshot

    @property
    def feature_writer_snapshot(self) -> FeatureWriterSnapshot | None:
        return None if self.feature_writer is None else self.feature_writer.snapshot

    def start(self) -> None:
        with self._lock:
            if self._status != PersistenceRuntimeStatus.CREATED:
                raise RuntimeError("persistence runtime can only start once")
        try:
            if self.maintenance is not None:
                self.retention_report = self.maintenance.run(datetime.now(UTC))
            self.writer.start()
            ready = self.writer.wait_until_ready(self.config.runtime_startup_timeout_seconds)
            if not ready:
                snapshot = self.writer.snapshot
                if snapshot.status == PersistenceWriterStatus.FAILED:
                    detail = snapshot.last_error or "unknown writer failure"
                    raise RuntimeError(
                        f"persistence writer failed during startup recovery: {detail}"
                    )
                raise RuntimeError("persistence writer timed out during startup recovery")
            if self.feature_writer is not None:
                self.feature_writer.start()
        except Exception:
            with self._lock:
                self._status = PersistenceRuntimeStatus.FAILED
            stopped = self.writer.stop(self.config.runtime_shutdown_timeout_seconds)
            if self.feature_writer is not None:
                self.feature_writer.stop(self.config.runtime_shutdown_timeout_seconds)
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
            feature_stopped = self._stop_feature_writer()
            stopped = self.writer.stop(self.config.runtime_shutdown_timeout_seconds)
            if not stopped or not feature_stopped:
                with self._lock:
                    self._status = PersistenceRuntimeStatus.FAILED
                writer_snapshot = self.writer.snapshot
                feature_snapshot = self.feature_writer_snapshot
                self.metadata.close()
                raise RuntimeError(
                    "persistence writers did not stop cleanly within timeout: "
                    f"catalog={writer_snapshot.status.value} "
                    f"pending={writer_snapshot.pending_count} "
                    f"error={writer_snapshot.last_error or 'none'}; "
                    "feature="
                    + (
                        "disabled"
                        if feature_snapshot is None
                        else (
                            f"{feature_snapshot.status.value} "
                            f"pending={feature_snapshot.pending_count} "
                            f"error={feature_snapshot.last_error or 'none'}"
                        )
                    )
                )
        elif self.writer.snapshot.status not in {
            PersistenceWriterStatus.STOPPED,
            PersistenceWriterStatus.FAILED,
        }:
            self.writer.stop(self.config.runtime_shutdown_timeout_seconds)
        self.metadata.close()
        with self._lock:
            self._status = PersistenceRuntimeStatus.STOPPED

    def _stop_feature_writer(self) -> bool:
        if self.feature_writer is None:
            return True
        snapshot = self.feature_writer.snapshot
        if snapshot.status in {FeatureWriterStatus.STOPPED, FeatureWriterStatus.FAILED}:
            return snapshot.status == FeatureWriterStatus.STOPPED
        return self.feature_writer.stop(self.config.runtime_shutdown_timeout_seconds)
