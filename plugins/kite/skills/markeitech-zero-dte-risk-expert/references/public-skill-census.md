# Public Agent-Skill Census

Research date: 2026-08-25. External skills were inspected only for structure and decision-pattern
inspiration. No external prose, formulas, thresholds, strategy rules, or code was copied into the
Markeitech skill.

| Repository and inspected version | License | Useful ideas | Rejected ideas | Compatibility concerns |
| --- | --- | --- | --- | --- |
| [dongzhuoyao/finance-option-skills](https://github.com/dongzhuoyao/finance-option-skills), commit `fc4c4ac1bc9b790a0fa2c0fc6cb3a3f25c69c00a` | MIT; repository API returned `NOASSERTION`, but the tracked `LICENSE` contains the MIT text and attribution | Discriminating skill descriptions; gather exact inputs; state Greek units/conventions; sanity-check outputs; split large guidance into references | Fixed concentration thresholds, portfolio aggregation, hedging handoffs, strategy routing, position sizing, and treating generic BSM outputs as sufficient near expiry | Broadly targets portfolio/trade workflows and European-model calculations; overlaps prohibited portfolio authority and lacks Markeitech evidence/provenance gates. Structure only was adopted. |
| [FoundationalResearch/optionsderivatives](https://github.com/FoundationalResearch/optionsderivatives), commit `8971367d118f3d6c12abf5d69c641932b75b83f3` | MIT | Ordered analysis lanes; explicit scenario analysis; surface leverage, assignment, liquidity, and event risks | Strategy selection, recommended trades, percentage-of-portfolio sizing, probability-of-profit shortcuts, stop-loss/profit targets, fixed DTE doctrine, and universal IV-rank rules | Its core purpose is trade and strategy evaluation, directly conflicting with this read-only risk-only advisor. No wording or doctrine adopted. |
| [agiprolabs/claude-trading-skills](https://github.com/agiprolabs/claude-trading-skills), commit `f3fa5a2a20719cc275d8561ec8ae59a135f36948` | MIT | Explicit stub status and capability honesty; informational boundary | Stubbed option-pricing coverage, crypto-specific product assumptions, live provider integration, dependency additions, and implementation code | The relevant skill is explicitly incomplete and crypto-oriented. It is unsuitable domain evidence for U.S. SPXW/SPY/QQQ 0DTE risk. Only the honesty pattern was retained. |
| [skill-mill/agent-skill-porter](https://github.com/skill-mill/agent-skill-porter), commit `d63625f61d7d4623f9e04be8ca034a84f712e2e3` | No license declared through the GitHub repository metadata; treat as unlicensed/unknown for reuse | Public comparison confirms common `SKILL.md` frontmatter and Codex `agents/openai.yaml` metadata conventions | Conversion tooling, installation behavior, and cross-agent policy translation | Format reference only. No source material reused because no license was established and repository-owned Kite conventions are controlling. |

## Adopted Pattern Summary

- Concise, discoverable frontmatter with exclusions that prevent misrouting.
- Required input census before calculations.
- Explicit Greek units, source/model identity, and sanity/stop checks.
- Progressive disclosure through focused references.
- Capability honesty when evidence or source coverage is incomplete.

## Rejected Pattern Summary

- Strategy selection, directional bias, entry/exit rules, hedging instructions, position sizing,
  account or portfolio thresholds, and trade recommendations.
- Generic fixed thresholds presented as universal risk policy.
- Delta-as-probability and first-order Greek approximations presented without model limitations.
- Live-data integrations, dependencies, broker automation, or provider calls.
- Crypto or generic European-option mechanics transferred to the exact U.S. listed products.

The new skill is original, repository-specific work. Its domain contract and evidence gates derive
from Markeitech authority and current primary research, not from external skill doctrine.
