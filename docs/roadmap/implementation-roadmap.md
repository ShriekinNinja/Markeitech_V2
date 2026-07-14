# Implementation Roadmap

This roadmap describes current future intent. Completed slice details live in
the [implementation history](implementation-history.md), while exact progress
lives in [current status](../current-status.md).

## Immediate: Signal Visibility And Acceptance

### Stage 5C.3c: Console Signal Projection

- Read durable signal lifecycle changes without recalculating evidence.
- Emit concise human-readable Candidate, Armed, Triggered, Invalidated, and
  Expired events.
- Include instrument, definition, Direction regime, Location episode, evidence
  summary, transition reason, and durable identity.
- Keep active/background role as presentation metadata, not signal identity.
- Bound and deduplicate console output.
- Run live shadow acceptance against NQ and configured watchlist instruments.

Exit condition: durable signal changes are visible and understandable in live
console output, restart does not duplicate alerts, and runtime health remains
stable.

## Stage 5D: Aggression And Follow-Through

- Define provider-aware, bounded observation windows.
- Add deterministic trade, quote, pace, and follow-through evidence where source
  fidelity permits.
- Represent missing or damaged tick evidence explicitly.
- Allow definitions to configure their timeframe stack and aggression policy.
- Progress Armed signals to Triggered only through persisted evidence.
- Define time-based Armed expiry from the actual observation cadence.

This stage must support different setup families. A slower context setup may use
1-hour plus 15-minute evidence, while a future scalp definition may use 15-minute
plus 5-minute or 1-minute evidence without changing global signal semantics.

## Stage 5E: Composite Decision Policy

- Combine Direction, Location, and Aggression through versioned definitions.
- Add deterministic confidence and reason codes.
- Apply cooldown, replacement, suppression, and expiry rules.
- Preserve identical evaluation semantics for active and background instruments.
- Produce structured notification-ready signal events.

## Stage 6: Notifications And Reports

- Deliver durable outbox intents through Discord webhooks.
- Keep webhook secrets outside source and durable payloads.
- Add retry, rate-limit handling, batching, and delivery observability.
- Produce scheduled watchlist and session analysis reports.
- Do not build a Discord bot or accept inbound commands.

## Options Chain And Trade-Expression Context

Options are the primary manual trade expression, even though the current
analytical runtime begins with NQ and a related-market watchlist. This is a
deliberate future capability, not an execution feature and not part of the
immediate Stage 5 signal-visibility work.

The first options slice should establish contracts and provider behavior before
adding analytics:

- model option identity explicitly by underlying, expiry, strike, right,
  multiplier, exchange, trading class, and provider contract id
- represent the relationship between each option and its analytical underlying
- discover valid chains without silently substituting expiries or trading classes
- capture timestamped bid/ask, last, volume, open interest, implied volatility,
  and provider Greeks with explicit availability and fidelity
- respect IB entitlements, pacing limits, delayed fields, and snapshot semantics
- select bounded expiries and strike ranges instead of subscribing to an entire
  chain tick by tick
- persist reproducible chain snapshots and methodology before deriving features

Later options analytics may include liquidity and spread quality, expected move,
term structure, skew, volatility regime, strike positioning, and contract
selection assistance. These features must remain distinct from underlying DLA
evidence while allowing an explicit versioned relationship between a market
signal and possible option expressions.

Exit conditions for this track will require provider acceptance, durable and
replayable snapshots, stale-field handling, and operator-readable chain reports.
Order construction, routing, sizing, and risk remain in the separately approved
execution stage.

## Validation Track: Replay And Backtesting

Live operation remains the immediate product focus, but deterministic replay and
backtesting are required before systematic execution or model claims.

- Replay canonical persisted events through shared domain logic.
- Reproduce feature and signal outputs by version.
- Add session-level fixtures and regression baselines.
- Compare live, restored, and replayed outcomes.
- Keep replay controls isolated from ordinary live operation.

## Later Product Stages

### Strategy Runtime

Add isolated, replaceable strategy processes only after signals and replay are
stable. Strategy failure must not interrupt ingestion or operator context.

### ML And AI Assistance

Train only from versioned deterministic features and labels. ML may rank or
calibrate candidates. AI may explain persisted evidence. Neither receives
execution authority.

### Gateway And UI

Add a transport-neutral gateway, then a dashboard, after console and Discord
workflows prove the operator contracts. The UI must consume backend projections
and never connect directly to IB or calculate canonical analytics.

### Execution And Risk Controls

Execution remains a separately approved final capability. It requires explicit
account configuration, order lifecycle persistence, independent risk limits,
kill controls, reconciliation, and paper acceptance before any live authority.

## Scope Guardrails

- NQ, ES, indices, and equities receive current product attention.
- Options-chain support is planned and must preserve a clear boundary between
  underlying analysis and trade expression.
- Crypto-specific features are not planned.
- Redis is introduced only for a demonstrated coordination requirement.
- UI polish does not displace live correctness, signal usefulness, or recovery.
- A profitable observation does not waive replay, calibration, or risk gates.
