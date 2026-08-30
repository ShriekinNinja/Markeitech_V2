# Desired Runtime Architecture Council Gap Review

**Status:** High-quality informative council discovery record and proposal source; not accepted
architecture, a roadmap, a development plan, an authoritative debt ledger, or implementation
approval

**Evidence date:** 2026-08-29

**Handoff branch:** v3-es-progressive-capability-review

**Reviewed checkout:** detached HEAD at
76451f69b5a879dd9e81073414a3174a23e85bcc, created from the handed-off working tree

**Desired-runtime source:** [desired-arch.md](desired-arch.md)

## 1. Scope, Authority, Method, And Limitations

This report compares the desired runtime with the current Markeitech V2 implementation, accepted
architecture, and accepted future plans. It identifies what is already supported, what is
partially reusable, what is planned, what is missing, and what conflicts with current accepted
constraints. It recommends the smallest coherent direction for later decision; it does not accept
that direction, define a low-level implementation, select trading rules, or authorize execution.

Future work may cite the council's evidence and proposals, but this report does not create stages,
reorder the canonical roadmap, make every identified concern mandatory debt, or require that all
preserved questions be answered before unrelated approved data-processing work continues. Current
repository authority and later stage-specific decisions govern action.

The repository authorities were read in the handoff's required order:

1. [markeitech.md](../../markeitech.md)
2. [current-status.md](../current-status.md)
3. [development-guidelines.md](../development-guidelines.md)
4. [docs/README.md](../README.md)
5. [markeitech-advisor-council.md](../architecture/markeitech-advisor-council.md)
6. [v2-adaptive-market-data-plane.md](../architecture/v2-adaptive-market-data-plane.md)
7. [v2-market-events-live-agent-plan.md](../roadmap/v2-market-events-live-agent-plan.md)
8. [desired-arch.md](desired-arch.md)

Current implementation and nearby tests were inspected where the distinction between implemented
behavior and future intent was material. The current-status ledger governs implementation status;
the adaptive data-plane and Stage 9 roadmap govern accepted future direction within their scope;
the desired document is a review target, not accepted authority.

### 1.1 Fresh-task Kite gate

The fresh-task gate passed before consultation:

- installed Kite policy 2026-08-29-v3 was exposed by the installed router;
- the installed policy and router matched the current source byte-for-byte for the checked files;
- the live task custom-role registry exposed all eight approved role IDs as
  gpt-5.6-sol with xhigh reasoning;
- the repository profiles declared those same settings and a read-only consultation default;
- the dependency-free validator passed for 20 advisors, 27 in-Kite routing cases, and 9 activation
  cases; and
- all 20 focused council-validator tests passed.

This proves the exact fresh-task role-loading gate needed for this review and the exercised static
validation scope. It does not prove general Kite dormancy, end-to-end behavior for every routing
fixture, technical tool isolation, revocation behavior, or all future tasks. The council
architecture explicitly keeps those acceptance claims separate
([markeitech-advisor-council.md:130-178](../architecture/markeitech-advisor-council.md)).

### 1.2 Selected-role dependency graph

Exactly the approved eight roles were used:

1. architecture boundaries;
2. Nautilus alignment, after architecture;
3. data quality and lineage, after Nautilus;
4. event-driven architecture, after Nautilus;
5. market structure, after data quality;
6. market microstructure and order flow, after data quality;
7. statistical learning and optimization, after data quality; and
8. live-agent governance, after all upstream dispositions.

No additional advisor was silently substituted for missing coverage. Every consultation succeeded
and remained read-only. The Nautilus advisor completed its mandatory native-capability census and
Nautilus Alignment Matrix.

### 1.3 Evidence labels

This report uses the following meanings:

- **Verified fact:** established by current tracked authority, current source, exact installed
  contract, or a directly inspected deterministic artifact.
- **Measured evidence:** a recorded test or connected-run observation within its exact stated
  scope.
- **Inference:** a conclusion derived from verified facts whose consequence has not itself been
  directly measured.
- **Hypothesis:** a plausible explanation or future analytical claim which still requires
  falsifiable evidence.
- **Recommendation:** a proposed disposition for Markeitect's decision.
- **Unknown:** evidence is absent, stale, outside the selected advisors' authority, or insufficient
  to choose honestly.

### 1.4 Review limitations

- No connected IB or Discord run was performed.
- PostgreSQL was not used.
- No provider capacity, paid quota, authenticated session, secret, or external mutation was used.
- No V2 runtime tests were rerun. Existing test and connected-acceptance results are cited as
  recorded evidence. Only the offline Kite council validator and its focused tests were executed.
- No formula-parity, provider-entitlement, options-contract, account-risk, execution, legal,
  licensing, security-isolation, persistence-mechanics, or final evidence-fitness conclusion was
  substituted for missing specialist coverage.
- Public primary sources refreshed by selected advisors were used only within their bounded
  domains. Installed NautilusTrader 2.0.0rc3 remains runtime truth; nightly documentation is drift
  evidence, not a replacement contract.
- The working tree intentionally contained pre-existing uncommitted and untracked files. This
  report is the only file created by this review.

## 2. Executive Disposition

**Recommendation: broadly compatible foundation; material extension and boundary correction
required; do not rewrite; do not approve yet.**

The desired direction is broadly compatible with the strongest parts of the current V2
foundation:

- one data-only Nautilus LiveNode and native high-volume data path;
- one logical provider-demand and subscription-lifetime owner;
- typed, bounded, versioned acquisition and historical-work primitives;
- deterministic measurement and entity owners;
- explicit evidence health, fidelity, missingness, revision, and lineage concepts;
- bounded entity state and immutable snapshot patterns;
- operational audit and resource-health foundations; and
- projection-only Discord and visual boundaries.

Those capabilities should be reused. The desired runtime does not justify replacing Nautilus,
adding a second raw-data path, inventing a custom bus/cache, introducing Redis, splitting into
microservices, or constructing agent-specific market-truth pipelines.

The current runtime is not yet an agent runtime, however. The largest blockers are:

1. **No governed live-agent control plane.** There is no implemented principal/grant model,
   deterministic intent-policy/resource governor, dynamic observation-universe owner, runtime
   capability manager, agent read model, approval/revocation lifecycle, abstention record, or
   canonical plural-opportunity owner.
2. **Incomplete evidence identity for the desired joins.** Current completed-bar evidence is
   strong in its exact paths, but generic MetricValue loses material timeframe, bar-specification,
   profile, calendar, trade-date, window, configuration-epoch, and parameter-effective identity.
   No cross-instrument as-of join exists.
3. **A latent calendar authority conflict.** SessionStateActor, acquisition, and
   SessionMetricsActor independently instantiate and evaluate calendars. They normally receive
   equivalent startup definitions, so present boundary-value divergence was not measured, but
   future runtime mutation cannot be honest without one definition identity/effective epoch and a
   single canonical contract.
4. **Open event-delivery and reliability gates.** Agent-directed work lacks end-to-end identities,
   bounded admission, autonomous live-subscription retry/reconnect reconciliation, safe uncertain
   effect handling, complete shutdown outcomes, and durable decision reconstruction. Historical
   timeout/cancellation can leave a late callback correlation hazard.
5. **Only a partial top-down analytical substrate.** Exact-horizon Stage 9D primitives and
   one-, five-, and fifteen-minute rolling families are reusable, but direct broader-timeframe
   runtime applications, same-instrument cross-horizon relationships, cross-instrument
   relationships, semantic interactions, and agent-safe read-model admission are not implemented.
