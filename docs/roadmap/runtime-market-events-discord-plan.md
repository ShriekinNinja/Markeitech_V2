# Runtime, Market Events, And Discord Delivery Plan

Started: 2026-07-17

Owners: Markeitect and Kite

Motto: No Obstacles, Only Challenges.

This plan turns the immediate product priorities into measurable delivery
boundaries. Markeitect owns scope, acceptance, and the final call. Kite owns
architecture, integration, and engineering recommendations. Workers may handle
bounded tests, investigations, or independent reviews; they do not make product
or architectural decisions.

## Objective

Deliver a trustworthy live decision-support path in which:

- raw ingestion, analytics, feature persistence, context events, and signal
  evaluation either continue advancing or fail visibly at a recoverable boundary
- Fabio Direction-Location-Aggression remains one shadow setup family rather
  than the organizing center of Markeitech
- deterministic market interactions describe approaching, entering, testing,
  holding, rejecting, breaking, reclaiming, and exiting meaningful structures
- useful market, signal, and runtime events reach Discord without blocking the
  Nautilus event loop or bypassing durable truth
- live acceptance distinguishes mechanical correctness from trading usefulness

## Dreams Versus Reality

| Desired outcome | Starting reality | Required evidence | Status |
| --- | --- | --- | --- |
| Signal runtime is mechanically trustworthy | A valid suppressed-episode exit terminated signal evaluation on 2026-07-16 | Regression, restart, and live evidence show continuous processing | Deterministic repair in review |
| Signal failure cannot silently cascade | The stopped consumer filled a 2,048-revision handoff and later stopped feature persistence | Immediate health projection and deterministic recovery behavior | Not started |
| Market interactions are first-class evidence | Trend and value transitions exist; level interaction episodes do not | Versioned contracts, pure state machine, persistence, restart, and live projection | Not started |
| Discord is an operator surface | Durable signal outbox foundations exist; no webhook delivery runtime exists | Durable intent, bounded delivery, retry, dedupe, recovery, and live message | Not started |
| Fabio is useful but not dominant | DLA lifecycle exists but has not passed trading-usefulness review | Clearly marked shadow output alongside independent market events | Partially true |
| Core runtime remains dependable | Raw data, analytics, and operator context continued through long live runs | Continued acceptance with expanded watchlist and new consumers | Strong evidence |

## Slice 1: Runtime Integrity

Repair the suppressed-episode exit defect and close its regression gap.

Required cases:

- expired episode followed by confirmed adverse exit
- expired episode terminated by a Direction-regime change
- restart followed by suppressed-episode exit
- failed committed revision is processed successfully after correction

Preserve fail-closed detection when an ended episode does not match known open
or suppressed state. Do not weaken lifecycle invariants to make the exception
disappear.

Then define the containment boundary for a failed signal consumer. Queue depth,
last successful feature sequence, feature-writer health, and signal-runtime
failure must become visible before saturation. Recovery must reconcile committed
feature revisions deterministically; silently dropping the critical handoff is
not acceptable.

Exit conditions:

- focused and full deterministic suites pass
- signal failure is immediately attributable
- no valid location decision terminates the consumer
- committed revision continuity is preserved across restart
- a short live run shows advancing signal, feature, and context-event sequences

## Slice 2: Market Interaction Lifecycle

Create a setup-independent `LevelInteraction` model over durably committed
market context.

Initial progression:

```text
Approaching -> Entered -> Testing
                         -> Holding
                         -> Rejected
                         -> Broken
                         -> Exited
```

`Reclaimed` may follow a confirmed break when price returns through the same
semantic structure. These are observations, not order instructions.

Every interaction retains instrument, timeframe, active/background role,
semantic level identity, source kind, bounds, approach side, timestamps,
penetration, confirmation counts, feature evidence, and fidelity.

Semantic boundaries:

- `Entered` means price reached the configured zone.
- `Holding` requires configured completed observations showing defense or
  acceptance.
- `Rejected` requires departure toward the approach side after interaction.
- `Broken` requires confirmed acceptance through the opposite boundary.
- `Exited` is neutral when rejection or break is not justified.
- One wick cannot independently claim holding, rejection, or break.

