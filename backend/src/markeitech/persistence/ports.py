from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

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


class NotificationOutboxStore(Protocol):
    def enqueue(self, record: NotificationOutboxRecord) -> bool: ...

    def lease_pending(self, *, limit: int) -> tuple[NotificationOutboxRecord, ...]: ...

    def save(self, record: NotificationOutboxRecord) -> None: ...
