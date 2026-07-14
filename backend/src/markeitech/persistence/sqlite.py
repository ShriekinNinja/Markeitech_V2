from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import UUID

from markeitech.analytics.features import MarketContextFeatureSnapshot
from markeitech.domain.base import unix_ns_from_utc_datetime, utc_datetime_from_unix_ns
from markeitech.domain.state import GapState, ReadinessState
from markeitech.persistence.config import PersistenceConfig
from markeitech.persistence.contracts import (
    NotificationOutboxRecord,
    OutboxStatus,
    PersistenceBatch,
    PersistenceBatchStatus,
    PersistenceEventIdentity,
    PersistenceEventKind,
    RecoveryRecord,
    RecoveryStatus,
    RetentionReport,
    RetentionStatus,
    SignalPersistenceOutcome,
    SQLiteCompactionReport,
    SQLiteCompactionStatus,
    StreamCheckpoint,
    dedupe_key_fingerprint,
    logical_event_identity_fingerprint,
    same_logical_event_identity,
)
from markeitech.signals import SignalSnapshot, SignalStatus, SignalTransitionEvent

LATEST_SCHEMA_VERSION = 8

MIGRATIONS: tuple[tuple[int, str], ...] = (
    (
        1,
        """
        CREATE TABLE schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_ts_ns INTEGER NOT NULL
        );
        CREATE TABLE stream_checkpoints (
            stream_key TEXT PRIMARY KEY,
            schema_version TEXT NOT NULL,
            instrument_id TEXT NOT NULL,
            event_kind TEXT NOT NULL,
            source TEXT NOT NULL,
            last_event_ts_ns INTEGER NOT NULL,
            last_dedupe_key TEXT NOT NULL,
            committed_ts_ns INTEGER NOT NULL
        );
        CREATE TABLE recovery_records (
            recovery_id TEXT PRIMARY KEY,
            schema_version TEXT NOT NULL,
            instrument_id TEXT NOT NULL,
            event_kind TEXT NOT NULL,
            source TEXT NOT NULL,
            status TEXT NOT NULL,
            requested_start_ts_ns INTEGER NOT NULL,
            requested_end_ts_ns INTEGER NOT NULL,
            missing_intervals INTEGER NOT NULL,
            reason_codes_json TEXT NOT NULL,
            started_ts_ns INTEGER NOT NULL,
            updated_ts_ns INTEGER NOT NULL,
            completed_ts_ns INTEGER
        );
        CREATE TABLE readiness_states (
            instrument_id TEXT PRIMARY KEY,
            payload_json TEXT NOT NULL,
            updated_ts_ns INTEGER NOT NULL
        );
        CREATE TABLE gap_states (
            instrument_id TEXT PRIMARY KEY,
            payload_json TEXT NOT NULL,
            updated_ts_ns INTEGER NOT NULL
        );
        CREATE TABLE notification_outbox (
            outbox_id TEXT PRIMARY KEY,
            schema_version TEXT NOT NULL,
            topic TEXT NOT NULL,
            destination_key TEXT NOT NULL,
            aggregate_key TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_schema_version TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            dedupe_key TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            attempt_count INTEGER NOT NULL,
            available_ts_ns INTEGER NOT NULL,
            created_ts_ns INTEGER NOT NULL,
            updated_ts_ns INTEGER NOT NULL,
            lease_owner TEXT,
            lease_expires_ts_ns INTEGER,
            delivered_ts_ns INTEGER,
            last_error TEXT
        );
        CREATE INDEX outbox_claim_idx
            ON notification_outbox(status, available_ts_ns, lease_expires_ts_ns, created_ts_ns);
        """,
    ),
    (
        2,
        """
        CREATE TABLE persistence_batches (
            batch_id TEXT PRIMARY KEY,
            schema_version TEXT NOT NULL,
            instrument_id TEXT NOT NULL,
            event_kind TEXT NOT NULL,
            source TEXT NOT NULL,
            bucket_start_ts_ns INTEGER NOT NULL,
            bucket_end_ts_ns INTEGER NOT NULL,
            expected_event_count INTEGER NOT NULL,
            identity_hash TEXT NOT NULL,
            status TEXT NOT NULL,
            created_ts_ns INTEGER NOT NULL,
            updated_ts_ns INTEGER NOT NULL,
            catalog_written_ts_ns INTEGER,
            committed_ts_ns INTEGER,
            last_error TEXT
        );
        CREATE INDEX persistence_batches_status_idx
            ON persistence_batches(status, bucket_start_ts_ns);
        CREATE TABLE persisted_event_identities (
            dedupe_key TEXT PRIMARY KEY,
            batch_id TEXT NOT NULL,
            identity_json TEXT NOT NULL,
            committed_ts_ns INTEGER NOT NULL,
            FOREIGN KEY(batch_id) REFERENCES persistence_batches(batch_id)
        );
        CREATE INDEX persisted_event_batch_idx
            ON persisted_event_identities(batch_id);
        """,
    ),
    (
        3,
        """
        CREATE TABLE provider_empty_intervals (
            instrument_id TEXT NOT NULL,
            source TEXT NOT NULL,
            open_ts_ns INTEGER NOT NULL,
            attempts INTEGER NOT NULL,
            first_observed_ts_ns INTEGER NOT NULL,
            last_observed_ts_ns INTEGER NOT NULL,
            PRIMARY KEY(instrument_id, source, open_ts_ns)
        );
        CREATE INDEX provider_empty_range_idx
            ON provider_empty_intervals(instrument_id, source, open_ts_ns);
        """,
    ),
    (
        4,
        """
        CREATE TABLE compact_persisted_event_identities (
            dedupe_hash BLOB PRIMARY KEY,
            identity_hash BLOB NOT NULL,
            batch_id TEXT NOT NULL,
            instrument_id TEXT NOT NULL,
            event_kind TEXT NOT NULL,
            source TEXT NOT NULL,
            event_ts_ns INTEGER NOT NULL,
            committed_ts_ns INTEGER NOT NULL,
            FOREIGN KEY(batch_id) REFERENCES persistence_batches(batch_id)
        );
        INSERT INTO compact_persisted_event_identities
        SELECT sha256_blob(dedupe_key), logical_identity_hash(identity_json), batch_id,
               json_extract(identity_json, '$.instrument_id'),
               json_extract(identity_json, '$.event_kind'),
               json_extract(identity_json, '$.source'),
               json_extract(identity_json, '$.event_ts_ns'),
               committed_ts_ns
        FROM persisted_event_identities;
        DROP TABLE persisted_event_identities;
        ALTER TABLE compact_persisted_event_identities RENAME TO persisted_event_identities;
        CREATE INDEX persisted_event_batch_idx
            ON persisted_event_identities(batch_id);
        CREATE INDEX persisted_event_retention_idx
            ON persisted_event_identities(event_kind, instrument_id, source, event_ts_ns);
        """,
    ),
    (
        5,
        """
        CREATE TABLE retention_maintenance_runs (
            run_id TEXT PRIMARY KEY,
            schema_version TEXT NOT NULL,
            maintenance_ts_ns INTEGER NOT NULL,
            status TEXT NOT NULL,
            inspected_file_count INTEGER NOT NULL,
            catalog_bytes_before INTEGER NOT NULL,
            catalog_bytes_after INTEGER NOT NULL,
            deleted_file_count INTEGER NOT NULL,
            deleted_bytes INTEGER NOT NULL,
            pruned_identity_count INTEGER NOT NULL,
            pruned_batch_count INTEGER NOT NULL,
            unmanaged_instruments_json TEXT NOT NULL,
            reason_codes_json TEXT NOT NULL,
            error TEXT
        );
        CREATE INDEX retention_maintenance_time_idx
            ON retention_maintenance_runs(maintenance_ts_ns DESC);
        CREATE TABLE metadata_compaction_runs (
            run_id TEXT PRIMARY KEY,
            schema_version TEXT NOT NULL,
            maintenance_ts_ns INTEGER NOT NULL,
            status TEXT NOT NULL,
            database_path TEXT NOT NULL,
            page_size_bytes INTEGER NOT NULL,
            page_count_before INTEGER NOT NULL,
            free_page_count_before INTEGER NOT NULL,
            page_count_after INTEGER NOT NULL,
            free_page_count_after INTEGER NOT NULL,
            reclaimed_bytes INTEGER NOT NULL
        );
        CREATE INDEX metadata_compaction_time_idx
            ON metadata_compaction_runs(maintenance_ts_ns DESC);
        """,
    ),
    (
        6,
        """
        CREATE TABLE feature_snapshot_commits (
            feature_id BLOB PRIMARY KEY,
            content_hash BLOB NOT NULL,
            instrument_id TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            as_of_ts_ns INTEGER NOT NULL,
            feature_set TEXT NOT NULL,
            calculation_version TEXT NOT NULL,
            configuration_hash BLOB NOT NULL,
            committed_ts_ns INTEGER NOT NULL
        );
        CREATE INDEX feature_snapshot_lookup_idx
            ON feature_snapshot_commits(instrument_id, timeframe, as_of_ts_ns DESC);
        """,
    ),
    (
        7,
        """
        CREATE TABLE signal_snapshots (
            signal_id BLOB PRIMARY KEY,
            initial_content_hash BLOB NOT NULL,
            content_hash BLOB NOT NULL,
            instrument_id TEXT NOT NULL,
            family TEXT NOT NULL,
            direction TEXT NOT NULL,
            status TEXT NOT NULL,
            updated_ts_ns INTEGER NOT NULL,
            snapshot_json TEXT NOT NULL
        );
        CREATE INDEX signal_snapshot_lookup_idx
            ON signal_snapshots(instrument_id, status, updated_ts_ns DESC);
        CREATE TABLE signal_transitions (
            transition_id BLOB PRIMARY KEY,
            signal_id BLOB NOT NULL,
            sequence_no INTEGER NOT NULL,
            occurred_ts_ns INTEGER NOT NULL,
            from_status TEXT NOT NULL,
            to_status TEXT NOT NULL,
            event_json TEXT NOT NULL,
            notification_outbox_id TEXT,
            FOREIGN KEY(signal_id) REFERENCES signal_snapshots(signal_id),
            FOREIGN KEY(notification_outbox_id) REFERENCES notification_outbox(outbox_id)
        );
        CREATE UNIQUE INDEX signal_transition_sequence_idx
            ON signal_transitions(signal_id, sequence_no);
        """,
    ),
    (
        8,
        """
        ALTER TABLE signal_snapshots
            ADD COLUMN definition_id TEXT NOT NULL DEFAULT 'intraday_context';
        DROP INDEX signal_snapshot_lookup_idx;
        CREATE INDEX signal_snapshot_lookup_idx
            ON signal_snapshots(instrument_id, definition_id, status, updated_ts_ns DESC);
        """,
    ),
)


