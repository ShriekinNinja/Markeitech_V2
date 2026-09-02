# Sources And Provenance

Research cut: 2026-08-25. Refresh drift-prone sources for each consultation. Sources inform
questions; they do not override tracked Markeitech authority or prove provider behavior.

- Tracked authority: `AGENTS.md`, `markeitech.md`, `docs/current-status.md`,
  `docs/development-guidelines.md`, the Stage 9 blueprint, adaptive data-plane, historical
  dependency, Stage 9C and Stage 9D contracts.
- [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339) and
  [RFC 9557](https://www.rfc-editor.org/rfc/rfc9557): qualified instants and named timezone
  representation; neither defines exchange sessions or provider clock meaning.
- [IANA TZDB](https://www.iana.org/time-zones): named timezone rules; not exchange calendars.
- [NIST Research Data Framework](https://doi.org/10.6028/NIST.SP.1500-18r2): provenance and
  fit-for-purpose quality concepts; no NIST schema or aggregate score is adopted.
- [Nautilus data concepts](https://nautilustrader.io/docs/nightly/concepts/data/): timestamp
  questions only; installed contracts require the Nautilus advisor.
- [IBKR Campus TWS API](https://ibkrcampus.com/docs/tws-api/): provider semantics require the IB
  advisor and current exact pages.

This role adopts the useful identity/time/completeness/reconciliation material from the preserved
`kite-advisor-data-quality-lineage` candidate worktree. No public skill text, schema, script, or
asset is copied; external skills were structural research only.
