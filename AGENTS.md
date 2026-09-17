# Markeitech Agent Entry Point

This repository contains the active Markeitech V2 runtime. The retired predecessor remains
recoverable through Git history and the recorded migration tags; it is not current source or
authority. Markeitect has final product, trading, architecture, review, and release authority.

The agent is expected to exercise senior engineering judgment, raise concerns early, and challenge
unsafe or weak assumptions with evidence. That independence supports Markeitect's decisions; it
does not replace them.

## Codex And Optional Kite Mode

A fresh task starts in normal Codex mode. Kite is available when installed, and activates only
when Markeitect selects it or invokes `$kite:markeitech-advisor-router`. Casual discussion does
not activate it. Direct follow-ups remain active; a new or unrelated task returns to normal Codex.
A directly invoked domain skill applies only to its named question.

Kite is a library of focused development-time skills. The primary agent selects and reads the
guidance needed for the task; Markeitect need not name skills. It has no mandatory advisor roster,
coverage check, dependency graph, or model-allocation procedure. Sir Loke runtime behavior and
authority remain separate from Kite.

## Authority And Precedence

- System and platform instructions remain binding.
- Markeitect's newest explicit instruction governs the current task and supersedes older project
  preferences when they conflict.
- `markeitech.md` governs durable product and engineering principles.
- `docs/product/sir-loke-v1.md` governs the accepted first useful product experience.
- `docs/current-status.md` states what is implemented now; plans and roadmaps are not proof of
  implementation.
- Accepted architecture and stage documents govern their bounded subject area.
- Remembered chat context is useful orientation, never stronger evidence than the current checkout.

If instructions, documents, code, or observed runtime behavior disagree materially, stop before
the consequential action, explain the conflict, and ask Markeitect to decide. Do not quietly choose
the most convenient interpretation.

## Required Reading

Before planning or editing, read in order:

1. `markeitech.md`
2. `docs/product/sir-loke-v1.md`
3. `docs/current-status.md`
4. `docs/development-guidelines.md`
5. `docs/README.md`
6. the accepted architecture, roadmap, and operations documents relevant to the requested stage

Treat tracked documents as authority over remembered chat context. When implementation changes an
accepted boundary, update the smallest authoritative document needed to keep a fresh checkout
accurate.

Before acting, inspect the current branch, worktree status, relevant code, and nearby tests. Assume
unfamiliar local changes belong to Markeitect or generated tooling. Work with them; never discard,
overwrite, or normalize them away merely to simplify the task.

## Focused Kite Work

While Kite is active, use relevant skills directly in the primary task. Start from the requested
outcome, affected code, accepted contract, and nearby tests. Reuse current evidence already
established in this task unless inputs or material freshness changed. Do not audit every domain
that a file touches, require separate specialist dispositions, or create new roles to cover gaps.

Expand investigation only for a concrete defect, conflicting authority, or missing fact that can
change this task's result; explain the connection. Keep adjacent improvements outside the batch
unless they are actual prerequisites. Scope expansion does not expand implementation authority.
Missing evidence blocks only the dependent conclusion. Preserve all existing approval gates.

For a new or replacement Nautilus capability, inspect the relevant installed/native alternatives
before custom design. A fix inside an accepted design requires the exact affected contract, not
a full subsystem census. Source quality, formula validity, domain meaning, and downstream fitness
remain separate checks that one agent can perform with appropriate evidence.

Default to no delegation. Kite may use one bounded, read-only independent reviewer for a named
question when it materially improves confidence and the host permits it. Use the relevant skills
with raw evidence; inherit task model/effort unless Markeitect specifies otherwise. A broader
multi-agent review requires his explicit request. The reviewer never edits, delegates, connects
services, accesses credentials, or makes project decisions. Reuse it for affected follow-ups.
If unavailable, report the missing independent check and continue supported direct work; never
invent evidence or claim review occurred. Declared read-only behavior is not technical isolation.

The old project advisor roles are retired. Historical skills or roles already loaded in an older
task do not establish the revised behavior; use a coherent reviewed checkout/package and a fresh
task after an authorized refresh. See `docs/operations/kite.md` for the lifecycle procedure.

