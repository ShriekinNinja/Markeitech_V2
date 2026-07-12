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

from markeitech.domain.base import unix_ns_from_utc_datetime, utc_datetime_from_unix_ns
from markeitech.domain.state import GapState, ReadinessState
from markeitech.persistence.config import PersistenceConfig
from markeitech.persistence.contracts import (
    NotificationOutboxRecord,
    OutboxStatus,
    PersistenceEventKind,
    RecoveryRecord,
    RecoveryStatus,
    StreamCheckpoint,
)

LATEST_SCHEMA_VERSION = 1

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
        last_event_ts_ns = checkpoint.last_event_ts_ns or unix_ns_from_utc_datetime(
            checkpoint.last_event_ts
        )
        with self._transaction() as connection:
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
            if cursor.rowcount != 1:
                raise ValueError("checkpoint update cannot move stream progress backward")

    def load_checkpoint(self, stream_key: str) -> StreamCheckpoint | None:
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

    def save_recovery(self, recovery: RecoveryRecord) -> None:
        with self._transaction() as connection:
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
        row = self._connection.execute(
            "SELECT * FROM recovery_records WHERE recovery_id = ?",
            (str(recovery_id),),
        ).fetchone()
        return None if row is None else _row_to_recovery(row)

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
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO notification_outbox VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                _outbox_values(record),
            )
            return cursor.rowcount == 1

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

    def _configure(self) -> None:
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
