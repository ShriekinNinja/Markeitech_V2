# External Skill Census

Research date: 2026-08-25. Public skills were inspected for structure and guardrails only. This
candidate was written independently for Markeitech and does not copy third-party prompt text.

## Census

| Repository and artifact | Inspected revision | License | Learned | Rejected or bounded |
|---|---|---|---|---|
| [Open-Dot-Agents/SKILL.md](https://github.com/Open-Dot-Agents/SKILL.md) specification and docs | `69ef37e9424c0a7ea9dd2293b559e43ec8176379` | Code Apache-2.0; documentation CC-BY-4.0 | A skill is a discoverable folder with concise metadata and optional focused resources; progressive disclosure keeps the entrypoint usable. | The public specification does not replace the repository's established Kite layout or Codex-specific advisor schema. |
| [anthropics/skills](https://github.com/anthropics/skills), `skills/skill-creator` | `3b3fad96af16a10759d930941b4520ba0c40edae` | The inspected skill-creator is Apache-2.0; other skills have their own licenses, including proprietary terms. | Keep the entry skill focused, route substantial detail to references, and validate real behavior rather than scaffold wording. | No proprietary skill content was used. No generic script or example was copied. |
| [mblode/agent-skills](https://github.com/mblode/agent-skills), `codebase-architecture` | `e97a3b383f5944f90d41eb92b24b4fb3b917a7f9` | MIT | Strong trigger metadata, explicit in-scope/out-of-scope boundaries, mode selection, output artifacts, and a validation loop improve discoverability and use. | Its TypeScript/codebase doctrine, fixed modes, rhetorical sections, and broad hardening workflow are outside this advisor's contract. |
| [microsoft/GitHub-Copilot-for-Azure](https://github.com/microsoft/GitHub-Copilot-for-Azure), `.github/skills/skill-authoring` | `355320f73189aee3b18dcc1986de38577d33e8b1` | MIT notice in the inspected skill; repository license metadata is non-SPDX | Validate directory/name agreement, concise trigger descriptions, and frontmatter constraints. | Azure-specific conventions, `WHEN:` syntax preference, and repository-wide authoring rules were not imported. |

## Local Pattern That Governs

The repository-owned Kite plugin is the controlling implementation pattern:

- `plugins/kite/skills/markeitech-advisor-router/`
- `plugins/kite/skills/markeitech-nautilus-v2-expert/`
- `plugins/kite/skills/markeitech-architecture-boundaries-expert/`
- `plugins/kite/skills/markeitech-python-runtime-expert/`
- `plugins/kite/skills/markeitech-data-quality-lineage-expert/`
- `plugins/kite/skills/markeitech-quantitative-metric-validation-expert/`
- `plugins/kite/skills/markeitech-evidence-fitness-expert/`
- `.codex/agents/markeitech-nautilus-advisor.toml`

This candidate therefore uses:

- required `name` and discriminating `description` frontmatter;
- a concise `SKILL.md` entrypoint with linked, task-specific references;
- `agents/openai.yaml` for skill UI metadata;
- one separate project-scoped `.codex/agents/*.toml` read-only advisor role; and
- no manager, marketplace, dependency, or runtime integration change. Integration still requires a
  plugin cachebuster refresh, reinstall, and fresh-thread routing acceptance.

## License Compatibility Decision

Only structural ideas and general facts were adopted. No third-party text, code, assets, or
templates were copied. The new files remain part of the proprietary Markeitech repository. URLs,
revisions, licenses, adopted ideas, and rejected ideas are recorded here so future reviewers can
reproduce the provenance check.
