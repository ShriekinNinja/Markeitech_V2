# Primary Source Census

Research snapshot: 2026-08-25. Refresh only the subset relevant to each consultation. URLs,
versions, image contents, and project contracts can drift; this census records source families and
guardrails, not permanent conclusions.

## Local Authority And Executable Contract

| Source | Snapshot | Use | Boundary |
| --- | --- | --- | --- |
| `AGENTS.md`, `markeitech.md`, `docs/current-status.md`, `docs/development-guidelines.md`, `docs/README.md` | commit `f029715ac17801d51012d7603cf4174db036d2c7` | Permissions, evidence bar, present storage boundary, authority order | Refresh in current checkout |
| `docs/architecture/v2-persistence-boundary-discovery.md` | same commit | Accepted operational-audit ownership and raw-observation exclusion | Initial discovery references older Nautilus RC; current status governs implementation |
| `docs/operations/v2-postgresql.md` and `docs/roadmap/v2-infrastructure-plan.md` | same commit | Implemented startup/repair/failure behavior and accepted foundation gates | Operations text is not a schema dump or live database measurement |
| `src/markeitech/system/persistence.py` and `persistence_migrations.py` | same commit | Exact migration, schema verification, transactions, identity collision, reads/writes | Inspect current files and all callers before advising |
| `tests/system/test_persistence.py` and `test_persistence_postgres.py` | same commit | Exercised record conversion, ordering, idempotency, restart reads, and missing-table recreation | Tests prove only covered fixtures and disposable-database paths |
| `compose.yaml` | same commit; declares `postgres:17-alpine` | Declared local PostgreSQL major family and volume | Floating tag does not prove running patch version or digest |
| `uv.lock` | same commit; locks Psycopg `3.3.4` | Exact packaged driver version | Lock does not prove imported version or runtime behavior |

At this snapshot, tracked authority says PostgreSQL stores runtime runs, system-health events,
generic operational events, and compact evidence-recency profiles; raw provider observations and
transient numerical metric values remain outside PostgreSQL. Reinspect rather than carrying this
inventory forward.

## PostgreSQL 17 Primary Documentation

The project declares PostgreSQL major 17. The official documentation site reported PostgreSQL
17.11 as the supported 17 release on 2026-08-25. Use the exact running `server_version` and image
digest when available; do not claim 17.11 merely from the documentation or floating image tag.

