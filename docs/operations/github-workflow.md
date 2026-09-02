# GitHub Workflow

Markeitech uses GitHub for reviewable integration of the V2 runtime. This is a source-control
and continuous-integration workflow; it is not a deployment system.

Fresh-machine preparation is documented in
[`developer-setup.md`](developer-setup.md). The conventional repository contribution summary is
available at the root in [`CONTRIBUTING.md`](../../CONTRIBUTING.md).

## Protocol And Authority

Effective 2026-09-02: **every repository change uses a new scoped branch and an open GitHub PR;
Markeitect approves the current PR head and owns the merge.** This includes code, tests,
documentation, configuration templates, tools, and small fixes. One change means one coherent
review batch, not a new branch per file or commit.

The integration/default branch is currently `master`. Informal references to the main branch mean
that branch; a rename to `main` requires a separate request. Never implement or commit changes
directly on the integration branch, push changes directly to it, or use a local merge as a bypass
around the PR gate.

An authorized repository-change request includes the commits, branch pushes, and PR creation or
updates needed to present that scope for review. It does not authorize a merge. Read-only requests
authorize no edits and need no branch or PR; plan-only requests permit only the requested planning
artifact, not runtime implementation. An explicitly requested plan file follows the same branch/PR
protocol. Explicit no-commit or no-push restrictions still limit publication. Ignored machine-state
repairs remain separately authorized local operations and must never be committed just to create
a PR.

This protocol replaces older default instructions to leave changes uncommitted or seek separate
permission for routine publication of the requested work. Historical stage records and old
planning/skill text do not override it. Local IDE review remains available when Markeitect asks
for it; architecture approval, connected acceptance, secrets, and destructive-action boundaries
are unchanged.

## Change Lifecycle

1. Inspect the current branch, worktree, remote default branch, and task scope. Refresh the
   integration checkpoint without discarding local work. If unrelated work is present, preserve
   it and create a separate worktree rather than stash, reset, or carry it into the new PR.
2. Create a new stage/task-specific branch, without a `codex/` prefix, before editing. Keep one
   coherent change on it. Review corrections stay on this branch while its PR is open; never
   reuse a merged/closed PR branch for a new change.
3. Explain the intended batch and meaningful tradeoffs, implement the authorized scope, and keep
   code and documentation consistent. Do not infer new architecture or product authority.
4. Run proportional local verification and inspect the full diff for unintended files, secrets,
   local configuration, data, or generated churn. Commit only task-owned paths, with a detailed
   message, and push the branch without force.
5. Open a PR into `master` once the first coherent batch is published. Use a draft for unfinished
   work and state its remaining gates. A review-ready delivery includes the PR URL, exact head,
   scope, validation, known debt, and current CI state; uncommitted files alone are not the default
   handoff. If credentials, connectivity, or an explicit task restriction block publication,
   preserve the work and report the exact remaining action instead of claiming completion.
6. Address requested review changes with ordinary commits on the same open PR. Update its scope
   and evidence, rerun affected checks, and report the new head. Do not amend and force-push.
7. Stop with the PR **unmerged**. Passing CI, opening a PR, receiving implementation approval,
   or being asked to finish the workflow does not grant merge authority. Do not enable auto-merge
   or bypass branch rules/checks.
8. Markeitect approves the current head and performs the merge after required CI passes. An agent
   may merge only if Markeitect explicitly delegates that specific PR merge. Before a delegated
   merge, verify the PR/base/head, current approval, absence of unreviewed changes, and successful
   required checks for that head; use a merge commit bound to the approved head. New commits
   invalidate the prior merge approval and require renewed approval.
9. Verify the remote merge result before reporting it as merged. Only then refresh the local
   integration branch by fast-forward and start the next change on another new branch. Dependent
   work waits for its prerequisite PR to merge unless Markeitect explicitly approves another
   arrangement. Branch/worktree deletion still requires separate approval.

## PR Review Record

Use `.github/pull_request_template.md`. Every PR must state:

- the requested stage/change, included files/responsibilities, and explicit exclusions;
- contract, behavior, configuration, dependency, provider, schema, and persistence effects, or
  an explicit `none` where applicable;
- local validation commands/results and remaining CI/acceptance gates;
- connected/live acceptance, clearly separated from offline tests;
- operational/data impact, recovery considerations, and known debt; and
- that the PR is awaiting Markeitect's review/merge rather than claiming approval on his behalf.

An agent does not approve its own work or fabricate a user approval. A review approval is tied to
the exact head reviewed and does not by itself delegate merge execution to an agent.

## Required CI

Pull requests targeting `master` and manual workflow runs execute `.github/workflows/v2-ci.yml`.
The workflow has three branch-protection-ready jobs:

- **V2 Ruff** runs `ruff check` over `src` and `tests`.
- **V2 Offline Tests** runs the V2 pytest suite with PostgreSQL-marked tests excluded.
- **V2 PostgreSQL Integration** starts an ephemeral PostgreSQL 17 service and runs only the
  PostgreSQL-marked tests with a synthetic CI DSN.

CI uses Python 3.13 and the V2 `uv.lock` with frozen installation. It has `contents: read`,
cancels superseded pull-request runs, and never launches the Markeitech runtime, IB/TWS,
Discord, or a market-data path. The CI database and credentials exist only for the job.

All three jobs must succeed on the current PR head before merge; failed, pending, missing, or
skipped required checks do not satisfy the gate. Green CI does not replace Markeitect's approval.

GitHub branch protections/rulesets should enforce PR-only integration, these checks, and denial
of force pushes. Documentation and the PR template express policy; they do not configure or prove
server-side enforcement. Changing protection settings, permissions, review requirements, merge
methods, or the default branch needs separate approval. Do not add a second required reviewer as
an incidental change to Markeitect's owner-led workflow.

## Merge History

Use merge commits for change pull requests. Deliberate stage history is useful for auditing
architecture decisions and live acceptance. Do not squash away that sequence by default.

Pre-migration source remains recoverable through the annotated migration tags and Git history.
This CI workflow runs only the current V2 project.

## Deployment Boundary

There is no continuous deployment step yet. Markeitech runs locally beside TWS/IB Gateway and
does not currently have a defined deployment target, operator, secret-management boundary, or
rollback procedure. Add CD only after those operational decisions are approved.
