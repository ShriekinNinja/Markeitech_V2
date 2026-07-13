from __future__ import annotations

from pathlib import Path

from pydantic import Field, model_validator

from markeitech.domain.base import VersionedDomainModel


class PersistenceConfig(VersionedDomainModel):
    catalog_path: Path = Path("data/catalog")
    metadata_path: Path = Path("data/runtime/markeitech.sqlite3")
    journal_path: Path = Path("data/runtime/ingress-journal")
    retention_maintenance_enabled: bool = False
    tick_retention_sessions: int = Field(default=5, ge=5)
    bar_retention_sessions: int = Field(default=250, ge=5)
    catalog_writer_queue_size: int = Field(default=10_000, ge=1)
    catalog_batch_size: int = Field(default=1_000, ge=1)
    persistence_batch_interval_seconds: int = Field(default=60, ge=1)
    catalog_flush_poll_seconds: float = Field(default=0.25, gt=0, le=5)
    journal_max_bytes: int = Field(default=512 * 1024 * 1024, ge=1)
    journal_max_record_bytes: int = Field(default=1024 * 1024, ge=1)
    journal_fsync: bool = True
    recovery_max_lookback_days: int = Field(default=30, ge=1)
    recovery_max_intervals_per_request: int = Field(default=1_000, ge=1)
    recovery_max_requests_per_plan: int = Field(default=64, ge=1)
    recovery_max_total_requests: int = Field(default=256, ge=1)
    recovery_provider_empty_confirmation_attempts: int = Field(default=2, ge=1)
    runtime_startup_timeout_seconds: float = Field(default=30, gt=0)
    runtime_shutdown_timeout_seconds: float = Field(default=30, gt=0)
    outbox_lease_seconds: int = Field(default=30, ge=1)
    outbox_max_attempts: int = Field(default=8, ge=1)
    sqlite_busy_timeout_ms: int = Field(default=5_000, ge=1)
    redis_enabled: bool = False

    @model_validator(mode="after")
    def _retention_and_batching_must_be_consistent(self) -> PersistenceConfig:
        if self.bar_retention_sessions < self.tick_retention_sessions:
            raise ValueError("bar retention cannot be shorter than tick retention")
        if self.catalog_batch_size > self.catalog_writer_queue_size:
            raise ValueError("catalog batch size cannot exceed writer queue size")
        return self
