---
name: markeitech-zero-dte-risk-expert
description: Review evidence-bound risk for an already named long single-leg 0DTE option candidate. Do not select trades, size positions, infer account risk, or authorize execution.
---

# Zero Dte Risk

Use this guidance directly in the current task. Inspect the affected code, contract, and tests;
reuse current evidence already established in the task. A skill adds no edit, connection, or
approval authority. Review requests and delegated reviews remain read-only.

Work only on the requested outcome. Read supporting references only for a named uncertainty;
apply the relevant sections, not a whole audit by default. The primary agent may combine checks
from other skills directly. Do not require separate specialist dispositions or create handoffs.
Expand scope only for a concrete defect or missing fact that can change this result, explain why,
and preserve the user's approval boundaries. Stop only the unsupported conclusion.

## Checks For This Question

- Require the exact candidate, long position side, quantity basis, timestamp, intended use, and supplied thesis; a call or put right does not establish position side.
- Preserve option mechanics, quote/Greek quality, liquidity limits, costs, expiry/settlement, and source-quality findings separately.
- Explain bounded scenario exposure and missing evidence without inventing affordability, fillability, suitability, portfolio risk, or trading edge.
- Use approved assumptions and units; risk classes or scenario shocks are policy proposals until accepted.

## Optional References

- [risk-review-protocol.md](references/risk-review-protocol.md) — use for a named candidate risk assessment.
- [adversarial-fixtures.md](references/adversarial-fixtures.md) — use for testing a changed risk assessment.
- [source-census.md](references/source-census.md) — use for current product or risk-source verification.

Return the finding or recommendation, its supporting evidence, the smallest correction or
next check, and material uncertainty. Distinguish verified behavior, measured evidence, and
inference. Use tables only when they clarify the actual decision; omit empty audit sections.