class SQLiteMetadataStore:
    def __init__(self, config: PersistenceConfig) -> None:
        self._config = config
        self._path = Path(config.metadata_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(
            self._path,
            timeout=config.sqlite_busy_timeout_ms / 1_000,
            isolation_level=None,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._lock = Lock()
        try:
            self._configure()
            self._migrate()
        except BaseException:
            self._connection.close()
            raise

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __enter__(self) -> SQLiteMetadataStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @property
    def schema_version(self) -> int:
        row = self._connection.execute("PRAGMA user_version").fetchone()
        return int(row[0])

    def save_checkpoint(self, checkpoint: StreamCheckpoint) -> None:
        with self._transaction() as connection:
            self._upsert_checkpoint(connection, checkpoint, reject_regression=True)

    def load_checkpoint(self, stream_key: str) -> StreamCheckpoint | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM stream_checkpoints WHERE stream_key = ?",
                (stream_key,),
            ).fetchone()
        if row is None:
            return None
        return StreamCheckpoint(
            schema_version=row["schema_version"],
            instrument_id=row["instrument_id"],
            event_kind=PersistenceEventKind(row["event_kind"]),
            source=row["source"],
            last_event_ts=utc_datetime_from_unix_ns(row["last_event_ts_ns"]),
            last_event_ts_ns=row["last_event_ts_ns"],
            last_dedupe_key=row["last_dedupe_key"],
            committed_ts=utc_datetime_from_unix_ns(row["committed_ts_ns"]),
        )

    def committed_feature_ids(
        self,
        features: tuple[MarketContextFeatureSnapshot, ...],
    ) -> frozenset[str]:
        if not features:
            return frozenset()
        by_id: dict[bytes, MarketContextFeatureSnapshot] = {}
        for feature in features:
            feature_id = bytes.fromhex(feature.feature_id)
            existing = by_id.get(feature_id)
            if existing is not None and existing != feature:
                raise ValueError("feature id conflicts within metadata lookup")
            by_id[feature_id] = feature
        placeholders = ",".join("?" for _ in by_id)
        rows = self._connection.execute(
            f"""
            SELECT feature_id, content_hash FROM feature_snapshot_commits
            WHERE feature_id IN ({placeholders})
            """,
            tuple(by_id),
        ).fetchall()
        committed: set[str] = set()
        for row in rows:
            feature_id = bytes(row["feature_id"])
            feature = by_id[feature_id]
            if bytes(row["content_hash"]) != bytes.fromhex(feature.content_hash):
                raise ValueError("feature id conflicts with different committed content")
            committed.add(feature.feature_id)
        return frozenset(committed)

    def commit_feature_snapshots(
        self,
        features: tuple[MarketContextFeatureSnapshot, ...],
        *,
        committed_ts: datetime,
    ) -> None:
        committed_ts_ns = unix_ns_from_utc_datetime(committed_ts)
        with self._transaction() as connection:
            for feature in features:
                values = (
                    bytes.fromhex(feature.feature_id),
                    bytes.fromhex(feature.content_hash),
                    feature.snapshot.instrument_id,
                    feature.snapshot.timeframe.value,
                    unix_ns_from_utc_datetime(feature.snapshot.as_of),
                    feature.feature_set,
                    feature.calculation_version,
                    bytes.fromhex(feature.configuration_hash),
                    committed_ts_ns,
                )
                cursor = connection.execute(
                    """
                    INSERT INTO feature_snapshot_commits VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(feature_id) DO NOTHING
                    """,
                    values,
                )
                if cursor.rowcount == 0:
                    row = connection.execute(
                        """
                        SELECT content_hash FROM feature_snapshot_commits
                        WHERE feature_id = ?
                        """,
                        (values[0],),
                    ).fetchone()
                    if bytes(row["content_hash"]) != values[1]:
                        raise ValueError("feature id conflicts with different committed content")

    def save_signal_candidate(self, signal: SignalSnapshot) -> SignalPersistenceOutcome:
        if signal.status != SignalStatus.CANDIDATE:
            raise ValueError("initial signal snapshot must have candidate status")
        with self._transaction() as connection:
            return _save_signal_candidate(connection, signal)

    def save_signal_candidate_and_transition(
        self,
        candidate: SignalSnapshot,
        event: SignalTransitionEvent,
        *,
        notification: NotificationOutboxRecord | None = None,
    ) -> SignalPersistenceOutcome:
        if candidate.status != SignalStatus.CANDIDATE:
            raise ValueError("initial signal snapshot must have candidate status")
        if (
            event.signal_id != candidate.signal_id
            or event.from_status != SignalStatus.CANDIDATE
            or event.previous_content_hash != candidate.content_hash
        ):
            raise ValueError("initial signal transition does not match candidate")
        _validate_signal_notification(event, notification)
        with self._transaction() as connection:
            candidate_outcome = _save_signal_candidate(connection, candidate)
            transition_outcome = _apply_signal_transition(connection, event, notification)
            if (
                candidate_outcome == SignalPersistenceOutcome.DUPLICATE
                and transition_outcome == SignalPersistenceOutcome.DUPLICATE
            ):
                return SignalPersistenceOutcome.DUPLICATE
            return SignalPersistenceOutcome.TRANSITIONED

    def replace_signal_with_armed_candidate(
        self,
        ended_event: SignalTransitionEvent,
        candidate: SignalSnapshot,
        armed_event: SignalTransitionEvent,
    ) -> SignalPersistenceOutcome:
        if ended_event.to_status not in {SignalStatus.INVALIDATED, SignalStatus.EXPIRED}:
            raise ValueError("replaced signal must transition to a terminal status")
        if candidate.status != SignalStatus.CANDIDATE:
            raise ValueError("replacement signal must begin as candidate")
        if (
            armed_event.signal_id != candidate.signal_id
            or armed_event.from_status != SignalStatus.CANDIDATE
            or armed_event.to_status != SignalStatus.ARMED
            or armed_event.previous_content_hash != candidate.content_hash
        ):
            raise ValueError("replacement Armed transition does not match candidate")
        if ended_event.signal_id == candidate.signal_id:
            raise ValueError("replacement signal must have distinct identity")
        with self._transaction() as connection:
            ended_outcome = _apply_signal_transition(connection, ended_event, None)
            candidate_outcome = _save_signal_candidate(connection, candidate)
            armed_outcome = _apply_signal_transition(connection, armed_event, None)
            if all(
                outcome == SignalPersistenceOutcome.DUPLICATE
                for outcome in (ended_outcome, candidate_outcome, armed_outcome)
            ):
                return SignalPersistenceOutcome.DUPLICATE
            return SignalPersistenceOutcome.TRANSITIONED

    def apply_signal_transition(
        self,
        event: SignalTransitionEvent,
        *,
        notification: NotificationOutboxRecord | None = None,
    ) -> SignalPersistenceOutcome:
        _validate_signal_notification(event, notification)
        with self._transaction() as connection:
            return _apply_signal_transition(connection, event, notification)

    def load_signal(self, signal_id: str) -> SignalSnapshot | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM signal_snapshots WHERE signal_id=?",
                (bytes.fromhex(signal_id),),
            ).fetchone()
            if row is None:
                return None
            current, _ = _verified_signal_history(self._connection, row)
            return current

    def load_signals(
        self,
        *,
        instrument_id: str | None = None,
        definition_id: str | None = None,
        status: SignalStatus | None = None,
    ) -> tuple[SignalSnapshot, ...]:
        clauses: list[str] = []
        values: list[str] = []
        if instrument_id is not None:
            clauses.append("instrument_id=?")
            values.append(instrument_id)
        if definition_id is not None:
            clauses.append("definition_id=?")
            values.append(definition_id)
        if status is not None:
            clauses.append("status=?")
            values.append(status.value)
        where = "" if not clauses else f" WHERE {' AND '.join(clauses)}"
        with self._lock:
            rows = self._connection.execute(
                f"SELECT * FROM signal_snapshots{where} ORDER BY updated_ts_ns, signal_id",
                tuple(values),
            ).fetchall()
            return tuple(_verified_signal_history(self._connection, row)[0] for row in rows)

    def load_signal_transitions(self, signal_id: str) -> tuple[SignalTransitionEvent, ...]:
        with self._lock:
            snapshot_row = self._connection.execute(
                "SELECT * FROM signal_snapshots WHERE signal_id=?",
                (bytes.fromhex(signal_id),),
            ).fetchone()
            if snapshot_row is None:
                return ()
            _, events = _verified_signal_history(self._connection, snapshot_row)
            return events

    def save_recovery(self, recovery: RecoveryRecord) -> None:
        with self._transaction() as connection:
            existing = connection.execute(
                "SELECT status, updated_ts_ns FROM recovery_records WHERE recovery_id=?",
                (str(recovery.recovery_id),),
            ).fetchone()
            if existing is not None:
                _require_recovery_transition(
                    RecoveryStatus(existing["status"]),
                    existing["updated_ts_ns"],
                    recovery,
                )
            cursor = connection.execute(
                """
                INSERT INTO recovery_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(recovery_id) DO UPDATE SET
                    status=excluded.status,
                    missing_intervals=excluded.missing_intervals,
                    reason_codes_json=excluded.reason_codes_json,
                    updated_ts_ns=excluded.updated_ts_ns,
                    completed_ts_ns=excluded.completed_ts_ns
                WHERE excluded.updated_ts_ns >= recovery_records.updated_ts_ns
                """,
                (
                    str(recovery.recovery_id),
                    recovery.schema_version,
                    recovery.instrument_id,
                    recovery.event_kind.value,
                    recovery.source,
                    recovery.status.value,
                    unix_ns_from_utc_datetime(recovery.requested_start_ts),
                    unix_ns_from_utc_datetime(recovery.requested_end_ts),
                    recovery.missing_intervals,
                    _json_dump(recovery.reason_codes),
                    unix_ns_from_utc_datetime(recovery.started_ts),
                    unix_ns_from_utc_datetime(recovery.updated_ts),
                    _optional_ns(recovery.completed_ts),
                ),
            )
            if cursor.rowcount != 1:
                raise ValueError("recovery update cannot move state backward")

    def load_recovery(self, recovery_id: UUID) -> RecoveryRecord | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM recovery_records WHERE recovery_id = ?",
                (str(recovery_id),),
            ).fetchone()
        return None if row is None else _row_to_recovery(row)

    def record_provider_empty_interval(
        self,
        *,
        instrument_id: str,
        source: str,
        open_ts: datetime,
        observed_ts: datetime,
    ) -> int:
        open_ns = unix_ns_from_utc_datetime(open_ts)
        observed_ns = unix_ns_from_utc_datetime(observed_ts)
        with self._transaction() as connection:
            connection.execute(
                """
                INSERT INTO provider_empty_intervals VALUES (?, ?, ?, 1, ?, ?)
                ON CONFLICT(instrument_id, source, open_ts_ns) DO UPDATE SET
                    attempts=provider_empty_intervals.attempts + 1,
                    last_observed_ts_ns=excluded.last_observed_ts_ns
                """,
                (instrument_id, source, open_ns, observed_ns, observed_ns),
            )
            row = connection.execute(
                """
                SELECT attempts FROM provider_empty_intervals
                WHERE instrument_id=? AND source=? AND open_ts_ns=?
                """,
                (instrument_id, source, open_ns),
            ).fetchone()
        if row is None:
            raise RuntimeError("provider-empty interval write did not return a row")
        return int(row["attempts"])

    def load_confirmed_provider_empty_opens(
        self,
        *,
        instrument_id: str,
        source: str,
        start_ts: datetime,
        end_ts: datetime,
        minimum_attempts: int,
    ) -> tuple[datetime, ...]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT open_ts_ns FROM provider_empty_intervals
                WHERE instrument_id=? AND source=?
                  AND open_ts_ns>=? AND open_ts_ns<? AND attempts>=?
                ORDER BY open_ts_ns
                """,
                (
                    instrument_id,
                    source,
                    unix_ns_from_utc_datetime(start_ts),
                    unix_ns_from_utc_datetime(end_ts),
                    minimum_attempts,
                ),
            ).fetchall()
        return tuple(utc_datetime_from_unix_ns(row["open_ts_ns"]) for row in rows)

    def save_readiness(self, state: ReadinessState) -> None:
        self._save_state("readiness_states", state.instrument_id, state, state.updated_ts)

    def load_readiness(self, instrument_id: str) -> ReadinessState | None:
        payload = self._load_state("readiness_states", instrument_id)
        return None if payload is None else ReadinessState.model_validate_json(payload)

    def save_gap(self, state: GapState) -> None:
        self._save_state("gap_states", state.instrument_id, state, state.updated_ts)

    def load_gap(self, instrument_id: str) -> GapState | None:
        payload = self._load_state("gap_states", instrument_id)
        return None if payload is None else GapState.model_validate_json(payload)

    def enqueue(self, record: NotificationOutboxRecord) -> bool:
        with self._transaction() as connection:
            return _enqueue_outbox(connection, record)

    def lease_pending(
        self,
        *,
        lease_owner: str,
        now: datetime,
        limit: int,
    ) -> tuple[NotificationOutboxRecord, ...]:
        if not lease_owner:
            raise ValueError("lease_owner must not be empty")
        if limit < 1:
            raise ValueError("lease limit must be positive")
        now_ns = unix_ns_from_utc_datetime(now)
        expires_ns = unix_ns_from_utc_datetime(
            now + timedelta(seconds=self._config.outbox_lease_seconds)
        )
        with self._transaction() as connection:
            rows = connection.execute(
                """
                SELECT outbox_id FROM notification_outbox
                WHERE attempt_count < ?
                  AND (
                    (status IN ('pending', 'failed') AND available_ts_ns <= ?)
                    OR (status = 'leased' AND lease_expires_ts_ns <= ?)
                  )
                ORDER BY created_ts_ns, outbox_id
                LIMIT ?
                """,
                (self._config.outbox_max_attempts, now_ns, now_ns, limit),
            ).fetchall()
            ids = [row["outbox_id"] for row in rows]
            if not ids:
                return ()
            placeholders = ",".join("?" for _ in ids)
            connection.execute(
                f"""
                UPDATE notification_outbox
                SET status = 'leased', attempt_count = attempt_count + 1,
                    updated_ts_ns = ?, lease_owner = ?, lease_expires_ts_ns = ?,
                    delivered_ts_ns = NULL
                WHERE outbox_id IN ({placeholders})
                """,
                (now_ns, lease_owner, expires_ns, *ids),
            )
            leased = connection.execute(
                f"SELECT * FROM notification_outbox WHERE outbox_id IN ({placeholders})",
                ids,
            ).fetchall()
            by_id = {row["outbox_id"]: _row_to_outbox(row) for row in leased}
            return tuple(by_id[outbox_id] for outbox_id in ids)

    def mark_delivered(
        self,
        *,
        outbox_id: UUID,
        lease_owner: str,
        delivered_ts: datetime,
    ) -> NotificationOutboxRecord:
        delivered_ns = unix_ns_from_utc_datetime(delivered_ts)
        with self._transaction() as connection:
            cursor = connection.execute(
                """
                UPDATE notification_outbox
                SET status='delivered', updated_ts_ns=?, delivered_ts_ns=?,
                    lease_owner=NULL, lease_expires_ts_ns=NULL, last_error=NULL
                WHERE outbox_id=? AND status='leased' AND lease_owner=?
                """,
                (delivered_ns, delivered_ns, str(outbox_id), lease_owner),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("outbox delivery requires the active lease owner")
            row = connection.execute(
                "SELECT * FROM notification_outbox WHERE outbox_id=?",
                (str(outbox_id),),
            ).fetchone()
            return _row_to_outbox(row)

    def mark_failed(
        self,
        *,
        outbox_id: UUID,
        lease_owner: str,
        failed_ts: datetime,
        retry_ts: datetime,
        error: str,
    ) -> NotificationOutboxRecord:
        if not error:
            raise ValueError("outbox failure error must not be empty")
        failed_ns = unix_ns_from_utc_datetime(failed_ts)
        retry_ns = unix_ns_from_utc_datetime(retry_ts)
        if retry_ns < failed_ns:
            raise ValueError("outbox retry cannot precede failure")
        with self._transaction() as connection:
            cursor = connection.execute(
                """
                UPDATE notification_outbox
                SET status='failed', updated_ts_ns=?, available_ts_ns=?,
                    lease_owner=NULL, lease_expires_ts_ns=NULL, last_error=?
                WHERE outbox_id=? AND status='leased' AND lease_owner=?
                """,
                (failed_ns, retry_ns, error, str(outbox_id), lease_owner),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("outbox failure requires the active lease owner")
            row = connection.execute(
                "SELECT * FROM notification_outbox WHERE outbox_id=?",
                (str(outbox_id),),
            ).fetchone()
            return _row_to_outbox(row)

    def load_outbox(self, outbox_id: UUID) -> NotificationOutboxRecord | None:
        row = self._connection.execute(
            "SELECT * FROM notification_outbox WHERE outbox_id = ?",
            (str(outbox_id),),
        ).fetchone()
        return None if row is None else _row_to_outbox(row)

    def prepare_batch(self, batch: PersistenceBatch) -> PersistenceBatch:
        if batch.status != PersistenceBatchStatus.PREPARED:
            raise ValueError("new persistence batch must be prepared")
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT * FROM persistence_batches WHERE batch_id=?",
                (batch.batch_id,),
            ).fetchone()
            if row is not None:
                existing = _row_to_batch(row)
                _require_same_batch_identity(existing, batch)
                return existing
            connection.execute(
                """
                INSERT INTO persistence_batches
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _batch_values(batch),
            )
            return batch

    def mark_catalog_written(
        self,
        batch_id: str,
        written_ts: datetime,
    ) -> PersistenceBatch:
        written_ns = unix_ns_from_utc_datetime(written_ts)
        with self._transaction() as connection:
            cursor = connection.execute(
                """
                UPDATE persistence_batches
                SET status='catalog_written', updated_ts_ns=?, catalog_written_ts_ns=?
                WHERE batch_id=? AND status='prepared'
                """,
                (written_ns, written_ns, batch_id),
            )
            if cursor.rowcount == 0:
                row = connection.execute(
                    "SELECT * FROM persistence_batches WHERE batch_id=?",
                    (batch_id,),
                ).fetchone()
                if row is None:
                    raise KeyError(f"unknown persistence batch: {batch_id}")
                existing = _row_to_batch(row)
                if existing.status not in {
                    PersistenceBatchStatus.CATALOG_WRITTEN,
                    PersistenceBatchStatus.COMMITTED,
                }:
                    raise RuntimeError(f"batch cannot mark catalog written from {existing.status}")
                return existing
            row = connection.execute(
                "SELECT * FROM persistence_batches WHERE batch_id=?",
                (batch_id,),
            ).fetchone()
            return _row_to_batch(row)

    def commit_batch(
        self,
        *,
        batch_id: str,
        identities: tuple[PersistenceEventIdentity, ...],
        checkpoint: StreamCheckpoint,
        committed_ts: datetime,
    ) -> PersistenceBatch:
        committed_ns = unix_ns_from_utc_datetime(committed_ts)
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT * FROM persistence_batches WHERE batch_id=?",
                (batch_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown persistence batch: {batch_id}")
            batch = _row_to_batch(row)
            if batch.status == PersistenceBatchStatus.COMMITTED:
                return batch
            if batch.status != PersistenceBatchStatus.CATALOG_WRITTEN:
                raise RuntimeError("batch must be catalog-written before commit")
            if len(identities) != batch.expected_event_count:
                raise ValueError("committed identity count does not match prepared batch")

            for identity in identities:
                dedupe_hash = dedupe_key_fingerprint(identity.dedupe_key)
                identity_hash = logical_event_identity_fingerprint(identity)
                event_ts_ns = identity.event_ts_ns or unix_ns_from_utc_datetime(identity.event_ts)
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO persisted_event_identities
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dedupe_hash,
                        identity_hash,
                        batch_id,
                        identity.instrument_id,
                        identity.event_kind.value,
                        identity.source,
                        event_ts_ns,
                        committed_ns,
                    ),
                )
                if cursor.rowcount == 0:
                    existing = connection.execute(
                        "SELECT identity_hash FROM persisted_event_identities WHERE dedupe_hash=?",
                        (dedupe_hash,),
                    ).fetchone()
                    if bytes(existing["identity_hash"]) != identity_hash:
                        raise ValueError("dedupe key conflicts with a different event identity")

            self._upsert_checkpoint(connection, checkpoint, reject_regression=False)
            connection.execute(
                """
                UPDATE persistence_batches
                SET status='committed', updated_ts_ns=?, committed_ts_ns=?
                WHERE batch_id=?
                """,
                (committed_ns, committed_ns, batch_id),
            )
            row = connection.execute(
                "SELECT * FROM persistence_batches WHERE batch_id=?",
                (batch_id,),
            ).fetchone()
            return _row_to_batch(row)

    def load_batch(self, batch_id: str) -> PersistenceBatch | None:
        row = self._connection.execute(
            "SELECT * FROM persistence_batches WHERE batch_id=?",
            (batch_id,),
        ).fetchone()
        return None if row is None else _row_to_batch(row)

    def incomplete_batches(self) -> tuple[PersistenceBatch, ...]:
        rows = self._connection.execute("""
            SELECT * FROM persistence_batches
            WHERE status IN ('prepared', 'catalog_written')
            ORDER BY bucket_start_ts_ns, batch_id
            """).fetchall()
        return tuple(_row_to_batch(row) for row in rows)

    def retention_streams(self) -> frozenset[tuple[PersistenceEventKind, str, str]]:
        with self._lock:
            rows = self._connection.execute("""
                SELECT DISTINCT event_kind, instrument_id, source
                FROM persisted_event_identities
                """).fetchall()
        return frozenset(
            (
                PersistenceEventKind(row["event_kind"]),
                str(row["instrument_id"]),
                str(row["source"]),
            )
            for row in rows
        )

    def save_retention_report(self, report: RetentionReport) -> None:
        with self._transaction() as connection:
            connection.execute(
                """
                INSERT INTO retention_maintenance_runs
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(report.run_id),
                    report.schema_version,
                    unix_ns_from_utc_datetime(report.maintenance_ts),
                    report.status.value,
                    report.inspected_file_count,
                    report.catalog_bytes_before,
                    report.catalog_bytes_after,
                    report.deleted_file_count,
                    report.deleted_bytes,
                    report.pruned_identity_count,
                    report.pruned_batch_count,
                    json.dumps(list(report.unmanaged_instruments), separators=(",", ":")),
                    json.dumps(list(report.reason_codes), separators=(",", ":")),
                    report.error,
                ),
            )

    def load_retention_report(self, run_id: UUID) -> RetentionReport | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM retention_maintenance_runs WHERE run_id=?",
                (str(run_id),),
            ).fetchone()
        return None if row is None else _row_to_retention_report(row)

    def compact_database(self, minimum_reclaimable_bytes: int) -> SQLiteCompactionReport:
        if minimum_reclaimable_bytes < 0:
            raise ValueError("minimum reclaimable bytes cannot be negative")
        if any(self._config.journal_path.glob("*.wal")):
            raise RuntimeError("cannot compact metadata while ingress WAL files exist")
        with self._lock:
            incomplete = self._connection.execute("""
                SELECT COUNT(*) FROM persistence_batches
                WHERE status IN ('prepared', 'catalog_written')
                """).fetchone()[0]
            if incomplete:
                raise RuntimeError(
                    "cannot compact metadata while persistence batches are incomplete"
                )
            checkpoint = self._connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            if checkpoint[0] != 0:
                raise RuntimeError("cannot compact metadata while another SQLite client is active")
            page_size, pages_before, free_before = self._database_pages()
            reclaimable = page_size * free_before
            if reclaimable < minimum_reclaimable_bytes:
                report = SQLiteCompactionReport(
                    maintenance_ts=datetime.now(UTC),
                    status=SQLiteCompactionStatus.SKIPPED_THRESHOLD,
                    database_path=self._path,
                    page_size_bytes=page_size,
                    page_count_before=pages_before,
                    free_page_count_before=free_before,
                    page_count_after=pages_before,
                    free_page_count_after=free_before,
                    reclaimed_bytes=0,
                )
                self._save_compaction_report(report)
                return report

            self._connection.execute("PRAGMA locking_mode=EXCLUSIVE")
            try:
                self._connection.execute("BEGIN EXCLUSIVE")
                self._connection.execute("COMMIT")
                self._connection.execute("VACUUM")
            finally:
                self._connection.execute("PRAGMA locking_mode=NORMAL")
            _, pages_after, free_after = self._database_pages()
            report = SQLiteCompactionReport(
                maintenance_ts=datetime.now(UTC),
                status=SQLiteCompactionStatus.COMPLETED,
                database_path=self._path,
                page_size_bytes=page_size,
                page_count_before=pages_before,
                free_page_count_before=free_before,
                page_count_after=pages_after,
                free_page_count_after=free_after,
                reclaimed_bytes=max(0, (pages_before - pages_after) * page_size),
            )
            self._save_compaction_report(report)
            return report

    def load_compaction_report(self, run_id: UUID) -> SQLiteCompactionReport | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM metadata_compaction_runs WHERE run_id=?",
                (str(run_id),),
            ).fetchone()
        return None if row is None else _row_to_compaction_report(row)

    def _save_compaction_report(self, report: SQLiteCompactionReport) -> None:
        self._connection.execute(
            """
            INSERT INTO metadata_compaction_runs
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(report.run_id),
                report.schema_version,
                unix_ns_from_utc_datetime(report.maintenance_ts),
                report.status.value,
                str(report.database_path),
                report.page_size_bytes,
                report.page_count_before,
                report.free_page_count_before,
                report.page_count_after,
                report.free_page_count_after,
                report.reclaimed_bytes,
            ),
        )

    def _database_pages(self) -> tuple[int, int, int]:
        page_size = int(self._connection.execute("PRAGMA page_size").fetchone()[0])
        page_count = int(self._connection.execute("PRAGMA page_count").fetchone()[0])
        free_count = int(self._connection.execute("PRAGMA freelist_count").fetchone()[0])
        return page_size, page_count, free_count

    def prune_committed_history(
        self,
        cutoffs: dict[tuple[PersistenceEventKind, str, str], int],
    ) -> tuple[int, int]:
        if not cutoffs:
            return 0, 0
        with self._transaction() as connection:
            incomplete = connection.execute("""
                SELECT COUNT(*) FROM persistence_batches
                WHERE status IN ('prepared', 'catalog_written')
                """).fetchone()[0]
            if incomplete:
                raise RuntimeError("cannot prune metadata while persistence batches are incomplete")

            identity_count = 0
            for (event_kind, instrument_id, source), cutoff_ns in cutoffs.items():
                cursor = connection.execute(
                    """
                    DELETE FROM persisted_event_identities
                    WHERE event_kind=? AND instrument_id=? AND source=? AND event_ts_ns < ?
                    """,
                    (event_kind.value, instrument_id, source, cutoff_ns),
                )
                identity_count += cursor.rowcount
            batch_cursor = connection.execute("""
                DELETE FROM persistence_batches
                WHERE status='committed'
                  AND NOT EXISTS (
                      SELECT 1 FROM persisted_event_identities identities
                      WHERE identities.batch_id=persistence_batches.batch_id
                  )
                """)
            return identity_count, batch_cursor.rowcount

    def committed_dedupe_keys(
        self,
        identities: tuple[PersistenceEventIdentity, ...],
    ) -> frozenset[str]:
        if not identities:
            return frozenset()
        by_hash: dict[bytes, PersistenceEventIdentity] = {}
        for identity in identities:
            dedupe_hash = dedupe_key_fingerprint(identity.dedupe_key)
            existing = by_hash.get(dedupe_hash)
            if existing is not None and not same_logical_event_identity(existing, identity):
                raise ValueError("dedupe hash conflicts with a different event identity")
            by_hash[dedupe_hash] = identity
        hashes = tuple(by_hash)
        placeholders = ",".join("?" for _ in hashes)
        rows = self._connection.execute(
            f"""
            SELECT dedupe_hash, identity_hash FROM persisted_event_identities
            WHERE dedupe_hash IN ({placeholders})
            """,
            hashes,
        ).fetchall()
        for row in rows:
            dedupe_hash = bytes(row["dedupe_hash"])
            expected_hash = logical_event_identity_fingerprint(by_hash[dedupe_hash])
            if bytes(row["identity_hash"]) != expected_hash:
                raise ValueError("dedupe key conflicts with a different event identity")
        return frozenset(by_hash[bytes(row["dedupe_hash"])].dedupe_key for row in rows)

    def _configure(self) -> None:
        self._connection.create_function("sha256_blob", 1, _sha256_blob, deterministic=True)
        self._connection.create_function(
            "logical_identity_hash",
            1,
            _logical_identity_hash,
            deterministic=True,
        )
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA synchronous = FULL")
        self._connection.execute(f"PRAGMA busy_timeout = {self._config.sqlite_busy_timeout_ms}")

    def _migrate(self) -> None:
        current = self.schema_version
        if current > LATEST_SCHEMA_VERSION:
            raise RuntimeError(
                f"metadata schema version {current} is newer than supported "
                f"version {LATEST_SCHEMA_VERSION}"
            )
        for version, sql in MIGRATIONS:
            if version <= current:
                continue
            with self._transaction() as connection:
                for statement in sql.split(";"):
                    if statement.strip():
                        connection.execute(statement)
                connection.execute(
                    "INSERT INTO schema_migrations VALUES (?, ?)",
                    (version, unix_ns_from_utc_datetime(datetime.now(UTC))),
                )
                connection.execute(f"PRAGMA user_version = {version}")
            current = version

    def _save_state(
        self,
        table: str,
        instrument_id: str,
        state: ReadinessState | GapState,
        updated_ts: datetime,
    ) -> None:
        if table not in {"readiness_states", "gap_states"}:
            raise ValueError(f"unsupported state table: {table}")
        with self._transaction() as connection:
            cursor = connection.execute(
                f"""
                INSERT INTO {table} VALUES (?, ?, ?)
                ON CONFLICT(instrument_id) DO UPDATE SET
                    payload_json=excluded.payload_json,
                    updated_ts_ns=excluded.updated_ts_ns
                WHERE excluded.updated_ts_ns >= {table}.updated_ts_ns
                """,
                (
                    instrument_id,
                    state.model_dump_json(),
                    unix_ns_from_utc_datetime(updated_ts),
                ),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"{table} update cannot move state backward")

    def _load_state(self, table: str, instrument_id: str) -> str | None:
        if table not in {"readiness_states", "gap_states"}:
            raise ValueError(f"unsupported state table: {table}")
        row = self._connection.execute(
            f"SELECT payload_json FROM {table} WHERE instrument_id = ?",
            (instrument_id,),
        ).fetchone()
        return None if row is None else str(row["payload_json"])

    @staticmethod
    def _upsert_checkpoint(
        connection: sqlite3.Connection,
        checkpoint: StreamCheckpoint,
        *,
        reject_regression: bool,
    ) -> None:
        last_event_ts_ns = checkpoint.last_event_ts_ns or unix_ns_from_utc_datetime(
            checkpoint.last_event_ts
        )
        cursor = connection.execute(
            """
            INSERT INTO stream_checkpoints VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(stream_key) DO UPDATE SET
                schema_version=excluded.schema_version,
                instrument_id=excluded.instrument_id,
                event_kind=excluded.event_kind,
                source=excluded.source,
                last_event_ts_ns=excluded.last_event_ts_ns,
                last_dedupe_key=excluded.last_dedupe_key,
                committed_ts_ns=excluded.committed_ts_ns
            WHERE excluded.last_event_ts_ns >= stream_checkpoints.last_event_ts_ns
            """,
            (
                checkpoint.stream_key,
                checkpoint.schema_version,
                checkpoint.instrument_id,
                checkpoint.event_kind.value,
                checkpoint.source,
                last_event_ts_ns,
                checkpoint.last_dedupe_key,
                unix_ns_from_utc_datetime(checkpoint.committed_ts),
            ),
        )
        if cursor.rowcount != 1 and reject_regression:
            raise ValueError("checkpoint update cannot move stream progress backward")

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                yield self._connection
            except BaseException:
                self._connection.rollback()
                raise
            else:
                self._connection.commit()


