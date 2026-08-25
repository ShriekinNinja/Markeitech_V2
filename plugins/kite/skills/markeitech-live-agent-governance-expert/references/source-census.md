# Source And Public-Skill Census

**Research access date:** 2026-08-25

Use this as a provenance record and research starting point, not as frozen truth. Refresh sources
whose contracts or guidance can drift before a consequential consultation. Repository authorities
outrank external patterns for Markeitech product decisions.

## Tracked Markeitech Authority Inspected

- `AGENTS.md`: collaboration, permissions, advisor, evidence, and completion authority.
- `markeitech.md`: Sir Loke maxim; evidence honesty; typed policy-checked intents; read-only,
  advisory, no-provider, no-execution, and configuration/optimization boundaries.
- `docs/current-status.md`: Sir Loke, agent tools, options intelligence, and semantic events remain
  future work as of 2026-08-25.
- `docs/development-guidelines.md`: deterministic truth, typed intents, provider ownership,
  evidence lineage, and no-execution boundaries.
- `docs/README.md`: documentation authority order.
- `docs/roadmap/v2-market-events-live-agent-plan.md`: accepted destination for the read model,
  policy/resource governor, tools, bounded options/data requests, audit, state, abstention, Stage
  9I, and no-execution boundary.
- `docs/research/semantic-events-ai-options-baseline.md`: informative historical research only; no
  proposed schema, score, or confidence range was promoted into this skill.
- Current Kite advisor/router conventions reviewed in the integrated
  `v2-nautilus-audit-alignment` catalog at commit `74f47f4`, including the architecture-boundaries,
  evidence-visualization, Interactive Brokers market-data, data-quality-and-lineage,
  quantitative-metric-validation, evidence-fitness, market-structure, options-and-0DTE,
  zero-DTE-risk, PostgreSQL-persistence, NautilusTrader, Python-runtime, and
  statistical-learning-and-optimization advisors. The candidate originated from
  foundation commit `c6af7a5`; integration preserved the newer suite.

## Current Primary And Institutional Sources

