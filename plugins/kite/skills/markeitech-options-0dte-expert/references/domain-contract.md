# Options And 0DTE Domain Contract

## Questions This Advisor Owns

- Whether an option chain or contract identity is sufficiently exact for the stated decision.
- Whether expiry, session, last-trade, exercise, assignment, deliverable, and settlement semantics
  are represented truthfully for the exact product.
- Whether quotes, spreads, sizes, trades, volume, open interest, IV, and Greeks are fresh and fit
  for a named analytical use.
- Whether a bounded discovery universe can identify contracts for inspection without silently
  becoming a signal, product preference, or execution instruction.
- Whether option-specific flow, volatility-surface, exposure, and same-day-expiry interpretations
  exceed the identified source's coverage or assumptions. This is a defensive evidence review, not
  authority to create participant-positioning, market-impact, or microstructure semantics.
- Which material options-domain evidence is missing before architecture, implementation,
  candidate-quality, or advisory decisions proceed.

This advisor informs decisions. It cannot approve product semantics, architecture, persistence,
provider ownership, risk policy, execution, trading, release, or external actions.

It also does not own underlying swing, pivot, FVG, zone, or auction-structure semantics; provider
entitlement truth; OPRA or vendor licensing; statistical or causal validation; participant or
dealer-position inference; execution quality; margin; liquidation; or account-risk policy. Use the
router and the owning specialist whenever those questions are material.

## Exact Identity Gate

Do not compare, aggregate, or advise on a contract until the evidence identifies, as applicable:

- provider and provider contract identifier;
- option root/trading class and underlying or settlement index;
- venue or routing scope;
- expiration date and exchange trade date;
- strike with precision and call/put right;
- multiplier, currency, deliverable, and adjustment/corporate-action state;
- exercise style and settlement type;
- AM/PM settlement and settlement-value source;
- last eligible trading timestamp, exchange timezone, session, holiday/early-close state; and
- source event time, receive time, calculation time, and evidence lineage.

Root similarity is not identity. `SPX`, `SPXW`, and an SPX chain display may contain products with
different settlement. `SPY` and `QQQ` ETF options must not inherit SPX mechanics. An adjusted ETF
option must not inherit the standard 100-share deliverable without verification.

## Current Product Baseline To Re-Verify

These are routing hypotheses, not timeless constants:

- Cboe describes standard SPX/SPXW as $100-multiplier, European-style, cash-settled index options.
- SPXW daily/weekly expirations are generally PM-settled and expiring SPXW ordinarily stops at
  4:00 p.m. ET, with a stated half-day exception; standard SPX expiration mechanics differ.
- Cboe publishes distinct SPX Global, Regular, and Curb hours.
- SPY and QQQ are ETF options, generally American-style and physically settled with a standard
  100-share deliverable, subject to exact series adjustments and broker/OCC handling.
- SPY and QQQ have daily expirations, but actual listed series, holiday shifts, venue sessions,
  and last-trade eligibility must be discovered, not generated from weekday assumptions.
- Exchange hours can change by product and venue. A 2026 Cboe expansion covered a named set of
  equity-option classes and did not establish universal extended hours for SPY or QQQ.

Refresh exchange specifications, OCC materials, the actual series definition, and provider
delivery before using any baseline fact.

## 0DTE Identity And Time

`0DTE` means the contract is being evaluated on its actual expiration trading date under the
applicable exchange calendar. Do not trust a rounded vendor `DTE` field, local calendar date, or
`DTE=1` convention as proof. Record timezone, holiday shifts, exceptional sessions, current phase,
time to last eligible trade, time to settlement determination, and time to expiration separately.

Near expiration, small timestamp and underlying-price differences can dominate moneyness, Greeks,
and premium. A stale cash index must not masquerade as a live overnight reference. Any futures-
or basis-derived reference must be separately named, timestamp-aligned, fidelity-labelled, and
invalidated when its inputs or basis are stale.

## Quotes, Liquidity, And Execution Constraints

- `last` is historical, not an executable price.
- A fresh ask is a displayed long-entry reference, not a fill guarantee. A bid is likewise not a
  guaranteed exit.
- Midpoint is a derived ranking reference only when the market is fresh, two-sided, uncrossed, and
  within the approved spread policy.
- Preserve bid, ask, sizes, quote venue/aggregation scope, quote time, receive time, age, session,
  trading status, and feed entitlement. Reject missing, zero where semantically invalid, crossed,
  locked if unsupported by policy, stale, or wrong-session quotes explicitly.
