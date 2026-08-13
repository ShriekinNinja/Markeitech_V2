from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from queue import Empty, Full, Queue
from threading import Lock, Thread
from time import monotonic, sleep, time_ns
from types import MappingProxyType
from typing import Protocol
from uuid import UUID, uuid4

import psycopg
from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId
from psycopg.types.json import Jsonb

from markeitech.system.messages import (
    ACQUISITION_STATUS_REQUEST_SIGNAL,
    ACQUISITION_STATUS_SIGNAL,
    ACQUISITION_STREAM_SIGNAL,
    COMPONENT_FAILURE_SIGNAL,
    PERSISTENCE_READY_REQUEST_SIGNAL,
    PERSISTENCE_READY_SIGNAL,
    SYSTEM_HEALTH_SIGNAL,
    WATCHLIST_DEMAND_SIGNAL,
    WATCHLIST_LIFECYCLE_SIGNAL,
    WATCHLIST_MEMBERSHIP_SIGNAL,
    AcquisitionStatusEvent,
    AcquisitionStatusRequest,
    AcquisitionStreamEvent,
    ComponentFailureEvent,
    PersistenceReadyEvent,
    PersistenceReadyRequest,
    SystemHealthEvent,
    WatchlistDemandEvent,
    WatchlistLifecycleEvent,
    WatchlistMembershipEvent,
)
from markeitech.system.persistence_migrations import MIGRATIONS, REQUIRED_SCHEMA_COLUMNS

PERSISTENCE_SCHEMA_VERSION = 1
_MIGRATION_LOCK_ID = 4_873_274_823
_RESULT_TIMER = "operational-persistence-results"
_READY_ALERT = "operational-persistence-ready"
_READY_DELAY_NS = 1_000_000
_STOP = object()


@dataclass(frozen=True, slots=True)
class HealthEventRecord:
    run_id: UUID
    sequence: int
    event: SystemHealthEvent
    ts_event_ns: int
    ts_init_ns: int


@dataclass(frozen=True, slots=True)
class PersistenceResult:
    sequence: int
    state: str
    stored: bool
    attempts: int
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class PersistenceWorkerStats:
    accepted: int
    stored: int
    retry_attempts: int
    failed: int
    rejected: int

    @property
    def pending(self) -> int:
        return self.accepted - self.stored - self.failed


@dataclass(frozen=True, slots=True)
class RuntimeRunRecord:
    run_id: UUID
    runtime_id: str
    started_at_ns: int
    ended_at_ns: int | None
    terminal_state: str | None
    terminal_reason: str | None


@dataclass(frozen=True, slots=True)
class StoredHealthEvent:
    sequence: int
    state: str
    reason: str
    source: str
    evidence: dict[str, object]
    ts_event_ns: int
    ts_init_ns: int


@dataclass(frozen=True, slots=True)
class OperationalEventRecord:
    event_id: str
    run_id: UUID
    sequence: int
    signal_name: str
    event_type: str
    source: str
    payload: Mapping[str, object]
    ts_event_ns: int
    ts_init_ns: int
    schema_version: int
    correlation_id: str | None = None
    causation_id: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("event_id", "signal_name", "event_type", "source"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
            object.__setattr__(self, field_name, value.strip())
        for field_name in ("correlation_id", "causation_id"):
            value = getattr(self, field_name)
            if value is not None:
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"{field_name} must be None or a non-empty string")
                object.__setattr__(self, field_name, value.strip())
        for field_name in ("sequence", "schema_version"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{field_name} must be a positive integer")
        for field_name in ("ts_event_ns", "ts_init_ns"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        if not isinstance(self.payload, Mapping):
            raise ValueError("payload must be a mapping")
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))


@dataclass(frozen=True, slots=True)
class StoredOperationalEvent:
    event_id: str
    sequence: int
    signal_name: str
    event_type: str
    source: str
    correlation_id: str | None
    causation_id: str | None
    payload: dict[str, object]
    ts_event_ns: int
    ts_init_ns: int
    schema_version: int


type PersistedRecord = HealthEventRecord | OperationalEventRecord


class EventWriter(Protocol):
    def __call__(self, record: PersistedRecord) -> None: ...


