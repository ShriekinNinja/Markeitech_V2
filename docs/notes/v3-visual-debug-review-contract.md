# V3 Visual-Debug Review Contract

## Status And Scope

This is the current working contract for Markeitech's progressive visual-debug review process at
baseline commit `623f0b7` on branch `v3-es-progressive-capability-review`.

It preserves the still-valid debug-process rules previously scattered across:

- `current-indicators-and-intelligence-report.md`; and
- `es-live-knowledge-snapshot-suggestion.md`.

Those two source notes are no longer required in the active side-mission scope after this
consolidation. They may be moved out as historical material. Their checkout status, Pillow/PNG
implementation, fixed five-minute overview, artifact counts, branch names, and prior renderer
decisions do not govern the current process.

This document governs review procedure only. It does not accept a metric, entity, analytical
definition, runtime mode, provider request, visual artifact, or release.

Markeitect retains final product, trading, architecture, provider, review, visual-acceptance, and
release authority.

## Goal

Review what Markeitech actually knows, one exact capability at a time, over one explicitly
configured instrument and canonical series during the real runtime.

The process must:

- show canonical observations and calculations rather than display-derived substitutes;
- preserve instrument, venue, contract, timeframe, profile, session/window, UTC timestamps,
  parameter/configuration identity, lineage, health, fidelity, revision, and missingness wherever
  they affect meaning;
- review enabled, disabled, pure-only, unsupported, and deferred capabilities explicitly;
- separate observed evidence from inference, hypothesis, recommendation, and unknown;
- record a defensible outcome for every inventoried review item; and
- keep the visualization a non-authoritative projection rather than a second analytical system.

## Non-Interference Invariant

`visual_debug_capture` is a passive, bounded review projection. Enabling or disabling it must not
change normal Markeitech operation.

For an otherwise identical runtime configuration, capture off versus capture on must preserve:

- actor ownership and upstream actor composition;
- watchlist membership and capabilities;
- IB subscriptions and provider demand;
- historical demands, request boundaries, retry, readiness, and terminal outcomes;
- live demand and subscription lifecycle;
- completed-bar admission, aggregation, conflicts, and revisions;
- metric/entity calculation and publication;
- evidence-health behavior;
- operational persistence; and
- upstream shutdown and release behavior.

The only allowed effects of enabling the capture are:

- composition of one passive observer;
- observer-owned bounded in-memory state;
- observer-owned snapshot/deadline/quiet-period state which does not change a producer;
- projection-specific rendering work;
- ignored immutable artifacts; and
- projection-specific logs and counters.

The capture must never:

- enable, disable, add, suppress, refresh, or retime a provider request;
- change `watchlist_last` or another operational capability;
- choose a producer's historical boundary;
- make SessionMetrics or another producer calculate a series it would not otherwise calculate;
- alter upstream retention or lifecycle solely because the capture is enabled;
- call Interactive Brokers or a Nautilus market-data client directly;
- resample, fill gaps, fabricate observations, or relabel sources; or
- publish canonical analytical state.

The capture may select only canonical series and records independently configured and produced by
normal runtime components. A capture mode controls projection selection, not runtime operation.

### Baseline correction status

Commit `623f0b7` remains the almost-acceptable recovery point. The current uncommitted correction
removes its `visual_snapshot_enabled` path, producer snapshot handshake, capture-aligned history,
and capture-derived producer retention. Offline equivalence proves that capture on/off actor plans
differ only by the passive observer registration. Connected equivalence and visual acceptance
remain open.

No replacement may move the same coupling into Watchlist, acquisition, another capture flag, or a
hidden configuration derivation.

## Inventory Authority And Freshness

Every review run starts from a fresh inventory generated or reconciled against the exact checkout,
review configuration, actor composition, metric registry, entity catalog, and pure-code inventory.

An old count, prior branch report, type import, actor class, example configuration, or remembered
chat statement is not proof of current implementation or activation.

The inventory seed currently includes these families:

- quote quality: midpoint, absolute spread, and relative spread;
- completed-bar foundation: admitted OHLCV, simple return, and true range;
- session references: active, previous, optional overnight, gap, range, coverage, volume, and
  bar-derived VWAP evidence;
- analytical windows: opening ranges and close-relative/power-hour measurements;
- rolling measurement candidates across configured fast, tactical, and structural horizons;
- analytical-session and objective-level entities;
- optional volatility-state entities;
- confirmed swings;
- swing legs and pivot-structure state;
- fair-value gaps;
- constituent-preserving derived zones;
- pure-code prerequisites without an active producer;
- deferred semantic events, cross-instrument intelligence, options intelligence, opportunity
  lifecycle, Sir Loke runtime behavior, ML evaluation, replay, backtesting, and execution.

