from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from markeitech.persistence.contracts import (
    NotificationOutboxRecord,
    PersistenceEventIdentity,
    RecoveryRecord,
    StreamCheckpoint,
)


class TimeSeriesStore(Protocol):
    def write(self, events: Sequence[object]) -> tuple[PersistenceEventIdentity, ...]: ...


class RecoveryMetadataStore(Protocol):
    def save_checkpoint(self, checkpoint: StreamCheckpoint) -> None: ...

    def load_checkpoint(self, stream_key: str) -> StreamCheckpoint | None: ...

    def save_recovery(self, recovery: RecoveryRecord) -> None: ...

    def load_recovery(self, recovery_id: UUID) -> RecoveryRecord | None: ...

    def record_provider_empty_interval(
        self,
        *,
        instrument_id: str,
        source: str,
        open_ts: datetime,
        observed_ts: datetime,
    ) -> int: ...

    def load_confirmed_provider_empty_opens(
        self,
        *,
        instrument_id: str,
        source: str,
        start_ts: datetime,
        end_ts: datetime,
        minimum_attempts: int,
    ) -> tuple[datetime, ...]: ...


class NotificationOutboxStore(Protocol):
    def enqueue(self, record: NotificationOutboxRecord) -> bool: ...

    def lease_pending(
        self,
        *,
        lease_owner: str,
        now: datetime,
        limit: int,
    ) -> tuple[NotificationOutboxRecord, ...]: ...

    def mark_delivered(
        self,
        *,
        outbox_id: UUID,
        lease_owner: str,
        delivered_ts: datetime,
    ) -> NotificationOutboxRecord: ...

    def mark_failed(
        self,
        *,
        outbox_id: UUID,
        lease_owner: str,
        failed_ts: datetime,
        retry_ts: datetime,
        error: str,
    ) -> NotificationOutboxRecord: ...
