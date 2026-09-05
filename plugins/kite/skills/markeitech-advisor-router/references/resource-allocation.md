# Advisor Resource Allocation

Primary Kite owns each selected advisor's model and effort choice. The canonical mappings,
eligibility evidence, constraints, and retry bounds are in `council-policy.toml`; the advisor entry
owns required capabilities and profile references. Custom-role files carry no execution override.
Selection of advisors and dependency ordering remain governed by the existing routing contract.

## Before Every Spawn

1. Assess the exact question's complexity, ambiguity, evidence volume, and consequence. These
   `low`/`medium`/`high` values and the preferred allocation are judgments, not automatic scoring.
   Preserve user choices and required capabilities, including image input or context capacity
   where material. Do not lower evidence standards to fit a resource choice.
2. Capture the current task's exact-role and tool schema as a host snapshot. Record its identity
   and evidence reference. Refresh it for each dispatch; never reuse example data as host evidence.
   Include only capabilities actually established by current host evidence, and leave unknown
   context capacity `null`. Record every fixed role override. A matching fixed override is still
   incompatible with spawning-layer ownership.
3. Build a sanitized JSON request using [the example shape](allocation-request.example.json).
   Supply explicit activation/source/dependency dispositions from the existing route record.
   These booleans are evidence assertions, not substitutes for doing those checks. Retain that
   record as provenance for the snapshot, assessment, constraints, and authorized limits.
4. Run from the reviewed checkout with its matching installed package:

   ```bash
   python3 -B plugins/kite/scripts/resolve_advisor_allocation.py resolve --request -
   ```

   Pass the request JSON through the tool's process-input stream or a pipe; do not create a file
   during read-only work. For shell tools, a properly quoted `python3 -c` producer can write the
   control JSON to stdout and pipe it to this command. Avoid heredocs on shells that materialize
   temporary files. Retain decisions/receipts in the conversation/tool record; durable file output
   requires separately authorized write access. File-path inputs remain supported for callers
   that already have authorized records.

   When the root checkout is unavailable, invoke the same script from the matching installed
   plugin and use its adjacent policy. Never execute a mismatched script/policy package.
5. On success, save the returned decision in the existing consultation record. Call the exact
   `decision.role` with `model=decision.requested.model`,
   `reasoning_effort=decision.requested.reasoning_effort`, and
   `fork_turns=decision.fork_turns`. Supply a bounded handoff with authority paths, question,
   source references, upstream dispositions, output requirements, stop gates, and decision ID.
   All three execution/context fields are explicit; no implicit inheritance or generic-role
   substitution is allowed. Full-history forks cannot carry overrides on this host.
6. Capture the child execution ID, outcome, and host-reported effective pair when observable.
   Otherwise use `effective: null`. Validate the receipt using:

   ```bash
   python3 -B plugins/kite/scripts/resolve_advisor_allocation.py receipt --record -
   ```

   With `--record -`, stdin is one JSON object with exactly `decision` (the returned decision)
   and `receipt` (the host-evidence receipt). Both are validated in memory; stdout carries the
   result. File callers may still use `--decision PATH --receipt PATH`. Never read stdin twice.

   A receipt contains exactly `decision_id`, `execution_id`, `effective`, `outcome`, and `evidence`.
   Its outcome is `completed`, `model_unavailable`, `execution_failure`, `insufficient_resources`,
   or `unknown`. A child asserting its own model is not effective-setting evidence. A mismatch
   stops the affected conclusion. Missing metadata leaves execution allocation unverified; it
   does not independently waive evidence or consultation acceptance gates.

The helper validates requests and receipts; it never spawns, invokes models, accesses credentials,
reads raw prompts, or enforces host permissions. Its snapshots/receipts are supplied evidence, not
authenticated attestations. The router must actually call it; source tests cannot prove compliance.

## Contract And Precedence

Council schema 3 contains allocation schema 1. Advisor `intent_version` and request/result
`schema_version` are 1. Unknown fields/versions and invalid types are rejected. Control-record
strings are bounded to 4,096 characters; arrays/registries to 128 entries; integers to signed
32-bit nonnegative values (positive where required); CLI JSON input to 1 MiB. These are serialization
bounds, not model token or spending budgets. JSON duplicate keys are rejected.