6. **Observed order flow is unavailable.** Current data can support quoted-friction measurements,
   bar geometry, reported bar volume, and explicitly named bar-derived proxies. It does not
   establish NBBO, classified aggressive trades, delta/CVD, recovered books, depth/resilience,
   true effort-response, or participant intent.
7. **Statistical learning is not evaluation-ready.** Deterministic versioned features are useful
   foundations, but there is no approved data strategy, point-in-time dataset, label contract,
   leakage-safe protocol, prediction ledger, calibration evidence, or model governance. Training,
   shadow promotion, live adaptation, and automatic optimization are blocked.
8. **Risk and execution coverage is missing.** The desired risk objective and future execution
   option require account/portfolio risk, execution/order lifecycle, provider authorization,
   security/tool isolation, approval, reconciliation, and kill-switch owners which were outside
   this approved council set. No execution conclusion can proceed.

The smallest coherent direction is therefore to retain the native/provider and deterministic
evidence foundation, correct its known identity/reliability limits, and compose a shared,
deterministic control and read-model plane above it. The agent remains a bounded advisory
consumer/requester; it does not become a provider owner, evidence owner, policy owner, opportunity
truth owner, risk owner, or execution owner.

## 3. Requirement-To-Current-State Matrix

The classification describes the current checkout and accepted future intent, not approval to
implement the desired state.

| Desired requirement | Classification | Current evidence | Gap, conflict, or required decision |
|---|---|---|---|
| Live market-evidence runtime | **SUPPORTED_NOW** | One data-only Nautilus 2.0.0rc3 LiveNode, native observations, static watchlist, acquisition ownership, session/evidence actors, metrics, entities, operational audit, and bounded recorded connected acceptance are current ([current-status.md:9-96](../current-status.md)). | Support is bounded to accepted instruments, feeds, selectors, sessions, and capabilities. It is not general provider or advisory readiness. |
| Advisory/no-order posture | **SUPPORTED_NOW** | Current charter and node composition prohibit order routing and configure only an IB data client ([markeitech.md:43-53](../../markeitech.md); [node.py:40-88](../../v2/src/markeitech/system/node.py)). | Retain. Future compatibility does not authorize an execution client or order tool now. |
| One live advisory agent | **PLANNED** | Sir Loke, read model, policy, and tools are accepted Stage 9I future intent; current status says they are absent ([v2-market-events-live-agent-plan.md:685-727](../roadmap/v2-market-events-live-agent-plan.md); [current-status.md:93-100](../current-status.md)). | Pre-9I reliability, evidence admission, governance, security/licensing, audit, and model-context gates remain open. |
| Multiple agents with different perspectives | **MISSING** | The desired document explicitly permits multiple agents; the accepted roadmap is primarily singular-agent language with plural opportunities ([desired-arch.md:45-62](desired-arch.md); [v2-market-events-live-agent-plan.md:276-301](../roadmap/v2-market-events-live-agent-plan.md)). | Decide whether the first runtime is operationally single-agent but multi-agent-safe in identity, grants, budgets, claims, and conflict handling. |
| Agent predictions, recommendations, and abstention | **PLANNED** | Advisory interpretation and abstention are accepted future boundaries; deterministic evidence exists, but no agent schema, invocation, claim, or abstention owner is implemented. | Missing named-use admission, read-model identity, citation validation, governance, and opportunity semantics. |
| Controlled future execution without coupling intelligence to authority | **UNKNOWN** | Nautilus contains risk/execution/portfolio types, but Markeitech does not configure them. Current authority explicitly separates interpretation and execution and prohibits orders now ([markeitech.md:20-27](../../markeitech.md)). | Framework type availability is not end-to-end compatibility. Missing risk/account/security/execution specialists block the conclusion. |
| Risk management controls impact of being wrong | **MISSING** | Current runtime has operational/resource health, but no account, portfolio, position, order, loss, exposure, agent-risk budget, or execution kill-switch authority. | Desired risk semantics require a separate approved risk program. The selected zero-DTE advisor explicitly excludes portfolio risk, so existing council inventory is also incomplete for this use. |
| Initial SPX 0DTE, SPY/QQQ 0-3 DTE, and ES/NQ futures trade focus | **CONFLICTING** | Accepted product direction currently seeds SPXW/SPY/QQQ 0DTE option expressions and treats ES/NQ as evidence examples; no expression is globally preferred ([markeitech.md:13-27](../../markeitech.md)). | SPY/QQQ 1-3 DTE and ES/NQ futures as trade expressions materially broaden accepted product scope and risk/execution mechanics. Markeitect must revise or retain the existing boundary explicitly. |
| Extensible instruments and trade styles | **PARTIAL** | Contracts preserve explicit identity and the architecture rejects permanent whitelists. Current runtime still uses a static 18-member configuration-owned set ([current-status.md:93-100](../current-status.md)). | Dynamic membership and new product semantics are not implemented; extension requires provider, session, risk, and evidence contracts per product. |
| Dynamic observation universe | **PLANNED** | Adaptive data-plane architecture defines dynamic membership and accepted Stage 8E future control; current membership is static ([v2-adaptive-market-data-plane.md:54-75](../architecture/v2-adaptive-market-data-plane.md)). | Current SystemConfig.instrument_ids is derived directly from static watchlist members, and acquisition rejects outside-scope demand ([config.py:633-654](../../v2/src/markeitech/system/config.py); [acquisition.py:494-568](../../v2/src/markeitech/system/acquisition.py)). |
| Agent requests instruments, feeds, history, capabilities, parameters, and focus | **PARTIAL** | Logical demand, expiry at the lower-level ObservationDemand, shared provider subscriptions, bounded historical execution, and lifecycle vocabulary are reusable. | Direct AnalyticalDemandEvent-to-acquisition is not authorization and lacks grant, policy, lease, parameter, aggregate-budget, causation, and requester-result contracts ([messages.py:255-339](../../v2/src/markeitech/system/messages.py)). |
| Deterministic policy and aggregate resource governance | **PLANNED** | Accepted topology names a policy/resource governor and current runtime has component-local bounds and telemetry ([v2-adaptive-market-data-plane.md:151-177](../architecture/v2-adaptive-market-data-plane.md)). | No aggregate per-agent/global admission, reservation, approval, revocation, or protected cancellation/release capacity exists. |
| Dynamic capability activation and reconfiguration | **PLANNED** | Capability declarations and static configuration contain inputs, history, versions, bounds, and optimization metadata. | No runtime capability registry/manager owns activation, preparation, reconfiguration, leases, aggregate cost, or rollback. |
| Top-down multi-timeframe intelligence | **PARTIAL** | Current one-, five-, and fifteen-minute rolling families and exact-horizon Stage 9D entities provide reusable deterministic context. Stage 9D plans broader one-hour/day and weekly-reference scopes. | Current singular completed-bar foundation, generic MetricValue identity, unimplemented broader-horizon applications, and missing cross-horizon relationship prevent a delivered top-down capability. A long lookback on smaller bars is not higher-timeframe structure. |
| Same-instrument cross-horizon agreement, conflict, and dependency | **MISSING** | Source entities preserve exact horizon identity and conflicts can remain explicit. | No typed as-of evidence bundle selects several horizon revisions under one cutoff with age, skew, missingness, conflict, dependency, decay, or expiry policy. |
| Cross-instrument context and evolving relationships | **PLANNED** | Stage 9G accepts future freshness-aligned, horizon-specific relationship work; current status lists it as future ([v2-market-events-live-agent-plan.md:393-400](../roadmap/v2-market-events-live-agent-plan.md)). | No implemented as-of join, relationship owner, normalization, member-role contract, roll mapping, revision, decay, or connected acceptance exists. Leadership/lag/causality remains unsupported. |
| Broader structure, direction, locations, and objectives | **PARTIAL** | Confirmed swings, legs, pivot relationships, objective levels, FVGs, zones, market-state contracts, and bounded state books are implemented/tested as deterministic primitives. | Current tracked entity analysis is disabled, the active runtime binding is limited, higher-timeframe applications and connected structure acceptance remain incomplete, and geometry is not trading meaning. |
| Optional order-flow refinement | **PARTIAL** | Provider top-of-book quote transport, quote-friction metrics, bar geometry/volume, a narrow ES/SPY trade transport proof, and an inferred candle-volume distribution primitive exist. | Observed flow is unavailable: no accepted broad trades, classifier, quote/trade alignment, corrections, delta/CVD, book recovery, true liquidity, effort-response, or participant evidence. |
| Honest source, lineage, clocks, completeness, freshness, and fidelity | **PARTIAL** | CompletedBarInput, EvidenceHealthEvent, metrics, and entities contain many strong fields and bounded admission rules. | Provider/adapter identity, complete request causation, calendar epoch, generic metric subject identity, expected-population completeness, correction lifecycle, and cross-instrument as-of alignment are incomplete. |
| Runtime calendar/profile mutation | **CONFLICTING** | Variable behavior is required to be typed and optimization-ready, but three current components evaluate copied calendar definitions independently. | No complete definition digest/effective epoch or atomic switch contract exists. Runtime mutation must remain blocked until authority and evidence identity are resolved. |
| Configurability and governed optimization readiness | **PARTIAL** | Parameter identities, bounds, steps, source, mutability classes, and versions are present in several current contracts. | Parameter effective time is not fully enforced or published, no governed live change lifecycle exists, and no objective/data/evaluation/rollback contract authorizes optimization. |
| Semantic interaction events | **PLANNED** | Stage 9E is accepted future work. Current entities deliberately stop at geometry/state. | Approach, test, acceptance, rejection, break, failure, target, and opportunity meaning are not implemented and require the semantic-event specialist. |
| Bounded options intelligence | **PLANNED** | Stage 9F defines bounded SPXW/SPY/QQQ discovery, references, quotes/Greeks, lifecycle, and resource proof. | Options mechanics, provider delivery, contract identity, sessions, liquidity, settlement, flow, and risk require unselected specialists and connected evidence. |
| Plural advisory opportunities | **PLANNED** | Stage 9J and accepted product direction require plural target-exposure opportunities. | No canonical opportunity identity/admission/conflict owner, persistence, agent claim, or operator lifecycle is implemented. |
| Statistical learning and model evaluation | **PLANNED but BLOCKED** | Stage 9K preserves future model/evaluation intent; deterministic versioned evidence provides useful prerequisites. | No approved data strategy, point-in-time dataset, labels, leakage-safe evaluation, prediction freeze, calibration, monitoring, promotion, or named-use evidence fitness exists. |
| Operational audit | **SUPPORTED_NOW** | Runtime, health, generic operational events, and recency profiles are stored through a bounded PostgreSQL owner ([current-status.md:93-94](../current-status.md)). | Current generic audit is not a logical agent-decision, approval, opportunity, model, or execution audit. New durable meanings require explicit schemas and owners. |
| Agent decision reconstruction | **MISSING** | Generic event fields such as event/run/sequence/correlation/causation are mechanically reusable. | Principal/grant, invocation, snapshot, evidence admission, model/prompt/tool versions, policy decision, approval, command, attempt, result, opportunity, and operator-disposition graph is absent. |
| Partial-failure resilience for agent-directed work | **PARTIAL** | Existing components show useful failure isolation and bounded workers; accepted connected runs preserved unrelated work in several cases. | Mandatory pre-9I retry, reconnect, overflow, recovery, correlation, persistence, and shutdown evidence gate remains open. |

