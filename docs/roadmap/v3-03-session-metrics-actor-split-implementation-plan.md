# V3-03 Session Metrics Ownership Split Implementation Plan

**Status:** Planning decisions accepted on 2026-09-01. Slices 1 and 2 are reviewed and merged;
Slice 3 is the next V3-03 slice and has not started. A separate NautilusTrader rc4 upgrade PR
precedes it, as requested on 2026-09-02. Each remaining implementation batch and connected run
still requires its own explicit authorization.

**Planning branch:** `v3-03-session-metrics-split-plan`

**Planning baseline:** `d417b55` (`Merge API docs metadata rendering`), which includes the
V3-02 baseline `c9c55cf`

**Target:** V3-03 only: replace the disabled combined `SessionMetricsActor` with explicit,
independently bounded completed-bar and numerical-measurement owners, and migrate Visual Debug as
their passive, non-gating review projection

**Depends on:** Implemented V3-01 canonical-calendar authority and implemented V3-02
current-state snapshot/reconciliation

## Execution Progress And Resume Point

Verified on 2026-09-02 at `master` code baseline `d0aee01`, after V3-03 integration PR 12 and
the two root-migration PRs. The original planning baseline above is historical context, not the branch
from which to resume. Current implementation evidence is recorded in
[`current-status.md`](../current-status.md).

**Prerequisite PR:** the separate NautilusTrader `2.0.0rc3` to `2.0.0rc4` upgrade is implemented
and offline-verified; its evidence and connected-acceptance limits are recorded in
[`current-status.md`](../current-status.md). Complete its required CI and Markeitect review/merge
before resuming Slice 3; it does not expand or reorder the V3-03 slices below.

| Slice | Current state |
|---|---|
| 1 — identities, contracts, manifest | Reviewed and merged; implementation `4631df5`. Public v2 contracts remain inactive in tracked runtime profiles. |
| 2 — completed-bar foundation | Reviewed and merged; final implementation `eb3995b`, stage merge `e8f49e3`. Private actor and state pass disconnected fixtures; no production composition or activation. |
| 3 — direct completed-bar metrics | **Next V3-03 slice, after the rc4 upgrade PR; not implemented.** Add only the disabled direct-metrics owner and its focused integration/parity fixtures. |
| 4 — calendar-dependent numerical owners | Not started; session references and analytical windows. |
| 5 — rolling measurements | Not started; includes the accepted predecessor-aware ATR and zero-median corrections. |
| 6 — passive Visual Debug | Not started; remains mandatory within V3-03, not optional follow-up work. |
| 7 — configuration/composition/cold cutover | Not started; owns schema 24 and the atomic active-wire migration. |
| 8 — legacy retirement and authority closure | Not started; only after replacement responsibility coverage. |
| 9 — bounded connected acceptance | Not started; each exact run needs separate authorization. |

