# Development Guidelines

These guidelines capture the product and collaboration lessons established
while building and operating Markeitech. They supplement the project charter.

## Product Posture

Markeitech serves a discretionary operator first. Optimize for trustworthy
context, inspectable evidence, useful timing, and recovery rather than HFT
latency or automated execution.

Separate the market used to form a thesis from the instrument used to express
the trade. NQ and correlated markets may provide Direction, Location, and later
Aggression while Markeitect expresses the decision through an option. Do not
force options contracts into the active/background market-data role model until
their distinct chain, expiry, strike, liquidity, and Greek semantics are
designed.

The current priority order is:

1. dependable live operation
2. human-readable console signals and analysis
3. Discord webhook delivery and reports
4. replay and backtest validation
5. strategy runtime and research workflows
6. gateway and UI
7. execution only after explicit risk design and approval

This ordering is a product priority, not permission to make replay impossible.
Live and replay paths should share deterministic domain logic where practical.

## Instrument Model

Exactly one instrument is logically active at a time and receives tick-by-tick
data. It can be switched during runtime through a guarded handoff.

All enabled instruments warm up across configured analytical timeframes before
live evaluation. Background instruments receive live 1-minute bars and use the
same analytics and signal definitions as the active instrument when evidence is
available. Active status affects data cadence and operator emphasis, not the
importance or correctness of background analysis.

NQ is the first active focus. ES, index, and equity context are important to
index trading. Crypto was useful for an early continuous-market connectivity
test but is not an active product priority.

## Runtime Ownership

Prefer NautilusTrader for instruments, market-data models, actors, message-bus
integration, clocks, lifecycle, and provider adapters. Extend it through narrow
Markeitech boundaries when the product requires semantics Nautilus does not own.

Do not pursue framework purity at the expense of clear ownership. The feature
catalog, SQLite control plane, DLA analytics, durable signal lifecycle, and
operator projections are legitimate Markeitech responsibilities.

Only one component may own a subscription or canonical stream. Native IB access
is allowed only for a capability Nautilus does not expose and must share the
same contract, timestamp, source, health, persistence, and deduplication rules.

## Data And Evidence

- Keep provider source and explicit contract identity on canonical boundaries.
- Store time in UTC and apply explicit IANA timezones for market sessions.
- Distinguish historical, live, restored, derived, and inferred evidence.
- Do not silently fill gaps or invent trade direction from unsupported data.
- Treat completed bars as durable analytical facts; treat in-progress state as
  replaceable runtime state.
- Advance dependent state only after the evidence it references is committed.
- Version feature definitions, signal definitions, schemas, and future ML data.

Because Markeitech is not HFT, isolated missing ticks need not halt bar-based
analysis. They must remain observable and lower the confidence or fidelity of
tick-sensitive aggression evidence.

## Analytics And Signals

Analytics must be deterministic and transport-neutral. Console, Discord, a
future gateway, and a future UI consume projections; they do not calculate
market truth.

The first formal model is DLA:

- Direction describes the broader market condition.
- Location identifies repeatable, evidence-backed areas of interest.
- Aggression will assess bounded near-real-time confirmation.

Current signal state progresses monotonically from Candidate to Armed to
Triggered, with Invalidated and Expired terminal states. Signal identity must be
stable across ordinary feature refreshes and anchored to a market-semantic
episode rather than a timestamp alone.

No signal is an order instruction. Do not infer product validation from one
profitable trade, one screenshot, or one live session.

## ML And AI

Build deterministic features and labels before training models. Persist the
feature definition and model identity with every inference.

ML may later rank, classify, or calibrate deterministic candidates. AI may
summarize and explain persisted evidence for an operator. Neither may silently
alter canonical data, invent evidence, control the IB connection, or bypass
reviewed signal and risk boundaries.

## Operator Validation

Ask for screenshots when visual comparison can resolve ambiguity. TradingView,
Tradovate, and order-flow references can all be useful, provided the comparison
records:

- exact contract and venue
- chart and API timezone
- session and start/end timestamps
- timeframe and visible window
- study inputs, row size, value-area percentage, and price source
- whether a study uses fixed range, visible range, or session boundaries

Record disagreements as calibration work. Do not tune solely until one image
looks similar.

## Collaboration And Git

Work in reviewable batches:

1. Commit the previously approved batch before starting new changes.
2. Explain the intent and meaningful tradeoffs before substantial edits.
3. Leave the new batch uncommitted for Markeitect to inspect in the IDE.
4. Commit only after explicit approval, using a detailed message.
5. Use a dedicated branch for a new stage or intentionally divergent work.

Pause when an architectural assumption becomes questionable. A short design
review is cheaper than carrying a convenient workaround into persistence or
live-runtime behavior.

## Documentation Discipline

Keep current status, implementation history, and future plans separate. Update
present-tense architecture when a future boundary becomes implemented. Preserve
accepted decision rationale, but do not use the decisions register as a task
tracker.

State validation honestly. Assumed provider coverage, untested instruments,
manual observations, and deferred acceptance all belong in validation debt.

Update the smallest authoritative document whenever implementation, product
direction, or validation status changes. Avoid copying the same status into
multiple files; link to `current-status.md` or the roadmap instead. Move
completed roadmap detail into history as part of closing a reviewed slice.
