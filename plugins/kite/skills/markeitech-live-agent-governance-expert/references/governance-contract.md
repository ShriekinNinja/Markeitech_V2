# Sir Loke Governance Contract

Read this reference completely for every substantive Sir Loke governance consultation. It defines
review requirements and policy candidates, not implemented runtime contracts or preapproved
product semantics.

## Authority Model

Sir Loke is an advisory reasoner with no inherent authority. A valid design keeps five identities
distinct:

1. **Evidence owner** publishes deterministic, versioned evidence and health.
2. **Sir Loke** reads a compact projection, records interpretations, abstains, and submits typed
   intents or advisory opportunity proposals.
3. **Policy governor** deterministically validates authority, bounds, budgets, health, approval,
   leases, and expiry. It may accept, modify, queue, reject, expire, or cancel an intent.
4. **Runtime owner** performs only the authorized work and reports execution and evidence
   lifecycle. An accepted request is not proof of execution, data flow, readiness, or success.
5. **Markeitect** retains final product, trading, architecture, review, release, and approval-policy
   authority. An **operator** is a separate identity which may exercise only explicitly delegated,
   typed, versioned operational authority.

No prompt, model output, confidence score, tool description, retrieved text, prior approval,
operator identity, policy acceptance, or agent memory can grant, widen, redelegate, or substitute
for Markeitect authority.

## Sir Loke-Facing Reference And Citation Minimum

A material observation or interpretation should make the following upstream-owned fields
representable at the Sir Loke boundary. Exact field names and storage are stage design decisions.
This advisor verifies preservation and resolvability; it does not define or recalculate evidence
identity, provenance, completeness, duplicate/conflict/revision meaning, timestamps, session
assignment, freshness, fidelity, or analytical sufficiency.

| Concern | Required meaning |
|---|---|
| Identity | Stable claim/observation ID, subject ID, schema version, producer, producer version |
| Classification | One evidence class; observation/measurement/entity/event/model/agent layer |
| Claim | Typed predicate/value/unit or typed state; prose may explain but not replace it |
| Scope | Instrument/contract, venue/provider, session, horizon, capability, and population as applicable |
| Time | Effective/event, observed, received, calculated, projected, and cited-at times as applicable; UTC internally |
| Provenance | Source record IDs or immutable evidence references, lineage, parameter/config/model versions |
| Health | Freshness/age, completeness, fidelity, readiness/warmup, entitlement/subscription, correction/conflict, missing reasons |
| Limits | Permitted inference, known exclusions, assumptions, uncertainty, expiry/invalidation |
| Relationships | Supporting, conflicting, superseding, causation, and correlation references |

Citation completeness is a deterministic validation question. The model may not satisfy it with an
uncited paraphrase or invented record ID. Summaries must preserve resolvable source references and
must not broaden scope beyond their constituents.

## Model Context Release Gate

Before live model access, require a reviewed contract for the exact compact read-model fields which
may leave the deterministic boundary. It must identify the selected model/provider/version, minimum
necessary scope, excluded fields, credentials and secrets prohibition, redaction boundary, licensed
or provider-material constraints, sensitive or personal data, external retention and Zero Data
Retention compatibility, maximum payload/resource bounds, and the audit record of what was
released. Unapproved fields, raw unlimited streams, arbitrary history, credentials, and unrelated
watchlist context fail closed.

This advisor owns the least-authority requirement and data-release acceptance question. Security,
privacy, legal, licensing, provider terms, redaction implementation, access controls, external
authorization, and retention decisions require their owning specialists and Markeitect.

## Agent Output Minimum

Every consequential Sir Loke proposal, revision, invalidation, or abstention should make these
elements independently inspectable:

- output identity, revision, lifecycle, agent/model/provider/prompt/tool-schema/policy versions;
- exposure, direction, horizon, scope, and advisory/no-execution label when applicable;
- typed thesis or abstention reason;
- supporting, conflicting, missing, stale, and unavailable evidence references;
- explicit separation of verified facts, measured evidence, inferences, hypotheses,
  recommendations, and unknowns;
- trigger, invalidation, expiry, alternatives, and unresolved contradictions;
- option-expression rationale and quality only when supplied by the options owner;
- tool/intents requested and their current lifecycle, without treating acceptance as completion;
- uncertainty dimensions rather than a single confidence scalar; and
- validation result plus an explicit reason when publication is rejected or narrowed.

Abstention is required when evidence needed for the decision is unavailable, stale outside its
approved envelope, materially contradictory without a policy-approved resolution, unsupported at
the requested scope/horizon, or incapable of distinguishing the remaining alternatives. The
abstention must cite what is missing or conflicting and may request bounded evidence; it must not
invent a conclusion to keep output cadence.

