# External Agent-Skill Census

Researched on **2026-08-25** for structure and guardrails only. No external skill text, script, or
asset was copied into this candidate.

| Source | Revision inspected | License found | Learned | Rejected or not adopted |
|---|---|---|---|---|
| Anthropic `skills`, `skill-creator` | `3b3fad96af16a10759d930941b4520ba0c40edae` | Repository did not expose an SPDX license through the GitHub API; the skill points to complete terms in its own `LICENSE.txt`, which was not reliably retrievable during this run | Put trigger quality in frontmatter; keep the entry file concise; use one-level references and progressive disclosure | No wording or templates copied because the exact applicable license text was not confirmed; no generic scripts or broad skill-creation doctrine imported |
| Anthropic `financial-services` | `69cbc81467a5dced793eee03dec4658aa24ef856` | Apache-2.0 | Validate manifests and cross-file references; keep finance workflows source-backed and reproducible | Did not import valuation, wealth, investment-banking, portfolio, or recommendation semantics; those domains do not match Markeitech options evidence review |
| OpenAI `role-specific-plugins`, Data Analytics index | `fe5608d2512a7d6a7b9821ce8a88c48464ecd6e4` | MIT | Use explicit routing boundaries, positive trigger evidence, and focused workflows instead of a monolithic generic analyst | Did not import connector behavior, business KPI semantics, runtime-surface logic, or tools not present in this project |
| Open-Dot-Agents `SKILL.md` specification | `69ef37e9424c0a7ea9dd2293b559e43ec8176379` | Apache-2.0 for code and CC-BY-4.0 for documentation as stated by the project | Confirmed the portable folder model: required `SKILL.md` with metadata plus optional references/scripts/assets | No alternate manifest or payment/API extensions adopted; the repository-owned Kite convention governs this plugin |

Immutable inspection URLs:

- https://github.com/anthropics/skills/tree/3b3fad96af16a10759d930941b4520ba0c40edae/skills/skill-creator
- https://github.com/anthropics/financial-services/tree/69cbc81467a5dced793eee03dec4658aa24ef856
- https://github.com/openai/role-specific-plugins/blob/fe5608d2512a7d6a7b9821ce8a88c48464ecd6e4/plugins/data-analytics/skills/index/SKILL.md
- https://github.com/Open-Dot-Agents/SKILL.md/tree/69ef37e9424c0a7ea9dd2293b559e43ec8176379

## Candidate Design Consequences

- The frontmatter names both positive triggers and material exclusions so routing can remain
  narrow without manager integration.
- The entry file owns mandatory workflow and invariant guards; detailed mechanics, gates, and
  source inventories live in directly linked references.
- Domain content is project-authored from repository authority and attributed primary research.
- No executable scripts or network actions are bundled because this advisor is analytical and
  read-only; validation uses repository/offline tooling outside the skill package.
- The existing Kite skill and custom-advisor pattern takes precedence over external examples.