## 4. Reuse Inventory

### 4.1 Implemented and verified within bounded scope

1. **Native data-only foundation**
   - one NautilusTrader 2.0.0rc3 LiveNode;
   - native DataEngine/cache/actor observation path;
   - IB data-client composition without an execution client;
   - explicit contract identity and current no-order posture.

2. **Logical acquisition ownership**
   - DataAcquisitionActor and AcquisitionCoordinator own logical demand and provider-facing
     subscription/request lifetime;
   - stable demand IDs, exact duplicate/conflict handling, shared logical demand, priority,
     optional lower-level expiry, first-observation state, and last-consumer release;
   - measured Stage 8C evidence that eight actor-level subscriptions became four provider
     subscriptions and one consumer could leave without stopping the remaining consumer
     ([current-status.md:253-276](../current-status.md)).

3. **Session and evidence primitives**
   - typed calendar definitions, UTC boundaries, trade dates, phases, session transitions,
     evidence-health states, source fidelity, recency, and missing reasons;
   - isolated calendar and evidence tests for DST, holidays, early closes, overrides, and
     lifecycle behavior.

4. **Historical dependency primitives**
   - capability-declared, bounded, deduplicated, prioritized historical work;
   - shared provider request with separate consumer readiness;
   - exact recent-completed connected acceptance for the bounded Stage 9B path
     ([current-status.md:425-438](../current-status.md)).

5. **Deterministic measurements**
   - completed-bar admission, historical/live convergence, duplicates/conflicts, sessions,
     references, windows, gaps, opening ranges, power-hour, and rolling families;
   - measured Stage 9C record of 10,632 accepted completed bars and 307,296 rolling values with
     zero calculation failures in the exact run
     ([current-status.md:553-572](../current-status.md)).

6. **Typed entities and bounded state**
   - stable identity, revision, lifecycle, health, fidelity, evidence references, bounded state
     books, and immutable snapshot patterns;
   - implemented session/reference entities, volatility state, confirmed swings, swing legs,
     pivot relationships, FVGs, and constituent-preserving zones;
   - useful exact-horizon tests and bounded actor integration evidence.

7. **Operational audit, resource health, and projections**
   - bounded PostgreSQL operational persistence;
   - runtime resource telemetry and health;
   - Discord/visual boundaries which project existing truth and do not calculate or mutate it.

### 4.2 Implemented but insufficient for the desired runtime

1. **Static watchlist as total acquisition scope**
   - useful bootstrap authority;
   - structurally coupled to system readiness, actor composition, instrument resolution, and
     rejection of outside-scope work;
   - cannot simply be mutated into optional focus without separating bootstrap and advisory
     readiness.

2. **AnalyticalDemandEvent**
   - useful as a post-policy internal feed-demand command;
   - unsafe as an agent intent or authorization boundary because it lacks grant, policy decision,
     authorized parameters, lease, budget, causation, approval, and full outcome identity.

3. **Singular SessionMetricsActor foundation**
   - valuable and live-proven for its exact selectors;
   - currently combines completed-bar foundation, session references, calendar windows, and
     rolling measurements under one live selector, one historical selector, and one calculation
     interval;
   - cannot support a second independent canonical foundation in the temporary profile
     ([current-status.md:528-537](../current-status.md)).

