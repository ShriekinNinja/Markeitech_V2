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

Migration 3 adds `evidence_recency_profiles`. This is compact derived control state rather than raw
market data: one current profile per instrument, feed, selector, provider, session phase, and policy
version. Profiles let evidence health resume with observed delivery cadence after restart while
policy-version isolation prevents incompatible settings from silently reusing old learning.

The persistence actor consumes existing acquisition requests, acquisition status and stream
lifecycle, component failures, evidence recency checkpoints, and static watchlist membership and
lifecycle signals through one ordered bounded worker. The worker writes bounded batches in one
transaction and reserves configured admission capacity for health and failure records. It records
semantic control history only; native quote and bar callbacks remain outside PostgreSQL.

Nautilus signals are transient rather than retained. Runtime startup therefore has two persistence
guarantees. Process preflight verifies PostgreSQL and migrations before the node is built. Inside
the node, the persistence actor publishes a versioned readiness fact only after its worker is
running, all audited signal subscriptions are installed, and its Nautilus `on_start` callback has
returned. System control, acquisition, and watchlist actors request and wait for that fact before
publishing startup events.

This ordering preserves acquisition `REQUESTED`, `ACCEPTED`, and `SUBSCRIBED` events before the
first market observation can produce `ACTIVE`. It does not turn readiness chatter or raw market
callbacks into database records.

## Normal Operation

The **Markeitech V2** PyCharm run configuration starts the local PostgreSQL service, waits until it
is healthy, and then starts Markeitech. This remains the only run configuration required.

The service configuration is `compose.yaml`. Local credentials and the application DSN live in
the Git-ignored `.env`:

- `MARKEITECH_POSTGRES_PASSWORD`
- `MARKEITECH_POSTGRES_DSN`

Docker Desktop must be running. PostgreSQL remains running after Markeitech stops, and its data is
kept in the `v2_markeitech-postgres` Docker volume.

## Startup And Shutdown Truth

Before connecting to IB, Markeitech:

1. connects to PostgreSQL;
2. reapplies idempotent schema definitions under an advisory lock, repairing missing tables and
   indexes even when their migration versions were already recorded;
3. verifies every required table and column, failing startup on incompatible schema drift;
4. confirms the persistence actor can connect; and
5. opens the runtime run record.

`READY` requires both configured instrument definitions and operational persistence readiness.
During shutdown, the actor records `STOPPING`. The CLI records `STOPPED` only after Nautilus has
fully returned. An unclosed run is intentional evidence of a crash, forced kill, or failed terminal
write.

## Failure Behavior

- Startup database failure prevents IB startup and prevents `READY`.
- Normal admissions cannot consume the queue capacity reserved for health and failure records.
- A persistence admission rejection is reported once to the control actor and produces
  `DEGRADED`; the persistence actor never defines system state.
- An unresolved persistence failure prevents a later readiness evaluation from overwriting the
  degraded or failed state.
- Accepted writes drain in order during bounded shutdown.
- Duplicate `(run_id, sequence)` writes are ignored by a PostgreSQL uniqueness constraint.

## Manual Service Commands

From ``:

```bash
docker compose up -d --wait postgres
docker compose ps
docker compose stop postgres
```

Do not run `docker compose down --volumes` unless the PostgreSQL history is intentionally being
destroyed.
