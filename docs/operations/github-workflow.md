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

## Issues, Labels, And Planning

Use an issue for a bug, improvement proposal, or documentation gap that benefits from tracking.
The forms in `.github/ISSUE_TEMPLATE/` prompt for the problem, evidence, and expected result and
apply the existing `bug`, `enhancement`, or `documentation` label. They become available in the
normal issue chooser after merge into `master`; blank issues remain available for other work.
Form labels must already exist in the repository. See GitHub's
[issue-form documentation](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms).

Start with the existing labels rather than maintaining a large taxonomy:

| Label | Use on an issue or PR |
| --- | --- |
| `bug` | A correction to observed incorrect behavior |
| `enhancement` | A new capability or improvement |
| `documentation` | A documentation change; may accompany another label |
| `question` | An unresolved question or a request for clarification |
| `duplicate`, `wontfix` | A recorded disposition, with a reason and relevant links |

Apply one primary kind and add `documentation` when useful. Existing other labels remain
available. Issue forms set their default label automatically; the PR template only prompts the
author to apply labels in the sidebar or with `gh pr edit --add-label`. Labels classify work;
they do not indicate approval, runtime acceptance, or permission to implement. See
[managing labels](https://docs.github.com/en/issues/using-labels-and-milestones-to-track-work/managing-labels).

Optional additions for a later triage pass are `priority:high` for agreed urgent work,
`status:blocked` for a named unresolved dependency, `needs:decision` for a Markeitect decision,
and `needs:live-acceptance` for operator-owned verification. These are suggestions, not labels
installed by this PR. Add them only when needed, remove temporary labels when resolved, and
record the reason in the issue. Avoid a label for every actor, stage, or normal PR state.

Use a [milestone](https://docs.github.com/en/issues/using-labels-and-milestones-to-track-work/about-milestones)
to group issues and PRs for an accepted stage such as V3-03. Link its accepted roadmap instead of
copying a second status ledger. A GitHub Projects board is optional if the issue list becomes hard
to scan; no board or milestone is created by this batch. Git tags mark repository history and
underpin [releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases);
reserve new tags for explicitly approved release or recovery checkpoints.

In a PR, use `Closes #123` only when merging completes that issue's acceptance criteria. Use
`Refs #123` for partial work, investigation, or offline implementation with live acceptance still
pending. An issue, label, milestone, or checklist never replaces tracked project authority or
Markeitect's approval.

## Required Reviewer And Approval Enforcement

Markeitect's requested reviewer is **@ShriekinNinja for every PR**. The repository-wide
`.github/CODEOWNERS` entry assigns every path, including the ownership file and CI workflows,
to that account. GitHub reads ownership from the PR's base branch and automatically requests
code-owner reviews on eligible non-draft PRs once the file is merged. Existing open PRs should
be checked explicitly. Draft PRs receive automatic requests when marked ready. See
[GitHub code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners).

There is an identity prerequisite: GitHub does not allow PR authors to approve their own PRs.
On 2026-09-02, the CLI authenticated as `ShriekinNinja`, so PRs created with that authentication
are authored by the required reviewer. A distinct GitHub account or GitHub App must open PRs
for `ShriekinNinja` to review them. Changing Git commit author name/email does not change PR
authorship. Agents must not submit an approval using Markeitect's credentials or treat an
assignee, comment, label, or checklist as an approving review. See
[GitHub's approval rules](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews).

**Activation is pending the separate author identity; this PR does not enable the server-side
approval gate.** Before activating it, settle the author identity and handling of already-open
self-authored PRs with Markeitect. Keep such PRs unmerged until he resolves that conflict. Do not
silently weaken the review rule, add another approving owner, or create a bypass to avoid it.

After that prerequisite, configure the existing `master` protection with:

| Setting | Required value |
| --- | --- |
| Require a pull request before merging | Enabled |
| Required approving reviews | 1 |
| Require review from Code Owners | Enabled; `ShriekinNinja` is the sole owner of every path |
| Dismiss stale approvals when new commits are pushed | Enabled |
| Apply protection to administrators | Enabled; no review bypass allowances |
| Required status checks | Preserve all three existing V2 checks and their GitHub Actions source |
| Require branch to be up to date | Preserve enabled |
| Require conversation resolution | Preserve enabled |
| Allow force pushes / branch deletion | Preserve disabled |

The 2026-09-02 read-only API inspection found zero required approvals, code-owner reviews disabled,
and stale-review dismissal disabled. The other protection settings above were already present;
there were no repository rulesets. This is an inspection snapshot, not proof of later enforcement.
Re-read live protection before any update and preserve unrelated settings. GitHub's
[branch-protection guide](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule)
describes these controls.

Verify activation using a PR authored by the separate identity: confirm the reviewer request and
blocked merge state before approval, then the review requirement after Markeitect approves and
after a subsequent change dismisses that approval. Inspect API/UI state without attempting an
unapproved merge. GitHub's stale-review dismissal covers code-modifying pushes; the project rule
still requires Markeitect to review the current head after every new commit. Record the tested
scope and resulting settings before claiming this gate is enforced.

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