This seed is a routing aid, not a frozen claim that every item remains implemented, active, or
applicable. The current V3 ES baseline activates only the completed-bar foundation review; quote
quality, session references, analytical windows, rolling measurements, and entity analysis are
disabled in `system.v3-es-minimal.toml`.

For each candidate, the inventory must also record whether Nautilus supplies:

- the canonical native primitive already reused by Markeitech;
- a partial numerical building block;
- a similarly named but semantically different component;
- a parity candidate requiring a shadow comparison; or
- no matching native capability.

Native availability does not automatically transfer ownership. Custom presence does not prove
custom arithmetic is preferable. Any ownership move remains a separate architecture decision.

## Required Review Item Identity

One inventory item represents one exact versioned review question. Its identity includes every
applicable field:

- capability kind and ID;
- implementation/producer ID;
- metric, entity, definition, and parameter version;
- instrument, contract, venue, and applicability;
- canonical series and bar specification;
- input selector and target timeframe;
- analytical profile and version;
- session, phase, window, horizon, and candidate/application ID;
- source/fidelity class;
- configuration identity; and
- producer where more than one implementation could exist.

One representative member cannot cover a family with different horizons, definitions, parameters,
or lifecycle semantics.

## Review Status Taxonomy

Every inventory item receives exactly one terminal review outcome for the reviewed capture and
question:

| Outcome | Meaning |
|---|---|
| `PASS` | The exact required behavior and evidence were observed, reconciled, and accepted by the reviewer. |
| `FAIL` | Observed evidence contradicts the accepted contract or visual representation. |
| `CONDITION_NOT_OBSERVED` | The runtime was valid, but the market/lifecycle condition needed for this question did not occur. |
| `MISSING_REQUIRED_EVIDENCE` | Evidence required to decide the item was absent or incomplete. |
| `PRODUCER_ACTIVE_NO_OUTPUT` | The producer was composed and active but emitted no compatible output before the cutoff. |
| `UNSUPPORTED_FOR_ES` | The exact capability cannot be supported for the reviewed ES contract/evidence. |
| `BLOCKED_BY_KNOWN_DEFECT` | A verified current defect prevents an honest acceptance decision. |
| `PURE_ONLY_NO_RUNTIME_PRODUCER` | Deterministic code exists, but no canonical runtime producer is composed. |
| `DEFERRED_RUNTIME_BINDING` | Runtime ownership/binding is deliberately deferred. |
| `NOT_IMPLEMENTED` | No current implementation exists for the exact item. |
| `DEFERRED_BY_ACCEPTED_PLAN` | Tracked authority explicitly defers the item. |

Starting an actor, importing a type, finding deterministic code, observing a related value, or
seeing a visually plausible mark is never sufficient for `PASS`.

`PASS` and `FAIL` are human review decisions. Runtime code and the projection may report objective
capture facts, but may not promote message arrival into acceptance.

## Enabled Capability Procedure

For every enabled item, verify and record:

1. the real producer is composed exactly once;
2. its required canonical dependencies are active without duplicate provider ownership;
3. compatible evidence for the exact instrument/series/profile/session/horizon was received;
4. the selected revision/cohort is coherent;
5. value, unit, timestamp, health, fidelity, missingness, and lineage are preserved;
6. the selected visual or textual representation matches the canonical type;
7. every visible value or mark reconciles to an exact canonical record;
8. the required market and lifecycle condition actually occurred; and
9. conflicts, omissions, caps, unsupported evidence, and unavailable inputs are explicit.

An enabled item whose required condition did not occur remains `CONDITION_NOT_OBSERVED`; it may
require another separately authorized observation and is not silently passed.

## Disabled, Pure-Only, And Deferred Procedure

Every disabled item is handled separately:

1. **Runtime-capable with reviewed dependencies:** enable its real producer exactly once in a
   separately reviewed analytical configuration, then apply the enabled-capability procedure.
2. **Pure implementation without a runtime producer:** record `PURE_ONLY_NO_RUNTIME_PRODUCER` or
   `DEFERRED_RUNTIME_BINDING`. Do not call the pure function inside the projection to manufacture a
   live value.
3. **Unsupported for the evidence/instrument:** record `UNSUPPORTED_FOR_ES` with the exact missing
   contract or evidence reason.