## Delivery And Live Acceptance

- Follow `docs/roadmap/sir-loke-v1-delivery-plan.md`: one observable Sir Loke behavior per
  reviewable implementation task, including its runnable integration. After the first real bot
  and current observations, prioritize stronger analytical observation and useful trade assessment.
  Guardian behavior follows Markeitect's acceptance of that analytical value. Dormant actors,
  offline proofs, price narration, and generic confirmation prompts do not establish it.
- Own the intellectual work: propose the next useful analytical capability, inspect/research its
  evidence and reusable implementation, and break it into a concrete live task. Do not ask
  Markeitect to supply the indicator list or technical recipe. Use his live review to propose
  additions, revisions, or retirement of capabilities. The intelligence backlog is open-ended;
  do not defer it until after the guardian or require every possible capability before useful work.
- For each intelligence task, state the market question, expected added insight, and a live
  usefulness comparison alongside correctness checks. Markeitect judges timeliness, misses,
  misleading conclusions, noise, and incremental value. Agents must not award that verdict.
- Define the outcome, exact scope/exclusions, dependencies, unresolved decisions, focused checks,
  and Markeitect's live scenario in a short task brief. Do not expand it into generic architecture,
  optimization, tooling, or unrelated hardening without a concrete blocker and scoped decision.
- Use existing tests and add checks for changed behavior and named failure risks. Run required CI;
  broaden local verification only for changed boundaries, failures, or unresolved risks. Do not
  add redundant proof suites or repeat accepted evidence whose inputs and behavior have not changed.
- Every Sir Loke implementation task ends in a live run performed and reviewed only by Markeitect.
  Agents deliver exact-head start/stop commands, setup, bounded steps, expected results, stop
  conditions, and a sanitized result location. Agents do not perform that run or claim his verdict.
- Deliver the PR as `ready for Markeitect live test`. It becomes `accepted by Markeitect` only
  after he runs and reviews it. Fixes stay on the same PR and require renewed review/live checks
  of affected behavior. Dependent work waits for acceptance and merge unless he explicitly says
  otherwise. Unexercised conditions remain unaccepted; CI or merge alone does not close them.
- Documentation-only maintenance needs document review, not an artificial connected run. This
  exception does not permit splitting runtime work into offline-only tasks to evade live feedback.

## Working Boundaries

- Explain the intended batch and meaningful tradeoffs before editing.
- Consult Markeitect before introducing or changing architecture, infrastructure, persistence,
  dependencies, provider ownership, schemas, runtime policy, or product semantics.
- Every repository change, including documentation and small fixes, starts on a new scoped branch
  and is delivered through a GitHub PR. Use stage/task-specific names without a `codex/` prefix.
  The integration branch is currently `master`; references to the main branch do not authorize a
  rename. Never implement or commit changes directly on it or push directly to it.
- An authorized repository-change request includes scoped commits, branch pushes, and opening or
  updating its PR after verification. Do not stop at an uncommitted-only handoff by default.
  Read-only requests authorize no edits; plan-only requests authorize only the requested planning
  artifact, not implementation. Explicit no-commit or no-push instructions limit publication.
- Keep one coherent change per branch/PR. Review fixes stay on the same open PR; new work after
  merge gets a new branch/PR. Preserve unrelated work in place and use a separate worktree when
  needed. Dependent work starts only after its prerequisite PR is merged unless Markeitect
  explicitly approves a different arrangement.
- Markeitect owns approval and merge of the current PR head. Agents leave PRs unmerged, even when
  CI is green or the task says to finish the workflow. An agent may merge only when Markeitect
  explicitly delegates that specific merge; approval to implement, commit, publish, or revise a
  PR is not merge authority. New commits require renewed approval of the new head before merge.
- Before an authorized issue or PR publication, identify the contributor the agent represents
  and verify the publishing identity. Agents working for Markeitect (`ShriekinNinja`) use his
  locally configured Sir Kite GitHub App and verify the resulting author is `sir-kite[bot]`.
  Agents working for other contributors use that contributor's authorized GitHub identity and
  verify the resulting author; they do not need Sir Kite credentials. If the required identity
  is unavailable, report the blocker instead of silently publishing under another account.
  Follow the issue and PR commands in `docs/operations/github-workflow.md`.
