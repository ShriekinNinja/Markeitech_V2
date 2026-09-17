---
name: markeitech-market-microstructure-order-flow-expert
description: Review trade/quote classification, BBO/NBBO, delta/CVD, books, liquidity, or effort-response evidence. Preserve observed versus inferred flow and bounded participant hypotheses.
---

# Market Microstructure Order Flow

Use this guidance directly in the current task. Inspect the affected code, contract, and tests;
reuse current evidence already established in the task. A skill adds no edit, connection, or
approval authority. Review requests and delegated reviews remain read-only.

Work only on the requested outcome. Read supporting references only for a named uncertainty;
apply the relevant sections, not a whole audit by default. The primary agent may combine checks
from other skills directly. Do not require separate specialist dispositions or create handoffs.
Expand scope only for a concrete defect or missing fact that can change this result, explain why,
and preserve the user's approval boundaries. Stop only the unsupported conclusion.

## Checks For This Question

- Identify feed, venue, instrument, conditions, timestamps, coverage, and the quote/trade alignment used.
- Distinguish aggressor classification from an observed exchange flag; specify unknown classification and coverage.
- Do not reconstruct historical delta from OHLCV or claim participant identity, motive, or position from prints.
- Check book depth and update semantics, trade corrections, crossed/locked markets, and session resets only when they affect the question.

## Optional References

- [domain-contract.md](references/domain-contract.md) — use for the matching flow, classification, or book question.
- [sources.md](references/sources.md) — use for feed or market rules require current primary evidence.

Return the finding or recommendation, its supporting evidence, the smallest correction or
next check, and material uncertainty. Distinguish verified behavior, measured evidence, and
inference. Use tables only when they clarify the actual decision; omit empty audit sections.
