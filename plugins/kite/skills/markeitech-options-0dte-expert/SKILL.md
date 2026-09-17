---
name: markeitech-options-0dte-expert
description: Check a named option contract, chain, quote/Greek set, expiration, exercise, settlement, or discovery requirement. Do not infer one product mechanics from another.
---

# Options 0Dte

Use this guidance directly in the current task. Inspect the affected code, contract, and tests;
reuse current evidence already established in the task. A skill adds no edit, connection, or
approval authority. Review requests and delegated reviews remain read-only.

Work only on the requested outcome. Read supporting references only for a named uncertainty;
apply the relevant sections, not a whole audit by default. The primary agent may combine checks
from other skills directly. Do not require separate specialist dispositions or create handoffs.
Expand scope only for a concrete defect or missing fact that can change this result, explain why,
and preserve the user's approval boundaries. Stop only the unsupported conclusion.

## Checks For This Question

- Verify exact underlying, class, expiry, strike, right, multiplier/deliverable, venue, and current product rules as needed.
- Distinguish SPX/SPXW from ETF option exercise and settlement; verify last-trade and broker cutoffs rather than infer from weekdays.
- Check quote age, spread, source/model and timestamp of Greeks, underlying alignment, and actual contract delivery.
- Keep theoretical value, quote, liquidity, fillability, suitability, and candidate risk distinct. Do not select or prefer a product without authority.

## Optional References

- [domain-contract.md](references/domain-contract.md) — use for the relevant option mechanics or evidence question.
- [review-protocol.md](references/review-protocol.md) — use for a requested broader option-evidence review.
- [source-census.md](references/source-census.md) — use for current exchange, OCC, OPRA, or broker sources.

Return the finding or recommendation, its supporting evidence, the smallest correction or
next check, and material uncertainty. Distinguish verified behavior, measured evidence, and
inference. Use tables only when they clarify the actual decision; omit empty audit sections.