4. **Generic MetricValue**
   - carries useful values, clocks, health, fidelity, source, evidence references, missing reasons,
     and revision;
   - omits material self-describing subject identity needed by top-down, cross-instrument,
     point-in-time, model, and agent uses
     ([metrics.py:294-357](../../v2/src/markeitech/intelligence/metrics.py)).

5. **Independent calendar evaluation**
   - normally deterministic under equivalent immutable startup definitions;
   - violates the accepted sole-owner posture at authority level and becomes conflicting for
     runtime mutation without a canonical definition digest/effective epoch.

6. **Historical callback correlation and shutdown**
   - current bounded execution is useful;
   - a callback without request identity can be attributed to the currently active request after a
     prior timeout/cancellation, and shutdown cancellation can leave incomplete outcomes.

7. **Quote and bar evidence**
   - sufficient for provider top-of-book observations, midpoint/quoted-spread measurements, price
     geometry, reported bar volume, and explicit bar-derived proxies;
   - insufficient for NBBO, size-aware liquidity, aggressive classification, delta/CVD, recovered
     depth, or participant meaning.

8. **Generic operational audit**
   - strong mechanical base;
   - not an approved dynamic control-state, agent-decision, analytical-summary, model, opportunity,
     or execution store.

### 4.3 Accepted plans, not implementation

- dynamic observation and focus control in the adaptive data plane;
- policy/resource governance and capability management;
- Stage 9E semantic events;
- Stage 9F bounded options proof;
- Stage 9G cross-instrument state;
- Stage 9H richer analytics and optional true microstructure work;
- mandatory reliability gate before Stage 9I;
- Stage 9I read model, policy, tools, and Sir Loke;
- Stage 9J plural advisory opportunities;
- Stage 9K evaluation and ML readiness;
- dedicated analytical-summary durability and restored-state admission where later approved.

### 4.4 Missing capabilities

- versioned dynamic observation-universe owner;
- deterministic intent-policy/resource governor;
- runtime capability registry/manager;
- principal, role, grant, approval, revocation, and non-delegation contracts;
- agent read-model projector with one immutable as-of snapshot identity;
- named-use evidence admission and final fitness;
- same-instrument cross-horizon relationship;
- cross-instrument as-of join and relationship owner;
- semantic interaction and opportunity admission semantics;
- live-agent invocation, claim, abstention, and decision audit;
- aggregate multi-agent budgets and conflict handling;
- provider-verified true trade/quote/book coverage and accepted order-flow classifiers;
- point-in-time data/label/evaluation/model-monitoring path;
- account/portfolio risk, execution, reconciliation, and kill-switch owners.

## 5. Advisor Dispositions

All eight advisors succeeded at gpt-5.6-sol/xhigh and returned read-only evidence. No advisor
approved a project decision.

| Advisor | Disposition | Material evidence and recommendation | Stop gates and unknowns |
|---|---|---|---|
| Architecture boundaries | **REVISE THROUGH NARROW COMPOSITION; DO NOT REWRITE** | Retain native/provider, acquisition, deterministic evidence, entity, audit, and projection owners. Compose shared policy, capability, universe, read-model, and opportunity responsibilities. Separate bootstrap readiness from optional/dynamic advisory readiness. | Exact SessionMetricsActor split, event mechanics, agent authority, persistence mechanics, and execution topology remain undecided. Account/portfolio risk and execution coverage are missing. |
| Nautilus alignment | **USE/WRAP NATIVE; CUSTOM PRODUCT SEMANTICS WHERE JUSTIFIED** | Installed RC3 provides the node, data engine, cache, actor lifecycle, native feeds, historical requests, CustomData, signals, queue telemetry, bar types, indicators, and optional persistence/risk/execution primitives. Current native path and logical acquisition wrapper are aligned. | Type availability does not prove IB delivery, provider semantics, native/custom parity, persistence fitness, or execution readiness. No custom bus/cache, second node, dynamic actor infrastructure, or native indicator cutover is justified. Exact split is deferred. |
| Data quality and lineage | **CURRENT FOUNDATION ADMISSIBLE WITH LIMITS; DESIRED JOINS NOT VERIFIED** | CompletedBarInput and evidence-health contracts are strong for exact accepted paths. Generic metric identity is incomplete, cross-instrument joins are absent, expected-population completeness/corrections are partial, and demand-to-request causation is incomplete. | Calendar authority is latent-conflicting for runtime mutation; native/custom parity, provider timestamps, corrections, restored state, cross-instrument joins, and final named-use fitness remain stopped. |
| Event-driven architecture | **FOUNDATION PARTIAL; GOVERNED EXECUTABLE LIFECYCLE MISSING** | Stable demand IDs, shared subscriptions, historical scheduling, lifecycle vocabulary, snapshots, and bounded audit are reusable. A distinct intent, decision, command, claim, attempt, event, result, and snapshot chain is required. | Historical late-callback correlation, unbounded pre-queue pending sets, no autonomous live retry/reconnect, incomplete shutdown outcomes, and no end-to-end idempotency/acknowledgement are material stops. |
| Market structure | **PARTIAL REUSE; MATERIAL EXTENSION REQUIRED** | Exact-horizon entity/revision/state primitives, swings, legs, pivots, levels, FVGs, zones, and limited market-state contracts are reusable. Current rolling families provide exact numerical context. | Broader direct horizons, cross-horizon relationships, cross-instrument state, semantic interaction, runtime/connected acceptance, durability, and agent-safe evidence identity are missing. Geometry is not forecast or trade meaning. |
| Market microstructure and order flow | **PARTIAL QUOTE/BAR REFINEMENT; OBSERVED ORDER FLOW UNAVAILABLE** | Current runtime can honestly name provider top-of-book observations, midpoint/quoted spread, completed-bar geometry, reported bar volume, and inferred bar-volume response proxies. | NBBO, broad trade-tape coverage, classifier, delta/CVD, recovered books, depth/resilience, true effort-response, participant intent, and cross-instrument flow are unavailable or unknown. Provider, quantitative, fitness, and licensing handoffs are required. |
| Statistical learning and optimization | **RESEARCH_ONLY; BLOCKED FOR TRAINING, SHADOW PROMOTION, OR ADAPTATION** | Versioned deterministic evidence and parameter envelopes are useful foundations. No reproducible point-in-time dataset, label card, leakage-safe evaluation, immutable prediction record, calibration, model monitor, or optimization objective exists. | Stage 9K data strategy, source rights, as-of reconstruction, named-use fitness, protected evaluation, and governed change lifecycle are required. No live mutation or model-derived authority. |
| Live-agent governance | **GOVERNANCE-COMPATIBLE DIRECTION; NO LIVE AGENT ADMISSIBLE NOW** | Existing demands may be post-policy internal commands only. Agents require independent grants, typed intents, deterministic decisions, approvals/revocations, bounded resources, immutable read-model snapshots, first-class abstention, separate claims, and reconstructible audit. | Pre-9I reliability/evidence gates, security/licensing context-release review, opportunity semantics, persistence, provider/options, account/portfolio risk, and execution coverage remain missing. Execution tools are forbidden now. |

### 5.1 Reconciled tensions