Exit conditions:

- deterministic duplicate, correction, stale-input, and conflict behavior
- atomic event and detector-checkpoint persistence
- restart restoration without historical notification replay
- active and background parity where evidence supports the same semantics

## Slice 3: Operator Relevance

Apply a transport-neutral policy after canonical events exist. It may select,
prioritize, deduplicate, cool down, or suppress notifications, but it cannot
alter market-event truth.

Initial controls:

- active-instrument priority without silencing important background events
- event severity and source-family routing
- minimum confirmation and material-distance thresholds
- developing versus completed evidence
- deduplication and cooldown
- high-value-only `Approaching` notifications

Exit condition: a representative fixture produces a concise useful event stream
without losing the canonical underlying events.

## Slice 4: Discord Projection And Delivery

A lightweight Discord projection actor subscribes to typed Nautilus bus events,
formats bounded operator messages, and creates durable notification intents. It
does not perform HTTP in the synchronous subscriber callback.

A bounded delivery worker owns webhook I/O:

- webhook URLs come only from environment variables
- secrets are never committed, logged, or persisted in payloads
- SQLite outbox state precedes delivery
- delivery identity is idempotent
- rate limits and transient failures use bounded retry with backoff
- final failure enters an observable dead-letter state
- startup resumes pending deliveries without duplicating delivered messages
- delivery failure cannot stop ingestion, persistence, analytics, or signals

Initial routes:

1. Market Events: context and level interactions
2. Signal Lifecycle: setup transitions, with Fabio explicitly marked `SHADOW`
3. Runtime Health: readiness, degradation, queue pressure, failure, and recovery

Ordinary heartbeats do not belong in Discord.

## Slice 5: Acceptance

Deterministic acceptance covers saturation, retry, restart with pending intents,
duplicate publication, rate limiting, server failure, timeout, malformed
responses, projection isolation, secret hygiene, and the full repository suite.

Live acceptance requires:

- advancing signal heartbeats and feature commit sequences
- bounded healthy handoff depth
- no stale restored signals
- correct market-interaction progression
- one successful message per configured Discord route
- no duplicate delivery after restart
- visible runtime degradation and recovery
- uninterrupted raw ingestion

Mechanical acceptance does not imply signal calibration or trading usefulness.

## Credit Guard

Starting balance: 1,062 credits

Recommended reserve: 300 credits for live-run failures and recovery work.

Before each slice, record a Low, Medium, or High forecast, the exact deliverable,
worker assignment, and review boundary. After each slice, Markeitect supplies the
visible balance so aggregate spend can be calculated without inventing billing
data.

| Checkpoint | Forecast | Balance before | Balance after | Credits used | Accepted output | Decision |
| --- | --- | ---: | ---: | ---: | --- | --- |
| Plan established | Low | 1,062 | Pending | Pending | Branch and measurable delivery plan | In progress |
| Slice 1A: lifecycle defect | Medium | 1,062 | Pending | Pending | Repair plus adverse-exit, Direction-exit, and restart regressions; 18 signal-runtime tests pass | In review |
| Slice 1B: containment and health | Medium | Pending | Pending | Pending | Pending | Pending |
| Slice 2: market interactions | Medium-High | Pending | Pending | Pending | Pending | Pending |
| Slice 3: relevance policy | Low-Medium | Pending | Pending | Pending | Pending | Pending |
| Slice 4: Discord vertical slice | Medium-High | Pending | Pending | Pending | Pending | Pending |
| Slice 5: acceptance | Medium | Pending | Pending | Pending | Pending | Pending |

Stop feature work around 300-350 remaining credits unless Markeitect explicitly
changes the reserve. Stop at every coherent review boundary; do not leave
durability, recovery, or lifecycle semantics half implemented.

## Delivery Record

Append reviewed facts here as slices close. Move stable implementation status to
`docs/current-status.md`, accepted architecture to the architecture documents,
and completed slice detail to the implementation history. This plan remains the
record of forecast versus outcome.
