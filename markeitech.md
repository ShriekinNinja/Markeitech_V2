# Markeitech Project Charter

Markeitech is a live-first market-analysis and decision-support system built by
Markeitect and Kite for discretionary index trading. Its current purpose is to
turn reliable underlying-market data into deterministic, inspectable context
and signals that can inform manual options trades. It is not an HFT system and
does not currently execute orders.

This charter governs current product and engineering work. Historical source is recoverable
through Git history but does not define current behavior.

## Current Product Direction

- ES and SPY are the initial V2 bootstrap instruments, not a permanent universe.
  The observation universe, acquisition cadence, enabled analysis capabilities,
  and temporary market focus may change while the system runs.
- SPXW, SPY, and QQQ 0DTE options form the initial configurable expression universe. No expression
  instrument is globally preferred. The long-term product goal is a deterministic semantic-event
  stream, multidimensional rolling market state, options context, and an advisory AI observer that
  maintains, ranks, and explains multiple concurrent 0DTE opportunities.
- The future advisory AI observer is named **Sir Loke**. Its governing maxim is Sherlock Holmes's
  principle: "When you have eliminated the impossible, whatever remains, however improbable, must
  be the truth." Sir Loke must eliminate through cited evidence and deterministic policy, preserve
  unresolved uncertainty, and abstain when the remaining case is not sufficiently supported.
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
- provider-facing demand reconciled independently from analytical consumers
- no fixed one-active-instrument limit on granular observation
- analytics independent of console, Discord, WebSocket, and UI transports
- strategy or presentation failure must not stop ingestion

## Configuration And Optimization Principle

Do not encode variable market assumptions, analytical thresholds, instrument preferences, timing
windows, scoring weights, policy choices, or resource budgets as hidden constants.

Anything which may reasonably vary by instrument, asset class, session, regime, market condition,
data quality, infrastructure capacity, operator preference, experiment, or future model
optimization must be explicit, typed, scoped, bounded, versioned configuration. Each such
parameter must define:

- a stable identity, meaning, unit, and type;
- an explicit documented default rather than an unexplained magic number;
- its scope, such as global, capability, asset class, instrument, contract, session, or regime;
- validation and an authorized minimum/maximum envelope;
- whether it is startup-only, between-session mutable, safely runtime mutable, operator-controlled,
  policy-controlled, or optimization-eligible;
- its source, such as default, checked-in configuration, operator, deterministic policy, model, or
  experiment;
- version and effective time so every result can identify the parameters which produced it; and
- safe rejection, expiry, rollback, and audit behavior where runtime changes are allowed.

Design optimization-ready interfaces even when the first implementation reads startup
configuration only. Models and agents may propose or apply changes only through typed,
policy-checked intents within authorized envelopes and resource budgets. They may not mutate
arbitrary configuration, rewrite history, bypass validation, or silently change live behavior.

This principle does not make system truth negotiable. Schema integrity, type safety, evidence
honesty, source identity, authorization boundaries, audit requirements, and the prohibition on
unauthorized execution remain code-enforced invariants. Tunable limits belong in configuration;
the enforcement of those limits belongs in deterministic code.

PostgreSQL currently owns runtime runs, system-health events, generic operational events, and
compact evidence-recency profiles. Additional analytical or agent state requires an explicit
schema, lifecycle, retention, and recovery decision. Redis, SQLite, Parquet, and raw market-data
retention are not selected V2 infrastructure. Market data that IB can fetch again should not be
stored without an approved live consumer and retention requirement.

## Evidence And Interpretation

Authoritative source data, derived evidence, and inferred evidence must remain
distinguishable. Never represent inferred order flow as exchange-provided truth
or fabricate historical delta from histogram data.

Analytics are admitted only through current evidence and architecture review.
The intended intelligence path is deterministic measurement, typed analytical
entities, semantic observations and interpretations, multidimensional rolling
state, options context, narrow ML scores, and an advisory AI observer.

ML may later rank versioned deterministic evidence. AI may synthesize evidence,
surface contradictions, suggest an options expression with triggers and
invalidation, and request policy-approved changes to observation focus,
historical evidence, option snapshots, or analytical capabilities. It acts
through typed intents and deterministic policy; it may not connect to IB,
submit orders, invent evidence, or bypass explicit resource and risk controls.

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