## Tool And Intent Minimum

For each tool or intent, require a reviewable contract containing:

- stable tool and schema identity/version, requesting agent/invocation, correlation and causation;
- one narrow purpose and one owning component;
- typed parameters with closed schemas, explicit units, enumerated scope, and `additionalProperties`
  rejection or equivalent;
- requested and authorized subjects, horizons, time bounds, quantities, fidelity, and resource
  estimates;
- policy identity/version/effective time and decision with machine-readable reasons;
- budget class, priority, lease/start/expiry/renewal/cancellation when work persists;
- mutability and human-approval class, approval identity, exact reviewed arguments, decision time,
  approver authority, and expiry where applicable;
- the required idempotency/correlation identity and bounded retry policy reference supplied by the
  executable owner's reviewed contract;
- accepted/modified/queued/rejected/expired/canceled execution lifecycle followed separately by
  requested/subscribed/active/ready/partial/failed/stopped evidence lifecycle as applicable;
- bounded result/error schema, freshness, completeness, continuation/pagination bounds, and
  sanitization; and
- audit linkage from request through policy, approval, dispatch, owner outcome, agent consumption,
  and operator projection.

Unknown tools, schema drift, malformed arguments, non-finite numeric values, out-of-envelope
parameters, ambiguous units, missing subjects, expired approval, or policy/audit unavailability
must fail closed before dispatch. The event-driven, Nautilus, or Python-runtime specialist owns the
exact delivery, duplication, retry, cancellation, reconciliation, restart, shutdown, and
partial-failure mechanics; this contract owns only the Sir Loke-facing governance invariant and
observable state distinctions.

## Tool Classes

### Compact reads

Read only from approved projections such as market state, evidence health, opportunity state, and
intent outcomes. Require bounded scopes/horizons, deterministic pagination, freshness, and maximum
response size. Exclude arbitrary SQL, raw provider streams, unlimited history, credentials, and
unrelated context.

### Data and capability requests

Sir Loke may request observation, historical evidence, capability activation, or focus only through
the deterministic governor and the existing owner. Requests declare exact purpose, dependencies,
bounds, cost estimate, priority, lease, and expiry. The agent neither translates a request into
provider calls nor selects hidden fallback data.

### Subscription and option-chain requests

The agent requests a bounded analytical need; it never subscribes. The acquisition or options
owner controls provider translation, entitlement, pacing, deduplication, candidate windows,
contract identity, quote/Greek scope, refresh, and release. Reject unrestricted chains and implicit
strike, expiry, session, premium, instrument, or refresh rules. All such values remain approved
typed/versioned configuration or request parameters inside deterministic envelopes.

### Configuration proposals

Sir Loke may propose a typed change intent only for parameters explicitly marked agent-proposable
and within a separately approved envelope. It cannot write configuration, alter policy envelopes,
change code/schema, select its own mutability class, or approve its proposal. The policy candidate
must define parameter identity, current/proposed value, unit/type, scope, rationale/evidence,
authorized range/step, source, version/effective time, approval class, activation boundary,
expiry, rollback, and full audit. Unknown or startup-only parameters remain unchanged.

### Opportunity and abstention writes

Writes target only a typed advisory lifecycle owner. They do not mutate deterministic evidence,
positions, accounts, orders, provider state, or configuration. Schema validation, evidence
citations, idempotent revision rules, and no-execution labels precede publication.

## Human Approval Policy Candidates

Do not choose approval policy values inside this advisor. Require Markeitect to approve the policy
taxonomy and its typed/versioned configuration. Candidate distinctions include:

- read-only inspection inside an already authorized scope;
- temporary resource request inside a preapproved envelope;
- expensive, paid, entitlement-sensitive, or materially capacity-affecting request;
- runtime-mutable configuration proposal;
- between-session or startup-only change;
- external publication or operator notification;
- architecture, persistence, schema, provider, security, product-semantic, or trading change; and
- any future action with financial or execution effect.

Approval must be specific, informed, attributable, reviewable before dispatch, and bound to the
exact action, arguments, policy/tool versions, scope, and lifetime. Denial, timeout, withdrawal,
and restart must remain explicit states. Never infer approval from silence, prior conversation,
model confidence, or a similar earlier action.

Architecture, infrastructure, persistence, schema, provider ownership, runtime policy, product
semantics, trading, review, release, and any future execution authority remain Markeitect-only
decisions. An approved policy may delegate bounded operational actions to a named operator, but it
cannot delegate or transform those final authorities.

