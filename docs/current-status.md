# Current Status

Last reviewed: 2026-07-17

This page is the source of truth for implementation progress. It separates code
that exists from behavior that has received live acceptance.

## Operating Posture

- Live-first discretionary decision support
- Interactive Brokers paper account in read-only/data-only mode
- Explicit-expiry NQ as the first active instrument
- One active tick-by-tick instrument plus live 1-minute background instruments
- Console-first operator workflow
- No automated execution
- No active crypto product work
- Options are the primary manual trade expression; chain ingestion is deferred

## Implemented

### Domain And Configuration

- Versioned canonical contracts for instruments, bars, trades, quotes, context,
  features, and signals
- Explicit active/background roles and guarded runtime switching
- Contract identity and session-aware configuration validation
- Timeframe-specific analytical warmup plans

### Live Market Data

- NautilusTrader `LiveNode` with the Interactive Brokers adapter
- Historical warmup for every enabled instrument
- Active-instrument tick-by-tick subscriptions
- Background live 1-minute bars
- Bounded normalization and event handoff
- Duration-limited acceptance runs and continuous paper-data runs
- Recovery planning, stale-data handling, and observable shutdown

### Persistence And Recovery

- Nautilus Parquet catalog for bulk time-series data
- SQLite control plane for identities, checkpoints, recovery, features, signals,
  transitions, and notification intents
- Serialized bounded catalog writes
- Restart verification and checkpoint recovery
- Retention and offline SQLite compaction tooling

### Analytics

- Multi-timeframe EMA, trend, VWAP, support/resistance, FVG, and session context
- Prior-session and named-session levels
- Current, prior, named-session, and composite volume profiles
- Timeframe-specific deep warmup, including daily and hourly analytical context
- Deterministic Direction and Location scores with reason codes
- Active-first, bounded, change-aware operator context logs
- Versioned durable feature snapshots

### Signals

- Versioned signal definitions and stable semantic identity
- Candidate, Armed, Triggered, Invalidated, and Expired contracts
- Append-only, hash-chained SQLite lifecycle persistence
- Atomic signal transition and notification-intent persistence
- Direction regime tracking
- Direction-aligned location qualification
- Repeatable location episode tracking
- Soft Direction degradation preserves open regimes while blocking Trigger
- Directional Location departure classification with confirmed adverse breach
- Restart restoration of verified open signal state
- Bounded post-commit live feature composition and Direction/Location evaluation
- Equal evaluation path for active and background instruments
- Durable role-selected Aggression and follow-through evaluation
- Atomic Armed-to-Triggered and Armed-to-Expired lifecycle transitions
- Restart-stable expiry suppression for unchanged Location episodes
- Concise lifecycle and runtime-health console projections

## Current Boundary

Stage 5D.3 has live evidence across the full Candidate, Armed, Invalidated, and
Expired lifecycle. The managed bounded
consumer restores verified signal state, evaluates durably committed feature
and Aggression evidence, persists transitions atomically, and projects concise
signal events plus runtime health. Its corrected legacy recovery path has also
survived live restart. The 2026-07-16 run exposed a valid expired-episode exit
which terminated the signal consumer; its deterministic repair and adverse,
Direction-change, and restart regressions are complete for review but still
require live acceptance.

Stage 5D.4 is active. Signal-runtime failures retain phase, input identity, last
successful commit sequence, exception, and traceback. The 2026-07-16 failure
provided live acceptance for those diagnostics: it identified ES feature commit
sequence 3693, the last successful sequence 3692, and the exact location-episode
exception. Active trade classification uses bounded event-time quote history
and accounts for every classified or rejected observation; its short-run live
evidence is promising but not a full-session calibration.

The first event-spine vertical slice is also test-complete. Durable feature
revisions become compact versioned notices, cross a bounded thread-safe bridge,
and publish on the Nautilus event-loop thread to a dedicated operator projection
actor. Bus rejection is explicitly counted but cannot invalidate already-
committed evidence or the existing critical signal handoff. Live publication
is now observed for active and background features. One idempotently repeated
feature notice exposed and produced a bounded consumer-deduplication fix.
Graceful shutdown counters remain the next acceptance evidence because the
review run ended without entering Nautilus's logged stopping lifecycle.

The same short 2026-07-16 run classified 64 of 66 active NQ trades and 91 of 94
volume units, reporting a 96.81% classified-volume ratio with explicit reasons
for the remaining two observations. This is strong evidence for the corrected
event-time classifier, but it is not yet full-session Aggression calibration.

