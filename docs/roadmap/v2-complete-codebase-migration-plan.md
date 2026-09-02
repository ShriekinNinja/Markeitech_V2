# V2 Root Promotion And V1 Retirement Plan

Status: **ACCEPTED — implementation proceeds as two separately reviewed pull requests**

Originally prepared: 2026-08-30

Accepted and revised: 2026-09-02

Execution baseline: `553ad135` (`Merge pull request #12 from MarkeiTech/v3-03-session-metrics-slice-2`)

PR 1 branch: `v2-root-promotion-v1-retirement`

Pre-migration recovery tag: `pre-v2-root-promotion-2026-09-02` at `553ad135`

Earlier V1 reference: annotated tag `v1-runtime-final`, peeled commit `b398bdf`

## 1. Accepted Outcome

Make Markeitech a conventional, V2-only Python repository:

```text
/
├── .agents/
├── .codex/
├── .github/
├── docs/
├── plugins/
├── scripts/
├── tools/
├── src/markeitech/
├── tests/
├── config/
├── data/                       # ignored/local runtime and evidence state
├── compose.yaml
├── pyproject.toml
├── uv.lock
├── .env.example
├── .python-version
├── AGENTS.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md
└── markeitech.md
```

The final tracked tree has no `v2/`, `backend/`, `frontend/`, V1 package, V1 tests, V1
configuration, or V1-only documentation. V2 becomes the only runtime and is promoted from `v2/`
to the repository root.

This is a structural repository migration. It does not add product behavior, revive V1 behavior,
rename the V2 distribution, update dependencies, change schemas, or widen connected acceptance.
The package name remains `markeitech-v2` during this migration; a later rename, if desired, is a
separate small change.

## 2. Two-PR Boundary

The migration is intentionally split so deletion and path movement are never mixed in one review.

### PR 1 — retire tracked V1, keep V2 nested

Branch: `v2-root-promotion-v1-retirement`

PR 1:

- records this accepted migration plan and recovery point;
- removes the tracked V1 runtime, package, tests, configuration, frontend, and V1-only documents;
- repairs active documentation and source references to describe one current V2 runtime;
- leaves all V2 runtime files under `v2/`;
- leaves functional `v2/...` commands, CI paths, scripts, and tool source roots unchanged; and
- proves the nested V2 project remains green before review.

PR 1 must not move V2 files, alter dependencies or lockfiles, delete Git refs, or touch ignored
local state.

### PR 2 — promote V2 to the repository root

PR 2 starts only after PR 1 is reviewed and merged. It atomically moves:

| Current path | Final path |
|---|---|
| `v2/src/` | `src/` |
| `v2/tests/` | `tests/` |
| `v2/config/` | `config/` |
| `v2/.env.example` | `.env.example` |
| `v2/compose.yaml` | `compose.yaml` |
| `v2/pyproject.toml` | `pyproject.toml` |
| `v2/uv.lock` | `uv.lock` |

PR 2 also updates all functional path assumptions in CI, scripts, tests, documentation tools,
plugins, architecture manifests, operator documentation, and project instructions. It removes the
empty `v2/` directory, normalizes safe ignore rules, regenerates affected generated artifacts, and
proves the root project is green.

PR 2 must not add behavior or combine the structural move with a package rename, dependency update,
configuration redesign, IDE migration, or connected-provider work.

## 3. Critical Definition: Retired V1 Versus V2 Contract Version 1

The project cleanup must not use a blind text replacement for `v1`.

Retired V1 material includes the former root runtime and its product model:

- root `backend/`, `frontend/`, `tests/`, and tracked `config/`;
- root `.env.example`, `pyproject.toml`, and `uv.lock`;
- V1-only operations, architecture, roadmap, note, research, and archive documents; and
- obsolete references to those paths or behaviors as current authority.

All of these tracked project surfaces are accepted for deletion. No V1 implementation or behavior
is admitted into V2 by this migration. Any future need must be designed anew against current V2
authority.

The following are current V2 version identities and are not retired-project material:

- typed contract identifiers such as `markeitech.historical.request_plan.v1`;
- calendar, metric, entity, policy, fixture, parameter-set, and configuration identities ending in
  `.v1` or `-v1`;
