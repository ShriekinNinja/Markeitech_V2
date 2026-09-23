---
name: markeitech-quantitative-metric-validation-expert
description: Check a specific metric formula, units, warmup, rolling window, aggregation, numerical behavior, or causal cutoff using independent examples and the accepted definition.
---

# Quantitative Metric Validation

Use this guidance directly in the current task. Inspect the affected code, contract, and tests;
reuse current evidence already established in the task. A skill adds no edit, connection, or
approval authority. Review requests and delegated reviews remain read-only.

Work only on the requested outcome. Read supporting references only for a named uncertainty;
apply the relevant sections, not a whole audit by default. The primary agent may combine checks
from other skills directly. Do not require separate specialist dispositions or create handoffs.
Expand scope only for a concrete defect or missing fact that can change this result, explain why,
and preserve the user's approval boundaries. Stop only the unsupported conclusion.

## Checks For This Question

- State the equation, input basis, units, window edges, warmup/reset, missing-value rule, and causal cutoff that matter to this metric.
- Trace source quality separately from the calculation. A math fix does not establish provider coverage or trading usefulness.
- Use a small independent oracle or invariant for changed behavior; avoid tests that merely reproduce the implementation.
- Check native/library parity only when relevant, recording semantic differences. Visual resemblance and shared-code agreement are insufficient.
- Report exactly what is established: definition correctness, implementation parity, numerical robustness, causal validity, or a narrower subset.

## Optional References

- [validation-contract.md](references/validation-contract.md) — use for the matching numerical or causal failure mode.
- [sources.md](references/sources.md) — use for a formula or library contract requires primary evidence.

Return the finding or recommendation, its supporting evidence, the smallest correction or
next check, and material uncertainty. Distinguish verified behavior, measured evidence, and
inference. Use tables only when they clarify the actual decision; omit empty audit sections.
