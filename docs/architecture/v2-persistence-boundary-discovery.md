# V2 Persistence Boundary Discovery

**Status:** Initial Decision Gate 4 accepted on 2026-08-05; operational-audit scope expanded by
Markeitect on 2026-08-13.

**Scope:** The current V2 runtime and NautilusTrader `2.0.0rc1` installed in `.venv`.
This document recommends a boundary. It does not approve or implement a database.

## Executive Finding

V2 began with one small durable-information requirement: preserve an honest history of runtime
runs and system-health transitions. The accepted long-term boundary is broader: PostgreSQL must
preserve a full audit of meaningful system behavior. Raw market-data retention is not approved.
Replay and backtesting are outside current planning and must not justify speculative storage.

The storage decision should therefore stay split:

1. use a relational operational store for durable system intent, decisions, lifecycle, and
   outcomes; and
2. fetch reconstructable market data from IB when the live runtime needs it, and revisit durable
   market-data storage only after Markeitect approves a non-reconstructable live requirement.

Markeitect selected **PostgreSQL from the start**, behind one narrow persistence boundary. This
accepts the local service cost in exchange for a durable server-backed foundation that will not
need replacement when separately deployed consumers arrive. Redis, actor snapshots, logs, and
Parquet remain useful facilities, but none substitutes for the operational audit requirement.

## Current Durable-Information Inventory

| Information | Volume and writes | Required queries | Retention | Restart need | Recommendation |
|---|---|---|---|---|---|
| Runtime run identity and outcome | One row at start and one terminal update | Last run, incomplete runs, run duration and outcome | Indefinite; very small | Yes | Persist |
| `SystemHealthEvent` transitions | A few append-only rows per run | Timeline by run, state, source, and time | Indefinite; very small | Yes | Persist |
| Discord delivery attempts | Small but transport-specific | Only troubleshooting | Local logs are sufficient initially | No | Do not persist |
| IB instrument definitions | Small and replaceable | Current definition by instrument | Provider/cache concern | Re-request on restart | Do not own yet |
| TOML and environment configuration | One set per run | Reproduce effective configuration | Source and deployment concern | Reload from configuration | Do not copy into rows |
| Runtime logs | Append-only diagnostic text | Incident investigation and live tail | File rotation policy | No state restoration | Keep as files |
| Market ticks, bars, and books | Potentially high-volume streams | Not yet approved | Not yet approved | Not yet approved | Defer technology choice |
| Future analytics and actor state | Unknown | Unknown | Unknown | Unknown | Out of scope until designed |

The database must not become a second configuration source, a Discord outbox, an instrument
master, or an accidental market-data warehouse during this stage.

## Durable Audit Invariant

PostgreSQL is the authoritative audit ledger for meaningful system occurrences. As each V2
component is introduced, its persistence contract must cover:

- external and internal intents, including source, authority, correlation, and causation;
- policy decisions and their reasons;
- actor and component lifecycle transitions;
- provider requests, acceptance, rejection, cancellation, retry, and failure outcomes;
- subscription, freshness, readiness, degradation, and recovery transitions;
- derived analytics, semantic market events, agent conclusions, and recommendations;
- notification attempts and delivery outcomes; and
- later risk, option-selection, and execution decisions and outcomes.

This does not mean persisting every function call, log line, timer firing, or native callback.
Those are implementation diagnostics, not domain history. The audit must be sufficient to answer
what the system knew, requested, decided, changed, published, attempted, and observed as an
outcome, in order and with stable identities.

Raw ticks, quotes, bars, books, option-chain payloads, and other provider market observations stay
outside PostgreSQL. Their operational handling is still audited through bounded facts such as
request identity, first observation, watermark, count, freshness, gap, and terminal outcome.
Derived semantic events are system outputs and therefore belong in the audit even when their
evidence originated in transient market data.

## Exact Nautilus Facilities Reviewed

### Actor and node state

Actors expose save/load lifecycle support, and `LiveNode` exposes state load/save configuration.
This is appropriate for restoring a component snapshot. It does not provide an append-only,
queryable history of runtime transitions, and it should not be stretched into one.

### Cache configuration

The installed `CacheConfig` includes cache capacities, encoding, startup flushing, market-data
saving, and account-event persistence controls. Cache ownership is Nautilus runtime state. V2
should not assume that enabling cache persistence creates the operational schema or queries listed
above. Although Redis and PostgreSQL cache configuration types exist in the installed wheel, this
RC's Python `LiveNode` builder does not expose a way to attach those backings.

### Message-bus backing and external streams

The installed `MessageBusConfig` describes stream prefixes, external streams, per-topic streams,
filtering, trimming, and heartbeat behavior. Redis message-bus configuration types also exist, but
this RC's Python builder does not expose a way to attach the egress/ingress backing. These
facilities may become useful when Markeitech needs supported external event transport.

They do not currently give ordinary Python actors a public raw message-bus API, and the approved
system-health contract uses actor signals. Stage 4 should not introduce Redis or a custom bridge
merely to turn a transient signal into an operational database. Redis streams are transport and
bounded retention, not historical replay or a relational source of truth.