- schema version values; and
- tests of current version or compatibility boundaries.

Those identities preserve lineage and wire meaning. They remain unless their actual contract is
changed through a separately reviewed version migration.

## 4. Verified Starting Census

Measured at the accepted execution baseline:

| Surface | Tracked files | Accepted disposition |
|---|---:|---|
| Entire repository | 608 | Census universe |
| `v2/` | 141 | Keep in PR 1; promote in PR 2 |
| Root `backend/` | 97 | Delete in PR 1 |
| Root `tests/` | 60 | Delete in PR 1 |
| Root tracked `config/` | 3 | Delete in PR 1 |
| `frontend/` | 7 | Delete in PR 1 |
| Root `.env.example`, `pyproject.toml`, `uv.lock` | 3 | Delete in PR 1 |
| V1-only documents listed below | 24 | Delete in PR 1 |

The V1 executable/package deletion surface is 170 tracked files. The V1-only documentation
surface is 24 tracked files. Counts must be rechecked in the final PR 1 diff.

## 5. PR 1 Exact Deletion Scope

### 5.1 Executable and package surfaces

- `backend/`
- root `tests/`
- tracked files under root `config/`
- `frontend/`
- root `.env.example`
- root `pyproject.toml`
- root `uv.lock`

### 5.2 V1-only documents

- `LEGACY.md`
- `docs/architecture/data-contracts.md`
- `docs/architecture/decisions-register.md`
- `docs/architecture/runtime-architecture.md`
- `docs/architecture/runtime-data-flow-audit.md`
- `docs/archive/initial-greenfield-brief.md`
- `docs/archive/stage-0-project-context.md`
- `docs/archive/v1-current-status.md`
- `docs/archive/v1-run-configurations/README.md`
- `docs/notes/2026-07-21-markeitect-model-handoff.md`
- `docs/notes/markeitect-notes.md`
- `docs/operations/analytics-chart.md`
- `docs/operations/operator-context-logs.md`
- `docs/operations/operator-signal-logs.md`
- `docs/operations/persistence-maintenance.md`
- `docs/operations/reference-set-enrichment.md`
- `docs/operations/signal-outcome-audit.md`
- `docs/research/markeitect-model-plan.md`
- `docs/research/markeitect-model.md`
- `docs/research/trading-frameworks-study.md`
- `docs/roadmap/implementation-history.md`
- `docs/roadmap/implementation-roadmap.md`
- `docs/roadmap/runtime-market-events-discord-plan.md`
- `docs/roadmap/trading-quality-evidence-plan.md`

No replacement legacy archive is created. Git history and the recovery tags preserve point-in-time
inspection without leaving conflicting authority in the active tree.

## 6. Explicitly Protected Local State

Ignored and local state is outside both tracked PRs. The migration must not stage, expose, move, or
delete:

- root `.env`;
- root `.venv/` and `v2/.venv/`;
- `.idea/` and local run configurations;
- ignored root `config/market-data.btc.local.toml`;
- ignored `v2/config/system.local.toml` and `v2/.env`;
- root or V2 `data/`, including vendor exports, research data, databases, and logs; or
- caches, generated runtime output, secrets, and machine-specific configuration.

After PR 2 is merged, the operator recreates or selects the root environment and PyCharm
interpreter. Local configuration may be copied deliberately after comparing key names without
printing secret values. That local cutover is not Git content.

## 7. Recovery And Git History

The annotated tag `pre-v2-root-promotion-2026-09-02` identifies the exact master commit before
either migration PR. The earlier `v1-runtime-final` tag remains available for direct V1 inspection.
Normal Git ancestry also preserves every removed tracked file.

Neither PR deletes branches, tags, commits, worktrees, or remote refs. Any later ref cleanup is a
separate repository-hygiene decision and requires a fresh ref census, an external verified bundle
for unique tips, and explicit approval. History rewriting and force-pushing are out of scope.

Before either PR is merged, rollback is ordinary branch switching or discarding the uncommitted
review batch. After merge, rollback uses a normal revert commit; history is not rewritten.

## 8. PR 1 Verification

### 8.1 Tracked-tree result

The exact root V1 paths and deleted documents must be absent, while these remain present:

