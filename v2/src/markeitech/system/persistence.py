from __future__ import annotations

import json
import os
from dataclasses import dataclass
from queue import Empty, Full, Queue
from threading import Thread
from time import monotonic, time_ns
from typing import Protocol
from uuid import UUID, uuid4

import psycopg
from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId
from psycopg.types.json import Jsonb

from markeitech.system.messages import SYSTEM_HEALTH_SIGNAL, SystemHealthEvent
from markeitech.system.persistence_migrations import MIGRATIONS

PERSISTENCE_FAILURE_SIGNAL = "markeitech.persistence.failure"
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
    error_code: str | None = None


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
    ) -> None:
        self._writer = writer
        self._shutdown_timeout_seconds = shutdown_timeout_seconds
        self._pending: Queue[HealthEventRecord | object] = Queue(maxsize=queue_capacity)
        self.results: Queue[PersistenceResult] = Queue()
        self._closed = False
        self._thread = Thread(
            target=self._run,
            name="markeitech-operational-persistence",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def submit(self, record: HealthEventRecord) -> bool:
        if self._closed:
            return False
        try:
            self._pending.put_nowait(record)
        except Full:
            return False
        return True

    def close(self) -> bool:
        if self._closed:
            return not self._thread.is_alive()
        self._closed = True
        deadline = monotonic() + self._shutdown_timeout_seconds
        try:
            self._pending.put(_STOP, timeout=max(0.0, deadline - monotonic()))
        except Full:
            return False
        self._thread.join(timeout=max(0.0, deadline - monotonic()))
        return not self._thread.is_alive()

    def _run(self) -> None:
        while True:
            item = self._pending.get()
            try:
                if item is _STOP:
                    return
                assert isinstance(item, HealthEventRecord)
                try:
                    self._writer(item)
                except Exception as exc:
                    self.results.put(
                        PersistenceResult(
                            sequence=item.sequence,
                            state=item.event.state,
                            stored=False,
                            error_code=type(exc).__name__,
                        ),
                    )
                else:
                    self.results.put(
                        PersistenceResult(
                            sequence=item.sequence,
                            state=item.event.state,
                            stored=True,
                        ),
                    )
            finally:
                self._pending.task_done()


class OperationalPersistenceActorConfig(DataActorConfig):
    def __new__(
        cls,
        run_id: str,
        dsn_env: str,
        connect_timeout_seconds: int,
        queue_capacity: int,
        result_poll_interval_ms: int,
        shutdown_timeout_seconds: int,
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
        return obj


class OperationalPersistenceActor(DataActor):
    def __init__(self, config: OperationalPersistenceActorConfig) -> None:
        super().__init__(config)
        self._run_id = UUID(config.run_id)
        self._dsn_env = config.dsn_env
        self._connect_timeout_seconds = config.connect_timeout_seconds
        self._queue_capacity = config.queue_capacity
        self._shutdown_timeout_seconds = config.shutdown_timeout_seconds
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
                self._report_failure("health_event_write_failed", result.error_code or "unknown")

    def _report_failure(self, reason: str, error_code: str) -> None:
        self.log.error(
            f"OPERATIONAL_PERSISTENCE_FAILED | reason={reason} | error={error_code}",
        )
        if self._failure_published:
            return
        self._failure_published = True
        self.publish_signal(
            PERSISTENCE_FAILURE_SIGNAL,
            json.dumps(
                {"reason": reason, "error_code": error_code, "run_id": str(self._run_id)},
                separators=(",", ":"),
                sort_keys=True,
            ),
        )