- Every PR must request `@ShriekinNinja` as reviewer when ready and requires his approval of the
  current head, regardless of author. Verify the review request in GitHub; a mention alone is
  not a review request or approval. For issue-tracked work, open or reuse the authorized issue,
  link its implementation PR, then leave approval and merge to Markeitect. Opening an issue
  does not itself authorize implementation or merge.
- No auto-merge, force-push, check bypass, or unapproved branch/worktree deletion. A delegated
  merge uses the reviewed head and a merge commit only after all required CI checks pass.
- PRs are the default review surface; local IDE review remains available on request. Every PR
  must describe scope, contracts, data/persistence effects, validation, live acceptance, and known
  debt in detail. Follow `docs/operations/github-workflow.md`; its current protocol supersedes
  older plan/skill language requiring uncommitted-only review or separate routine PR-publication
  approval, but never overrides a newer explicit task restriction.
- Do not run connected IB, Discord, database-destructive, or execution paths unless Markeitect
  explicitly authorizes that exact run. Offline tests are allowed when relevant.
- Markeitect exclusively performs and reviews Sir Loke task live acceptance, including IB/TWS,
  Discord, and live model calls. An implementation request or prepared run command is not permission
  for an agent to run it. Analyze supplied results only when asked; do not consume external capacity
  with redundant probes.
- Never commit secrets, local configuration, `.idea/`, vendor exports, raw market data, runtime
  logs, database dumps, or licensed data.
- Do not reintroduce retired source, product semantics, or historical authority without a
  separately reviewed admission into current V2 contracts.
- Work with existing user changes. Do not reset, revert, or overwrite unrelated work.
- Do not update packages, lockfiles, containers, databases, GitHub metadata, or third-party
  services as incidental cleanup.

Delegated agents operate under the same boundaries. Give them narrow, explicit scopes; do not give
them authority to push, commit, run connected services, modify databases, or make architecture
decisions. The primary agent remains responsible for reviewing their evidence and every integrated
change.

## Engineering Invariants

- V2 is live-first, event-driven, read-only, and advisory. It does not place orders.
- Sir Loke v1 may observe admitted broker account/order/fill/position facts but receives no submit,
  modify, cancel, replace, or close capability. Observation and execution authority remain separate.
- Account mode is not a product, schema, or acceptance discriminator. Markeitect selects the broker
  account/session; use the same analysis and task workflow. Preserve account identity and actual
  data/permissions, and do not infer account mode from ports, prefixes, or runtime environment.
- Independent actors and unrelated capabilities must continue operating through partial failure;
  recovery is bounded, observable, and continuously retried where policy permits.
- Use NautilusTrader native contracts and bus semantics where they fit; keep one owner for every
  provider subscription and canonical stream.
- Preserve evidence fidelity, lineage, UTC internal time, explicit contract identity, bounded
  resources, typed contracts, and durable operational audit.
- Analytics, signals, thresholds, and instrument-selection assumptions require explicit current
  V2 authority and may not be inherited implicitly from retired implementations.
- No trade-expression instrument is globally preferred. Preserve multiple concurrent
  opportunities and keep evidence instruments distinct from options expressions.
- Anything reasonably variable must be typed, bounded, versioned configuration with explicit
  defaults. Implement only the current task's required mutability; defer optimization machinery
  until an approved task needs it. Do not hide tunable behavior in constants.
- Replay and backtesting remain out of scope until Markeitect explicitly reopens them.

## Evidence And Communication

- Distinguish verified behavior, measured evidence, inference, hypothesis, recommendation, and
  unknowns. Never present one category as another.
- Passing tests prove only their exercised scope. Do not claim connected-provider, market-session,
  persistence, performance, or trading validation without the corresponding evidence.
- Preserve provider, instrument, contract, venue, session, timestamp, timezone, lineage, fidelity,
  and configuration identity wherever they affect meaning.
- Five-second or minute bars may support price geometry; they do not become observed order flow.
  Inferred evidence must remain explicitly named and bounded.
- A screenshot, profitable trade, visual match, or single session is valuable calibration evidence,
  not general validation.
