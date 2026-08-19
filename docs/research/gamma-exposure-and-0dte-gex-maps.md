# Gamma Exposure And 0DTE GEX Maps

**Status:** Research guidance only. This document does not define a trading signal, accepted
metric contract, or implemented Markeitech capability.

## Purpose

Gamma-exposure maps can help identify option-sensitive locations and the market regime in which
those locations may matter. They cannot establish dealer inventory, predict direction, or prove
that hedging caused a move. Markeitech should treat a GEX map as one fallible evidence source to
combine with price acceptance, volume profile, order flow, volatility, and cross-instrument state.

This note generalizes the common concepts found in vendor GEX displays. A label used by one vendor
may have a proprietary formula, sign convention, universe, or unit. Vendor-specific values must
remain `reported` evidence until their methodology is documented and independently validated.

## Core Mechanics

### Delta And Gamma

- **Delta** estimates how much an option's value changes for a small move in its underlying.
- **Gamma** estimates how much that delta changes as the underlying moves.
- A long call or long put has positive mathematical gamma. A short call or short put has negative
  mathematical gamma. Puts are not intrinsically negative gamma.
- A chart which draws call exposure above zero and put exposure below zero is applying a
  positioning or visualization convention. It is not displaying the mathematical sign of long
  put gamma.

A frequently used dollar-gamma approximation is:

```text
contracts x contract_multiplier x option_gamma x underlying_price^2 x 0.01
```

This estimates the change in delta-equivalent notional for a one-percent underlying move. Other
implementations report exposure per point, per index percent, or with different scaling. A number
such as `$-5.39B` is therefore meaningless without its formula, unit, option universe, timestamp,
and position-sign assumptions.

### Dealer-Hedging Interpretation

Under a simplified assumption that liquidity providers hold the opposite side of customer option
positions:

- a dealer who is **long gamma** tends to sell underlying as it rises and buy as it falls, which
  can damp movement and favor rotation;
- a dealer who is **short gamma** tends to buy as it rises and sell as it falls, which can amplify
  movement and favor continuation.

This is a conditional regime hypothesis, not an observed fact. Dealers may hedge discretely,
internally offset positions, hedge with futures or related products, carry vanna and charm risk,
or have inventory unlike the vendor's assumed positioning.

## Common Display Fields

Exact definitions must be obtained from the provider. The following are defensible generic
interpretations only.

| Display field | Likely meaning | What it does not mean |
| --- | --- | --- |
| `POS` / `NEG` | Modeled aggregate GEX sign at the current reference price | Certain dealer positioning or market direction |
| Net GEX amount | Aggregate modeled gamma sensitivity in the provider's units | A portable value that can be compared across vendors without normalization |
| Call/put GEX balance | Relative call-side and put-side contribution under the provider's sign methodology | Probability of an up/down move or a put/call volume ratio |
| ATM straddle | Current or reference at-the-money call-plus-put premium | A guaranteed range or necessarily a one-standard-deviation move |
| Day straddle | Session reference straddle or expected-move proxy | A standardized field across vendors |
| Magnet | Provider-selected strike or price expected to exert pinning/attraction pressure | A guaranteed destination |
| Gamma flip | Hypothetical underlying price where recomputed aggregate GEX crosses zero | Proof that the realized regime changes when price merely touches the level |
| Call wall | Strong call-side concentration selected by the provider | Guaranteed resistance |
| Put wall | Strong put-side concentration selected by the provider | Guaranteed support |
| Strike histogram | Modeled contribution or concentration by strike | Executed hedge flow or observed inventory |
| `PX` | Current reference price | Necessarily the same instrument or basis as the execution chart |

Markers commonly abbreviated as `MAG`, `PX`, and `GF` refer to the magnet, current price, and
gamma-flip estimates. The zero axis separates positive and negative modeled contribution under the
vendor's convention.

## How To Read A Map

### Start With Identity And Freshness

Before interpreting any level, establish:

1. underlying and option root;
2. expiration and settlement style;
3. spot, index, ETF, or futures reference used by the map;
4. exchange, session, and timestamp in UTC;
5. strike and expiration coverage;
6. source and age of open interest, quotes, implied volatility, and Greeks;
7. formula, scaling, and dealer-positioning assumptions; and
8. whether the map is open-interest based, intraday-flow based, or hybrid.

Index, ETF, and futures prices require an explicit timestamped basis. An SPX level cannot be
silently treated as an ES, SPY, or MES level.

### Treat Levels As Investigation Areas

Walls, magnets, and flips identify locations where option sensitivity may be concentrated. They
tell the operator or agent where to demand additional evidence:

- Did price probe, reject, reclaim, or accept beyond the area?
- Did aggressive volume create proportional price progress?
- Did delta or CVD confirm the move, stall, or reverse?
- Did liquidity absorb and replenish, or did the book clear?
- Did value, VWAP, an HVN, LVN, gap, opening range, or higher-timeframe level coincide?
- Did ES and NQ participate together, or did one lead while the other lagged?
- Did VIX and implied volatility confirm fragility or contradict it?
- Did the GEX level persist, strengthen, disappear, or migrate on the next snapshot?

A level touch alone is not an entry.

### Conditional Regime Use

In modeled negative gamma:

- accepted breaks may travel faster;
- failed breaks may expose trapped participants sharply; and
- a put wall can fail as support and become more informative through that failure.

