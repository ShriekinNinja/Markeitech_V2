# Markeitech Agent Entry Point

This repository contains the active Markeitech V2 runtime. The retired predecessor remains
recoverable through Git history and the recorded migration tags; it is not current source or
authority. Markeitect has final product, trading, architecture, review, and release authority.

The agent is expected to exercise senior engineering judgment, raise concerns early, and challenge
unsafe or weak assumptions with evidence. That independence supports Markeitect's decisions; it
does not replace them.

## Codex And Optional Kite Mode

A fresh Codex task starts in normal Codex mode. The installed or enabled Kite plugin is available,
not active. Do not invoke Kite, its router, a Kite specialist skill, or a Kite custom advisor unless
Markeitect explicitly selects the Kite plugin, invokes `$kite:markeitech-advisor-router`, or
explicitly invokes one named specialist skill. Direct specialist invocation is a narrow user
override; it does not activate Kite mode or count as router acceptance. Merely mentioning or
discussing Kite is not activation.

Explicit activation starts Kite mode for that task and its direct follow-ups. A new task or an
unrelated request returns to normal Codex mode unless Kite is explicitly invoked again. While Kite
mode is active, the plugin owns advisor selection and uses its smallest sufficient advisor set by
default; Markeitect does not need to name individual advisors.

Kite and its advisor council are development-time engineering collaborators. Sir Loke is the
accepted first V2 product experience but remains an unimplemented runtime advisory component.
Kite consultation does not create Sir Loke behavior, product semantics, tool authority, policy
acceptance, runtime readiness, or completed work. Sir Loke does not invoke or inherit authority
from the development-time Kite advisor council.

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

## Kite Advisor Consultation

The repository-owned Kite plugin packages specialist Markeitech advisors. Those advisors provide
evidence and recommendations; they do not override this file, tracked project authority, or
Markeitect's final decision.

This section applies only while Kite mode is active. Kite performs the advisor-coverage check
automatically after explicit activation. Select the smallest sufficient set: every selected role
must own one exact question whose answer can materially change the recommendation, edit,
acceptance result, or stop gate. Selection is evidence-bounded Kite judgment; dependency execution
becomes deterministic only after selected-role edges are recorded. Dependency tiers and adjacent
usefulness do not activate advisors. Consult each selected domain through its exact custom role
before planning or editing; do not use a specialist skill directly when that role exists unless
Markeitect explicitly invoked that skill. An explicit specialist invocation does not count as
router acceptance. Keep successful, unnecessary, and `NOT_NEEDED` routing silent unless a
consultation changes the recommendation, exposes material risk, or supplies useful evidence. If
coverage is missing, report the domain and proposed advisor briefly, then wait for Markeitect's
approval before creating it or making the consequential domain decision. Do not silently replace
missing or failed coverage with general engineering knowledge, and do not create advisors merely
to accumulate generic skills.

Advisor roles have a mandatory read-only consultation contract and declare a read-only sandbox
default. Effective tool isolation depends on the parent task's live permissions and requires
separate acceptance evidence; configuration or cooperative behavior alone is not proof of least
authority. Advisors never receive permission to edit, commit, connect services, consume paid
capacity, mutate data, or make a project decision.

While Kite mode is active, before a consequential NautilusTrader design, review, plan, or edit
involving actors, LiveNode, indicators, cache, persistence, catalog, message bus, market data,
adapters, lifecycle, concurrency, configuration, or framework alignment, delegate a narrow
read-only consultation to the project-scoped `markeitech_nautilus_advisor` custom agent. That
advisor must invoke the bundled `$kite:markeitech-nautilus-v2-expert` skill and complete its
native-capability gate and Nautilus Alignment Matrix before Kite recommends or implements custom
behavior. Kite remains responsible for validating the returned evidence against tracked authority
and the current checkout.

If a required advisor is unavailable, stale, or cannot inspect its required sources, report that
limitation and stop before the consequential decision or edit. Do not silently substitute memory,
stable-channel documentation, or the current custom implementation for the required consultation.
Invoking an advisor never grants permission to edit, commit, connect services, mutate data, or
perform another restricted action.

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
- Markeitect normally owns connected acceptance runs. Do not consume time, market-data capacity,
  paid credits, or external quotas with redundant probes when logs or deterministic tests suffice.
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
- Anything reasonably variable must be typed, bounded, versioned configuration and ready for
  policy-controlled optimization. Do not hide tunable behavior in constants.
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

A batch is not complete until its implementation and documentation agree, focused verification
passes, broader verification is proportional to risk, `git diff --check` is clean, and untested or
deferred acceptance is stated honestly. Before presenting work for review:

1. inspect the final diff and worktree for accidental files, secrets, data, or unrelated churn;
2. verify local configuration and IDE state were not overwritten;
3. confirm no connected or destructive action occurred without approval;
4. summarize what changed, what was verified, and what remains unknown; and
5. commit only the scoped files, push the change branch, open or update its PR, and report its
   exact head and CI status while leaving it unmerged for Markeitect; if an explicit task
   restriction prevents publication, preserve the work and state the remaining gate.

See `CONTRIBUTING.md` and `docs/operations/github-workflow.md` for the branch, PR review, CI, and
Markeitect-owned merge process.
