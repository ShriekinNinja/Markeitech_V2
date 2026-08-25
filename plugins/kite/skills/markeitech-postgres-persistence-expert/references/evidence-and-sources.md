# Evidence And Source Discipline

Apply this protocol to every consultation. A recorded census is orientation; refresh the relevant
primary source whenever the server, driver, schema, workload, or upstream guidance may have changed.

## Claim Labels

- **Verified fact:** directly established from current tracked authority, exact local code/schema,
  version-matched primary documentation, or an inspected database artifact whose provenance is
  known.
- **Measured evidence:** observed output from a named environment and workload, with timestamp,
  duration, data scale, settings, query parameters or redaction policy, and measurement method.
- **Inference:** a conclusion derived from verified facts or measurements; state the reasoning and
  plausible alternatives.
- **Hypothesis:** an explanation or risk that still needs a named falsification step.
- **Recommendation:** proposed action with rationale, alternatives, tradeoffs, approvals, and
  required acceptance.
- **Unknown:** unavailable, stale, ambiguous, or unverified information that could change the
  conclusion.

Do not promote a test assertion, migration name, documentation claim, estimated plan, log snippet,
or generic best practice to verified runtime behavior without the missing evidence.

## Source Priority

1. Current tracked Markeitech authority and accepted persistence decisions.
2. Current migration/schema definitions, persistence code, locked dependencies, exact server and
   driver versions, relevant tests, and schema/catalog snapshots.
3. Accepted runtime, query-plan, lock, capacity, backup, restore, and recovery measurements with
   provenance and bounded scope.
4. Version-matched PostgreSQL documentation and release notes.
5. Version-matched Psycopg documentation and local installed signatures/source.
6. PostgreSQL project or extension maintainer material for an already approved component.
7. Peer-reviewed or institutionally credible work when PostgreSQL primary sources do not answer a
   measurement or failure-model question.
8. Public agent skills only for packaging and review-workflow inspiration.

Search snippets, blogs, tuning checklists, generated SQL, and remembered behavior are discovery
leads, not authority. Prefer exact documentation sections and local executable contracts.

## Plan And Measurement Discipline

- `EXPLAIN` estimates; `EXPLAIN ANALYZE` executes. State whether the query can mutate data, trigger
  side effects, scan broadly, lock objects, reveal parameters, warm caches, or perturb statistics.
- A plan is scoped to query text and parameters, data distribution, schema/indexes, statistics,
  PostgreSQL version, settings, cache state, concurrency, and capture options. Do not generalize one
  plan beyond those conditions.
- Use actual versus estimated rows, loops, timing, buffers, WAL, I/O timing when enabled, temp use,
  planning time, execution time, locks, and repeated samples as applicable. Measurement overhead
  and cache effects remain explicit.
- Statistics views are cumulative and may reset. Record reset time, sampling interval, server
  version, enabled extensions/settings, and whether values cover unrelated workload.
- Query normalization can merge statements; logging or statement statistics can expose sensitive
  SQL or parameters. Apply explicit redaction, access, retention, and raw-market-data exclusions.

## Schema And Migration Evidence

For each schema change, inspect:

- exact before and after definitions, ownership, privileges, dependencies, constraints, indexes,
  defaults, generated expressions, functions/triggers, and extension requirements;
- lock level, table/index scan or rewrite, WAL, disk headroom, transaction behavior, concurrent DDL
  restrictions, timeout/cancellation, and partial-failure state;
- old/new application compatibility, deployment order, repair behavior, migration-ledger meaning,
  schema verification, rollback or roll-forward, and restart recovery;
- representative data scale and invalid legacy rows before adding or validating constraints.

`IF NOT EXISTS` proves only that the command did not create a conflictingly named object; inspect
catalog definitions to prove compatibility. Idempotent repair must converge to the approved schema
without destroying unexplained state.

## Backup And Recovery Evidence

Name the approved objective before selecting a mechanism:

- protected databases, roles, ownership, privileges, extensions, configuration, and encryption;
- recovery point and recovery time objectives;
- logical dump, filesystem/base backup, WAL archive/PITR, or approved managed mechanism;
- destination, immutability, access control, encryption, retention, monitoring, and failure alert;
- version/platform compatibility and required external secrets or configuration;
- restore procedure, integrity checks, application/schema verification, and dated restore drill.

A created archive, named volume, successful backup command, or presence of WAL is not recovery
proof. Recovery evidence requires a restore into an approved isolated target and verification of
the expected durable facts.

## Freshness Statement

For substantive output, state:

`Access date | tracked commit | declared image/server evidence | exact running server if known | driver version | documentation version/channel | unavailable or mismatched sources`

If exact running PostgreSQL is not inspected, say so. A `postgres:17-alpine` tag establishes the
declared major family, not the running patch release or image digest.
