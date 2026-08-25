# Semantic Events And Opportunity Lifecycle Contract

Each definition records schema/definition/config versions; subject/exposure/instrument/relationship
identity; evidence/entity revisions; event/effective, observed, published, expiry and invalidation
times; causation/correlation; direction/horizon/magnitude/confidence/urgency as separate fields when
approved; deduplication and revision keys; allowed transitions; stale/conflict/unknown behavior;
and permitted/forbidden downstream inference.

An immutable event records a meaningful transition. A current-state projection may revise through
new immutable events but must not rewrite the prior availability record. `SUPERSEDED` links an
authoritative replacement; `INVALIDATED` means the definition's evidence or predicate no longer
supports validity; `EXPIRED` is time/policy terminality; `STALE` is evidence-age invalidity;
`RESOLVED` is an approved outcome state, not automatically success or profit.

Opportunity identity is target exposure, direction, horizon, episode, evidence set/versions,
trigger/invalidation and lifecycle identity, not a source instrument or option contract. Preserve
coexisting opportunities, competing explanations, conflicts and abstention. Expression candidates
remain separate children and require the options owner.

Thresholds, hysteresis, confirmations, decay, expiry, conflict priority, revision windows,
cardinality and retention are typed, scoped, bounded, versioned policy candidates. The advisor may
propose but never accept their market meaning.
