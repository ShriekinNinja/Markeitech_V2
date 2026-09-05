# Market Intelligence Request Catalog

**Status:** Human-readable product catalog. Implementation remains stage-gated.

## Why This Exists

This document lists the complete kinds of work Markeitech's components and later advisory agent
must be able to request. It consolidates the market-specialist brief, the semantic-events and
options baseline, and the accepted V2 live-agent blueprint.

It is intentionally broader than Stage 9B. Stage 9B implements historical dependency execution,
but its contracts must fit the complete destination rather than only the first examples.

The catalog separates five things which must never be confused:

1. **Provider data requests:** obtain reported native market evidence.
2. **Historical evidence requests:** obtain bounded past observations for an approved capability.
3. **Capability requests:** activate deterministic calculations over native or historical inputs.
4. **State queries:** inspect already calculated metrics, entities, events, and opportunities.
5. **Agent intents:** request policy-controlled work without accessing IB or infrastructure.

An entry does not mean it is implemented or approved for activation. Every entry still requires a
concrete contract, configuration, resource budget, fidelity policy, and acceptance test.

## Universal Request Fields

Every executable request must eventually identify:

- stable request and schema identity;
- requester, authority, purpose, and consumer;
- instrument, contract, venue, and asset class where applicable;
- session, trade date, horizon, timeframe, or exact UTC bounds;
- source/provider and required fidelity;
- priority, deadline, lease/expiry, and cancellation identity;
- requested cadence, depth, and maximum observations;
- parameter and policy version;
- estimated and admitted provider/CPU/memory cost;
- dynamic/static parameter permissions and safety bounds;
- causation/correlation identity;
- lifecycle result: accepted, modified, queued, rejected, active, completed, degraded, failed,
  expired, or canceled; and
- evidence health, missing reasons, and operational audit identity.

No request may silently imply that data exists, is fresh, has volume, is consolidated, or is
reported rather than inferred.

## 1. Provider Data Requests

These requests are owned by `DataAcquisitionActor` and executed through Nautilus/IB or another
approved provider. Analytical actors do not issue them directly.

| Request | What it obtains | Important limits and honesty |
|---|---|---|
| Instrument definition | Canonical instrument metadata | Resolve identity before other demand |
| Instrument universe query | Definitions matching configured venue/type filters | Bounded and policy-authorized |
| Top-of-book quote stream | Bid, ask, sizes, timestamps | Entitlement, staleness, crossed/one-sided state |
| Trade stream | Reported trade price and size | Provider coverage is not assumed consolidated |
| Completed-bar stream | Native/provider OHLCV bars | Selector and aggregation source are explicit |
| Instrument-status stream | Trading/auction/halt status where supported | Absence must not mean normal trading |
| Order-book stream | Bounded depth or deltas | Deferred until justified; expensive and feed-specific |
| Historical bars | Exact bounded bar observations | Stage 9B initial provider proof |
| Historical quotes | Exact bounded quote observations | Planned only when a capability earns the cost |
| Historical trades | Exact bounded trade observations | Planned; fidelity/provider limits explicit |
| Option-chain discovery | Expiries, strikes, rights, contract identities | Bounded discovery, never full-chain by default |
| Option quote stream/snapshot | Bid, ask, sizes, last, volume | Fresh executable ask governs long affordability |
| Option Greeks/IV | Provider-computed IV and Greeks | Optional, source-labelled, nullable and freshness-bound |
| Option trade stream | Contract trades and sizes | Local flow inference only unless coverage proves otherwise |
| Funding/reference/index value | Provider reference values where applicable | Cash SPX may be stale outside its reporting session |
| News/economic release | Scheduled and released factual data | Future external provider; fact and interpretation separated |

## 2. Historical Evidence Request Catalog

Historical requests are transient inputs. Raw responses are not persisted merely for replay or
possible future use.

### Session and phase windows

| Window | Meaning |
|---|---|
| Previous RTH | The previous completed regular trading session |
| Previous GTH/overnight | The previous accepted overnight/global phase |
| Current overnight | Current overnight phase through now or RTH open |
| Current RTH/session to date | Current regular session through the last completed interval |
| Current GTH/session to date | Current eligible global session through the last completed interval |
| Curb session | Exact configured curb phase where applicable |
| Premarket | Configured premarket phase for the instrument class |
| Power hour | Configurable final portion of a completed regular session |
| Opening range | Configurable duration from an authoritative phase open |
| Named phase slice | Configurable start/end offsets within a session phase |
| Previous N sessions | Bounded completed sessions for normalization or structure |
| Recent completed bars | Last bounded N bars before an explicit `as_of` timestamp |
| Anchored interval | Exact interval beginning at an approved event/entity anchor |
| Synchronized cross-instrument interval | The same exact UTC interval for several instruments |

