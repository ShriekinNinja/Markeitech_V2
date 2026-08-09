# Markeitech Project Charter

Markeitech is a live-first market-analysis and decision-support system built by
Markeitect and Kite for discretionary index trading. Its current purpose is to
turn reliable underlying-market data into deterministic, inspectable context
and signals that can inform manual options trades. It is not an HFT system and
does not currently execute orders.

The original greenfield brief is preserved in
[`docs/archive/initial-greenfield-brief.md`](docs/archive/initial-greenfield-brief.md).
That document records the project's origin, but this charter governs current
work.

## Current Product Direction

- ES and SPY are the initial V2 instruments. Instrument roles, acquisition
  cadence, and later watchlist behavior remain Stage 8 decisions.
- Options are the primary intended trade expression. The long-term product goal
  is a deterministic semantic-event stream, multidimensional rolling market
  state, options context, and an advisory AI observer that suggests and explains
  0DTE opportunities.
- Native provider observations, deterministic facts, semantic events, persistent
  entities, rolling state, model outputs, AI interpretations, and execution
  authority remain separate boundaries.
- Discord provides the first concise human projection. A full UI remains a later
  concern.
- Crypto product work is out of current scope. Provider-neutral support for
  continuous-session instruments may remain where it costs no product focus.
- Live operation is the only current product path. Replay and backtesting are out
  of scope until Markeitect explicitly reopens them and must not drive current
  storage, contracts, or infrastructure.

Keep analytical instruments distinct from trade-expression instruments. A
signal derived from NQ, ES, SPX, volatility, or equity context may later inform
an option contract without treating that option as the source of the underlying
market thesis. Any future linkage must be explicit, versioned, and inspectable.

## Engineering Invariants

Use NautilusTrader extensively where its semantics fit. Markeitech may own
product-specific configuration, validation, analytics, persistence, signals,
and operator projections when duplicating those concerns inside Nautilus would
reduce clarity or correctness. Document meaningful ownership decisions.

The live market-data runtime is centered on a NautilusTrader `LiveNode`.
Interactive Brokers access remains manual, explicitly confirmed, data-only, and
read-only. Do not add order routing until a separately reviewed execution and
risk stage.

Maintain these invariants:

- explicit contract identity with no silent rollover
- one owner for every live subscription and canonical event stream
- UTC timestamps internally and explicit IANA timezones for session logic
- bounded queues and no blocking I/O in live data callbacks
- provider-specific payloads contained within adapters
- required durable state written before dependent lifecycle progress is published
- deterministic, versioned analytics, evidence, signal definitions, and ML data
- restart recovery that verifies persisted state before resuming evaluation
- active and background instruments evaluated through the same analytical path
- analytics independent of console, Discord, WebSocket, and UI transports
- strategy or presentation failure must not stop ingestion

PostgreSQL currently owns only operational run and system-health records. Redis,
SQLite, Parquet, and raw market-data retention are not selected V2 infrastructure.
Market data that IB can fetch again should not be stored without an approved live
consumer and retention requirement.

## Evidence And Interpretation

Authoritative source data, derived evidence, and inferred evidence must remain
distinguishable. Never represent inferred order flow as exchange-provided truth
or fabricate historical delta from histogram data.

V2 analytics begin from a blank page after the runtime foundation is accepted.
The intended intelligence path is deterministic measurement, typed analytical
entities, semantic observations and interpretations, multidimensional rolling
state, options context, narrow ML scores, and an advisory AI observer.

ML may later rank versioned deterministic evidence. AI may synthesize evidence,
surface contradictions, and suggest an options expression with triggers and
invalidation. Neither may become an unversioned source of market truth, control
IB, or bypass explicit risk controls.

## Quality And Validation

Prioritize correctness, determinism, resilience, maintainability, and operator
utility over microsecond latency. Tick loss may reduce aggression fidelity, but
must not be hidden or automatically corrupt bar-based context.

Tests should scale with the behavioral risk and include deterministic fixtures,
persistence and restart coverage, bounded-runtime failure cases, and manual IB
acceptance where real provider behavior matters.

Screenshots and external chart studies are welcome calibration evidence when the
instrument contract, timezone, session, window, timeframe, and study settings
are recorded. A successful trade or visual match is useful evidence, not broad
statistical validation.

## Working Agreement

- Pause and raise architectural concerns when implementation exposes them.
- Commit the previously approved batch before starting a new change batch.
- Leave each new batch uncommitted for Markeitect's IDE review.
- Commit reviewed changes with a detailed message after approval.
- Keep current status separate from implementation history and future intent.
- Do not claim validation that has not occurred.

See [`docs/README.md`](docs/README.md) for the documentation authority order and
navigation map.
