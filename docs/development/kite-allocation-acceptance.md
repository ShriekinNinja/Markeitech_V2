# Kite Allocation Acceptance

**Disposition: the final-fix allocation acceptance passes for package
`0.1.0+codex.20260905204949`: stable package observations, exact-role execution, and task-driven
Sol/Astra allocation are verified. PR approval and merge remain Markeitect's gates.**

The [operations runbook](../operations/kite.md) owns lifecycle procedures. The
[final sanitized evidence](kite-allocation-final-acceptance.json) records the current CLI and
desktop runs, requests, decisions, host metadata, receipts, and package observations. The
[initial evidence](kite-allocation-acceptance.json) and historical account below preserve the
previous failed stability check; they are not the current acceptance disposition.

## Final-Fix Reruns — 2026-09-05 UTC

The [final-fix comment](https://github.com/ShriekinNinja/Markeitech_V2/pull/40#issuecomment-5554684032)
requested precise Astra admission evidence, fresh package stability, and actual cross-model routing.
Commit `6ad23c70b4d7717bb5ad60dfa15d079a68324bb6` corrects the policy evidence and versions policy v6
with package `0.1.0+codex.20260905204949`. That corrected bundle necessarily supersedes the
comment's `...203558` package. It was installed before testing and remained frozen through both
runs; subsequent acceptance-record edits are outside the bundle.

At the admission checkpoint, Astra had policy-level eligibility and offline eligible/unavailable-host
validation, while live execution was unverified. The policy evidence records that checkpoint; it
is not a dynamic execution-status field. The subsequent desktop execution below supplies new
host-specific evidence in this external ledger. Neither admission nor a model catalog establishes
availability on another host.

The exact role remained `markeitech_architecture_boundaries_advisor`, with no model/effort override.
All runs began and ended at source `6ad23c70b4d7717bb5ad60dfa15d079a68324bb6` with a clean worktree
and role SHA-256 `e0b96b4154727c88e4ebf998188040c410b564bac610f37c2e2a03b03b10cd07`.

| Run | Start/end package verification | Additional observations |
| --- | --- | --- |
| Fresh read-only CLI session `01a07356-8e5a-7d90-9ca9-daef75c10093` | Both `BYTE_IDENTICAL` | 157 periodic samples, zero mismatches, 20:50:46–20:56:01 UTC |
| New same-directory desktop task `01a0735a-d771-7561-bf9b-623dbfe29e6e` | Both `BYTE_IDENTICAL` | 108 periodic samples covering both child executions, zero mismatches, 20:56:29–21:00:06 UTC |

Every sample and task check observed the same 116-file inventory SHA-256:
`3299ab7503e25fd950afa825d7048164d1fb464fd681af3d9ecb4e1ba328bed7`. Sampling targeted two-second
intervals; maximum observed intervals were 2.084 seconds for CLI and 2.151 seconds for desktop.
No missing directory, changed bytes, or reversion was observed. These are bounded sampled and
start/end observations, not a continuous attestation or a guarantee about future host behavior.
The earlier cache replacement's cause remains unknown, but its failed observation was not repeated
in either final-package run.

The CLI schema exposed Sol, Terra, Luna, GPT-5.5, and GPT-5.4-mini, but not Astra. It correctly ran
only the small lookup through the router, stdin resolver, and exact role, using Sol medium. Host
metadata confirmed completion and the effective pair. One diagnostic label initially contaminated
the JSON pipe; the resolver rejected it before dispatch. Moving that label to stderr produced the
validated initial allocation, with one child and no model retry.

The separate desktop task loaded the current role catalog and exposed both admitted models. It
was a same-directory fork with completed history, not a claim of an empty parent conversation.
Its current schema and source were checked afresh; both child consultations used `fork_turns=none`
and bounded handoffs, so neither child inherited that parent conversation.

| Desktop question | Assessment | Requested and host-effective allocation | Outcome |
| --- | --- | --- | --- |
| One-file mapping-owner lookup and role override check | low complexity, ambiguity, evidence volume, and consequence | `gpt-5.6-sol` / `medium` | Completed; `EXECUTION_VERIFIED` |
| Seven-layer ownership reconciliation with stale-role, cache-byte, and unavailable-user-choice conflicts | high complexity, ambiguity, evidence volume, and consequence | `gpt-6-astra` / `high` | Completed; `EXECUTION_VERIFIED` |

Both independently routed `SINGLE` to the same unchanged architecture advisor. The choices were
recorded task judgments within policy, not deterministic classification or forced test outcomes.
Each request passed the real stdin resolver before the exact-role spawn. The desktop task used
exactly two child calls, with no retry or child delegation.

Desktop decision IDs are `123014fed1624a6795f36c5eca6f141feaef9634e4cc5e19818748bc5fcc87b3` (A)
and `07c166cad9b5de0b9cdec059e74a41eff8cd9b1b3cfcf90bdb85b69dbcf8aa7e` (B). Host sessions
`01a0735b-dfbf-7142-824c-d9acf419d8bf` and `01a0735b-f524-71b3-b528-34bc17f80f5c` bind each child to
its exact role and parent at `session_meta` line 1. `turn_context` line 8 records the effective pair;
`task_complete` is at lines 94 and 64 respectively. Operator receipt validation independently
returned `EXECUTION_VERIFIED` for both. No child self-report is used as effective-setting proof.

## Current Limits And Review Gate

**Effective read-only isolation is not accepted.** The CLI parent/child had read-only sandbox
metadata. Desktop children instead inherited `workspace-write` with network disabled, despite
their read-only role defaults. They were instructed to perform read-only work and made no file
changes, but that behavior does not prove host-enforced write denial. This is the already separate
council tool-isolation limitation; it does not change the observed model/effort allocation result.

No general council-routing matrix, revocation, prompt-injection resistance, comparative model
quality, latency, cost saving, or connected runtime/provider acceptance is claimed. The 54 focused
tests, council validator (20 advisors, 27 routing cases, 9 activation cases), and proportional
repository CI are separate evidence. Decisions/receipts in the final JSON replay against the
recorded v6 source policy; earlier JSON retains its original policy/package bindings.

The three final-fix requests are now addressed for their bounded scope. Issue #39 remains open
pending PR #40 review and merge; no agent approval or merge is performed. The tested package is
left installed. No additional package bump or reinstall is needed merely to record these results.

## Earlier Acceptance History

The following preserves the initial checkpoints and their then-outstanding gates. Current status
is given above; the failed initial run has not been rewritten into a pass.

### Source And Initial Installation

- Tested source: `20057578bb48d369dab0ce2ca6ff3b59884d5e14` on
  `kite-advisor-allocation-design`; the worktree was clean during the fresh task.
- Package: `0.1.0+codex.20260905202217`, 116 files.
- Complete source/cache inventory SHA-256:
  `c3e08039044956ac8ae1404bf4fdb366d8c80e74dbcb994628770289a1fc32dd`.
- CLI: `codex-cli 0.150.1`. Fresh task:
  `01a0733d-af93-7971-a676-eb7a66dfae45`.
- Exact role: `markeitech_architecture_boundaries_advisor`.
- Role SHA-256 before and after:
  `e0b96b4154727c88e4ebf998188040c410b564bac610f37c2e2a03b03b10cd07`.

The starting local marketplace registration pointed at
`/Users/markeitect/PycharmProjects/Markeitech`, whose clean `master` checkout retained older source.
The supported CLI rejected replacing an existing marketplace with a different source. The operator
therefore removed only the `markeitech` registration, added
`/Users/markeitect/.codex/worktrees/b5ec/Markeitech`, and installed `kite@markeitech`. No marketplace or
cache file was edited by hand. CLI readback showed the candidate enabled, and the tracked package
verifier returned `BYTE_IDENTICAL` before the fresh task and again inside it before dispatch.
The main checkout and unrelated plugins were preserved.

### Fresh Router, Resolver, And Exact-Role Execution

The acceptance explicitly invoked `$kite:markeitech-advisor-router` in a new read-only CLI session.
The two questions were independent. Each honestly selected `SINGLE` with the architecture advisor,
no dependency edges, and no adjacent domain consultation. Neither allocation was forced merely to
produce a difference.

| Question | Assessment: complexity / ambiguity / evidence / consequence | Requested and host-effective allocation | Outcome |
| --- | --- | --- | --- |
| A: locate the one current owner of concrete model/effort mappings and check the role for overrides | low / low / low / low | `gpt-5.6-sol` / `medium`; `fork_turns=none` | Completed; receipt `EXECUTION_VERIFIED` |
| B: reconcile seven ownership/lifecycle layers and three hypothetical conflicts involving stale roles, differing cache bytes, and unavailable user-selected models | high / high / high / high | `gpt-5.6-sol` / `xhigh`; `fork_turns=none` | Completed; receipt `EXECUTION_VERIFIED` |

The router ran `resolve --request -` before each dispatch and supplied every validated execution
field to `collaboration.spawn_agent` with the exact custom role. The complete bounded handoff
contained the question, current authority/source paths, decision ID, upstream dispositions, and
read-only/no-delegation/no-retry constraints. Requests and decisions used stdin/stdout pipelines,
with no temporary control-record file. Exactly two child consultations ran.

| Record | A | B |
| --- | --- | --- |
| Decision ID | `e31340a1f4bf84b8a8c65fc6976b77c9ac15595488d5447af62d3f59a4b3597f` | `fb294e548e3f52b6bf77e0857ad4895fd56ae3cddf52b08b6179efe3fda4ece3` |
| Child ID | `01a0733f-fb9e-7b22-a7a9-0a3b1e55c9b5` | `01a07340-292a-79b1-9ea5-edc49c288ce5` |
| Child path | `/root/allocation_a` | `/root/allocation_b` |

The fresh parent initially received canonical child paths and completion without effective-setting
metadata. It correctly validated both receipts as `EXECUTION_UNVERIFIED` with `effective: null`.
After the run, the operator inspected only the identified local host session records:
`session_meta` line 1 establishes the exact role and parent; `turn_context` line 8 records the
model, effort, and read-only sandbox; `task_complete` establishes completion. These host facts,
not child self-reports, supplied the effective pairs and opaque child IDs in the JSON record.
Revalidating each combined receipt through stdin returned `EXECUTION_VERIFIED`. This upgrades only
the effective-allocation evidence; it does not erase the separate package failure below.

### Installed-Package Failure And Bounded Recovery

At the fresh task's final check, the previously verified installed directory
`~/.codex/plugins/cache/markeitech/kite/0.1.0+codex.20260905202217` no longer existed. The same verifier
returned `PACKAGE_DIRECTORY_REQUIRED`. Filesystem inspection and subsequent operator CLI readback
showed `0.1.0+codex.20260829091645` installed and enabled instead, although the marketplace still
pointed to the PR checkout. Source HEAD, worktree, package bytes, and advisor file hash were
unchanged. The cause and precise transition time are **unknown**; no continuous installed-package
identity or complete loaded-bundle provenance is inferred from the initial check.

After the read-only task ended, the operator performed one authorized repair reinstall using
`codex plugin remove kite@markeitech --json`, then `codex plugin add kite@markeitech --json` from the
still-correct marketplace. Immediate verification again returned the candidate's 116-file
`BYTE_IDENTICAL` result, and CLI listing showed it enabled. The repair is a separate dated
observation. It does not establish stability through a fresh task or retroactively pass the failed
run. The remaining operational gate is to identify/reconcile the host's replacement behavior and
retain the same package through fresh-task acceptance. No repeated reinstall loop or extra model
calls were used to hide the failure.

### Final Documentation-Only Package Follow-Up

A final consistency check found that the bundled `routing-acceptance.md` still described the
initial uninstalled checkpoint in present tense. Revision
`0f92a93eb6dbaee29a23445e01448bae18dbc0ab` makes that checkpoint explicitly historical and points to
this external record. It changes that reference and the coordinated manifest/policy package
identifiers only. Resolver bytes and advisor definitions are unchanged from the tested revision.

The resulting `0.1.0+codex.20260905203558` package was installed through `plugin add`; its 116-file
source/cache SHA-256 is `6bcb6f46a1e2c7add29da004035ad8f7ecf22ca38d1b3be89872870439cc4995`, verified
`BYTE_IDENTICAL`. No additional model calls were made. The earlier run remains evidence for the
unchanged allocation behavior, with its original policy/package binding preserved in JSON. This
later documentation package has no separate fresh-task stability pass, and does not close either
remaining acceptance gate. Replay the recorded decisions against their recorded source revision's
policy, not a different package-version binding.

### Model Admission And Scope Limits

Central policy admits two real models: Sol at medium/high/xhigh and Astra at high. Sol preserves
prior exact-role use. Astra admission uses the desktop host's supported spawn metadata and
[primary model documentation](https://developers.openai.com/api/docs/models/gpt-6-astra). This is
technical eligibility evidence, not measured quality equivalence or current availability everywhere.
The offline test resolves the real Astra pair with a compatible host snapshot and rejects it when
host support is missing, without changing the advisor definition.

This fresh CLI task's actual spawn schema did not list Astra. The router therefore omitted it from
both host snapshots. **No live Astra execution or task-driven switch between different models is
claimed.** What was observed is two task-driven effort allocations on Sol. Cross-model execution
acceptance requires a fresh host that actually exposes both admitted models; a cached model catalog
or another host's schema is insufficient.

All three task contexts reported a read-only sandbox. No repository edits, model retries, child
delegation, service connections, authenticated sessions, broker/database operations, or deliberate
write probes occurred within the fresh task. `codex --version` emitted a warning that its incidental
PATH-alias creation attempt was denied; no successful write from that attempt was observed. Its
relationship to the cache replacement is unknown. Configuration and cooperative behavior do not
establish complete tool isolation, network denial, or revocation. No such pass is claimed.

### Verification And Remaining Gates

- 54 focused tests passed, covering allocation precedence/constraints/retries/receipts, real and
  synthetic model admission, bounded stdin transport, and package version/identity failure cases.
- Council validator passed: 20 advisors, 27 routing cases, 9 activation cases.
- Ruff, generic plugin/skill validation, local documentation links, and `git diff --check` passed.
- All 20 role files were compared as parsed TOML against `master`: only `model` and
  `model_reasoning_effort` were removed; all other fields were preserved.
- Runtime/provider/database acceptance was not relevant to this development-tool batch and was
  not run locally. Required repository CI remains a separate PR-head check.

The source runbook, tracked package procedure, separate purge semantics, second-model admission,
and read-only transport requests are implemented. Two distinct effective effort allocations are
recorded for the same unchanged advisor. At this earlier checkpoint, complete issue acceptance was withheld for package stability and
live cross-model evidence. The final-fix reruns above supersede those two outstanding gates;
PR review and merge remain separate. No model quality, latency, cost improvement, full isolation, or approval is
inferred from this record.
