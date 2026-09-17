---
name: markeitech-event-driven-architecture-expert
description: Inspect delivery, ordering, idempotency, retry, backpressure, or recovery for a named event path. Preserve accepted component ownership unless a concrete defect requires reconsideration.
---

# Event Driven Architecture

Use this guidance directly in the current task. Inspect the affected code, contract, and tests;
reuse current evidence already established in the task. A skill adds no edit, connection, or
approval authority. Review requests and delegated reviews remain read-only.

Work only on the requested outcome. Read supporting references only for a named uncertainty;
apply the relevant sections, not a whole audit by default. The primary agent may combine checks
from other skills directly. Do not require separate specialist dispositions or create handoffs.
Expand scope only for a concrete defect or missing fact that can change this result, explain why,
and preserve the user's approval boundaries. Stop only the unsupported conclusion.

## Checks For This Question

- Trace the affected producer, acceptance point, queue, consumer, acknowledgement, and effect.
- Distinguish receipt, acceptance, durable commit, and external delivery; do not claim exactly-once from a local send.
- Check the relevant duplicate, late, retry, cancellation, overload, or partial-failure case and identify its owner.
- Keep retry/resource policy explicit and preserve independent capabilities. Avoid adding a bus, supervisor, queue, or durable layer without a demonstrated need.

## Optional References

- [review-protocol.md](references/review-protocol.md) — use for the relevant delivery or failure mode.
- [source-census.md](references/source-census.md) — use for an external delivery guarantee needs verification.

Return the finding or recommendation, its supporting evidence, the smallest correction or
next check, and material uncertainty. Distinguish verified behavior, measured evidence, and
inference. Use tables only when they clarify the actual decision; omit empty audit sections.
