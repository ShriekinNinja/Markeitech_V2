"""Persistence contracts and storage boundaries."""

from markeitech.persistence.catalog import NautilusParquetTimeSeriesStore
from markeitech.persistence.catalog_data import CanonicalOneMinuteBarRecord
from markeitech.persistence.config import PersistenceConfig
from markeitech.persistence.contracts import (
    DataFidelity,
    NotificationOutboxRecord,
    OutboxStatus,
    PersistenceBatch,
    PersistenceBatchStatus,
    PersistenceEventIdentity,
    PersistenceEventKind,
    RecoveryRecord,
    RecoveryStatus,
    StreamCheckpoint,
)
from markeitech.persistence.coordinator import (
    IdempotentPersistenceCoordinator,
    PersistenceFailurePoint,
    PersistenceWriteResult,
)
from markeitech.persistence.journal import (
    DurableIngressJournal,
    JournalCapacityError,
    JournalCorruptionError,
    JournalEntry,
    JournalError,
)
from markeitech.persistence.pipeline import (
    BoundedPersistenceWriter,
    PersistenceSubmissionStatus,
    PersistenceWriterSnapshot,
    PersistenceWriterStatus,
)
from markeitech.persistence.ports import (
    NotificationOutboxStore,
    RecoveryMetadataStore,
    TimeSeriesStore,
)
from markeitech.persistence.sqlite import SQLiteMetadataStore

__all__ = [
    "DataFidelity",
    "BoundedPersistenceWriter",
    "DurableIngressJournal",
    "IdempotentPersistenceCoordinator",
    "JournalCapacityError",
    "JournalCorruptionError",
    "JournalEntry",
    "JournalError",
    "CanonicalOneMinuteBarRecord",
    "NotificationOutboxRecord",
    "NotificationOutboxStore",
    "OutboxStatus",
    "PersistenceBatch",
    "PersistenceBatchStatus",
    "NautilusParquetTimeSeriesStore",
    "PersistenceConfig",
    "PersistenceFailurePoint",
    "PersistenceEventIdentity",
    "PersistenceEventKind",
    "PersistenceWriteResult",
    "PersistenceSubmissionStatus",
    "PersistenceWriterSnapshot",
    "PersistenceWriterStatus",
    "RecoveryMetadataStore",
    "RecoveryRecord",
    "RecoveryStatus",
    "SQLiteMetadataStore",
    "StreamCheckpoint",
    "TimeSeriesStore",
]
