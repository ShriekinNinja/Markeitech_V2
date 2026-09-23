# Contributing To Markeitech

Markeitech is proprietary. Contributions require prior approval from Markeitect and do not grant
rights to use or distribute the project.

## Before Work

Read, in order:

1. `markeitech.md`
2. `docs/product/sir-loke-v1.md`
3. `docs/current-status.md`
4. `docs/development-guidelines.md`
5. the accepted architecture and stage plan relevant to the change

Markeitect has final product and trading authority. Architecture and implementation decisions are
discussed before code changes.

## Publishing Identity And Issues

Before opening an authorized issue or PR, confirm whom the agent represents and the publishing
identity. Agents working for Markeitect (`ShriekinNinja`) use his locally configured Sir Kite
GitHub App and verify that the resulting author is `sir-kite[bot]`. Other contributors and their
agents use the contributor's authorized GitHub identity and verify the resulting author; they do
not need Sir Kite or its credentials. Report an unavailable identity instead of silently switching
to another account. The [GitHub workflow](docs/operations/github-workflow.md#publishing-identity)
contains the commands for both routes.

Every repository change begins with an authorized tracking issue. Read it and comment with a
milestone checklist, human and agent effort/time estimates, suggested model/reasoning effort,
Spark suitability, and open decisions. Markeitect resolves decisions and explicitly approves the
plan before an implementation PR or milestone work. Record substantive answers, decisions,
revisions, approvals, blockers, and completion in follow-up issue comments; link relevant PR
discussion there. An issue alone does not authorize implementation. Repository changes follow the
branch/PR process below.

## Branch And PR Workflow

Every repository change, including a documentation edit or small fix, follows this protocol.

1. After plan approval, begin from current `master` on a **new** stage/task-specific branch
   without a `codex/` prefix. Preserve unrelated local work; use a separate worktree when needed.
2. Explain the intended batch and boundaries. Implement and verify only approved milestone 1,
   then commit and push its first coherent change. Immediately open one linked PR with the
   approved checklist before requesting M1 approval. Keep its progress current; use a draft while
   unfinished. An implementation-ready handoff includes a PR URL. Use the publishing identity
   above. Request `@ShriekinNinja` as reviewer when the PR is ready and verify the request in
   GitHub. His approval is required for every PR, regardless of author; a mention alone does not
   satisfy the review requirement.
3. For later approved milestones, implement only their scope, update documentation, run
   proportional verification, and commit and push scoped changes.
4. Update the PR checklist, exact head, verification, and remaining gates. Record the milestone
   handoff on the issue, then stop for Markeitect's explicit approval before the next milestone.
   If approval occurs on the PR, link and record it on the issue before continuing.
5. Address review fixes through ordinary commits on that same PR and rerun affected checks. Do
   not combine unrelated work or reuse the branch after merge.
6. **Stop before merge.** Markeitect approves the final current head and merges it after all four
   required CI checks pass. An agent may perform only a specifically delegated merge, using a
   merge commit and the approved head. Any later commit requires renewed approval.
7. After the accepted checklist and merge are verified, close the linked issue. If task-local
   cleanup was approved in the issue plan, record exact targets on the issue and remove only that
   task's clean local branch/managed worktree. Preserve other or dirty work for a separate decision.
   Start the next change from refreshed `master` on another new branch.

The authorized change request includes commits, branch pushes, and PR publication after plan
approval; it does not waive milestone gates or authorize merge. Read-only requests authorize no
edits; plan-only work stays limited to the requested planning artifact. Explicit no-commit or
no-push instructions still limit publication.
Never commit or push directly to `master`, enable auto-merge, bypass checks, or force-push. Local
IDE review is available on request but is not the default delivery gate.

Do not commit secrets, machine configuration, vendor data, logs, database dumps, or raw market data.

## Verification

```bash
.venv/bin/markeitech verify all
```

Run `.venv/bin/markeitech verify postgres` separately only against an explicitly configured
disposable PostgreSQL database. Focused task-specific Ruff or pytest invocations remain valid for
development, but the full-repository acceptance scope is owned by `markeitech verify`.

Connected IB acceptance is manual and operator-owned. Automated tests and CI must never connect to
TWS/IB Gateway, Discord, or a live market-data provider.

See `docs/operations/github-workflow.md` for the full integration policy.
