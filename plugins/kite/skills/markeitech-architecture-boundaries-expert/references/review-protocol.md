# Architecture Boundary Review Protocol

Use this protocol for consequential design advice or a defect-first boundary audit. Scale the
depth to the decision, but do not omit a material owner, canonical source, persistence effect, or
escalation.

## Questions To Ask Before Recommending

1. What exact user, operator, product, or runtime outcome is required?
2. What current failure, limitation, measured cost, or accepted future requirement creates the
   need? Is it verified, measured, inferred, hypothesized, or unknown?
3. Which tracked document governs this subject, and does current status say it is implemented,
   deferred, or unselected?
4. What fact or decision is at issue? What are its identity, scope, lifecycle, timestamps,
   fidelity, version, and authorized mutations?
5. Which component currently defines, mutates, transports, persists, restores, and projects it?
6. Which consumers depend on it, and which merely observe or format it?
7. Is the proposed owner already present in NautilusTrader or an existing Markeitech component?
   If the answer depends on Nautilus, has `markeitech_nautilus_advisor` returned current evidence?
8. Does the proposal create a second writer, state machine, cache, bus, wrapper, database,
   scheduler, retry policy, calendar, configuration source, or health truth?
9. Can reuse, composition, a narrower contract, or deletion solve the requirement with less
   authority and lower change cost?
10. Which specialist owns duplicate delivery, out-of-order delivery, partial failure, restart,
    shutdown, schema/version change, provider absence, and component-removal semantics, and what
    verified result does the boundary analysis consume?
11. Which parameters can vary, who may change them, and where are bounds, version, effective time,
    rollback, and audit defined?
12. What evidence would prove the design fit, and what acceptance remains operator-owned or
    connected?

## Authority And Evidence Census

Record, in precedence order:

| Source | Version or date | Scope | Evidence class | What it establishes | Limits or conflicts |
|---|---|---|---|---|---|

At minimum inspect tracked authority, implementation, tests, configuration, and available runtime
evidence relevant to the decision. Plans establish accepted intent, not implementation. Code shows
current behavior, not automatic approval. Tests prove only exercised cases. Logs and connected
runs are measurements bounded by their environment and date.

## Ownership Census

Create one row per concern or canonical fact:

| Concern or fact | Semantic owner | Mutation owner | Transport owner | Persistence owner | Recovery owner | Projection owner | Policy owner | Evidence | Conflict or gap |
|---|---|---|---|---|---|---|---|---|---|

Use named components and exact contracts. Do not use vague owners such as "the system," "the
backend," or "the database." If there is no owner, say `NONE`. If evidence is insufficient, say
`UNKNOWN` rather than selecting the most convenient candidate.

## Boundary Matrix

For every proposed change, produce:

| Requirement | Current owner/contract | Proposed owner/contract | Reuse or extension path | Duplicate-authority risk | Persistence/recovery effect | Change cost | Decision | Escalation or acceptance evidence |
|---|---|---|---|---|---|---|---|---|

Allowed decisions are `PRESERVE`, `REUSE`, `COMPOSE`, `NARROW_EXTENSION`, `REPLACE_WITH_MIGRATION`,
`REJECT`, `DEFER`, and `UNKNOWN`. A custom replacement requires an explicit rejection record for
every existing candidate.

## Architecture Drift Checks

Check for:

- tracked authority describing an owner or contract that code no longer implements;
- code implementing a future plan that current status still marks deferred;
- two components creating or mutating the same semantic fact;
- a consumer copying state and later acting as an independent authority;
- a projection, UI, Discord path, report, or agent recalculating market or system truth;
- a database, cache, log, or snapshot becoming a second configuration or canonical state source;
- event names or payloads that silently change meaning across versions;
- retries, pacing, freshness, lifecycle, or health decisions split across owners;
- wrapper types that rename native or existing contracts without adding approved meaning;
- persistent storage introduced for replay, backtesting, ML, convenience, or a hypothetical
  consumer rather than an approved live requirement;
- hidden constants that actually encode market, policy, resource, or operator choices; and
- architecture documents updated to claim acceptance that tests or live evidence do not prove.

Lead with concrete defects ordered by impact. Continue beyond the first finding. A missing diagram,
fashionable pattern, high coupling metric, or large file is not independently a boundary defect.

## Change-Cost Analysis

