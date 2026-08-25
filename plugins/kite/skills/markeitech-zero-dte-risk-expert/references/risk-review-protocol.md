# Zero DTE Candidate Risk Review Protocol

Use this protocol to synthesize risk for supplied long, single-leg same-day-expiry option
candidates. It is not a contract-discovery, candidate-quality, affordability, trade-selection,
portfolio-management, or execution workflow.

## Review Mode

Choose the smallest mode that answers the request:

- `NARROW_LANE`: answer one supported risk question with evidence cutoff, dependencies,
  disposition, validity, and stop conditions.
- `COMPLETE_CANDIDATE`: review every material lane for one named candidate.
- `BOUNDED_SET`: apply `COMPLETE_CANDIDATE` independently to each candidate; do not collapse them
  into a universal score or preferred contract.

## Mandatory Input Census

Establish or mark unknown:

1. Review mode, exact downstream decision, evidence cutoff, and required fidelity.
2. Position context: supplied `LONG` side, `SINGLE_LEG` structure, candidate versus existing
   position, opening/closing context when relevant, and quantity only if supplied. Written,
   multi-leg, existing-position, and account-risk conclusions are outside v1.
3. Exact option root, OCC and local contract identifiers, trade date, expiration, strike, right,
   multiplier, currency, venue, exercise style, settlement method, settlement-value convention,
   and non-standard deliverable or adjustment state.
4. Exchange trade-date/session model, current phase, last eligible trade time, expiration and
   exercise cutoffs, holiday/early-close state, IANA timezone, and authoritative source/version.
5. Externally owned thesis, horizon, trigger, and thesis invalidation, or an explicit statement that
   the narrow risk question does not require them.
6. Canonical Options Intelligence candidate state, including eligibility, quality, affordability,
   tradeability, degradation, lifecycle, configuration identity, and source snapshot. This advisor
   does not recalculate the disposition.
7. Underlying/reference identity, reported/derived/proxy fidelity, price, event and receipt times,
   source, basis where applicable, and freshness-policy identity.
8. Quote evidence envelope: contract, source/provider, venue or consolidated scope, selector,
   entitlement/delivery mode, bid/ask, sizes, event and receipt timestamps, quote conditions,
   sequence ordering, corrections/revisions, coverage, and suppressed/dropped counts.
9. Spread metric ID/version, absolute formula and units, relative denominator and units, display
   conversion, observed/event age, receive age, and the exact freshness/stability policy.
10. IV and Greeks: provider/model, field semantics, units, option style, underlying reference,
    rates/dividends, event/receipt/calculation/as-of times, update trigger, revision policy,
    applicability, and evidence-validation disposition.
11. Scenario method when numerical scenarios are requested: model/version, applicability, inputs,
    spot/time/IV path and shocks, surface assumption, exercise treatment, precision/tolerance,
    independent check, invariants, and policy/configuration identity.
12. Official scheduled event and exchange-notice facts overlapping the remaining lifetime, with
    source, version, scheduled time, timezone, revision state, and access time.
13. Current public broker expiration, liquidation, exercise, and contrary-instruction policy when
    material. Keep account-specific treatment and buying power unknown without an approved owner.

Do not solicit credentials or unnecessary account data. Quantity may be used only for transparent
arithmetic after the per-contract result is supported; never recommend or approve it.

## Required Consultations

Return `REQUIRED_CONSULTATION` with the exact question and smallest evidence needed when a
conclusion depends on:

- option-series, exchange, quotation, exercise, settlement, or provider-field mechanics not already
  verified by the options-market mechanics owner;
- quote, timestamp, spread, stability, IV, Greek, formula, scenario, or lineage correctness not
  admitted by market-evidence validation;
- thesis direction, timing, or invalidation not supplied by its owner;
- prints, flow, open interest, or dealer-position inference;
- account exposure, buying power, margin, liquidation control, sizing, or suitability; or
- Nautilus, provider adapter, lifecycle, persistence, or implementation behavior.

## Lane Stop Gates

Stop only the affected lane and preserve independently supported findings when:

- position side/structure is absent for loss, assignment, exercise-obligation, or settlement-
  exposure conclusions;
- exact contract, expiry, multiplier, exercise style, settlement method, or deliverable is
  unresolved;
- the relevant product specification, session calendar, event calendar, or broker policy cannot
  be refreshed;
- quote identity, source scope, timestamps, executable comparison side, sizes, or multiplier is
  missing where the requested risk depends on them;
- the quote is stale, crossed, one-sided, zero-size, halted, materially unstable, or incomplete
  under the named reviewed policy;
- stability is inferred from one snapshot or a sequence with unknown suppression, loss, ordering,
  or coverage;
- spread percentage or quote age lacks a formula, denominator or clock, unit, and version;
- IV/Greeks lack source, semantics, units, timestamps, reference, model applicability, or a required
  validation disposition;
- a numerical scenario lacks a versioned applicable repricing method, shocks/path, independent
  check, or required invariants;
- the supplied thesis is absent and the request asks this advisor to invent or endorse it;
- the result would require affordability, tradeability, candidate-quality, ranking, portfolio,
  suitability, or execution authority; or
- a material contradiction remains unresolved.

Abstention is valid. A stopped quote-sensitive lane does not erase independently verified product
or expiry risks.

## Analysis Lanes

### 1. Scope, Identity, And Clock

