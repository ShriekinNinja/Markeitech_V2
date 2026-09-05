# Kite Per-Consultation Resource Allocation

**Status:** Proposed for Markeitect's decision; no allocation behavior is changed.

**Tracking:** [Issue #39](https://github.com/ShriekinNinja/Markeitech_V2/issues/39)

**Evidence date:** 2026-09-05

This proposal makes primary Kite responsible for choosing each advisor consultation's model and
reasoning effort within validated policy. The [council guide](kite-advisor-council.md) continues
to describe current behavior. This document is not an accepted replacement for that behavior.

## Decision Requested

Approve this bounded design before changing role configuration:

1. Put allocation intent in each advisor's existing plugin-owned `council-policy.toml` entry.
   Centralize concrete resource mappings in the same file; advisor entries reference named
   profiles. Do not add unsupported metadata keys to Codex custom-role TOMLs.
2. Remove both execution overrides from all 20 custom-role files together. Preserve exact names,
   instructions, read-only defaults, MCP restrictions, source gates, and non-delegation contracts.
3. Primary Kite assesses the question and proposes a complete pair. A dependency-free resolver
   validates constraints before returning an exact-role spawn request. Primary Kite executes that
   request through the supported platform tool; the resolver does not call models or spawn agents.
4. Initially retain `gpt-5.6-sol` and the existing `medium`, `high`, and `xhigh` defaults as
   preferences. Permit task-specific effort selection within those settings when requirements are
   satisfied. Implement model-independent resolution and synthetic multi-model fixtures; admit
   additional real models through reviewed eligibility evidence rather than availability alone.
5. Default to one attempt per consultation, zero automatic retries, and zero escalation. Support
   explicitly authorized bounded alternatives without introducing paid evaluations, new quotas,
   persistence, plugin installation, or background work in the implementation batch.
6. Use `fork_turns="none"` with a complete bounded evidence handoff for explicit choices. Allow a
   positive turn count only when the host supports overrides in that mode. Reject full-history
   forks for this host's explicit-choice path.

This separates allocation ownership without coupling it to a model migration. The tradeoff is
that cross-model quality and savings remain unmeasured, and fresh-context handoffs must preserve
all material evidence. Broader initial model eligibility, larger attempt budgets, or required
full-history continuity need a different approved policy.

## Reconciled Baseline

The clean starting checkout and fetched `origin/master` both resolved to
`06f03c31171d54106c9a965fe5d814ab454fd67c`. Issue #39 inspected the earlier `295cdb7` checkpoint.
The intervening documentation consolidation relocated the council guide from `docs/architecture/`
to `docs/development/`.

| Surface | Verified observation | Implication |
|---|---|---|
| `.codex/agents/*.toml` | 20 roles set both execution fields; all use `gpt-5.6-sol` | Policy-only changes cannot enable dynamic allocation. |
| Council policy | Schema 2, policy `2026-08-29-v3`; 8 `xhigh`, 8 `high`, 4 `medium` assignments | Preserve these as default-profile references during migration. |
| Validator | One allowed model, three efforts, profile/policy equality | Replace fixed equality with allocation validation while preserving routing and safety checks. |
| Offline baseline | 20 advisors, 27 routing cases, 9 activation cases pass; all 20 unit tests pass | Structural evidence only. |
| Source/cache | Both identify `0.1.0+codex.20260829091645`; each has 111 files excluding Python bytecode; 14 differ | Version equality does not prove installed identity. |
| Cache differences | 3 specialist `SKILL.md` files and 11 specialist references differ; policy and manifest match | The guide's historical byte-equality observation is not current acceptance. |
| Local executable | `codex --version` reports `codex-cli 0.150.1` | Identifies the CLI, not the desktop host build or minimum supported version. |
| Current task schema | Exact roles expose fixed non-overridable settings; general spawn fields expose model, effort, and fork mode | This already-loaded task cannot prove the proposed dynamic configuration. |

No Kite activation, advisor consultation, model evaluation, plugin refresh, or connected runtime
occurred during this investigation. The installed cache was inspected without modification.

## Platform Feasibility

The current [official Codex subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents#custom-agents)
states that custom-role model/effort settings override explicit spawn settings. Without those
role overrides, explicit spawn settings take precedence over agent defaults and parent settings.
Required role fields are name, description, and developer instructions. This documents a path to
retain role identity while moving resource choices to the caller.

The current task tool contract separately rejects explicit overrides for full-history forks and
requires user or applicable instruction authority for model/effort overrides. The revised
explicit-only router must supply the allocation instruction. Documentation supports the design;
source edits do not establish that a fresh host loaded or applied it.

Capture a fresh host snapshot of exact-role availability and overrides, supported model/effort
pairs, permitted context modes, and effective-setting observability. The snapshot is evidence,
not model authorization. Missing/stale evidence, locked roles, and unsupported context modes stop
dispatch. Do not switch to generic agents, change global defaults, or infer desktop compatibility
from the local CLI version. No minimum supported host version is established yet.

The current spawn interface guarantees no effective-model receipt. Record effective settings as
unknown unless host execution metadata exposes them. A child repeating the requested model, a
successful call, matching files, or a tool description does not prove effective execution. A known
mismatch fails allocation acceptance and blocks admission of the affected consultation.

## Proposed Versioned Contract And Ownership

Use council schema 3 and a new policy revision for implementation. Resolver input and result
contracts each carry `schema_version = 1`. These are plugin contracts, not Codex configuration
keys. Reject unknown fields, duplicate identities, invalid types, unsupported versions, empty
required sets, dangling references, and incomplete execution pairs.

| Contract | Canonical owner | Fields and meaning |
|---|---|---|
| Advisor intent | Existing advisor entry in council policy | `intent_version`, `required_capabilities`, `default_profile`, `constraint_profile`, `retry_profile`; reuse existing role identity. |
| Resource profiles | Central `allocation.profiles` in council policy | Stable profile ID and complete `model` / `reasoning_effort` mapping. |
| Eligibility catalog | Central `allocation.models` in council policy | Exact model ID, allowed efforts, capability evidence references/dispositions, known context capacity, compatibility limits. |
| Constraint profiles | Central `allocation.constraints` in council policy | Allowed profiles/pairs, context modes, and justified mandatory restrictions distinct from preferences. |
| Retry profiles | Central `allocation.retries` in council policy | `max_attempts`, `max_fallbacks`, `max_escalations`, ordered authorized alternatives, allowed failure reasons. |
| Task assessment | Primary Kite's consultation record | Stable consultation ID, exact role/question, evidence references, complexity, ambiguity, consequence, capabilities/context needed, authorized limits, proposed pair, brief rationale. |
| Host snapshot | Current platform evidence | Observation identity/time, exact-role availability/overrides, supported pairs, context modes, effective-setting observability, evidence references. |
| Resolution result | Resolver | Policy/intent/host identities, constraints, selection source, complete requested pair, exact role/context mode, disposition/reason, attempt history. |
| Execution receipt | Host metadata attached by primary Kite | Resolution identity, child ID, observable effective settings or explicit unknowns, outcome, measured usage/latency when available, provenance. |

Capabilities describe requirements such as source/code inspection, tool use, structured evidence
reporting, and image input. Image input is conditional on the question; context capacity is an
explicit quantity when known. Task requirements can strengthen advisor requirements but cannot
weaken them. A family name or universal intelligence score is not capability evidence.

Eligibility intersects reviewed policy admission with current host support. Technical support,
prior use, and quality evaluation remain distinct evidence dispositions. Existing sol assignments
provide continuity, not new quality proof for every question or lower effort. Missing material
eligibility evidence blocks the choice. Hard context or monetary limits also block dispatch when
the host cannot establish or enforce them. Unknown usage is never zero; ordinary consultation
authorization does not authorize a paid comparative evaluation.

## Resolution And Precedence

1. Confirm explicit Kite activation, exact selected role, ready dependencies, and source gates.
   Allocation does not add advisors or change the selected-role dependency graph.
2. Validate inputs and intersect platform restrictions, user constraints, advisor/task hard
   requirements, and policy bounds. An incompatible combination stops resolution.
3. Honor explicit user fields. A supplied model constrains model choice; a supplied effort
   constrains effort choice. Resolve any missing half through a compatible proposed/default
   profile. If none exists, report a conflict; never silently replace an explicit choice.
4. Otherwise validate primary Kite's proposed pair. With no proposal, use the advisor's default
   profile. An invalid proposal is a conflict, not permission to silently use the default.
5. Return both execution fields, exact custom role, and supported context mode. Omitted request
   fields may be filled during resolution; omitted dispatch fields are rejected.
6. Primary Kite records the concise decision, dispatches the validated request, and attaches any
   receipt. Unknown effective settings remain unverified; observed mismatch fails acceptance.

Task assessment and preferred-pair selection are discretionary judgments. Schema checks,
constraint intersections, default resolution, authorized alternative order, and attempt counters
are deterministic. Do not claim a keyword classifier establishes task complexity or quality.

Reject a role execution override even when it matches the proposed pair: it would restore final
authority to the role. Do not omit execution settings or use inherited full history to evade a
conflict. For a fresh-context handoff, supply authority paths, exact scope, source references,
upstream dispositions, expected output, stop gates, and the allocation identity. Missing material
context blocks the consultation.

## Attempts, Fallback, And Decision Evidence

The proposed initial retry profile is `max_attempts = 1`, `max_fallbacks = 0`,
`max_escalations = 0`. Attempt 1 counts toward the total. Later authorized profiles use finite
integer bounds, at least one total attempt, nonnegative fallback/escalation counts, and an
ordered non-cyclic list of complete alternatives. Both fallback and escalation consume the same
aggregate attempt/resource budget. Effort labels have no universal ordering across models.

Preserve consultation identity and prior outcomes across retries. A newly assessed question
links its predecessor explicitly; inventing a new ID cannot reset a failed consultation's budget.
Validate every alternative against unchanged hard requirements and remaining resources.

Unavailable models or transient execution failure may permit an authorized alternative. Missing
sources, failed coverage, authority conflicts, and incomplete handoffs do not. Explicit user
choices prohibit substitution unless the user also authorized alternatives. Reconcile an ambiguous
launch outcome before retrying to avoid duplicate agents. Advisors may report insufficient
resources but never respawn, delegate, or raise their own budget.

Use compact typed entries in the existing task/consultation record: constraints, rationale,
requested/effective settings, selection source, prior outcomes, and measured usage/latency where
available. Store no raw private prompts, credentials, chain-of-thought, or new database state.
Exhaustion stops affected conclusions under existing council failure rules; independent work can
continue only when the gap cannot change it.

## Implementation, Installation, And Rollback

After the design decision, implement one coherent branch/PR covering:

- the dependency-free resolver under `plugins/kite/scripts/` and deterministic fixtures/tests;
- centralized allocation policy and all 20 advisor intent/default migrations;
- removal of both execution overrides from all 20 custom roles, preserving all other fields;
- strict allocation validation in place of fixed model equality, preserving the existing role,
  activation, dependency, source, safety, and failure checks;
- router instructions requiring resolution before dispatch, complete context handoff, and receipt
  handling; council routing contracts, advisor design guidance, and acceptance guidance;
- current council documentation and one coordinated schema/policy/package version update through
  the existing plugin packaging workflow.

The router must invoke the resolver; a test-only helper is insufficient. The resolver validates a
request for primary Kite, not a host-enforced interception layer. Static checks cannot prevent a
spawning agent from bypassing it. Fresh-task evidence must exercise the actual
router-to-resolver-to-exact-role path before claiming execution acceptance.

After implementation review/merge, separately authorize a complete package refresh, reconcile
project role files, compare source/cache relative paths and hashes, and start a fresh task.
Inspect the newly exposed role definitions before dispatch. Cache refresh does not prove that an
already-running task reloaded its roles. Preserve the observed cache drift in the acceptance
record; do not treat matching version strings as sufficient.

Rollback restores the complete reviewed fixed-allocation configuration through the normal PR
workflow: role overrides, policy, validator, router, fixtures, and manifest must agree. A separately
authorized cache refresh and fresh task then verify it. Keep failed acceptance evidence; do not
mix legacy role pins with a dynamic router or reset/delete unrelated work or user configuration.

## Verification And Acceptance Plan

| Fixture or check | Required result |
|---|---|
| Simple and ambiguous questions for one unchanged advisor | Two complete eligible allocations, with task judgments supplied explicitly. |
| Default and omitted request fields | Stable default; both execution fields explicit, no accidental inheritance. |
| Explicit complete and partial user choice | Honor supplied fields; compatible completion or a named conflict. |
| Missing capability / unknown context capacity under a hard limit | Stop with the missing evidence, no unsupported assurance. |
| Unavailable model / unsupported effort / unknown field or version | Reject before dispatch, no silent substitution. |
| Fixed host override / inherited-setting conflict / full-history fork | Reject; do not switch roles or omit execution settings. |
| Budget exhaustion / fallback / escalation limits | Preserve history and enforce aggregate bounds and permitted alternatives. |
| Missing source / failed coverage / ambiguous launch | Stop or reconcile; higher effort does not repair evidence or duplicate launches. |
| Requested/effective mismatch / unavailable metadata | Mismatch fails acceptance; missing metadata remains explicitly unverified. |
| Synthetic second model with different supported efforts | Model-independent resolution without advisor-definition edits. |
| Council regressions | All 20 roles, explicit activation, read-only/non-delegating contracts, dependency order, and source/stop gates survive. |

Run `python3 -B plugins/kite/scripts/validate_advisor_council.py`,
`python3 -B -m unittest discover -s plugins/kite/tests`, applicable offline lint/repository checks,
and `git diff --check`. The matrix above defines new implementation tests; it does not claim those
tests exist. The existing baseline passes its 20 tests.

Fresh-task acceptance records the actual host build, source revision, installed identity, exact
role, context mode, assessment, resolver result, requested pair, actual call, and any effective
receipt. Exercise two allocations for the same role with unchanged instructions. If the host
cannot express the request or expose effective settings, record the precise platform limitation
and leave that acceptance blocked/unverified. Static or cache equality never suffices.

Evaluate quality, latency, or savings only with separate authorization. Define representative
evidence sets, required findings, unacceptable omissions, repeat counts, and comparison thresholds
against the fixed-allocation baseline before running models. Higher effort alone proves neither
quality parity nor savings.

Issue #39 remains open through this design PR. Implementation, policy approval, installation,
fresh-task execution evidence, and separately requested comparative evaluation retain their own
acceptance status.