### Parquet catalog and streaming writers

`ParquetDataCatalog` supports native market data, custom data, queries, consolidation, and
deduplication. `StreamingFeatherWriter` supports high-volume stream persistence and rotation.
These facilities remain technically available, but they are not selected V2 storage.

They are a poor fit for transactional run closure, operational uniqueness constraints, schema
migrations, and simple queries such as "show the latest incomplete run." No Parquet layout or raw
market-data retention policy will be designed without a separately approved live requirement.

## Technology Comparison

| Option | Current fit | Strengths | Costs and limits | Decision |
|---|---|---|---|---|
| Local logs only | Insufficient | Already present; excellent diagnostics | Not structured state, weak queries, no uniqueness or migrations | Keep, not authoritative |
| Nautilus actor/node state | Insufficient alone | Native component recovery | Snapshot semantics, not operational history | Use later where actor recovery requires it |
| Redis/message streams | Unavailable and premature | External fan-out, retention, stream consumers | Python builder cannot attach the backing in this RC; not a relational source of truth | Defer |
| SQLite | Smallest current fit | Transactional, local, zero service burden, queryable | Requires replacement when separately deployed consumers arrive | Rejected by decision |
| PostgreSQL in Docker | Accepted | Concurrent clients, remote services, mature transactions and queries | Local container, credentials, migrations, backup, and availability become owned infrastructure | Use for operational records |
| Parquet/Feather | Unselected | Efficient immutable columnar data and Nautilus-native facilities | No approved live retention consumer; replay/backtesting are out of scope | Do not introduce |

## Recommended Ownership

The accepted runtime adds one `OperationalPersistenceActor`. It:

- subscribe to `markeitech.system.health` as a read-only consumer;
- own every operational write while Nautilus is running;
- move database work off the Nautilus event thread through one bounded actor-owned worker;
- preserve event order;
- expose failures through logs first, without redefining system state;
- close and drain within a bounded stop period; and
- never publish a second version of a health transition.

The outer CLI performs only the process-boundary writes that no stopped actor can truthfully own:
it initializes and migrates PostgreSQL before IB is built, opens the run immediately before
`LiveNode.run()`, and records `STOPPED` only after the node returns cleanly. No other actor executes
operational SQL. Read access should be added through a separate query boundary only when an actual
consumer exists.

## Implemented Initial Records

### `runtime_runs`

- `run_id`: generated UUID and primary key
- `runtime_id`: configured Nautilus runtime identity
- `started_at_ns`: process/run start time
- `ended_at_ns`: nullable terminal time
- `terminal_state`: nullable outcome known at closure
- `terminal_reason`: nullable human-readable reason
- `schema_version`: record contract version

### `system_health_events`

- `event_id`: generated primary key
- `run_id`: foreign key to `runtime_runs`
- `sequence`: monotonically increasing within the run
- `signal_name`: `markeitech.system.health`
- `state`, `reason`, `source`, and `evidence_json`: accepted event payload
- `ts_event_ns` and `ts_init_ns`: Nautilus signal timestamps
- `recorded_at_ns`: persistence timestamp
- `schema_version`: event contract version

A uniqueness rule on `(run_id, sequence)` provides idempotent insertion without changing the
approved system-health message contract. The persistence owner creates the run identifier and
sequence because no other current consumer needs them.

## Queries The First Schema Must Prove

- Return the latest run and whether it ended cleanly.
- Return the ordered health timeline for one run.
- Find runs with no terminal outcome.
- Filter health events by state, source, and time range.
- Retry an already accepted write without creating a duplicate row.

Anything beyond these queries needs a new requirement rather than a speculative column.

This restriction governed the initial schema only. New components now require explicit audit
records under the durable-audit invariant above; they must not be squeezed into the health-event
table or omitted merely because the first schema was intentionally narrow.

## Migration, Retention, And Backup

- Create a migration ledger before the first production row.
- Apply migrations before connecting to IB; a migration failure must prevent startup.
- Keep operational records indefinitely initially. Their volume is negligible.
- Keep PostgreSQL data in its named Docker volume and out of Git.
- Define backup and restore operations before the database contains records that cannot be
  reconstructed.
- Keep SQL and schema ownership inside the operational persistence boundary; do not build a
  generic storage framework.

## Accepted Decisions

1. Use PostgreSQL from the start. Docker Compose owns the local service definition.
2. PostgreSQL connectivity and migrations are mandatory before V2 can publish `READY` or connect
   to IB.
3. A mid-run persistence write failure is the first approved `DEGRADED` condition.
4. `STOPPING` remains an actor event. The CLI records `STOPPED` only after `LiveNode.run()` returns
   cleanly. A crash, forced kill, or failed terminal write leaves the run open and visibly
   incomplete.

## References

- [Nautilus cache](https://nautilustrader.io/docs/latest/concepts/cache/)
- [Nautilus message bus](https://nautilustrader.io/docs/latest/concepts/message_bus/)
- [Nautilus data and catalogs](https://nautilustrader.io/docs/latest/concepts/data/)
