"""Persistence contracts and storage boundaries."""

from markeitech.persistence.config import PersistenceConfig
from markeitech.persistence.contracts import (
    DataFidelity,
    NotificationOutboxRecord,
    OutboxStatus,
    PersistenceEventIdentity,
    PersistenceEventKind,
    RecoveryRecord,
    RecoveryStatus,
    StreamCheckpoint,
)
from markeitech.persistence.ports import (
    NotificationOutboxStore,
    RecoveryMetadataStore,
    TimeSeriesStore,
)

__all__ = [
    "DataFidelity",
    "NotificationOutboxRecord",
    "NotificationOutboxStore",
    "OutboxStatus",
    "PersistenceConfig",
    "PersistenceEventIdentity",
    "PersistenceEventKind",
    "RecoveryMetadataStore",
    "RecoveryRecord",
    "RecoveryStatus",
    "StreamCheckpoint",
    "TimeSeriesStore",
]
