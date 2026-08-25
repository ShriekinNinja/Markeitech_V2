# Source And Public-Skill Census

**Census date:** 2026-08-25

This census records foundations and known limitations. Refresh drift-prone market, provider,
framework, timezone, calendar, and product documentation during each consequential consultation.
Repository authority and current executable behavior control Markeitech-specific claims.

## Tracked Markeitech Authority

Inspect the current versions of:

- `AGENTS.md`, `markeitech.md`, `docs/current-status.md`, `docs/development-guidelines.md`, and
  `docs/README.md`;
- `docs/architecture/v2-adaptive-market-data-plane.md`;
- `docs/architecture/v2-historical-dependency-execution.md`;
- `docs/roadmap/v2-market-events-live-agent-plan.md`;
- `docs/roadmap/v2-first-market-intelligence-coding-sequence.md`;
- `docs/roadmap/v2-stage-9c-session-measurements-plan.md`;
- `docs/roadmap/v2-stage-9d-entities-rolling-state-plan.md`; and
- `docs/market-intelligence-request-catalog.md`.

Relevant code and tests currently include `v2/src/markeitech/intelligence/`, historical acquisition
contracts under `v2/src/markeitech/acquisition/`, configuration/composition under
`v2/src/markeitech/system/`, and corresponding `v2/tests/` paths. These locations are orientation,
not permanent ownership claims; confirm them from the current checkout.

## Primary And Institutional Sources

