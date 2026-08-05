from __future__ import annotations

import os
from dataclasses import dataclass
from queue import Empty, Full, Queue
from threading import Lock, Thread
from time import monotonic, sleep, time_ns
from typing import Protocol
from uuid import UUID, uuid4

import psycopg
from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId
from psycopg.types.json import Jsonb

from markeitech.system.messages import (
    COMPONENT_FAILURE_SIGNAL,
    SYSTEM_HEALTH_SIGNAL,
    ComponentFailureEvent,
    SystemHealthEvent,
)
from markeitech.system.persistence_migrations import MIGRATIONS

PERSISTENCE_SCHEMA_VERSION = 1
_MIGRATION_LOCK_ID = 4_873_274_823
_RESULT_TIMER = "operational-persistence-results"
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


class HealthEventWriter(Protocol):
    def __call__(self, record: HealthEventRecord) -> None: ...


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
                    if migration.version in applied:
                        continue
                    cursor.execute(migration.sql)
                    cursor.execute(
                        "INSERT INTO markeitech_schema_migrations (version, name) VALUES (%s, %s)",
                        (migration.version, migration.name),
                    )

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

    def _connect(self):  # noqa: ANN202
        return psycopg.connect(
            self._dsn,
            connect_timeout=self._connect_timeout_seconds,
        )


class PersistenceWorker:
    def __init__(
        self,
        writer: HealthEventWriter,
        queue_capacity: int,
        shutdown_timeout_seconds: int,
        write_max_attempts: int,
        write_retry_backoff_ms: int,
    ) -> None:
        self._writer = writer
        self._shutdown_timeout_seconds = shutdown_timeout_seconds
        self._write_max_attempts = write_max_attempts
        self._write_retry_backoff_seconds = write_retry_backoff_ms / 1_000
        self._pending: Queue[HealthEventRecord | object] = Queue(maxsize=queue_capacity)
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

    def submit(self, record: HealthEventRecord) -> bool:
        if self._closed:
            self._increment("_rejected")
            return False
        try:
            self._pending.put_nowait(record)
        except Full:
            self._increment("_rejected")
            return False
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
                assert isinstance(item, HealthEventRecord)
                self._write_with_retries(item)
            finally:
                self._pending.task_done()

    def _write_with_retries(self, record: HealthEventRecord) -> None:
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
                        state=record.event.state,
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
                    state=record.event.state,
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
        self._subscribed = False
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
            store.write_health_event,
            self._queue_capacity,
            self._shutdown_timeout_seconds,
            self._write_max_attempts,
            self._write_retry_backoff_ms,
        )
        self._worker.start()
        self.subscribe_signal(SYSTEM_HEALTH_SIGNAL)
        self._subscribed = True
        self.clock.set_timer_ns(
            _RESULT_TIMER,
            self._result_poll_interval_ns,
            callback=self._drain_results,
        )
        self.log.info(f"OPERATIONAL_PERSISTENCE_READY | run_id={self._run_id}")

    def on_signal(self, signal: Signal) -> None:
        if self._worker is None:
            self._report_failure("persistence_worker_unavailable", "not_started")
            return
        try:
            event = SystemHealthEvent.from_signal_value(signal.value)
        except ValueError as exc:
            self._report_failure("invalid_system_health_event", type(exc).__name__)
            return
        self._sequence += 1
        record = HealthEventRecord(
            run_id=self._run_id,
            sequence=self._sequence,
            event=event,
            ts_event_ns=signal.ts_event,
            ts_init_ns=signal.ts_init,
        )
        if not self._worker.submit(record):
            self._report_failure("persistence_queue_unavailable", "queue_full_or_closed")

    def on_stop(self) -> None:
        if self._subscribed:
            self.unsubscribe_signal(SYSTEM_HEALTH_SIGNAL)
            self._subscribed = False
        if _RESULT_TIMER in self.clock.timer_names():
            self.clock.cancel_timer(_RESULT_TIMER)
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
                    f"OPERATIONAL_EVENT_STORED | sequence={result.sequence}"
                    f" | state={result.state}",
                )
            else:
                self._report_failure(
                    "health_event_write_failed",
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