- `v2/pyproject.toml`
- `v2/uv.lock`
- `v2/src/markeitech/`
- `v2/tests/`
- `v2/config/`
- `v2/.env.example`
- `v2/compose.yaml`

### 8.2 Reference review

Search active tracked text for deleted paths and retired root entry points. Every remaining `v1`,
`-v1`, `schema_version = 1`, or “legacy” match must be classified as a current V2 version identity,
a current compatibility test, an external specification version, historical Git terminology, or a
defect. Do not allowlist entire files.

### 8.3 Offline code and documentation verification

At minimum:

```bash
uv run --project v2 ruff check v2/src v2/tests
uv run --project v2 pytest -q v2/tests -m "not postgres"
git diff --check
```

Also run focused locked tests for repository tools whose source/reference census changed. Regenerate
the complete system-dataflow artifact set only when its canonical manifest changes. Do not run
connected IB, Discord, operator PostgreSQL, or other external acceptance for unreachable-code and
documentation deletion.

Known baseline debt: at `553ad135`, the system-diagram static census rejects the non-literal
`METRIC_VALUE_TYPE_NAME` alias introduced by V3-03. PR 1 does not touch that runtime contract or the
canonical manifest. The failure must be reported, not repaired inside the retirement batch.

## 9. PR 2 Verification

PR 2 must prove the repository works from its root:

```bash
uv sync --locked --dev
uv run ruff check src tests
uv run pytest -q tests -m "not postgres"
git diff --check
```

It must additionally verify:

- no tracked path remains under `v2/`;
- no active command or tool assumes the old `v2/` prefix;
- package imports and CLI entry points work from the root environment;
- Compose configuration resolves from the root;
- CI, scripts, plugins, and PyCharm guidance use the root project;
- the locked API-documentation wrapper validates and generates successfully;
- system-dataflow generation and drift checks pass;
- Markdown links and referenced repository paths resolve;
- current authorities describe one root V2 project; and
- the diff contains no secret, local configuration, vendor data, runtime data, IDE state, or
  unrelated churn.

PostgreSQL-marked tests use only the established ephemeral test boundary when authorized by the
normal offline/CI workflow. Connected-provider acceptance is not required merely because paths
moved.

## 10. Risks And Controls

| Risk | Control |
|---|---|
| Deletion and path movement become too hard to review | Separate PR 1 retirement from PR 2 promotion |
| Valid `.v1` contract identities are renamed accidentally | Semantic reference review; no blind replacement |
| V1 behavior is silently reactivated | No capability migration in either PR |
| Secrets or local data become stageable | Preserve ignored state and inspect `git status --ignored` before ignore cleanup |
| Tooling still points at `v2/` after promotion | Atomic PR 2 path census across CI, scripts, tools, tests, docs, and plugins |
| Git recovery is weakened | Keep both annotated tags, refs, ancestry, and normal revert path |
| Structural migration grows into a redesign | No package rename, dependency update, schema change, or behavior change |
| Active V2 work changes during migration | Rebase/update census before each PR and rerun the full bounded verification |

## 11. Completion Criteria

### PR 1 is ready for review when

- [x] this accepted plan is tracked;
- [x] all exact PR 1 V1 paths are deleted;
- [x] active authorities and navigation have no dependency on a deleted document;
- [x] the nested V2 project remains fully usable;
- [x] V2 Ruff, all 616 non-PostgreSQL tests, and Kite structural tests pass;
- [x] the pre-existing system-diagram census failure is reproduced and documented without scope
      expansion;
- [x] protected ignored/local state is untouched;
- [x] the final deletion and modification diff is inspected; and
- [x] the complete batch is left uncommitted for Markeitect's review.

### The full migration is complete when

- [ ] PR 1 is reviewed, committed, pushed, merged, and its merge is verified;
- [ ] PR 2 promotes every V2 project surface to the root and removes the empty `v2/` directory;
- [ ] all root commands, CI, scripts, tools, plugins, documentation, and generated artifacts agree;
- [ ] root locked setup, lint, offline tests, documentation validation, and drift checks pass;
- [ ] local environment and PyCharm cutover is completed separately by the operator;
- [ ] the active tree contains one V2 runtime and no V1 project surface; and
- [ ] package rename, ref cleanup, and any future behavior work remain separate decisions.
