# GitHub Workflow

Markeitech uses GitHub for reviewable integration of the V2 runtime. This is a source-control
and continuous-integration workflow; it is not a deployment system.

Fresh-machine preparation is documented in
[`developer-setup.md`](developer-setup.md). The conventional repository contribution summary is
available at the root in [`CONTRIBUTING.md`](../../CONTRIBUTING.md).

## Stage Branches

Keep one approved stage branch active at a time. Before beginning a new stage, the previously
approved batch must already be committed. The next batch is reviewed in the IDE while its edits
remain uncommitted. After Markeitect approves the changes, create a detailed commit and use that
commit as the branch checkpoint.

The normal flow is:

1. Create or switch to the stage branch from the approved checkpoint.
2. Explain the slice and its contracts before editing.
3. Leave implementation changes uncommitted for Markeitect review.
4. Commit the approved batch with a detailed message.
5. Push the stage branch manually.
6. Open a pull request into `master`.
7. Merge only after the required CI checks pass.

The branch name should identify the stage, such as `v2-ci-foundation`. Do not use force pushes.

## Required CI

Pull requests targeting `master` and manual workflow runs execute `.github/workflows/v2-ci.yml`.
The workflow has three branch-protection-ready jobs:

- **V2 Ruff** runs `ruff check` over `v2/src` and `v2/tests`.
- **V2 Offline Tests** runs the V2 pytest suite with PostgreSQL-marked tests excluded.
- **V2 PostgreSQL Integration** starts an ephemeral PostgreSQL 17 service and runs only the
  PostgreSQL-marked tests with a synthetic CI DSN.

CI uses Python 3.13 and the V2 `uv.lock` with frozen installation. It has `contents: read`,
cancels superseded pull-request runs, and never launches the Markeitech runtime, IB/TWS,
Discord, or a market-data path. The CI database and credentials exist only for the job.

Once the repository is connected, configure `master` to require the three named CI jobs and
disallow force pushes. External approval is intentionally not required yet so Markeitect can
merge the reviewed work directly.

## Merge History

Use merge commits for stage pull requests. Deliberate stage history is useful for auditing
architecture decisions and live acceptance. Do not squash away that sequence by default.

Pre-migration source remains recoverable through the annotated migration tags and Git history.
This CI workflow runs only the current V2 project.

## Deployment Boundary

There is no continuous deployment step yet. Markeitech runs locally beside TWS/IB Gateway and
does not currently have a defined deployment target, operator, secret-management boundary, or
rollback procedure. Add CD only after those operational decisions are approved.
