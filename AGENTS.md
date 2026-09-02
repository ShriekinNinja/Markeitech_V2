# Markeitech Agent Entry Point

This repository contains the active Markeitech V2 runtime and preserved V1 source. Markeitect has
final product, trading, architecture, review, and release authority.

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

Kite and its advisor council are development-time engineering collaborators. Sir Loke is a future
V2 runtime advisory component. Kite consultation does not create Sir Loke behavior, product
semantics, tool authority, policy acceptance, runtime readiness, or completed work. Sir Loke does
not invoke or inherit authority from the development-time Kite advisor council.

## Authority And Precedence

- System and platform instructions remain binding.
- Markeitect's newest explicit instruction governs the current task and supersedes older project
  preferences when they conflict.
- `markeitech.md` governs durable product and engineering principles.
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
2. `docs/current-status.md`
3. `docs/development-guidelines.md`
4. `docs/README.md`
5. the accepted architecture, roadmap, and operations documents relevant to the requested stage

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
- Commit the previously reviewed batch before beginning a separately approved batch.
- Leave each new batch uncommitted for Markeitect's local review.
- Commit only after explicit approval, with a detailed message.
- Use stage-specific branches without a `codex/` prefix. Push, open a PR, merge, or delete a branch
  only when that integration step is approved. Never force-push.
- Pull requests are an external integration record, not a substitute for local review. Every PR
  must describe scope, contracts, data/persistence effects, validation, live acceptance, and known
  debt in detail.
- Do not run connected IB, Discord, database-destructive, or execution paths unless Markeitect
  explicitly authorizes that exact run. Offline tests are allowed when relevant.
- Markeitect normally owns connected acceptance runs. Do not consume time, market-data capacity,
  paid credits, or external quotas with redundant probes when logs or deterministic tests suffice.
- Never commit secrets, local configuration, `.idea/`, vendor exports, raw market data, runtime
  logs, database dumps, or licensed data.
- Never delete preserved V1 source, notes, instructions, research, or archives without a separately
  reviewed migration and recovery point.
- Work with existing user changes. Do not reset, revert, or overwrite unrelated work.
- Do not update packages, lockfiles, containers, databases, GitHub metadata, or third-party
  services as incidental cleanup.

Delegated agents operate under the same boundaries. Give them narrow, explicit scopes; do not give
them authority to push, commit, run connected services, modify databases, or make architecture
decisions. The primary agent remains responsible for reviewing their evidence and every integrated
change.

## Engineering Invariants

- V2 is live-first, event-driven, read-only, and advisory. It does not place orders.
- Independent actors and unrelated capabilities must continue operating through partial failure;
  recovery is bounded, observable, and continuously retried where policy permits.
- Use NautilusTrader native contracts and bus semantics where they fit; keep one owner for every
  provider subscription and canonical stream.
- Preserve evidence fidelity, lineage, UTC internal time, explicit contract identity, bounded
  resources, typed contracts, and durable operational audit.
- Do not reactivate V1 analytics, signals, thresholds, or one-active-instrument assumptions.
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
- Do not run bare `mkdocs` or `mkdocstrings` commands. Provision with the locked tool project and
  invoke only the first-party `markeitech_api_docs validate` or `generate` wrapper documented in
  `docs/operations/v2-api-documentation.md`.
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
- The existing system-diagram tool continues to consume `docs/architecture/system-dataflow.toml`
  during the migration interval. A future, separately reviewed exporter may make validated source
  documentation upstream of generated TOML and diagrams; until it exists, do not declare the TOML
  generated or remove its maintenance procedure.
- Generated `docs/api` and `tools/api-docs/.build` content is untracked and must not be hand-edited.
  Commit source/configuration/registries/tests/lockfiles, then regenerate locally or in approved CI.

## Completion Standard

A batch is not complete until its implementation and documentation agree, focused verification
passes, broader verification is proportional to risk, `git diff --check` is clean, and untested or
deferred acceptance is stated honestly. Before presenting work for review:

1. inspect the final diff and worktree for accidental files, secrets, data, or unrelated churn;
2. verify local configuration and IDE state were not overwritten;
3. confirm no connected or destructive action occurred without approval;
4. summarize what changed, what was verified, and what remains unknown; and
5. leave the batch uncommitted for Markeitect unless approval to commit was already explicit for
   that completed diff.

See `CONTRIBUTING.md` and `docs/operations/github-workflow.md` for the local review, commit, PR, CI,
and merge process.
