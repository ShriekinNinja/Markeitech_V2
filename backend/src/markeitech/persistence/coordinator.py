from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from markeitech.domain.base import utc_datetime_from_unix_ns
from markeitech.persistence.catalog import NautilusParquetTimeSeriesStore
from markeitech.persistence.config import PersistenceConfig
from markeitech.persistence.contracts import (
    PersistenceBatch,
    PersistenceBatchStatus,
    PersistenceEventIdentity,
    StreamCheckpoint,
    same_logical_event_identity,
)
from markeitech.persistence.sqlite import SQLiteMetadataStore


class PersistenceFailurePoint(StrEnum):
    AFTER_PREPARE = "after_prepare"
    AFTER_CATALOG_WRITE = "after_catalog_write"
    AFTER_CATALOG_ACK = "after_catalog_ack"
    AFTER_COMMIT = "after_commit"


@dataclass(frozen=True)
class PersistenceWriteResult:
    batch: PersistenceBatch | None
    persisted_count: int
    duplicate_count: int


class IdempotentPersistenceCoordinator:
    def __init__(
        self,
        config: PersistenceConfig,
        catalog: NautilusParquetTimeSeriesStore,
        metadata: SQLiteMetadataStore,
        *,
        clock: Callable[[], datetime] | None = None,
        failure_injector: Callable[[PersistenceFailurePoint], None] | None = None,
    ) -> None:
        self._config = config
        self._catalog = catalog
        self._metadata = metadata
        self._clock = clock or (lambda: datetime.now(UTC))
        self._failure_injector = failure_injector

    def persist_closed_batch(self, events: Sequence[object]) -> PersistenceWriteResult:
        if not events:
            return PersistenceWriteResult(batch=None, persisted_count=0, duplicate_count=0)
        if len(events) > self._config.catalog_batch_size:
            raise ValueError("persistence batch exceeds configured catalog batch size")

        paired = self._validated_pairs(events)
        unique = self._deduplicate_input(paired)
        committed_keys = self._metadata.committed_dedupe_keys(
            tuple(identity for _, identity in unique)
        )
        pending = tuple(pair for pair in unique if pair[1].dedupe_key not in committed_keys)
        duplicate_count = len(events) - len(pending)
        if not pending:
            return PersistenceWriteResult(
                batch=None,
                persisted_count=0,
                duplicate_count=duplicate_count,
            )

        self._require_one_closed_bucket(tuple(identity for _, identity in pending))
        pending = tuple(
            sorted(
                pending,
                key=lambda pair: (_init_ns(pair[1]), pair[1].dedupe_key),
            )
        )
        identities = tuple(identity for _, identity in pending)
        batch = self._build_batch(identities)
        existing = self._metadata.prepare_batch(batch)
        self._inject(PersistenceFailurePoint.AFTER_PREPARE)

        if existing.status == PersistenceBatchStatus.PREPARED:
            written = self._catalog.write([event for event, _ in pending])
            if written != identities:
                raise RuntimeError("catalog identities differ from prepared batch")
            self._inject(PersistenceFailurePoint.AFTER_CATALOG_WRITE)
            existing = self._metadata.mark_catalog_written(batch.batch_id, self._clock())
        self._inject(PersistenceFailurePoint.AFTER_CATALOG_ACK)

        if existing.status == PersistenceBatchStatus.COMMITTED:
            return PersistenceWriteResult(
                batch=existing,
                persisted_count=0,
                duplicate_count=len(events),
            )

        committed_ts = self._clock()
        checkpoint_identity = max(
            identities,
            key=lambda identity: (_event_ns(identity), identity.dedupe_key),
        )
        checkpoint = StreamCheckpoint(
            instrument_id=checkpoint_identity.instrument_id,
            event_kind=checkpoint_identity.event_kind,
            source=checkpoint_identity.source,
            last_event_ts=checkpoint_identity.event_ts,
            last_event_ts_ns=checkpoint_identity.event_ts_ns,
            last_dedupe_key=checkpoint_identity.dedupe_key,
            committed_ts=committed_ts,
        )
        committed = self._metadata.commit_batch(
            batch_id=batch.batch_id,
            identities=identities,
            checkpoint=checkpoint,
            committed_ts=committed_ts,
        )
        self._inject(PersistenceFailurePoint.AFTER_COMMIT)
        return PersistenceWriteResult(
            batch=committed,
            persisted_count=len(pending),
            duplicate_count=duplicate_count,
        )

    def _validated_pairs(
        self,
        events: Sequence[object],
    ) -> tuple[tuple[object, PersistenceEventIdentity], ...]:
        identities = self._catalog.identify(events)
        pairs = tuple(zip(events, identities, strict=True))
        first = identities[0]
        for identity in identities[1:]:
            if (
                identity.instrument_id,
                identity.event_kind,
                identity.source,
            ) != (first.instrument_id, first.event_kind, first.source):
                raise ValueError("persistence batch must contain exactly one stream")
        return pairs

    @staticmethod
    def _deduplicate_input(
        pairs: tuple[tuple[object, PersistenceEventIdentity], ...],
    ) -> tuple[tuple[object, PersistenceEventIdentity], ...]:
        unique: dict[str, tuple[object, PersistenceEventIdentity]] = {}
        for pair in pairs:
            identity = pair[1]
            existing = unique.get(identity.dedupe_key)
            if existing is not None and not same_logical_event_identity(existing[1], identity):
                raise ValueError("input dedupe key conflicts with a different event identity")
            if existing is None or _init_ns(identity) < _init_ns(existing[1]):
                unique[identity.dedupe_key] = pair
        return tuple(unique.values())

    def _require_one_closed_bucket(
        self,
        identities: tuple[PersistenceEventIdentity, ...],
    ) -> None:
        interval_ns = self._config.persistence_batch_interval_seconds * 1_000_000_000
        buckets = {_init_ns(identity) // interval_ns for identity in identities}
        if len(buckets) != 1:
            raise ValueError("persistence batch must fit one fixed initialization-time bucket")

    def _build_batch(
        self,
        identities: tuple[PersistenceEventIdentity, ...],
    ) -> PersistenceBatch:
        interval_ns = self._config.persistence_batch_interval_seconds * 1_000_000_000
        bucket_start_ns = (_init_ns(identities[0]) // interval_ns) * interval_ns
        bucket_end_ns = bucket_start_ns + interval_ns
        identity_hash = _hash_identities(identities)
        first = identities[0]
        batch_id = hashlib.sha256(
            (
                f"{first.source}|{first.instrument_id}|{first.event_kind.value}|"
                f"{bucket_start_ns}|{identity_hash}"
            ).encode()
        ).hexdigest()
        now = self._clock()
        return PersistenceBatch(
            batch_id=batch_id,
            instrument_id=first.instrument_id,
            event_kind=first.event_kind,
            source=first.source,
            bucket_start_ts=utc_datetime_from_unix_ns(bucket_start_ns),
            bucket_end_ts=utc_datetime_from_unix_ns(bucket_end_ns),
            expected_event_count=len(identities),
            identity_hash=identity_hash,
            created_ts=now,
            updated_ts=now,
        )

    def _inject(self, point: PersistenceFailurePoint) -> None:
        if self._failure_injector is not None:
            self._failure_injector(point)


def _init_ns(identity: PersistenceEventIdentity) -> int:
    if identity.init_ts_ns is None:
        raise ValueError("persistence identity requires nanosecond initialization time")
    return identity.init_ts_ns


def _event_ns(identity: PersistenceEventIdentity) -> int:
    if identity.event_ts_ns is None:
        raise ValueError("persistence identity requires nanosecond event time")
    return identity.event_ts_ns


def _hash_identities(identities: tuple[PersistenceEventIdentity, ...]) -> str:
    payload = [identity.model_dump(mode="json") for identity in identities]
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()
