# GitHub Workflow

Markeitech uses GitHub for reviewable integration of the V2 runtime. This is a source-control
and continuous-integration workflow; it is not a deployment system.

The API-reference Pages site is deployed by `.github/workflows/api-docs.yml` after the API-docs
verification pipeline succeeds. Runtime services and deployment targets are managed separately from
this document.

Fresh-machine preparation is documented in
[`developer-setup.md`](developer-setup.md). The conventional repository contribution summary is
available at the root in [`CONTRIBUTING.md`](../../CONTRIBUTING.md).

## Protocol And Authority

Effective 2026-09-02: **every repository change uses a new scoped branch and an open GitHub PR;
Markeitect approves the current PR head and owns the merge.** This includes code, tests,
documentation, configuration templates, tools, and small fixes. One change means one coherent
review batch, not a new branch per file or commit.

For repository changes, begin with a tracking issue. Read it and comment there with a milestone
checklist, human and agent effort/time estimates, suggested model and reasoning effort, Spark
suitability, and open questions or decisions. Markeitect resolves the decisions and explicitly
approves the plan before the implementation PR opens or milestone work begins. One PR carries the
approved checklist and is updated through ordinary commits. Stop after each milestone until
Markeitect explicitly approves continuing. Final PR-head approval and merge remain separate gates.

The integration/default branch is currently `master`. Informal references to the main branch mean
that branch; a rename to `main` requires a separate request. Never implement or commit changes
directly on the integration branch, push changes directly to it, or use a local merge as a bypass
around the PR gate.

An authorized repository-change request includes the commits, branch pushes, and PR creation or
updates needed to present its approved milestones for review. It does not waive plan or milestone
approval and does not authorize a merge. Read-only requests authorize no edits and need no branch
or PR; plan-only requests permit only the requested planning artifact, not runtime
implementation. An explicitly requested plan file follows the same branch/PR
protocol. Explicit no-commit or no-push restrictions still limit publication. Ignored machine-state
repairs remain separately authorized local operations and must never be committed just to create
a PR.

This protocol replaces older default instructions to leave changes uncommitted or seek separate
permission for routine publication of the requested work. Historical stage records and old
planning/skill text do not override it. Local IDE review remains available when Markeitect asks
for it; architecture approval, connected acceptance, secrets, and destructive-action boundaries
are unchanged.

## Publishing Identity

Before an authorized issue or PR publication, identify the contributor the agent represents and
verify the publishing identity. The repository owner or a Git commit author setting alone does
not identify whom the agent represents.

| Contributor represented | Required publishing route | Author to verify |
| --- | --- | --- |
| Markeitect (`ShriekinNinja`) | His locally configured Sir Kite GitHub App | `sir-kite[bot]` |
| Another contributor | That contributor's authorized GitHub account | The contributor's verified account |

This rule applies to both issues and PRs. Other contributors do not need Sir Kite credentials.
If the required identity is unavailable, report the blocker instead of silently falling back to
another account, CLI login, or connector. The Codex GitHub connector and Sir Kite are separate
integrations; the availability of a connector does not establish the required publishing identity.
Verify the returned author and report the issue or PR URL after creation.