Context Event semantics, durable recovery, and live runtime wiring are
deterministic-test complete for review. Immutable contracts and a pure ordered detector cover
trend and coarse value-area region transitions, suppress initial, duplicate,
stale, and same-timestamp correction output, and break comparison across
unavailable evidence. SQLite schema 10 atomically commits emitted transitions
with a compact detector checkpoint; no-change revisions still advance the
checkpoint. The existing bounded feature-writer thread owns ordered processing;
startup seeds new streams from their latest feature and reconciles only durable
checkpoint gaps without historical projection. Newly committed transitions
cross the event bridge to a dedicated non-blocking projection actor. Live
transition publication is observed; restart acceptance remains outstanding.

The same 2026-07-16 signal failure exposed a delayed containment problem. The
stopped signal consumer left its critical feature handoff undrained. After the
2,048-revision capacity filled, feature persistence failed closed at commit
sequence 5747 around 16:08 UTC. Raw tick and canonical bar persistence plus
in-memory operator context continued until shutdown around 18:25 UTC. This was
not observed raw-data loss; it was a signal outage followed by feature and
projection loss. Durable catch-up and earlier handoff-health visibility are the
next reliability boundary.

The 2026-07-15 run separated operational success from trading usefulness. The
LiveNode, market-data ingestion, persistence, recovery, analytics, and operator
context continued through London and New York observation. The initial Fabio
Direction-Location-Aggression definition armed and expired setups, but produced
no Triggered transition and its output did not pass Markeitect's discretionary
trading-usefulness review. The lifecycle implementation is retained as a
deterministic shadow setup family; it is not a trusted trading signal.

The same run exposed an observability defect. At 15:30:08 UTC the signal runtime
reported `FAILED` after 889 revisions, 676 evaluations, 47 lifecycle writes,
221 confirmation evaluations, and 12 expirations, while the main LiveNode and
analytics continued. The heartbeat did not include the underlying exception.
Failure-cause visibility and classified-tick fidelity accounting are therefore
the first Stage 5D.4 acceptance gates.

An experimental, manually invoked Plotly analytics chart is available on the
current branch. It reads persisted evidence and does not participate in the
LiveNode or canonical analytics path.

## Validation Debt

- NQ live operation has been exercised more thoroughly than ES, indices, and
  equities. Broader provider and contract coverage remains an acceptance task.
- Signal failure diagnostics have live acceptance. Event-time trade
  classification has healthy short-run evidence but not a full-session
  calibration.
- The 2026-07-15 run classified only a small fraction of observed trade volume.
  Corrected timestamp alignment and explicit unclassified reasons need new live
  evidence before delta, CVD, or tick Aggression can be trusted.
- The committed-feature event bridge and operator consumer have reviewed live
  publication evidence; graceful shutdown-health evidence remains outstanding.
- Context-transition persistence and restart restoration are deterministic-test
  complete and connected to the live event actor. Live transition publication
  is observed; live restart acceptance remains outstanding.
- A failed signal consumer can eventually saturate the critical feature
  handoff and stop later feature persistence. Queue-health projection and a
  deterministic committed-revision catch-up policy remain outstanding.
- Stage 5D.3 has deterministic active, background, expiry, race-order, and
  restart tests plus live Armed and Expired evidence, but no live Triggered
  evidence and no trading-usefulness acceptance.
- Tick gaps and damaged tick windows are observable; their effect on future
  Aggression confidence still needs an explicit policy.
- Selected profile, FVG, session, and context values have been compared with
  external charts. The full analytical system has not been independently
  calibrated across many sessions and regimes.
- Replay and backtest reproducibility remain designed obligations rather than a
  completed runtime.
- The frontend is only a skeleton and is not part of the present operator path.

## Deliberately Deferred

- Stage 5E composite scoring, suppression, and expiry refinement
- Discord webhook delivery and scheduled reports
- Options contract discovery, chain snapshots, and options-derived context
- ML ranking and AI explanation
- Strategy runtime
- Replay and backtesting implementation
- WebSocket gateway and UI
- Execution and risk controls
- Redis coordination unless a demonstrated runtime need appears

## Acceptance Evidence

The continuous live context runtime has completed warmup, emitted context for
active and background instruments, survived operator restarts, and continued
running during live observation. On 2026-07-14, Markeitect followed a Direction
change from `+2` to `-1` over roughly 45 minutes and used that context in a
profitable discretionary puts trade. On 2026-07-15, the broader runtime and
analytics remained useful throughout extended live observation, while the first
Fabio signal definition did not provide useful trading guidance and its managed
consumer later failed without a causal operator message.

That observation is evidence that the operator projection can be useful. It is
not statistical validation, signal calibration, or evidence for automation.
