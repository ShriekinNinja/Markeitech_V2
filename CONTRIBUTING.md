# Contributing To Markeitech

Markeitech is proprietary. Contributions require prior approval from Markeitect and do not grant
rights to use or distribute the project.

## Before Work

Read, in order:

1. `markeitech.md`
2. `docs/current-status.md`
3. `docs/development-guidelines.md`
4. the accepted architecture and stage plan relevant to the change

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

For issue-tracked work, follow **Issue -> PR -> Approve -> Merge**: open or reuse the authorized
tracking issue with the problem and acceptance criteria, link the implementation PR, and leave
approval of its current head and merge to Markeitect. An issue alone needs no branch or PR and
does not authorize implementation. Repository changes follow the branch/PR process below.

## Branch And PR Workflow

Every repository change, including a documentation edit or small fix, follows this protocol.

1. Begin from the current integration branch (`master`) on a **new** stage/task-specific branch
   without a `codex/` prefix. Preserve unrelated local work; use a separate worktree when needed.
2. Explain the intended batch and boundaries before editing.
3. Implement the authorized scope, update its documentation, and run proportional verification.
4. Commit the scoped files with a detailed message, push the change branch, and open a detailed
   PR into `master`. Use a draft if unfinished; an implementation-ready handoff includes a PR URL.
   Use the publishing identity above. Request `@ShriekinNinja` as reviewer
   when the PR is ready and verify the request in GitHub. His approval is required for every PR,
   regardless of author; a mention alone does not satisfy the review requirement.
5. Address requested review fixes through ordinary commits on that same open PR and rerun the
   affected checks. Do not combine unrelated work or reuse the branch after merge.
6. **Stop before merge.** Markeitect approves the current head and merges it after all three
   required CI checks pass. An agent may perform only a specifically delegated merge, using a
   merge commit and the approved head. Any later commit requires renewed approval.
7. After the merge is verified, start the next change from refreshed `master` on another new
   branch. Do not delete branches or worktrees without approval.

The authorized change request includes commits, branch pushes, and PR publication; it does not
authorize merge. Read-only requests authorize no edits; plan-only work stays limited to the
requested planning artifact. Explicit no-commit or no-push instructions still limit publication.
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