### Historical evidence purposes

The same window may satisfy several consumers. Purpose and lineage remain attached even when the
provider request is shared.

- Previous-session open, high, low, close, range, and volume.
- Overnight high, low, range, and gap reference.
- Session-to-date open, high, low, range, location, VWAP, and participation.
- Configurable opening ranges and extensions, including but not limited to OR5 or OR15.
- Prior power-hour participation and price-response summary inputs.
- Rolling return, range, volatility, percentile, and normalization warmup.
- Directional efficiency, rotation, compression, expansion, and transition warmup.
- Any approved configurable moving/anchored calculation, including EMA examples.
- Multi-horizon market structure and swing detection.
- Gaps, FVGs, levels, zones, balance areas, trend lines, and profile construction.
- Volume baseline, relative volume, price/volume distribution, HVN/LVN, and POC/value-area inputs.
- Cross-instrument aligned returns, disagreement, leadership, lag, and changing relationship
  warmup.
- Prior option/underlying summary inputs when approved and available.
- Compact prior-session entity reconstruction when cheaper and equally honest than persistence.

### Historical response

Every response must state:

- request and consumer lineage;
- exact requested and received bounds;
- selector, source, and provider;
- observation count, missing intervals, and completeness;
- event-time ordering and duplicate/correction findings;
- reported/inferred/partial/unavailable fidelity;
- request, provider, receive, and completion timestamps;
- per-consumer minimum evidence and readiness result; and
- terminal reason: ready, degraded, failed, canceled, or expired.

## 3. Deterministic Capability Requests

Capabilities consume native observations and historical dependencies. Each capability requires a
reviewed specification covering inputs, formula, cadence, warmup, retained state, fidelity,
failure behavior, cost, and possible events.

### Quote and liquidity

- Bid, ask, midpoint, spread, spread percentage, and sizes.
- Quote age, stability, update rate, one-sided/crossed state, and executable-price quality.
- Near-the-money option liquidity, expected slippage/fillability, and deterioration.
- Order-book pressure/depth only after a bounded supported-data review.

### Completed-bar geometry and returns

- OHLCV, range, body, upper/lower wick, body ratio, and close location.
- Normalized return over configurable event/time/session horizons.
- Relative range and relative volume against named baselines.
- Candle patterns with exact definitions of what was engulfed or displaced.

### Session and auction structure

- Session open/high/low/close, range, location, and time remaining.
- Previous-session references and current overnight range/gap.
- Configurable opening range and extensions.
- Session VWAP where volume is meaningful.
- Rotation, directional efficiency, compression, expansion, and transition.
- GTH/RTH/Curb/premarket distinctions and explicit cash-versus-proxy references.

### Volatility and trend

- Realized range/volatility across configurable horizons.
- Volatility percentile, z-score, regime, expansion, and contraction.
- Directional efficiency and trend/rotation state across horizons.
- Configurable moving or anchored references, slopes, separation, and hold/failure behavior.
- Trend-line anchors, contacts, slope, projection timestamp, fit error, age, break, and role reversal.

### Levels, zones, gaps, and profiles

- Session, prior-session, opening-range, swing, gap, and user-approved levels.
- Distance, approach direction/velocity, penetration, touches, acceptance, rejection, hold, failure,
  and target interaction.
- FVG, order-block, supply/demand, value-area, liquidity-pool, balance-area, and user-defined zones.
- Zone width, age, entries/touches, fill percentage, remaining imbalance, strength, and
  invalidation.
- Volume/price histogram, POC, VAH/VAL, HVN/LVN, and distribution shape.
- Reported trade-at-price profiles only when source data supports them; candle-derived profiles
  remain separately named inferred approximations.

### Participation, volume, and effort versus response

