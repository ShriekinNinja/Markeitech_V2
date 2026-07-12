from __future__ import annotations

from pathlib import Path

from pydantic import Field, model_validator

from markeitech.domain.base import VersionedDomainModel


class PersistenceConfig(VersionedDomainModel):
    catalog_path: Path = Path("data/catalog")
    metadata_path: Path = Path("data/runtime/markeitech.sqlite3")
    tick_retention_sessions: int = Field(default=5, ge=5)
    bar_retention_sessions: int = Field(default=250, ge=5)
    catalog_writer_queue_size: int = Field(default=10_000, ge=1)
    catalog_batch_size: int = Field(default=1_000, ge=1)
    outbox_lease_seconds: int = Field(default=30, ge=1)
    outbox_max_attempts: int = Field(default=8, ge=1)
    redis_enabled: bool = False

    @model_validator(mode="after")
    def _retention_and_batching_must_be_consistent(self) -> PersistenceConfig:
        if self.bar_retention_sessions < self.tick_retention_sessions:
            raise ValueError("bar retention cannot be shorter than tick retention")
        if self.catalog_batch_size > self.catalog_writer_queue_size:
            raise ValueError("catalog batch size cannot exceed writer queue size")
        return self