def _json_dump(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _optional_ns(value: datetime | None) -> int | None:
    return None if value is None else unix_ns_from_utc_datetime(value)


def _optional_datetime(value: int | None) -> datetime | None:
    return None if value is None else utc_datetime_from_unix_ns(value)


def _require_recovery_transition(
    current_status: RecoveryStatus,
    current_updated_ns: int,
    recovery: RecoveryRecord,
) -> None:
    updated_ns = unix_ns_from_utc_datetime(recovery.updated_ts)
    if updated_ns < current_updated_ns:
        raise ValueError("recovery update cannot move state backward")
    allowed = {
        RecoveryStatus.PENDING: {
            RecoveryStatus.PENDING,
            RecoveryStatus.RECOVERING,
            RecoveryStatus.COMPLETE,
            RecoveryStatus.DEGRADED,
            RecoveryStatus.FAILED,
        },
        RecoveryStatus.RECOVERING: {
            RecoveryStatus.RECOVERING,
            RecoveryStatus.COMPLETE,
            RecoveryStatus.DEGRADED,
            RecoveryStatus.FAILED,
        },
        RecoveryStatus.COMPLETE: {RecoveryStatus.COMPLETE},
        RecoveryStatus.DEGRADED: {RecoveryStatus.DEGRADED},
        RecoveryStatus.FAILED: {RecoveryStatus.FAILED},
    }
    if recovery.status not in allowed[current_status]:
        raise ValueError(
            f"recovery status cannot move from {current_status.value} to {recovery.status.value}"
        )


def _row_to_recovery(row: sqlite3.Row) -> RecoveryRecord:
    return RecoveryRecord(
        schema_version=row["schema_version"],
        recovery_id=UUID(row["recovery_id"]),
        instrument_id=row["instrument_id"],
        event_kind=PersistenceEventKind(row["event_kind"]),
        source=row["source"],
        status=RecoveryStatus(row["status"]),
        requested_start_ts=utc_datetime_from_unix_ns(row["requested_start_ts_ns"]),
        requested_end_ts=utc_datetime_from_unix_ns(row["requested_end_ts_ns"]),
        missing_intervals=row["missing_intervals"],
        reason_codes=tuple(json.loads(row["reason_codes_json"])),
        started_ts=utc_datetime_from_unix_ns(row["started_ts_ns"]),
        updated_ts=utc_datetime_from_unix_ns(row["updated_ts_ns"]),
        completed_ts=_optional_datetime(row["completed_ts_ns"]),
    )


def _outbox_values(record: NotificationOutboxRecord) -> tuple[Any, ...]:
    return (
        str(record.outbox_id),
        record.schema_version,
        record.topic,
        record.destination_key,
        record.aggregate_key,
        record.event_type,
        record.event_schema_version,
        _json_dump(record.payload),
        record.dedupe_key,
        record.status.value,
        record.attempt_count,
        unix_ns_from_utc_datetime(record.available_ts),
        unix_ns_from_utc_datetime(record.created_ts),
        unix_ns_from_utc_datetime(record.updated_ts),
        record.lease_owner,
        _optional_ns(record.lease_expires_ts),
        _optional_ns(record.delivered_ts),
        record.last_error,
    )


def _enqueue_outbox(connection: sqlite3.Connection, record: NotificationOutboxRecord) -> bool:
    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO notification_outbox VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        _outbox_values(record),
    )
    return cursor.rowcount == 1