class OperationalStore:
    def __init__(self, dsn: str, connect_timeout_seconds: int) -> None:
        self._dsn = dsn
        self._connect_timeout_seconds = connect_timeout_seconds

    @classmethod
    def from_environment(cls, dsn_env: str, connect_timeout_seconds: int) -> OperationalStore:
        dsn = os.getenv(dsn_env, "").strip()
        if not dsn:
            raise RuntimeError(f"required PostgreSQL environment variable is missing: {dsn_env}")
        return cls(dsn, connect_timeout_seconds)

    def initialize(self) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", (_MIGRATION_LOCK_ID,))
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS markeitech_schema_migrations (
                        version INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """,
                )
                cursor.execute("SELECT version FROM markeitech_schema_migrations")
                applied = {row[0] for row in cursor.fetchall()}
                for migration in MIGRATIONS:
                    cursor.execute(migration.sql)
                    if migration.version not in applied:
                        cursor.execute(
                            """
                            INSERT INTO markeitech_schema_migrations (version, name)
                            VALUES (%s, %s)
                            """,
                            (migration.version, migration.name),
                        )
                self._verify_schema(cursor)

    @staticmethod
    def _verify_schema(cursor: psycopg.Cursor[object]) -> None:
        cursor.execute(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = ANY(%s)
            """,
            (list(REQUIRED_SCHEMA_COLUMNS),),
        )
        actual: dict[str, set[str]] = {}
        for table_name, column_name in cursor.fetchall():
            actual.setdefault(str(table_name), set()).add(str(column_name))

        problems: list[str] = []
        for table_name, required_columns in REQUIRED_SCHEMA_COLUMNS.items():
            actual_columns = actual.get(table_name)
            if actual_columns is None:
                problems.append(f"missing table {table_name}")
                continue
            missing_columns = sorted(required_columns - actual_columns)
            if missing_columns:
                problems.append(
                    f"table {table_name} missing columns {', '.join(missing_columns)}",
                )
        if problems:
            raise RuntimeError(f"PostgreSQL schema verification failed: {'; '.join(problems)}")

    def check(self) -> None:
        with self._connect() as connection:
            row = connection.execute("SELECT 1").fetchone()
            if row != (1,):
                raise RuntimeError("PostgreSQL readiness check returned an unexpected result")

    def start_run(self, runtime_id: str, run_id: UUID | None = None) -> UUID:
        run_id = run_id or uuid4()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO runtime_runs (
                    run_id, runtime_id, started_at_ns, schema_version
                ) VALUES (%s, %s, %s, %s)
                """,
                (run_id, runtime_id, time_ns(), PERSISTENCE_SCHEMA_VERSION),
            )
        return run_id

    def close_run(self, run_id: UUID, terminal_state: str, terminal_reason: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE runtime_runs
                SET ended_at_ns = %s, terminal_state = %s, terminal_reason = %s
                WHERE run_id = %s AND ended_at_ns IS NULL
                """,
                (time_ns(), terminal_state, terminal_reason, run_id),
            )
            if cursor.rowcount != 1:
                raise RuntimeError(f"runtime run could not be closed exactly once: {run_id}")

    def write_health_event(self, record: HealthEventRecord) -> None:
        event = record.event
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO system_health_events (
                    run_id, sequence, signal_name, state, reason, source, evidence_json,
                    ts_event_ns, ts_init_ns, recorded_at_ns, schema_version
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id, sequence) DO NOTHING
                """,
                (
                    record.run_id,
                    record.sequence,
                    SYSTEM_HEALTH_SIGNAL,
                    event.state,
                    event.reason,
                    event.source,
                    Jsonb(dict(event.evidence)),
                    record.ts_event_ns,
                    record.ts_init_ns,
                    time_ns(),
                    event.schema_version,
                ),
            )

    def write_operational_event(self, record: OperationalEventRecord) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO operational_events (
                    event_id, run_id, sequence, signal_name, event_type, source,
                    correlation_id, causation_id, payload_json, ts_event_ns, ts_init_ns,
                    recorded_at_ns, schema_version
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id, event_id) DO NOTHING
                """,
                (
                    record.event_id,
                    record.run_id,
                    record.sequence,
                    record.signal_name,
                    record.event_type,
                    record.source,
                    record.correlation_id,
                    record.causation_id,
                    Jsonb(dict(record.payload)),
                    record.ts_event_ns,
                    record.ts_init_ns,
                    time_ns(),
                    record.schema_version,
                ),
            )
            if cursor.rowcount == 1:
                return
            existing = connection.execute(
                """
                SELECT run_id, sequence, signal_name, event_type, source,
                       correlation_id, causation_id, payload_json, ts_event_ns,
                       ts_init_ns, schema_version
                FROM operational_events
                WHERE run_id = %s AND event_id = %s
                """,
                (record.run_id, record.event_id),
            ).fetchone()
            if existing != _operational_identity(record):
                raise RuntimeError(
                    f"operational event identity collision: {record.event_id}",
                )

    def load_run(self, run_id: UUID) -> RuntimeRunRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT run_id, runtime_id, started_at_ns, ended_at_ns,
                       terminal_state, terminal_reason
                FROM runtime_runs
                WHERE run_id = %s
                """,
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return RuntimeRunRecord(
            run_id=row[0],
            runtime_id=row[1],
            started_at_ns=row[2],
            ended_at_ns=row[3],
            terminal_state=row[4],
            terminal_reason=row[5],
        )

    def load_health_events(self, run_id: UUID) -> tuple[StoredHealthEvent, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT sequence, state, reason, source, evidence_json,
                       ts_event_ns, ts_init_ns
                FROM system_health_events
                WHERE run_id = %s
                ORDER BY sequence
                """,
                (run_id,),
            ).fetchall()
        return tuple(
            StoredHealthEvent(
                sequence=row[0],
                state=row[1],
                reason=row[2],
                source=row[3],
                evidence=row[4],
                ts_event_ns=row[5],
                ts_init_ns=row[6],
            )
            for row in rows
        )

    def load_operational_events(self, run_id: UUID) -> tuple[StoredOperationalEvent, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_id, sequence, signal_name, event_type, source,
                       correlation_id, causation_id, payload_json, ts_event_ns,
                       ts_init_ns, schema_version
                FROM operational_events
                WHERE run_id = %s
                ORDER BY sequence
                """,
                (run_id,),
            ).fetchall()
        return tuple(
            StoredOperationalEvent(
                event_id=row[0],
                sequence=row[1],
                signal_name=row[2],
                event_type=row[3],
                source=row[4],
                correlation_id=row[5],
                causation_id=row[6],
                payload=row[7],
                ts_event_ns=row[8],
                ts_init_ns=row[9],
                schema_version=row[10],
            )
            for row in rows
        )

    def _connect(self):  # noqa: ANN202
        return psycopg.connect(
            self._dsn,
            connect_timeout=self._connect_timeout_seconds,
        )


def _operational_identity(record: OperationalEventRecord) -> tuple[object, ...]:
    return (
        record.run_id,
        record.sequence,
        record.signal_name,
        record.event_type,
        record.source,
        record.correlation_id,
        record.causation_id,
        dict(record.payload),
        record.ts_event_ns,
        record.ts_init_ns,
        record.schema_version,
    )


class PersistenceWorker:
    def __init__(
        self,
        writer: EventWriter,
        queue_capacity: int,
        shutdown_timeout_seconds: int,
        write_max_attempts: int,
        write_retry_backoff_ms: int,
    ) -> None:
        self._writer = writer
        self._shutdown_timeout_seconds = shutdown_timeout_seconds
        self._write_max_attempts = write_max_attempts
        self._write_retry_backoff_seconds = write_retry_backoff_ms / 1_000
        self._pending: Queue[PersistedRecord | object] = Queue(maxsize=queue_capacity)
        self.results: Queue[PersistenceResult] = Queue()
        self._closed = False
        self._stop_enqueued = False
        self._counter_lock = Lock()
        self._accepted = 0
        self._stored = 0
        self._retry_attempts = 0
        self._failed = 0
        self._rejected = 0
        self._thread = Thread(
            target=self._run,
            name="markeitech-operational-persistence",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def submit(self, record: PersistedRecord) -> bool:
        if self._closed:
            self._increment("_rejected")
            return False
        # Operational events are sparse control-plane data and must not be dropped
        # when startup or shutdown briefly fills the bounded queue. Backpressure is
        # preferable to creating holes in the audit sequence.
        self._pending.put(record)
        self._increment("_accepted")
        return True

    def close(self) -> bool:
        self._closed = True
        deadline = monotonic() + self._shutdown_timeout_seconds
        if not self._stop_enqueued:
            try:
                self._pending.put(_STOP, timeout=max(0.0, deadline - monotonic()))
            except Full:
                return False
            self._stop_enqueued = True
        self._thread.join(timeout=max(0.0, deadline - monotonic()))
        return not self._thread.is_alive()

    def snapshot(self) -> PersistenceWorkerStats:
        with self._counter_lock:
            return PersistenceWorkerStats(
                accepted=self._accepted,
                stored=self._stored,
                retry_attempts=self._retry_attempts,
                failed=self._failed,
                rejected=self._rejected,
            )

    def _run(self) -> None:
        while True:
            item = self._pending.get()
            try:
                if item is _STOP:
                    return
                assert isinstance(item, HealthEventRecord | OperationalEventRecord)
                self._write_with_retries(item)
            finally:
                self._pending.task_done()

    def _write_with_retries(self, record: PersistedRecord) -> None:
        for attempt in range(1, self._write_max_attempts + 1):
            try:
                self._writer(record)
            except Exception as exc:
                if attempt < self._write_max_attempts:
                    self._increment("_retry_attempts")
                    sleep(self._write_retry_backoff_seconds)
                    continue
                self._increment("_failed")
                self.results.put(
                    PersistenceResult(
                        sequence=record.sequence,
                        state=_record_state(record),
                        stored=False,
                        attempts=attempt,
                        error_code=type(exc).__name__,
                    ),
                )
                return
            self._increment("_stored")
            self.results.put(
                PersistenceResult(
                    sequence=record.sequence,
                    state=_record_state(record),
                    stored=True,
                    attempts=attempt,
                ),
            )
            return

    def _increment(self, field_name: str) -> None:
        with self._counter_lock:
            setattr(self, field_name, getattr(self, field_name) + 1)


class OperationalPersistenceActorConfig(DataActorConfig):
    def __new__(
        cls,
        run_id: str,
        dsn_env: str,
        connect_timeout_seconds: int,
        queue_capacity: int,
        result_poll_interval_ms: int,
        shutdown_timeout_seconds: int,
        write_max_attempts: int,
        write_retry_backoff_ms: int,
        actor_id: str | ActorId = "OPERATIONAL-PERSISTENCE",
    ) -> OperationalPersistenceActorConfig:
        resolved_actor_id = (
            actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        )
        obj = super().__new__(cls, actor_id=resolved_actor_id)
        obj.run_id = run_id
        obj.dsn_env = dsn_env
        obj.connect_timeout_seconds = connect_timeout_seconds
        obj.queue_capacity = queue_capacity
        obj.result_poll_interval_ms = result_poll_interval_ms
        obj.shutdown_timeout_seconds = shutdown_timeout_seconds
        obj.write_max_attempts = write_max_attempts
        obj.write_retry_backoff_ms = write_retry_backoff_ms
        return obj


class OperationalPersistenceActor(DataActor):
    def __init__(self, config: OperationalPersistenceActorConfig) -> None:
        super().__init__(config)
        self._run_id = UUID(config.run_id)
        self._dsn_env = config.dsn_env
        self._connect_timeout_seconds = config.connect_timeout_seconds
        self._queue_capacity = config.queue_capacity
        self._shutdown_timeout_seconds = config.shutdown_timeout_seconds
        self._write_max_attempts = config.write_max_attempts
        self._write_retry_backoff_ms = config.write_retry_backoff_ms
        self._result_poll_interval_ns = config.result_poll_interval_ms * 1_000_000
        self._worker: PersistenceWorker | None = None
        self._sequence = 0
        self._subscribed_signals: set[str] = set()
        self._failure_published = False

    def on_start(self) -> None:
        try:
            store = OperationalStore.from_environment(
                self._dsn_env,
                self._connect_timeout_seconds,
            )
            store.check()
        except Exception as exc:
            self._report_failure("runtime_connection_failed", type(exc).__name__)
            raise
        self._worker = PersistenceWorker(
            lambda record: _write_record(store, record),
            self._queue_capacity,
            self._shutdown_timeout_seconds,
            self._write_max_attempts,
            self._write_retry_backoff_ms,
        )
        self._worker.start()
        for signal_name in (
            SYSTEM_HEALTH_SIGNAL,
            COMPONENT_FAILURE_SIGNAL,
            ACQUISITION_STATUS_REQUEST_SIGNAL,
            ACQUISITION_STATUS_SIGNAL,
            ACQUISITION_STREAM_SIGNAL,
            WATCHLIST_DEMAND_SIGNAL,
            WATCHLIST_MEMBERSHIP_SIGNAL,
            WATCHLIST_LIFECYCLE_SIGNAL,
            PERSISTENCE_READY_REQUEST_SIGNAL,
        ):
            self.subscribe_signal(signal_name)
            self._subscribed_signals.add(signal_name)
        self.clock.set_timer_ns(
            _RESULT_TIMER,
            self._result_poll_interval_ns,
            callback=self._drain_results,
        )
        self.clock.set_time_alert_ns(
            _READY_ALERT,
            self.clock.timestamp_ns() + _READY_DELAY_NS,
            callback=self._announce_ready,
        )

    def on_signal(self, signal: Signal) -> None:
        if signal.name == PERSISTENCE_READY_REQUEST_SIGNAL:
            try:
                PersistenceReadyRequest.from_signal_value(signal.value)
            except ValueError as exc:
                self._report_failure("invalid_persistence_ready_request", type(exc).__name__)
                return
            self._publish_ready()
            return
        if self._worker is None:
            self._report_failure("persistence_worker_unavailable", "not_started")
            return
        self._sequence += 1
        try:
            record = _record_from_signal(self._run_id, self._sequence, signal)
        except ValueError as exc:
            self._report_failure("invalid_operational_event", type(exc).__name__)
            return
        if not self._worker.submit(record):
            self._report_failure("persistence_queue_unavailable", "queue_full_or_closed")

    def _publish_ready(self) -> None:
        self.publish_signal(
            PERSISTENCE_READY_SIGNAL,
            PersistenceReadyEvent(
                source=str(self.actor_id),
                run_id=str(self._run_id),
            ).to_signal_value(),
        )

    def _announce_ready(self, _event) -> None:  # noqa: ANN001
        self._publish_ready()
        self.log.info(f"OPERATIONAL_PERSISTENCE_READY | run_id={self._run_id}")

    def on_stop(self) -> None:
        for signal_name in tuple(self._subscribed_signals):
            self.unsubscribe_signal(signal_name)
            self._subscribed_signals.remove(signal_name)
        if _RESULT_TIMER in self.clock.timer_names():
            self.clock.cancel_timer(_RESULT_TIMER)
        if _READY_ALERT in self.clock.timer_names():
            self.clock.cancel_timer(_READY_ALERT)
        if self._worker is not None and not self._worker.close():
            self._report_failure("persistence_worker_timeout", "shutdown_timeout")
        self._drain_results(None)
        self._log_summary()

    def on_dispose(self) -> None:
        if self._worker is not None:
            self._worker.close()

    def _drain_results(self, _event) -> None:  # noqa: ANN001
        if self._worker is None:
            return
        while True:
            try:
                result = self._worker.results.get_nowait()
            except Empty:
                return
            if result.stored:
                self.log.info(
                    f"OPERATIONAL_EVENT_STORED | sequence={result.sequence} | state={result.state}",
                )
            else:
                self._report_failure(
                    "operational_event_write_failed",
                    result.error_code or "unknown",
                    evidence={"attempts": result.attempts, "sequence": result.sequence},
                )

    def _report_failure(
        self,
        reason: str,
        error_code: str,
        *,
        evidence: dict[str, str | int | float | bool | None] | None = None,
    ) -> None:
        self.log.error(
            f"OPERATIONAL_PERSISTENCE_FAILED | reason={reason} | error={error_code}",
        )
        if self._failure_published:
            return
        self._failure_published = True
        self.publish_signal(
            COMPONENT_FAILURE_SIGNAL,
            ComponentFailureEvent(
                component="operational_persistence",
                code=reason,
                reason="operational persistence is unavailable",
                evidence={
                    "error_code": error_code,
                    "run_id": str(self._run_id),
                    **(evidence or {}),
                },
            ).to_signal_value(),
        )

    def _log_summary(self) -> None:
        if self._worker is None:
            self.log.info(
                "OPERATIONAL_PERSISTENCE_SUMMARY | accepted=0 | stored=0"
                " | retries=0 | failed=0 | rejected=0 | pending=0",
            )
            return
        stats = self._worker.snapshot()
        self.log.info(
            "OPERATIONAL_PERSISTENCE_SUMMARY"
            f" | accepted={stats.accepted} | stored={stats.stored}"
            f" | retries={stats.retry_attempts} | failed={stats.failed}"
            f" | rejected={stats.rejected} | pending={stats.pending}",
        )


def _write_record(store: OperationalStore, record: PersistedRecord) -> None:
    if isinstance(record, HealthEventRecord):
        store.write_health_event(record)
        return
    store.write_operational_event(record)


def _record_from_signal(run_id: UUID, sequence: int, signal: Signal) -> PersistedRecord:
    if signal.name == SYSTEM_HEALTH_SIGNAL:
        return HealthEventRecord(
            run_id=run_id,
            sequence=sequence,
            event=SystemHealthEvent.from_signal_value(signal.value),
            ts_event_ns=signal.ts_event,
            ts_init_ns=signal.ts_init,
        )
    if signal.name == WATCHLIST_MEMBERSHIP_SIGNAL:
        event = WatchlistMembershipEvent.from_signal_value(signal.value)
        return OperationalEventRecord(
            event_id=event.event_id,
            run_id=run_id,
            sequence=sequence,
            signal_name=signal.name,
            event_type="watchlist.membership",
            source=event.source,
            correlation_id=event.event_id,
            causation_id=None,
            payload=json.loads(signal.value),
            ts_event_ns=signal.ts_event,
            ts_init_ns=signal.ts_init,
            schema_version=event.schema_version,
        )
    if signal.name == WATCHLIST_DEMAND_SIGNAL:
        event = WatchlistDemandEvent.from_signal_value(signal.value)
        return _generic_signal_record(
            run_id,
            sequence,
            signal,
            event_type="watchlist.demand",
            source=event.owner_id,
            schema_version=event.schema_version,
            correlation_id=event.demand_id,
        )
    if signal.name == WATCHLIST_LIFECYCLE_SIGNAL:
        event = WatchlistLifecycleEvent.from_signal_value(signal.value)
        return OperationalEventRecord(
            event_id=event.event_id,
            run_id=run_id,
            sequence=sequence,
            signal_name=signal.name,
            event_type="watchlist.lifecycle",
            source=event.source,
            correlation_id=event.correlation_id,
            causation_id=None,
            payload=json.loads(signal.value),
            ts_event_ns=signal.ts_event,
            ts_init_ns=signal.ts_init,
            schema_version=event.schema_version,
        )
    if signal.name == COMPONENT_FAILURE_SIGNAL:
        event = ComponentFailureEvent.from_signal_value(signal.value)
        return _generic_signal_record(
            run_id,
            sequence,
            signal,
            event_type="component.failure",
            source=event.component,
            schema_version=event.schema_version,
        )
    if signal.name == ACQUISITION_STATUS_REQUEST_SIGNAL:
        event = AcquisitionStatusRequest.from_signal_value(signal.value)
        return _generic_signal_record(
            run_id,
            sequence,
            signal,
            event_type="acquisition.status_request",
            source=event.requester,
            schema_version=event.schema_version,
            correlation_id=f"acquisition-status-request:{sequence}",
        )
    if signal.name == ACQUISITION_STATUS_SIGNAL:
        event = AcquisitionStatusEvent.from_signal_value(signal.value)
        return _generic_signal_record(
            run_id,
            sequence,
            signal,
            event_type="acquisition.status",
            source=event.source,
            schema_version=event.schema_version,
        )
    if signal.name == ACQUISITION_STREAM_SIGNAL:
        event = AcquisitionStreamEvent.from_signal_value(signal.value)
        return _generic_signal_record(
            run_id,
            sequence,
            signal,
            event_type="acquisition.stream",
            source=event.source,
            schema_version=event.schema_version,
            correlation_id=event.demand_id,
        )
    raise ValueError(f"unsupported operational signal: {signal.name}")


def _generic_signal_record(
    run_id: UUID,
    sequence: int,
    signal: Signal,
    *,
    event_type: str,
    source: str,
    schema_version: int,
    correlation_id: str | None = None,
) -> OperationalEventRecord:
    return OperationalEventRecord(
        event_id=f"operational:{sequence}",
        run_id=run_id,
        sequence=sequence,
        signal_name=signal.name,
        event_type=event_type,
        source=source,
        correlation_id=correlation_id,
        causation_id=None,
        payload=json.loads(signal.value),
        ts_event_ns=signal.ts_event,
        ts_init_ns=signal.ts_init,
        schema_version=schema_version,
    )


def _record_state(record: PersistedRecord) -> str:
    if isinstance(record, HealthEventRecord):
        return record.event.state
    return record.event_type
