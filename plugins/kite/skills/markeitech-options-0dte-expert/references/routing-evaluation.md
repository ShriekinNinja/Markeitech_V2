# Options And 0DTE Routing Evaluation

Use these cases to validate router selection and advisor handoffs after installation. They test
domain boundaries; they are not trading scenarios or approved product policy.

## Direct Options Coverage

| Request | Expected routing | Required behavior |
|---|---|---|
| Compare SPXW and SPY expiration, exercise, deliverable, and settlement mechanics | Options advisor | Refresh exact product sources, preserve exceptions, and do not prefer either product globally |
| Decide whether a named option quote and Greek set are fit for candidate-quality review | Options advisor | Require contract identity, source/model, timestamps, freshness, and explicit rejection reasons |
| Review whether a discovered chain is sufficiently exact and bounded | Options advisor | Separate definition capability, listed series, provider delivery, and actual observations |
| Review a vendor sweep/block interpretation | Options advisor | Guard option-specific identity and reject unsupported intent, positioning, or consolidated-flow claims |

## Negative Routing

| Request | Expected routing | Why |
|---|---|---|
| Define an ES swing, pivot, FVG, zone, or auction relationship | Market-structure advisor | Underlying price structure is not option-contract expertise |
| Review ordinary IB bar delivery with no option-specific decision | IB and, when applicable, Nautilus advisors | No options-domain decision is present |
| Validate a generic rolling metric formula or historical/live overlap | Quantitative-validation advisor for formula; data-quality advisor for overlap; evidence-fitness advisor only for a named downstream use | Formula, overlap integrity, and downstream fitness are distinct and are not option-product semantics |

## Required Multi-Advisor Handoffs

| Request | Expected routing | Ownership split |
|---|---|---|
| Discover SPXW/SPY/QQQ chains through the current IB account | Options plus IB advisors | Options owns exact contract/chain meaning; IB owns entitlement, delivery, request, and account/provider truth |
| Implement option discovery or quote subscriptions through Nautilus | Options plus IB plus Nautilus advisors | Options owns product evidence; IB owns provider truth; Nautilus owns installed adapter and runtime behavior |
| Normalize and retain vendor options-flow data | Options plus licensing coverage, and architecture/persistence advisors when material | Options guards semantics; other owners decide rights, storage, ownership, and schema |
| Validate GEX or dealer-positioning claims | Options plus data-quality, quantitative-validation, evidence-fitness, and approved statistical/microstructure specialists | Options guards contract/Greek inputs; it cannot supply missing position signs, methodology validation, or causal authority |

## Stop Or Refusal Cases

- A request to select a trade, side, size, entry, exit, or order must not produce trading or execution
  instructions.
- Margin, liquidation, exercise instructions, assignment handling, position limits, or automated
  action require separately approved execution/risk coverage.
- Tax, legal, regulatory, suitability, redistribution, non-display, or external-model rights require
  their qualified owner; unresolved coverage is a `MISSING` gate.
- An adjusted or exceptional contract without an exact current memo, deliverable, calendar, and
  provider identity must produce abstention and the smallest next evidence request.

## Acceptance Signals

The routing passes only when the options advisor is selected for the direct cases, not selected for
the negative cases, joined with every required co-owner, and unable to convert missing evidence into
trade, provider, architecture, licensing, execution, or statistical authority.