Policy `allocation.models` is the reviewed admission catalog, not a copy of every available model.
Each entry supplies allowed efforts, capability IDs, and eligibility evidence. Profile mappings
are complete model/effort pairs; constraints reference allowed profiles and `none`/`bounded` fork
modes. Advisor requirements are joined with task requirements; the default profile must satisfy
advisor requirements. Existing model use is continuity evidence, not comparative quality proof.
New models and new mandatory capabilities need policy admission evidence; higher effort proves
neither correctness nor equivalent cost. Read concrete mappings from policy, not this document.

Platform restrictions, user constraints, advisor/task requirements, and policy bounds intersect.
An explicit user choice takes precedence over the proposed/default choice when compatible. Partial
choices constrain their supplied fields; resolution fills the missing field using the compatible
proposal or default/ordered allowed profiles. With no user choice, validate the spawning agent's
proposal, or use the advisor default if no proposal exists. Invalid explicit choices/proposals
stop rather than silently changing them. A discretionary proposal that conflicts with an explicit
user field is superseded by the user choice, which must still satisfy all hard constraints.

The host snapshot contains `snapshot_id`, `evidence`, exact `role`, `role_overrides`, `models`,
and `fork_modes`. Each host model supplies `efforts`, `capabilities`, and `context_tokens` (positive
integer or `null`). `required_context_tokens: 0` means no quantified requirement has been asserted;
it is not unlimited capacity. A positive requirement needs known adequate host capacity. Do not
invent a capacity to pass validation. Unsupported hard `max_cost_usd` or `max_tokens` limits stop
with `HARD_BUDGET_UNSUPPORTED`; this host adapter cannot enforce those budgets.

Requests contain a stable consultation ID, exact role/question, assessment/rationale, capability
and context requirements, activation/source/dependency dispositions, host snapshot, history, and
`limits.max_attempts`. Optional fields are `user_choice`, complete `proposed_choice`, `fork_turns`,
`retry_kind`, and policy profile IDs in `user_alternatives`. The example is synthetic and must not
be dispatched as an actual consultation.

## Attempts And Stop Behavior

Policy controls maximum attempts, fallbacks, escalations, and ordered alternative profiles. The
request may reduce the attempt cap, never increase it. The initial policy permits no retry.
For an explicitly authorized retry policy, preserve the original consultation ID, constraints,
and prior decision/receipt entries in `history`; both fallback and escalation consume the same
aggregate attempt budget. Full or partial user choices prohibit substitution unless the user also
authorized named alternative profiles. A fallback can follow model unavailability or execution
failure; escalation can follow reported insufficient resources. Missing sources or coverage cannot
be repaired through resource escalation.

Each historical decision is bound to the policy, consultation, question, requirements, user choices,
and limits. The digest detects inconsistent records; it is not a signature or durable uniqueness
service. Do not discard history or invent IDs to reset budgets. Reconcile unknown launch outcomes
before retrying; completed work is not retried. Advisors never delegate or adjust their own budgets.
Keep measured latency/usage in the existing record with provenance; unknowns remain unknown.

The CLI returns exit 0 with a validated decision or receipt disposition, or exit 1 with a `BLOCKED`
reason. A failed receipt outcome may be structurally valid: read its `status`, not only the exit
code. `REQUEST_VALIDATED_EXECUTION_UNVERIFIED` and `EXECUTION_UNVERIFIED` are not effective-execution
passes. `EXECUTION_VERIFIED` requires a matching effective pair and a completed outcome.

## Installation And Acceptance

No installation is performed by the resolver. Follow the repository's
`docs/operations/kite.md` runbook for exact install, versioning, verification, purge, and rollback
commands. Refresh the complete reviewed package and reconcile project role files before using it.
Compare relative paths/hashes and start a fresh task; already-running tasks retain old role
definitions. Source/cache identity does not prove host execution.

Fresh-task acceptance must exercise the router, resolver, and exact-role tool calls for two
different allocations of one unchanged role. Record actual host version, source/package identities,
requested/effective settings, context handoff, user override and failure behavior. If effective
settings are unavailable, record that limitation explicitly. No quality or cost improvement is
claimed; comparative model runs require separate authorization and predeclared thresholds.

Rollback restores a coherent reviewed role/policy/router/validator/fixture/package set through a
PR, then an authorized package refresh and fresh task. Never mix restored fixed roles with the new
router or change unrelated user configuration.
