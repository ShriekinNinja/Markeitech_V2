# External Skill Census

Research snapshot: 2026-08-25. These public repositories were inspected for structure and
guardrails only. No external text, scripts, or assets were copied. The candidate is original and
governed by the proprietary Kite plugin license.

| Repository/artifact | Revision inspected | License observed | Learned | Rejected or not copied |
|---|---|---|---|---|
| [OpenAI `skills`, skill-creator](https://github.com/openai/skills/blob/49f948faa9258a0c61caceaf225e179651397431/skills/.system/skill-creator/SKILL.md) | `49f948faa9258a0c61caceaf225e179651397431` (2026-06-24); repository now marked deprecated in favor of `openai/plugins` | Skill-local Apache-2.0 `LICENSE.txt` | Concise discovery metadata, progressive disclosure, referenced resources, deterministic validation | Did not copy wording or assume the deprecated repository is the current distribution pattern |
| [OpenAI `plugins`, writing-skills example](https://github.com/openai/plugins/blob/11c74d6ba24d3a6d48f54a194cd00ef3beea18f9/plugins/superpowers/skills/writing-skills/SKILL.md) | `11c74d6ba24d3a6d48f54a194cd00ef3beea18f9` (2026-07-13) | Plugin-local MIT license, copyright Jesse Vincent | Plugin-local skill placement and small entrypoint with on-demand detail | Copied no prompt text, scripts, or behavior; retained the stricter repository-owned advisor pattern |
| [Anthropic `skills`, skill-creator](https://github.com/anthropics/skills/blob/3b3fad96af16a10759d930941b4520ba0c40edae/skills/skill-creator/SKILL.md) | `3b3fad96af16a10759d930941b4520ba0c40edae` (2026-08-21) | Skill-local Apache-2.0; repository contains separately proprietary/source-available document skills | Three-level progressive disclosure, realistic forward evaluation, explicit trigger quality | Did not copy proprietary document-skill material, fixed line-count doctrine, or evaluation machinery unnecessary for this candidate |
| [GitHub `awesome-copilot`, skill guidance](https://github.com/github/awesome-copilot/blob/d0d9d9f014abb27bf0d8321851867500a3a46bba/instructions/agent-skills.instructions.md) | `d0d9d9f014abb27bf0d8321851867500a3a46bba` (2026-08-25) | MIT | Name/folder agreement, discoverable descriptions, optional references/scripts, explicit security review before installation | Did not import community skills, broad tool permissions, arbitrary templates, or Copilot-specific frontmatter |
| [Agent Skills specification](https://agentskills.io/specification) | live specification accessed 2026-08-25 | Specification page; no reusable implementation imported | Minimal required frontmatter and portable directory conventions | Project conventions and Codex validation govern fields actually emitted here |

## Applied Structure

- One project-scoped skill directory with `SKILL.md`, `agents/openai.yaml`, and routed references.
- One matching project-scoped read-only advisor definition.
- A discriminating description limited to material Python-runtime correctness and operations, with
  an explicit NautilusTrader framework-contract boundary.
- No scripts or assets because the current candidate has no repeated transformation that justifies
  executable helpers.
- No advisor-specific router hardcoding is required: the generic router discovers the skill catalog
  and matching project custom-agent role. Static routing cases are recorded in
  [routing-evaluation.md](routing-evaluation.md); installed-plugin discovery remains unverified
  until the approved cachebuster, reinstall, and fresh-thread acceptance run.

## License Compatibility Conclusion

Only abstract organizational lessons were used. No external expressive content was incorporated,
so mixed, absent, proprietary, or source-available licenses do not contaminate the candidate. Any
future adoption of external scripts or text requires a new source-level license review and
attribution record.
