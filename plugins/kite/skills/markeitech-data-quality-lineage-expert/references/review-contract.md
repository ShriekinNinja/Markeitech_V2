# Data Quality And Lineage Review Contract

For each path record provider/adapter/version, venue, exact instrument/contract/raw symbol,
observation type/selector/aggregation/resolution, request/subscription/artifact/filter identity,
schema/config/transformation versions, parents, event/interval/receive/init/calculate/publish times,
clock sources/precision, IANA timezone/session/trade date, expected population, gaps, duplicates,
conflicts, late evidence, corrections, health, fidelity, owner and consumer.

Also record the observation grain and candidate join keys; expected and observed join cardinality;
whether joins can multiply rows or create many-to-many duplication; event time versus availability
time; historical/live overlap ownership and convergence; and dated calendar boundaries including
holidays, early closes, and DST gaps/folds. Treat these as explicit quality and lineage questions,
not incidental implementation details.

Classify separately:

- request completion, temporal coverage, observation coverage, field validity, contract continuity,
  semantic suitability and lineage completeness;
- transport duplicate, exact duplicate, possible semantic duplicate, provider revision,
  correction/cancel, identity conflict, late evidence and stale/out-of-window evidence;
- source availability, identity validity, temporal recency, completeness, conflict state, fidelity,
  lineage and consumer-specific quality inputs.
- one-to-one, one-to-many, many-to-one, or many-to-many join behavior; expected versus observed
  output cardinality; historical/live overlap duplicates or conflicts; and evidence that was not
  yet available at the claimed decision time.

An artifact hash proves byte identity, not market-event identity. A response terminator proves the
request ended, not that the market population is complete. A closed market is not stale merely
because updates stop. Defaults and aliases can preserve structural compatibility but cannot create
an observed field or legitimize changed meaning.

Variable age limits, coverage floors, lateness, revision windows, tolerances, precedence, health
aggregation, retention and reconciliation rules are typed, scoped, bounded, versioned policy
candidates. Identity, type safety, provenance and non-silent conflict handling are invariants.
