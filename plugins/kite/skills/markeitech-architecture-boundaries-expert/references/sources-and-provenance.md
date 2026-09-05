# Sources And Provenance

Last researched: 2026-08-25.

This reference records foundations for the advisor, not architecture authority for Markeitech.
Tracked repository authority and current implementation evidence take precedence. External
material is paraphrased; no external skill text or code is copied into this proprietary plugin.

## Repository Source Census

| Source | Role in this skill |
|---|---|
| `AGENTS.md` | Authority order, advisor routing, permissions, evidence bar, and completion gates. |
| `markeitech.md` | Durable ownership, canonical stream, configuration, persistence, and product invariants. |
| `docs/current-status.md` | Current implemented owners, accepted evidence, deferred work, and validation debt. |
| `docs/development-guidelines.md` | Runtime ownership, transport-neutral analytics, configuration, and review discipline. |
| `docs/README.md` | Documentation precedence and current-versus-historical classification. |
| `docs/architecture/runtime-foundation.md` | Native messaging, composition, system control, persistence, projection, failure, and bounded-work boundaries. |
| `docs/architecture/market-data-and-acquisition.md` | Native provider transport, demand ownership, watchlist, and historical execution boundaries. |
| `docs/architecture/session-evidence-health.md` | Calendar/session ownership and evidence-health semantics. |
| `docs/architecture/deterministic-evidence-contracts.md` | Completed-bar, measurement, entity, identity, health, and fidelity boundaries. |
| `docs/architecture/sir-loke-v1-boundaries.md` | Future Sir Loke ownership, request, tool, and side-effect boundaries. |
| `docs/roadmap/sir-loke-v1-delivery-plan.md` | Canonical future product gates and scoped reliability requirements. |
| `plugins/kite/skills/markeitech-advisor-router/references/advisor-design.md` | Minimum specialist contract and evidence/permission expectations. |
| `plugins/kite/skills/markeitech-nautilus-v2-expert/` | Nautilus-specific contract to which this advisor defers. |

## Authoritative And Institutional Sources