## Agent State And Recovery

Separate deterministic read-model state, agent working hypotheses, durable advisory records, and
conversation/model context. Agent hypotheses may reference but never overwrite evidence truth.
Define lifecycle for creation, revision, contradiction, invalidation, expiry, compaction, and
restart. Bound hypothesis/opportunity count, evidence references, context size, tool iterations,
wall time, tokens, latency, and cost through configuration.

After restart, require revalidation of evidence freshness, policy/tool/config versions, approvals,
active leases, pending intents, and opportunity validity before resuming. Stale authority must not
resume, and ambiguous work must be handed to the executable owner's reviewed reconciliation
contract; never replay a side effect solely because the model did not observe its result. Model
outage, malformed output, tool loop, or agent crash must not erase deterministic state or stop
unrelated ingestion and analysis. The exact restart, reconciliation, cancellation, and isolation
mechanics come from the event-driven, Nautilus, or Python-runtime specialist as applicable.

## Audit And Traceability

Decision reconstruction should link:

`invocation -> read-model snapshot -> evidence references -> model/prompt/inference settings ->
structured output -> tool calls -> validation -> policy -> human approval -> owner execution ->
tool result -> state revision -> projection/delivery outcome`

Record stable identities, versions, event and processing time, actor/authority, exact validated
arguments, machine-readable decisions/reasons, retries, latency, resource/token/cost counters,
errors, and lifecycle. Audit failure is not permission to continue a consequential action whose
durability is required.

Trace capture can expose prompts, market context, credentials, personal data, or provider material.
Require approved content, redaction before export, access, retention, deletion, and Zero Data
Retention decisions before enabling it. Security, privacy, legal, provider, and persistence owners
define those mechanisms and policies. Traces are diagnostic evidence, not canonical market or
opportunity state.

## Failure Containment And Offline Acceptance

At minimum, deterministic fixtures should prove the following governance outcomes, using the
applicable adjacent specialist's executable contracts rather than inventing their mechanics:

- required citation omissions, fabricated references, class promotion, stale evidence, scope
  widening, and hidden contradictions are rejected or force abstention;
- malformed, unknown-version, out-of-bounds, excessive-scope, non-finite, duplicate, and expired
  requests fail closed without owner dispatch;
- approval denial/timeout/withdrawal, policy outage, audit failure, tool timeout, partial result,
  retry exhaustion, and loop ceilings produce explicit bounded outcomes;
- untrusted instructions in evidence or tool results cannot grant permission or alter the task;
- accepted, executed, active, ready, partial, failed, canceled, and expired remain distinct;
- restart reconciles pending work without duplicate side effects or stale authority;
- unrelated ingestion and deterministic capabilities survive agent failure; and
- no order-routing, provider-credential, arbitrary query/code, or unrestricted configuration tool
  is discoverable to Sir Loke.

Connected acceptance is separately authorized and cannot be inferred from offline tests. It should
be the smallest run necessary to prove real owner delivery, policy/audit reconciliation, resource
bounds, failure isolation, and shutdown without granting the agent execution authority.

## Overlap And Escalation

- Consult the Nautilus advisor for actors, message bus, lifecycle APIs, cache, adapters, and native
  framework ownership. This advisor owns the governance requirement, not the framework mechanism.
- Consult the event-driven architecture specialist for delivery, ordering, acknowledgement,
  duplication, idempotency implementation, retry, reconciliation, cancellation, queue admission,
  backpressure, supervision, restart, shutdown, and partial-failure execution. This advisor owns
  the Sir Loke governance invariant, not those mechanics.
- Consult the Python runtime advisor for asyncio, concurrency, worker isolation, serialization,
  process safety, resource implementation, and non-Nautilus execution mechanics. This advisor owns
  the required governance outcome, not its executable implementation.
- Escalate market semantics, evidence sufficiency, confidence/calibration, opportunity meaning, and
  option selection to the relevant market/options specialists and Markeitect.
- Escalate provider capabilities, entitlements, pacing, chain/Greek semantics, and subscription
  translation to provider/options owners.
- Escalate schema, retention, deletion, recovery, migrations, durable audit ownership, backup,
  restore, and database observability to persistence and architecture review.
- Escalate authentication protocols, cryptography, secrets, threat modeling, privacy, compliance,
  and external-service authorization implementation to security/legal/privacy specialists.
- Stop before execution, risk, account, position, order, or kill-switch design; those require a
  separately approved execution-and-risk stage and specialist coverage.

When overlap is unresolved, return the governance invariant, name the missing specialist evidence,
and defer the consequential recommendation rather than impersonating adjacent expertise.