| Source | Authority and use | Adopted | Limit or compatibility concern |
|---|---|---|---|
| [ISO/IEC 25012:2008](https://www.iso.org/standard/35736.html), confirmed current in 2025 | International data-quality model | Fit-for-purpose quality framing; accuracy, completeness, consistency, and related characteristics are requirements, not generic scores | Abstract/model only; full standard is licensed and was not copied |
| [NIST Research Data Framework SP 1500-18r2](https://doi.org/10.6028/NIST.SP.1500-18r2) | Institutional research-data lifecycle and fit-for-purpose quality | Planned use, metadata, integrity, quality measures, and peer review matter to admission | Broad research-data guidance, not market-metric semantics |
| [RFC 9557](https://www.rfc-editor.org/rfc/rfc9557.html) | IETF Standards Track timestamp extensions | Preserve instant, UTC offset, and named-zone meaning; reject offset-as-timezone shortcuts | Serialization standard, not an exchange calendar |
| [IANA Time Zone Database](https://www.iana.org/time-zones) and [theory](https://www.iana.org/time-zones/theory.html), release `2026c` at census | Primary civil-time rules used by software | Explicit IANA zones and tzdb-version awareness for DST/civil-time reproducibility | IANA states tzdb is updated and not itself legal authority; exchange calendars still control sessions |
| [W3C PROV-DM](https://www.w3.org/TR/prov-dm/) and [PROV-O](https://www.w3.org/TR/prov-o/) | W3C Recommendations for provenance entities, activities, agents, derivation, and attribution | Preserve source, transformation, version, and responsible-owner lineage through derivation | Conceptual interoperability model; no requirement to introduce RDF/OWL |
| [NautilusTrader nightly data concepts](https://nautilustrader.io/docs/nightly/concepts/data/) | Current upstream framework guide | Keep `ts_event` and `ts_init` semantics distinct and verify exact pinned contracts locally | Nightly is unreleased and may differ from the installed pin; requires Nautilus advisor for framework conclusions |
| [SEC Rule 613 overview](https://www.sec.gov/about/divisions-offices/division-trading-markets/rule-613-consolidated-audit-trail) | Primary regulatory source illustrating linked event identity, clock synchronization, and timestamp granularity | Timestamp precision and linkage affect evidence meaning | CAT rules are not a general Markeitech implementation mandate |
| [Cboe Hours and Holidays](https://www.cboe.com/about/hours/us-options) and [Cboe 24/5 FAQ](https://www.cboe.com/document/tech-spec/document/technical-specifications/cboe-options-exchange-245-faq/) | Primary exchange session, holiday, trade-date, business-date, and calendar-date material | Session/trade-date validation must use current exchange evidence and handle cross-calendar-day sessions | Schedule changes are drift-prone; refresh notices for the exact date/product |
| [CME Group trading hours](https://www.cmegroup.com/trading-hours.html) | Primary exchange holiday/trading-hours material | Futures windows require exact product/date schedule evidence | Page aggregates products and may use display-time conventions; validate exact product schedule |
| [IBKR Campus TWS API](https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/) | Current provider API root | Verify request selector, timestamp/timezone, bar, revision, and schedule behavior against current provider docs and local acceptance | Provider documentation is not measured adapter delivery or consolidated market truth |
| [IBKR historical bars legacy page](https://interactivebrokers.github.io/tws-api/historical_bars.html) | Deprecated provider page retaining explicit warnings about daily futures settlement and cross-calendar-day sessions | Warning patterns worth rechecking in current Campus docs and acceptance | Deprecated; never use alone as current provider authority |
| [Apache Flink timely stream processing](https://nightlies.apache.org/flink/flink-docs-stable/docs/concepts/time/) | Mature event-time/watermark reference implementation | Separate event time from processing time; treat lateness/watermarks as explicit policy | Markeitech does not adopt Flink; watermarks do not prove completeness |
| Akidau et al., [The Dataflow Model](https://www.vldb.org/pvldb/vol8/p1792-Akidau.pdf), VLDB 2015 | Peer-reviewed unbounded/out-of-order processing model | Ask what is computed, where in event time, when emitted, and how later data changes results | General stream-processing model, not provider or market semantics |
| [NIST/SEMATECH measurement process characterization](https://www.nist.gov/publications/nistsematech-engineering-statistics-handbook-chapter-2-measurement-process) | Institutional measurement guidance | Independent calibration, repeatability, reproducibility, stability, and uncertainty strengthen analytical acceptance | Physical measurement framing must be adapted carefully to software-derived metrics |

## Public Agent-Skill Census

No external prompt text was copied. The candidate is an original Markeitech contract derived from
project authority and the primary sources above.

| Public skill | Version inspected and license | Ideas adopted | Ideas rejected or compatibility concerns |
|---|---|---|---|
| OpenAI [`analyze-data-quality`](https://github.com/openai/role-specific-plugins/tree/fe5608d2512a7d6a7b9821ce8a88c48464ecd6e4/plugins/data-analytics/skills/analyze-data-quality), file/repo commit `fe5608d2512a7d6a7b9821ce8a88c48464ecd6e4`, MIT | Start from intended use and grain; test completeness, uniqueness, validity, consistency, integrity, timeliness, volume, shape, and temporal drift; tie findings to impact | Generic dataset profiling, connector assumptions, notebook/report handoffs, and business-data examples are not mandatory for a live market-evidence gate |
| OpenAI [`metric-diagnostics`](https://github.com/openai/role-specific-plugins/tree/fe5608d2512a7d6a7b9821ce8a88c48464ecd6e4/plugins/data-analytics/skills/metric-diagnostics), file/repo commit `fe5608d2512a7d6a7b9821ce8a88c48464ecd6e4`, MIT | Reproduce the metric before explaining it; reconcile definition, source, grain, filters, freshness, lineage, conflicts, and residuals | Broad source discovery, business driver decomposition, and mandatory report handoff can expand scope and are not evidence-review criteria |
| OpenAI [`validate-data`](https://github.com/openai/role-specific-plugins/tree/fe5608d2512a7d6a7b9821ce8a88c48464ecd6e4/plugins/data-analytics/skills/validate-data), file/repo commit `fe5608d2512a7d6a7b9821ce8a88c48464ecd6e4`, MIT | Independently recompute high-impact values; check joins, denominators, periods, timezones, look-ahead, caveats, and decision readiness | Three-level stakeholder sharing score, visualization polish, generic SQL recipes, and causal-analysis breadth are insufficient for pre-Sir Loke evidence review |
| The Interdependency [`validate-data`](https://github.com/The-Interdependency/skill-lib/tree/be791091dffb74d4f5f65352fd7d8bc7cd6d887f/validate-data), file commit `be791091dffb74d4f5f65352fd7d8bc7cd6d887f`, repository commit inspected `5eb0d5ee31a4718bd340d1eccdb9748010782a84`, MPL-2.0 | Adversarial pre-share review and independent spot checks confirmed that validation should attack conclusions, not just presentation | No text adopted; current MPL-2.0 file-level copyleft and generic stakeholder orientation are unnecessary compatibility burdens for this proprietary skill |
| TerminalSkills [`data-validator`](https://github.com/TerminalSkills/skills/tree/7a5cc96749b07bcbd33d4f27e98a26a3dba456ca/skills/data-validator), repo commit `7a5cc96749b07bcbd33d4f27e98a26a3dba456ca`, Apache-2.0, skill metadata `1.0.0` | Profile before judging; separate failed checks from warnings; quantify affected observations; test freshness and time-series gaps | CSV/JSON/ETL focus, sample-generating templates, fixed example thresholds, and generic cleaning advice would encourage mutation or hidden policy |

## Compatibility Conclusions

- MIT and Apache-2.0 sources permit inspiration with attribution, but this candidate intentionally
  copies no external prompt text.
- The MPL-2.0 skill was reviewed only for ideas; no text or file was incorporated.
- ISO material is referenced, not reproduced.
- Provider, exchange, framework-nightly, calendar, and timezone facts are drift-prone and require a
  fresh read for consequential use.
- External skills do not encode Markeitech's provider identity, session semantics, evidence
  fidelity, historical/live convergence, configuration discipline, read-only boundary, or the
  advisory evidence review required before Sir Loke integration; those are repository-specific
  original requirements.
