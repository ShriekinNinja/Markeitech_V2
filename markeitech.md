# Markeitech Project Charter

Markeitech is a live-first market-intelligence and trading-discipline system built by Markeitect
for discretionary index trading. Its first product experience is **Sir Loke**, a personal live
trading companion, mentor, and configurable advisory governor. Markeitech turns reliable market,
options, and broker-observation evidence into recommendations, trade monitoring, firm challenges,
and inspectable after-trade reports for manual trading. It is not an HFT system and does not
currently execute orders.

This charter governs current product and engineering work. Historical source is recoverable
through Git history but does not define current behavior.

## Current Product Direction

- The canonical first-version product contract is
  [`docs/product/sir-loke-v1.md`](docs/product/sir-loke-v1.md). Sir Loke is a live, two-way private
  Discord bot for Markeitect, running locally. Infrastructure is valuable insofar as it supplies
  the trustworthy evidence, policy, resilience, and audit required by that user experience.
- Sir Loke participates before, during, and after a trade. It may recommend qualified trades,
  observe what Markeitect actually trades, analyze independently entered trades, monitor thesis
  and risk changes, challenge plan drift or invalidation, request acknowledgement, withhold its own
  recommendations during a configured cooldown, and publish factual after-trade reports.
- First-version governance is forceful but advisory. Sir Loke may recommend reducing or closing a
  position but has no order-submission, modification, cancellation, replacement, or closing tool.
  Broker-side enforcement or closing authority is a separately approved future execution-and-risk
  product boundary; it is not a dormant v1 feature.
- ES and SPY were initial V2 provider-bootstrap instruments; they do not define the first-version
  trade scope and are not a permanent universe.
  The observation universe, acquisition cadence, enabled analysis capabilities,
  and temporary market focus may change while the system runs.
- SPXW and QQQ 0DTE options are the first-version trade-expression products. SPY and other
  expressions remain later candidates. No expression instrument is globally preferred, and the
  initial scope is not a permanent whitelist. Evidence instruments remain distinct from trade
  expressions.
- Sir Loke's governing maxim is Sherlock Holmes's
  principle: "When you have eliminated the impossible, whatever remains, however improbable, must
  be the truth." Sir Loke must eliminate through cited evidence and deterministic policy, preserve
  unresolved uncertainty, and abstain when the remaining case is not sufficiently supported.
- The first connected trade-observation acceptance uses an Interactive Brokers paper account
  through Trader Workstation. Sir Loke's analytical and governance behavior is the same for paper
  and live accounts, but every broker fact and report preserves account identity and environment.
  Paper acceptance does not authorize or validate a live-money connection.
- Native provider observations, deterministic facts, semantic events, persistent
  entities, rolling state, broker-reported execution facts, trader statements, policy decisions,
  model outputs, AI interpretations, and execution authority remain separate boundaries.
- Discord provides the first authenticated conversation surface. The current outbound webhook
  health projection is useful infrastructure but is not the Sir Loke bot. A full UI remains later.
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

The live runtime is centered on a NautilusTrader `LiveNode`. The implemented Interactive Brokers
connection remains manual, explicitly confirmed, paper, market-data-only, and read-only. The
first-version product now requires a separately reviewed broker-observation path for account,
order, fill, and position facts. Evaluate NautilusTrader's native execution client,
reconciliation, cache, and events before custom IB access, while exposing no order action to Sir
Loke. Do not add order routing until a separately reviewed future execution and risk stage.

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
- exact broker account/environment identity and honest reconciliation on every trade observation
- no order-action contract reachable from the v1 agent, Discord, policy, or observation surfaces

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

Analytics are admitted only through current evidence and architecture review. The intended
intelligence path is deterministic measurement, typed analytical entities, semantic observations
and interpretations, multidimensional rolling state, options context, bounded broker facts,
policy state, and Sir Loke's evidence-cited advisory synthesis.

ML may later rank versioned deterministic evidence. Sir Loke may synthesize evidence, surface
contradictions, suggest an options expression with triggers and invalidation, monitor admitted
broker observations, mentor the trader, apply configured advisory interventions, and request
policy-approved changes to observation focus, historical evidence, option snapshots, or analytical
capabilities. It acts through typed intents and deterministic policy; it may not connect to IB
directly, submit or alter orders, invent evidence, rewrite the original thesis, or bypass explicit
resource and risk controls.

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
- Every repository change has a new scoped branch and GitHub PR, including documentation and
  small fixes. Never implement, commit, or push directly on the integration branch (`master`).
- A request to make a repository change includes scoped commits, pushes, and PR publication for
  review unless the task explicitly restricts them. PR review replaces the former default of
  stopping with uncommitted changes; local IDE review remains available when requested.
- Markeitect approves the current PR head and owns its merge. Agents stop with the PR unmerged
  unless Markeitect explicitly delegates that exact merge. Passing CI is required, not permission
  to merge; later commits require renewed approval. No auto-merge or force-push.
- Keep review fixes on the same open PR. Start a new change on a new branch, and wait for a
  prerequisite PR to merge before dependent work unless Markeitect approves another arrangement.
- Keep current status separate from implementation history and future intent.
- Do not claim validation that has not occurred.

The [GitHub workflow](docs/operations/github-workflow.md) defines the operational protocol and
supersedes older uncommitted-review instructions. Explicit task restrictions and all architecture,
connected-run, secret-handling, and destructive-action approval boundaries still apply.

See [`docs/README.md`](docs/README.md) for the documentation authority order and
navigation map.