The commands below document [the contributor route](#publishing-as-another-contributor) and
[the local Sir Kite route](#publishing-locally-for-markeitect-as-sir-kite). This routing rule does
not itself authorize external publication, implementation, approval, or merge.

## Change Lifecycle

1. Read or open the tracking issue, post the [milestone plan](#issues-labels-and-planning),
   resolve its decisions, and obtain Markeitect's explicit plan approval. Record approval on the
   issue before proceeding. Inspect the current branch, worktree, remote default branch, and task
   scope. Refresh the integration checkpoint without discarding local work. If unrelated work is
   present, preserve it and create a separate worktree rather than stash or reset it.
2. Create a new stage/task-specific branch, without a `codex/` prefix, after plan approval. Keep
   one coherent change on it. Review corrections stay on this branch while its PR is open; never
   reuse a merged/closed PR branch for new work.
3. Explain the intended batch and meaningful tradeoffs, implement only approved milestone 1,
   and keep code and documentation consistent. Run proportional verification and inspect the diff
   for unintended files, secrets, local configuration, data, or generated churn. Commit only
   task-owned paths and push without force. Do not infer new architecture or product authority.
4. Immediately open one PR into `master` through the required
   [publishing identity](#publishing-identity) after the first coherent milestone commit. Copy the
   approved checklist, estimates, decisions, scope, and gates into its body; link the issue.
   Request `@ShriekinNinja` as reviewer when ready and verify the request in GitHub. Use a draft
   while unfinished if appropriate. If credentials, connectivity, or an explicit restriction
   block publication, preserve the work and report the blocker before requesting M1 approval.
5. Update the PR checklist, exact head, scope, validation, debt, and CI state. Post a milestone
   handoff on the issue with the PR link and evidence. Stop until Markeitect explicitly approves
   the milestone in an issue or PR comment. If approval occurs on the PR, link and record that
   outcome on the issue before the next milestone. A review-ready delivery includes the PR URL,
   exact head, scope, validation, known debt, and current CI state.
6. Address review changes with ordinary commits on the same PR. Update its checklist and evidence,
   rerun affected checks, and report the new head. Do not amend and force-push. A revised milestone
   needs renewed review of the affected behavior.
7. Stop with the PR **unmerged**. Passing CI, opening a PR, receiving milestone approval, or being
   asked to finish the workflow does not grant merge authority. Do not enable auto-merge or bypass
   branch rules/checks.
8. Markeitect approves the final current head and performs the merge after required CI passes. An
   agent may merge only if Markeitect explicitly delegates that specific PR merge. Before a
   delegated merge, verify the PR/base/head, current approval, absence of unreviewed changes, and
   successful required checks for that head; use a merge commit bound to the approved head. New
   commits invalidate prior approval and require renewed approval.
9. After the accepted checklist is complete, record the final milestone outcome and any approved
   task-local cleanup targets on the issue before merge. Verify the remote merge result before
   reporting it as merged. Close the linked issue if merge has not already closed it. If the
   approved issue plan includes task-local cleanup, remove only the recorded clean local branch
   and managed worktree after verifying a clean tree. Preserve other or dirty work and request a
   separate decision.
   Refresh the local integration branch by fast-forward when appropriate, then start new work on
   another branch.
   Dependent work waits for its prerequisite PR to merge unless Markeitect approves otherwise.

## Runtime Live Feedback And Local Tests

Agents locally run the tests they add/change and specific CI failures needed for diagnosis. PR CI
owns broad regression checks. Do not routinely run full suites or unrelated validation tools, or
create a test solely to satisfy process. Narrow integrity checks/generation apply to changed
artifacts. Existing CI jobs and final-head approval requirements remain in force.

For runtime changes, reach a short practical live scenario promptly. Provide exact revision,
setup/commands, account/instruments, intended actions, expected result and stop condition.
Markeitect performs and reviews the run unless he explicitly delegates it. A development request
does not authorize an account connection or order. Record actual findings and unexercised cases;
fix concrete findings on the same PR. Do not require an exhaustive proof programme before live use.

Documentation changes need document review. Use `Refs` when issue acceptance still requires a live
result, and `Closes` when this PR completes the issue. CI does not establish connected behavior.

## PR Review Record

Use `.github/pull_request_template.md`. Every PR must state:

- the approved milestone checklist and current progress, with links to issue-recorded decisions;
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

Use an issue for every repository change. For repository changes, follow **Issue -> Plan -> Approve
plan -> PR -> Approve each milestone -> Approve final head -> Merge**:

1. Check for an existing relevant issue, then open or reuse the authorized tracking issue using
   the required publishing identity. State the problem, evidence, bounded scope, and acceptance
   criteria. Verify the author and record its URL.
2. Read the issue and post a solution-plan comment with a milestone checklist. For each milestone,
   include its outcome/scope, human effort and time estimate, agent time estimate, suggested model
   and reasoning effort, and whether Spark is suitable. List open questions and decisions. Resolve
   every implementation-dependent decision and obtain Markeitect's explicit plan approval before
   opening the implementation PR or starting milestone 1. Silence, a label, or an issue's existence
   is not approval.
3. Open one linked PR with the approved checklist. Update its checklist state, exact head,
   verification, and remaining gates after each milestone. Record substantive answers, plan
   changes, decisions, milestone reviews/approvals, blockers, and completion in new follow-up
   issue comments. When conversation happens elsewhere, summarize its outcome and link it on the
   issue; editing the plan comment alone does not preserve the conversation.
4. Present each milestone for Markeitect's explicit approval before continuing. Then present the
   verified final PR head for his formal approving review. An agent never approves on his behalf.
5. Markeitect owns the merge after the required CI and current-head approval gates pass. An agent
   may perform only a specifically delegated merge under the existing change lifecycle.

Opening an issue alone changes GitHub metadata and needs no source branch or PR. It grants no
implementation or merge authority. Do not create a duplicate merely to test permissions or retry
an uncertain write: inspect the reported resource or recent issues first.

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

The approval requirement applies to every author. Verify that `ShriekinNinja` appears in the
requested reviewers when a PR becomes ready, even when `CODEOWNERS` should request him
automatically. If the publisher lacks permission to request reviewers, tag `@ShriekinNinja` in
the PR body and report the missing review request for a maintainer to resolve. A mention does
not satisfy a review request or the required approval, and the PR must remain unmerged.

GitHub does not allow PR authors to approve their own PRs. Sir Kite is Markeitect's private,
locally configured GitHub App, used by his agents to open PRs as `sir-kite[bot]` so
`ShriekinNinja` can review and approve them. Other contributors and their agents open PRs through
their own authorized GitHub identities; they do not need Sir Kite, its private key, or its
local configuration. The absence of Sir Kite on another contributor's machine is not a
publication blocker. Changing Git commit author name/email does not change PR authorship.
Agents must not submit an approval using Markeitect's credentials or treat an
assignee, comment, label, or checklist as an approving review. See
[GitHub's approval rules](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews).

On 2026-09-02, Markeitect authorized Sir Kite's registration and installation on only
`ShriekinNinja/Markeitech_V2`. App authentication and a single-repository installation token
were verified against GitHub. Later that day Markeitect added Issues read/write and approved the
installation update; [issue #23](https://github.com/ShriekinNinja/Markeitech_V2/issues/23) was
created as `sir-kite[bot]` in the bounded live permission test.
The approved installation now has contents/metadata read access and issues/pull-request
read/write access; it has no administration, secrets, or workflow permissions. Webhooks and
user OAuth are disabled. App registration ID is `4807574`; installation ID is `158548175`.
These identifiers are not credentials. The private key and local configuration stay outside Git.

The following `master` protection settings were read back on 2026-09-17. The original
protection was activated on 2026-09-02; issue #34 subsequently added the API docs check.

| Setting | Required value |
| --- | --- |
| Require a pull request before merging | Enabled |
| Required approving reviews | 1 |
| Require review from Code Owners | Enabled; `ShriekinNinja` is the sole owner of every path |
| Dismiss stale approvals when new commits are pushed | Enabled |
| Apply protection to administrators | Enabled; no review bypass allowances |
| Required status checks | `V2 Ruff`, `V2 Offline Tests`, `V2 PostgreSQL Integration`, and `API docs verification`, all bound to GitHub Actions |
| Require branch to be up to date | Preserve enabled |
| Require conversation resolution | Preserve enabled |
| Allow force pushes / branch deletion | Preserve disabled |

The 2026-09-17 API readback reports all four checks with strict synchronization enabled,
one required code-owner approval, stale-review dismissal, administrator enforcement,
conversation resolution, and force-push and deletion prohibitions. This is a dated settings
observation; re-read live protection
before any later update. GitHub's
[branch-protection guide](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule)
describes these controls.

PR #20 merged `CODEOWNERS` into `master` on 2026-09-02, enabling automatic routing and
owner-specific enforcement for subsequent eligible PRs. The self-authored predecessor, PR #19,
was closed unmerged with its history preserved. Do not weaken protection or create a bypass.

Inspect API/UI state without attempting an unapproved merge. Approval and subsequent stale-review
dismissal still require human acceptance evidence; no agent submits a review on Markeitect's
behalf. GitHub's stale-review dismissal covers code-modifying pushes; the project rule requires
Markeitect to review the current head after every new commit.

## Publishing As Another Contributor

Use the contributor's own authorized GitHub account for issues and PRs through GitHub's UI, CLI,
or API. Confirm the active account before publishing; agents representing Markeitect use Sir Kite
instead. To open an authorized issue:

```bash
gh api user --jq .login
gh issue create --repo ShriekinNinja/Markeitech_V2 \
  --title "Describe the problem" --body-file /tmp/issue-description.md --label enhancement
```

Read back the returned issue with
`gh issue view ISSUE-NUMBER --repo ShriekinNinja/Markeitech_V2 --json url,author`
and verify its author matches the intended contributor. Replace the example title, body file,
label, and issue number with the authorized scope. Record the plan and substantive follow-ups with
`gh issue comment ISSUE-NUMBER --repo ShriekinNinja/Markeitech_V2 --body-file /tmp/issue-comment.md`
and verify the resulting comment author and URL. For a branch already pushed to the target
repository, a ready PR can be opened with:

```bash
gh api user --jq .login
gh pr create --repo ShriekinNinja/Markeitech_V2 --base master \
  --head your-change-branch --title "Describe the change" \
  --body-file /tmp/pr-description.md --reviewer ShriekinNinja
```

For a fork, select the fork branch in GitHub or use `--head YOUR-LOGIN:your-change-branch`.
Replace the example values and apply the relevant existing labels. Use a draft for unfinished
work, then verify the reviewer request when marking it ready. If the PR already exists, update
it and use `gh pr edit PR-NUMBER --repo ShriekinNinja/Markeitech_V2 --add-reviewer ShriekinNinja`
when a review request is missing and the account has permission. Verify the resulting PR author
with `gh pr view PR-NUMBER --repo ShriekinNinja/Markeitech_V2 --json url,author`. Agents working for
`ShriekinNinja` use the local Sir Kite route for both issues and PRs.

## Publishing Locally For Markeitect As Sir Kite

This section applies to Markeitect's agents using his authorized local Sir Kite setup.
Use `scripts/sir-kite-pr.py` for issues, issue comments, and PRs. Its existing path and PR
arguments remain compatible; `--issue` selects issue creation and `--comment ISSUE` selects an
existing issue. Markeitect's ordinary GitHub CLI login remains `ShriekinNinja`; the helper
authenticates its publications as `sir-kite[bot]`. It requires Python 3,
OpenSSL, and curl and adds no Python package dependency. If this local setup is unavailable,
report the blocker instead of publishing under another identity. Other contributors use the
preceding section.

To open an authorized tracking issue before implementation:

```bash
python3 scripts/sir-kite-pr.py --issue \
  --title "Describe the problem" \
  --body-file /tmp/issue-description.md \
  --label enhancement
```

The issue command creates one issue with the supplied labels in the same request, prints its URL,
and verifies its author is `sir-kite[bot]`. It does not update or close an existing issue, create a
branch, request PR review, or implement the issue. `--head` and `--draft` are PR-only. Do not rerun
issue creation blindly after a timeout, error, or unexpected author: a write may have succeeded.
Inspect the printed URL or recent issues before deciding whether another creation is needed.

To record a plan, decision, milestone result, or follow-up on an open issue:

```bash
python3 scripts/sir-kite-pr.py --comment ISSUE-NUMBER \
  --body-file /tmp/issue-comment.md
```

The comment command reuses an issue-scoped token. It checks that the target is the exact open
issue in this repository and not a PR, then verifies the returned issue and `sir-kite[bot]`
author. It prints the comment URL before postflight validation; inspect that URL or the issue
before retrying an uncertain result. A comment takes a body file, not a title, label, or draft
flag. Recording a plan comment is not plan approval.

After the approved plan and the first publishable branch diff, open or update its PR with the
approved checklist. Include the tracking issue in the PR body with the appropriate `Closes`
or `Refs` relationship:

```bash
python3 scripts/sir-kite-pr.py \
  --head your-change-branch \
  --title "Describe the change" \
  --body-file /tmp/pr-description.md \
  --label enhancement --label documentation
```

Replace the branch, title, body file, and labels for the task. `master` is the fixed base.
The PR command creates or updates the open Sir Kite PR for that branch, verifies its author, and
requests `ShriekinNinja` on non-draft PRs. `--draft` applies when creating a PR; it does not change an
existing PR's draft state. An existing PR by a different author is rejected without changing it.
If a later reviewer/label operation fails, the PR URL is printed first; inspect that resource
and rerun the command rather than assuming no PR was created. It never approves or merges PRs.

When diagnosing authentication, `python3 scripts/sir-kite-pr.py --verify` checks PR token scope;
add `--issue` to check issue token scope. Verification issues and revokes a temporary token but
does not publish an issue or PR. A successful publication already exercises its authentication
checks, so a separate verification run is not required before every publication.

The default machine configuration is `~/.config/markeitech/sir-kite/config.json`; use
`SIR_KITE_CONFIG` or `--config` for another local path. It has the following fields:

```json
{
  "app_id": 4807574,
  "client_id": "Iv23li4ifiTkL9po4BA6",
  "installation_id": 158548175,
  "repository_id": 1336146392,
  "repository": "ShriekinNinja/Markeitech_V2",
  "owner": "ShriekinNinja",
  "slug": "sir-kite",
  "private_key": "/absolute/path/outside/the/repository/private-key.pem"
}
```

This is a configuration example, not a key. Keep the actual key in a private directory with
mode `0700`, and key/config files with mode `0600`. This private setup belongs to Markeitect;
do not distribute it to other contributors or make it part of general developer onboarding.
Provisioning it on another machine for Markeitect remains a separately authorized operation;
do not copy credentials into a PR, chat, repository, or log.

The helper signs a short-lived app JWT locally, validates the app and installation identity, and
requires the exact approved installation permission set above. Missing or unapproved permissions
stop the operation before token issuance; changing the app registration also requires approval of
the new permissions on the installation. No helper command changes GitHub app or installation
settings.

Tokens are narrowed to this repository ID and the selected operation:

| Operation | Requested token permissions |
| --- | --- |
| PR creation/update or default `--verify` | Contents read, Metadata read, Pull requests write |
| Issue creation or `--issue --verify` | Metadata read, Issues write |

Installation permissions and operation token permissions are validated separately: the approved
Issues grant no longer breaks PR authentication, and PR tokens do not acquire it incidentally.
The helper checks the exact token scope before publication and revokes the token on exit.
Tokens pass to curl through stdin rather than command arguments; curl's default config and redirects are disabled,
and certificate verification stays enabled. A failed revocation is reported; an unreleased
installation token expires within one hour. A terminated process may likewise leave a token
valid until expiration. See GitHub's
[installation-token procedure](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app).

The command is a development-time publishing utility. It is separate from the optional Kite
development plugin and does not grant runtime or review authority.

## Required CI

Pull requests targeting `master` and manual workflow runs execute `.github/workflows/v2-ci.yml`.
That workflow has three required jobs:

- **V2 Ruff** runs `markeitech verify lint` over `src`, `tests`, and the Sir Kite publishing helper.
- **V2 Offline Tests** runs `markeitech verify test`, with PostgreSQL-marked tests excluded.
- **V2 PostgreSQL Integration** starts an ephemeral PostgreSQL 17 service and runs only the
  PostgreSQL-marked tests with a synthetic CI DSN through `markeitech verify postgres`.

CI uses Python 3.13 and the V2 `uv.lock` with frozen installation. It has `contents: read`,
cancels superseded pull-request runs, and never launches the Markeitech runtime, IB/TWS,
Discord, or a market-data path. The CI database and credentials exist only for the job.

`.github/workflows/api-docs.yml` also runs on pull requests to `master`. Its required
**API docs verification** job validates the static API documentation, checks that the tracked
`docs/api` artifact is current, runs the API-docs tests, and checks that the tests leave the
artifact unchanged. Pages deployment runs only after verification on `master` and is not a
required PR check.

All four required checks must succeed on the current PR head before merge; failed, pending,
missing, or skipped required checks do not satisfy the gate. Green CI does not replace
Markeitect's approval.

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
