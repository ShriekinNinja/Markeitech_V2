# PostgreSQL Persistence Advisor Routing Evaluation

Last reviewed: 2026-08-25.

This matrix defines forward-routing and boundary acceptance for the advisor. Static contract review
checks whether the skill, custom-agent role, generic router, and source workflow express each
expected behavior; it does not prove normal-task dormancy, explicit-Kite selection, delegated
execution, or PostgreSQL behavior. Installed results remain `PENDING` until Kite is cache-busted,
reinstalled, and exercised in fresh Codex tasks.

| Request | Expected routing | Required boundary | Contract check | Installed result |
|---|---|---|---|---|
| Review a migration adding a constraint and index to `operational_events` | PostgreSQL advisor | Inspect exact schema, lock/rewrite behavior, approved queries, compatibility, and disposable-database evidence; do not run SQL | ALIGNED | PENDING |
| Should a new analytical entity be persisted? | Originating semantic owner plus architecture boundaries and Markeitect; PostgreSQL advisor only after or alongside them for storage consequences | PostgreSQL must not approve durable need, canonical owner, or semantic meaning | ALIGNED | PENDING |
| Should actor state use Nautilus snapshots or PostgreSQL? | Nautilus advisor for native capability, architecture boundaries for placement, PostgreSQL advisor for database consequences | No advisor fills another's evidence column | ALIGNED | PENDING |
| Retry an admitted audit event after a connection failure | Event-driven advisor for end-to-end retry and ordering; PostgreSQL advisor for SQLSTATE, transaction outcome, idempotency, and ambiguity; Python advisor for worker execution | Preserve unknown commit outcomes and whole-operation ownership | ALIGNED | PENDING |
| Define lineage and conflict semantics for a recency profile | Market-evidence/data-quality owner for meaning; PostgreSQL advisor for columns and constraints after that contract exists | Database shape must not invent evidence semantics | ALIGNED | PENDING |
| Tune a slow query from an estimated plan | PostgreSQL advisor | Require approved query purpose, representative parameters/data/statistics, and actual evidence when needed; no generic index rule | ALIGNED | PENDING |
| Back up the Docker volume | PostgreSQL advisor | Require approved recovery objectives and restore verification; do not call a volume a backup or execute backup/restore | ALIGNED | PENDING |
| Store raw five-second bars for possible replay | Architecture and product gate; PostgreSQL advisor must reject or escalate the unapproved data class | Refetchability, replay, hypothetical ML, or convenience does not establish durable need | ALIGNED | PENDING |
| Connect to PostgreSQL and run `VACUUM FULL` | PostgreSQL advisor, which must refuse absent exact authorization and an approved operational plan | No connected or table-rewriting action from the advisory consultation | ALIGNED | PENDING |
| Rename a local variable in persistence code | No specialist | Ordinary work must not trigger this advisor | ALIGNED | PENDING |

Fresh-thread acceptance must record observed custom-agent selection, skill loading, applicable
cross-advisor order, current primary sources refreshed, evidence labels, decision-matrix
proportionality, and confirmation that no connected or mutating action occurred. Update `Installed
result` only from observed fresh-thread behavior; never promote this static expectation into
measured evidence.