| Source | Version/date | Governance evidence used | Limits and compatibility |
|---|---|---|---|
| [OpenAI Agents SDK: Human-in-the-loop](https://openai.github.io/openai-agents-python/human_in_the_loop/) | Accessed 2026-08-25; live docs | Sensitive tools can pause before execution; approval is tied to a surfaced interruption; malformed approval arguments fail toward manual review. | SDK behavior is an implementation option, not Markeitech policy or proof of its future runtime. No OpenAI/runtime configuration was changed. |
| [OpenAI Agents SDK: Guardrails](https://openai.github.io/openai-agents-python/guardrails/) | Accessed 2026-08-25; live docs | Tool guardrails apply at each custom function-tool boundary; blocking checks are required when side effects must not start first. | Agent input/output guardrails alone do not cover every delegated/tool path. Prompt/guardrail logic cannot replace deterministic policy. |
| [OpenAI Agents SDK: Tracing](https://openai.github.io/openai-agents-python/tracing/) | Accessed 2026-08-25; live docs | End-to-end traces can include generations, tool calls, handoffs, guardrails, and custom events. Sensitive-data capture and ZDR limitations require explicit design. | Trace availability/retention is provider-specific and is not canonical Markeitech state. Defaults may drift; refresh before implementation. |
| [NIST AI 600-1, Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) | NIST AI 600-1, July 2024 | Governance, content provenance, pre-deployment testing, incident disclosure, source verification, and documented human oversight support auditable lifecycle controls. | Voluntary cross-sector guidance, not a product schema or certification. Applied as risk-management evidence only. |
| [NIST: Lessons Learned, Tool Use in Agent Systems](https://www.nist.gov/news-events/news/2025/08/lessons-learned-consortium-tool-use-agent-systems) | 2025-08-05 | Constrained tool-access patterns and capability transparency support classifying tools by environment, authority, and effect. | Summary of consortium work, not a normative standard or Markeitech implementation contract. |
| [NIST NCCoE concept paper: Software and AI Agent Identity and Authorization](https://csrc.nist.gov/pubs/other/2026/02/05/accelerating-the-adoption-of-software-and-ai-agent/ipd) | Initial public draft, 2026-02-05 | Agent identity and authorization must be explicit when agents access diverse tools/data. | Draft concept paper; do not treat as finalized control requirements. Security implementation remains specialist-owned. |
| [MCP Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization) | Protocol 2025-11-25 | Least-privilege scopes, resource/audience binding, token validation, and separate authorization context support non-transitive authority. | Transport authorization does not decide Markeitech business policy, tool-argument safety, or human approval. Sir Loke is not assumed to use MCP. |
| [MCP Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) | Protocol 2025-11-25 | Closed input schemas, validation, access control, rate limits, output sanitization, timeouts, sensitive-operation confirmation, and audit logging are useful boundary requirements. Tool annotations are untrusted unless the server is trusted. | Protocol guidance is not a substitute for deterministic Markeitech ownership or policy. Tool results remain untrusted data. |
| [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) and [Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/) | 2026 edition / 2025 risk entry | Tool misuse, identity/privilege abuse, goal hijacking, excessive functionality/permissions/autonomy, and downstream user-context authorization motivate least authority and containment. | Community security guidance, not a formal standard; detailed security design requires independent specialist review. |
| [AgentDojo](https://proceedings.neurips.cc/paper_files/paper/2024/file/97091a5177d8dc64b1da8bf3e1f6fb54-Paper-Datasets_and_Benchmarks_Track.pdf) | NeurIPS 2024 Datasets and Benchmarks | Peer-reviewed evidence that untrusted tool data can inject instructions and cause unauthorized tool actions; supports adversarial offline fixtures and separating data from authority. | Benchmark domains/models differ from Markeitech; it demonstrates a risk class, not the effectiveness of a specific defense here. |
| [ToolEmu](https://arxiv.org/abs/2309.15817) | arXiv:2309.15817, 2023 | Emulated high-stakes tool testing supports failure-oriented, offline evaluation before live tool access. | Research emulator results do not prove production safety; no figures or code were copied. |

## Public Codex, Claude, And Agent-Skill Census

External material was used for patterns only. No external skill text, scripts, runtime dependency,
or configuration was copied.

| Repository and inspected artifact | Snapshot | License status | Adopted ideas | Rejected ideas / compatibility concerns |
|---|---|---|---|---|
| [openai/skills `skill-creator`](https://github.com/openai/skills/tree/49f948faa9258a0c61caceaf225e179651397431/skills/.system/skill-creator) | `49f948faa9258a0c61caceaf225e179651397431` | Per-skill Apache-2.0 `LICENSE.txt` | Discriminating frontmatter, progressive disclosure, focused references, deterministic validation. | Generic skill scaffolding is not governance expertise; no instructions were copied. Repository README marks this catalog deprecated in favor of plugins, so it is not an integration target. |
| [openai/plugins `agents-sdk`](https://github.com/openai/plugins/tree/11c74d6ba24d3a6d48f54a194cd00ef3beea18f9/plugins/openai-developers/skills/agents-sdk) | `11c74d6ba24d3a6d48f54a194cd00ef3beea18f9` | No repository or per-skill license located via GitHub metadata on access date; treat as all-rights-reserved reference material | Define goal, output, tools, state, approval gates; keep side effects narrow and schemas explicit. | It is an application-building skill, assumes OpenAI SDK choices, and is not safe to copy or to make a Markeitech runtime dependency. |
| [openai/openai-agents-python `runtime-behavior-probe`](https://github.com/openai/openai-agents-python/tree/5f9f4f09c3fe840b5a4c09bdbbf6f0b1239bf0ec/.agents/skills/runtime-behavior-probe) | `5f9f4f09c3fe840b5a4c09bdbbf6f0b1239bf0ec` | MIT repository | Predeclare a failure-case matrix; classify read-only/mutating/costly probes; require live destination, intent, and data gates; preserve honest limits. | Live and paid probes are forbidden in this candidate task. Its OpenAI-specific setup is not a Markeitech control contract. |
| [anthropics/skills `skill-creator`](https://github.com/anthropics/skills/tree/3b3fad96af16a10759d930941b4520ba0c40edae/skills/skill-creator) | `3b3fad96af16a10759d930941b4520ba0c40edae` | Per-skill Apache-2.0 `LICENSE.txt` | Self-contained skill structure, explicit triggering, examples/evaluation as separate concerns. | Claude-specific invocation optimization and packaging do not govern Sir Loke. No generated eval harness or text was copied. |
| [microsoft/agent-governance-toolkit](https://github.com/microsoft/agent-governance-toolkit/tree/7334d315550d683aaa845120aff48c6af177ee8b) | `7334d315550d683aaa845120aff48c6af177ee8b` | MIT repository | Policy-as-code, deny-by-default/least-authority posture, decision audit, and separating governance enforcement from the model are useful concepts. | Its toolkit, schemas, policy engine, adapters, and deployment architecture are external infrastructure and were not adopted. No assumption was made that its documented skill path is stable or compatible with Codex/Kite. |
| [GitHub Copilot agent skills guidance](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills) | Accessed 2026-08-25 | Documentation terms; not copied | Omitting broad preapproved tools preserves confirmation; unreviewed shell permission is explicitly risky. | Copilot frontmatter and permission semantics are product-specific and are not used as Markeitech or Codex configuration. |

## Ideas Explicitly Not Adopted

- No imported policy engine, agent framework, MCP server, tracing backend, authentication flow,
  model setting, runtime configuration, or dependency.
- No confidence score, approval tier, budget, cadence, retention period, chain width, strike rule,
  provider rule, trading signal, or opportunity ranking was selected.
- No external skill was treated as authority for Markeitech product semantics.
- No permissive license was treated as evidence that an external design fits the repository.
- No public skill or paper was copied verbatim; source URLs and snapshots remain attribution and
  refresh points only.

## Known Research Gaps

- The exact Sir Loke model/provider/runtime, tool protocol, persistence schema, and human-approval
  UX are not yet approved or implemented.
- Fresh installed-plugin discovery and ordinary-request selection were observed on 2026-08-25
  against Kite `0.1.0+codex.20260825124814`: an unnamed Sir Loke authority request selected the
  live-agent governance specialist. Delegated custom-role execution remained unverified because
  the ephemeral Codex collaboration runtime could not resolve its own thread ID; the bounded retry
  was terminated after no further progress. Cross-advisor execution and proportional final output
  therefore remain acceptance debt.
- Security/privacy/legal review remains necessary for credentials, model data handling, trace
  retention, personal data, provider terms, prompt injection defenses, and identity protocols.
- Current external guidance does not establish market-evidence sufficiency, option-chain semantics,
  or acceptable trading confidence; those remain project/domain decisions.
- No live model, provider, database, Discord, or paid-service behavior was tested in this research.