- Observed volume against a named lookback/baseline.
- Z-score, percentile, ratio, and session-relative participation.
- Observed/inferred buy and sell volume, delta, cumulative delta, and classification coverage.
- Price response to aggressive buying/selling, favorable/adverse excursion, and efficiency.
- Large trade, same-side burst, absorption/non-response, trapped-participant, and follow-through
  hypotheses only with explicit fidelity.
- Bar-derived pressure proxies under separate names; OHLCV never becomes counterfeit order flow.

### Cross-instrument relationships

- Freshness-aligned normalized and volatility-adjusted movement.
- Contemporaneous alignment/disagreement and participation differences.
- Lead/lag hypotheses with horizon, strength, decay, and expiry.
- Catch-up state and changing relationships among approved structural groups.
- Regime-dependent VIX, ES/SPX/SPY, NQ/QQQ, sector, leader, commodity, and later relationships.
- Correlation/association never labelled causation without separate evidence.

### Options and underlying context

- Correct 0DTE expiry and bounded strike universe.
- Fresh bid, ask, midpoint, last, sizes, spread, spread percentage, and quote stability.
- Premium-band state based on executable ask; midpoint ranking only with a valid two-sided market.
- Strike distance and moneyness against a named reported or derived underlying reference.
- Time to RTH open, expiry, and last eligible trading time.
- IV, delta, gamma, theta, and vega when valid.
- Open-interest and volume concentration, volume/OI, skew, term structure, and Greek exposure.
- Pin/gamma-sensitivity areas, volatility expansion risk, and liquidity deterioration.
- Option trade side inference, repeated strike activity, blocks/sweeps/clusters, and
  option-price/underlying divergence with provider limitations.
- SPX/ES basis and an explicitly derived overnight SPX reference with timestamp alignment and
  invalidation.
- Candidate tradeability, affordability, rejection reasons, and contract degradation.

## 4. Analytical Entity And State Requests

Components and the agent need bounded read access to approved current state, not arbitrary SQL.

### Entities

- Trading session and phase.
- Previous-session reference set and compact power-hour summary.
- Opening range and extensions.
- Gap.
- Level.
- Zone, including FVG and value/profile areas.
- Trend line and role-reversed line.
- Volume-profile node and balance area.
- Cross-instrument relationship episode.
- Option candidate set.
- Opportunity evidence graph.

Every entity requires stable identity, revisions, validity, activity, completion, expiry,
invalidation, replacement, and session/contract rollover rules.

### Rolling state

- Evidence and capability health.
- Active sessions, levels, zones, gaps, profiles, and trends.
- Bullish pressure, bearish pressure, neutral risk, net direction, gross activity, confidence, and
  urgency as separate dimensions rather than one universal score.
- Regime, trend/rotation, volatility, compression/expansion, and auction state by horizon.
- Cross-instrument alignment, disagreement, leadership, lag, and confidence.
- Active option candidates and contract quality.
- Concurrent opportunity candidates, conflicts, missing evidence, and invalidations.

## 5. Semantic Event Families Requested By The Specialist

Events represent meaningful transitions, not every metric update.

### System, session, and evidence

- Session opened, phase changed, and session closed.
- Evidence became healthy, degraded, stale, unavailable, or unsupported.
- Capability became ready, degraded, failed, recovered, or reconfigured.

### Price and entity interaction

- Price approached, touched, crossed, breached, accepted, reclaimed, rejected, held, failed, or
  targeted a level/zone/reference.
- Opening range completed or materially extended.
- Gap opened, entered, partially filled, fully filled, rejected, or invalidated.
- Trend line created, confirmed, dormant, reactivated, touched, rejected, broken, role-reversed,
  invalidated, or expired.
- FVG/zone created, entered, partially filled, fully filled, invalidated, or expired.

### Bar, participation, and regime

- Defined candle pattern completed.
- Volume exceeded a named baseline.
- Volatility regime changed.
- Compression transitioned to expansion or expansion failed.
- Liquidity sweep, absorption/non-response, aggressive-flow follow-through, trapped-participant,
  and price/flow divergence hypotheses.

### Cross-instrument

- Alignment or disagreement became material.
- Leadership/lag episode began, strengthened, reversed, decayed, or expired.
- Catch-up evidence became active or invalid.
- Relationship regime changed.

### News

- News scheduled, released, revised, or canceled.
- Separate market-interpretation event linked to the factual release.

### Options