def _enqueue_outbox_exact(
    connection: sqlite3.Connection,
    record: NotificationOutboxRecord,
) -> None:
    if _enqueue_outbox(connection, record):
        return
    row = connection.execute(
        """
        SELECT * FROM notification_outbox
        WHERE outbox_id=? OR dedupe_key=?
        """,
        (str(record.outbox_id), record.dedupe_key),
    ).fetchone()
    if row is None or _row_to_outbox(row) != record:
        raise ValueError("signal notification conflicts with existing outbox record")


def _same_outbox_intent(
    existing: NotificationOutboxRecord,
    submitted: NotificationOutboxRecord,
) -> bool:
    excluded = {
        "status",
        "attempt_count",
        "updated_ts",
        "lease_owner",
        "lease_expires_ts",
        "delivered_ts",
        "last_error",
    }
    return existing.model_dump(exclude=excluded) == submitted.model_dump(exclude=excluded)


def _validate_signal_notification(
    event: SignalTransitionEvent,
    notification: NotificationOutboxRecord | None,
) -> None:
    if notification is None:
        return
    if notification.status != OutboxStatus.PENDING:
        raise ValueError("signal transition notification must be pending")
    if (
        notification.aggregate_key != event.signal_id
        or notification.event_type != "signal.transition"
        or notification.event_schema_version != event.schema_version
    ):
        raise ValueError("signal transition notification metadata does not match event")


