---
name: markeitech-python-runtime-expert
description: Diagnose Python cancellation, task or worker ownership, shutdown, concurrency, import boundaries, or measured resource behavior. Skip broad architecture review for local fixes.
---

# Python Runtime

Use this guidance directly in the current task. Inspect the affected code, contract, and tests;
reuse current evidence already established in the task. A skill adds no edit, connection, or
approval authority. Review requests and delegated reviews remain read-only.

Work only on the requested outcome. Read supporting references only for a named uncertainty;
apply the relevant sections, not a whole audit by default. The primary agent may combine checks
from other skills directly. Do not require separate specialist dispositions or create handoffs.
Expand scope only for a concrete defect or missing fact that can change this result, explain why,
and preserve the user's approval boundaries. Stop only the unsupported conclusion.

## Checks For This Question

- Inspect the affected function, caller, cleanup path, and nearby tests in the actual interpreter/package version.
- Check cancellation propagation, awaited task completion, exception observation, and cleanup ownership for the reported failure.
- Verify framework-specific callbacks or threading guarantees from their exact contract when needed; generic asyncio knowledge does not establish them.
- Prefer a local correction within the accepted lifecycle. New queues, executors, dependencies, or timeout policy need a concrete reason.
- Claim performance improvement only from representative measurements; annotations do not prove runtime validation or thread safety.

## Optional References

- [review-protocol.md](references/review-protocol.md) — use for a specific concurrency, package, or resource investigation.
- [evidence-and-sources.md](references/evidence-and-sources.md) — use for interpreter or measurement evidence is disputed.
- [source-census.md](references/source-census.md) — use for locating current Python documentation.

Return the finding or recommendation, its supporting evidence, the smallest correction or
next check, and material uncertainty. Distinguish verified behavior, measured evidence, and
inference. Use tables only when they clarify the actual decision; omit empty audit sections.
