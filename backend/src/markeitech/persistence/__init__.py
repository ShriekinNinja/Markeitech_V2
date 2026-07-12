"""Persistence contracts and storage boundaries."""

from markeitech.persistence.catalog import NautilusParquetTimeSeriesStore
from markeitech.persistence.catalog_data import CanonicalOneMinuteBarRecord
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
from markeitech.persistence.sqlite import SQLiteMetadataStore

__all__ = [
    "DataFidelity",
    "CanonicalOneMinuteBarRecord",
    "NotificationOutboxRecord",
    "NotificationOutboxStore",
    "OutboxStatus",
    "NautilusParquetTimeSeriesStore",
    "PersistenceConfig",
    "PersistenceEventIdentity",
    "PersistenceEventKind",
    "RecoveryMetadataStore",
    "RecoveryRecord",
    "RecoveryStatus",
    "SQLiteMetadataStore",
    "StreamCheckpoint",
    "TimeSeriesStore",
]
