# Implementation Roadmap

This roadmap describes current future intent. Completed slice details live in
the [implementation history](implementation-history.md), while exact progress
lives in [current status](../current-status.md).

## Immediate: Reliability And Market Events

### Stage 5D.4: Event Backbone

- Expose signal-runtime failure causes, tracebacks, last successful sequence,
  and affected input identity without requiring forensic log reconstruction.
- Account for every classified and unclassified trade by explicit reason before
  using tick Aggression, delta, or CVD as trusted evidence.
- Introduce versioned, immutable Markeitech domain messages on the Nautilus
  message bus while preserving commit-before-publish ordering.
- Bridge post-commit worker notifications onto the Nautilus event-loop thread;
  never call the non-thread-safe bus directly from persistence workers.
- Keep blocking persistence, rendering, and delivery work behind bounded worker
  queues rather than inside synchronous bus subscribers.
- Prove the boundary with an operator projection consumer, then add a dedicated
  Context Event actor.
- Emit persisted and deduplicated level, value, trend, and pressure transitions
  independently from any setup family.

Exit condition: no signal subsystem failure is silent, observation fidelity is
fully accountable, and multiple actors can consume committed market events
without blocking ingestion or bypassing durable truth.

The first Fabio Direction-Location-Aggression definition remains a shadow setup
family during this work. Its live lifecycle is engineering evidence, not trading
acceptance and not the organizing boundary for market context.

## Stage 5E: Composite Decision Policy

- Combine Direction, Location, and Aggression through versioned definitions.
- Add deterministic confidence and reason codes.
- Apply cooldown, replacement, suppression, and expiry rules.
- Preserve identical evaluation semantics for active and background instruments.
- Produce structured notification-ready signal events.
- Add a deterministic cross-market context overlay with confirm, oppose,
  divergence, suggest, and insufficient outcomes.
- Persist versioned, horizon-specific relationship inputs suitable for later
  statistical and ML shadow models without granting them lifecycle authority.

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

## Supplemental Provider Capabilities

Nautilus remains the owner of supported IB historical bars, ticks, quotes, and
subscriptions. Do not introduce a second general-purpose IB client while those
paths satisfy the requirement.

IB `reqHistogramData` is a possible future supplemental input for profile
comparison and feature research. If adopted, retain its provider-reported
methodology and request window explicitly, persist it as supporting evidence,
and do not substitute it for Markeitech's session-aligned canonical profiles.
Any native IB extension must own only capabilities unavailable through the
Nautilus adapter and must demonstrate a real need before adding another
connection lifecycle.

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
