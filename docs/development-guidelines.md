# Development Guidelines

These guidelines capture the product and collaboration lessons established
while building and operating Markeitech. They supplement the project charter.

## Product Posture

Markeitech serves a discretionary operator first. Optimize for trustworthy
context, inspectable evidence, useful timing, and recovery rather than HFT
latency or automated execution.

Separate the markets used to form a thesis from the instrument used to express
the trade. Underlyings, indexes, futures, volatility, sectors, and other context
may inform an options decision without becoming the traded product. Options
require distinct chain, expiry, strike, liquidity, and Greek semantics.

The current priority order is:

1. dependable live operation
2. human-readable console signals and analysis
3. Discord webhook delivery and reports
4. strategy runtime, ML, and agent research workflows
5. gateway and UI
6. execution only after explicit risk design and approval

Replay and backtesting are outside current scope until Markeitect explicitly
reopens them. Do not add storage or abstractions for that hypothetical path.

## Instrument Model

Do not encode V1's one-active-instrument and background-1-minute-bar model as a
V2 invariant. V2 distinguishes the trade universe, dynamic observation
universe, active analytical capabilities, and temporary focus. Multiple
instruments may receive granular continuous data when justified and supported.

SPXW, SPY, and QQQ 0DTE options form the initial configurable trade-expression universe. No
instrument is preferred by implementation or configuration. The agent may maintain and rank
multiple simultaneous opportunities. SPY, QQQ, SPX, ES, and NQ are useful initial evidence
examples, not a complete or fixed observation universe. Crypto is not a current product priority.

Analytical capabilities declare the native feeds and historical evidence they
require. The acquisition owner expands approved demand, coordinates provider
requests, and publishes honest lifecycle facts. An agent may later request
policy-approved changes to focus and capability activation, but does not call
IB or own deterministic analysis.

## Runtime Ownership

Prefer NautilusTrader for instruments, market-data models, actors, message-bus
integration, clocks, lifecycle, and provider adapters. Extend it through narrow
Markeitech boundaries when the product requires semantics Nautilus does not own.

Do not pursue framework purity at the expense of clear ownership. Product-specific analytical
entities, semantic events, rolling state, agent policy, and operator projections may be
legitimate Markeitech responsibilities after their requirements are approved.

Only one component may own a subscription or canonical stream. Native IB access
is allowed only for a capability Nautilus does not expose and must share the
same contract, timestamp, source, health, persistence, and deduplication rules.

## Data And Evidence

- Keep provider source and explicit contract identity on canonical boundaries.
- Store time in UTC and apply explicit IANA timezones for market sessions.
- Distinguish historical, live, restored, derived, and inferred evidence.
- Do not silently fill gaps or invent trade direction from unsupported data.
- Treat completed bars as immutable observations within one live runtime unless an approved
  provider-revision policy says otherwise.
- Do not require durable raw market data or feature history without an approved live consumer.
- Version feature definitions, signal definitions, schemas, and future ML data.

Because Markeitech is not HFT, isolated missing ticks need not halt bar-based
analysis. They must remain observable and lower the confidence or fidelity of
tick-sensitive aggression evidence.

## Analytics And Intelligence

Analytics must be deterministic and transport-neutral. Console, Discord, a
future gateway, and a future UI consume projections; they do not calculate
market truth.

V2 analytics begin from a blank page. Do not reactivate V1's DLA model, signal lifecycle,
indicators, or thresholds implicitly. New capabilities must declare their inputs, warmup,
fidelity, configuration, outputs, and resource cost before implementation.

Semantic events should represent meaningful changes rather than duplicate raw observations.
Rolling state, ML outputs, and agent interpretations must retain evidence lineage. No event,
score, or agent proposal is an order instruction. Do not infer product validation from one
profitable trade, one screenshot, or one live session.

## ML And AI

Build deterministic features and labels before training models. Persist the
feature definition and model identity with every inference.

ML may later rank, classify, or calibrate deterministic evidence. AI may synthesize live semantic
state and issue typed, policy-checked intents for observation and analysis. Neither may silently
alter canonical data, invent evidence, control the IB connection, or bypass reviewed resource and
risk boundaries.

## Configuration And Optimization

Do not hide a tunable market or operational decision in implementation code. Variable thresholds,
windows, weights, instruments, sessions, budgets, limits, cadences, and selection rules must be
typed, scoped, validated, versioned configuration with explicit defaults and units.

Every optimization-eligible parameter must declare its authorized range, mutability boundary,
source, effective time, and audit behavior. Runtime adjustment must use a typed, policy-checked
intent with expiry and rollback semantics; models do not receive arbitrary configuration access.

Keep true invariants in code: evidence honesty, schema and type integrity, source identity,
authorization, audit, and execution prohibitions. The authoritative full rule is the
[Configuration And Optimization Principle](../markeitech.md#configuration-and-optimization-principle)
in the project charter.

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
