# Development Guidelines

These guidelines capture the product and collaboration lessons established
while building and operating Markeitech. They supplement the project charter.

## Product Posture

Markeitech serves one discretionary operator first through Sir Loke, its live trading companion,
mentor, and configurable advisory governor. Optimize for trustworthy context, timely intervention,
inspectable evidence, disciplined trade decisions, and recovery rather than HFT latency or
automated execution. The canonical first-version experience is defined in
[`product/sir-loke-v1.md`](product/sir-loke-v1.md).

Separate the markets used to form a thesis from the instrument used to express
the trade. Underlyings, indexes, futures, volatility, sectors, and other context
may inform an options decision without becoming the traded product. Options
require distinct chain, expiry, strike, liquidity, and Greek semantics.

The current priority order is:

1. prove safe read-only observation of Markeitect's paper-account TWS trades;
2. define the canonical trade episode, recommendation linkage, advisory policy, and audit;
3. provide an authenticated, failure-isolated two-way Discord bot;
4. complete the minimum honest SPXW/QQQ evidence needed for recommendation or abstention;
5. deliver Sir Loke's live recommendation, monitoring, mentoring, governance, and reporting loop;
6. harden and extend deterministic intelligence according to demonstrated product needs;
7. add a dashboard or broader user experience only when it supports an approved need; and
8. consider execution only through a separately approved future risk and execution program.

Existing calendar, acquisition, evidence-health, persistence, measurement, and entity work remains
reusable foundation. This priority change does not declare inactive or unverified capabilities
live, and it does not authorize a language model to substitute for missing evidence.

Replay and backtesting are outside current scope until Markeitect explicitly
reopens them. Do not add storage or abstractions for that hypothetical path.

## Instrument Model

The current instrument model distinguishes the trade universe, dynamic observation universe,
active analytical capabilities, and temporary focus; it has no one-active-instrument or fixed
background-timeframe invariant. Multiple
instruments may receive granular continuous data when justified and supported.

SPXW and QQQ 0DTE options form the first-version trade-expression boundary. SPY and other products
remain later candidates. No instrument is globally preferred by implementation or configuration.
Sir Loke may maintain and rank multiple simultaneous opportunities. SPY, QQQ, SPX, ES, NQ,
volatility, and other approved instruments are useful evidence candidates, not a complete or fixed
observation universe. Crypto is not a current product priority.

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

Broker account, order, fill, and position observation is distinct from market-data acquisition.
Evaluate NautilusTrader's native IB execution client, live reconciliation, cache, event, and report
contracts before custom provider access. If native execution facilities are used to observe, place
a narrow fact-only boundary in front of Sir Loke and expose no mutable order object or order action.
The account environment, account alias/identity, broker/source identity, reconciliation origin,
and exact order/fill/position identities must remain visible.

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

Analytics are admitted only through current requirements and evidence. New capabilities must
declare their inputs, warmup, fidelity, configuration, outputs, and resource cost before
implementation; retired models, lifecycles, indicators, and thresholds confer no authority.

Semantic events should represent meaningful changes rather than duplicate raw observations.
Rolling state, ML outputs, and agent interpretations must retain evidence lineage. No event,
score, or agent proposal is an order instruction. Do not infer product validation from one
profitable trade, one screenshot, or one live session.

A canonical trade episode may include recommendations, independent trader entries, multiple
orders, partial fills, scale changes, plan revisions, interventions, acknowledgements, closure, and
an after-trade report. Preserve the original thesis and each later revision. Recommendation-to-
execution attribution must be explicit and may remain ambiguous; never invent why the trader
entered. A new opportunity after a loss must qualify independently and must not be framed as a
recovery trade.

## ML And AI

Build deterministic features and labels before training models. Persist the
feature definition and model identity with every inference.

ML may later rank, classify, or calibrate deterministic evidence. Sir Loke may synthesize live
semantic and broker-observation state, recommend or abstain, monitor open trades, mentor the trader,
and issue typed policy-checked intents for observation and analysis. Deterministic code—not the
model—owns evidence admission, authorization, intervention transitions, acknowledgement state,
cooldown enforcement, and the no-execution invariant. Neither ML nor AI may silently alter
canonical data, invent evidence, control the IB connection, reach an order method, or bypass
reviewed resource and risk boundaries.

Sir Loke's firmness is policy state, not prose style. Concern, warning, invalidation,
acknowledgement-required, noncompliance, cooldown, and resolution behavior must have explicit
inputs, transitions, timing, recovery, and audit. A generated forceful sentence is not an enforced
risk control.

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

Every repository change is a reviewable branch/PR batch, including documentation and small fixes:

1. Create a new scoped branch from current `master` before editing; preserve unrelated work.
2. Explain the intent and meaningful tradeoffs, implement only the authorized scope, and verify it.
3. Commit the scoped files, push the branch, and open a PR. This is included in an authorized
   change request unless the task explicitly restricts commits or publication.
4. Keep review fixes on that open PR. Leave it unmerged for Markeitect's approval of the current
   head and merge after required CI passes. Agents may merge only when that exact operation is
   explicitly delegated; new commits require renewed approval.
5. After merge, use a new branch/PR for the next change. Do not begin dependent work before its
   prerequisite merges unless Markeitect explicitly approves another arrangement.

No direct integration-branch commits/pushes, auto-merge, force-push, or check bypass. Local IDE
review remains available when requested. The current
[GitHub workflow](operations/github-workflow.md) replaces older uncommitted-only review language
without widening architecture, service, data, or destructive-operation authority.

Pause when an architectural assumption becomes questionable. A short design
review is cheaper than carrying a convenient workaround into persistence or
live-runtime behavior.

## Documentation Discipline

Architecture-sensitive changes must follow the
[system/data-flow manifest maintenance procedure](architecture/system-dataflow-maintenance.md).
Update the canonical TOML and its complete generated artifact set in the same reviewed batch.
Generated diagrams are never hand-edited authority, and successful generation does not prove live
runtime behavior.

Public V2 Python APIs follow the separately locked, static
[API documentation procedure](operations/v2-api-documentation.md). Use Google-style docstrings and
the versioned public-surface denominator. Custom docstring attributes remain schema-gated discovery
evidence: they do not establish caller/callee relationships, ownership, accepted architecture, or
runtime truth, and unknown or invalid values must never escape into generated artifacts.

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
