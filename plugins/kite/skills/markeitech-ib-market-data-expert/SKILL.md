---
name: markeitech-ib-market-data-expert
description: Resolve a specific Interactive Brokers market-data request, entitlement, pacing, field, session, or provider error question from exact requests and current official evidence.
---

# Ib Market Data

Use this guidance directly in the current task. Inspect the affected code, contract, and tests;
reuse current evidence already established in the task. A skill adds no edit, connection, or
approval authority. Review requests and delegated reviews remain read-only.

Work only on the requested outcome. Read supporting references only for a named uncertainty;
apply the relevant sections, not a whole audit by default. The primary agent may combine checks
from other skills directly. Do not require separate specialist dispositions or create handoffs.
Expand scope only for a concrete defect or missing fact that can change this result, explain why,
and preserve the user's approval boundaries. Stop only the unsupported conclusion.

## Checks For This Question

- Capture the exact request, product, dated contract, delivery mode, timestamp, and provider response needed for the question.
- Classify request family, entitlement, pacing, session, and error semantics using the relevant current IB documentation.
- Verify Nautilus adapter exposure separately if the proposed correction depends on it. Provider documentation alone does not establish adapter delivery.
- Preserve delayed/frozen/live distinctions, explicit rollover, and unknown coverage. Never infer account mode or permission from a port or alias.
- Source inspection does not authorize an IB connection, entitlement change, or live probe.

## Optional References

- [provider-domain-playbook.md](references/provider-domain-playbook.md) — use for the matching IB request or error family.
- [evidence-and-workflow.md](references/evidence-and-workflow.md) — use for provider versus adapter evidence needs clarification.
- [source-census.md](references/source-census.md) — use for locating the relevant official source.

Return the finding or recommendation, its supporting evidence, the smallest correction or
next check, and material uncertainty. Distinguish verified behavior, measured evidence, and
inference. Use tables only when they clarify the actual decision; omit empty audit sections.
