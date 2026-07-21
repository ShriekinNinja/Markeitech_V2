# Markeitect Model Handoff

Date: 2026-07-21

Source branch: `codex/trading-framework-research`

Primary live evidence:
`data/logs/markeitech-live_2026-07-20_130814:241.jsonl`

## Why This Handoff Exists

The July 20 run showed that Markeitech's runtime, persistence, analytics, and
signal-lifecycle architecture are strong enough to support a more capable
trading model. It also showed that improving the mechanics of the existing DLA
interpretation did not make its decisions sufficiently useful to Markeitect.

The project will therefore stop treating inherited DLA/Fabio semantics as the
primary trading intelligence. They remain available as prior research and a
versioned signal definition. New trading-quality work begins with an explicit
Markeitect Model derived from Markeitect's actual decision process.

## July 20 Run Evidence

The principal run lasted approximately 6 hours and 7 minutes. It completed 736
signal evaluations over 968 committed feature revisions with no runtime errors,
rejected handoffs, projection errors, or render errors. Active NQ order-flow
classification ended near 98.2% of observed volume.

Signal activity was mechanically busy but operationally weak:

- 90 Armed signals
- 5 Triggered signals: 2 active NQ and 3 background ES
- 73 Invalidated signals
- 16 Expired signals
- 54 invalidations caused by `location_episode_replaced`
- 17 invalidations caused by confirmed acceptance through a location
- 2 invalidations caused by ordinary episode exit

Only about 5.6% of Armed signals Triggered. Sixty percent of all Armed signals
were eventually invalidated because another analytical location replaced the
current one. More Location matches therefore produced more lifecycle churn,
not proportionally more tradeable opportunities.

Direction also changed in broad blocks:

| Instrument | Observed Armed-direction sequence, UTC |
| --- | --- |
| ES | Long 13:09, Short 14:02, Long 16:02, Short 17:10 |
| NQ | Long 13:13, Short 15:02, Long 16:03, Short 18:03 |

These logs are not used as an external market replay and cannot independently
label each direction correct or incorrect. Markeitect's operator review was
that many Long decisions represented Short opportunities and vice versa. The
logged behavior supports the underlying architectural diagnosis: timeframe
Direction agreement plus a nearby aligned level is not a complete trade thesis.

## Diagnosis

The current model can identify trend labels, locations, and subsequent
aggression. It does not yet explain the auction narrative connecting them. The
same price area can be continuation support, failed support, a rejection entry,
an acceptance boundary, a target, or the origin of a reversal. Treating every
new qualifying analytical object as a replacement episode discards that
meaning.

The missing decision layer must reason about:

1. Market state: trend, rotation, transition, and expansion.
2. Auction map: accepted value, rejected areas, targets, and trapped zones.
3. Narrative: where price came from, what it attempted, and whether it
   succeeded.
4. Setup thesis: continuation, rejection, failed breakout, return to value, or
   rotation.
5. Trigger evidence: price action plus available order-flow evidence.
6. Trade contract: entry area, invalidation, targets, hold, and exit conditions.
7. Outcome evidence recorded without hindsight mutation.

## What We Keep

Signal algorithm 1.2 remains valuable infrastructure. It gives the next model:

- coherent price-local Location clusters;
- transparent quality components instead of an opaque confidence score;
- canonical completed-bar interaction states;
- atomic lifecycle and interaction persistence;
- restart restoration of pending rejection and acceptance evidence;
- deterministic tests and operator-readable evidence.

This machinery represented the existing decision model faithfully. Its failure
to improve trading quality is evidence that the decision model must change, not
that the underlying durability and evidence contracts should be discarded.

## Next Branch Boundary

The next branch begins specification of the Markeitect Model. No thresholds,
scores, or indicator combinations should be coded until Markeitect has explained
the model in his own language and that explanation has been translated into
explicit, reviewable domain contracts.

Fabio Valentini, Oliver Velez, Jim Dalton, and other research sources remain
inspiration and comparative vocabulary. They are not the authority for the new
model. Markeitect has final decision authority; Kite is responsible for turning
that judgment into honest, testable system behavior.
