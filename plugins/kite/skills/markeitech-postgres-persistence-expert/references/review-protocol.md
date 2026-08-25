# PostgreSQL Persistence Review Protocol

Select only the modes relevant to the request. This protocol is advisory and read-only; it does
not authorize SQL execution, migrations, repairs, retention, backup, restore, or infrastructure
changes.

## Common Intake

1. Restate the durable requirement, data class, explicit exclusions, query/recovery consumer,
   acceptance evidence, and authorized side effects.
2. Map the already approved semantic owner, durability decision, and logical persistence owner from
   the source fact through serialization, admission, transaction, durable row, read model,
   retention, recovery, and operator projection. Mark missing approval or ownership explicitly;
   do not assign it from the database layer.
3. Inventory exact PostgreSQL major/patch evidence, driver, migration mechanism, schemas, roles,
   extensions, settings that affect the decision, and current data scale.
4. Trace normal, duplicate, conflict, retry, overload, partial failure, ambiguous outcome, shutdown,
   crash, restart, repair, retention, backup, and restore paths. Settle only PostgreSQL transaction,
   constraint, lock, SQLSTATE, schema, and durable-state mechanics; route end-to-end delivery and
   runtime execution semantics to their owners.
5. Inspect current code, migrations, constraints, indexes, tests, and captured database evidence
   before proposing new objects or operations.

## Persistence Admission Mode

Build the required decision matrix and reject speculative storage. Architecture boundaries and
Markeitect approve the persisted class, logical durable need, canonical component owner, and
recovery meaning; the originating semantic owner defines the fact. This advisor verifies or marks
those inputs missing, then advises PostgreSQL mechanics. Verify:

- the durable consumer and why reconstruction is insufficient;
- operational fact versus provider observation, transient measurement, derived semantic state,
  configuration, log, projection, cache, or diagnostic sample;
- the approved canonical identity, revisions, ordering, event and record timestamps, source,
  correlation, causation, lineage, fidelity, schema/configuration version, and conflict semantics;
  route missing semantic meaning to the applicable market-evidence or domain owner;
- write/read volumes, growth bound, resource budget, retention, recovery, and access model;
- PostgreSQL consequences of the approved choice among the generic ledger, a current-state
  projection, or a separately approved specialized schema, including duplicate-authority risk;
  do not approve that logical placement from the database layer.

Do not accept raw provider observations by relabeling them as audit payloads. Audit their handling
through bounded lifecycle, watermark, count, freshness, gap, request, attempt, and outcome facts.

## Schema, Constraint, And Migration Mode

Check:

- primary/unique/foreign/check/exclusion constraints and null semantics against the real invariant;
- deterministic identity and collision detection, including same-identity/different-content cases;
- data types, units, UTC/internal timestamp representation, JSON structure and validation boundary,
  size limits, and schema/configuration versions;
- foreign-key delete/update actions, dependency direction, index support on referencing columns,
  and whether cascades preserve audit and retention policy;
- ordered migration identity, advisory-lock scope, transaction boundaries, repeat execution,
  schema-drift detection, compatible repair, and missing/corrupt ledger behavior;
- DDL lock/rewrite/scan/WAL/disk effects, concurrent-index restrictions, timeouts, deployment order,
  mixed-version compatibility, rollback/roll-forward, and restart behavior;
- legacy-row validation, backfill provenance, partial failure, resumability, and acceptance checks.

Idempotence means repeated execution converges to the approved definition. Name checks and
`IF NOT EXISTS` alone are insufficient; verify catalog definitions and fail closed on incompatible
drift. Never prescribe destructive repair merely because deterministic recreation is convenient.

## Query And Index Mode

Start from an approved query and representative scale, not an index idea. Record:

`Query purpose | Frequency/burst | Parameters/selectivity | Required order/limit | Existing constraints/indexes | Statistics freshness | Plan evidence | Lock/I/O/WAL | Recommendation | Recheck trigger`

Check predicate, join, ordering, grouping, limit, partition, JSON, and time-range semantics. Include
write amplification, storage, vacuum, cache, build/maintenance, and migration cost for each index.
Do not report every sequential scan, sort, heap fetch, unused index, or estimate error as a defect.
Require representative evidence and counter-evidence. Use a different evidence path to disprove
each candidate, such as catalog definition, alternative parameter set, actual call frequency,
constraint coverage, or repeated plan.