Reconcile position context, exact series, exchange trade date, UTC timestamps, IANA timezone,
session phase, remaining eligible trading time, expiration, settlement observation, early close,
and evidence cutoff. Never transfer SPX/SPXW mechanics to SPY or QQQ.

### 2. Risk-Review Validity

State what evidence the review depends on and when it expires. Name invalidators such as quote or
Greek refresh, session transition, product correction, scheduled event release, broker-policy
change, owning-thesis invalidation, source degradation, or movement outside the reviewed scenario
envelope. Do not mutate thesis invalidation or canonical candidate lifecycle.

### 3. Convexity And Scenario Risk

Explain local delta, gamma, theta, vega/IV, moneyness, remaining-time, jump, halt, and missing-market
risks without treating Greek labels as a complete forecast.

Numerical scenarios require a versioned, applicable repricing method plus independent validation.
Provider-reported Greeks alone cannot authorize distant path P&L. If that gate is absent, use a
qualitative scenario and mark the numerical consequence `UNKNOWN`.

### 4. Quote And Liquidity Consequences

Consume the canonical candidate and market-evidence dispositions. State how spread, age, sequence
coverage, size, instability, or withdrawal limit the risk review. A displayed ask is a cash-outlay
comparison input, not a guaranteed fill. Do not recalculate affordability, tradeability, expected
slippage, fillability, or candidate quality.

### 5. Expiration, Exercise, Settlement, And Broker Unknowns

Using verified mechanics, state separately:

- European versus American exercise;
- cash versus physical settlement;
- multiplier, deliverable, and settlement-value source;
- early exercise or assignment possibility where applicable;
- expiration exercise and contrary-instruction risk;
- per-contract cash obligation or resulting share exposure for the supplied long candidate;
- public broker discretion and cutoff uncertainty; and
- account-specific treatment, buying power, and liquidation as `UNKNOWN` absent an approved owner.

Official product terms do not prove how a broker will manage a particular account.

### 6. Event And Operational Risk

Use official issuer, agency, exchange, and broker sources for scheduled facts. Treat direction,
magnitude, IV response, liquidity response, and gaps as scenarios, not facts. Include unscheduled
news, halts, feed loss, and quote withdrawal as unresolved exposure rather than predicted events.

### 7. Disclosure And Unknowns

For a supplied long candidate, disclose possible full premium loss, nonlinear and expiring
sensitivity, quote/model limitations, exercise/settlement consequences, broker and event unknowns,
and the assessment's expiry. Do not imply suitability, acceptance, ranking, or permission to trade.

## Dispositions

Each material lane must receive one:

- `SUPPORTED`: all material gates for the exact stated scope passed.
- `SUPPORTED_WITH_LIMITS`: usable only within named evidence, model, session, or validity limits.
- `NOT_VERIFIED`: missing evidence or independent validation prevents a defensible conclusion.
- `STOPPED`: a hard boundary or contradiction prohibits the requested conclusion.
- `NOT_APPLICABLE`: the lane cannot change the bounded decision; state why.

End a complete review with one overall advisory disposition:

- `RISK_REVIEW_COMPLETE`
- `RISK_REVIEW_COMPLETE_WITH_LIMITS`
- `ABSTAIN`
- `NOT_VERIFIED`

Aggregate deterministically:

- `RISK_REVIEW_COMPLETE` only when every material lane is `SUPPORTED`.
- `RISK_REVIEW_COMPLETE_WITH_LIMITS` only when every decision-critical lane is `SUPPORTED` or
  `SUPPORTED_WITH_LIMITS`, no lane is `STOPPED`, and every limit is explicit, bounded, and accepted
  by the downstream contract.
- `NOT_VERIFIED` when evidence or independent validation required for the requested risk conclusion
  is missing, stale, contradictory, or semantically insufficient.
- `ABSTAIN` when a hard boundary, unresolved material contradiction, expired validity envelope, or
  stopped decision-critical lane makes acting on the review indefensible.

`NOT_APPLICABLE` lanes do not lower the overall disposition when their irrelevance is stated and
they cannot change the bounded decision. Do not average or vote across lanes to conceal a hard gate.

These are review dispositions, not product approval, candidate acceptance, portfolio authorization,
or permission to trade.

## Output Contract

Begin with `Advisory risk analysis only`, the bounded conclusion, and overall disposition.

For `NARROW_LANE`, provide:

1. exact question, scope, and evidence cutoff;
2. evidence class and source identity;
3. lane disposition and bounded risk consequence;
4. validity/expiry and stop conditions; and
5. unknowns or required consultations.

For `COMPLETE_CANDIDATE` or `BOUNDED_SET`, provide:

1. exact candidate, long/single-leg position context, session, and evidence cutoff;
2. source and unavailable-input inventory;
3. `Lane | Disposition | Evidence class and identity | Risk consequence | Validity/expiry |
   Unknown or consultation` matrix;
4. qualitative or validated numerical convexity scenarios with method and limits;
5. quote/liquidity consequences without affordability or tradeability reclassification;
6. exercise, settlement, broker, event, and operational consequences;
7. disclosure, stop conditions, and review expiry;
8. policy candidates and unknowns; and
9. overall disposition.

Do not output an entry, exit, stop-loss, target, preferred contract, rank, position size, portfolio
allocation, probability of profit, suitability conclusion, risk-acceptance conclusion, or order
instruction.
