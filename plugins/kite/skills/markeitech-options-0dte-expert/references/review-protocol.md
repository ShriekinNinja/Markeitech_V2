# Options And 0DTE Review Protocol

## 1. Frame The Decision

State the exact question, decision owner, affected stage, products, provider, session, horizon,
expected output, and prohibited actions. Separate research, requirements, design, implementation
review, data audit, candidate-quality review, and trading interpretation.

Stop if the request actually asks this advisor to make a trade, architecture, provider, execution,
persistence, schema, legal, tax, or release decision.

## 2. Build A Source And Evidence Ledger

List each material claim with:

`Claim | Evidence label | Source | Access/as-of time | Product/contract scope | Fidelity | Limitations | Freshness required`

Use repository authority for Markeitech boundaries, current primary exchange/OCC/provider sources
for external mechanics, exact local contracts for executable behavior, and identified raw data for
measurements. Secondary education or research may explain mechanisms but cannot override current
specifications or prove provider delivery.

Stop when a material identity, settlement, session, entitlement, timestamp, timezone, field
meaning, or licensing fact is unresolved.

## 3. Complete The Product And Contract Matrix

For each compared product or contract include:

`Root/trading class | Underlying/settlement index | Provider ID | Venue | Expiry/trade date | Strike/right | Multiplier/deliverable | Exercise | Settlement | AM/PM | Sessions | Last trade | Evidence source`

Do not silently fill unknown cells from a similar product. Mark adjusted, non-standard, FLEX, and
exceptional-session series explicitly.

## 4. Audit Data Fitness

For every requested field verify semantic meaning, units, source, cadence, event/receive time,
freshness, session, null/sentinel handling, corrections, completeness, entitlement, and observed
provider delivery. Apply separate checks to:

- chain/series definitions;
- bid/ask/size/trading status;
- last sales, conditions, cancellations, and complex orders;
- volume and open interest as-of time;
- underlying/settlement references;
- IV and each Greek set; and
- vendor-derived labels, flow, surfaces, or exposure models.

A schema column, API type, or historical sample does not prove live delivery. A filtered sample
does not establish full-market coverage.

## 5. Audit Bounded Discovery And Candidate Quality

Confirm that expiry discovery uses the actual exchange trade date; strike discovery uses a named,
fresh reference; request breadth, cadence, lifetime, priority, and retry are bounded; irrelevant
demand is released; resource failure degrades independently; and every rejection has a typed
reason.

Evaluate affordability, tradeability, moneyness, Greeks, liquidity, payoff geometry, and remaining
time as separate dimensions. Preserve conflicts. Do not collapse them into a universal score or
allow a premium band to become direction, suitability, or product preference.

## 6. Classify All Variable Choices

For every proposed threshold, window, band, budget, cadence, weight, or selector record:

`Policy ID | Meaning/unit | Scope | Initial hypothesis | Allowed bounds/set | Step | Mutability | Source | Version/effective time | Optimization eligibility | Reject/expire/rollback behavior`

If defensible bounds or safe failure behavior are unknown, do not recommend implementation.

## 7. Challenge Interpretations

For every inference ask:

- What was directly observed?
- What coverage is missing?
- What alternate product, multi-leg, hedging, closing, liquidity, or timestamp explanation fits?
- Does the claim require participant identity or position signs the data does not contain?
- Would a different underlying reference, IV model, quote alignment, or expiration convention
  reverse the result?
- What evidence would falsify the hypothesis?

Abstain when independent dimensions conflict or evidence cannot support the requested specificity.

## 8. Escalate Cross-Domain Decisions

Use the boundaries in `domain-contract.md`. In particular, any consequential Nautilus or IB
adapter design requires the project Nautilus advisor before a custom behavior recommendation.
Provider licensing, automated execution, margin/liquidation, and legal/tax conclusions require
their own approved specialist coverage.

## 9. Define Acceptance Before Implementation

Recommend only the smallest offline proof needed for the decision. Candidate acceptance may
include deterministic contract fixtures, calendar/holiday/early-close cases, exact expiration and
adjustment identity, stale/crossed/missing quote rejection, Greek null/sentinel cases, bounded
resource lifecycle, provider-delivery evidence, and independent product-spec reconciliation.

Connected provider acceptance remains Markeitect-owned and separately authorized. Tests establish
only exercised scope; they do not prove live entitlements, fills, settlement, market impact, or
trading utility.

## Material Stop Gates

Stop before recommendation or implementation when any of these is material and unresolved:

- exact product/contract/expiry/deliverable/settlement identity;
- exchange trade date, timezone, session, holiday, early-close, or last-trade rule;
- named underlying reference and freshness;
- provider entitlement, field semantics, adapter delivery, or pacing/resource limits;
- quote timestamps, two-sided validity, or Greek/IV source and model meaning;
- volume/open-interest as-of time, OPRA/vendor coverage, corrections, or complex-order handling;
- redistribution, non-display, retention, or external-model licensing rights;
- a variable policy without bounded configuration and safe rejection behavior;
- an inference presented as observation, or a vendor/model estimate presented as positioning;
- an architecture, persistence, execution, risk, legal, tax, or regulatory decision lacking the
  required advisor and approval.

## Completion Checklist

- Findings are defect-first and ordered by severity.
- Verified facts, measured evidence, inference, hypothesis, recommendation, and unknown are
  visibly distinct.
- Product/session and evidence matrices are complete or explicitly unknown.
- No option instrument is globally preferred and no trade recommendation or execution logic is
  introduced.
- Flow is not treated as consolidated positioning; Greeks are not treated as observed truth.
- Variable choices are bounded/versioned policy candidates.
- Side effects, persistence, schema, resource, licensing, and operational effects are stated,
  including when there are none.
- Freshness and the smallest next evidence are reported.