Evaluate cost across the lifecycle, not only implementation effort:

- code and contract changes;
- affected producers, consumers, tests, configuration, and documentation;
- data/schema migration, dual-read/write, reconciliation, rollback, and cleanup;
- operational services, secrets, backups, monitoring, on-call knowledge, and failure modes;
- provider entitlements, pacing, paid capacity, connected acceptance, and market-session timing;
- resource use and bounded-state implications;
- compatibility and deployment coordination;
- reversibility and the cost to remove the new boundary; and
- future constraint: which otherwise-local changes would now require cross-owner coordination.

Use `LOW`, `MEDIUM`, `HIGH`, or a bounded range only after stating assumptions. Separate one-time
change cost from continuing coordination and operational cost. Describe blast radius with the
actual affected owners and contracts.

## Unacceptable Shortcuts

- Do not infer an owner from a class name or folder location alone.
- Do not call a cache, table, event stream, or projection canonical without naming its authorized
  writer and question-specific scope.
- Do not recommend a new event bus, repository, service, wrapper, queue, database, or cache as a
  generic decoupling measure.
- Do not equate duplicated code with duplicated authority; conversely, do not excuse duplicated
  authority merely because implementations differ.
- Do not use DRY, SOLID, microservices, DDD, CQRS, or another pattern as a conclusion.
- Do not fabricate coupling metrics, story points, percentage savings, incident likelihood, or
  universal cost multipliers.
- Do not require three stakeholders, two signals, a fixed line threshold, or another generic quota
  when the actual decision can be supported more directly.
- Do not treat a historical document, passing unit test, screenshot, or single live run as broader
  proof than it is.
- Do not let an advisor approve architecture, mutate the repository, or expand permissions.

## Overlap And Escalation

- `markeitech_nautilus_advisor`: every Nautilus capability, installed-version, adapter, bus,
  lifecycle, cache, catalog, persistence, indicator, or native-versus-custom claim.
- Event-driven architecture specialist: event delivery, ordering, acknowledgement, duplication,
  idempotency, retry, reconciliation, cancellation, queues, backpressure, supervision, shutdown,
  restart, and partial-failure execution. This advisor owns topology and accountability, not those
  runtime semantics.
- PostgreSQL persistence specialist: schema objects, migrations, constraints, indexes, queries,
  transactions, locks, retention and deletion mechanics, backup, restore, and database
  observability. This advisor owns the logical durable boundary and change consequences.
- Data-quality and lineage specialist: provenance, identity, completeness, duplicates, conflicts,
  revisions, timestamps, timezones, session identity, staleness, and fidelity classifications.
  This advisor may assign their structural owners but may not define their meaning.
- Markeitech Python runtime expert: consequential asyncio, threading, GIL, typing, memory,
  profiling, package, or partial-failure implementation questions not owned by Nautilus.
- Live-agent governance specialist, when available through the advisor router: Sir Loke authority,
  tool policy, approvals, abstention, advisory-state semantics, configuration proposals, and agent
  failure containment. This advisor may map structural ownership and change consequences but may
  not define those semantics. If coverage is unavailable, use the router's missing-coverage gate.
- Product/trading specialist: signal meaning, market interpretation, opportunity semantics,
  option selection, or execution behavior.
- Provider/data specialist: entitlement, market-data fidelity, exchange/provider semantics,
  licensing, and paid-feed constraints.
- Security specialist: threat model, secrets, trust boundary, authorization, or security sign-off.
- Markeitect: architecture, infrastructure, persistence, schema, provider ownership, runtime
  policy, product semantics, trading, review, and release decisions.

If another specialist is missing, use the repository advisor router's missing-coverage gate. Do
not impersonate the absent domain.

## Output Contract

Deliver:

1. scope and domain contract;
2. authority and evidence census with explicit evidence labels;
3. ownership census and boundary matrix;
4. defect-first findings ordered by severity;
5. preserved strengths only where they affect the decision;
6. architecture drift and duplicated-authority assessment;
7. options and change-cost comparison;
8. persistence, schema, infrastructure, provider, runtime, configuration, and product-semantic
   effects, including explicit `NONE` entries;
9. overlap, escalations, stop gates, unknowns, and smallest resolving evidence; and
10. a recommendation plus the next approval or acceptance gate.

When the review finds no defect, say what scope and evidence were checked. Do not imply the whole
system is validated.
