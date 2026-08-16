# V2 First Market-Intelligence Coding Sequence

## Decision Summary

The first implementation sequence should build the smallest truthful path from live market data to
an auditable option candidate. It should not begin with a large indicator catalog or an AI prompt.

The approved product boundary is:

- **Trade universe:** SPXW, SPY, and QQQ 0DTE options.
- **Instrument selection:** evidence-driven. No instrument receives a configured preference.
- **SPXW discovery band:** configurable, initially approximately `$0.10-$2.00` per option.
- **Meaning of the band:** candidate discovery only. Cheap does not mean good, liquid, timely, or
  directionally justified.
- **Long-option affordability:** use a fresh executable ask. Use midpoint only for ranking when the
  quote is two-sided and its spread is acceptable.
- **Observation universe:** independent from the trade universe and dynamically expandable later.
- **Opportunity model:** plural. Maintain multiple independently valid candidates across
  instruments, directions, horizons, and contracts.
- **Opportunity identity:** target exposure, direction, horizon, relationship/market-structure
  episode, evidence set, and invalidation. The instrument producing leading evidence need not be
  the exposure selected for the opportunity.
- **Output:** a ranked advisory opportunity set for Markeitect. No automated execution.

Cboe currently lists SPXW as PM-settled, cash-settled, European-style, and available during Global
Trading Hours. Cboe states that SPX/SPXW GTH runs from 8:15 p.m. to 9:25 a.m. Eastern; the runtime
must still use an exchange calendar for holidays, DST, and exceptional sessions rather than
hard-coded local times.

Primary references:

- [Cboe SPX product and trading hours](https://www.cboe.com/tradable-products/sp-500/spx-options)
- [Cboe SPX Weeklys specifications](https://www.cboe.com/tradable_products/sp_500/spx_weekly_options/specifications/)

## Evidence Example To Preserve

The supplied execution screenshot records an SPXW Aug 13, 2026 7835 call bought for `$0.55` and
sold for `$2.20`, a `4x` gross value or `+300%` before costs. The chart and operator account describe
the thesis as prior consolidation plus previous power-hour evidence that buying continued without
meaningful selling.

This example establishes two requirements:

1. A premarket decision may depend on a compact, durable summary of the previous regular session.
2. A cheap OTM option can be the correct expression, but contract affordability remains separate
   from the underlying directional thesis.

The screenshot shows 7835C; any 7830C reference should be treated as an operator note requiring
confirmation, not silently merged into the evidence record.

## Recommended Sequence

The canonical stage order is:

```text
Session/calendar ownership
    -> evidence-health contracts
    -> historical dependency execution
    -> baseline metric contracts
    -> entities and rolling state
    -> first semantic events
    -> bounded options-data proof
    -> cross-instrument state
    -> richer analytics
    -> live advisory agent
```

The detailed sections below expand that sequence without changing its order.

## Cross-Cutting Configuration Rule

Every stage must follow the project charter's
[Configuration And Optimization Principle](../../markeitech.md#configuration-and-optimization-principle).
In particular:

- no instrument list, preference, threshold, timeframe, lookback, session window, freshness age,
  scoring weight, cadence, subscription budget, or resource limit may exist as an unexplained
  implementation constant;
- every variable parameter has a type, unit, documented default, scope, validation envelope,
  mutability class, source, version, and effective time;
- analytical outputs and opportunity decisions identify the effective parameter version;
- runtime/model changes use typed, policy-checked, expiring, auditable intents; and
- evidence honesty, schemas, authorization, audit, and execution prohibitions remain
  code-enforced invariants rather than tunable settings.

### 1. Session And Calendar Ownership

Implement one authoritative session-state capability before analytical metrics.

It must:

- represent Cboe SPXW Global, Regular, and Curb sessions separately;
- represent equity/index cash sessions and futures overnight/regular phases;
- use exchange timezone and calendar dates, including DST, holidays, and early closes;
- expose `session_id`, trade date, phase, open/close timestamps, and time-to-transition;
- publish semantic session transitions only once; and
- reject option discovery when the contract is not in an eligible session.

**Exit:** every downstream value can answer which market session produced it.

### 2. Evidence Health Contract

Implement a shared evidence-health vocabulary before calculating market meaning.

Minimum fields:

- source and feed kind;
- instrument and contract identity;
- event, receive, and calculation timestamps;
- age and freshness state;
- entitlement and subscription state;
- completeness and missing-input reasons;
- fidelity: reported, derived, inferred, partial, stale, or unavailable; and
- session alignment.

This contract must support quotes, bars, trades, historical responses, option values, and derived
cross-instrument references.

**Exit:** no metric or candidate can hide stale or unsupported evidence.

### 3. Historical Dependency Execution

Extend acquisition demand with bounded historical requirements declared by analytical
capabilities. Do not let each analytics actor call IB directly.

The first dependency set should support:

- previous regular-session OHLC and close;
- overnight high/low and gap reference;
- session-to-date bars;
- opening-range warmup; and
- enough completed bars for the first approved volatility and trend measurements.

Historical responses remain transient unless transformed into approved metrics, entities, or
session summaries. Raw history is not stored for replay.

**Exit:** a capability can declare, receive, and validate its exact warmup without provider
ownership leaking into analytics.

### 4. Baseline Deterministic Measurements

Build only the foundation metrics needed by several later decisions:

- fresh bid, ask, midpoint, spread, and spread percentage;
- completed-bar OHLCV and normalized return;
- session open/high/low/range and location within range;
- previous-session high/low/close and overnight gap;
- opening range and extensions;
- session VWAP where volume is meaningful;
- realized range/volatility;
- directional efficiency; and
- compression/expansion state.

Each metric contract must state inputs, cadence, warmup, units, nullability, retained state,
fidelity, and failure behavior.

**Exit:** live values match an independent operator reference and remain bounded in memory.

### 5. Session Entities And Durable Summaries

Create stable identities only for subjects required by the baseline:

- trading session;
- previous-session reference set;
- opening range;
- gap; and
- compact derived session summary.

Persist meaningful derived summaries, not raw market data. The first durable summary should retain
approved prior-session and power-hour measurements needed by the next premarket run. It must carry
metric versions and fidelity so changed formulas cannot rewrite history invisibly.

**Exit:** a restart before the open does not erase yesterday's decision evidence.

### 6. Quiet Semantic Market Events

Publish events only for meaningful transitions:

- evidence became healthy, degraded, stale, or unavailable;
- session phase changed;
- opening range completed or materially extended;
- volatility state changed;
- compression transitioned to expansion;
- gap state changed; and
- price approached, tested, accepted, or rejected an approved session reference.

Numerical churn remains a metric update, not an event. Events require stable identity,
deduplication, effective time, evidence links, expiry, and invalidation rules.

**Exit:** the stream is quiet enough for an agent and a human to follow.

### 7. Bounded Options-Data Proof

Move this proof earlier than broad analytical expansion because GTH availability is now a core
product requirement.

Prove, through the existing acquisition boundary:

- discovery of the correct SPXW expiration for the exchange trade date;
- bounded strike selection around a trustworthy underlying reference;
- quote subscriptions for a small candidate set rather than the full chain;
- bid, ask, midpoint, last, quote age, spread, and market validity;
- available IB Greeks/IV with source and freshness;
- candidate entry to and exit from the configurable premium band;
- pacing, subscription budget, cancellation, and shutdown; and
- GTH behavior in a real paper session.

No option becomes a candidate from `last` alone. A zero bid, missing ask, crossed quote, stale
quote, or excessive spread must produce an explicit rejection reason.

**Exit:** during GTH and RTH the system can truthfully say which bounded SPXW contracts are
currently affordable and executable enough to inspect, without preferring them over stronger
opportunities in other supported products.

#### 7A. Overnight Underlying Reference

Do not assume the cash SPX index is live throughout GTH.

Build an explicit reference state containing:

- latest reported SPX value and age;
- ES price and session phase;
- the observed SPX/ES basis when both references were recently valid;
- any projected SPX reference as a separately named derived value;
- timestamp alignment and confidence/fidelity; and
- invalidation when the basis or inputs are stale.

An ES-derived reference may guide strike-window discovery, but it must never be labeled as the
reported SPX price.

**Exit:** moneyness and strike distance remain honest before cash hours.

#### 7B. Option Candidate Quality

Calculate contract quality separately from market direction.

Minimum candidate fields:

- contract, expiry, strike, right, multiplier, and settlement style;
- executable ask, midpoint, bid, spread, and spread percentage;
- premium-band state;
- distance and moneyness relative to the named underlying reference;
- time to RTH open, expiry, and last eligible trading time;
- IV, delta, gamma, theta, and vega when valid;
- quote freshness and two-sidedness;
- expected slippage or fillability class;
- candidate rejection reasons; and
- source/fidelity for every optional value.

Useful events include `option.candidate.entered_band`, `option.candidate.became_tradeable`,
`option.candidate.degraded`, and `option.candidate.left_band`. These are observations, not signals.

**Exit:** the system can explain why a cheap contract is or is not a usable expression.

### 8. Cross-Instrument Relationship State

Begin with structural groups rather than all-pairs correlation:

- SPX, ES, and SPY;
- NQ and QQQ;
- VIX as volatility context; and
- other watchlist instruments only when a decision question justifies them.

Measure freshness-aligned normalized returns, disagreement, leadership/lag hypotheses, and regime
changes. Do not encode permanent folklore such as “CL up means NQ down.”

Relationship evidence must remain distinct from opportunity identity. For example, NQ may lead an
aligned breakout while ES lags; with sufficient additional evidence, that relationship may support
an S&P catch-up opportunity expressed through SPXW or SPY. The same evidence graph may also support
a separate QQQ continuation opportunity. Neither source instrument nor expression contract owns
the thesis.

**Exit:** relationships are dynamic evidence with explicit horizons and decay.

### 9. Richer Analytics

Add richer capabilities only after the foundational and cross-instrument state is trustworthy.
Priorities are approved market structure, level/zone interaction, participation, price response,
and option-underlying behavior, not a generic indicator catalog.

Trade-response measurements should run only for instruments granted bounded focus leases. The
first release should distinguish:

- observed or honestly inferred aggressor flow;
- price response to buying and selling effort;
- directional efficiency of that response;
- absorption/non-response hypotheses with explicit limitations; and
- power-hour aggregates persisted as compact derived session summaries.

The agent may request focus for more than one instrument when policy and resource budgets allow.
This stage must not counterfeit order flow from OHLCV bars. Bar-derived participation metrics may
exist under separate names and fidelity.

**Exit:** multiple instrument opportunities can use richer, truthful evidence, and the next
premarket session can consume yesterday's approved summaries without raw-tick replay.

### 10. Agent Read Model And Advisory Opportunity Set

Only after the deterministic path is trustworthy, expose a compact read model and typed tools to
the live agent.

The agent may:

- inspect rolling state and cited evidence;
- request bounded historical dependencies;
- request or release focus leases;
- request bounded option candidate refreshes;
- maintain several concurrent opportunity candidates; and
- propose one or more SPXW, SPY, or QQQ 0DTE contracts when independently justified.

Policy must enforce resource budgets, session eligibility, expiry, allowed parameters, and audit.
Every opportunity must separate:

1. underlying thesis;
2. timing and invalidation;
3. expression-vehicle choice;
4. contract quality and payoff geometry;
5. conflicting or missing evidence; and
6. uncertainty or abstention.

There is no default winner. The agent ranks opportunities from evidence and may surface several,
surface one, or abstain entirely. A cheap SPXW contract remains only one possible expression, and
automated order placement remains absent.

**Exit:** Markeitech can produce an evidence-cited, inspectable advisory opportunity set or a
precise reason to abstain.

## First Coding Batch Recommendation

The first coding batch should implement **Session And Calendar Ownership plus the Evidence Health
Contract**, and nothing analytical beyond what is required to prove those foundations.

Recommended batch deliverables:

1. typed session phase and evidence-health contracts;
2. one authoritative session-state owner wired to the Nautilus bus;
3. Cboe SPXW GTH/RTH/Curb calendar behavior plus futures/equity session identities;
4. freshness evaluation for the existing quote and five-second-bar observations;
5. quiet session/evidence transition events;
6. PostgreSQL audit of those semantic lifecycle transitions, not raw observations;
7. restart and DST/holiday boundary tests; and
8. updated human-readable logs showing exchange session, trade date, and evidence status.

This batch creates the foundation needed for historical warmup, analytics, options discovery, and
the live agent without committing us to unapproved indicator definitions.

Every session definition and freshness threshold in this batch must be supplied through typed
configuration. Initial values may be startup-only, but their contracts must already declare future
runtime mutability and optimization eligibility.

## Accepted Decisions Before Coding

1. **Opportunity identity:** an opportunity is identified by its target exposure, direction,
   horizon, relationship/market-structure episode, evidence, and invalidation. Evidence may come
   from different leading or confirming instruments. One opportunity may own several independently
   ranked expression candidates, and one evidence graph may support several concurrent
   opportunities.
2. **Initial expression seed:** the first configured expression universe is SPXW, SPY, and QQQ. It
   remains runtime-expandable through later policy-approved intents and is not a permanent
   whitelist.
3. **First-batch mutability:** session and evidence-health parameters are typed startup
   configuration initially. Their contracts still declare scope, source, authorized range,
   mutability class, optimization eligibility, version, and effective time. Live changes wait for
   typed intents, deterministic policy, safe application boundaries, audit, expiry, and rollback.

## Explicitly Deferred

- full-chain continuous subscriptions;
- unrestricted all-watchlist trade subscriptions;
- order-book analytics;
- gamma exposure, dealer positioning, or max-pain claims without defensible inputs;
- a universal market score;
- ML optimization;
- prompt-only trading logic; and
- automated execution.