The council did not produce an unresolved disagreement requiring one advisor to override another.
It did identify four tensions which the primary synthesis resolves conservatively:

1. **SessionMetricsActor:** architecture sees a structural bottleneck; Nautilus does not justify a
   specific split or native replacement. Reconciled disposition: accept the limitation, preserve
   exact current behavior, and defer the mechanism until subject identity, canonical admission,
   direct/native-composite parity, workload, and lifecycle evidence exist.
2. **Calendar ownership:** identical startup definitions make current equal results plausible, but
   the accepted sole-owner posture and future runtime mutation require a stronger contract.
   Reconciled disposition: no claim of present measured divergence; classify the authority as
   conflicting for future mutation and require a definition digest/effective epoch.
3. **Single versus multiple agents:** accepted roadmap language is primarily singular while the
   desired runtime allows several agents. Reconciled disposition: decide separately whether the
   first operation uses one agent, but make identity, grants, budgets, claims, and conflict rules
   multi-agent-safe from the first accepted schema.
4. **No raw retention versus Stage 9K:** current retention boundaries prevent accidental
   infrastructure and should remain. They do not prove that future learning is impossible.
   Reconciled disposition: retain now; reopen only through an approved Stage 9K data strategy,
   provider/licensing review, and explicit persistence/retention decision.

## 6. Constraint Review

No change below is accepted by this report. Each recommendation remains for Markeitect's decision.

| Existing constraint or boundary | Recommendation | Original purpose | Consequence of retaining unchanged | Consequence and risk of change | Decision authority |
|---|---|---|---|---|---|
| One data-only LiveNode and native high-volume path | **RETAIN** | Use Nautilus lifecycle, cache, normalized objects, and adapters; avoid duplicate raw truth. | Supports the desired runtime and keeps one technical data plane. | A second node/bus/cache adds ownership, ordering, recovery, and operational cost without current evidence. | Markeitect after Nautilus/architecture evidence. |
| One logical provider-demand owner | **RETAIN** | Prevent duplicate subscriptions and unsafe cancellation. | Compatible with dynamic claims if policy and membership remain upstream. | Multiple executors would duplicate provider traffic and obscure lifecycle truth. | Markeitect. |
| Static responsibility-keyed actor composition initially | **RETAIN** | Keep lifecycle and failure ownership explicit and bounded. | Dynamic instruments/capabilities can be state within stable owners. | Runtime actor loading adds lifecycle complexity and is not required by current evidence. | Markeitect after measured workload evidence if revisited. |
| Static watchlist as bootstrap authority | **REVISE** | Provide deterministic cold start and readiness. | Safe bootstrap remains, but using it as the only universe prevents desired runtime membership. | Separate dynamic/optional membership can create readiness and ownership ambiguity unless one owner and versioned policy are defined. | Markeitect. |
| Static watchlist as the complete observation universe | **REMOVE AS A FUTURE INVARIANT** | It was an accepted stopping point after Stage 8 proof, not permanent product direction. | Blocks desired runtime instrument changes and focus. | Removal must not mutate bootstrap readiness or give policy/acquisition/agents competing membership authority. | Markeitect. |
| Direct AnalyticalDemandEvent-to-acquisition for current internal analyzers | **RETAIN INTERNALLY, REVISE FOR AGENT USE** | Simple typed feed demand from trusted current components. | Works for static internal producers but cannot prove agent authority. | A new pre-policy intent boundary and authorized command identity add contract/audit work but prevent acquisition from becoming an accidental governor. | Markeitect after governance/event design. |
| Singular completed-bar/session/rolling actor foundation | **REVISE** | Delivered a coherent bounded first measurement stage. | Continues to limit independent selectors, horizons, histories, and capability lifecycles. | Splitting too early can create duplicate canonical bars and parity drift. First define identity, admission, overlap, lifecycle, and direct/native-composite evidence. | Markeitect after architecture/Nautilus/data/quantitative review. |
| Independent copied calendar evaluation in three owners | **REVISE** | Let each component calculate bounded windows without synchronous coupling. | Plausibly equal at immutable startup, but cannot support honest runtime mutation or complete provenance. | Canonical facts or digest-verified independent evaluation requires a definition identity, effective epoch, atomic switch, and migration/revision policy. | Markeitect after calendar/data architecture review. |
| Current broad CME OPEN envelope and unverified schedule-version label | **INVESTIGATE** | Provide a provisional session envelope for V3 debugging. | Can misclassify maintenance breaks and falsely degrade evidence. | Correcting it requires dated calendar/provider authority and regression/connected acceptance; no values are selected here. | Markeitect with calendar/provider evidence. |
| Completed bars are first-accepted and unequal later values conflict | **INVESTIGATE** | Preserve deterministic current-runtime truth and prevent silent revisions. | Safe for current bounded use, but does not provide provider correction finality or point-in-time revision history. | A correction lifecycle affects downstream recomputation, semantic invalidation, ML as-of reconstruction, and audit. | Markeitect after provider/data/event/semantic review. |
| Bars and bar volume never become observed order flow | **RETAIN** | Preserve source fidelity and prevent fabricated flow/intent. | Correctly limits claims to geometry and explicit proxies. | Relaxing it would misrepresent evidence. True flow requires trades/quotes/books, classifier, corrections, coverage, and fitness evidence. | Evidence invariant; not a tunable product rule. |
| Current advisory-only/no-order posture | **RETAIN** | Protect the system from unauthorized financial side effects. | Does not prevent a separately designed future program. | Weakening it now creates unowned account/risk/execution authority and unacceptable damage potential. | Markeitect through a separate risk/execution stage. |
| Initial SPXW/SPY/QQQ 0DTE expression seed | **REVISE OR RETAIN BY EXPLICIT PRODUCT DECISION** | Keep initial product scope bounded and options-specific. | Conflicts with desired SPY/QQQ 1-3 DTE and ES/NQ futures expression scope. | Broadening introduces new expiry, settlement, margin, leverage, account-risk, session, and execution semantics. | Markeitect with product/options/futures/risk specialists. |
| No raw provider observations in PostgreSQL | **RETAIN** | Keep PostgreSQL an operational/semantic audit rather than a market-data warehouse. | Compatible with current live-first architecture. | Changing it would require source rights, retention, schema, scale, recovery, deletion, and data-strategy decisions. | Markeitect after persistence/licensing/data-strategy review. |
| No replay/backtesting or speculative raw retention | **RETAIN NOW; INVESTIGATE ONLY AT STAGE 9K** | Prevent hypothetical paths from driving current infrastructure. | Blocks premature ML claims but not research-contract design. | A future data strategy may need external point-in-time history or prospective capture; that must not be smuggled in as incidental work. | Markeitect. |
| No Redis, external stream, or custom raw-data bus | **RETAIN** | Avoid unmeasured infrastructure and competing state/ordering owners. | Native RC3 messaging/cache is sufficient for current in-process needs. | Revisit only for measured cross-process/deployment need with architecture, recovery, security, and operations evidence. | Markeitect. |
| Singular Sir Loke wording in accepted roadmap | **REVISE FOR CARDINALITY, NOT AUTHORITY** | Describe the first advisory agent simply. | Risks retrofitting principal/claim/budget identity after implementation. | Multi-agent-safe schemas add early complexity but prevent agents from becoming competing policy/evidence owners. | Markeitect. |
| Model/agent parameters are optimization-ready but not automatically mutable | **RETAIN** | Separate tunability from authority and evidence truth. | Supports later governed experimentation. | Automatic mutation without data, objectives, approval, rollback, and monitoring would create feedback and authority failures. | Markeitect through policy and Stage 9K gates. |

