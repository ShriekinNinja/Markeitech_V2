---
name: markeitech-postgres-persistence-expert
description: Review a named PostgreSQL schema, migration, transaction, query, or recovery change after its durable purpose is established. A storage question does not authorize database access.
---

# Postgres Persistence

Use this guidance directly in the current task. Inspect the affected code, contract, and tests;
reuse current evidence already established in the task. A skill adds no edit, connection, or
approval authority. Review requests and delegated reviews remain read-only.

Work only on the requested outcome. Read supporting references only for a named uncertainty;
apply the relevant sections, not a whole audit by default. The primary agent may combine checks
from other skills directly. Do not require separate specialist dispositions or create handoffs.
Expand scope only for a concrete defect or missing fact that can change this result, explain why,
and preserve the user's approval boundaries. Stop only the unsupported conclusion.

## Checks For This Question

- Confirm the approved durable fact and query/recovery requirement; refetchable raw observations are not retained for convenience.
- Inspect the affected SQL, constraints, migration compatibility, transaction ownership, and relevant tests.
- Check idempotency and ambiguous commit outcomes, locks or rewrites, and retry scope where the change can affect them.
- Use actual plans and representative evidence for performance claims. EXPLAIN ANALYZE executes the statement.
- Keep connected/destructive operations behind their existing authorization and recovery requirements.

## Optional References

- [review-protocol.md](references/review-protocol.md) — use for the matching migration, query, transaction, or recovery question.
- [evidence-and-sources.md](references/evidence-and-sources.md) — use for database evidence or measurement limits matter.
- [source-census.md](references/source-census.md) — use for a PostgreSQL version-specific claim.

Return the finding or recommendation, its supporting evidence, the smallest correction or
next check, and material uncertainty. Distinguish verified behavior, measured evidence, and
inference. Use tables only when they clarify the actual decision; omit empty audit sections.
