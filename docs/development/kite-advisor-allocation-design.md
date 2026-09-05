# Kite Per-Consultation Resource Allocation

**Status:** Source and offline checks pass; two task-driven effective effort allocations are
verified. Complete acceptance remains blocked by installed-package stability and live cross-model
evidence; see the [acceptance record](kite-allocation-acceptance.md).

**Tracking:** [Issue #39](https://github.com/ShriekinNinja/Markeitech_V2/issues/39)

**Evidence date:** 2026-09-05

Primary Kite now owns each selected advisor consultation's model and reasoning effort. All 20
custom-role files omit both execution overrides while retaining their names, instructions,
read-only defaults, and MCP restrictions. This change concerns development-time consultation;
it does not implement Sir Loke or change runtime/provider behavior.

## Ownership And Implementation

The canonical [allocation contract](../../plugins/kite/skills/markeitech-advisor-router/references/resource-allocation.md)
owns the request/receipt schema, commands, precedence, bounds, failure handling, and host handoff.
The [council policy](../../plugins/kite/skills/markeitech-advisor-router/references/council-policy.toml)
owns concrete model mappings, capability evidence, constraints, defaults, and retry settings.
The [resolver](../../plugins/kite/scripts/resolve_advisor_allocation.py) checks them before the
router dispatches an explicit pair through the exact custom-role tool. These are the single
maintained owners; this page records implementation scope and acceptance limits.

- Council schema 3 contains allocation schema 1 and versioned advisor intent. Advisor defaults
  are profile references, separate from mandatory capability/compatibility constraints.
- Existing Sol/effort assignments survive as preferences. The spawning agent may choose another
  eligible allocation for the actual question. The real-model catalog admits Sol and Astra high using current host support and primary model
  documentation. A synthetic fixture separately proves extensibility without advisor edits.
- Task assessment is recorded judgment. Default resolution, constraint validation, and bounded
  alternatives are deterministic. Complete model/effort pairs prevent accidental inheritance.
- Full or partial user choices are honored when compatible; invalid choices are not silently
  replaced. Missing capabilities, unknown required context capacity, locked host roles, and
  incompatible fork modes stop the affected consultation.
- The initial policy allows one attempt, no automatic retry, and no escalation. Future authorized
  profiles use shared attempt budgets, stable consultation identity/history, and explicit alternatives.
- Receipts distinguish requested/effective settings and verified, unverified, failed, or unknown
  outcomes. The helper is an offline validator, not a host execution or authentication boundary.

## Reconciled Baseline And Platform Evidence

The starting checkout and fetched master both resolved to
`06f03c31171d54106c9a965fe5d814ab454fd67c`. Issue #39 inspected `295cdb7`; the intervening
consolidation relocated the council guide to `docs/development/`.

Before migration, 20 roles pinned Sol with 8 xhigh, 8 high, and 4 medium assignments. The existing
validator passed 20 advisors, 27 routing cases, 9 activation cases, and 20 unit tests. The new
validator preserves the council checks while replacing fixed allocation equality with strict
intent/profile and allocation validation.

The inspected installed cache and old source both identified `0.1.0+codex.20260829091645` and
contained 111 files excluding bytecode, but 14 differed: 3 specialist skill files and 11 reference
files. Policy and manifest matched. This observation predates the new package; no reinstall or
cache mutation had occurred at that baseline checkpoint. The CLI reports `codex-cli 0.150.1`, which does not identify the desktop
host build or establish a minimum supported version.

[Official Codex subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents#custom-agents)
describes custom-role settings taking precedence over spawn settings; omitting both execution
fields permits explicit caller choices while retaining required role identity/instructions.
This task's host separately prohibits explicit overrides on full-history forks. The updated router
uses a complete bounded handoff with a supported explicit-choice context mode.

The original task retained its earlier role catalog after source edits. Acceptance therefore used
a fresh CLI session; its exact-role execution evidence and host/package limitations are recorded
separately in the acceptance record.

## Verification And Remaining Acceptance

The allocation tests exercise distinct choices for one unchanged role, deterministic defaults,
complete/partial user overrides, missing capabilities, model/effort availability, inheritance and
fork conflicts, context requirements, budget exhaustion, fallback/escalation limits, stable history,
ambiguous launch outcomes, and requested/effective mismatches. Synthetic model eligibility and
receipts are test inputs, not live host evidence or quality evaluation.

Run the council validator and complete plugin unittest discovery as described in the
[allocation contract](../../plugins/kite/skills/markeitech-advisor-router/references/resource-allocation.md).

The [operations runbook](../operations/kite.md) owns installation, updates, verification, purge,
project-role lifecycle, recovery, and rollback. The resolver accepts stdin and emits stdout, so
read-only consultations can retain control records in tool history without filesystem writes.

The current [acceptance record](kite-allocation-acceptance.md) owns observed installation and
fresh-task results. The required procedure is to refresh the complete reviewed package,
reconcile the project role files, compare source/cache hashes, and start a fresh task. Exercise the
actual router-to-resolver-to-exact-role path with two allocations for one unchanged advisor. Record
host version, source/package identity, context, requested pair, and effective settings when the host
exposes them. Unknown effective settings remain explicitly unverified. A successful spawn or a
child repeating its model name is not effective-setting proof.

Issue #39 remains open for that acceptance. No model-consuming benchmark, quality-parity result,
latency reduction, or cost saving is claimed. Comparative evaluations need separate authorization
and predefined thresholds. The allocation contract documents coherent rollback through the normal
PR, installation, and fresh-task workflow; unrelated user configuration remains untouched.