4. **Not implemented or accepted as deferred:** record `NOT_IMPLEMENTED` or
   `DEFERRED_BY_ACCEPTED_PLAN` and cite tracked authority.

The visual observer never activates a disabled capability. Enabling a real producer is an
independent runtime-configuration decision and must behave the same with capture off or on.

## Visual Review Form

The current progressive form is one canonical series and one selected capability question at a
time. Candles provide context; only the selected item and its directly necessary evidence are
emphasized.

Allowed representations include:

- canonical price/time geometry as candles, traces, markers, regions, or annotations;
- scalar numerical evidence as a dedicated trace or exact text/table value;
- categories, counts, lifecycle, missingness, unsupported states, and pure/deferred status as
  explicit text; and
- exact structured details for identity and lineage.

Forbidden transformations include:

- forcing a scalar or category onto the price axis merely to make it visual;
- connecting sparse state revisions into an interpolated series;
- drawing one timeframe as another timeframe's geometry;
- mixing metric cohorts from different revisions or series;
- filling gaps or calculating absent values in the renderer;
- calling historical evidence live; and
- interpreting a value as direction, confidence, setup, opportunity, support/resistance, or advice
  unless an accepted canonical producer supplied that exact semantic contract.

One artifact must expose its exact instrument, series, bar specification, capture mode, source
population, UTC window, configuration/capture/parameter identity, and unavailable lineage.

## Review Ledger

The review record contains one entry per exact inventory item with:

- full review identity;
- current implementation classification;
- producer and activation state;
- required evidence and condition;
- observed canonical record references;
- selected visual/table artifact reference;
- objective capture facts;
- reviewer outcome;
- defect, blocker, missingness, or unobserved-condition reason; and
- required follow-up observation or decision.

The ledger must reconcile exactly:

```text
total inventoried items
= PASS count
+ FAIL count
+ CONDITION_NOT_OBSERVED count
+ MISSING_REQUIRED_EVIDENCE count
+ PRODUCER_ACTIVE_NO_OUTPUT count
+ UNSUPPORTED_FOR_ES count
+ BLOCKED_BY_KNOWN_DEFECT count
+ PURE_ONLY_NO_RUNTIME_PRODUCER count
+ DEFERRED_RUNTIME_BINDING count
+ NOT_IMPLEMENTED count
+ DEFERRED_BY_ACCEPTED_PLAN count
```

No item may remain unclassified. Counts created by the projection must be labeled as review
inventory, captured records, shown marks, or omitted records—not analytical market state.

## Verified Current Blockers Carried Forward

The following two rolling-measurement risks were rechecked against commit `623f0b7` and remain
current code-level blockers until independently fixed and validated:

1. **Rolling ATR window predecessor:** `_average_true_range` initializes the first bar in each
   selected rolling window with `high - low`. It does not receive the compatible close immediately
   before that selected window, so a gap at the window boundary can be omitted from the arithmetic.
2. **Zero-median baseline publication:** `_baseline_values` can return a valid non-null percentile
   together with `MetricHealth.UNAVAILABLE` when the median reference range is zero.
   `rolling_metric_values` applies that unavailable health to the percentile, while `MetricValue`
   rejects unavailable metrics carrying a value. No focused zero-median regression fixture was
   found in the current rolling test file.

These findings are not evidence that other rolling calculations fail. They prevent the affected
questions from receiving `PASS` and must remain `BLOCKED_BY_KNOWN_DEFECT` until their exact paths are
corrected and verified.

## Completion Gate

A progressive review is complete only when:

- the inventory matches the exact checkout and reviewed runtime configuration;
- every item has one allowed outcome;
- all visible marks/text reconcile to canonical records;
- enabled and disabled items are handled according to this contract;
- unobserved conditions and known defects remain explicit;
- capture on/off non-interference is verified;
- runtime and artifact counters reconcile;
- shutdown is clean;
- the resulting artifact passes Markeitect's visual review; and
- no offline fixture, screenshot, single session, or visually plausible result is promoted into
  broader provider, formula, lifecycle, or product acceptance.

## Explicitly Superseded Debug Directions

The current process does not revive:

- the rejected everything-at-once Plotly/Kaleido static chart;
- the rejected exhaustive Pillow/PNG frame set;
- a fixed five-minute overview for every capability;
- a hard-coded 391-item inventory or 392-image output;
- display-side activation or calculation of missing capabilities;
- screenshot-only acceptance; or
- a projection mode that changes normal runtime operation.
