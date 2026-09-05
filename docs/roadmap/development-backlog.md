# Markeitech Development Backlog

**Status:** Unresolved work only

The ordered V1 path is [`sir-loke-v1-delivery-plan.md`](sir-loke-v1-delivery-plan.md). The
implementation ledger is [`../current-status.md`](../current-status.md). Completed stage history
is recoverable through Git and merged pull requests; it is intentionally absent here.

## Sir Loke V1 Gates

- **Gate 1 — broker observation:** complete the pinned Nautilus/IB offline safety decision, inspect
  every startup/open-order/binding path, approve a bounded paper probe, and prove manual TWS event
  coverage without order control.
- **Gate 2 — deterministic product truth:** approve and implement recommendation, attribution,
  trade-episode, intervention, acknowledgement, report, and audit contracts.
- **Gate 3 — Discord bot transport:** approve and implement private authentication, allowlisting,
  inbound/outbound ordering, deduplication, retry, reconnect, rate-limit, queue, secret, and
  shutdown behavior.
- **Gate 4 — minimum options corridor:** approve the minimum honest SPXW/QQQ 0DTE option and
  cross-instrument evidence needed for a recommendation or defensible abstention.
- **Gate 5 — bounded reasoning:** approve model/provider identity, budgets, tools, structured
  output, citation validation, redaction, audit, degradation, and abstention behavior.
- **Gate 6 — integration:** join broker observation, market/options evidence, policy, reasoning,
  audit, and Discord without collapsing their independent health.
- **Gate 7 — acceptance:** pass the separate qualified-recommendation, insufficient-evidence
  abstention, and independent-trade scenarios in deterministic fixtures and an authorized TWS
  paper run.

## Reliability Of Used Paths

Close these debts before the affected component becomes a V1 dependency:

- initial subscription failure recovery and controlled provider disconnect/resubscription;
- historical-request correlation beyond one lane, cancellation fencing, timeout/retry, duplicate,
  and shutdown behavior;
- late-consumer session/evidence projection reconciliation and connected retry/failure evidence;
- complete calendar-definition identity through completed bars and metric subjects;
- deterministic producer-route, duplicate-owner, atomicity, historical/live equivalence,
  conflict/revision, warmup, restart, and health/fidelity proof for the V3 evidence cutover;
- broker-event omission, duplication, late arrival, reconciliation, reconnect, and sanitized
  no-control proof;
- Discord reconnect/rate-limit/delivery ordering and bounded shutdown;
- persistence idempotency, required-write atomicity, restart recovery, terminal outcome, retention,
  and redaction; and
- model/tool timeout, cost, citation, authorization, loop, malformed-output, and failure isolation.

Passing offline suites or a single connected session does not close a wider reliability item.

## V3 Deterministic Evidence Cutover

- Finish the inactive completed-bar foundation replacement and its producer-manifest/composition
  proof.
- Close projection correlation and actual routing identity.
- Prove atomic publication/state behavior and historical/live semantic equivalence.
- Add adversarial duplicate-route, lifecycle, correction/conflict, and source-lineage tests.
- Admit replacement metric owners only after completed-bar acceptance.
- Reintroduce entity analysis and any dependent semantic capability only after the replacement
  owners are accepted in the active profile.
- Keep Visual Debug passive and non-gating; it may return only when the reviewed capability and
  fixture inventory is current.

The detailed replacement contract remains in
[`../reference/session-metrics-replacement-plan.md`](../reference/session-metrics-replacement-plan.md).

## Dynamic Watchlist Decision

Before enabling dynamic membership, approve one canonical membership owner and typed contracts
for proposals, claims, reasons/evidence, priority, policy/configuration version, effective time,
lease/expiry, revision/invalidation, resource admission, restart behavior, and audit. A model may
propose bounded intent but cannot mutate membership, provider subscriptions, or capability
activation directly. Static configuration remains authoritative until this decision is accepted.

## Optional Options-Flow Evidence

No vendor file or flow label is admitted by default. A future source-specific batch must approve:

- vendor/schema/version and immutable provenance;
- timestamp, venue, condition, correction/cancel, side/classification, premium, size, strike,
  expiry, option type, underlying, and contract identity semantics;
- NBBO or quote-context availability and whether classifications are reported or inferred;
- open-interest publication timing and the impossibility of per-print opening/closing truth when
  the source does not provide it;
- completeness, deduplication, revision, licensing, permitted use, retention, display,
  redistribution, derived-data, and deletion obligations; and
- deterministic isolation from native broker/market observations and from generic product truth.

The prior detailed vendor-export assessment remains recoverable through Git history. Its findings
are evidence about that exact export, not a universal options-flow contract.

## Optional Gamma-Exposure Evidence

Any GEX capability requires a separately approved source and formula contract covering exact
option universe, open-interest vintage, gamma/Greek source and units, multiplier, sign convention,
spot reference, expiry/settlement identity, filters, missing contracts, freshness, corrections,
dealer-positioning assumptions, aggregation, and display limits. It must remain an explicitly
derived scenario under stated assumptions, not observed dealer inventory or causal certainty.

The earlier GEX research is recoverable through Git history and remains informative only.

## Deferred Visualization

A full live dashboard remains deferred. If reopened, begin with a fresh user/job decision and use
only canonical projections. The UI must not create market truth, broker truth, policy, or agent
state; must expose identity, freshness, fidelity, gaps, and provenance; and must remain isolated
from the runtime event loop. The stable passive review contract is
[`../operations/visual-evidence-review.md`](../operations/visual-evidence-review.md).

## Later Product And Research Tracks

- richer market-structure, order-flow, cross-instrument, options, and volatility capabilities;
- measured opportunity utility and calibration;
- ML only after an approved leakage-safe data/label/evaluation/rollback strategy;
- policy-controlled optimization only for explicitly dynamic, bounded, versioned parameters;
- additional products, expiries, accounts, users, hosted operation, and interfaces; and
- any broker-side prevention or close authority as a separately governed product/security program.

Replay, backtesting, raw-data retention for hypothetical use, and autonomous execution remain out
of scope until Markeitect explicitly reopens them.

## Documentation And Tooling

- Keep the active human-authored set small and update the narrowest authority with each accepted
  boundary change.
- Keep completed history in Git/PRs rather than restoring stage plans as current authority.
- Regenerate system-diagram artifacts only through the tool procedure under
  [`../../tools/system-diagram/docs/maintenance.md`](../../tools/system-diagram/docs/maintenance.md).
- Regenerate tracked API documentation only through the isolated first-party wrapper described in
  [`../operations/v2-api-documentation.md`](../operations/v2-api-documentation.md).
- Fail CI on broken active links, stale generated artifacts, invalid diagrams, public-surface
  drift, or accidental admission of secrets, local configuration, logs, raw/licensed data, and
  generated scratch files.
