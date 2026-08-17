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
            CREATE TABLE IF NOT EXISTS runtime_runs (
                run_id UUID PRIMARY KEY,
                runtime_id TEXT NOT NULL,
                started_at_ns BIGINT NOT NULL,
                ended_at_ns BIGINT,
                terminal_state TEXT,
                terminal_reason TEXT,
                schema_version INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS system_health_events (
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

            CREATE INDEX IF NOT EXISTS system_health_events_state_time_idx
                ON system_health_events (state, ts_event_ns);
            CREATE INDEX IF NOT EXISTS system_health_events_source_time_idx
                ON system_health_events (source, ts_event_ns);
        """,
    ),
    Migration(
        version=2,
        name="generic_operational_event_ledger",
        sql="""
            CREATE TABLE IF NOT EXISTS operational_events (
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

            CREATE INDEX IF NOT EXISTS operational_events_type_time_idx
                ON operational_events (event_type, ts_event_ns);
            CREATE INDEX IF NOT EXISTS operational_events_source_time_idx
                ON operational_events (source, ts_event_ns);
            CREATE INDEX IF NOT EXISTS operational_events_correlation_idx
                ON operational_events (correlation_id)
                WHERE correlation_id IS NOT NULL;
        """,
    ),
    Migration(
        version=3,
        name="evidence_recency_profiles",
        sql="""
            CREATE TABLE IF NOT EXISTS evidence_recency_profiles (
                instrument_id TEXT NOT NULL,
                feed_kind TEXT NOT NULL,
                selector TEXT NOT NULL,
                provider_id TEXT NOT NULL,
                session_phase TEXT NOT NULL,
                policy_version TEXT NOT NULL,
                sample_count BIGINT NOT NULL,
                mean_interval_ms DOUBLE PRECISION NOT NULL,
                variance_ms2 DOUBLE PRECISION NOT NULL,
                last_observed_ns BIGINT NOT NULL,
                fresh_for_ms BIGINT NOT NULL,
                stale_after_ms BIGINT NOT NULL,
                unavailable_after_ms BIGINT NOT NULL,
                source_run_id UUID NOT NULL REFERENCES runtime_runs(run_id),
                updated_at_ns BIGINT NOT NULL,
                schema_version INTEGER NOT NULL,
                PRIMARY KEY (
                    instrument_id, feed_kind, selector, provider_id,
                    session_phase, policy_version
                )
            );

            CREATE INDEX IF NOT EXISTS evidence_recency_profiles_updated_idx
                ON evidence_recency_profiles (updated_at_ns);
        """,
    ),
)

REQUIRED_SCHEMA_COLUMNS = {
    "runtime_runs": frozenset(
        {
            "run_id",
            "runtime_id",
            "started_at_ns",
            "ended_at_ns",
            "terminal_state",
            "terminal_reason",
            "schema_version",
        },
    ),
    "system_health_events": frozenset(
        {
            "event_id",
            "run_id",
            "sequence",
            "signal_name",
            "state",
            "reason",
            "source",
            "evidence_json",
            "ts_event_ns",
            "ts_init_ns",
            "recorded_at_ns",
            "schema_version",
        },
    ),
    "operational_events": frozenset(
        {
            "event_id",
            "run_id",
            "sequence",
            "signal_name",
            "event_type",
            "source",
            "correlation_id",
            "causation_id",
            "payload_json",
            "ts_event_ns",
            "ts_init_ns",
            "recorded_at_ns",
            "schema_version",
        },
    ),
    "evidence_recency_profiles": frozenset(
        {
            "instrument_id",
            "feed_kind",
            "selector",
            "provider_id",
            "session_phase",
            "policy_version",
            "sample_count",
            "mean_interval_ms",
            "variance_ms2",
            "last_observed_ns",
            "fresh_for_ms",
            "stale_after_ms",
            "unavailable_after_ms",
            "source_run_id",
            "updated_at_ns",
            "schema_version",
        },
    ),
}