## 7. Broad Target Architecture In Words

This is a responsibility model, not a low-level design or an approval.

### 7.1 Native data plane

Keep one data-only Nautilus LiveNode. Nautilus and the IB adapter own technical connectivity,
normalized native observations, the DataEngine, cache, and supported actor lifecycle. High-volume
quotes, trades, bars, books, and option data remain on native paths when each feed is actually
supported and accepted.

DataAcquisitionActor remains the sole logical owner which converts authorized desired demand into
provider subscriptions and historical requests, deduplicates compatible work, preserves consumer
claims, observes lifecycle, and releases the provider effect only after the last valid claim ends.
It does not decide whether an agent is allowed to ask.

### 7.2 Deterministic control plane

Introduce one shared deterministic governance path with distinct responsibilities:

- an intent ingress receives typed proposals from operators or agents;
- a policy/resource governor checks principal/grant, allowed type, scope, parameters, evidence
  state, provider/runtime capacity, aggregate budget, priority ceiling, approval requirement,
  expiry, and audit availability;
- a versioned observation-universe owner maintains bootstrap and approved dynamic membership
  without owning provider subscriptions;
- a capability registry/manager owns approved capability definitions, dependency expansion,
  activation/preparation/reconfiguration state, and resource estimates while capability actors
  retain calculation truth.

Intent, policy decision, approval, authorized command, claim/lease, attempt, lifecycle occurrence,
observed effect, result, and read-model projection remain separate identities. Accepted never
silently means dispatched, active, ready, fit, or completed.

Stable responsibility-keyed actors should remain the initial runtime shape. Dynamic membership and
capability activation are state changes inside accepted owners, not automatic reasons for runtime
actor construction.

### 7.3 Evidence and intelligence plane

Retain capability-specific deterministic measurement and entity owners. Each evidence item must be
self-describing or refer immutably to a complete evidence envelope covering:

- instrument/contract/provider/venue/source identity;
- exact selector, timeframe, window, session, calendar definition and epoch;
- event, receipt, calculation, publication, and as-of clocks;
- historical/live/restored/aggregate lineage;
- definition, parameter, configuration, and revision identity;
- completeness, gaps, duplicates, conflicts, corrections, freshness, health, and fidelity; and
- permitted and forbidden downstream inferences.

Resolve calendar authority before runtime calendar/profile mutation. Support several exact
timeframes through independently identified dependencies rather than one hidden base pyramid.
Direct provider bars should be preferred when they meet the exact contract; native composites or
indicators remain shadow/parity candidates until equivalence is proved.

Retain exact-horizon structure independently. Add a same-instrument cross-horizon relationship only
after it can select exact source revisions under one as-of cutoff while preserving conflicts and
missingness. Add cross-instrument relationships later through a dedicated owner with exact member
roles, clocks, join tolerance, session/roll mapping, normalization, validity, decay, and
falsification. Agents must not calculate these relationships independently.

### 7.4 Agent read and advisory plane

One shared read-model projector builds compact immutable snapshots from admitted canonical
evidence. It does not query arbitrary raw streams, calculate market truth, or erase upstream
limitations. Each snapshot has one as-of identity and resolves every cited revision, conflict,
missing lane, readiness state, and permitted inference.

One or more agents consume only authorized snapshots and typed tools. Each agent has an independent
principal, role, grant, invocation, budget, and claim identity. Agents may maintain local
hypotheses, propose bounded evidence work, publish typed advisory claims, or abstain. They may not
own canonical market evidence, authorize themselves, widen policy, call IB, query arbitrary SQL,
mutate configuration files, run arbitrary code, or create execution authority.

A separate canonical opportunity lifecycle owner, after its semantics are approved, admits,
revises, invalidates, expires, and preserves plural advisory opportunities. Agent proposals do not
become canonical because of confidence, rank, recency, model seniority, or last-writer arrival.

### 7.5 Audit and projections

Preserve the operational audit owner. Add analytical, agent, opportunity, model, or control-state
durability only after each logical owner, schema, retention, recovery, and write-before-dependent-
progress boundary is approved. PostgreSQL remains an audit and approved semantic-state boundary,
not the bus or a raw market-data warehouse.

Discord, console, visual tools, and later UI remain projections of canonical state. They never
recalculate truth or mutate it.

### 7.6 Future execution boundary

Do not add a dormant or discoverable order tool. If Markeitect later opens execution, create a
separate authority namespace and program with independent account/portfolio risk, permissions,
approvals, execution/order lifecycle, broker acknowledgement, position/account reconciliation,
ambiguous-effect handling, cancellation, kill switches, recovery, audit, and operator oversight.
An advisory grant cannot be reinterpreted as an execution grant.

## 8. Council-Proposed Work Areas

The areas below preserve the council's proposed direction for later reference. They are not stages,
an ordered work plan, prerequisites for current work, or changes to the canonical Stage 9 sequence.
Their letter labels are reference labels only. A proposal becomes actionable only if Markeitect
selects it during the relevant stage and approves its exact scope.

### Proposal Area A: Resolve destination and authority decisions

**Scope**

- decide whether the accepted expression universe expands to SPY/QQQ 1-3 DTE and ES/NQ futures;
- decide whether the first agent is operationally singular while contracts are multi-agent-safe;
- accept or reject the proposed separation among evidence owners, policy/resource governor,
  observation-universe owner, capability manager, read-model projector, opportunity owner, and
  agents;
- decide which request classes could ever be automatically authorized within an envelope;
- confirm that future execution is a separate program and authority namespace.

**Acceptance evidence**

- updated smallest authoritative product/architecture documents;
- no implementation or provider run;
- explicit missing-specialist plan for any newly accepted product/risk scope.

### Proposal Area B: Close current reliability and evidence-identity debt

**Reuse**

- existing acquisition coordinator, historical executor, session/evidence actors, completed-bar
  ledger, metrics/entities, state books, resource telemetry, and audit worker.

**Required work before agent direction**

- bounded autonomous live-subscription retry/reconciliation and connection recovery;
- explicit effect-unknown behavior;
- safe historical request/callback correlation after timeout/cancel;
- admission bounds before pending/deferred/retry sets;
- shutdown admission cutoff, no new dispatch, terminal per-claim outcomes, late-callback quarantine,
  and unresolved-effect accounting;
- canonical calendar-definition identity/effective epoch and cross-component parity;
- lossless agent-eligible evidence envelope or immutable references;
- parameter effective-time/configuration identity enforcement where runtime use depends on it;
- deterministic LiveNode disposal/cleanup investigation;
- current adaptive architecture documentation drift correction in a separately approved batch.

**Acceptance**

- deterministic duplicate/conflict/retry/reconnect/overflow/restart/shutdown fixtures;
- provider-specific connected recovery run only when explicitly authorized;
- reconciled resource, persistence, unaffected-work, and controlled-shutdown evidence;
- no agent or model access.

### Proposal Area C: Introduce governed dynamic control offline

**Scope**

- principal/role/grant and non-delegation contracts;
- intent, decision, approval, revocation, command, claim/lease, attempt, event, result, and snapshot
  identities;
