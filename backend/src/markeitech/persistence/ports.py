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
