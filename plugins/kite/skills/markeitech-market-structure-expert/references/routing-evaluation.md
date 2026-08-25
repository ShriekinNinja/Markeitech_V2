# Market Structure Advisor Routing Evaluation

Use this reference when validating discovery, custom-agent delegation, adjacent-specialist
handoffs, or proportional output. These are static expectations until exercised after the Kite
plugin is refreshed and reinstalled in a fresh Codex thread.

## Canonical Coverage Decision

`markeitech-market-structure-expert` is the canonical specialist for deterministic Markeitech
market-structure evidence and entity semantics. Do not install or route to a second overlapping
general market-structure-and-auction advisor. Session or gap geometry may remain an input here when
it affects entity identity. Acceptance, rejection, breakout, failed-auction, trapped-participant,
and opportunity semantics belong to later semantic-event coverage. Observed aggressor flow,
absorption, delta, CVD, and participant-outcome claims belong to microstructure/order-flow
coverage.

## Static Routing Cases

| Request | Expected specialist behavior | Prohibited shortcut | Status |
| --- | --- | --- | --- |
| Review whether confirmed pivots leak future evidence | Delegate to `markeitech_market_structure_advisor` | Do not publish a right-span pivot at pivot time | PENDING |
| Review FVG formation, fill, expiry, or zone constituent lineage | Delegate to `markeitech_market_structure_advisor` | Do not infer institutional intent, future fill, or tradeability | PENDING |
| Decide whether candle volume proves absorption at a level | Market-structure advisor states the fidelity boundary, then hands off to microstructure/order-flow coverage | Do not counterfeit observed order flow from OHLCV | PENDING |
| Review a Nautilus actor callback, message bus, cache, lifecycle, or native capability used by market structure | Consult `markeitech_nautilus_advisor` for framework truth; consume only its verified result in the market-meaning review | Do not let this advisor settle Nautilus mechanics | PENDING |
| Define acceptance, rejection, breakout, failed-auction, or trapped-participant events around a zone | This advisor may state entity prerequisites and forbidden inferences, then require semantic-event coverage | Do not absorb semantic interaction events into geometric entities | PENDING |
| Select an SPXW, SPY, or QQQ option from underlying structure | Hand off to options coverage | Do not perform contract selection or imply a trade | PENDING |
| Estimate expectancy, predictive validity, or promotion thresholds | Hand off to statistics, evaluation, or ML coverage | Do not infer edge from fixtures, charts, or one session | PENDING |
| Answer one narrow tie-handling or lifecycle question | Return a compact evidence record | Do not emit a mostly empty twelve-column matrix | PENDING |
| Review several competing structure definitions or interacting entity families | Return the full Market Structure Evidence Matrix | Do not hide conflicts or collapse horizons | PENDING |

## Fresh-Thread Acceptance

After integration:

1. update the Kite plugin cachebuster with the repository-approved helper;
2. reinstall `kite` from the configured local `markeitech` marketplace;
3. start a new thread so Codex discovers the new skill and custom role;
4. exercise representative positive, negative, overlap, and proportional-output cases above; and
5. replace `PENDING` only with observed results, including selected advisor, advisor order, skill
   loading, evidence labels, stop behavior, output shape, and any unexpected routing.

Repository parsing or skill validation does not prove discovery, delegation, or behavioral
quality. Keep failed or ambiguous cases visible until corrected and rerun.
