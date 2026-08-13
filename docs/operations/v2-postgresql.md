# V2 Operational PostgreSQL

## Purpose

The implemented schema currently stores runtime runs and system-health transitions. PostgreSQL is
the accepted V2 audit ledger: every new component must durably record its meaningful intents,
decisions, lifecycle transitions, publications, attempts, and outcomes.

PostgreSQL does not store raw ticks, quotes, bars, books, option-chain payloads, ordinary log
lines, or every internal callback. Raw market data remains transient. Its system-level handling,
including requests, readiness, freshness, gaps, retries, and failures, is audited.

Migration 2 adds the generic append-only `operational_events` ledger. Each event is idempotent by
`(run_id, event_id)`, ordered within its run, schema-versioned, and retains source plus optional
correlation and causation identity. A repeated identity with different content is corruption and
must fail visibly. Specialized health history remains intact; raw market payloads remain excluded.

## Normal Operation

The **Markeitech V2** PyCharm run configuration starts the local PostgreSQL service, waits until it
is healthy, and then starts Markeitech. This remains the only run configuration required.

The service configuration is `v2/compose.yaml`. Local credentials and the application DSN live in
the Git-ignored `v2/.env`:

- `MARKEITECH_POSTGRES_PASSWORD`
- `MARKEITECH_POSTGRES_DSN`

Docker Desktop must be running. PostgreSQL remains running after Markeitech stops, and its data is
kept in the `v2_markeitech-postgres` Docker volume.

## Startup And Shutdown Truth

Before connecting to IB, Markeitech:

1. connects to PostgreSQL;
2. applies pending versioned migrations under an advisory lock;
3. confirms the persistence actor can connect; and
4. opens the runtime run record.

`READY` requires both configured instrument definitions and operational persistence readiness.
During shutdown, the actor records `STOPPING`. The CLI records `STOPPED` only after Nautilus has
fully returned. An unclosed run is intentional evidence of a crash, forced kill, or failed terminal
write.

## Failure Behavior

- Startup database failure prevents IB startup and prevents `READY`.
- Mid-run queue or write failure is reported once to the control actor.
- The control actor publishes `DEGRADED`; the persistence actor never defines system state.
- Accepted writes drain in order during bounded shutdown.
- Duplicate `(run_id, sequence)` writes are ignored by a PostgreSQL uniqueness constraint.

## Manual Service Commands

From `v2/`:

```bash
docker compose up -d --wait postgres
docker compose ps
docker compose stop postgres
```

Do not run `docker compose down --volumes` unless the PostgreSQL history is intentionally being
destroyed.