| Source | Accessed | Adopted idea | Limits or compatibility concern |
|---|---:|---|---|
| [ISO/IEC/IEEE 42010:2022](https://www.iso.org/standard/74393.html) | 2026-08-25 | Architecture descriptions organize stakeholder concerns through explicit concepts, relationships, viewpoints, and model kinds; the description is distinct from the architecture itself. | The full standard is copyrighted and not reproduced. It does not prescribe Markeitech's method or architecture. |
| [CMU SEI Architecture Tradeoff Analysis Method](https://www.sei.cmu.edu/library/the-architecture-tradeoff-analysis-method/) | 2026-08-25 | Evaluate architectural choices against explicit scenarios and competing quality goals; expose risks, sensitivity points, and tradeoffs. | Full formal ATAM workshops are disproportionate for ordinary repository reviews. This skill adopts scenario and tradeoff reasoning, not ATAM certification or ceremony. |
| [AWS Prescriptive Guidance: ADR process](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html) | 2026-08-25 | Significant choices need context, decision, consequences, ownership, lifecycle, and supersession rather than silent rewriting. | Markeitech's tracked authority governs its decision-record process; the advisor never writes or accepts an ADR without scope and approval. |
| [Microsoft: Data sovereignty per microservice](https://learn.microsoft.com/en-us/dotnet/architecture/microservices/architect-microservice-container-applications/data-sovereignty-per-microservice) | 2026-08-25 | A bounded component owns its domain data and logic; other contexts integrate through explicit interfaces rather than shared mutation. | Markeitech is not presumed to be microservices. Logical ownership applies without requiring separate processes or databases. |
| [Martin Fowler: Bounded Context](https://martinfowler.com/bliki/BoundedContext.html) | 2026-08-25 | Canonical models are context-scoped and relationships between contexts must be explicit. | Secondary practitioner source; used for vocabulary, not as a mandate to adopt DDD or new services. |
| [Martin Fowler: Integration Database](https://martinfowler.com/bliki/IntegrationDatabase.html) | 2026-08-25 | Shared schemas can create deep coupling and increased change coordination. | A shared database is not automatically wrong; Markeitech's accepted PostgreSQL boundary and actual mutation ownership control the decision. |

## Public Skill Census

### `paulpas/agent-skill-router`: `architectural-review`

- URL: [skill](https://github.com/paulpas/agent-skill-router/blob/9185de8e1ef4505e4c64ecb3411cf4dd2197965c/skills/coding/architectural-review/SKILL.md)
- Skill commit: `9185de8e1ef4505e4c64ecb3411cf4dd2197965c` (2026-06-04).
- Repository head inspected: `03735f82d38538c0a7ba34a6056fa8e5e3704be8`.
- License: MIT, repository `LICENSE` with SPDX identifier.
- Adopted: explicit separation of observed evidence, derived assessment, and recommendation;
  prioritize by impact and change cost; show confidence and concrete evidence.
- Rejected: mandatory static metrics, fixed numeric smell thresholds, universal two-signal rules,
  required stakeholder counts/sign-off, and generated analyzer code. They do not establish
  Markeitech ownership and could manufacture false precision.
- Compatibility: OpenCode-oriented metadata and generic audit assumptions do not match Codex or
  Markeitech permissions. No text or code was copied.

### `45ck/software-architecture-skills`

- URL: [repository](https://github.com/45ck/software-architecture-skills/tree/14966b2ccf3df92d37d73a1862699e5aa3f1f652)
- Commit: `14966b2ccf3df92d37d73a1862699e5aa3f1f652` (2026-04-11).
- License: MIT.
- Skills inspected: `component-boundary-reviewer`, `integration-boundary-mapper`,
  `architecture-risk-assessor`, and `tradeoff-analysis-writer`.
- Adopted: map responsibilities, contracts, data movement, dependencies, uncertainty, change
  scenarios, risks, and competing options; keep evidence, inference, and recommendation separate.
- Rejected: generic handoff chains and identical one-size-fits-all procedures. Markeitech uses its
  repository-owned advisor router and explicit authority gates.
- Compatibility: portable Agent Skills layout, but its extra frontmatter is not used. No text was
  copied.

### `proflead/codex-skills-library`: `architecture-review`

- URL: [skill](https://github.com/proflead/codex-skills-library/blob/763f731147ea65674e93b9375bda930ad31ad21c/skills/architecture/architecture-review/SKILL.md)
- Skill commit: `763f731147ea65674e93b9375bda930ad31ad21c` (2026-01-12).
- Repository head inspected: `a05260c8832b11054b0cc311b51e0fd1afb1a62a`.
- License: no repository or skill license found during the 2026-08-25 census.
- Adopted: none from the skill text because licensing was not established.
- Rejected: its scope is too generic to detect duplicate authority, persistence drift, or
  Nautilus overlap.
- Compatibility: frontmatter is structurally close to Codex, but legal reuse is unclear.

### `oimiragieo/agent-studio`: Claude `architecture-review`

- URL: [skill](https://github.com/oimiragieo/agent-studio/blob/406628a513993fbc92c097db4a2b11522bdf8675/.claude/skills/architecture-review/SKILL.md)
- Skill commit: `406628a513993fbc92c097db4a2b11522bdf8675` (2026-04-21).
- Repository head inspected: `64b580eab27ba37673f042ecc12ac53413cd9dd5`.
- License: no repository or skill license found during the 2026-08-25 census.
- Adopted: none from the skill text because licensing was not established.
- Rejected: unsupported universal cost multipliers, generic "iron laws," mandatory memory writes,
  Claude-specific tool/model metadata, and automatic event-bus or service prescriptions.
- Compatibility: Claude-specific schema and mutation workflow conflict with this read-only custom
  advisor and repository write gates.

### Official skill-authoring conventions

- OpenAI Codex skill creator: [commit `4ab6e0fd99c6667163bc34173e3ed3a3fed75ebc`](https://github.com/openai/skills/blob/4ab6e0fd99c6667163bc34173e3ed3a3fed75ebc/skills/.system/skill-creator/SKILL.md), Apache-2.0 license in the skill directory.
- Anthropic skill creator: [commit `b0cbd3df1533b396d281a6886d5132f623393a9c`](https://github.com/anthropics/skills/blob/b0cbd3df1533b396d281a6886d5132f623393a9c/skills/skill-creator/SKILL.md), Apache-2.0 license in the skill directory.
- Adopted: concise discoverable frontmatter, progressive disclosure, supporting references only
  when they change decisions, and validation of the completed package.
- Rejected: packaging, installation, and generic examples not needed by this repository-owned
  candidate. Cross-advisor routing expectations and installed acceptance debt are recorded in
  [routing-evaluation.md](routing-evaluation.md).
- Compatibility: the local installed Codex skill-creator instructions govern this candidate. No
  external authoring text was copied.

## Maintenance Rule

Refresh URLs, commits, licenses, and factual claims before materially revising the advisor from an
external source. Record new adoption and rejection decisions here. Never import unlicensed or
incompatible material merely because it appears in a public repository.