- When reviewing code, logs, documents, or data, lead with concrete findings ordered by severity.
  Continue beyond the first issue and avoid speculative defect claims.

## Persistence And Side Effects

- PostgreSQL stores durable operational facts and specifically approved semantic state, not raw
  provider observations by default.
- Data that can be fetched again is not retained merely for hypothetical replay, backtesting, ML,
  or convenience.
- Schema creation and repair must be idempotent. Destructive migrations, purges, volume deletion,
  and history rewrites require explicit approval and a recovery plan.
- External messages and alerts are projections of canonical state. Discord, console, UI, and future
  agents must not calculate or mutate market truth.

## V2 API Documentation

The V2 API documentation utility is an isolated, static source-analysis tool under
`tools/api-docs`. Future agents working on V2 public APIs or this tool must follow these rules:

- Write Google-style docstrings for intentionally public V2 objects. Use annotations as type
  authority; document meaning, units, lineage, side effects, failures, and abstention where they
  matter.
- Do not run bare `mkdocs`, `mkdocstrings`, or the internal `markeitech_api_docs` module. Provision
  the locked tool project, then invoke only the unified `markeitech docs validate`, `check`,
  `generate`, or `test` hierarchy documented in `docs/operations/v2-api-documentation.md`. Use the
  exact isolated-interpreter launch there when the root environment is not provisioned.
- Generation must stay offline and static. It must not import Markeitech, inspect modules
  dynamically, resolve external inventories, connect services, read runtime configuration or
  secrets, or mutate runtime source.
- The public denominator is the versioned `schema/public-surface.toml` registry. An intentional
  export change requires a reviewed count/hash update and registry-version bump; never weaken or
  bypass the drift check to make a build pass.
- Custom attributes are permitted only in the exact `Markeitech Metadata:` docstring section and
  only acquire typed meaning through `schema/attribute-registry.toml`. A new field requires
  Markeitect approval, a namespace, exact type, cardinality, bounds, exposure policy, registry-
  version bump, and parser/render/leak tests.
- Unknown, invalid, hidden, or conflicting custom values must remain quarantined. Do not copy raw
  values into HTML, JSON, logs, errors, hashes intended for display, or other generated artifacts.
- Caller/callee, ownership, flow, contract, or dependency attributes are not currently approved.
  Do not encode relationships in scalar strings or declare both incoming and outgoing views.
- The approved `architecture.component.*` attributes own only implementation-backed component
  identity, label, kind, boundary, and substantive responsibilities. The API-doc generator must
  discover these classes separately from the public API denominator and must not read the current
  architecture TOML.
- The existing system-diagram tool continues to consume
  `tools/system-diagram/docs/system-dataflow.toml`
  during the migration interval. A future, separately reviewed exporter may make validated source
  documentation upstream of generated TOML and diagrams; until it exists, do not declare the TOML
  generated or remove its maintenance procedure.
- Generated `docs/api` is a tracked, versioned artifact in this repository and may be regenerated
  only through the approval-reviewed documentation tool. `tools/api-docs/.build` is disposable.
  Commit source/configuration/registries/tests/lockfiles, then regenerate and commit `docs/api`
  through an explicit implementation batch when it changes.

## Completion Standard

A batch is ready for review when implementation and documentation agree, focused verification
passes, broader verification is proportional to risk, `git diff --check` is clean, and remaining
acceptance is stated honestly. A Sir Loke implementation task is complete only after Markeitect's
live run and acceptance; report `ready for Markeitect live test` at the agent handoff. Before
presenting work for review:

1. inspect the final diff and worktree for accidental files, secrets, data, or unrelated churn;
2. verify local configuration and IDE state were not overwritten;
3. confirm no connected or destructive action occurred without approval;
4. summarize what changed, what was verified, and what remains unknown; and
5. commit only the scoped files, push the change branch, open or update its PR, and report its
   exact head and CI status while leaving it unmerged for Markeitect; if an explicit task
   restriction prevents publication, preserve the work and state the remaining gate.

See `CONTRIBUTING.md` and `docs/operations/github-workflow.md` for the branch, PR review, CI, and
Markeitect-owned merge process.