In modeled positive gamma:

- rotation, pinning, and mean reversion may be more likely;
- breakout attempts may require stronger proof of acceptance; and
- level migration or volatility expansion can invalidate the stabilizing prior.

The map supplies a prior. Realized price and order-flow evidence decide whether that prior remains
credible.

## Markeitect Interpretation Framework

### Candidate Trapped Sellers At A Lower Concentration

Supporting observations may include aggressive selling, strongly negative delta, little downside
progress, bid absorption, failure to build value below the area, a reclaim, weakening VIX, and ES/
NQ no longer making synchronized lows.

Contradicting observations include sustained acceptance below, price and CVD falling together,
expanding volatility, broad cross-index participation, and the wall or magnet migrating lower.

### Candidate Trapped Buyers At An Upper Concentration

Supporting observations may include aggressive buying, little upside progress, replenishing
offers, delta/CVD divergence, rejection back below the area, and failure by the leading index to
pull the lagging index through.

Contradicting observations include acceptance above, a successful retest, value migration higher,
sustained price/CVD progress, broad participation, and the concentration migrating higher.

### Gamma Flip

Crossing a previously reported flip is insufficient. Stronger evidence requires a fresh map still
placing the flip there, acceptance beyond it, coherent volatility behavior, and a measurable
change in realized auction character. A flip is a modeled regime boundary, not a trigger.

## Claims Markeitech Must Not Make From GEX Alone

Markeitech must not infer or state that:

- dealers are certainly net long or short gamma;
- put-heavy exposure predicts a decline;
- a wall must act as support or resistance;
- a magnet must attract price;
- crossing a wall or flip caused a move;
- hedging will occur at a known time, venue, or instrument;
- the displayed straddle is a guaranteed range;
- a GEX map selects the correct option contract; or
- a vendor's modeled exposure is observed order flow.

When methodology or inputs are unavailable, the correct output is a reported vendor level with
explicit uncertainty, not a reconstructed dealer-position claim.

## Future Markeitech Evidence Contract

A provider-neutral GEX observation would need:

- observation identity, provider, provider model/version, and methodology class;
- underlying, option root, expiration set, settlement style, multiplier, and currency;
- reference instrument, reference price, timestamped basis, and market session;
- exchange timestamp, provider snapshot timestamp, ingestion timestamp, and latency;
- aggregate sign/value/unit/scaling and call/put contribution definitions;
- strike-level concentrations with exact strike and expiration provenance;
- wall, magnet, flip, and straddle definitions rather than names alone;
- open-interest date/age, quote age, strike coverage, IV-surface quality, and Greek source;
- position-sign assumption and whether evidence is OI, flow, or hybrid;
- stale, partial, conflicted, corrected, and unavailable states; and
- formula/parameter version with policy bounds and rollback identity.

Raw option-chain observations remain outside PostgreSQL unless a later reviewed retention decision
requires otherwise. PostgreSQL may audit source lifecycle, quality summaries, accepted derived
state transitions, agent use, and outcomes. A displayed numerical update is not automatically a
durable semantic event.

## Validation Path

1. Obtain licensed access and document provider methodology and retention rights.
2. Capture timestamped snapshots with complete provenance and evidence health.
3. Normalize prices and basis across SPX, SPY, ES, QQQ, and NQ explicitly.
4. Compare provider levels with independent chain-derived calculations where inputs permit.
5. Track level persistence and migration rather than judging isolated screenshots.
6. Evaluate conditional outcomes: rejection, acceptance, traversal speed, realized volatility,
   delta/CVD response, and cross-instrument participation.
7. Keep vendor reports and internal derivations as separate evidence sources.
8. Admit GEX to the advisory agent only after it can cite the exact snapshot, methodology,
   freshness, conflicts, and limitations used in its reasoning.

## Operator Checklist

Before the session:

- record the map identity, timestamp, GEX sign, walls, magnet, flip, and straddle;
- map them against value, profile nodes, gaps, VWAP, opening ranges, and major scheduled events;
- identify basis differences; and
- compare with earlier snapshots for persistence or migration.

At a location:

- observe aggression versus price progress;
- distinguish a probe from acceptance;
- check delta/CVD, liquidity response, ES/NQ leadership, and VIX;
- refresh the map before relying on a stale boundary; and
- abstain when source health or cross-market evidence conflicts.

After the interaction:

- record whether the area rejected, accepted, traversed, or migrated;
- preserve the evidence available at decision time;
- avoid hindsight relabeling; and
- evaluate the hypothesis separately from the outcome of any option expression.

## References

- [Options Industry Council: Gamma](https://prd-web.optionseducation.org/advancedconcepts/gamma)
- [Cboe: Gamma squeezes and option-market mechanics](https://cdn.cboe.com/resources/education/research_publications/gammasqueezes.pdf)
- [Cboe: Evaluating the market impact of SPX 0DTE options](https://www.cboe.com/insights/posts/volatility-insights-evaluating-the-market-impact-of-spx-0-dte-options/)
- [Cboe: 0DTE positioning trends and market impact](https://www.cboe.com/insights/posts/0-dt-es-decoded-positioning-trends-and-market-impact)

No indexed first-party OFS/UMR methodology was found during this review. Its exact field formulas
must therefore remain unverified until the provider supplies authoritative documentation.