The agent resuming V3-03 must read the repository entrypoint and required authorities, then
implement [Slice 3](#slice-3-direct-completed-bar-metrics-owner) only after the rc4 upgrade PR is
merged and Markeitect authorizes the slice:

- Start from the approved current integration checkpoint on a new slice branch, not an old
  nested-layout worktree. Let Markeitect approve and merge the handoff PR before beginning a
  dependent code batch. Use root `src/`, `tests/`, `config/`, `pyproject.toml`, and `uv.lock`;
  do not recreate `v2/`.
- The existing foundation actor, configuration, and state are in
  `src/markeitech/intelligence/completed_bar_foundation.py`, not a separate
  `completed_bar_foundation_actor.py`. Reuse its exact-series/readiness contracts from
  `completed_bar_messages.py` and `metric_producer_manifest.py`, and v2 metric identity/admission
  from `metric_messages.py` and `metric_value_admission.py`.
- Reuse the seven definitions/calculations in `session_measurements.py`: `completed_bar.open`,
  `.high`, `.low`, `.close`, `.volume`, `.simple_return`, and `.true_range`. That helper still
  accepts legacy `CompletedBarInput` and returns the private legacy metric shape; it is formula
  and compatibility evidence, not a ready-to-publish canonical v2 implementation.
- Keep the new actor private and uncomposed in tracked profiles. Preserve existing enabled
  legacy-v1 publishers until Slice 7; exercise new canonical v2 delivery only in disconnected
  fixtures. Do not change provider demand, introduce another bar writer, bump system schema,
  migrate Visual Debug, fix rolling families, or remove the old actor in Slice 3.
- Extend the nearby `test_session_measurements.py`, `test_completed_bar_foundation.py`,
  `test_metric_messages_v2.py`, `test_metric_producer_manifest.py`, and message-delivery fixtures
  as applicable. Prove exact predecessor dependence, partial-input degradation and recovery,
  unavailable/warmup outcomes, identity, revisions, series/family isolation, and fixture parity.
- Run focused tests, `uv run --locked --offline ruff check src tests`,
  `uv run --locked --offline pytest -q tests -m "not postgres"`, and `git diff --check`.
  Apply the existing conditional API-doc and diagram gates when their owned surfaces change.
  Commit and push the scoped implementation and open its PR under the
  [GitHub workflow](../operations/github-workflow.md). Stop for Markeitect's approval and merge;
  publishing a PR and passing CI grant no merge or connected-run authority.

Version freshness at the pre-upgrade handoff: the installed and locked contract was NautilusTrader
`2.0.0rc3`. On 2026-09-02 the [nightly guides](https://nautilustrader.io/docs/nightly/) identified themselves as
unreleased, and the [nightly Python API](https://nautechsystems.github.io/nautilus_docs/python-api-nightly/)
displayed `v2.0.0rc4`. The handoff changed no dependency. Local `DataActor` typed
publish/subscribe/unsubscribe stubs and the existing rc3 routing fixtures were inspected; no
provider, persistence, performance, or connected acceptance was repeated. The separate upgrade now
pins `2.0.0rc4`; use its current-status evidence for the new baseline and recheck exact APIs before
each slice. Older rc3-specific findings below retain their historical scope; future slice gates
must run against the current locked version.

## Accepted Decision Record

These decisions govern the V3-03 plan. Each implementation slice still requires its own reviewed
and approved batch.

| Decision | Accepted disposition |
|---|---|
| Responsibility topology | Accept five logical and physical owners for the first implementation: completed-bar foundation, direct completed-bar metrics, session-reference metrics, analytical-window metrics, and rolling measurements. Do not create a generic capability manager. |
| Foundation instances | Start with one statically composed, bounded multi-series foundation instance for the exact reviewed ES scope. Do not create one actor per series or one actor per instrument. Set `maximum_series_per_instance = 16` and `maximum_total_series = 64`; these are safety ceilings, not measured capacity claims. Permit later static partitioning only after measured need. |
| Series assignment configuration | Define canonical series independently from deployment ownership. Each statically configured foundation instance explicitly lists its `series_ids`; validation requires every enabled series to appear exactly once, rejects duplicate or unknown assignments, and enforces the 16-series instance and 64-series total ceilings. Never auto-place or silently reshuffle a series. Derive the producer/partition manifest from this validated configuration. |
| Canonical bar authority | Every admitted completed-bar series resolves to exactly one foundation actor instance and one canonical writer. Direct metrics and rolling calculations never admit, aggregate, revise, or republish canonical bars. |
| First canonical series | The first reviewed profile consumes `ESU6.CME-5-SECOND-LAST-EXTERNAL` live input and publishes only `ESU6.CME-1-MINUTE-LAST-EXTERNAL` canonical output. Five-minute, fifteen-minute, hourly, and other coarser canonical outputs require separate series review; when accepted, the foundation rather than a metric owner produces them. Native composites remain a later parity candidate. |
| First convergence cohort | Prove 15 `COMPLETE` historical one-minute bars followed by five newly `COMPLETE` live one-minute bars as exactly 20 unique, contiguous canonical bars. History ends and live continuation begins at one exact minute boundary; no forming or partial first live minute is published in this complete-only acceptance cohort. This is an acceptance population, not runtime duration, retention, or the operational recovery horizon. |
| Cold-start reconstruction | On a whole-runtime cold start or restart, each enabled owner declares the purpose-specific history required to reconstruct its state. Session-to-date, previous/overnight boundaries, analytical windows, rolling warmup, baselines, and compatible predecessors are not limited to the 15-bar convergence cohort. Same-run late attachment or independent consumer restart remains deferred because V3-03 adds no completed-bar replay/snapshot contract. |
| Completed-bar retention and overlap | For the first series set `maximum_retained_completed_bars_per_series = 16`, `maximum_history_live_overlap_bars = 1`, `maximum_buffered_live_completed_bars_per_series = 2`, and `revision_policy = "reject"`. Drop and count equal duplicates; treat unequal same-identity observations as a terminal integrity conflict for that series; reject and count observations older than the retained watermark window as stale. The two-bar pending-live bound is derived from the accepted one-minute output and unchanged 30-second historical request timeout. |
| Canonical metric authority | A composition-time producer manifest fails closed if two enabled owners claim the same complete metric subject. Actor-local registries remain formula validators, not global uniqueness authority. |
| Producer-manifest representation | Composition derives one immutable `ProducerManifestV1` from validated configuration and canonical catalogs before constructing `LiveNode`; there is no second hand-authored manifest. It contains schema version, configuration epoch/digest, sorted exact bar-series ownership/partition entries, sorted typed metric-producer claim entries, dependencies, activation disposition, and a deterministic manifest digest. Each actor receives only its immutable relevant entries plus the full digest; readiness acknowledgements echo that digest. Validation fails closed before actor construction or provider demand. |
| Subject identity | Introduce complete completed-bar and metric subject identities before any replacement owner publishes canonical data. An opaque `session_id`, metric ID, or bar specification alone is insufficient. |
| Startup delivery | All enabled numerical consumers start gated and attempt to subscribe to their exact canonical completed-bar series. Before foundation demand, each participating numerical consumer must acknowledge subscription readiness; a consumer quarantined by the accepted timeout is excluded from the sealed run set. Participating consumers reconstruct and become evidence-ready independently; no required consumer attaches after foundation warmup. Completed-bar snapshots and same-run consumer recovery are deferred. Visual Debug is the explicit passive exception: it is composed and subscribed before publishers but is not in the required readiness set and cannot delay demand. |
| Readiness acknowledgement | Every required numerical consumer publishes one typed acknowledgement per exact `(consumer_actor_id, series_id)` pair immediately after subscribing and validating the expected series and producer manifest. The acknowledgement carries the startup epoch, consumer actor ID, series ID, manifest digest, subscription status, timestamp, and an explicit reason when rejected. The foundation owner's own clock sampled when the callback is admitted decides timeliness; the consumer timestamp remains evidence only. `SUBSCRIBED` means only that bar delivery cannot be missed; metric/evidence readiness remains a later independent state. Visual Debug publishes no readiness acknowledgement. |
| Readiness timeout and failure | Set `consumer_readiness_timeout_ms = 5000`. Begin demand immediately when the expected acknowledgements arrive. At timeout, quarantine only missing/rejected consumers for that run and continue the series for acknowledged consumers; if no consumer acknowledged a series, publish no demand for it. Reject late acknowledgements and recover quarantined consumers through a whole-runtime restart in V3-03. |
| Late-consumer recovery scope | V3-03 may quarantine a consumer which misses the startup barrier and require a whole-runtime restart for recovery; healthy acknowledged consumers continue. This is a deliberate temporary scope limit, not accepted steady-state resilience. A mandatory later capability must let every configured late, failed, or restarted consumer subscribe, buffer live input, reconstruct purpose-specific history through an exact watermark, reconcile, and rejoin without corrupting canonical order. No actor may remain permanently left behind after a recoverable failure. |
| First historical usage | Classify the 15 completed historical `ESU6.CME` one-minute bars as `canonical_series_bootstrap`. They are the ordered prefix of the same canonical `es_1m` series continued by live bars, so the foundation validates and publishes them once to every acknowledged subscriber. They are not a local bounded calculation. |
| Historical routing | Historical usage is classified per requirement, not per actor. Historical observations enter the foundation only when explicitly declared as `canonical_series_bootstrap`. A `bounded_batch_calculation` uses shared pure validation, remains local to its requesting owner, publishes no canonical bars, and discards raw observations after calculation. One continuing live actor may declare both kinds for different needs. |
| Historical validation disposition | The shared pure validator returns a structured `COMPLETE`, `PARTIAL`, or `REJECTED` result. `COMPLETE` means the exact requested evidence is valid and present. `PARTIAL` returns usable ordered observations plus explicit missing/gap facts without claiming completeness. `REJECTED` means identity, schema, ordering, or same-interval content is unsafe and no calculation or canonical admission may proceed. Evidence incompleteness is data state, not an exception; programmer/configuration contract violations may still raise before runtime use. |
| Historical exact duplicates | Within the configured hard raw-batch bound, collapse identical same-identity historical observations into one ordered accepted observation, count each duplicate, and merge its additional lineage/evidence references. Exact duplicates do not prevent `COMPLETE` when all requested unique intervals are present and never calculate or publish twice. Unequal same-identity content remains `REJECTED`. |
| Historical validator envelope | Every immutable result carries request ID/digest and usage, exact series identity, requested UTC bounds, disposition, raw/accepted-unique/duplicate/conflict/gap counts, exact missing or gap intervals, evidence health and fidelity, lineage/evidence references, typed reason codes, and ordered unique bars only for `COMPLETE` or `PARTIAL`. `REJECTED` exposes no usable bars. A requesting owner may calculate from `PARTIAL` only when its own policy permits and must preserve the validator disposition and reasons in its output. |
| Subscriber routing | Route canonical completed bars through metadata-qualified Nautilus `DataType` values whose stable schema-versioned type name carries exactly one bounded, topic-safe `series_id` metadata value. Publishers, subscribers, and unsubscription use the identical `DataType`. Payload identity must match the route. Do not use `DataType.identifier`, raw message-bus injection, or type-only fan-out as the first contract. |
| Canonical wire-type names | Accept `markeitech.completed_bar.canonical.v1` for canonical closed-interval bars and `markeitech.metric.value.v2` for the breaking replacement of the incomplete metric-value contract. Encode schema versions in the stable type names and never dual-publish old and new canonical types in one active profile. |
| Completed-bar public API | Make `CompletedBarV1`, `CompletedBarSeriesIdentity`, `CompletedBarInputIdentity`, `CompletedBarLineageEntry`, `BarCompletionState`, and `VolumeState` public V2 Python APIs because independent actors exchange and interpret them. Give them stable exports, public docstrings, public-surface registry coverage, and compatibility tests. Keep the foundation actor, aggregation buckets, ledgers, deduplication, validation, conversion, and codec mechanics private unless separately reviewed. |
| Metric public API | Make the v2-schema `MetricValue`, `MetricSubjectIdentity`, `MetricValueKind`, `MetricHealth`, `MetricFidelity`, and typed `MetricReasonCode` public V2 Python APIs because independent actors publish and consume them. Give them stable exports, public docstrings, public-surface registry coverage, and compatibility tests. Keep new formula implementations, rolling-state mechanics, owner actors, and new internal registries private unless separately reviewed. |
| Canonical payload bounds | Apply the accepted final field-and-bound table to `CompletedBarV1`, its nested public identities/lineage, `MetricValue` v2, and `MetricSubjectIdentity`. Bound `series_id` to 64 safe ASCII characters; other identifiers and enum tokens to 128 ASCII characters; text metric values to 512 Unicode characters; typed reason tuples to 16 entries; total deduplicated evidence references per payload to 256 entries of at most 256 characters; and completed-bar lineage to 64 entries. Use positive signed 64-bit timestamps, sequences, and revisions plus UUID runtime epochs. Missing subintervals cannot exceed the declared constituent count, which is exactly 12 for the first ES one-minute series. Decimal precision remains definition-owned with no float conversion or global truncation. Reject and count an over-bound payload; never truncate it. |
| MetricRegistry compatibility | Preserve the already-public `MetricRegistry` and its compatible public surface through V3-03. Do not make it private or replace it as an incidental part of the owner split. New producer, owner, or rolling-state registries remain private; any future `MetricRegistry` removal or replacement requires a separate API-migration decision. |
| Operational API privacy | Keep `ProducerManifestV1` and its producer claims, startup-readiness acknowledgements, historical validator/result envelopes, foundation ledgers/buckets/counters, actor classes, and new internal registries private. They remain typed, bounded, documented internally, and fully tested, but are orchestration mechanics rather than supported extension APIs. |
| Completed-bar payload identity | Every canonical completed-bar payload carries both its short routing `series_id` and the complete immutable `CompletedBarSeriesIdentity`. The canonical identity includes instrument/venue, canonical bar specification, interval, timestamp/completion/aggregation/revision policy, calendar/profile/configuration identity, and canonical producer/schema identity. Provider, adapter, source-stream, selector, and source-schema identity belong only to one exact `CompletedBarInputIdentity` on each lineage entry. Historical and live inputs therefore converge into one canonical output identity without erasing their distinct source paths. Consumers validate the route, payload identity, lineage input identities, and manifest together; they do not recover meaning from the short ID alone. |
| Live completion grace | `completion_grace_ms` is a private startup-only, typed, versioned foundation policy with default `1000` and inclusive configuration envelope `1..5000`. The immutable cutoff is `interval_end_ns + completion_grace_ms * 1_000_000`. A callback is eligible only when the foundation owner's admission-clock sample is strictly before cutoff; exactly at or after cutoff is late and cannot mutate the interval. A timer firing at or after cutoff seals once and never extends the cutoff or authorizes a revision. |
| Completed-bar event time | Set `timestamp_policy = "interval_end"`. A canonical bar for `[interval_start_ns, interval_end_ns)` uses `interval_end_ns` as its event time for both historical and live lineage. Source-receive, normalization, and foundation-publication timestamps remain separate fields. Forming bars are never canonically published. |
| Completed-bar volume truth | Never use numeric zero for unknown volume. Preserve observed zero as `0` with `VolumeState.OBSERVED`; use null with `VolumeState.UNSUPPORTED` when the source cannot supply volume and null with `VolumeState.MISSING` when expected volume is absent. Preserve an observed partial amount only with `VolumeState.PARTIAL`. Price evidence may remain usable, but volume-dependent outputs must retain partial/unavailable truth. |
| Completed-bar value representation | Publish a versioned custom `CompletedBarV1` payload rather than embedding a native Nautilus `Bar`. Copy prices and available volume exactly from Nautilus fixed-point values without any `float` conversion. Represent volume as `Decimal | None` plus a typed `VolumeState` enum: `OBSERVED`, `MISSING`, `UNSUPPORTED`, or `PARTIAL`. Negative sentinels and free-form reason strings are forbidden. Preserve exact round-trip precision in the reviewed codec before any serialized transport is accepted. |
| Completed-bar completion state | `markeitech.completed_bar.canonical.v1` represents a closed interval and carries typed `completion_state: BarCompletionState` with `COMPLETE` or `PARTIAL`; it does not use a boolean. A one-minute live bar is `COMPLETE` with exactly 12 contiguous valid five-second constituents. With one through eleven valid constituents it is published once as `PARTIAL` with truthful OHLCV from only those observations, expected/received counts, exact missing subintervals, typed reasons, health/fidelity, timestamps, and evidence references. With zero valid constituents there is no OHLCV bar to publish; only bounded health/audit records the missing interval. `BarCompletionState.PARTIAL` is distinct from `VolumeState.PARTIAL`. |
| Partial-bar calculation | Every canonical numerical consumer uses a `PARTIAL` bar as input and marks every affected calculated output `DEGRADED`, preserving the partial completion state, missing intervals, health/fidelity, and lineage. The payload does not expose the raw constituent bars. The separately accepted future closed-period-average contract remains an explicit exception: it emits a typed non-value placeholder instead of a degraded numeric value. |
| Partial-input recovery | Degradation clears only when the metric's mathematics no longer depend on the partial input. A stateless current-bar metric recovers on its next `COMPLETE` input; a fixed rolling metric recovers after the partial input leaves every relevant window; a recursive metric such as EMA recovers only after clean reconstruction or an explicit reviewed reset. One later complete bar never clears degradation merely by arrival. |
| Degraded metric value | `MetricValue` v2 uses `DEGRADED` only when a defensible typed scalar result exists. It carries the value, unit, typed degradation reasons, and exact affected-input lineage. If no defensible result exists, `value` is null and health is `UNAVAILABLE` with typed reasons. Numeric zero is never substituted for unavailable evidence. |
| Metric scalar representation | `MetricValue` v2 carries explicit public `MetricValueKind`: `NUMBER` requires `Decimal`, `INTEGER` requires `int` but rejects `bool`, `BOOLEAN` requires `bool`, and `TEXT` requires a bounded string. `value` must match its kind exactly or be null only under a typed non-value health state. Canonical publication forbids `float`; any internal floating-point calculation must convert deterministically before publication and pass exact codec tests. |
| Metric unit identity | Each versioned metric definition owns one bounded canonical `unit_id`; it is neither a fixed wire-schema enum nor a free-form publication choice. `MetricValue` echoes that exact `unit_id` and publication fails on a definition/value mismatch. Reviewed metric definitions may add units without changing the wire schema. |
| Metric timestamps | `MetricValue` v2 carries five UTC-nanosecond timestamps with distinct meanings: `effective_ts_ns` is the market boundary the value describes; `observed_ts_ns` is the latest required source-observation time; `received_ts_ns` is when the owner received its final required input; `calculated_ts_ns` is calculation completion; and `published_ts_ns` is canonical publication. Enforce `observed <= received <= calculated <= published`; `effective_ts_ns` remains semantic event time and need not equal processing time. Use effective time as `ts_event` and published time as `ts_init`. |
| Metric reason codes | `MetricValue` v2 carries an immutable tuple of zero through 16 unique typed `MetricReasonCode` values in deterministic canonical enum order. Multiple simultaneous limitations remain visible rather than being collapsed into one reason. Reject duplicate, out-of-order, untyped, or over-bound reason collections before publication. |
| Metric health reasons | `MetricHealth.READY` requires an empty reason tuple. Every other metric health state requires at least one typed reason. A value with any active limitation cannot claim `READY`, and a non-ready value cannot omit the reason for its state. |
| Metric health/value presence | `READY` and `DEGRADED` require a non-null current value. `STALE` requires the last defensible non-null value plus a staleness reason. `WARMING`, `UNAVAILABLE`, `UNSUPPORTED`, and `FAILED` require a null value plus typed reasons. A null `READY`/`DEGRADED`/`STALE` value or non-null `WARMING`/`UNAVAILABLE`/`UNSUPPORTED`/`FAILED` value is invalid before publication. |
| Metric revision continuity | Each exact `MetricSubjectIdentity` has a positive contiguous revision chain scoped to one runtime `run_epoch`. Its first published value is `(revision = 1, previous_revision = None)` and each later value is `(revision = N, previous_revision = N - 1)`. The chain resets only under a new runtime epoch. Revisions order the evolving metric subject; they are not completed-bar corrections. |
| Metric revision duplicate/conflict | An identical repeat of the same metric subject, runtime epoch, and revision is a duplicate and is dropped and counted. An unequal repeat of the same revision is a malformed incoming message: reject and count only that message, retain the last accepted value, and allow the metric subject to continue. A changed truth is accepted only as revision `N + 1` with `previous_revision = N`; a later timestamp never substitutes for a missing revision increment. |
| ATR predecessor correction | ATR with window `N` requires `N + 1` compatible bars: one exact predecessor `B0` plus the `N` measured bars `B1..BN`. `B0` supplies only the previous close for `B1` and is cited in lineage; it is not an extra ATR sample. A missing or incompatible predecessor produces null `UNAVAILABLE` rather than substituting `B1.high - B1.low`. A partial predecessor or measured bar participates in the calculation and keeps the output `DEGRADED` until its influence leaves the window under the accepted recovery rule. |
| Zero-median baseline behavior | Calculate expansion ratio and percentile as independent outputs with independent health. When the reference median is zero, the expansion ratio is null `UNAVAILABLE` with typed reason `BASELINE_MEDIAN_ZERO`; never substitute epsilon, zero, or infinity. Percentile remains mathematically valid and is calculated normally, carrying `DEGRADED` only when its own inputs are degraded. A shared health result may not invalidate a valid percentile or attach a non-null value to `UNAVAILABLE`. |
| Partial-bar finality | Under the accepted `revision_policy = "reject"`, a published partial bar is final for V3-03. A later constituent cannot upgrade or replace it during the run and is rejected and counted as late or stale under the series policy. Canonical revision and dependent-metric recalculation remain outside V3-03. |
| Completed-bar revision semantics | `markeitech.completed_bar.canonical.v1` carries no `bar_revision` field because V3-03 never accepts canonical revisions. `(series_id, interval_start_ns, interval_end_ns)` is the observation identity: an equal repeat is a duplicate and an unequal repeat is a terminal integrity conflict for that series. Source correction or revision metadata remains lineage for rejection and audit. Any future acceptance of canonical revisions requires a separately reviewed `markeitech.completed_bar.canonical.v2` contract. |
| Completed-bar publication sequencing | Every published canonical bar, whether `COMPLETE` or `PARTIAL`, carries the immutable runtime `run_epoch` and a positive, monotonic `publication_sequence` scoped to its exact series. The sequence starts at 1 for each series in each runtime epoch, spans historical bootstrap and live operation without resetting, and advances once per bar publication. It detects bar-delivery loss or reordering; interval identity and the bar's completion evidence describe market-data gaps. Neither field is part of market observation identity. |
| Completed-bar source lineage | One canonical bar carries a bounded ordered collection of typed `CompletedBarLineageEntry` values rather than one source label. Each entry identifies `HISTORICAL` or `LIVE`, the provider observation/evidence references, source timestamps, and source correction metadata. Equal historical/live or same-source observations merge their distinct lineage into the one admitted bar; they never cause a second publication or force one source's evidence to be discarded. |
| Future closed-period placeholder debt | A future closed-period average whose required evidence is missing, unsupported, or partial must emit an explicit typed non-value placeholder state at the expected boundary rather than numeric zero, a guessed value, or silence. The exact metric owner and schema are deferred and are not added to V3-03 merely to resolve this debt. |
| Configuration schema migration | Allocate system configuration schema `24` to the V3-03 split. Migrate the tracked example and V3 ES profile together through one cold, atomic cutover. Do not support schemas 23 and 24 simultaneously, accept schema 23 with any new split section, or retain both old and new configuration shapes. |
| Completed-bar configuration section | Configure the canonical-bar foundation under top-level `[completed_bars]`, outside `[metrics]`. Define each canonical series once in `[[completed_bars.series]]` and assign those IDs explicitly through `[[completed_bars.instances]]`. Use `COMPLETED-BARS-1` for the first instance and reserve the numeric suffix for later static partitions without renaming it. Completed bars are canonical metric inputs, not metrics, and the configuration hierarchy must preserve that ownership boundary. |
| Direct completed-bar metric configuration | Configure direct completed-bar calculations under `[metrics.completed_bar_metrics]` with canonical actor ID `COMPLETED-BAR-METRICS`. This owner consumes exact `[completed_bars]` series but cannot define, aggregate, revise, or republish them. |
| Session-reference metric configuration | Configure active-session, previous-session, overnight, and gap reference calculations under `[metrics.session_reference_metrics]` with canonical actor ID `SESSION-REFERENCE-METRICS`. It consumes canonical bars and immutable calendar/session evidence but owns no bars or calendar truth. |
| First session-reference profile | Enable every reviewed `active_session.*` and `previous_session.*` metric plus `gap.opening.points` and `gap.opening.ratio`. Keep every `overnight.*`, `gap.indicative.points`, and `gap.indicative.ratio` metric disabled and unclaimed because the first ES profile has no separately enabled overnight phase. Configuration exposes explicit family switches; disabled families publish neither placeholder values nor canonical claims. |
| Analytical-window metric configuration | Configure opening-range and other calendar-relative analytical-window calculations under `[metrics.analytical_window_metrics]` with canonical actor ID `ANALYTICAL-WINDOW-METRICS`. It consumes canonical bars and immutable window/session evidence but owns no bars, calendar truth, or session-reference outputs. |
| First analytical-window profile | Enable `opening_range_fast` as a 15-minute window and `opening_range_slow` as a 30-minute window. Anchor both to the configured session start, calculate both from canonical `es_1m` bars, and publish each window's complete reviewed `opening_range.*` metric family. Keep `power_hour` and every other analytical window disabled and unclaimed. |
| Rolling-measurement configuration | Configure ATR, rolling range, efficiency, baseline, and later separately reviewed recursive families under `[metrics.rolling_measurements]` with canonical actor ID `ROLLING-MEASUREMENTS`. It consumes exact canonical bar series and owns only its declared numerical subjects. |
| First rolling profile | Enable only the one-minute `fast` family on canonical `es_1m`, with `context_45m` and `expansion_10m` as its only active candidates and `context_45m` as the selected context. For each candidate publish the reviewed range, realized-log-return magnitude, ATR, directional-efficiency, coverage, recent/phase expansion-ratio, percentile, and reference-count outputs. Default to eight recent references and five phase-matched references while retaining safety ceilings of 64 and 30 respectively. Keep all other fast candidates and the `tactical` and `structural_intraday` families disabled and unclaimed. |
| First-profile activation and Visual Debug | After their independent offline gates pass, cold-start the completed-bar foundation, all four accepted numerical owners, and `VISUAL-DEBUG-CAPTURE` in the V3 ES acceptance profile. The five canonical owners become evidence-ready independently; there is no global all-metrics-ready barrier. Visual Debug is a sixth passive actor, never an owner or producer. Start its exact bar and metric subscriptions before publishers, but exclude it from the foundation's required-consumer readiness set. It creates no demand or special history, and its subscription, collection, rendering, deadline, overflow, or output failure affects only the review artifact. Each separately authorized run selects the exact owner or candidate under review; the first bar/direct-metric artifact selects the accepted 15 historical plus five live `es_1m` bars. Entity Analysis remains disabled. |
| Connected acceptance | Require a separately authorized run for each exact owner/window/candidate. Reconcile configuration, manifest, subscriptions, demands, inputs, values, units, timestamps, health, fidelity, reasons, lineage, revisions, counts, resource bounds, shutdown, and Visual Debug artifacts. Permit only identified and counted equal overlap duplicates; require zero unequal conflicts, accepted bar revisions, unexplained sequence gaps, or unaccounted drops. Capture-on/off must leave upstream counts and behavior identical. The foundation run requires exactly 15 historical plus five live `COMPLETE` bars as 20 unique contiguous `es_1m` bars; direct metrics reconcile all seven outputs for that cohort; session references require one reconstructed complete previous session and the configured current-session opening boundary; analytical windows require both accepted completion boundaries; and rolling requires complete 45-minute and 10-minute calculation evidence, eight recent references, and five phase-matched references. If a required condition does not occur, record `CONDITION_NOT_OBSERVED`; never infer acceptance or automatically extend or rerun. |
| Cutover | Because the old actor is disabled in both tracked profiles, use offline/isolated shadow parity followed by a cold-start, composition-enforced single-writer activation. Do not reactivate the faulty actor as a canonical producer in a tracked profile and do not perform same-run hot replacement. |
| Review order | Accept one exact ES series and owner at a time: bars, direct metrics, session references, each analytical window, then each rolling family/timeframe. Include Visual Debug as a passive projection in each bounded connected review without allowing it to gate or change the producer under review. |

These dispositions narrow the earlier role-review proposal to the verified post-V3-02 baseline. In
particular, there is no active old writer to fence during a live handoff. The cutover fence is
therefore configuration and composition: one runtime plan contains either the dormant legacy
actor in an isolated noncanonical fixture or the new canonical owners, never both as canonical
publishers. Exactly-one ownership applies per complete series, not to one universal actor instance.

## Planning Decision Closure

No V3-03 architecture or acceptance decision remains open in this plan. Accepted first-series,
capacity, retention, overlap, revision, convergence, metric-family, Visual Debug, and connected-run
values are recorded above. Low-level partial-bucket and callback/publication work limits must be
derived from these accepted safety ceilings, made explicit in the applicable implementation-slice
configuration batch, and reviewed before that batch is enabled; they are not authorization to
change the accepted topology, semantics, or connected scope.

## Authority And Verified Baseline

This plan is subordinate to:

1. [`markeitech.md`](../../markeitech.md);
2. [`docs/current-status.md`](../current-status.md);
3. [`docs/development-guidelines.md`](../development-guidelines.md);
4. [`v2-session-evidence-health.md`](../architecture/v2-session-evidence-health.md);
5. [`v3-02-session-state-actor-implementation-plan.md`](v3-02-session-state-actor-implementation-plan.md);
6. [`v3-03-session-metrics-actor-split-review.md`](../notes/v3-03-session-metrics-actor-split-review.md);
7. [`v3-visual-debug-review-contract.md`](../notes/v3-visual-debug-review-contract.md); and
8. [`system-dataflow-maintenance.md`](../architecture/system-dataflow-maintenance.md).

Verified at the planning baseline:

- V3-01 makes `SessionStateActor` the only mcal-backed calendar evaluator owner.
- V3-02 supplies strict current-state transition/snapshot delivery and a reusable bounded
  subscribe-buffer-snapshot-reconcile protocol.
- `EvidenceHealthActor` and `HistoricalEvidencePlannerActor` use that protocol now.
- `SessionMetricsActor`, dependent Entity Analysis, and Visual Debug are absent from both tracked
  active actor plans. Their code and tests are dormant migration evidence, not canonical runtime
  authority.
- The dormant `SessionMetricsActor` still combines feed demand, consumer attachment, calendar
  projection, bar normalization and aggregation, historical/live convergence, bar admission,
  four numerical families, derived bars, multiple timers, and one shutdown summary.
- `CompletedBarInput.key` currently contains only instrument, bar specification, and interval end.
  Its payload lacks canonical calendar-definition digest/effective epoch, provider/stream
  identity, configuration epoch, and producer epoch.
- `MetricValue` currently identifies a formula/version, parameter version, instrument, optional
  session string, timestamps, health, fidelity, source, evidence, and revision. It does not fully
  identify timeframe, profile, calendar epoch, window, rolling family/candidate, parameter
  effective time, configuration epoch, or canonical producer.
- `MetricRegistry` rejects duplicate definitions only inside one registry. Composition has no
  global canonical-output manifest.
- The current rolling owner path creates and publishes derived completed bars, which is
  incompatible with a separate foundation owner being the only canonical bar writer.
- Pure calculation and state modules already exist for completed-bar metrics, session references,
  analytical windows, and rolling measurements and should be reused rather than rewritten.
- The tracked configuration schema is 23. Both tracked profiles retain the complete combined
  configuration only as a disabled surface.
- Historical planning and acquisition remain separately owned. The accepted provider path is
  still bounded to one outstanding request, one in-flight request, and one attempt.
- The visual-review contract carries two verified rolling blockers: ATR lacks the compatible
  predecessor outside the selected window, and zero-median baseline publication can construct an
  unavailable non-null metric.

The connected V3-01 and V3-02 runs are prerequisite evidence only. They do not accept completed
bars, formula values, the owner split, producer uniqueness, completed-bar startup delivery, or the
V3-03 cutover.

## Purpose And Completion Claim

V3-03 answers one bounded question:

> How can Markeitech replace the disabled combined session-measurement actor with independent
> canonical completed-bar and numerical-measurement owners without duplicating calendar,
> provider, bar, or metric authority?

V3-03 may be marked implemented only when:

- complete bar-series, bar-observation, metric-subject, producer, and epoch identity plus metric
  revision identity is accepted and enforced;
- composition can prove one canonical writer and one deterministic instance assignment for every
  enabled bar series and one writer for every metric subject;
- the foundation owner alone normalizes, aggregates, converges, admits, and publishes canonical
  completed bars;
- only `canonical_series_bootstrap` history enters that canonical stream, while bounded
  historical-only calculations validate locally and publish no canonical bar;
- each numerical owner consumes only canonical bars and the exact additional canonical temporal
  facts it requires;
- required numerical consumers subscribe and acknowledge readiness before foundation demand or
  publication, while timed-out consumers are quarantined from the sealed run set; passive Visual
  Debug subscribes first but is explicitly outside that required set;
- whole-runtime cold start reconstructs each enabled owner's bounded continuing state from its
  declared purpose-specific history rather than from a universal 15-minute lookback;
- every independent owner and every foundation series has bounded retained state, work, timers,
  failures, and shutdown behavior;
- the existing accepted pure calculations are preserved, with the two known rolling correctness
  defects either corrected and accepted or the affected rolling outputs left disabled;
- the dormant combined actor and its configuration are retired without a dual-canonical period;
- the exact reviewed ES producer set passes offline gates and separately authorized bounded
  connected acceptance; and
- status, architecture manifest, generated diagrams, API documentation registries, and code agree.

The completion claim does not include broad multi-instrument calibration, all calendar types,
visual acceptance beyond the exact selected V3-03 review artifacts, entities, semantic events,
dynamic capability activation, performance at unmeasured scale, the future closed-period
placeholder metric, or provider behavior not observed in the authorized runs.

## Scope

### In scope

- complete canonical completed-bar series and observation identity;
- complete metric subject and producer identity;
- a global composition-time bar/metric producer manifest;
- one deterministic series-to-foundation-instance map with per-instance and total bounds;
- one subscribe-and-ready-before-demand startup handshake;
- a shared pure validator for `bounded_batch_calculation` history;
- the exact first `ESU6.CME` five-second-live-input to one-minute-canonical-output series, its
  15-history/five-live convergence cohort, and accepted admission/resource bounds;
- `CompletedBarFoundationActor` for configured native inputs and `canonical_series_bootstrap`
  history, deterministic aggregation, overlap convergence, admission, canonical publication, and
  producer health;
- separate direct completed-bar, session-reference, analytical-window, and rolling metric actors;
- independent typed configuration, activation, resource bounds, and historical requirements for
  every owner and rolling family;
- reuse of accepted pure calculation books, registries, policies, and fixtures;
- focused correction and parity evidence for the two already verified rolling blockers before the
  affected outputs can be enabled;
- passive Visual Debug migration to the new canonical bar/metric contracts, one exact bounded
  review selection per authorized run, capture-on/off non-interference, and review artifacts;
- a cold-start single-writer cutover in the exact reviewed ES profile;
- purpose-specific whole-runtime cold-start reconstruction without persistence or replay;
- retirement of `SessionMetricsActor` only after all enabled responsibilities have accepted
  replacements;
- focused unit, actor, lifecycle, composition, disconnected integration, and authorized connected
  evidence; and
- the smallest authoritative status, architecture, diagram, and API-surface updates required by
  the implemented topology.

### Explicitly out of scope

- changing V3-01 calendar definitions, product phases, corrections, mcal ownership, or schedule
  truth;
- changing the V3-02 current-state contracts or active consumer semantics except reuse by the new
  calendar-dependent owners;
- provider pacing, retry, callback correlation, request concurrency, cancellation, or IB adapter
  redesign;
- new provider subscriptions or historical requests merely for shadow comparison;
- native Nautilus composite-bar or indicator adoption;
- enabling a five-minute, fifteen-minute, hourly, or other coarser canonical output in the first
  ES profile without a separate reviewed series decision;
- raw bar or metric persistence, replay, backtesting, restoration, or durable recovery;
- reactivating Entity Analysis, market-structure consumers, or Discord analytical output as part
  of V3-03;
- changing existing metric meaning or adding a new metric to justify the split;
- cross-calendar analytical windows;
- dynamic actor loading, same-run actor replacement, failover, or a general capability manager;
- completed-bar snapshot/watermark recovery for late, detached, restarted, or dynamically loaded
  consumers within V3-03; this remains a mandatory follow-on before dynamic activation or a
  same-run consumer-recovery claim;
- Watchlist membership or dynamic observation-universe changes;
- semantic events, options intelligence, opportunities, Sir Loke, ML, recommendations, orders, or
  execution; and
- connected IB, PostgreSQL, Discord, paid, or external runs without separate exact authorization.

## Target Runtime Topology

```text
Nautilus native bars                  transient HistoricalBatch
        |                                      |
        |                         +------------+-------------+
        |                         |                          |
        |          canonical_series_bootstrap   bounded_batch_calculation
        |                         |                          |
        +-------------------------+                          v
                    |                              pure batch validation
                    v                                      |
     bounded multi-series foundation                      v
     - independent state per exact series       requesting historical owner
     - deterministic series-to-instance map     calculates one bounded result
     - normalize and aggregate                   and discards raw observations
     - converge historical/live overlap
     - admit duplicate/conflict/revision truth
     - publish each canonical bar once
                    |
          exact-series completed-bar stream
                    |
       +------------+-------------+------------------+
       |            |             |                  |
       v            v             v                  v
CompletedBar   SessionReference  AnalyticalWindow  RollingMeasurements
MetricsActor   MetricsActor       MetricsActor      Actor
       |            |             |                  |
       +------------+-------------+------------------+
                    |
                    v
             canonical MetricValue v2
                    |
                    v
       passive VisualDebugCaptureActor
       - also selects exact `es_1m` bars
       - never requests or calculates evidence
       - writes bounded ignored review artifacts
```

`HistoricalEvidencePlannerActor` still resolves symbolic evidence needs. `DataAcquisitionActor`
still admits and executes exact plans. A `HistoricalBatch` remains transient. The foundation may
canonicalize a returned batch only when its typed requirement declares
`canonical_series_bootstrap` and the composition manifest maps it to one admitted series and
foundation instance; it must ignore unrelated batches. A `bounded_batch_calculation` is validated
locally, cannot publish canonical bars or join continuing live state, and discards raw observations
after the named calculation. Enabled canonical-series consumers subscribe and acknowledge
readiness before foundation demand begins.

Visual Debug is deliberately outside the canonical ownership chain. It starts its exact
metadata-qualified `es_1m` bar subscription and canonical MetricValue v2 subscription before the
publishers, filters immediately by complete payload/manifest identity and the configured bounded
subject allowlist, and never acknowledges as a required foundation consumer. Missing projection
data makes the capture partial or failed; it cannot delay or change upstream demand or output.

## Ownership Matrix

| Concern | Canonical owner | Explicit non-owner |
|---|---|---|
| Calendar definition, state, and projection | `SessionStateActor` | All V3-03 owners |
| Symbolic historical need resolution | `HistoricalEvidencePlannerActor` | All metric actors and acquisition |
| Provider request execution and lifecycle | `DataAcquisitionActor` | All analytical actors |
| Canonical live/bootstrap bar normalization | Assigned foundation actor instance | Numerical owners |
| Historical/live convergence and conflict | `CompletedBarFoundationActor` | Numerical owners and projections |
| Smaller-to-larger canonical aggregation | `CompletedBarFoundationActor` | `RollingMeasurementsActor` |
| Bounded historical-only validation | Shared pure validator used by requesting owner | Foundation and canonical bar stream |
| Direct OHLCV/return/true-range metrics | `CompletedBarMetricsActor` | Foundation owner |
| Session/previous/overnight/gap references | `SessionReferenceMetricsActor` | Calendar and window owners |
| Opening-range and other analytical windows | `AnalyticalWindowMetricsActor` | Session authority and references owner |
| Rolling families and baselines | `RollingMeasurementsActor` | Foundation and other metric owners |
| Canonical producer uniqueness | Validated composition manifest | Actor-local registry alone |
| Passive display and review artifact | `VisualDebugCaptureActor` for the exact configured review item | Every canonical producer; Visual Debug owns no market or metric truth |
| Operational audit | Existing persistence boundary for approved lifecycle facts | No raw bar/metric storage |

## Nautilus Alignment Matrix

The required Kite Nautilus consultation reached the current nightly guide and Python API roots and
reconciled them with the rc3-oriented checkout. A bounded follow-up checked the installed rc3
`Bar` and `Quantity` stubs for completed-bar value representation; it did not prove broad
nightly/current-pin semantic equivalence. The matrix therefore approves native runtime mechanics
already evidenced by the repository and leaves semantically richer replacement candidates
deferred.

| Requirement | Native candidate | Disposition | V3-03 boundary and acceptance |
|---|---|---|---|
| Actor lifecycle and scheduling | `DataActor`, actor `Clock`, timers/alerts | `USE_NATIVE` | Each owner uses native start/stop and clock facilities; prove cancellation, bounded stop, and no post-stop publication. |
| Live bar delivery and sharing | `Bar`, `BarType`, DataEngine routing, metadata-qualified `DataType` | `COMPOSE_NATIVE` | Acquisition retains logical/provider demand ownership; the foundation is a local consumer. Canonical custom data uses exact `series_id` metadata topics verified in-process on pinned rc3. Reconcile one provider stream per demand. |
| Canonical completed-bar truth | Native `Bar` inputs plus typed `CustomData` output | `ADAPT_NATIVE` | Native `Bar.volume` is mandatory and cannot represent missing or unsupported volume. Copy exact fixed-point OHLC and available volume into custom `CompletedBarV1`; never embed a native `Bar`, fabricate volume, use a negative sentinel, or convert through `float`. Markeitech owns full subject identity, normalization, convergence, admission, gaps, lineage, health/fidelity, revision rejection, and exact-series publication. |
| Smaller-to-larger aggregation | Native composite bars | `DEFER` | Keep the reviewed custom deterministic path in the foundation for V3-03. Any native replacement needs separate noncanonical parity for boundaries, partial/no-update intervals, timestamps, OHLCV, volume, overlap, and revisions. |
| Direct bar metrics | Native bar fields and registered indicators | `COMPOSE_NATIVE` | Native fields are inputs; Markeitech retains formula/version, predecessor lineage, missingness, and evidence envelope. Native indicator substitution is not part of the split. |
| Session references | Native bus/clock mechanics | `CUSTOM_RECOMMENDED` | Product semantics consume V3-01/V3-02 canonical facts; no local mcal and no provider execution. |
| Analytical windows | Native bus/clock mechanics | `CUSTOM_RECOMMENDED` | Opening-range and close-relative meaning remains versioned Markeitech policy, distinct from product phases. |
| Rolling measurements | Registered indicators and native bar updates | `DEFER` native replacement | Reuse accepted pure calculators over canonical inputs; require separate formula, warmup, reset, timestamp, revision, and session parity before considering a native replacement. |
| Startup delivery | Native typed subscription plus bounded readiness handshake | `COMPOSE_NATIVE` | Consumers subscribe to the exact canonical-bar series and acknowledge it before demand. Late/restarted-consumer snapshots remain deferred. |
| Passive Visual Debug | Native typed subscriptions, actor clock, and lifecycle | `ADAPT_NATIVE` | Subscribe with the exact metadata-qualified canonical bar `DataType` and the accepted canonical MetricValue v2 `DataType`, using the identical objects for unsubscribe. Filter metrics by complete subject and manifest claims. Visual Debug starts before publishers but is non-gating, publishes no readiness acknowledgement, creates no demand, and isolates its bounded writer and failures from every producer. |
| Persistence | Nautilus cache/database/catalog facilities | `DEFER` | No V3-03 durability requirement exists; bars, historical batches, metrics, and rolling state remain transient. |

If implementation needs a native behavior not already proven by the current checkout, stop for a
fresh installed rc3 API/stub check and exact nightly-page reconciliation. Class or method presence
alone is not semantic parity.

## Contract And Identity Model

### Canonical type identities

Use the accepted non-overlapping versioned custom-data type names:

```text
markeitech.completed_bar.canonical.v1
markeitech.metric.value.v2
```

Do not dual-publish the existing unversioned completed-bar type and the canonical replacement in
an active runtime. Shadow records use an explicitly noncanonical test namespace which production
consumers cannot subscribe to.

Canonical completed-bar routing uses one exact Nautilus data type per series:

```python
DataType(
    "markeitech.completed_bar.canonical.v1",
    metadata={"series_id": "es_1m"},
)
```

The type name owns only the wire-schema version. Routing metadata contains only the stable
configuration-derived series ID. That ID must be a bounded safe ASCII token or digest without
glob metacharacters, dots, equals signs, or undocumented escaping requirements. Complete series
identity remains in the payload and producer manifest; a subscriber rejects any route/payload
identity mismatch. `DataType.identifier` does not select the message topic and is not used for
routing. Raw low-level message-bus access would require an unjustified actor bridge and is not part
of V3-03.

### Completed-bar series identity

Every canonical completed-bar payload contains its short routing `series_id` and one immutable
`CompletedBarSeriesIdentity` with:

- exact Nautilus instrument ID, including contract and venue identity;
- provider and adapter/source-stream identity;
- source selector and canonical bar specification;
- interval duration, aggregation policy, timestamp interpretation, completion policy, and
  revision policy;
- calendar ID, definition version, definition digest, and definition effective epoch;
- analytical profile ID and version;
- configuration epoch/digest;
- canonical producer ID and producer/output schema version; and
- stable series ID derived from the validated fields.

The route's `series_id`, the payload's derived stable series ID, and the composition manifest must
match exactly before a consumer admits the observation. The full identity makes the payload
self-describing across configuration, calendar-definition, and producer-epoch changes; consumers
must not interpret the short routing token through actor-local assumptions.

Composition separately binds that stable series ID to exactly one statically configured
foundation instance. Actor-instance identity is not part of market subject identity and may change
only between reviewed startup configurations.

Historical and live source class must not split the canonical series; they are competing lineage
for the same interval and must converge. Their exact provider observation references, source
class, source timestamps, and transformation chain remain as distinct typed lineage entries on the
one bar observation.

### Completed-bar observation identity

One canonical observation is identified by:

```text
(series_id, interval_start_ns, interval_end_ns)
```

It also carries:

- immutable runtime `run_epoch` and positive per-series `publication_sequence`, starting at 1 and
  continuing without reset from historical bootstrap through live operation in that run;
- `interval_end_ns` as canonical event time under the accepted `interval_end` policy;
- typed `completion_state` of `COMPLETE` or `PARTIAL`, expected and received constituent counts,
  exact missing subintervals, and typed completion reasons;
- truthful OHLC from all and only the admitted constituents and truthful volume: observed zero
  remains zero, unsupported or missing volume is null with its typed state, and an observed
  partial amount carries `VolumeState.PARTIAL`;
- trade date, exchange state, product-phase memberships, and exact state/projection evidence;
- foundation publication UTC nanoseconds;
- a bounded ordered collection of typed `CompletedBarLineageEntry` values, each carrying
  `HISTORICAL` or `LIVE`, provider observation/evidence references, source observed/received/
  normalized UTC nanoseconds, the transformation chain, and any source correction metadata;
- health, fidelity, completion-basis evidence, and gap/coverage facts; and
- no source-independent correction or revision field.

The canonical payload has no `complete` boolean. Admission to
`markeitech.completed_bar.canonical.v1` proves the interval is closed, while typed
`BarCompletionState` reports its evidence completeness. A live one-minute bar with all 12
contiguous valid five-second constituents is `COMPLETE`. At interval close or expiry, one through
eleven valid constituents produce one `PARTIAL` bar whose OHLCV uses only those admitted
observations and whose coverage fields disclose exactly what is missing. The payload does not
expose the raw constituent bars. With zero valid constituents there is no truthful OHLCV bar to
publish, so bounded series health and audit record the absent interval. `BarCompletionState` is
independent of `VolumeState`.

The first V3-03 policy remains reject-conflict/reject-revision, so the v1 payload carries no
`bar_revision` field. Equal observation identity with unequal content is a hard conflict.
Historical/live equality is a duplicate with additional lineage, not a second canonical
publication. Any future canonical revision support requires a separately reviewed
`markeitech.completed_bar.canonical.v2` contract with explicit revision semantics.

A partial v1 bar is final once published. A later constituent for that interval cannot upgrade or
replace it and is rejected and counted as late or stale under the accepted series policy. Canonical
revision and dependent-metric recalculation remain outside V3-03.

Equal observations merge their distinct lineage entries before the one canonical publication.
Neither historical nor live evidence replaces the other. Exact repeated lineage references are
deduplicated, and the collection remains within the hard evidence bounds of the accepted input and
validator contracts; overflow cannot silently truncate audit evidence.

Each `COMPLETE` or `PARTIAL` canonical-bar publication consumes exactly one
`publication_sequence` number. A consumer uses a missing or out-of-order sequence to detect bar
delivery failure within one run. It uses interval identity and the bar's typed completion evidence
to describe market-data gaps. `run_epoch` and `publication_sequence` are delivery coordinates, not
market identity.

### Completed-bar value representation

`CompletedBarV1` is a versioned custom payload and does not embed a native Nautilus `Bar`. Its
open, high, low, and close values and any available volume are copied exactly from Nautilus
fixed-point values without passing through `float`. Volume is `Decimal | None` and is paired with
the typed `VolumeState` enum `OBSERVED`, `MISSING`, `UNSUPPORTED`, or `PARTIAL`:

- an observed zero is `Decimal("0")` with `OBSERVED`;
- missing or unsupported volume is `None` with the matching state; and
- a partial observed amount is preserved with `PARTIAL`.

Negative sentinels and free-form reason strings are invalid. The implementation slice must prove
deterministic codec round trips for zero, null, partial amounts, maximum supported precision,
identity, timestamps, and typed states before accepting any serialized or backed transport.

### Metric subject identity

Replace actor-local interpretation of `MetricValue` with an immutable `MetricSubjectIdentity`
containing every applicable dimension:

- metric ID and definition version;
- parameter version, effective time, and parameter/configuration epoch;
- exact instrument and input completed-bar series ID;
- calendar definition identity;
- analytical profile ID/version;
- session/trade-date identity where applicable;
- analytical window ID/version where applicable;
- rolling family, candidate, input timeframe, horizon, and baseline policy where applicable;
- output schema version and canonical producer ID.

`MetricValue` v2 carries the subject, explicit `MetricValueKind`, value, canonical `unit_id`, all
five accepted UTC-nanosecond timestamps, health, fidelity, missing reasons, evidence references,
source/run epoch, subject revision, and prior revision. `effective_ts_ns` is the described market
boundary and `ts_event`; `observed_ts_ns` is the latest required source-observation time;
`received_ts_ns` is receipt of the final required input; `calculated_ts_ns` is calculation
completion; and `published_ts_ns` is canonical publication and `ts_init`. Enforce
`observed <= received <= calculated <= published`. The `unit_id` is owned by the versioned metric
definition, echoed exactly on the value, and validated before publication. `NUMBER` accepts only
`Decimal`; `INTEGER` accepts `int` but not `bool`; `BOOLEAN` accepts only `bool`; and `TEXT` accepts
only a bounded string. `float` is not a canonical wire value. A value affected by a partial
canonical bar carries `DEGRADED` health plus the exact partial-input lineage until the
metric-specific recovery invariant is satisfied.
`READY` and `DEGRADED` require a non-null current value; `STALE` requires the last defensible
non-null value; and `WARMING`, `UNAVAILABLE`, `UNSUPPORTED`, and `FAILED` require a null value.
Numeric zero is never a missing-value sentinel. The reason collection is an immutable tuple of at
most 16 unique `MetricReasonCode` values in deterministic canonical enum order. `READY` requires
no reasons; every other health state requires at least one. Consumers must not recover subject
meaning from an opaque `session_id`, actor name, or metric ID.

For each exact `MetricSubjectIdentity` and runtime `run_epoch`, the first publication carries
`revision = 1` and `previous_revision = None`; every later publication increments revision by one
and names the immediately preceding revision. A new runtime epoch starts a new chain. This revision
orders an evolving metric subject such as active-session high and does not authorize a canonical
completed-bar correction.

An identical repeat of the same subject/epoch/revision is dropped and counted as a duplicate. An
unequal repeat is rejected and counted as one malformed incoming message while the last accepted
value remains active and the subject continues. A changed truth must use revision `N + 1` with
`previous_revision = N`; `published_ts_ns` describes timing and cannot replace revision identity.

A later accepted closed-period-average contract must emit a typed non-value placeholder at the
expected period boundary whenever its required evidence is missing, unsupported, or partial. The
placeholder preserves the applicable health, fidelity, and reason instead of substituting zero, a
guess, or silence. This is mandatory recorded debt but does not add or enable that metric in
V3-03.

This is an atomic active-wire migration, not a session-metrics-only optional field. Slice 1 may
define, publicly export, document, serialize, and test the v2-schema `MetricValue` and its accepted
supporting contracts, and may migrate pure calculators and registries behind compatibility
fixtures. It does not activate `markeitech.metric.value.v2` on any runtime wire. Existing enabled
publishers and consumers, including Quote Quality, may remain temporarily on one minimal private
legacy-v1 compatibility path with unchanged wire identity and behavior during that preparatory
slice.

The atomic-migration rule applies when v2 is activated as a runtime wire type in the later cutover
slice. At that cut every enabled current publisher and consumer of `MetricValue` must adopt v2 in
the same reviewed batch or remain disabled. Dual publication remains forbidden. Existing
publishers populate only the subject dimensions applicable to their exact outputs. Visual Debug
acquires no analytical semantics; it filters and renders complete v2 subjects under its separate
passive activation gate. This sequencing clarification was accepted by Markeitect on 2026-09-01
and supersedes the earlier ambiguous wording without changing v2 payload semantics.

### Final canonical payload field and bound table

The following table closes the V3-03 public payload schema decision. Nested identity and lineage
objects are immutable parts of their parent payload. A field is optional only where the accepted
health/value, volume, subject-dimension, or revision rules explicitly permit `None`.

| Payload | Required fields |
|---|---|
| `CompletedBarV1` | `series_id`; complete `series_identity`; `interval_start_ns`; `interval_end_ns`; `run_epoch`; per-series `publication_sequence`; `completion_state`; `expected_constituent_count`; `received_constituent_count`; exact `missing_subintervals`; typed `completion_reasons`; exact `open`, `high`, `low`, `close`; `volume`; `volume_state`; trade-date, exchange-state, product-phase, and state/projection evidence; `published_ts_ns`; ordered `lineage`; `health`; `fidelity`; and evidence references. It contains no `bar_revision`, raw constituent bars, negative sentinel, or free-form reason. |
| `CompletedBarSeriesIdentity` | Exact instrument/contract and venue; canonical bar specification; interval, aggregation, timestamp, completion, and revision policies; calendar ID/version/digest/effective epoch; analytical profile ID/version; configuration epoch/digest; canonical producer ID; output schema version; and derived stable `series_id`. It contains no provider, adapter, source-stream, or source-selector dimension. |
| `CompletedBarInputIdentity` | Exact provider ID, adapter ID, source-stream ID, source selector, and source schema ID for one upstream path. Historical request validation binds its expected input identity separately from the canonical output identity; live configuration maps its exact input identity and `BarType` to that output. |
| `CompletedBarLineageEntry` | Typed `HISTORICAL` or `LIVE` source class; exactly one complete `input_identity`; provider observation and evidence references; source-observed, source-received, and normalized UTC nanoseconds; transformation chain; and source correction metadata. |
| `MetricValue` v2 | Complete `subject`; `kind`; typed `value`; definition-owned `unit_id`; `effective_ts_ns`; `observed_ts_ns`; `received_ts_ns`; `calculated_ts_ns`; `published_ts_ns`; `health`; `fidelity`; ordered typed `reasons`; evidence references; `run_epoch`; positive `revision`; and nullable `previous_revision` only for revision 1. |
| `MetricSubjectIdentity` | Metric ID and definition version; parameter version, effective time, and parameter/configuration epoch; exact instrument and input completed-bar series; calendar-definition identity; analytical profile ID/version; applicable session/trade-date, window, rolling-family, candidate, timeframe, horizon, and baseline-policy dimensions; output schema version; and canonical producer ID. Inapplicable dimensions are explicitly absent rather than encoded into an opaque ID. |

| Bound | Accepted limit and behavior |
|---|---|
| Routing `series_id` | At most 64 safe ASCII characters and subject to the accepted topic-token exclusions. |
| Other identifiers and enum tokens | At most 128 ASCII characters. |
| `MetricValue` `TEXT` value | At most 512 Unicode characters. |
| Typed reason tuple | Zero through 16 unique entries in deterministic enum order; health rules may require at least one. |
| Evidence references | At most 256 deduplicated references across one payload, each at most 256 characters. |
| Completed-bar lineage | At most 64 ordered entries in one bar payload. |
| Missing subintervals | Cannot exceed `expected_constituent_count`; the first ES one-minute series declares exactly 12 five-second constituents. |
| UTC-nanosecond timestamps, publication sequences, and metric revisions | Positive signed 64-bit integers. `previous_revision` is `None` only for revision 1. |
| Runtime epoch | UUID. |
| Decimal values | Precision is owned by the exact instrument or versioned metric definition. No global rounding, truncation, or canonical `float` conversion is permitted. |

Collection bounds are safety ceilings, not capacity claims. An over-bound or mismatched payload is
rejected and counted before publication or admission; evidence is never silently truncated. For
example, an `es_1m` partial bar with 11 admitted five-second constituents declares
`expected_constituent_count = 12`, `received_constituent_count = 11`, and the one exact missing
subinterval. A 50-period calculation may cite 50 bar references without approaching the accepted
256-reference ceiling.

### Global producer manifest

After loading configuration and canonical catalogs, composition derives one immutable
`ProducerManifestV1` before constructing `LiveNode`, any actor, or any provider demand. It is not a
second hand-authored TOML surface, a runtime discovery exchange, or a separately mutable registry.

The manifest contains:

- `manifest_schema_version = 1`;
- configuration epoch and digest;
- a sorted exact bar-series entry for every enabled `series_id`, including the full series-identity
  digest, canonical producer actor ID, deterministic foundation-instance assignment, producer and
  output schema versions, activation disposition, dependencies, and applicable resource bounds;
- a sorted typed metric-producer claim for every enabled output family, including the complete
  subject dimensions or bounded claim pattern, canonical producer actor ID, producer/output
  versions, exact input series, dependencies, parameter identity, and activation disposition; and
- one deterministic `manifest_digest` over the canonical serialized representation.

Composition injects only each actor's immutable relevant entries plus the full manifest digest.
Consumers validate those entries locally and echo the full digest in readiness acknowledgements;
actors do not receive authority to add, remove, or rewrite manifest claims at runtime.

Fail closed at this composition boundary on duplicate or unassigned bar-series owners, duplicate
metric producers, overlapping typed subject claims, missing upstream series, unknown producer or
instance references, unresolved parameter sets, circular metric dependencies, resource-bound
violations, nondeterministic serialization, or a shadow output referenced by a canonical consumer.
No actor construction, provider startup, or demand may occur after a manifest validation failure.

## Completed-Bar Startup And Historical Routing

### Canonical-series startup

Every enabled required numerical canonical-bar consumer follows one bounded startup handshake:

1. subscribe to each exact required series;
2. validate its configured series and producer identity;
3. publish one typed subscription acknowledgement per exact `(consumer_actor_id, series_id)` pair;
4. foundation instances validate the startup epoch, consumer actor ID, series ID, manifest digest,
   status, and required-consumer membership for every acknowledgement;
5. foundation instances wait for all required subscription acknowledgements for each series;
6. only then publish configured live and historical demands; and
7. publish explicit degraded/unavailable startup outcomes if readiness cannot complete within the
   configured bound.

The first configuration sets `consumer_readiness_timeout_ms = 5000`. A series starts immediately
when all expected consumers acknowledge. At timeout, the foundation seals the acknowledged
consumer set for the run, quarantines each missing or rejected consumer, and starts the series for
the acknowledged set. If the acknowledged set is empty, it publishes neither historical nor live
demand for that series. A late acknowledgement cannot mutate the sealed set.

Subscription readiness means that the actor is running, gated, and able to receive its exact
canonical series. It is distinct from metric/evidence readiness. Consumers receive canonical
bootstrap bars, reconstruct their own bounded state, and become `READY`, `WARMING`, `DEGRADED`, or
`UNAVAILABLE` independently according to their evidence contracts.

The first V3-03 implementation does not support late attachment, independent consumer restart,
same-run replacement, or dynamic activation. A completed-bar snapshot/watermark protocol requires
a later accepted requirement and is not copied from V3-02 merely because that calendar-state
pattern exists.

That later protocol is required rather than optional resilience polish. It must prevent permanent
consumer exclusion after a recoverable failure by subscribing first, buffering continuing live
bars, obtaining purpose-specific historical state through an exact canonical watermark,
reconciling duplicates/conflicts/gaps, applying buffered bars in order, and rejoining only when its
state is honest. Until that follow-on is accepted, a consumer which misses the V3-03 startup
barrier is quarantined for the run and can recover through a whole-runtime cold restart.

This deferral does not remove whole-runtime cold-start reconstruction. On every cold start or
whole-runtime restart, all enabled owners start together, subscribe before demand, and declare the
history required to reconstruct their configured continuing state. No owner waits for the next
session when bounded session-to-date, previous-session, overnight, window, rolling, baseline, or
predecessor evidence can reconstruct the required state. Missing evidence remains explicit and
cannot be replaced by the first convergence cohort.

### Historical usage

Every historical requirement declares exactly one usage:

- `canonical_series_bootstrap`: historical observations initialize, overlap, repair, or otherwise
  participate in a continuing/shared canonical series and therefore pass through its assigned
  foundation instance; or
- `bounded_batch_calculation`: one requesting owner validates the exact transient batch, calculates
  its named result, cites batch identity and completeness, publishes no canonical bar, joins no
  continuing live bar state, and discards raw observations afterward.

These are request usages, not actor classes. A continuing live actor may consume canonical bars
and also declare a separate `bounded_batch_calculation` for an immutable historical result. History
that initializes the same ordered bar sequence or continuing calculation state as future live bars
uses `canonical_series_bootstrap`.

Only the first 15-bar `es_1m` bootstrap is classified at this review point. Every later session,
window, rolling, baseline, or predecessor requirement must receive its own reviewed usage before
its owner can be enabled; no classification is inherited merely because the requesting actor also
consumes live canonical bars.

One shared pure validator checks instrument, selector, request and UTC bounds, timestamp policy,
completion, ordering, uniqueness, duplicates, unequal interval conflicts, gaps, revisions, volume
support, health, fidelity, and lineage. A bounded historical-only path cannot publish canonical
bars, feed canonical live ledgers, repair live gaps, or become a shared bar snapshot.

The validator returns one immutable structured disposition:

- `COMPLETE`: the exact requested evidence is valid and present;
- `PARTIAL`: usable ordered observations are returned with explicit missing or gap facts; or
- `REJECTED`: unsafe identity, schema, ordering, or same-interval content prevents calculation and
  canonical admission.

Normal evidence incompleteness returns `PARTIAL`; it is not converted into an exception or a false
complete result. Programmer and configuration contract violations may still fail before runtime
use. The requesting owner remains responsible for deciding whether its policy can calculate from
`PARTIAL` evidence and must preserve the validator's disposition in its output health and lineage.

Within the configured hard raw-batch bound, identical observations with the same complete identity
are collapsed into one accepted ordered observation. The result counts every duplicate and merges
its additional evidence references into lineage; it never calculates or publishes twice. Exact
duplicates do not prevent `COMPLETE` when all requested unique intervals are present. Unequal
same-identity content is a `REJECTED` conflict.

Every result is an immutable envelope containing:

- request ID, request digest, and historical usage;
- exact completed-bar series identity;
- requested UTC start and end;
- validation disposition;
- raw, accepted-unique, duplicate, conflict, and gap counts;
- exact missing or gap intervals;
- evidence health and fidelity;
- lineage, evidence references, and typed reason codes; and
- ordered unique observations for `COMPLETE` or `PARTIAL` only.

`REJECTED` returns no usable observations. A requesting owner may calculate from `PARTIAL` only
when its own accepted policy permits, and its output must preserve the validation disposition and
reason codes rather than upgrading the evidence silently.

### First accepted ES completed-bar profile

The exact first profile is deliberately narrower than the foundation's future capacity:

- instrument: `ESU6.CME`;
- live provider input: `5-SECOND-LAST-EXTERNAL`;
- canonical output: `1-MINUTE-LAST-EXTERNAL`;
- historical bootstrap selector: `1-MINUTE-LAST-EXTERNAL`;
- historical usage: `canonical_series_bootstrap`;
- timestamp policy: `interval_end`;
- connected convergence cohort: 15 `COMPLETE` historical output bars followed by five newly
  `COMPLETE` live output bars;
- required result: exactly 20 unique, contiguous canonical one-minute bars with the historical and
  live populations meeting at one exact minute boundary;
- partial first live minute: excluded from this complete-only acceptance cohort; the fixture must
  align the history/live cut so the first admitted live minute contains exactly 12 contiguous
  five-second constituents, while separate offline fixtures prove the accepted `PARTIAL` path;
- `maximum_series_per_instance = 16` and `maximum_total_series = 64`;
- `maximum_retained_completed_bars_per_series = 16`;
- `maximum_history_live_overlap_bars = 1`;
- `maximum_buffered_live_completed_bars_per_series = 2`; and
- `revision_policy = "reject"`.

The foundation retains completed bars only as bounded recent admission evidence. Equal overlap is
dropped and counted once, unequal same-identity content is a terminal integrity conflict for that
series, and observations older than the retained watermark window are rejected and counted as
stale. The historical batch and pending live cut are separately bounded transient state. Metric
warmup, session reconstruction, analytical history, late-subscriber replay, and runtime duration
are not derived from the 16-bar retention value or the 15-history/five-live cohort.

## Owner Designs

### CompletedBarFoundationActor

Use native `DataActor` lifecycle, `on_bar`, `Bar`/`BarType`, typed `CustomData`, data
publish/subscribe, actor clock timers/alerts, and the existing subscription port. The legacy
`CompletedBarLedger` and `aggregate_completed_bars` operate on the incomplete pre-v3 input model;
Slice 2 therefore keeps them dormant and uses private canonical-v1-aware buckets, convergence, and
admission state rather than treating compatibility helpers as canonical authority.

The actor:

- owns a statically bounded set of exact series rather than one series, one instrument, or the
  unbounded runtime universe;
- maintains independent ledger, aggregation, health, failure, counter, and publication state per
  series;
- attaches only to configured native series and publishes only configured canonical series;
- parses canonical, live, and historical `BarType` values and fails before actor construction when
  their instrument, interval, native-client authority, or immutable execution-port authority
  snapshot contradicts the complete series and request;
- constructs and retains one metadata-qualified `DataType` per owned canonical series and uses
  the identical value for publication and shutdown accounting;
- waits for exact-series consumer readiness before declaring live or historical demand and
  releases owned logical demand through the accepted acquisition boundary;
- consumes only `canonical_series_bootstrap` historical batches mapped to an owned series without
  owning provider execution;
- owns bounded correlated projection and V3-02 current-state request cycles, admits only exact
  requester/request/source/run/calendar/coverage/policy identity, reconciles revision gaps through
  a new bounded snapshot cycle, preserves refresh intent arriving during one outstanding
  projection request, and never evaluates mcal;
- interprets provider timestamps under the exact configured policy;
- closes each configured interval once, publishes `COMPLETE` from the full valid constituent set,
  publishes final `PARTIAL` OHLCV from one or more valid constituents with exact missingness, and
  publishes no bar when no valid constituent exists;
- bounds per-series and aggregate partial buckets, ledgers, callbacks, timers, and publication
  work;
- rejects off-grid five-second constituents before bucket mutation, validates a publication batch
  before committing sequence or retention, and treats delivery-only evidence as mergeable rather
  than market-content conflict authority;
- publishes explicit per-series health and shutdown accounting; and
- rejects callbacks, messages, timer rearming, and publication after `STOPPING`.

It does not calculate metrics, windows, semantic state, provider pacing, Watchlist membership, or
agent-facing read models. It also does not receive or publish `bounded_batch_calculation` bars.

### CompletedBarMetricsActor

This actor consumes exact canonical series and reuses `completed_bar_metric_definitions` and
`calculate_completed_bar_metrics`. It maintains only bounded compatible-predecessor state.
Return and true range must cite the exact predecessor observation or emit the accepted missing
outcome. It subscribes and acknowledges readiness before foundation demand. It never publishes a
canonical bar or attaches to native/provider data.

### SessionReferenceMetricsActor

This actor reuses `SessionReferenceBook` and session-reference calculation policy. It consumes
canonical bars, immutable calendar projections, and V3-02 state delivery. It declares exact
active-session and previous-session historical needs through the planner, classifying each
requirement as `canonical_series_bootstrap` or `bounded_batch_calculation`. The first profile
publishes every reviewed `active_session.*` and `previous_session.*` value plus
`gap.opening.points` and `gap.opening.ratio`. It does not claim or publish `overnight.*` or
`gap.indicative.*`. Partial coverage, predecessor lineage, unsupported volume, health, fidelity,
and session-boundary compatibility remain explicit. It never authors analytical windows or calls
acquisition.

### AnalyticalWindowMetricsActor

This actor reuses `AnalyticalWindowBook` and existing analytical-window calculations. Each window
has independent identity, temporal anchor, offset, duration, selector/series, historical need,
coverage policy, retention, revision, and lifecycle. Product phases remain canonical temporal
facts, not analytical windows. Each historical need declares its usage explicitly. Cross-calendar
windows require a later accepted design. The first profile enables `opening_range_fast` for 15
minutes and `opening_range_slow` for 30 minutes, both anchored to the configured session start with
canonical `es_1m` input. Each publishes its complete reviewed `opening_range.*` family.
`power_hour` and all other windows remain disabled and have no producer claims.

### RollingMeasurementsActor

This actor consumes the exact canonical input series named by each rolling family. It does not
derive or publish completed bars. Each family independently declares timeframe, candidate
durations, update alignment, coverage, recent and phase-matched baselines, parameter envelope,
retention, and output age.

The first profile enables only the `fast` family on canonical `es_1m`. Its active candidates are
`context_45m` and `expansion_10m`, and `context_45m` is the selected context. Each candidate owns
the complete reviewed rolling suffix set: price range, realized-log-return magnitude, ATR,
directional efficiency, coverage, recent and phase expansion ratios and percentiles, and their
reference counts. Recent comparison defaults to eight prior same-duration windows and
phase-matched comparison defaults to five prior sessions at the same phase offset; the respective
safety ceilings remain 64 and 30. Other fast candidates and the `tactical` and
`structural_intraday` families remain disabled and have no producer claims.

Before an affected family is enabled:

- ATR window `N` must receive `N + 1` compatible bars, cite `B0` as the predecessor used only for
  `B1`, return null `UNAVAILABLE` when that predecessor is missing/incompatible, and propagate
  partial-input `DEGRADED` state until the affected true-range sample leaves the window; and
- expansion ratio and percentile must have independent value/health results; a zero baseline median
  produces null `UNAVAILABLE` ratio with `BASELINE_MEDIAN_ZERO`, while percentile still publishes
  with health derived only from its own inputs.

Focused fixtures must prove the corrected formula and null/health behavior. This is correction of
verified existing defects, not authorization to introduce new analytical definitions.

## Lifecycle And Partial Failure

There is no assumed global order among calendar state, schedule projection, historical readiness,
historical batch, canonical bar, and metric publication.

Each owner must:

- expose `STARTING`, local `WARMING`/`READY`/`DEGRADED`/`FAILED` evidence, `STOPPING`, and terminal
  accounting without redefining global system health;
- bound retained inputs, pending publications, timers, retry attempts, and elapsed recovery;
- isolate formula/family/series failure so unrelated owners continue;
- reject new work after `STOPPING`, cancel timers, release only owned logical demand, and drain
  already accepted bounded work to a configured deadline;
- report incomplete, buffered, dropped/rejected, duplicate, conflict, and pending counts; and
- never allow a worker or callback to decide global health.

Each foundation instance must additionally isolate failures by exact series and enforce configured
per-series and aggregate callback/publication budgets. Failure of one series must not corrupt or
stop another owned series unless the shared actor lifecycle itself fails.

Do not add threads, workers, queues, or executors unless measurement proves actor callbacks cannot
meet an accepted budget and Markeitect separately approves the runtime design. Keep historical
request concurrency and retry at the accepted one-in-flight/one-attempt boundary until callback
attribution and cancellation defects close elsewhere.

## Configuration And Composition

Replace the monolithic `[metrics.session_measurements]` surface. The accepted canonical-bar
configuration authority is:

```text
completed_bars
metrics.completed_bar_metrics
metrics.session_reference_metrics
metrics.analytical_window_metrics
metrics.rolling_measurements
```

The remaining numerical-owner section names are reviewed separately below. They stay under
`[metrics]`; none may own or redefine the canonical series collection.

The assignment shape is explicit and does not duplicate complete series definitions:

```toml
[[completed_bars.series]]
series_id = "es_1m"

[[completed_bars.instances]]
actor_id = "COMPLETED-BARS-1"
series_ids = ["es_1m"]

[metrics.completed_bar_metrics]
actor_id = "COMPLETED-BAR-METRICS"

[metrics.session_reference_metrics]
actor_id = "SESSION-REFERENCE-METRICS"
enabled = true
active_session_enabled = true
previous_session_enabled = true
opening_gap_enabled = true
overnight_enabled = false
indicative_gap_enabled = false

[metrics.analytical_window_metrics]
actor_id = "ANALYTICAL-WINDOW-METRICS"
enabled = true
input_series_ids = ["es_1m"]
enabled_window_ids = ["opening_range_fast", "opening_range_slow"]

[metrics.rolling_measurements]
actor_id = "ROLLING-MEASUREMENTS"
enabled = true
input_series_ids = ["es_1m"]
enabled_family_ids = ["fast"]
enabled_candidate_ids = ["context_45m", "expansion_10m"]
selected_context_candidate_id = "context_45m"
recent_reference_count = 8
maximum_recent_reference_count = 64
phase_reference_count = 5
maximum_phase_reference_count = 30

[visual_debug_capture]
actor_id = "VISUAL-DEBUG-CAPTURE"
enabled = true
instrument_id = "ESU6.CME"
series_id = "es_1m"
bar_type_name = "markeitech.completed_bar.canonical.v1"
metric_type_name = "markeitech.metric.value.v2"
required_consumer = false
metric_ids = [
  "completed_bar.open",
  "completed_bar.high",
  "completed_bar.low",
  "completed_bar.close",
  "completed_bar.volume",
  "completed_bar.simple_return",
  "completed_bar.true_range",
]
target_historical_bars = 15
target_live_bars = 5
```

`es_1m` is defined once in the `completed_bars.series` canonical-series collection. The instance
list is the only deployment-assignment authority; composition validates it and derives the
producer/partition manifest before constructing the node.

The foundation configuration contains:

- statically identified actor instances;
- exact immutable series definitions with one bounded, topic-safe routing `series_id` each;
- an explicit `series_ids` list on every instance, separate from series definitions, with every
  enabled series assigned exactly once and no automatic placement or reshuffling;
- `maximum_series_per_instance = 16` and `maximum_total_series = 64` for the first schema;
- `maximum_retained_completed_bars_per_series = 16`, a derived aggregate ceiling, and separately
  reviewed partial-bucket limits;
- `maximum_history_live_overlap_bars = 1` and
  `maximum_buffered_live_completed_bars_per_series = 2` for the first one-minute profile;
- per-callback/publication work and bounded queue limits;
- exact source selector, output `BarType`, source eligibility, interval, timestamp, completion,
  aggregation, conflict, and revision policy; and
- `consumer_readiness_timeout_ms = 5000`, per-consumer quarantine state, sealed acknowledged sets,
  and explicit degraded/unavailable outcomes.

Each consumer configuration names exact input series and independently owns metric/parameter
versions, historical requirements and their usage, retention, output age, and family/window policy.
Each versioned metric definition declares how partial influence enters its state and the exact
mathematical recovery invariant; configuration may select only a reviewed rule. Calendar/profile
identity references the Watchlist and canonical catalogs; it does not copy their rules. The
producer/partition manifest is derived from validated configuration rather than hand-authored as a
second authority.

The reviewed implementation slice bumps the system configuration from schema 23 to schema 24.
The tracked example and V3 ES profile migrate together through a cold, atomic cutover. Reject
schema 23 with any new split section, reject schema 24 with the retired combined shape, and do not
preserve dual parsers or both shapes indefinitely.

Configuration must provide:

- independent enablement and actor ID per owner;
- exact series definitions and typed producer claims from which composition derives manifest
  identity;
- explicit, deterministic, duplicate-free instance `series_ids` assignment from which composition
  derives the series-to-foundation-instance map;
- calendar/profile bindings without copied calendar rules;
- independent historical needs with `canonical_series_bootstrap` or
  `bounded_batch_calculation` usage, selectors, priorities, retention, and output-age bounds;
- exact formula and parameter versions/effective times;
- independent rolling-family selectors and resource bounds; and
- one bounded Visual Debug review selection containing an exact canonical `series_id`, canonical
  schema versions, complete metric-subject allowlist, target populations, timers, retained-state
  limits, writer queue/drain bounds, and artifact identity; and
- fail-closed validation across Watchlist capabilities, calendars, profiles, series, metrics,
  entity dependencies, and actor composition.

Do not carry the provisional 1,000-observation retention, disabled rolling placeholder, coupled
output-age values, or completed-bar snapshot/retry settings forward without a separately reviewed
requirement and bound. Do not use the 15-history/five-live acceptance population as a universal
historical, analytical, recovery, replay, or retention policy.

The tracked example remains disabled by default. The tracked V3 ES profile activates replacement
owners and the passive Visual Debug projection only in the separately reviewed acceptance slice.
Entity Analysis remains disabled through V3-03.

## Implementation Slices

Each slice is a separate change branch and PR under the current
[GitHub workflow](../operations/github-workflow.md). Publish the verified slice for Markeitect's
review, then stop before merge. Begin a dependent slice only after its prerequisite PR is merged.

### Slice 1: Identity, contracts, and producer manifest

- Add immutable completed-bar series/observation and metric-subject identities.
- Add canonical bar and MetricValue v2 wire contracts with enforced degraded-value/non-value
  invariants.
- Export and document the accepted public completed-bar contracts only: `CompletedBarV1`,
  `CompletedBarSeriesIdentity`, `CompletedBarInputIdentity`, `CompletedBarLineageEntry`,
  `BarCompletionState`, and `VolumeState`; keep foundation mechanics private.
- Export and document the accepted public metric contracts: v2-schema `MetricValue`,
  `MetricSubjectIdentity`, `MetricValueKind`, `MetricHealth`, `MetricFidelity`, and
  `MetricReasonCode`; keep new calculation and owner mechanics private.
- Preserve the existing public `MetricRegistry` contract; do not expose new internal registries.
- Keep manifest, readiness, historical-validation, foundation-state, actor, and new registry
  contracts private while testing their full internal behavior.
- Add pure producer/partition-manifest validation, exactly-one series assignment, and
  complete-subject overlap detection.
- Add typed historical-usage configuration and one pure bounded historical-batch validator.
- Add pure startup requirement/readiness validation without a bar snapshot protocol.
- Adapt pure registries/calculators behind compatibility fixtures without publishing new runtime
  types.
- Keep existing enabled `MetricValue` publishers and consumers, including Quote Quality, on one
  minimal private legacy-v1 compatibility path with unchanged runtime wire identity and behavior;
  do not activate, publish, or subscribe to `markeitech.metric.value.v2` in this slice.
- Treat acquisition's current pre-`HistoricalBatch` duplicate/order rejection as later-slice
  integration debt: prove the accepted duplicate-collapse behavior in the pure validator without
  changing acquisition admission here.
- Prove deterministic identity/digest construction, duplicate/conflict semantics, bounds,
  historical usage isolation, partition uniqueness, per-consumer/per-series readiness accounting,
  five-second timeout, quarantine/sealing behavior, `COMPLETE`/`PARTIAL`/`REJECTED` historical
  dispositions, exact immutable validator-envelope fields, no usable bars on `REJECTED`, partial
  reason preservation, and serialization.

**Gate:** no actor or tracked profile publishes or subscribes to a new canonical type in this
slice. The temporary legacy-v1 compatibility path is removed or left disabled when the later
atomic v2 runtime-wire cutover occurs; old and new types are never dual-published.

### Slice 2: Completed-bar foundation owner

- Add the disabled foundation actor and independent configuration model.
- Start with one bounded multi-series instance and independently isolated per-series state.
- Implement the first `ESU6.CME` path as five-second live input to one-minute canonical output;
  keep unreviewed five-minute, fifteen-minute, hourly, and other coarser outputs disabled.
- Close each minute under the versioned private `completion_grace_ms = 1000` default and strict
  pre-cutoff callback rule; timer lateness never extends eligibility or revises a sealed bar.
- Reuse native bar callbacks, typed data, clock, and the existing subscription port; keep the
  legacy input ledger/aggregation helpers dormant and use private canonical-v1-aware state.
- Request and consume V3-02 current state plus bounded immutable calendar projections through the
  accepted correlated delivery/retry protocols; resynchronize transition revision gaps.
- Wait for exact-series consumer readiness before declaring demand.
- Canonicalize only manifest-admitted live inputs and `canonical_series_bootstrap` history.
- Bind parsed canonical/live/historical `BarType` identity to the native live client and an
  immutable snapshot taken from the actual historical execution port before actor construction or
  demand; retain the same snapshot as batch source authority and reject every contradiction.
- Reject `bounded_batch_calculation` and unrelated historical inputs.
- Publish canonical bars once with per-series health and shutdown counters in disconnected
  fixtures only.
- Enforce the accepted 16-bar recent ledger, one-bar overlap, two-completed-bar pending-live
  buffer, reject-revision, duplicate-drop, conflict-stop, and stale-reject policies.
- Prove history-first/live-first overlap, partial aggregation, gaps, duplicates, conflicts,
  timestamp policies, calendar-definition mismatch, projection refresh, delivery-only evidence
  merge, consumer-readiness timeout, calendar delivery timeout/retry/revision-gap reconciliation,
  five-second grid rejection, atomic publication, series isolation, per-series and aggregate
  overflow, and terminal stop behavior.
- Prove one-outstanding-request projection refresh: a transition during `WAITING` produces no
  duplicate publication, retains refresh intent, and starts exactly one new correlated generation
  after the in-flight response completes.
- Reproduce the pinned-version routing fixture: publication for metadata-qualified series `A` reaches
  subscriber `A` exactly once, reaches subscriber `B` zero times, and reaches a metadata-free
  type-only subscriber zero times; reject any route/payload series mismatch.

**Gate:** no tracked profile enables the actor and no provider demand changes.

### Slice 3: Direct completed-bar metrics owner

- Add the disabled direct-metrics actor.
- Subscribe to the exact configured canonical-bar series and acknowledge readiness before
  foundation demand.
- Reuse direct OHLCV, predecessor return, and true-range definitions/calculations.
- Prove exact predecessor lineage, partial-input calculation with `DEGRADED` propagation, exact
  metric-specific recovery, warmup/missing outcomes, revision, health/fidelity, family isolation,
  exact-series routing, and MetricValue v2 identity.

**Gate:** exact fixture parity is required before the owner can become canonical.

### Slice 4: Calendar-dependent numerical owners

- Add disabled session-reference and analytical-window actors as separate registrations.
- Reuse V3-02 current-state reconciliation and immutable schedule projections.
- Reuse existing pure books and calculations.
- Give every owner/window its own historical need, explicit historical usage, bounds, lifecycle,
  and counters.
- Prove bounded historical-only validation never publishes canonical bars or joins live state.
- Prove partial inputs update the applicable calculation while `DEGRADED` health persists until
  the exact window or metric recovery invariant is satisfied.
- Prove active-session, previous-session, and opening-gap behavior; prove disabled overnight and
  indicative-gap families have no producer claim or publication; prove the 15-minute
  `opening_range_fast` and 30-minute `opening_range_slow` developing-to-complete lifecycles and no
  claims from disabled windows; and cover early close, DST, out-of-order delivery, missing
  coverage, unsupported volume, deferred boundaries, and one-owner failure isolation.

**Gate:** each owner and each configured window passes independently; no cross-calendar window is
admitted.

### Slice 5: Rolling-measurements owner

- Keep canonical wider-series ownership in the foundation, but do not enable a five-minute,
  fifteen-minute, hourly, or other new output in the first profile without its separate reviewed
  series decision.
- Add the disabled rolling actor consuming exact canonical input series.
- Configure only `fast/context_45m` and `fast/expansion_10m` on `es_1m`; prove all other candidate
  and family subjects are absent from the producer manifest and canonical publication.
- Correct the accepted `N + 1` predecessor-aware ATR behavior and independent zero-median
  ratio/percentile behavior with focused fixtures.
- Reuse the accepted rolling families, candidates, baseline policies, and calculations otherwise.
- Prove partial inputs update rolling state with `DEGRADED` outputs, fixed-window degradation lasts
  until the input leaves the relevant window, recursive degradation lasts until clean
  reconstruction or explicit reviewed reset, and independent family/timeframe configuration,
  warmup, aggregation lineage, coverage, recent/phase baselines, parameter bounds, family failure
  isolation, and bounded state.

**Gate:** an affected output remains disabled while either known rolling defect is unresolved.

### Slice 6: Passive Visual Debug migration

- Keep `VISUAL-DEBUG-CAPTURE` a passive, noncanonical actor with bounded in-memory collection, one
  bounded writer job/result, deadlines, quiet-period handling, drain deadline, counters, and
  ignored immutable artifacts.
- Replace the old unqualified completed-bar and metric subscriptions with the exact
  `DataType("markeitech.completed_bar.canonical.v1", metadata={"series_id": "es_1m"})` and the
  canonical `DataType("markeitech.metric.value.v2")`; use the identical `DataType` objects for
  unsubscription and immediately filter metrics through the complete v2 subject, producer
  manifest, exact series, and configured bounded allowlist.
- Migrate the collector, cohort validation, renderer, and manifest from `CompletedBarInput`, one
  source label, and old `MetricValue` fields to `CompletedBarV1` completion state, bounded source
  lineage, runtime/publication coordinates, complete `MetricSubjectIdentity`, v2 health/fidelity,
  typed reasons, and revision continuity. It may validate equality and lineage but never
  recalculate formulas or fill missing values.
- Remove the retired `SESSION-METRICS` historical-readiness signal dependency. Classify selected
  historical and live populations only from canonical bar lineage and publication coordinates;
  never subscribe to raw acquisition readiness or create a historical/capability requirement.
- Compose and start Visual Debug before the foundation and metric publishers, but exclude it from
  every required-consumer readiness set. Any subscription, timer, collection, overflow, renderer,
  writer, artifact, or shutdown failure is projection-local and cannot delay demand, change owner
  readiness, or alter canonical counts.
- Configure one exact review item per separately authorized run. The first bar/direct-metric
  artifact selects canonical `es_1m`, the reviewed direct completed-bar metric subjects, and the
  accepted 15 historical plus five live bar population. Later session-reference, analytical-window,
  and rolling captures select one exact accepted owner/window/candidate question at a time.
- Prove capture-on/off non-interference for actor ownership, provider and historical demand,
  foundation readiness, canonical bar/metric counts, health, persistence, lifecycle, and shutdown.

**Gate:** a disconnected pinned-version fixture proves Visual Debug subscribes before first selected
publication, exact bar and metric delivery, route/payload/manifest agreement, hard collection and
callback bounds, clean unsubscribe/shutdown, and projection-local failure. No tracked profile is
enabled if the observer changes any canonical producer behavior.

### Slice 7: Configuration, composition, and cold cutover

- Bump the system configuration atomically from schema 23 to schema 24 and replace the monolithic
  disabled configuration in both tracked profiles.
- Compose the global producer/partition manifest before `LiveNode` construction.
- Configure one bounded multi-series foundation instance with the accepted 16-series instance
  ceiling, 64-series total ceiling, and exact first ES five-second-input/one-minute-output series.
- Prove every enabled series resolves to exactly one instance and exact-series subscribers only.
- Add all replacement registrations disabled by default in the tracked example.
- Build a dedicated isolated parity fixture where legacy output is explicitly noncanonical.
- Compare exact input/output populations, formulas, timestamps, missingness, health, fidelity,
  lineage, revisions, and failure counters.
- Enable the new owners one at a time in the tracked V3 ES acceptance profile only after their
  offline gates pass.
- Prove no runtime plan can contain both the old and new canonical writers.

**Gate:** there is no hot handoff, dual-canonical namespace, or reactivation of the old actor in a
tracked active plan.

### Slice 8: Retirement and authoritative closure

- Remove `SessionMetricsActor`, its monolithic config class/loader/composition path, and tests that
  assert the retired topology only after every retained responsibility has an accepted owner.
- Preserve or migrate pure calculation fixtures and historical review documents.
- Reconcile every current canonical bar and metric consumer to v2 subject identity; migrate Visual
  Debug under its passive V3-03 contract and keep Entity Analysis disabled.
- Update current status and the accepted session/evidence architecture.
- Update `docs/architecture/system-dataflow.toml`, regenerate the complete artifact set with the
  locked offline tool, inspect all views visually, and pass drift/hash checks.
- Update public exports/docstrings and `tools/api-docs/schema/public-surface.toml` only for
  intentionally public objects, with the required denominator/hash/version change and locked
  static validation.
- Run the proportional offline suite and `git diff --check`.

**Gate:** retirement does not erase historical evidence and does not claim connected acceptance.

### Slice 9: Separately authorized bounded connected acceptance

Run only after explicit authorization for the exact profile and owner under review. Review in this
order:

1. one ES canonical completed-bar series and exact OHLCV;
2. direct bar metrics with predecessor-dependent return and true range;
3. active-session, previous-session, and opening-gap references;
4. the 15-minute `opening_range_fast` and 30-minute `opening_range_slow`, each separately; and
5. `fast/context_45m` and `fast/expansion_10m` separately on canonical `es_1m`.

Visual Debug passively accompanies every run and selects only the exact series and owner, window,
or candidate currently under review. Its artifact must reconcile to the same canonical records and
must not add a provider or historical request. A failed or partial artifact fails only the visual
review evidence for that run; it does not invalidate otherwise truthful producer evidence or stop
healthy owners.

For every run reconcile configuration/producer/partition manifest, consumer readiness, exact-series
subscription and callback counts, provider demands, historical plans/usages/results, canonical bar
counts, metric counts, duplicates/conflicts/gaps, health/fidelity/missingness, lifecycle counters,
persistence of operational facts, resources, and shutdown. A condition not observed remains
unaccepted rather than inferred from another run. Require exact input/output reconciliation for
value, unit, all timestamps, health, fidelity, typed reasons, lineage, and revision. Equal overlap
duplicates are permitted only when identified and counted; unequal conflicts, accepted bar
revisions, unexplained sequence gaps, unaccounted drops, resource-bound violations, and post-stop
publication are acceptance failures.

The first completed-bar run targets exactly 15 `COMPLETE` historical one-minute bars followed by
five newly `COMPLETE` live one-minute bars, with exactly 20 unique contiguous publications and no
forming first live minute. This bounded cohort does not accept general cold-start reconstruction,
coarser outputs, late-consumer replay, retention beyond its configured admission window, or
purpose-specific metric history.

The remaining exact run populations and conditions are:

- direct metrics: all seven accepted completed-bar outputs reconcile for the exact 20-bar
  foundation cohort, including predecessor-dependent unavailable/degraded behavior;
- session references: one complete previous session is reconstructed and the configured current
  session opening boundary is present, so active-session, previous-session, and opening-gap
  subjects can be reconciled without inferred boundaries;
- analytical windows: the configured start plus both the 15-minute `opening_range_fast` and
  30-minute `opening_range_slow` completion boundaries are reconstructed or observed with their
  exact evidence; and
- rolling: `context_45m` and `expansion_10m` each have their compatible predecessor, complete
  current calculation population, eight eligible recent references, and five eligible
  phase-matched references. A missing required reference remains explicit and cannot pass through
  another candidate's evidence.

For every run, Visual Debug must reconcile its selected artifact to the same canonical records and
capture-on/off must preserve provider/history demand, required-consumer readiness, canonical
counts, producer health, persistence, resources, and shutdown behavior. Do not extend or repeat a
connected run without new exact authorization. If the required market or lifecycle condition does
not occur, record `CONDITION_NOT_OBSERVED`.

**Gate:** Markeitect decides acceptance and whether V3-03 may close. A screenshot is optional
review evidence, never formula or runtime acceptance by itself. Every shared condition and the
exact owner-specific population above must pass; acceptance is not transferable between runs.

## Planned Code And Test Touchpoints

Exact filenames may be adjusted during review, but ownership must remain explicit.

### Reuse or extend

- `src/markeitech/intelligence/completed_bar_messages.py`
- `src/markeitech/intelligence/completed_bar_foundation.py`
- `src/markeitech/intelligence/historical_bar_validation.py`
- `src/markeitech/intelligence/metric_producer_manifest.py`
- `src/markeitech/intelligence/metric_messages.py`
- `src/markeitech/intelligence/metric_value_admission.py`
- `src/markeitech/intelligence/completed_bars.py`
- `src/markeitech/intelligence/metrics.py`
- `src/markeitech/intelligence/session_measurements.py`
- `src/markeitech/intelligence/session_references.py`
- `src/markeitech/intelligence/session_windows.py`
- `src/markeitech/intelligence/rolling_measurements.py`
- `src/markeitech/intelligence/visual_debug_capture.py`
- `src/markeitech/intelligence/visual_debug_capture_actor.py`
- `src/markeitech/intelligence/visual_debug_capture_plotly.py`
- `src/markeitech/intelligence/calendar_delivery.py`
- `src/markeitech/system/config.py`
- `src/markeitech/system/composition.py`

### Proposed remaining focused modules

- `src/markeitech/intelligence/completed_bar_metric_actor.py`
- `src/markeitech/intelligence/session_reference_metric_actor.py`
- `src/markeitech/intelligence/analytical_window_metric_actor.py`
- `src/markeitech/intelligence/rolling_measurement_actor.py`

### Retirement candidate after cutover

- `src/markeitech/intelligence/session_metric_actor.py`

### Focused verification

- retain and migrate `tests/intelligence/test_completed_bars.py`;
- retain and migrate `tests/intelligence/test_session_references.py`;
- retain and migrate `tests/intelligence/test_session_windows.py`;
- retain and extend `tests/intelligence/test_rolling_measurements.py`;
- retain and migrate `tests/intelligence/test_visual_debug_capture.py`;
- add focused identity, producer/partition-manifest, startup-readiness, historical-usage,
  historical-validation, exact-series-routing, route/payload mismatch, safe-topic-token, and
  one-actor-per-owner tests;
- extend `tests/system/test_config.py` and
  `tests/system/test_v3_es_minimal_config.py`;
- extend `tests/system/test_composition.py` for uniqueness and cutover exclusion;
- extend `tests/system/test_message_delivery.py` for native typed end-to-end delivery; and
- migrate the valid non-interference assertions from
  `tests/intelligence/test_session_metric_capture_alignment.py` to the new topology before
  retiring that legacy-monolith fixture.

## Acceptance Matrix

| Area | Required offline evidence | Connected debt after offline pass |
|---|---|---|
| Identity | Deterministic complete series/subject IDs; unequal epochs cannot alias | Exact live manifest/config reconciliation |
| Producer uniqueness | Duplicate/overlapping outputs and duplicate/unassigned series partitions fail before node construction | One observed canonical publisher per subject and configured series |
| Foundation | Five-second-to-one-minute normalization/aggregation; 15-history/five-live fixture; 20 unique contiguous `COMPLETE` bars; truthful final `PARTIAL` publication from one through eleven constituents; zero-constituent no-bar health/audit; late-upgrade rejection; accepted retention, overlap, buffer, duplicate/conflict, stale, gap, projection, and stop bounds | Provider timestamps, exact OHLCV, and the observed history/live boundary for only that cohort |
| Startup delivery | Exact-series typed acknowledgement before demand; immediate start on complete acknowledgement; five-second timeout; missing-consumer quarantine; acknowledged-consumer continuation; zero-consumer no-demand; late-ack rejection | Real startup ordering and callback accounting |
| Historical routing | Usage validation, `COMPLETE`/`PARTIAL`/`REJECTED` disposition, bounded exact-duplicate collapse with merged lineage and no double publication, pure bounded-batch isolation, canonical-bootstrap overlap, no canonical leak | Exact historical request purpose and history/live boundary |
| Partitioning | One bounded multi-series instance, independent series state, 16-series instance ceiling, 64-series total ceiling, and per-series/aggregate overflow | Measured callback latency, memory, publication pressure, and future partition need |
| Direct metrics | Formula fixtures, predecessor lineage, partial-input calculation, non-null `DEGRADED` value plus reasons/lineage, null `UNAVAILABLE` value plus reasons, exact recovery, warmup, missingness, revisions | Exact values for reviewed ES cohort |
| Session references | Enabled active/previous/opening-gap families; disabled overnight/indicative-gap non-publication; DST/holiday/early-close fixtures, coverage, supported volume, and boundary lifecycle | Required active/previous/opening-gap session conditions observed |
| Analytical windows | Fifteen-minute `opening_range_fast` and 30-minute `opening_range_slow`, each independently covering developing/complete, deferral, partial coverage, and disabled-window non-publication | Each configured start and completion boundary observed separately |
| Rolling | `fast/context_45m` and `fast/expansion_10m` separately on `es_1m`; disabled-candidate non-publication; ATR `N + 1` predecessor/lineage and missing/partial behavior; partial-state influence and metric-specific recovery; zero-median null ratio plus independently valid percentile; eight recent and five phase-matched reference defaults; 64/30 ceilings; bounds and isolation | Sufficient live/history population and exact output accounting for both accepted candidates |
| Visual Debug | Canonical v1/v2 subscription migration, complete identity filtering, bounded collection/writer behavior, exact artifact reconciliation, startup-before-publisher ordering, capture-on/off non-interference, projection-local overflow/failure, and clean shutdown | Markeitect's visual review of the exact selected canonical records for each authorized run |
| Lifecycle | Timers, retries, callback fencing, stop/post-stop, independent failure | Clean resource-bounded shutdown |
| Scope | Passive Visual Debug only; no Entity Analysis activation, raw persistence, or provider-owner move | No unapproved external effects |

Passing offline tests proves only their exercised contracts and fixtures. It does not prove IB
provider truth, market-session behavior, formula fitness for trading, performance, persistence,
visual acceptance, or broad multi-instrument readiness.

## Verification Sequence

For every slice:

1. run the focused pure and actor tests for the changed owner;
2. run configuration, composition, and message-delivery tests affected by the slice;
3. run the full disconnected V2 suite with PostgreSQL-marked tests excluded;
4. run the locked API-doc validation if the public denominator or component docstrings change;
5. run the locked system-diagram generation/drift check if topology changes;
6. inspect generated diagrams when regenerated;
7. run `git diff --check`;
8. inspect the final diff and `git status --short --branch` for unrelated files, secrets, local
   configuration, raw data, logs, or generated churn; and
9. commit and push the scoped slice, open or update its PR, and leave it unmerged for Markeitect's
   explicit approval and merge.

PostgreSQL-marked tests, a connected provider run, or a database migration are not implied by this
sequence. Request exact authorization if a later slice genuinely requires them.

## Risks And Stop Gates

Stop and return to Markeitect before implementation or continuation if:

- an implementation slice conflicts with the accepted decision record;
- a complete bar or metric subject cannot be represented without ambiguity;
- a consumer still requires actor-local knowledge to interpret a canonical value;
- two enabled owners overlap on one canonical output, or a series is unassigned/assigned twice;
- a foundation instance exceeds its configured series or aggregate resource bounds;
- history/live overlap exceeds one completed bar, pending live state exceeds two completed bars,
  or retained state exceeds 16 completed bars for the first series;
- a revision is accepted, an unequal same-identity conflict is silently chosen, or a stale bar is
  reinserted into the canonical sequence;
- outside the explicitly accepted future placeholder exception, a partial input is ignored by a
  required calculation, its influence is not marked `DEGRADED`, or degradation clears before the
  metric-specific mathematical recovery invariant is satisfied;
- a `DEGRADED` metric has no defensible typed scalar value or typed degradation reason, or an
  `UNAVAILABLE` metric carries a numeric value;
- a zero reference median is replaced by epsilon, zero, or infinity, ratio and percentile share
  one health result, or a valid percentile is suppressed solely because the ratio is undefined;
- the foundation would need to interpret provider pacing or an analytical owner would need to
  consume raw provider data;
- demand could begin before the exact-series readiness set either completes or times out and is
  sealed under the accepted quarantine policy;
- a missing consumer is allowed to process bars after quarantine, a late acknowledgement mutates
  the sealed run set, or a zero-consumer series emits provider demand;
- a `bounded_batch_calculation` would publish canonical bars, repair a live gap, or join continuing
  live state;
- a retained gap would be silently filled or labeled continuous;
- an owner would introduce a second mcal evaluator or local calendar fallback;
- a rolling family would publish while either verified correctness blocker affects it;
- the implementation requires higher historical concurrency, retries, or ambiguous callback
  correlation;
- old and new canonical publishers would coexist;
- broad type-level subscriber fan-out cannot be filtered, accounted, bounded, and measured before
  expansion;
- a stable series ID cannot be represented as a bounded topic-safe token, or routing metadata and
  the payload's complete series identity disagree;
- a native composite/indicator adoption is proposed without a separate parity decision;
- Visual Debug changes provider/history demand, required-consumer readiness, canonical counts,
  producer health, persistence, or shutdown behavior, or a producer correctness test passes only
  while the projection is enabled;
- system-diagram or API-documentation authority cannot be updated without weakening its drift
  checks; or
- current code, tracked authority, advisor evidence, and observed behavior materially disagree.

## Completion Checklist

Checked implementation items below describe reviewed Slice 1/2 disconnected evidence only;
they do not close the later runtime-composition or connected-acceptance gates.

- [x] Markeitect accepted the V3-03 planning decisions on 2026-09-01.
- [x] Complete bar/metric subject identity is implemented and reviewed in Slice 1, with the
  canonical/input-identity separation corrected in Slice 2.
- [ ] Global producer/partition uniqueness fails closed before runtime construction.
- [x] One bounded multi-series foundation instance passes per-series isolation and aggregate-bound
  tests for the exact first ES scope.
- [x] The first ES foundation series is exactly five-second live input to one-minute canonical
  output with the accepted 16-series instance and 64-series total ceilings.
- [x] Its disconnected acceptance fixture contains exactly 15 historical plus five newly
  completed live `COMPLETE` bars, producing 20 unique contiguous one-minute publications with no
  forming bar; this is not a connected-run result.
- [x] Its 16-bar retention, one-bar overlap, two-completed-bar pending-live buffer,
  reject-revision, duplicate-drop, conflict-stop, and stale-reject policies pass.
- [x] Canonical and input routes are parsed and bound to exact instrument, interval, native live
  client, and an immutable snapshot of the actual execution-port historical authority before
  actor construction or demand; provider, adapter, stream, and schema contradictions fail closed.
- [x] Projection and V3-02 current-state delivery use owned bounded request cycles, reject stale or
  unrelated responses, preserve refresh intent without republishing an in-flight request, retry
  within policy, and resynchronize transition revision gaps.
- [x] Off-grid constituents are rejected before mutation, multi-candidate publication is atomic,
  and compatible overlap merges delivery-only evidence under public bar equivalence.
- [x] Deterministic pinned-rc3 lifecycle coverage drives native `Bar` values through production
  `on_bar` using `Clock.new_test`, fires the actual scheduled cutoff callback at the exact cutoff,
  proves strict pre/exact-cutoff behavior before and after timer firing, and proves
  subscribe-before-ack, exact unsubscribe/release symmetry, absorbing stop, and shutdown
  accounting.
- [ ] Required numerical exact-series consumers subscribe and acknowledge readiness before
  foundation demand; passive Visual Debug subscribes first without joining the required set.
- [x] The five-second readiness timeout quarantines only missing consumers, continues for the
  acknowledged set, emits no zero-consumer demand, and rejects late acknowledgements.
- [x] Historical requirements use `canonical_series_bootstrap` or
  `bounded_batch_calculation`, with no historical-only canonical leak.
- [x] The pure historical validator returns the accepted immutable envelope and never exposes
  usable observations on `REJECTED` or silently upgrades `PARTIAL` evidence.
- [ ] Foundation is the only writer for every enabled canonical bar series.
- [ ] Each numerical owner passes independently.
- [ ] Known rolling blockers are corrected or affected outputs remain disabled.
- [ ] The exact tracked ES acceptance profile contains no old/new dual writer.
- [ ] The dormant combined actor is retired only after replacement coverage is complete.
- [ ] Visual Debug is migrated to canonical v1/v2 inputs, remains passive and non-gating, and
  passes capture-on/off non-interference plus bounded artifact review; Entity Analysis remains
  disabled and separately gated.
- [x] Focused and full disconnected verification pass.
- [ ] Architecture manifest and generated artifacts agree and are visually inspected.
- [x] Public API documentation gates pass for intentional surface changes.
- [x] No connected or destructive action occurs without exact authorization.
- [ ] Connected evidence, if authorized, is stated only to its observed scope.
- [x] Slice 1/2 final diffs were reviewed, committed, and merged. Each later slice has its own
  branch and PR, which remains unmerged until Markeitect approves and merges it or explicitly
  delegates that exact merge.

## Kite Advisory Basis

Kite routing for this planning batch was intentionally limited to one required read-only
NautilusTrader consultation. It confirmed native reuse for actor lifecycle, clock scheduling,
`Bar`/`BarType`, DataEngine delivery, and typed `CustomData`; it retained Markeitech ownership for
complete subject identity, historical/live convergence, admission/conflict policy, health,
fidelity, missingness, revisions, global producer/partition uniqueness, and analytical formulas.
A bounded follow-up confirmed one static multi-series foundation instance initially, independent
per-series state, exactly-one series assignment, and later static partitioning only after measured
need. It also confirmed that the old actor's current disablement makes the
parity-oracle/cold-cutover topology an explicit approval gate and that current one-request,
one-in-flight, one-attempt provider limits must remain unchanged. A second bounded follow-up
verified from the installed rc3 stubs that native `Bar.volume` requires a non-optional `Quantity`,
so the accepted nullable and typed volume truth requires exact value adaptation into custom
`CompletedBarV1` rather than embedding native `Bar`. A final narrow follow-up reviewed only the
newly accepted Visual Debug scope and confirmed exact canonical bar subscription, canonical
MetricValue v2 filtering, identical subscribe/unsubscribe types, startup-before-publisher ordering,
and exclusion from the required readiness set. It identified the dormant actor's old payload and
`SESSION-METRICS` readiness dependencies as mandatory migrations and required projection-local
failure plus capture-on/off non-interference.

The consultation reached the 2026-08-31 nightly documentation roots and performed only the narrow
installed-stub checks recorded above. It did not prove broad nightly/current-pin equivalence,
native composite semantics, native-indicator formula parity, IB delivery parity, serialized custom
payload behavior, or connected behavior. Those remain explicit unknowns and stop gates. No other
council roles were activated. Tracked authority and the current checkout remain stronger than
advisory recommendations, and Markeitect retains every architecture and acceptance decision.