- observation-universe membership separate from bootstrap readiness;
- capability registry/manager definitions and dependency expansion;
- aggregate per-agent/global budgets, priority ceilings, expiry, reservation, cancellation, and
  protected capacity;
- logical audit reconstruction graph.

**Reuse**

- lower-level ObservationDemand, AcquisitionCoordinator, CapabilityDeclaration, historical
  compiler, existing config bounds, and resource telemetry.

**Acceptance**

- deterministic fixtures only;
- forged/expired/revoked/out-of-scope requests fail closed;
- same-ID duplicates replay status and same-ID conflicts fail;
- several agents cannot evade aggregate budgets;
- no provider command or model access.

### Proposal Area D: Complete the broader deterministic evidence substrate

**Scope**

- evaluate the narrowest honest completed-bar ownership change;
- add direct broader-timeframe dependencies and exact-horizon applications only where one named
  decision question requires them;
- add same-instrument cross-horizon as-of relationship;
- retain explicit missing/conflicting horizons without a universal score;
- complete runtime/connected acceptance for the selected Stage 9D structures;
- implement approved analytical-summary durability only if a live requirement justifies it.

**Stop gates**

- no daily/weekly claim from a long intraday lookback;
- no native composite or indicator cutover without exact parity;
- no geometry-to-semantic or geometry-to-order-flow upgrade.

**Acceptance**

- exact selector/session/calendar/roll/completeness/revision fixtures;
- multi-horizon cutoff, late arrival, conflict, expiry, and restart fixtures;
- quantitative/final-fitness review for each named downstream use.

### Proposal Area E: Complete Stage 9E and Stage 9F boundaries

**Scope**

- define and accept minimal semantic interaction/event meaning;
- define bounded options mechanics, sessions, contract discovery, quotes/Greeks, references,
  liquidity, lifecycle, and resource proof.

**Required coverage**

- semantic-event/opportunity specialist;
- options 0DTE specialist;
- IB provider specialist;
- data quality, quantitative validation, evidence fitness, licensing/provenance, and risk coverage
  where material.

**Acceptance**

- offline event lifecycle and options-contract fixtures;
- bounded provider acceptance only when explicitly authorized;
- no agent execution or product-rule inference.

### Proposal Area F: Add cross-instrument state

**Scope**

- exact relationship definitions, member roles, horizon, as-of cutoff, availability clocks,
  maximum skew, normalization, session/roll/proxy identity, missing/conflict behavior, validity,
  decay, revision, and falsification;
- one canonical relationship owner.

**Required coverage**

- add or approve a dedicated cross-market relationship specialist before consequential
  leadership/lag/causal semantics.

**Acceptance**

- deterministic asynchronous-arrival, stale-member, missing-member, conflicting-session, roll,
  and revision fixtures;
- bounded connected evidence for exact selected instruments;
- no fixed causal rule from the examples in desired-arch.md.

### Proposal Area G: Add optional true microstructure only for a named decision

**Scope**

- begin with current provider quoted-friction evidence if it answers the question;
- add trades or books only after exact provider/adapter/venue/coverage contracts;
- version classifier, quote alignment, ambiguity, corrections, gaps, reset, restart, and coverage;
- keep bar-volume response as an explicitly inferred proxy.

**Acceptance**

- provider truth and entitlement evidence;
- labelled classifier/coverage fixtures;
- correction and restart reconciliation;
- quantitative validation and final named-use fitness;
- licensing/retention/display decision.

Delta, CVD, books, absorption, exhaustion, and participant hypotheses remain unavailable until
their exact evidence contract passes.

### Proposal Area H: Build Stage 9I read-only governance before mutable tools

**Scope**

- immutable agent read model and named-use admission;
- citation resolution and output classification;
- principal/grant/policy/approval/revocation enforcement;
- typed abstention;
- exact invocation/model/prompt/tool-schema/snapshot audit;
- security/licensing/privacy/provider context-release gate.

**First runtime mode**

- read-only shadow advisory use;
- no observation/capability/configuration mutation;
- no order/provider/credential/SQL/shell/code/unrestricted-config tool;
- no opportunity canonicalization until its owner is accepted.

**Acceptance**

- missing/stale/conflicting/unsupported evidence causes scoped abstention;
- malformed or fabricated citations fail;
- one agent failure does not stop deterministic runtime or another future agent;
- bounded model/tool loops, latency, tokens, context, and cost;
- no execution surface discoverable.

### Proposal Area I: Add one bounded governed request class

Only after the reliability and read-only governance gates pass, expose the smallest approved
request type behind the governor. Existing acquisition/capability owners receive only authorized
internal commands. Prove:

- requested versus authorized arguments;
- aggregate budget reservation;
- accepted versus dispatched versus active versus ready versus partial versus terminal outcomes;
- expiry/revocation/release;
- effect-unknown reconciliation;
- audit and restart behavior;
- unaffected live work.

Add other request classes one at a time. Configuration proposals should remain disabled initially
unless Markeitect explicitly accepts them.

### Proposal Area J: Add plural advisory opportunities

After semantic ownership is accepted:

- admit multiple target-exposure opportunities and expression candidates;
- keep agent claims separate from canonical state;
- preserve conflicts and abstentions;
- project revisions/invalidations/expiry to operators;
- record operator disposition independently;
- maintain explicit no-execution classification.

### Proposal Area K: Open statistical-learning work only through the accepted data gate

First approve:

- one named decision, baseline, horizon, action/abstention boundary, and label card;
- exact historical/prospective data source and rights;
- point-in-time as-of/revision/calendar/config/universe reconstruction;
- immutable dataset identity and construction manifest;
- protected chronological evaluation with grouping, gaps/embargoes, fold-local preprocessing,
  calibration separation, search accounting, and final forward evidence;
- immutable prediction/outcome reconciliation;
- model envelope, monitoring, disable/rollback, and human approval.

Until then, Stage 9K remains research-only. Training, shadow promotion, probabilities, online
learning, automatic retraining, and live parameter optimization remain blocked.

### Separate future program: risk and execution

Execution is not the last substep of advisory work. It requires a separately approved architecture,
specialist council, sandbox/paper evidence, account/portfolio risk authority, execution provider
truth, permissions/security, order and position reconciliation, kill switches, recovery, and
operator approval. No present stage creates that authority.

## 9. Risks, Stop Gates, And Missing Specialist Coverage

### 9.1 Highest architectural risks

1. **Authority collapse:** exposing current demand APIs to an agent would combine proposal,
   authorization, provider execution, and readiness.
2. **Identity loss:** flattening metrics/entities into a compact agent view without full immutable
   references would make timeframe, calendar, configuration, and as-of meaning unrecoverable.
3. **Readiness inflation:** connected, subscribed, first-observed, numerically available,
   evidence-ready, named-use-fit, advisory-ready, and execution-ready can be confused.
4. **Unbounded multi-agent demand:** individually valid requests can exhaust shared provider,
   runtime, model, audit, or notification capacity.
5. **Ambiguous provider effects:** blind retry after uncertain subscription/history/execution
   effects can create duplicates or false completion.
6. **Calendar drift:** copied mutable definitions can assign different session truth without a
   visible epoch or conflict.
7. **Market-semantic overreach:** exact geometry can be relabelled trend, support/resistance,
   order flow, causality, or trade signal without accepted semantics.
8. **Statistical leakage:** current values can be recomputed under later calendars/configuration or
   joined after their true availability cutoff.