- Option candidate entered/left the affordability band.
- Candidate became tradeable, degraded, stale, or rejected.
- Large/ask-side/bid-side option trade observed or inferred.
- Sweep, block, repeated-strike activity, flow cluster, volume-over-OI, or flow/price divergence.
- Call/put activity spike, skew steepening, gamma concentration, pin risk, liquidity deterioration,
  term-structure inversion, or volatility-expansion risk.

### Composite and opportunity

- Evidence-linked composite setup created, strengthened, contradicted, or invalidated.
- Opportunity moved through observing, candidate, proposed, revised, invalidated, expired, or
  closed.
- Agent abstained with explicit missing, conflicting, stale, unaffordable, or untradeable reasons.

Every event definition must specify its layer, subject, trigger transition, evidence, fidelity,
direction, horizon, timing, identity, deduplication, expiry/invalidation, separate significance
dimensions, state effect, permitted inference, and forbidden inference.

## 6. Agent-Authorized Requests

The advisory agent may eventually request only typed, policy-checked work:

- add, remove, or reprioritize observation demand;
- acquire or release bounded focus leases for richer trade-response data;
- request one cataloged historical dependency;
- activate, deactivate, or reconfigure one approved analytical capability;
- request a bounded option-chain/contract refresh;
- inspect compact metrics, entities, events, relationships, candidate sets, and health;
- compare several concurrent opportunities or expression candidates;
- publish an evidence-cited proposal, revision, invalidation, or abstention; and
- request operator attention.

The agent cannot invent formulas, selectors, instruments, provider parameters, or policy limits;
connect to IB; query arbitrary SQL; access credentials; mutate schemas/code; hide unavailable
evidence; or execute orders.

## 7. Human-Readable Response Types

| Response | Human meaning |
|---|---|
| Accepted | Request is valid and admitted under current policy |
| Modified | Policy reduced scope, cadence, duration, or cost and explains why |
| Queued | Valid work is waiting behind provider/resource limits |
| Active | Provider subscription/request or capability is running |
| Ready | Required evidence is complete enough for the named consumer |
| Degraded | Some useful evidence exists, but a named requirement is missing/weak |
| Rejected | Request is unsupported, unauthorized, invalid, or outside policy |
| Failed | Execution failed after the allowed attempts |
| Expired | Deadline or lease elapsed before completion |
| Canceled | Requester, policy, shutdown, or replacement ended the work |
| Completed | Bounded work ended and terminal facts were audited |

Responses must identify what happened, to which request and consumer, using which evidence and
policy version, and what can safely happen next.

## 8. Delivery Stages

| Catalog area | Planned stage |
|---|---|
| Session/evidence truth | 9A, implemented |
| Historical dependency contracts and execution | 9B, active |
| Baseline deterministic capability contracts/runtime | 9C |
| Entities and bounded rolling state | 9D |
| Quiet semantic event lifecycle | 9E |
| Bounded 0DTE option discovery and quality | 9F |
| Cross-instrument relationship state | 9G |
| Richer structure, profiles, participation, and response analytics | 9H |
| Agent read model, policy, and typed tools | 9I |
| Concurrent advisory opportunities | 9J |
| Evaluation and ML optimization | 9K |

The stages control implementation order, not whether a requirement exists. The complete catalog
is considered during every contract decision from Stage 9B onward.

## 9. Explicit Anti-Requests

Markeitech does not support requests to:

- store raw market history merely for future replay or backtesting;
- subscribe an unbounded option chain or all instruments without a resource policy;
- treat a stale cash index as a live overnight underlying;
- produce volume analytics for instruments without meaningful volume;
- label candle proxies as observed order flow;
- treat option call/put activity as automatically bullish/bearish;
- encode permanent causal folklore between instruments;
- collapse every dimension into one score;
- ask an LLM to calculate raw high-rate market facts;
- allow a model or agent to bypass parameter bounds or evidence health; or
- recommend or execute an order without a separately approved execution architecture.

## Source Documents

- [`research/market-analysis-specialist-brief.md`](research/market-analysis-specialist-brief.md)
- [`research/semantic-events-ai-options-baseline.md`](research/semantic-events-ai-options-baseline.md)
- [`product/sir-loke-v1.md`](product/sir-loke-v1.md)
- [`roadmap/v2-market-events-live-agent-plan.md`](roadmap/v2-market-events-live-agent-plan.md)

When those documents evolve, this catalog must be reviewed so future implementation does not
silently narrow the product destination.