- Report absolute spread, spread as a percentage of a named denominator, and tick granularity.
  Do not call a quote liquid from spread alone; stability, displayed size, tradeability, contract
  activity, market state, and remaining time may all matter.
- `expected slippage` is a model estimate unless measured from identified orders/fills. Effective
  spread and realized fill quality require execution evidence and belong behind execution/risk
  approval gates.

Any cutoff for quote age, spread, size, stability, premium, time remaining, or fillability is a
bounded, versioned policy candidate rather than domain truth.

## Greeks And Implied Volatility

IV and Greeks are model-dependent derived values, not exchange-observed future outcomes. Record:

- source/provider and whether values are provider-computed or Markeitech-computed;
- model/version when known, underlying reference, option price input, rates, dividends/borrow,
  exercise assumptions, units/sign conventions, event and calculation time;
- which Greek set is meant when bid-, ask-, last-, or model-price values coexist;
- missing/sentinel/error states and provider entitlement or calculation preconditions; and
- numerical stability and fitness for use near expiry, around the strike, and in sparse markets.

Delta is not probability without a separately justified model interpretation. Gamma does not prove
dealer positioning. Theta is not a deterministic next-tick loss. Vega and IV do not establish
realized volatility. Never substitute a provider field's existence for adapter-delivery proof.

## Volume, Open Interest, Flow, And Exposure

- Volume is activity over a defined venue/feed/session scope; it is not directional intent.
- Open interest is a clearing-derived position count with an as-of date and publication lag; it
  is not live positioning and does not identify holder direction. Volume greater than open
  interest does not prove opening trades.
- OPRA disseminates consolidated listed-options last-sale and quote information, but a downstream
  provider or vendor may filter, delay, normalize, omit conditions, or expose only a subset.
- Trade price relative to a contemporaneous NBBO can support bounded side inference only after
  sequence, condition, complex-order, late/cancel/correction, crossed/locked, and quote-alignment
  handling. It still does not prove buyer identity, opening/closing, or strategy.
- Blocks, sweeps, repeated strikes, and call/put labels do not automatically mean bullish,
  bearish, institutional, informed, opening, closing, or single-leg activity.
- GEX/dealer-exposure estimates require an exact universe, snapshot, Greek method, open-interest
  or intraday-position input, multiplier, underlying, sign/position assumptions, and formula.
  Treat modeled dealer inventory and hedge response as hypotheses unless observed independently.

Vendor exports require immutable artifact identity, export/download timestamp, source timezone,
filters, source version, licensing/terms, row lineage, corrections, and coverage disclosure. A
vendor-curated feed is not promoted to consolidated market evidence by normalization.

## Expression Separation

Evaluate these layers independently:

1. underlying evidence and target exposure;
2. decision horizon, trigger, contradiction, and invalidation;
3. eligible product/session;
4. contract identity and payoff geometry;
5. quote, liquidity, IV/Greek, exercise, settlement, and remaining-time quality; and
6. execution/risk constraints, only after separately approved architecture.

A sound thesis may have no usable option. A high-quality option does not create a thesis. One
opportunity may have several expression candidates, several opportunities may coexist, and the
advisor may abstain from ranking when evidence is not comparable.

## Required Other Advisors

Stop and invoke the repository advisor router when the work materially crosses domains:

- Nautilus actors, adapters, native option types, cache, message bus, subscription ownership,
  lifecycle, concurrency, persistence, or installed-version behavior require the project-scoped
  Nautilus advisor and its native-capability gate.
- Vendor schemas, sweeps/blocks/repeats, complex-order ambiguity, classifications, premium
  aggregation, filters and transformations require `markeitech_options_flow_advisor`.
- Provider entitlements or exchange routing require the provider advisor; OPRA redistribution,
  non-display use, retention, derived data, or vendor licensing require
  `markeitech_vendor_data_licensing_provenance_advisor`. If unavailable, stop.
- Execution, fill models, order types, margin, liquidation, exercise instructions, assignment,
  position/risk limits, or automated actions require separately approved execution and risk
  specialists. This options advisor does not supply that authority.
- Tax, legal, regulatory, suitability, or accounting conclusions require qualified coverage and
  current jurisdiction-specific authority.
- Statistical validation, causal market-impact claims, or optimization require an appropriate
  quantitative-methods review independent of the builder.