9. **Persistence overreach:** generic operational audit or native cache/catalog availability can
   be mistaken for fitness as analytical, agent, or model storage.
10. **Execution creep:** future compatibility can be misread as permission to add dormant order
    tools or let advisory confidence influence risk authority.

### 9.2 Missing coverage and affected conclusions

| Missing or unselected specialist | Why material | Conclusion that must stop |
|---|---|---|
| Account/portfolio risk | Desired risk objective includes trade, correlated exposure, agent, account, and portfolio damage. | Risk architecture, sizing, limits, aggregate exposure, affordability, and future execution safety. |
| Execution/order lifecycle | Orders, acknowledgements, partial fills, cancels, rejects, ambiguous effects, positions, and reconciliation are separate from data acquisition. | Any execution topology or claim that future execution is a configuration change. |
| Security/tool boundary | Agent/model access introduces authentication, secrets, permissions, tool isolation, prompt injection, redaction, external surfaces, and safe failure. | Model-context release, live tools, approval enforcement, credential/provider/account exposure. |
| Vendor licensing/provenance | Provider/model use, retention, derived data, display, redistribution, and export may carry contractual duties. | External model release, retention, dataset use, visualization/export, and vendor-flow use. |
| IB provider truth | API types do not establish entitlements, pacing, fields, sessions, timestamps, corrections, chains/Greeks/books, reconnect, or cancellation. | Provider-specific capability and budget claims. |
| Options 0DTE mechanics | SPXW/SPY/QQQ identity, expiration, settlement, sessions, chain, Greeks, quote liquidity, and last-trade rules are product-specific. | Detailed options target architecture and acceptance. |
| Options flow | Vendor prints, classifications, OI timing, complex orders, filters, and intent limits are separate. | Options-flow interpretation and any participant/directional claim. |
| Semantic events/opportunity lifecycle | Geometry/state does not define approach, acceptance, rejection, opportunity identity, merge, revision, or non-admission. | Stage 9E/9J meanings and canonical opportunity ownership. |
| Quantitative metric validation | Native/custom formulas, aggregation, units, warmup, numerical parity, and classifier metrics require exact validation. | Metric substitution, native indicator adoption, classifier/delta/CVD formula claims, learning feature validity. |
| Final evidence fitness | Quality and formula validity do not decide fitness for one named downstream use. | Admission to Sir Loke, a model feature, a semantic event, visualization, or release. |
| PostgreSQL persistence mechanics | Logical durability does not define schemas, migrations, transactions, indexes, recovery, retention, or observability. | Any physical dynamic-control, agent, opportunity, model, or analytical-summary design. |
| Python runtime mechanics | Accepted outcomes do not define tasks, timers, queues, cancellation, worker ownership, or shutdown implementation. | Consequential runtime mechanics outside established Nautilus guarantees. |
| Cross-market relationships | Current market-structure role excludes a dedicated causal/relationship specialty across instruments. | Leadership, lag, catch-up, causal, and relationship-confidence semantics. |

Missing coverage does not prevent this report from classifying the relevant desired capability as
missing, planned, unknown, or deferred. It prevents a consequential design or acceptance
conclusion in that domain.

## 10. Questions Preserved For Later Decisions

These questions are not one global approval gate. Each belongs to the stage where its answer can
materially affect an approved scope; later-stage questions remain deferred while current approved
work continues.

1. **Product scope:** Should the accepted initial expression scope expand from SPXW/SPY/QQQ 0DTE
   to SPY/QQQ 0-3 DTE and ES/NQ futures, or should those desired items remain future candidates
   pending separate product/risk review?
2. **Core authority model:** Should Markeitech retain the proposed separation among evidence
   owners, policy/resource governor, observation-universe owner, capability manager, read-model
   projector, opportunity owner, advisory agents, and Markeitect?
3. **Dynamic membership:** Should the static watchlist remain only bootstrap authority while one
   versioned observation-universe owner controls optional runtime membership and keeps its failures
   out of global bootstrap readiness?
4. **Calendar authority:** Should consumers use canonical published boundary facts, or may they
   independently evaluate one digest-verified immutable calendar definition? What is the approved
   effective-epoch and runtime-change behavior?
5. **Completed-bar ownership:** Should the next design gate evaluate separating completed-bar
   foundation from session/window/rolling measurement ownership, or first prove that multiple
   independent instances can coexist without duplicate canonical authority? No exact split is
   recommended yet.
6. **First broader horizons:** Which one named decision question justifies the first direct
   one-hour, daily, or weekly-reference evidence, and what exact instruments/sessions are in scope?
7. **Cross-horizon and cross-instrument coverage:** Should a dedicated cross-market relationship
   advisor be created/approved before detailed Stage 9G semantics? Which first relationship
   question should it own?
8. **First agent cardinality:** Should Stage 9I operate one agent initially while requiring
   multi-agent-safe principals, grants, budgets, claims, and conflicts from the first schema?
9. **Automatic versus approved requests:** Which read, observation, history, capability, focus,
   configuration-proposal, publication, and opportunity classes may be preauthorized inside an
   exact envelope, and which always require operator or Markeitect approval?
10. **Configuration proposals:** Should agent-proposed parameter changes remain entirely disabled
    in the first live-agent stage, even where metadata marks a field future policy-controlled?
11. **Audit failure:** Should consequential agent work fail closed whenever its required durable
    audit is unavailable while deterministic ingestion continues and the agent emits an
    audit-unavailable abstention?
12. **Model/provider release:** Which model/provider and exact evidence fields, if any, may leave
    the deterministic boundary after separate security, licensing, privacy, provider-terms,
    redaction, retention, and cost review?
13. **Optional microstructure:** What is the first named decision, if any, that justifies true trade
    or book evidence beyond quoted-friction and explicit bar-response proxies?
14. **Stage 9K data strategy:** Should the future learning path prefer an approved external
    point-in-time source, prospective bounded capture, or remain unopened until a stronger need is
    demonstrated? This report selects none.
15. **Future execution:** Should execution be formally declared a separate program and authority
    namespace with no discoverable order tool until account/portfolio risk, execution, provider,
    security, persistence/reconciliation, approval, and kill-switch specialists and evidence are
    accepted?
16. **Reliability sequencing:** Which currently recorded reliability debts must be fixed, and which
    if any may be explicitly accepted, before Stage 9I planning begins?

## 11. Final Council Recommendation

The desired runtime should be treated as **directionally compatible but not accepted**.

Retain the current native data path, acquisition owner, deterministic measurement/entity owners,
bounded state, operational audit, and projection-only outputs. Correct the current evidence
identity, calendar-authority, retry/recovery, correlation, admission, and shutdown gaps before
adding live-agent authority. Compose one shared deterministic governance/control plane and one
shared as-of read-model plane above the existing runtime. Keep agents advisory, independently
identified, bounded, auditable, and unable to acquire authority from prompts, confidence, rank, or
tool access.

Do not rewrite the runtime, introduce a custom raw-data bus/cache, make dynamic actors a
requirement, force native indicator/composite substitution, persist raw provider data
speculatively, promote bars to order flow, treat deterministic primitives as ML-ready, or add
execution surfaces.

This record requires no action by itself. Future stage-specific work may cite relevant findings and
raise only the decisions material to that bounded scope. Accepted repository authority, not this
report, determines the development sequence and implementation approval.
