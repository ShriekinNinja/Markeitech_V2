# Kite Allocation Acceptance

**Disposition: source checks and two effective effort allocations passed; complete fresh-task
acceptance remains blocked by an installed-package stability failure. Issue #39 remains open.**

This is the 2026-09-05 response to PR #40's requested changes. The
[operations runbook](../operations/kite.md) owns installation, update, verification, purge, and
recovery procedures. The [sanitized JSON evidence](kite-allocation-acceptance.json) preserves both
requests, decisions, host metadata references, and validated effective-setting receipts. It contains
no raw session transcript, credentials, provider data, or runtime logs.

## Source And Initial Installation

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

## Fresh Router, Resolver, And Exact-Role Execution

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

## Installed-Package Failure And Bounded Recovery

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

## Model Admission And Scope Limits

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

## Verification And Remaining Gates

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
recorded for the same unchanged advisor. Complete issue acceptance remains withheld for package
stability and live cross-model evidence. PR #40 stays unmerged for Markeitect's current-head review;
issue #39 remains open. No model quality, latency, cost improvement, full isolation, or approval is
inferred from this record.
