# Research And Source Census

Access date: 2026-08-25. This ledger records sources used to design the advisor, not permanent
product or dependency approval. Refresh versioned or drift-prone sources before consequential use.

## Tracked Markeitech Authority And Evidence

| Source | Status and use | Boundary |
|---|---|---|
| `AGENTS.md` | Current repository operating, advisor, evidence, side-effect, and completion contract | Highest repository-specific operating authority after platform and current user instruction |
| `markeitech.md` | Current charter: live-first, advisory, canonical-boundary separation, UTC, evidence fidelity, projection isolation, typed/versioned configuration | Governs durable product and engineering meaning |
| `docs/current-status.md` | Current implementation and acceptance ledger, including the local 9D.5D visual-acceptance projection | Passing/offline/current claims remain limited to recorded scope |
| `docs/development-guidelines.md` | Consumer/projection separation, evidence lineage, operator comparison metadata, and configuration discipline | Does not create new product semantics |
| `docs/README.md` | Documentation authority order and navigation | Drafts and historical records do not override accepted V2 authority |
| `docs/roadmap/v2-market-events-live-agent-plan.md` | Accepted future Sir Loke sequence and evidence boundaries | Roadmap intent is not implementation proof |
| `docs/roadmap/v2-stage-9d-entities-rolling-state-plan.md` | Accepted entity/state identities, lifecycle, health/fidelity, visual-acceptance scope, and open acceptance debt | Numerical fixtures are not trading calibration |
| `docs/roadmap/v2-live-dashboard-plan-draft.md` | Detailed 2026-08-24 visualization hypothesis and decision-gate inventory | Explicitly draft: no architecture, dependency, transport, runtime, or delivery choice is approved |
| Current source, tests, fixtures, and rendered artifacts | Executable evidence for actual payloads and presentation behavior | Inspect per task; a symbol or screenshot alone is not semantic proof |

## Primary Standards And Technical Sources