When recommending plan capture, keep it offline or on an explicitly approved disposable database.
`EXPLAIN ANALYZE` executes the statement; mutating SQL needs an approved safe wrapper or must not be
run. Production plan capture, broad scans, cold-cache tests, and configuration changes require
separate authorization.

## Transaction And Concurrency Mode

Define:

`Business operation | Connection owner | Transaction owner | Isolation | Lock/advisory-lock scope | Commit evidence | Retryable errors | Idempotency key/conflict rule | Ambiguous outcome | Shutdown/restart behavior`

Trace database atomicity, statement ordering, savepoints, isolation anomalies, explicit and advisory
locks, deadlock order, serialization failure, connection loss, cancellation, timeout, and database
retry scope. Event-driven architecture owns end-to-end admission, delivery order, acknowledgement,
duplication, retry, reconciliation, shutdown, restart, and partial-failure execution. Python runtime
owns worker, thread, queue, cancellation, and driver-integration execution outside database
semantics.
Do not retry only the failed statement when correctness requires replaying the whole transaction.
Do not infer rollback or commit from exception shape when the server outcome may be unknown.

For Psycopg, verify the locked version and actual context-manager/autocommit behavior. A connection
context, transaction context, cursor, statement, and database transaction are different boundaries.
Route Python thread/queue/shutdown mechanics to the Python runtime advisor.

## Retention, Backup, And Recovery Mode

Require an approved data lifecycle before designing deletion. Check legal/licensing and audit
holds, active/incomplete run protection, reference dependencies, quiescence, chunking, indexes,
locks, WAL, vacuum/bloat consequences, failure resumption, deletion identity, and durable outcome
audit. Treat all limits and cadences as bounded policy candidates.

For backup/recovery, compare logical dumps, physical/base backup, and WAL/PITR only against the
approved recovery objectives and local operating model. Record roles/ownership/extensions and
off-database configuration needed for recovery. A plan is incomplete without restore steps,
verification queries, application readiness checks, failure drills, and an owner/cadence.

## Observability And Troubleshooting Mode

Form a falsifiable question before collecting data. Choose the smallest source:

- application persistence counters and structured failures for admission/write truth;
- `pg_stat_activity` and lock views for current sessions, waits, blockers, and transaction state;
- cumulative database/table/index/WAL/checkpointer statistics with reset scope;
- `pg_stat_statements` only when approved, installed, configured, and safely retained;
- autovacuum/analyze progress and table statistics for maintenance questions;
- server logs only with an approved destination, fields, redaction, access, rotation, and retention;
- disk/WAL/connection headroom tied to an operator decision, not telemetry accumulation.

Never use a single cache-hit ratio, dead-tuple estimate, unused-index count, connection percentage,
or slow-query threshold as universal doctrine. Establish the workload, baseline, trend, saturation
point, and operator action. Avoid extensions, logging changes, resets, `ANALYZE`, vacuum, reindex,
or connected queries without approval.

## Code Review Mode

Review defect-first and continue beyond the first issue. Prioritize data loss/corruption, boundary
violations, false idempotency, migration/repair destruction, atomicity, identity collision,
unbounded retention, unrecoverable state, lock/deadlock risk, missing constraints, unsupported query
plans, observability gaps, then maintainability.

Each finding needs:

`Severity | Claim label | File/line or object | Trigger | Durable consequence | Evidence | Counter-evidence/disproof | Smallest safe correction | Verification | Approval gate`

Do not report stylistic SQL preferences or generic tuning advice as defects. Passing tests prove
only the exercised schema and paths; PostgreSQL-marked tests still do not prove production volume,
concurrency, backup, restore, recovery, or connected runtime behavior unless they exercised it.

## Completion Check

- Persisted classes and exclusions match tracked authority or remain explicitly unapproved.
- Semantic, logical durability, write/read, migration/repair, retention, and recovery owners are
  explicit without being assigned by PostgreSQL convenience.
- Identity, constraints, ordering, transaction, idempotency, conflict, retry, and failure semantics
  are inspectable.
- Approved queries and indexes have representative evidence and cost tradeoffs.
- DDL locking, compatibility, rollback/roll-forward, restart, and schema verification are covered.
- Retention and recovery have objectives, owners, bounded policy, and restore evidence requirements.
- Verified facts, measurements, inference, hypothesis, recommendations, and unknowns remain distinct.
- Architecture, semantic-evidence, event-driven, Nautilus, Python-runtime, approval, connected-run,
  resource, security, licensing, and operational handoffs are explicit.
