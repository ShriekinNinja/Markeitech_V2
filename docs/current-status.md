# Current Status

Last reviewed: 2026-07-15

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
- Concise lifecycle and runtime-health console projections

## Current Boundary

Stage 5C.3c is implemented and live-observed. The managed bounded consumer
restores verified signal state, rebuilds warmup state without emitting
historical setups, evaluates committed live feature bundles, persists lifecycle
changes atomically, and projects concise signal events plus runtime health.

Stage 5D.1 now protects the Armed observation window from two false
invalidation paths: soft Direction degradation and favorable or unresolved
Location departure. Only a fully qualified opposite Direction or configured
consecutive adverse breaches of the immutable entry geometry terminate the
setup before confirmation.

The next slice is Stage 5D.2: wire the existing cadence-bounded,
provider-aware Aggression policy into the managed live runtime. It will consume
active classified-tick windows and background bar-impulse windows, then persist
and project explicit Armed-to-Triggered or Armed-to-Expired transitions. The
pure Aggression evaluator exists and is tested; live lifecycle composition does
not yet call it.

## Validation Debt

- NQ live operation has been exercised more thoroughly than ES, indices, and
  equities. Broader provider and contract coverage remains an acceptance task.
- Post-commit Direction/Location evaluation and console lifecycle output have
  live evidence, but the new departure policy still awaits a live observation.
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
profitable discretionary puts trade.

That observation is evidence that the operator projection can be useful. It is
not statistical validation, signal calibration, or evidence for automation.