| Source | Version/date | Ideas adopted | Rejected or bounded use |
|---|---|---|---|
| [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/) | W3C Recommendation, current page retrieved 2026-08-25 | Text alternatives, keyboard operation, focus, reflow, non-text contrast, reduced/controlled motion, status semantics | Compliance criteria are a floor; they do not prove a dense financial visualization is usable |
| [W3C Understanding Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color) and [G209 adjoining-color contrast](https://www.w3.org/WAI/WCAG21/Techniques/general/G209) | Current WAI guidance retrieved 2026-08-25 | Redundant non-color encodings and explicit boundary contrast tests | Color palettes alone are not accessibility evidence |
| [Playwright visual comparisons](https://playwright.dev/docs/next/test-snapshots) | Current docs retrieved 2026-08-25 | Reviewed screenshot baselines, settling before capture, and environment-controlled comparison | Pixel equality across OS/browser/font/device environments; unexplained bulk baseline updates |
| [Playwright accessibility testing](https://playwright.dev/docs/accessibility-testing) and [ARIA snapshots](https://playwright.dev/docs/aria-snapshots) | Current docs retrieved 2026-08-25 | Automated issue scans, targeted state tests, stable violation fingerprints, accessibility-tree assertions | Automated checks as proof of full accessibility; snapshots of volatile implementation detail |
| [TradingView Lightweight Charts real-time updates](https://tradingview.github.io/lightweight-charts/tutorials/demos/realtime-updates) | Current docs retrieved 2026-08-25 | Incremental last-point/new-point update mechanics and explicit return-to-live interaction | Demo timers or simulated values as a transport/canonicality design |
| [Lightweight Charts 5.1 release notes](https://tradingview.github.io/lightweight-charts/docs/5.1/release-notes) and [time-scale options](https://tradingview.github.io/lightweight-charts/docs/api/interfaces/TimeScaleOptions) | Documentation showed 5.1 capabilities on 2026-08-25 | Inspect point-density and memory/initial-load tradeoffs before enabling performance features | Conflation or smoothing for candles/entities without proof that analytical meaning is unchanged; no dependency approval implied |
| [Rich Screen Reader Experiences for Accessible Data Visualization](https://vis.csail.mit.edu/pubs/rich-screen-reader-vis-experiences/) | Zong et al., Computer Graphics Forum 41(3), 2022, DOI 10.1111/CGF.14519 | Structure, navigation, and description as separate accessible-visualization dimensions; user-controlled levels of detail | Alt text or a raw table as the complete accessible experience; one study as universal preference evidence |
| [Scale matters: risk perception, return expectations, and investment propensity](https://pmc.ncbi.nlm.nih.gov/articles/PMC6373342/) | Peer-reviewed open-access article, 2019 | Financial-chart scale can affect human judgment; visible-window and scale policy require explicit acceptance | Treating any single auto-scale rule as perceptually neutral or universally correct |

## OpenAI Foundations Considered

| Source | Version/date | Ideas adopted | Compatibility concerns and rejected ideas |
|---|---|---|---|
| [OpenAI: Build a dashboard that stays up to date](https://learn.chatgpt.com/use-cases/analyze-data-export) | Official use case retrieved 2026-08-25 | Source-backed dashboards, freshness display, data-quality checks, meaningful-change updates, and human review before sharing | Spreadsheet calculations and scheduled mutation are incompatible with a projection-only live market UI unless supplied canonically |
| [OpenAI: Plan a dashboard and monitoring workflow](https://learn.chatgpt.com/use-cases/dashboard-builder-monitor) | Official use case retrieved 2026-08-25 | Decision questions, metric/source ownership, quality checks, and monitoring acceptance as planning inputs | Generic KPI design must not invent Markeitech measures or business semantics |
| [OpenAI model guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.5) | Official page retrieved 2026-08-25 | Outcome-first advisor contract, explicit success/stop conditions, representative validation, and rendered visual inspection | Model-prompt guidance is not a visualization or financial-domain standard |

OpenAI did not expose a single official skill named "real-time dashboard" or "visualization
testing" in the searched documentation. The closest foundations were the dashboard use cases,
OpenAI public data-analytics dashboard/visualization skills, and its Playwright skill. Record this as
a source-census result, not proof that no private or future skill exists.

## Public Skill Census And License Review

External skills are inspiration only. No external text is copied into the Markeitech advisor.

| Repository and exact revision | License evidence | Candidate patterns | Adopted | Rejected / compatibility concerns |
|---|---|---|---|---|
| [openai/role-specific-plugins](https://github.com/openai/role-specific-plugins), commit `fe5608d2512a7d6a7b9821ce8a88c48464ecd6e4`; `build-dashboard`, `visualize-data`, `validate-data` | Repository reports MIT | Source discovery, freshness, data-quality visibility, chart-semantic QA, reconciliation, explicit handoff | Source-to-visible-element traceability, decision-led views, QA beyond aesthetics | These skills may calculate/aggregate metrics and choose delivery surfaces; Markeitech UI may do neither without canonical contracts and approval |
| [openai/skills](https://github.com/openai/skills), commit `49f948faa9258a0c61caceaf225e179651397431`; curated `playwright` | Skill-local `LICENSE.txt` is Apache-2.0 | Browser reconnaissance, semantic locators, screenshots, console/network inspection, repeatable local UI testing | Rendered-state inspection and deterministic browser workflows as optional test mechanics | No assumption that Playwright is installed or approved; tests do not replace semantic, accessibility, or operator acceptance |
| [anthropics/skills](https://github.com/anthropics/skills), commit `3b3fad96af16a10759d930941b4520ba0c40edae`; `webapp-testing`, `frontend-design`, `skill-creator` | Skill-local licenses are Apache-2.0 | Reconnaissance before interaction, rendered screenshots, progressive disclosure, manual review and behavioral evals | Inspect rendered state before actions; combine deterministic and human review; keep the advisor entrypoint focused | Aesthetic novelty, generic frontend doctrine, mandatory tool stacks, and copied evaluation harnesses do not fit the evidence-projection contract |
| [mares29/dashboard-design-skill](https://github.com/mares29/dashboard-design-skill), commit `bbed535a08f0e1768b40087996fe019370312374` | MIT | Decision-first dashboard questions, visible quality, non-color encodings, keyboard/focus checks, performance checklist | Audience/decision questions, visible data-quality/freshness, accessibility and performance review categories | Universal quality scores, smart narratives, fixed navigation, precomputation, prescribed libraries, and blanket UI rules could invent semantics or architecture |
| [magnus919/agent-skills](https://github.com/magnus919/agent-skills), commit `e10508b034c61e1ca608e6b089abe7c93d3cbf8c` | Repository reports MIT | Agent Skills format and progressive-disclosure conventions | Discoverable name/description and a focused source reference | Generic format guidance adds no financial or visualization authority; no domain content adopted |

### License Compatibility Conclusion

MIT and Apache-2.0 sources are compatible for inspiration, but this proprietary skill contains an
independent synthesis rather than copied or modified external passages. No third-party asset,
script, code, fixture, or substantial text is bundled. If later implementation copies or modifies
external material, repeat the license/notice review at the exact revision and preserve required
attribution. A repository-level missing license is not permission; rely only on the recorded
skill-local license or reject reuse.

## Source Selection Discipline

- Prefer tracked Markeitech authority for product meaning and current implementation.
- Prefer standards bodies for accessibility requirements, installed APIs for executable behavior,
  official library documentation for versioned mechanics, and peer-reviewed studies for bounded
  human-factors evidence.
- Record access date, exact version/commit, license, and applicability before adopting a dependency,
  library behavior, visual rule, or test pattern.
- Separate measured findings from recommendations. Never turn a current workstation measurement,
  one screenshot, one operator session, or a third-party checklist into a universal threshold.
