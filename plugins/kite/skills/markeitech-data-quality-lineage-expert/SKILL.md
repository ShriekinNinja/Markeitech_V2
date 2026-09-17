---
name: markeitech-data-quality-lineage-expert
description: Check source identity, timestamps, sessions, coverage, duplicates, revisions, freshness, or lineage for identified evidence. Investigate only dimensions that can change the requested result.
---

# Data Quality Lineage

Use this guidance directly in the current task. Inspect the affected code, contract, and tests;
reuse current evidence already established in the task. A skill adds no edit, connection, or
approval authority. Review requests and delegated reviews remain read-only.

Work only on the requested outcome. Read supporting references only for a named uncertainty;
apply the relevant sections, not a whole audit by default. The primary agent may combine checks
from other skills directly. Do not require separate specialist dispositions or create handoffs.
Expand scope only for a concrete defect or missing fact that can change this result, explain why,
and preserve the user's approval boundaries. Stop only the unsupported conclusion.

## Checks For This Question

- Preserve provider, instrument/contract, clock domain, timezone/session, and source/filter/version where they affect meaning.
- Identify the expected population before claiming completeness; distinguish missing, conflicting, duplicate, revised, and stale observations.
- Do not silently fill gaps, merge possible duplicates, backdate availability, or upgrade inferred fidelity.
- Keep source quality separate from formula correctness and fitness for a named use. The same agent may check all three with their supporting evidence.

## Optional References

- [review-contract.md](references/review-contract.md) — use for a detailed lineage, time, revision, or coverage question.
- [sources.md](references/sources.md) — use for provider or standard semantics need verification.

Return the finding or recommendation, its supporting evidence, the smallest correction or
next check, and material uncertainty. Distinguish verified behavior, measured evidence, and
inference. Use tables only when they clarify the actual decision; omit empty audit sections.