| Primary source | Access | What it supports | Guardrail |
| --- | --- | --- | --- |
| [Constraints](https://www.postgresql.org/docs/17/ddl-constraints.html) | PostgreSQL 17 docs; accessed 2026-08-25 | Check, not-null, unique, primary, foreign, exclusion, null and index side effects | Cross-row checks and mutable functions have documented hazards; match the real invariant |
| [Indexes](https://www.postgresql.org/docs/17/indexes.html) | PostgreSQL 17 docs; accessed 2026-08-25 | Index families, multicolumn/order/partial/covering choices and usage examination | Indexes add write/storage/maintenance cost; existence does not prove benefit |
| [`CREATE INDEX`](https://www.postgresql.org/docs/17/sql-createindex.html) and [`ALTER TABLE`](https://www.postgresql.org/docs/17/sql-altertable.html) | PostgreSQL 17 docs; accessed 2026-08-25 | Concurrent-build restrictions, DDL forms, validation, locks and compatibility questions | Inspect exact command and table state; do not generalize one DDL path |
| [Using `EXPLAIN`](https://www.postgresql.org/docs/17/using-explain.html) | PostgreSQL 17 docs; accessed 2026-08-25 | Estimated/actual plans, rows, loops, costs and execution evidence | `ANALYZE` executes; plans are parameter/data/statistics/settings specific |
| [Transaction isolation](https://www.postgresql.org/docs/17/transaction-iso.html) and [explicit locking](https://www.postgresql.org/docs/17/explicit-locking.html) | PostgreSQL 17 docs; accessed 2026-08-25 | MVCC anomalies, serialization, table/row/advisory locks and deadlocks | Application retry/idempotency and owner semantics remain project decisions |
| [PostgreSQL error codes](https://www.postgresql.org/docs/17/errcodes-appendix.html) | PostgreSQL 17 docs; accessed 2026-08-25 | SQLSTATE classes and condition names for database-error classification | SQLSTATE identifies the server condition, not whether the whole application operation is safe to retry |
| [Cumulative statistics](https://www.postgresql.org/docs/17/monitoring-stats.html) | PostgreSQL 17 docs; accessed 2026-08-25 | Activity, database/table/index/WAL/checkpointer and progress views | Stats are cumulative, permission-scoped, can reset, and may cover unrelated workload |
| [`pg_stat_statements`](https://www.postgresql.org/docs/17/pgstatstatements.html) | PostgreSQL 17 contrib docs; accessed 2026-08-25 | Normalized planning/execution statistics | Requires approved extension/configuration; overhead, resets, query text, and privacy matter |
| [Routine vacuuming](https://www.postgresql.org/docs/17/routine-vacuuming.html) | PostgreSQL 17 docs; accessed 2026-08-25 | Space reuse, planner stats, visibility map, wraparound and autovacuum | `VACUUM FULL` rewrites the table and takes an `ACCESS EXCLUSIVE` lock; it is never a default fix |
| [Backup and restore](https://www.postgresql.org/docs/17/backup.html) | PostgreSQL 17 docs; accessed 2026-08-25 | Logical dump, filesystem/base backup, continuous archiving and PITR families | Select from approved RPO/RTO and prove restore; a volume is not a backup |
| [Roles](https://www.postgresql.org/docs/17/user-manag.html), [privileges](https://www.postgresql.org/docs/17/ddl-priv.html), and [`pg_hba.conf`](https://www.postgresql.org/docs/17/auth-pg-hba-conf.html) | PostgreSQL 17 docs; accessed 2026-08-25 | Ownership, role membership, grants, authentication routing and least-privilege review | Security architecture and credential operations require separate approval/specialist input |
| [Error reporting and logging](https://www.postgresql.org/docs/17/runtime-config-logging.html) | PostgreSQL 17 docs; accessed 2026-08-25 | Destinations, collector behavior, fields and rotation-related questions | Logging can block, expose sensitive content, and consume storage; define policy first |

## Psycopg Primary Documentation

| Primary source | Version/access | What it supports | Guardrail |
| --- | --- | --- | --- |
| [Transaction management](https://www.psycopg.org/psycopg3/docs/basic/transactions.html) | site rendered as 3.3.5.dev1; accessed 2026-08-25; local lock is 3.3.4 | Default implicit transactions, context behavior, autocommit, savepoints, isolation and retry cautions | Version mismatch: verify installed 3.3.4 source/signatures for consequential claims |
| [Concurrent operations](https://www.psycopg.org/psycopg3/docs/advanced/async.html) | site rendered as 3.3.5.dev1; accessed 2026-08-25 | Connection/cursor sharing, serialized execution, shared transaction state, cancellation | Route Python execution ownership to the runtime advisor; driver support is not application safety |
| [Connection API](https://www.psycopg.org/psycopg3/docs/api/connections.html) | site rendered as 3.3.5.dev1; accessed 2026-08-25 | Exact connection and transaction options to verify locally | Do not substitute development docs for locked-runtime proof |
| [Errors API](https://www.psycopg.org/psycopg3/docs/api/errors.html) and [transaction status](https://www.psycopg.org/psycopg3/docs/api/pq.html#psycopg.pq.TransactionStatus) | site rendered as 3.3.5.dev1; accessed 2026-08-25 | Exception hierarchy, SQLSTATE lookup, and observable connection transaction state to verify against local 3.3.4 | Exception or client status alone may not establish a remote commit outcome; inspect locked source and preserve ambiguity |

## Institutionally Credible Secondary Families

Use only when primary docs and local evidence do not answer the question:

- PostgreSQL release notes and security notices for the exact major/patch under review.
- PostgreSQL Wiki operational material as secondary orientation, checked against version-matched
  official documentation.
- Maintainer documentation for an explicitly approved backup, pooling, monitoring, or audit
  component; never introduce one because its documentation is useful.
- Peer-reviewed database literature for isolation, recovery, benchmarking, or measurement methods,
  with PostgreSQL applicability stated rather than assumed.

## Rejected As Authority

- Generic index, cache-ratio, connection-count, `work_mem`, vacuum, or slow-query thresholds.
- Estimated plans without representative parameters/data/statistics and actual evidence when needed.
- Docker volume existence, backup command success, or WAL generation as restore/recovery proof.
- Search snippets, vendor marketing, generic DBA blogs, and public agent skills as PostgreSQL truth.
- The current custom schema as proof that its ownership or design is optimal.