def _save_signal_candidate(
    connection: sqlite3.Connection,
    signal: SignalSnapshot,
) -> SignalPersistenceOutcome:
    values = _new_signal_snapshot_values(signal)
    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO signal_snapshots (
            signal_id, initial_content_hash, content_hash, instrument_id,
            family, direction, status, updated_ts_ns, snapshot_json, definition_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        values,
    )
    if cursor.rowcount == 1:
        return SignalPersistenceOutcome.CREATED
    row = connection.execute(
        "SELECT * FROM signal_snapshots WHERE signal_id=?",
        (values[0],),
    ).fetchone()
    if row is None:
        raise RuntimeError("signal candidate conflict row disappeared")
    _verified_signal_history(connection, row)
    if bytes(row["initial_content_hash"]) != bytes.fromhex(signal.content_hash):
        raise ValueError("signal identity conflicts with different initial content")
    return SignalPersistenceOutcome.DUPLICATE


def _apply_signal_transition(
    connection: sqlite3.Connection,
    event: SignalTransitionEvent,
    notification: NotificationOutboxRecord | None,
) -> SignalPersistenceOutcome:
    transition_id = bytes.fromhex(event.transition_id)
    signal_id = bytes.fromhex(event.signal_id)
    notification_id = None if notification is None else str(notification.outbox_id)
    prior_transition = connection.execute(
        "SELECT * FROM signal_transitions WHERE transition_id=?",
        (transition_id,),
    ).fetchone()
    if prior_transition is not None:
        existing = _row_to_signal_transition(prior_transition)
        if existing != event:
            raise ValueError("transition identity conflicts with different content")
        if prior_transition["notification_outbox_id"] != notification_id:
            raise ValueError("transition notification attachment conflicts with retry")
        if notification is not None:
            outbox_row = connection.execute(
                "SELECT * FROM notification_outbox WHERE outbox_id=?",
                (notification_id,),
            ).fetchone()
            if outbox_row is None or not _same_outbox_intent(
                _row_to_outbox(outbox_row), notification
            ):
                raise ValueError("transition notification content conflicts with retry")
        return SignalPersistenceOutcome.DUPLICATE

    row = connection.execute(
        "SELECT * FROM signal_snapshots WHERE signal_id=?",
        (signal_id,),
    ).fetchone()
    if row is None:
        raise KeyError(f"unknown signal: {event.signal_id}")
    current, _ = _verified_signal_history(connection, row)
    if current.content_hash != event.previous_content_hash:
        raise ValueError("signal transition previous content hash is stale")
    if current.status != event.from_status:
        raise ValueError("signal transition source status is stale")

    if notification is not None:
        _enqueue_outbox_exact(connection, notification)
    sequence_no = connection.execute(
        """
        SELECT COALESCE(MAX(sequence_no), 0) + 1
        FROM signal_transitions WHERE signal_id=?
        """,
        (signal_id,),
    ).fetchone()[0]
    connection.execute(
        """
        INSERT INTO signal_transitions VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            transition_id,
            signal_id,
            sequence_no,
            unix_ns_from_utc_datetime(event.occurred_ts),
            event.from_status.value,
            event.to_status.value,
            event.model_dump_json(),
            notification_id,
        ),
    )
    snapshot_values = _signal_current_values(event.current)
    cursor = connection.execute(
        """
        UPDATE signal_snapshots
        SET content_hash=?, instrument_id=?, family=?, direction=?, status=?,
            updated_ts_ns=?, snapshot_json=?, definition_id=?
        WHERE signal_id=? AND content_hash=?
        """,
        (
            *snapshot_values[1:],
            signal_id,
            bytes.fromhex(event.previous_content_hash),
        ),
    )
    if cursor.rowcount != 1:
        raise RuntimeError("signal transition lost optimistic update race")
    return SignalPersistenceOutcome.TRANSITIONED


def _new_signal_snapshot_values(signal: SignalSnapshot) -> tuple[Any, ...]:
    return (
        bytes.fromhex(signal.signal_id),
        bytes.fromhex(signal.content_hash),
        *_signal_current_values(signal)[1:],
    )


def _signal_current_values(signal: SignalSnapshot) -> tuple[Any, ...]:
    return (
        bytes.fromhex(signal.signal_id),
        bytes.fromhex(signal.content_hash),
        signal.instrument_id,
        signal.family.value,
        signal.direction.value,
        signal.status.value,
        unix_ns_from_utc_datetime(signal.updated_ts),
        signal.model_dump_json(),
        signal.definition_id,
    )


def _row_to_signal_snapshot(row: sqlite3.Row) -> SignalSnapshot:
    signal = SignalSnapshot.model_validate_json(row["snapshot_json"])
    if bytes(row["signal_id"]) != bytes.fromhex(signal.signal_id):
        raise ValueError("stored signal id does not match snapshot")
    if bytes(row["content_hash"]) != bytes.fromhex(signal.content_hash):
        raise ValueError("stored signal content hash does not match snapshot")
    if (
        row["instrument_id"] != signal.instrument_id
        or row["definition_id"] != signal.definition_id
        or row["family"] != signal.family.value
        or row["direction"] != signal.direction.value
        or row["status"] != signal.status.value
        or row["updated_ts_ns"] != unix_ns_from_utc_datetime(signal.updated_ts)
    ):
        raise ValueError("stored signal metadata does not match snapshot")
    return signal


def _row_to_signal_transition(row: sqlite3.Row) -> SignalTransitionEvent:
    event = SignalTransitionEvent.model_validate_json(row["event_json"])
    if (
        bytes(row["transition_id"]) != bytes.fromhex(event.transition_id)
        or bytes(row["signal_id"]) != bytes.fromhex(event.signal_id)
        or row["occurred_ts_ns"] != unix_ns_from_utc_datetime(event.occurred_ts)
        or row["from_status"] != event.from_status.value
        or row["to_status"] != event.to_status.value
    ):
        raise ValueError("stored signal transition metadata does not match event")
    return event


def _verified_signal_history(
    connection: sqlite3.Connection,
    snapshot_row: sqlite3.Row,
) -> tuple[SignalSnapshot, tuple[SignalTransitionEvent, ...]]:
    current = _row_to_signal_snapshot(snapshot_row)
    rows = connection.execute(
        """
        SELECT * FROM signal_transitions
        WHERE signal_id=? ORDER BY sequence_no
        """,
        (snapshot_row["signal_id"],),
    ).fetchall()
    events = tuple(_row_to_signal_transition(row) for row in rows)
    expected_hash = bytes(snapshot_row["initial_content_hash"]).hex()
    for expected_sequence, (row, event) in enumerate(zip(rows, events, strict=True), start=1):
        if row["sequence_no"] != expected_sequence:
            raise ValueError("stored signal transition sequence is not contiguous")
        if event.previous_content_hash != expected_hash:
            raise ValueError("stored signal transition history has a broken content chain")
        expected_hash = event.current.content_hash
    if expected_hash != current.content_hash:
        raise ValueError("stored signal transition history does not reach current snapshot")
    return current, events


def _row_to_outbox(row: sqlite3.Row) -> NotificationOutboxRecord:
    return NotificationOutboxRecord(
        schema_version=row["schema_version"],
        outbox_id=UUID(row["outbox_id"]),
        topic=row["topic"],
        destination_key=row["destination_key"],
        aggregate_key=row["aggregate_key"],
        event_type=row["event_type"],
        event_schema_version=row["event_schema_version"],
        payload=json.loads(row["payload_json"]),
        dedupe_key=row["dedupe_key"],
        status=OutboxStatus(row["status"]),
        attempt_count=row["attempt_count"],
        available_ts=utc_datetime_from_unix_ns(row["available_ts_ns"]),
        created_ts=utc_datetime_from_unix_ns(row["created_ts_ns"]),
        updated_ts=utc_datetime_from_unix_ns(row["updated_ts_ns"]),
        lease_owner=row["lease_owner"],
        lease_expires_ts=_optional_datetime(row["lease_expires_ts_ns"]),
        delivered_ts=_optional_datetime(row["delivered_ts_ns"]),
        last_error=row["last_error"],
    )


def _batch_values(batch: PersistenceBatch) -> tuple[Any, ...]:
    return (
        batch.batch_id,
        batch.schema_version,
        batch.instrument_id,
        batch.event_kind.value,
        batch.source,
        unix_ns_from_utc_datetime(batch.bucket_start_ts),
        unix_ns_from_utc_datetime(batch.bucket_end_ts),
        batch.expected_event_count,
        batch.identity_hash,
        batch.status.value,
        unix_ns_from_utc_datetime(batch.created_ts),
        unix_ns_from_utc_datetime(batch.updated_ts),
        _optional_ns(batch.catalog_written_ts),
        _optional_ns(batch.committed_ts),
        batch.last_error,
    )


def _row_to_batch(row: sqlite3.Row) -> PersistenceBatch:
    return PersistenceBatch(
        schema_version=row["schema_version"],
        batch_id=row["batch_id"],
        instrument_id=row["instrument_id"],
        event_kind=PersistenceEventKind(row["event_kind"]),
        source=row["source"],
        bucket_start_ts=utc_datetime_from_unix_ns(row["bucket_start_ts_ns"]),
        bucket_end_ts=utc_datetime_from_unix_ns(row["bucket_end_ts_ns"]),
        expected_event_count=row["expected_event_count"],
        identity_hash=row["identity_hash"],
        status=PersistenceBatchStatus(row["status"]),
        created_ts=utc_datetime_from_unix_ns(row["created_ts_ns"]),
        updated_ts=utc_datetime_from_unix_ns(row["updated_ts_ns"]),
        catalog_written_ts=_optional_datetime(row["catalog_written_ts_ns"]),
        committed_ts=_optional_datetime(row["committed_ts_ns"]),
        last_error=row["last_error"],
    )


def _row_to_retention_report(row: sqlite3.Row) -> RetentionReport:
    return RetentionReport(
        schema_version=row["schema_version"],
        run_id=UUID(row["run_id"]),
        maintenance_ts=utc_datetime_from_unix_ns(row["maintenance_ts_ns"]),
        status=RetentionStatus(row["status"]),
        inspected_file_count=row["inspected_file_count"],
        catalog_bytes_before=row["catalog_bytes_before"],
        catalog_bytes_after=row["catalog_bytes_after"],
        deleted_file_count=row["deleted_file_count"],
        deleted_bytes=row["deleted_bytes"],
        pruned_identity_count=row["pruned_identity_count"],
        pruned_batch_count=row["pruned_batch_count"],
        unmanaged_instruments=tuple(json.loads(row["unmanaged_instruments_json"])),
        reason_codes=tuple(json.loads(row["reason_codes_json"])),
        error=row["error"],
    )


def _row_to_compaction_report(row: sqlite3.Row) -> SQLiteCompactionReport:
    return SQLiteCompactionReport(
        schema_version=row["schema_version"],
        run_id=UUID(row["run_id"]),
        maintenance_ts=utc_datetime_from_unix_ns(row["maintenance_ts_ns"]),
        status=SQLiteCompactionStatus(row["status"]),
        database_path=Path(row["database_path"]),
        page_size_bytes=row["page_size_bytes"],
        page_count_before=row["page_count_before"],
        free_page_count_before=row["free_page_count_before"],
        page_count_after=row["page_count_after"],
        free_page_count_after=row["free_page_count_after"],
        reclaimed_bytes=row["reclaimed_bytes"],
    )


def _require_same_batch_identity(existing: PersistenceBatch, proposed: PersistenceBatch) -> None:
    fields = (
        "instrument_id",
        "event_kind",
        "source",
        "bucket_start_ts",
        "bucket_end_ts",
        "expected_event_count",
        "identity_hash",
    )
    if any(getattr(existing, field) != getattr(proposed, field) for field in fields):
        raise ValueError("batch id conflicts with different immutable metadata")


def _sha256_blob(value: str) -> bytes:
    return dedupe_key_fingerprint(value)


def _logical_identity_hash(payload: str) -> bytes:
    identity = PersistenceEventIdentity.model_validate_json(payload)
    return logical_event_identity_fingerprint(identity)
