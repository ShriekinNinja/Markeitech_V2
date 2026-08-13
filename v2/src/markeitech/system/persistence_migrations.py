from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    sql: str


MIGRATIONS = (
    Migration(
        version=1,
        name="operational_runtime_history",
        sql="""
            CREATE TABLE runtime_runs (
                run_id UUID PRIMARY KEY,
                runtime_id TEXT NOT NULL,
                started_at_ns BIGINT NOT NULL,
                ended_at_ns BIGINT,
                terminal_state TEXT,
                terminal_reason TEXT,
                schema_version INTEGER NOT NULL
            );

            CREATE TABLE system_health_events (
                event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                run_id UUID NOT NULL REFERENCES runtime_runs(run_id),
                sequence BIGINT NOT NULL,
                signal_name TEXT NOT NULL,
                state TEXT NOT NULL,
                reason TEXT NOT NULL,
                source TEXT NOT NULL,
                evidence_json JSONB NOT NULL,
                ts_event_ns BIGINT NOT NULL,
                ts_init_ns BIGINT NOT NULL,
                recorded_at_ns BIGINT NOT NULL,
                schema_version INTEGER NOT NULL,
                UNIQUE (run_id, sequence)
            );

            CREATE INDEX system_health_events_state_time_idx
                ON system_health_events (state, ts_event_ns);
            CREATE INDEX system_health_events_source_time_idx
                ON system_health_events (source, ts_event_ns);
        """,
    ),
    Migration(
        version=2,
        name="generic_operational_event_ledger",
        sql="""
            CREATE TABLE operational_events (
                event_id TEXT NOT NULL,
                run_id UUID NOT NULL REFERENCES runtime_runs(run_id),
                sequence BIGINT NOT NULL,
                signal_name TEXT NOT NULL,
                event_type TEXT NOT NULL,
                source TEXT NOT NULL,
                correlation_id TEXT,
                causation_id TEXT,
                payload_json JSONB NOT NULL,
                ts_event_ns BIGINT NOT NULL,
                ts_init_ns BIGINT NOT NULL,
                recorded_at_ns BIGINT NOT NULL,
                schema_version INTEGER NOT NULL,
                PRIMARY KEY (run_id, event_id),
                UNIQUE (run_id, sequence)
            );

            CREATE INDEX operational_events_type_time_idx
                ON operational_events (event_type, ts_event_ns);
            CREATE INDEX operational_events_source_time_idx
                ON operational_events (source, ts_event_ns);
            CREATE INDEX operational_events_correlation_idx
                ON operational_events (correlation_id)
                WHERE correlation_id IS NOT NULL;
        """,
    ),
)
