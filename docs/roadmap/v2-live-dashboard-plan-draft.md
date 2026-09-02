# V2 Live Dashboard Plan Draft

**Status:** Draft for Markeitect and Kite review; no architecture, product, dependency, runtime,
or delivery decision is approved by this document

**Prepared:** 2026-08-24

**Scope:** A local, read-only, desktop-first operator dashboard for inspecting canonical Markeitech
V2 evidence through the end of Stage 9D.6, with extension points for later accepted stages

**Implementation status:** Planning only. No dashboard, gateway, dashboard transport, or approved
live chart-series contract exists in the current checkout.

## 1. Purpose, Audience, And Authority

### Purpose

The dashboard should let Markeitect inspect what V2 is actually calculating, when it calculated
it, from which evidence, under which definitions and parameters, and with what health and fidelity.
Its first value is visual verification: compare canonical V2 geometry and state with external
charts or screenshots while preserving exact contract, session, timeframe, profile, timestamp,
lineage, missingness, and revision identity.

The dashboard is a replaceable human projection of canonical runtime truth. It never becomes an
analytical owner, a second market-data path, a persistence authority, or Sir Loke's read model.

### Audience

- **Primary operator and product authority:** Markeitect.
- **Engineering and evidence review:** Kite and later senior implementers.
- **Future secondary users:** explicitly authorized local reviewers using the same read-only
  surface. Remote or multi-user deployment is not assumed.

### Authority labels used in this draft

- **Verified current:** confirmed by `docs/current-status.md` and the current checkout.
- **Accepted roadmap intent:** approved future scope recorded in the Stage 9 blueprint or Stage 9D
  plan, but not necessarily implemented.
- **Recommendation:** a proposed dashboard choice requiring review.
- **Unknown / decision gate:** insufficiently specified or not approved; implementation must stop
  for a decision.

### Non-goals

The first dashboard will not:

- connect to IB, request provider data, own a Nautilus subscription, or consume raw IB callbacks;
- calculate metrics, classify state, detect structure, infer interactions, or revise entities;
- write PostgreSQL, persist raw observations, create replay storage, or use PostgreSQL as a market
  chart warehouse;
- alter analytical configuration, activate capabilities, direct focus, acknowledge alerts, or
  send operator intents;
- infer observed order flow, delta, CVD, absorption, trapped participants, support/resistance,
  setups, signals, option selection, opportunities, or advice;
- become Sir Loke's source of truth or share browser-derived state with Sir Loke;
- add semantic events before Stage 9E supplies accepted contracts;
- add cross-instrument interpretation before Stage 9G, options evidence before Stage 9F, or agent
  and opportunity output before Stages 9I-9J;
- support automated execution, order entry, account controls, or risk controls; or
- optimize for mobile trading, public hosting, marketing, decorative presentation, replay, or
  backtesting.

## 2. Capability Timeline

### 2.1 Verified current runtime capability

The current implementation provides the following relevant visual inputs:

- Stages 1-9C and runtime-resource hardening are implemented and connected-accepted within the
  evidence recorded in `docs/current-status.md`.
- `SessionStateEvent` owns calendar, trade date, phase, bounds, timezone, schedule version, source,
  reason, and revision through `markeitech.session.state`.
- `EvidenceHealthEvent` and its current snapshot contract expose instrument/feed/selector health,
  fidelity, subscription state, evidence times and age, session alignment, policy version, and
  revision.
- `MetricValue` is the typed CustomData contract for versioned numerical evidence. It carries
  metric and parameter version, instrument/session identity, value/unit, five relevant timestamps,
  health, fidelity, source, evidence references, missing reasons, and revision.
- Stage 9C publishes completed-bar OHLC, optional volume, return, and true-range metrics, plus
  active/previous-session references, configured windows, gaps, and rolling measurements.
- Stage 9D.1-9D.4C are approved and committed. `EntityRevision` carries deterministic identity,
  entity/parameter/schema versions, typed payload, lifecycle, timestamps, health, fidelity,
  evidence references, missing/conflict reasons, previous revision, source, and restoration state.
- `EntitySnapshotRequest` and `EntitySnapshotResponse` provide filtered immutable current entity
  snapshots by instrument, type, profile/version, and lifecycle.
- Group 1 runtime projection exists for analytical session, previous-session reference, opening
  range, opening gap, and direction-neutral objective levels.
- The optional Group 2/3 runtime boundary currently has one producer-backed binding only:
  fast-horizon volatility state from the configured `context_45m` recent-range percentile and
  coverage metrics. Its connected acceptance remains pending in the current status.
- Runtime resource samples and sustained resource-health transitions exist as separate typed,
  versioned facts. They do not alter global system health.
- PostgreSQL stores operational audit and compact recency profiles. Raw observations and transient
  numerical metric values remain outside PostgreSQL.

Current limitations that the UI must not hide:

- There is no implemented dashboard or gateway in the current branch.
- The optional Observatory remains isolated on `v2-stage-observatory`; it is not accepted current
  runtime behavior.
- There is no general `MetricValue` snapshot request/response contract for late consumers.
- `CompletedBarInput` is an internal deterministic input/ledger contract, not an approved external
  dashboard bus or bootstrap snapshot contract.
- Compression/expansion lacks its approved phase-duration producer; direction lacks its signed
  producers; moving/anchored references lack runtime producers; and trend/rotation still requires
  typed cross-entity reconciliation.
- Stage 9D.3 still has narrow opening-range developing-to-complete connected-acceptance debt.
- Semantic interaction events, market alerts, options evidence, cross-instrument state, Sir Loke,
  and opportunity lifecycle are not implemented.

### 2.2 Accepted end-of-9D.6 visual scope

Subject to implementation and acceptance of the owning runtime contracts, the first complete
dashboard scope should visualize:

- price and session geometry from accepted completed-bar evidence;
- active and previous-session references and configured calendar windows;
- gaps and direction-neutral objective levels;
- volatility, compression/expansion, direction, trend/rotation, and moving or anchored references
  only where each family is actually runtime-bound to accepted canonical inputs;
- confirmed swings and any developing swing state only if 9D.5 explicitly publishes that state as
  a canonical typed lifecycle rather than retaining it internally;
- FVG formation, fill, remaining interval, invalidation, expiry, and revisions;
- deterministic zones with complete constituent lineage and no support/resistance meaning;
- explicitly named `INFERRED_FROM_BARS` volume distribution, POC, value area, HVN/LVN candidates,
  balance areas, and shape descriptors where volume is supported; and
- health, fidelity, lineage, missingness, conflicts, revisions, and configuration identity for
  every displayed layer.

This is **accepted roadmap intent**, not a claim that 9D.5 or 9D.6 is currently implemented. Stage
9D is not complete until its connected acceptance and durability/recovery exit criteria are met.
The dashboard may prototype these layers from deterministic fixtures before those stages finish,
but a fixture preview must never be labeled live.

### 2.3 Later capabilities

The same workspace may later project, without calculating:

- Stage 9E semantic events and an event timeline;
- Stage 9F bounded option candidates and evidence quality;
- Stage 9G cross-instrument state and relationships;
- Stage 9H separately named richer evidence, including observed trade-at-price evidence only if an
  approved source and contract exist;
- Stage 9I Sir Loke read-model health, cited interpretations, intent lifecycle, and abstention;
- Stage 9J plural opportunities, expression candidates, revisions, invalidations, and expiry; and
- Stage 9K model identities, scores, calibration health, and outcome evidence.

Each later panel is gated on its canonical typed contract and accepted projection semantics. Empty
UI placeholders must not imply that the underlying capability exists.

## 3. Operator Decision Questions

The primary workspace must answer these questions quickly and without requiring log inspection:

1. Which exact instrument contract, provider, venue, analytical profile, session, trade date,
   horizon, source resolution, and configuration version am I viewing?
2. Is the dashboard live, intentionally frozen, reconnecting, stale, partial, or unavailable, and
   what event-time-to-screen delay is currently observed?
3. Are the displayed candles and layers from reported, derived, inferred, partial, restored, or
   unavailable evidence?
4. Which session is active, where are its exact bounds, and which prior-session or configured
   window references are valid?
5. Which canonical entity revision is current, what changed from the prior revision, and when did
   that evidence become effective, observed, calculated, and published?
6. Which objective levels, ranges, gaps, moving/anchored references, swings, FVGs, and zones exist
   on the selected horizon, and which are warming, active, complete, stale, invalidated, or expired?
7. Which state classifications are actually runtime-bound, which exact numerical evidence and
   policy produced them, and where do horizons conflict?
8. Is a volume map truly inferred from completed bars, is volume supported for this profile, and
   which bins/coverage/parameters produced POC, value area, and node candidates?
9. What evidence is missing, conflicting, late, corrected, or outside its permitted fidelity?
10. Can I reproduce an external-chart comparison using the same contract, timezone, session,
    timeframe, visible window, price source, profile method, and value-area settings?
11. Are unrelated instruments and capabilities still healthy, or is a problem local to one
    feed/entity/horizon?
12. Is the dashboard itself consuming abnormal CPU, memory, bandwidth, or render time without
    affecting the core runtime?

## 4. Information Architecture And Primary Workspace

### 4.1 Recommended navigation

Use a compact application shell with four workspaces. Only workspaces backed by accepted contracts
appear in the first release.

| Workspace | Initial content | Later extension |
|---|---|---|
| **Market** | Primary chart, entity layers, state strips, evidence inspector | Stage 9E event markers |
| **Compare** | Synchronized small multiples for up to a bounded instrument count | Stage 9G relationship state |
| **Evidence** | Feed/capability/entity health matrix and lineage inspection | Options, model, and agent health |
| **Timeline** | Initially omitted unless accepted lifecycle facts justify it | Stage 9E events and later opportunity lifecycle |

Do not create a landing page. Opening the application enters the last valid Market workspace or a
deterministic default selection supplied by dashboard configuration.

### 4.2 Primary desktop layout

**Recommendation:** Design first for `1440x900` and larger operational displays, while remaining
usable at `1280x720`.

```text
+--------------------------------------------------------------------------------+
| Global bar: Markeitech | LIVE/FROZEN | run | UTC clock | delay | health | menu |
+------------+--------------------------------------------------+----------------+
| Instrument | Context bar: contract / profile / timeframe / session / horizon    |
| rail       +--------------------------------------------------+----------------+
|            |                                                  | Evidence       |
| watchlist  | Price chart and canonical layers                 | inspector      |
| local      |                                                  | identity       |
| health     |                                                  | timestamps     |
|            |                                                  | lineage        |
|            +--------------------------------------------------+----------------+
|            | State strips / compact numerical evidence / later timeline         |
+------------+-------------------------------------------------------------------+
```

- **Global bar, 44-52 px:** product identity, transport state, live/frozen mode, run ID short form,
  UTC clock, measured projection delay, aggregate dashboard health, and overflow/reconnect status.
- **Instrument rail, 190-240 px:** scan-friendly rows with symbol/contract short label, session
  phase, feed/entity health, and stale age. It is a list, not a stack of cards.
- **Context bar, 40-48 px:** exact instrument, timeframe/source resolution, analytical profile,
  session, horizon, display timezone, and layer preset. Selectors must never silently change one
  another.
- **Chart:** the dominant workspace. It uses stable pane dimensions and does not resize when labels,
  tooltips, lifecycle badges, or missing states change.
- **Evidence inspector, 300-380 px:** a resizable details panel for the selected candle, entity,
  metric, or event. It uses sections and tables, not nested cards.
- **Bottom evidence band, 140-240 px:** synchronized state strips and compact scalar values. It can
  collapse to preserve chart area.

At narrower widths, the instrument rail collapses to an icon/symbol list and the inspector becomes
an edge drawer. Mobile is a coherent diagnostic fallback, not a full trading workspace: one chart,
one compact selector bar, and a bottom-sheet inspector with no overlap or hidden status.

### 4.3 Density rules

- No decorative cards, nested cards, hero treatment, gradients, bokeh, or explanatory feature copy.
- Use separators, aligned columns, restrained bands, and table density for scanability.
- Keep labels short in the workspace; full definitions belong in tooltips and the inspector.
- Reserve gold for selection, canonical focus, and identity emphasis rather than making every
  element gold.
- Show at most the configured visible layer count. Overflow goes to layer controls, not the chart.
- Every badge has fixed dimensions or a bounded responsive width so state changes do not shift the
  chart.

## 5. Chart And Layer Specification

### 5.1 Shared layer contract

Every rendered layer needs a projection record containing, directly or by stable reference:

- canonical definition/type and schema version;
- provider, instrument, exact contract, venue where supplied, profile and profile version;
- calendar, trade date, session/window, timeframe/source resolution, and horizon;
- effective/event, observed, received where applicable, calculated, and published UTC timestamps;
- revision and previous revision where supplied;
- source, evidence references, parameter/config versions, and restoration state;
- lifecycle, health, fidelity, missing reasons, and conflicts; and
- display bounds or values already present in canonical evidence.

The chart adapter may map canonical coordinates to pixels, format values, clip off-screen shapes,
and group already canonical OHLC fields into one visual candle. It may not resample, interpolate,
fill gaps, derive thresholds, merge zones, classify direction, calculate profile nodes, or infer
market meaning.

### 5.2 Candles and volume

- Render one exact configured bar specification at a time. Never blend sources within a series.
- Use canonical completed OHLC values. A developing candle may appear only if an approved canonical
  contract explicitly distinguishes it from completed evidence.
- Preserve actual timestamps. Scheduled closures may be visually compressed only under an explicit
  axis mode; unexpected in-session gaps remain visible.
- Default to candle bodies with thin wicks and optional supported volume in a dedicated pane.
- Missing or partial candles create whitespace or a hatched gap marker, never synthetic OHLC.
- Corrected/revised evidence replaces the affected candle and adds a temporary revision marker;
  the inspector preserves current and previous revision references.
- The visible-range auto-scale uses only visible canonical geometry plus configured display
  padding. Display padding is a UI parameter and has no analytical meaning.
- Volume is absent, not zero, when unsupported or missing. Tooltip text states the reason.

**Decision gate:** Current V2 has completed-bar `MetricValue` outputs but no approved late-join
completed-bar projection snapshot. Before live implementation, Markeitect must approve whether the
measurement owner publishes a bounded transport-neutral completed-bar projection/snapshot or the
dashboard bridge performs a strictly validated grouping of the existing OHLC `MetricValue`s. The
recommendation is an owner-supplied canonical projection contract because it can guarantee atomic
bar identity, source consistency, completeness, revision, and bootstrap semantics without making
the dashboard guess.

### 5.3 Sessions and prior references

- Show the selected session's exact open/close bounds as subtle vertical boundaries and phase
  shading. Closed, maintenance, GTH, RTH, Curb, and overnight labels come from configured vocabulary.
- Previous-session high, low, open, close, and other approved references use thin direction-neutral
  lines with compact right-axis labels.
- Distinguish active/developing, completed, restored, partial, and stale references through line
  pattern and opacity as well as color.
- Never infer a session from browser locale or wall-clock boundaries.
- The inspector shows calendar ID, schedule version, IANA timezone, trade date, phase bounds, and
  the source session event.

### 5.4 Configured ranges and windows

- Opening ranges, overnight ranges, power-hour windows, and future approved windows use named
  translucent bands with exact start/end boundaries.
- Developing windows have an open trailing edge or diagonal hatch. Completed windows use a solid
  boundary. Partial coverage uses a distinct hatch and explicit coverage value.
- Extensions appear only when the canonical entity supplies them. The UI does not calculate range
  multiples.
- A window outside its applicable profile/session is `UNAVAILABLE` or omitted with an explicit
  inspector reason; it is not rendered at zero.

### 5.5 Moving and anchored references

- Render session bar-VWAP estimates, configured EMAs, and later anchored references only when an
  accepted runtime-bound entity or metric supplies the value.
- Each line identifies formula/definition, source price, source resolution, period or anchor,
  parameter version, health, and fidelity.
- Slope and separation state belongs in the state strip or inspector. The frontend does not derive
  it from visible line pixels.
- No moving reference is visually privileged as support, resistance, trigger, or trend truth.

### 5.6 Swings

- Confirmed swings use compact pivot markers aligned to the canonical pivot timestamp and price.
- Confirmation time is separately inspectable so the chart cannot imply the swing was known at the
  pivot time.
- A developing candidate is shown only if Stage 9D.5 publishes it canonically. It must use a hollow
  or dashed marker distinct from confirmed geometry.
- Prominence, detector version, left/right span, horizon, source resolution, tie handling, health,
  and fidelity remain inspectable.
- Invalidated or expired swings fade and receive a lifecycle glyph; they do not disappear while
  revision visibility is enabled.

### 5.7 Fair value gaps

- Render the exact remaining FVG interval as a bounded rectangle from formation time to the current
  or terminal lifecycle time.
- Direction may influence edge color, but direction is not translated into a trade recommendation.
- Fill percentage is shown by an internal progress treatment only when supplied canonically.
- Formation, active, partially filled, filled/complete, invalidated, and expired states use a
  stable combination of border style, fill pattern, opacity, and lifecycle glyph.
- Width, normalized width, wick/body policy, source bars, merge policy, age, and revision are in the
  inspector.
- The label says `FVG geometry`; it never says support, resistance, target, or setup.

### 5.8 Derived zones

- Zones are low-opacity horizontal bands with exact bounds and a short definition/horizon label.
- Clicking a zone highlights every constituent entity and revision in the inspector.
- Split/merge revisions animate only as a brief reduced-motion-safe outline transition; current
  geometry must not interpolate through prices that never existed canonically.
- Confluence is a constituent count and lineage list only when the canonical payload supplies it.
- Zone opacity must be capped so candles, gaps, and evidence warnings remain readable.

### 5.9 Inferred bar-volume distribution

- Place a horizontal volume histogram against the right side of the price pane or in a synchronized
  narrow profile pane. Width encodes only canonical inferred bin volume.
- Keep the visible label `INFERRED_FROM_BARS` in the pane header and inspector at all times.
- POC, value-area bounds, HVN/LVN candidates, balance areas, and shape descriptors appear only when
  supplied by the accepted 9D.6 entity revision.
- Show contributing interval, bar count, allocation method/version, bin definition, tick rounding,
  value-area percentage, smoothing/node policy, coverage, supported volume, and fidelity.
- Changing the visible chart range must not silently recalculate a visible-range profile. A profile
  remains tied to its canonical configured session/window.
- Never label or style this layer as footprint, order flow, delta, CVD, aggressive volume,
  absorption, trapped traders, or observed trade-at-price volume.

### 5.10 State strips and numerical panels

- Use one fixed-height strip per enabled canonical family: volatility, compression/expansion,
  directional state by exact horizon, reference slope/separation, and later trend/rotation.
- Each strip shows category intervals over time, candidate/confirmation state where supplied,
  unavailable spans, and exact policy version.
- Conflicting horizons remain side by side. There is no universal bullish/bearish summary.
- The scalar table shows the exact values supporting the selected classification, including
  coverage, baseline counts, age, health, and fidelity.
- A family not runtime-bound is labeled `Not available in this runtime configuration`, not guessed
  from the chart.

### 5.11 Health, fidelity, lineage, and lifecycle styling

Use redundant visual encoding so color is never the only carrier:

| Meaning | Recommended treatment |
|---|---|
| `ACTIVE` / healthy usable evidence | solid line or fill, normal opacity, explicit text in inspector |
| `COMPLETE` | solid terminal cap and completion glyph |
| `WARMING` / developing | dashed boundary or hollow marker |
| `DEGRADED` / partial | amber edge plus diagonal hatch |
| `STALE` | muted color plus dotted edge and age label |
| `UNAVAILABLE` / `UNSUPPORTED` | no geometry; reserved empty state with reason |
| `INVALIDATED` | struck or crossed lifecycle glyph, low-opacity retained geometry |
| `EXPIRED` | low-opacity outline, hidden by default after a bounded grace period |
| `REPORTED` | neutral solid source marker |
| `DERIVED` | blue source marker |
| `INFERRED` | gold hatch and explicit fidelity label |
| `PARTIAL` | split marker plus missing-reason count |
| `RESTORED` | clock/restore glyph until catch-up evidence makes current use honest |

The inspector expands lineage from entity to metric/entity/session references without issuing
runtime queries that can block the market-data path. Unknown references remain unknown and visible.

### 5.12 Multi-timeframe and revision visibility

- Timeframe, source resolution, analytical horizon, and session window are separate selectors.
- Layer applicability is filtered by exact identity; selecting a five-minute candle view does not
  silently rewrite a one-hour swing into five-minute evidence.
- A compact horizon matrix shows which layers are available, hidden, stale, or unsupported.
- Default chart view shows current revisions. A revision mode overlays previous geometry for the
  selected entity only and lists meaningful changes; it does not retain unbounded revision history.
- If a revision sequence gap or conflict is detected, mark the affected projection `PARTIAL`, stop
  applying its deltas, and request a fresh snapshot. Never continue with a guessed revision.

## 6. Interaction Model

### 6.1 Selectors

- **Instrument:** canonical instrument/contract identity, not a free-form ticker alias.
- **Timeframe/source resolution:** populated from available canonical series and configuration
  metadata; unavailable values remain disabled with a reason.
- **Session:** configured named session/window and trade date.
- **Analytical profile:** exact ID and version; changing it creates a new view identity.
- **Horizon:** independent of candle resolution.
- **Timezone:** `UTC`, exchange IANA timezone, and operator-local display. UTC remains canonical.

Selectors preserve their current value when valid. A runtime configuration change that invalidates
a selection prompts a visible deterministic fallback and records why; it never silently displays a
different contract under the old label.

### 6.2 Layer controls

- Use eye icons for visibility, lock icons for pinned layers, swatches for colors/patterns, and
  grouped menus for mutually exclusive modes.
- Presets are display-only configurations such as `Geometry`, `Structure`, `Volume`, and `Health`.
  They do not activate runtime capabilities.
- Layer ordering is fixed by semantic z-index to prevent a user preference from hiding candles or
  health warnings behind opaque geometry.
- Persist local UI preferences only in browser-local storage under a versioned display schema.

### 6.3 Hover and inspect

- A synchronized crosshair drives candle, state-strip, profile-bin, and entity inspection.
- Hover gives a terse value/time/health summary. Click pins the full inspector.
- The inspector exposes identity, lifecycle, payload values, all timestamps, health/fidelity,
  missing/conflict reasons, source, schema/definition/parameter/config versions, and evidence refs.
- Copy actions produce a compact, source-faithful comparison record; they do not export secrets or
  raw unbounded data.
- Inspection must use the already received read model and must not issue a synchronous runtime call
  per hover.

### 6.4 Live and snapshot modes

- **Live mode:** apply bounded coalesced deltas and keep the selected latest edge visible unless the
  operator has panned away.
- **Snapshot mode:** freeze one complete projection generation with capture timestamp and watermarks.
  Incoming updates may update a small unread counter but cannot mutate the frozen view.
- Resuming live first requests or validates a fresh snapshot; it does not replay an unbounded hidden
  backlog.
- Exported screenshots include a small footer with mode, capture time, run, contract, profile,
  timeframe, session, timezone, and config/definition versions.

### 6.5 Compare instruments

- Recommend synchronized small multiples, not overlaid prices, for up to four configured instruments.
- Default to independent price scales with shared crosshair time. A display-only rebased percentage
  mode requires separate approval and a permanent `DISPLAY TRANSFORM` label.
- Comparison does not infer leadership, lag, correlation, or catch-up before Stage 9G supplies those
  canonical states.
- Each pane preserves its own contract, session, health, and missingness.

### 6.6 Zoom, pan, and time axis

- Mouse wheel/trackpad zoom, drag pan, double-click fit, and a `go live` control follow familiar
  financial-chart conventions.
- Preserve the exact selected window across layer changes where data bounds permit.
- Recommend two explicit axis modes: `Elapsed` and `Session-compressed`. Scheduled closures may be
  compressed in the second mode; in-session data gaps remain visible in both.
- External-chart comparison records the chosen axis mode and display timezone.

### 6.7 Later alerts and timeline

When Stage 9E and later contracts exist, add a quiet timeline below the chart:

- plot immutable event time separately from publication time;
- group repeated projections without changing event identity;
- filter by type, horizon, severity, fidelity, and lifecycle;
- select an event to highlight cited entities and evidence; and
- never let browser notification state become canonical alert acknowledgment.

### 6.8 Keyboard ergonomics

Recommended defaults, disabled while typing in inputs:

- `J` / `K`: next/previous instrument;
- `[` / `]`: previous/next available timeframe;
- `Space`: freeze/resume live mode;
- `F`: fit visible data;
- `I`: toggle inspector;
- `L`: open layer menu;
- `G`: go to live edge;
- `/`: open a compact command palette; and
- `Esc`: close transient UI or clear pinned inspection.

All controls remain operable without shortcuts. Icon buttons need accessible names and hover/focus
tooltips.

## 7. Data And Read-Model Boundary

### 7.1 Existing canonical inputs to consume

The first approved projection bridge should consume only the contracts required for enabled views:

- `MetricValue` CustomData (`markeitech.metric.value`);
- `EntityRevision` CustomData (`markeitech.entity.revision`);
- `EntitySnapshotRequest` / `EntitySnapshotResponse` for current entity bootstrap;
- `SessionStateEvent` signals;
- `EvidenceHealthEvent` and `EvidenceHealthSnapshot` signals;
- `SystemHealthEvent`, runtime resource samples, and resource-health transitions for operational
  status; and
- later accepted 9D.5/9D.6 contracts through the shared entity envelope.

Native quotes, trades, books, chains, and raw provider bars are not dashboard inputs. Historical
responses remain transient warmup evidence. The dashboard does not read PostgreSQL for chart data.

### 7.2 Missing bootstrap contract

Entity and evidence-health snapshots exist. A general metric/completed-bar late-join snapshot does
not. The dashboard therefore cannot assume that subscribing after runtime startup reconstructs a
complete chart.

**Recommendation:** Approve a bounded, transport-neutral projection bootstrap owned by the
component that already owns accepted completed bars and metric identity. It should provide exact
accepted candle/metric values for a requested instrument/profile/resolution/session scope plus a
watermark after which ordered deltas apply. It must not add a new calculation or raw-data retention
policy. Contract name, serialization, retention depth, requester authorization, and actor owner are
open architecture decisions.

### 7.3 Recommended process boundary

```text
Canonical Nautilus signals and CustomData
    -> minimal in-runtime projection bridge
       - validates allowed typed contracts
       - copies into bounded non-blocking egress queues
       - requests canonical snapshots when required
       - never calculates or stores market truth
    -> local IPC with schema/version handshake
    -> separate dashboard gateway/read-model process
       - bounded transient projection cache
       - snapshot + coalesced delta protocol
       - read-only HTTP/WebSocket surface
    -> browser client
```

The bridge is intentionally smaller than the former Observatory. It serves no HTML, performs no
chart rendering, owns no browser refresh loop, and never serializes an entire retained store from a
Nautilus callback.

### 7.4 What the projection may cache

The separate gateway may retain, within approved count and byte bounds:

- the latest revision by exact canonical identity;
- a bounded recent completed-bar/display-series window for explicitly active scopes;
- bounded recent revisions needed to render visible lifecycle history;
- current session, evidence health, system health, and resource-health projections;
- current definition/configuration metadata needed to label the view;
- per-stream sequence/watermark and gap state;
- one bounded bootstrap snapshot per active scope; and
- per-client selection, visibility, and delivery cursor.

This cache is transient and reconstructable. Gateway restart may cause a warming view until the
canonical snapshot contract responds.

### 7.5 What the projection must not do

It must not:

- aggregate or resample bars;
- interpolate missing data or fill absent values with zero;
- calculate returns, ATR, EMA, VWAP, profile bins/nodes, state, zones, thresholds, or interactions;
- merge, split, confirm, fill, invalidate, expire, or reclassify entities;
- substitute one source, contract, profile, resolution, or parameter version for another;
- infer session boundaries from the browser clock;
- query arbitrary PostgreSQL tables or treat logs as canonical market data;
- persist raw bars, metrics, full snapshots, or browser interaction into PostgreSQL;
- publish any projection back onto canonical market/intelligence channels; or
- expose dashboard cache or browser state to Sir Loke as evidence truth.

Display formatting, pixel geometry, sorting, filtering, clipping, and already-labeled selection are
presentation work. Any display transform that changes numerical values, such as rebasing prices,
must be explicitly labeled and approved.

### 7.6 Transport alternatives

| Alternative | Benefits | Costs / risks | Recommendation |
|---|---|---|---|
| Minimal bridge plus Unix-domain socket or loopback TCP to a separate gateway | Strong failure isolation; local; no new broker; bounded protocol; gateway can restart independently | Requires approved IPC and snapshot contracts; one small runtime bridge remains | **Preferred** |
| Embedded HTTP/WebSocket server inside the Nautilus process | Fewer processes; quick fixture demo | Repeats Observatory coupling; browser demand can consume runtime CPU/RSS; weaker containment | Fixture-only experiment, not live acceptance |
| PostgreSQL polling | Familiar durability and query tools | Current DB intentionally lacks raw/transient chart data; adds write volume and lag; confuses audit with bus | Reject |
| Redis, NATS, Kafka, or another broker | Mature cross-process fan-out | New infrastructure, ownership, persistence, and operations without measured need | Defer |
| File/log tailing | Simple prototype | No typed ordering/snapshot contract; log rotation and partial writes; diagnostics become truth | Reject |

**Recommendation:** Start with an inspectable versioned JSON envelope over a bounded local IPC
channel. Add binary encoding only if profiling shows serialization is a material bottleneck. The
browser uses snapshot plus WebSocket deltas, but the server must implement application-level
backpressure because the standard browser WebSocket API does not provide it automatically.

### 7.7 Snapshot and delta semantics

Before a client becomes live:

1. negotiate transport/schema versions and allowed view scopes;
2. receive one complete bounded snapshot with generation and per-stream watermark;
3. atomically install that snapshot;
4. apply only later compatible revisions/deltas;
5. detect sequence gaps, incompatible versions, or overflow;
6. mark the affected view partial and request a replacement snapshot; and
7. resume only after the replacement snapshot is complete.

At-least-once delivery and idempotent admission are assumed. Exactly-once transport is not.

### 7.8 Approval gates before implementation

Markeitect approval is required for:

- the in-runtime bridge owner and actor/composition change;
- the completed-bar/metric bootstrap snapshot contract;
- IPC transport, serialization, schema/version handshake, and trust boundary;
- gateway process/container ownership and startup relationship;
- transient cache scope and count/byte/time bounds;
- coalescing, priority, overflow, resnapshot, and reconnect policy;
- any new configuration block or dependency;
- whether resource events may be projected outside the core process;
- local authentication/token handling and remote-access prohibition;
- chart library/license and required attribution; and
- any future operator command path. The recommended first release has none.

## 8. Runtime Isolation And Performance Budget

### 8.1 Evidence from the prior Observatory

The experimental `v2-stage-observatory` branch maintained an honest read-only boundary and
accepted 307,296 metric points without reported actor/HTTP/rendering errors during its functional
run. Severe host degradation later occurred while the browser projection was open. Root cause was
not proven. The leading hypothesis was repeated full-store copy and JSON serialization on every
browser poll, followed by repeated full Plotly updates.

The subsequent Observatory-off resource run showed bounded core-runtime RSS/cache behavior. That
is evidence that the core runtime can remain bounded without the projection; it is not proof that
all future dashboard designs are safe. The dashboard must earn acceptance through controlled
off/on comparison.

### 8.2 Isolation recommendation

- Run the gateway/read model and frontend server in a **separate OS process** from Nautilus.
- Prefer an optional separately limited Docker Compose service after local-process development is
  stable. Do not place Nautilus in that container merely to simplify dashboard networking.
- Keep the in-runtime bridge limited to typed admission, bounded queueing, snapshot coordination,
  and non-blocking egress.
- Dashboard absence, crash, restart, browser overload, or slow clients must not alter acquisition,
  metrics, entities, persistence, Discord, readiness, or shutdown.
- The normal V2 runtime must remain fully operable with dashboard export disabled.

### 8.3 Proposed acceptance budgets

The following are **recommendations for measurement and review, not approved facts or proven
capacity**. They assume the current 18-member watchlist, one primary workspace, up to four local
browser clients, and bounded current/previous-session context. Benchmark fixtures must state their
exact message rate and layer cardinality.

| Dimension | Proposed initial budget |
|---|---|
| Core bridge steady RSS overhead | <= 64 MiB over dashboard-off control |
| Core bridge transient peak overhead | <= 96 MiB over control, returning below steady budget after burst |
| Core bridge CPU | <= 2% of one core over 5 minutes; <= 5% over any 10-second burst |
| Core callback admission | p99 <= 0.5 ms with no network, disk, JSON full-snapshot, or browser work inline |
| Core egress queue | Both message-count and byte bounded; proposed start 10,000 items and 16 MiB, subject to fixture sizing |
| Critical health/lifecycle reserve | Separate bounded lane; proposed 512 items and 1 MiB |
| Gateway RSS | <= 256 MiB steady for baseline scope; <= 384 MiB during resnapshot |
| Gateway CPU | <= 10% of one core over 5 minutes; <= 25% over a 10-second resnapshot burst |
| Browser RSS | <= 350 MiB for one workspace; <= 600 MiB for four-pane compare |
| Browser CPU while visible | <= 15% of one core over 5 minutes on the target workstation |
| Browser CPU while hidden | <= 1% of one core after visibility throttling settles |
| Healthy event-to-visible latency | p95 <= 500 ms and p99 <= 1,000 ms for accepted low-volume projection deltas |
| Render work | <= 4 visual commits/second for the active chart; <= 2/second for status tables |
| Outbound WebSocket frames | <= 10/second/client after server-side coalescing |
| Main-thread responsiveness | p95 long task < 50 ms during normal live operation |
| Reconnect | exponential backoff with jitter, proposed 0.5-15 seconds, then snapshot reconciliation |

These budgets must become typed, bounded, versioned configuration or acceptance-policy values where
they affect runtime behavior. Host-specific calibration can revise them only through review.

### 8.4 Backpressure and coalescing

- Bound every queue by item count and serialized bytes.
- Coalesce revisioned current state by exact identity in the gateway, not in the canonical runtime
  callback. Latest-wins coalescing is allowed only when the skipped intermediate revisions are not
  required by a visible lifecycle or audit question.
- Do not coalesce terminal lifecycle, health transitions, gap/conflict markers, or future semantic
  events unless their owning contract explicitly permits it.
- Assign explicit priorities: connection/schema/health and terminal lifecycle; current selected
  scope; visible comparison scopes; background watchlist summaries; optional diagnostics.
- On bridge overflow, never block. Count and publish an operational projection failure through an
  approved path, mark the gateway stream incomplete, and force snapshot recovery.
- On client overflow, disconnect or downgrade that client and require a fresh snapshot. Never let
  one client create an unbounded server queue.

### 8.5 Browser behavior

- Use `document.visibilityState` to suspend chart rendering in hidden tabs.
- Do not accumulate every hidden-tab delta for later animation. Retain only bounded current state
  and request/validate a snapshot on return.
- Render only visible panes and visible-range geometry; virtualize long tables and timeline rows.
- Avoid per-frame React state updates for chart points. Feed bounded batches directly to the chart
  adapter while keeping canonical identity in an immutable store.
- Dispose charts, observers, workers, and sockets when a workspace closes.
- Expose local dashboard render FPS, queue depth, dropped/coalesced counts, serialized bytes, and
  snapshot duration in a diagnostic panel and logs.

### 8.6 No-impact acceptance criterion

A dashboard-on run is unacceptable if, compared with a same-configuration dashboard-off control,
it changes provider subscription counts, accepted market observations, calculation failures,
entity revision correctness, persistence reconciliation, Discord behavior, global health, or clean
shutdown. Resource differences must remain within approved budgets, and disabling/killing the
dashboard must leave the core runtime healthy.

## 9. Configuration And Identity Contracts

### 9.1 Configuration separation

**Recommendation:** Separate configuration into two ownership domains after approval:

- a small runtime export/bridge block for enabled state, endpoint, allowed contract families,
  queue/byte bounds, snapshot-request limits, timeout, and shutdown budget; and
- a gateway/display block for bind address, client limit, cache bounds, update cadence, render
  budgets, default workspace, layer presets, compare count, and local auth policy.

Display preferences must not live in analytical configuration. Browser-local preferences are
versioned and reset safely when incompatible.

### 9.2 Required identity

Every dashboard snapshot, delta, layer, screenshot export, and copied comparison record preserves:

- runtime run ID and source component;
- provider and native instrument ID, explicit contract and venue where canonical contracts supply
  them;
- calendar ID/version, IANA timezone, trade date, session phase/window;
- analytical profile ID/version;
- source resolution/bar specification and independent horizon;
- metric/entity/event schema, definition, formula, parameter, policy, and configuration versions;
- effective/event, observed, received where applicable, calculated, published, gateway-received,
  and rendered timestamps as available;
- revision, previous revision, restored state, causation/correlation where supplied;
- health, fidelity, coverage, missing/conflict reasons, and lineage; and
- projection schema/generation and client display mode.

The UI may abbreviate identity in the chart, but the inspector and exports must retain it exactly.

### 9.3 Version behavior

- Unknown major schema/definition versions fail closed for that layer.
- Compatible additive projection fields require explicit decoder policy; never ignore a field that
  affects identity, fidelity, lifecycle, or numerical meaning.
- A parameter or profile version change creates a visible boundary. Do not draw one continuous line
  across changed semantics without a break marker.
- If two current revisions claim one identity/revision with different payloads, mark conflict and
  stop that projection pending snapshot recovery.
- UI defaults and layer presets carry their own display version and never overwrite analytical
  version labels.

### 9.4 Tunable display values

Theme, pane sizes, auto-scale padding, visible revision grace period, render cadence, cache limits,
client limits, reconnect windows, compare count, and label density are typed, bounded, versioned
display or operational configuration. They require defaults, units, scopes, minimum/maximum values,
mutability, source, effective time, and audit/log behavior where changes occur at runtime.

## 10. Technology Options And Recommendation

No dependency is selected or authorized by this draft. Versions and license terms must be
re-verified at the implementation gate.

### 10.1 Backend and transport

#### Option A: Python 3.13 gateway with FastAPI/Uvicorn

**Pros**

- Matches the V2 language/runtime expertise and typed-contract ecosystem.
- FastAPI has first-class WebSocket and test-client support and is MIT licensed.
- Straightforward health, snapshot, static-asset, and read-only WebSocket endpoints.
- Keeps serialization and projection validation close to existing Python contracts while remaining
  in a separate process.

**Cons**

- Adds dependencies and a second Python process.
- Shared dataclass contracts need an explicit transport serialization package/boundary rather than
  importing live actors or Nautilus internals into the gateway.
- Standard browser WebSocket requires application-level queue and backpressure policy.

#### Option B: Node/TypeScript gateway

**Pros**

- One language for server and browser transport schemas.
- Strong streaming ecosystem and direct reuse of generated TypeScript types.

**Cons**

- Duplicates Python contract validation or requires code generation.
- Adds another server runtime and operational toolchain beside the established Python project.

#### Option C: Embedded Python HTTP server

Fewer pieces, but unacceptable as the default because it repeats the single-process Observatory
risk and weakens failure containment.

**Backend recommendation:** A separate Python 3.13 FastAPI/Uvicorn gateway, with transport DTOs
generated or validated against an approved neutral schema. Keep the bridge in the core runtime
minimal. This is a recommendation, not dependency approval.

### 10.2 Frontend application

**Recommendation:** TypeScript with a small React application shell and a dedicated imperative
chart adapter. React owns selectors, tables, inspectors, connection state, and layout; the chart
engine owns canvas updates outside per-point React rendering. Pin exact versions only after a
dependency, license, bundle-size, and long-run benchmark review.

A framework-free client would reduce dependencies but increases custom state, accessibility, and
component lifecycle work for a multi-pane, multi-selector operational tool. A larger dashboard
framework would encourage decorative/card-heavy composition and bring unnecessary runtime weight.

### 10.3 Financial chart engines

#### TradingView Lightweight Charts 5.x

Official metadata currently describes it as an HTML5 Canvas financial chart library under
Apache-2.0. The 5.x API includes candlesticks, multiple panes, realtime updates, custom series, and
series/pane primitives; official plugin examples include session highlighting and volume profile.
Its project requires the TradingView attribution notice/link described in its repository.

**Pros:** financial interaction model, small focused surface, Canvas performance, panes, exact
crosshair, custom primitives for ranges/FVGs/zones/profile, TypeScript API.

**Cons:** custom layers and accessibility are implementation responsibility; volume profile and
complex lifecycle hit testing need a benchmark; attribution and NOTICE compliance require approval.

#### Apache ECharts 6.x

Official project material currently identifies Apache-2.0 licensing, Canvas/SVG rendering,
candlesticks, custom series, streaming, data zoom, and large-data support.

**Pros:** rich built-in visualization vocabulary, custom series, strong data-zoom/tooltips, broad
accessibility and renderer options.

**Cons:** more generic/heavier than a focused financial chart, financial crosshair/pane behavior
needs more tailoring, and complex option diffs can still trigger expensive rerenders.

#### Plotly.js / Plotly.py

Plotly.js is MIT licensed and broad. The isolated Observatory used embedded Plotly through Python
and called `Plotly.react` after polling a complete snapshot.

**Pros:** excellent exploratory plotting, broad traces, familiar offline output.

**Cons:** the prior implementation's full-copy/full-refresh pattern was associated with severe host
degradation, though Plotly was not proven as the root cause. It is not the best first choice for a
long-running dense financial workstation with many custom lifecycle layers.

#### Highcharts Stock

**Pros:** mature stock-chart interaction, navigator/range controls, annotations, accessibility, and
commercial support.

**Cons:** current Highcharts terms require a commercial license for internal business use, including
R&D/prototyping. Cost and license scope need explicit Markeitect approval.

### 10.4 Chart recommendation and proof gate

Prototype the exact hardest layers in **TradingView Lightweight Charts 5.x** using deterministic
fixtures: 5,000 candles, 200 concurrent FVG/zone/swing objects, a 200-bin inferred profile, four
synchronized panes, revision updates, hit testing, and accessibility companion content. Compare it
against an ECharts implementation using identical data and instrumentation.

Select Lightweight Charts only if it passes frame-time, memory, pixel, interaction, custom-layer,
and attribution review. Keep Plotly for bounded offline research artifacts, not the live primary
surface. Highcharts remains a paid fallback if commercial support and built-in capability justify
the license.

### 10.5 Current external references to recheck at approval

- [Lightweight Charts documentation](https://tradingview.github.io/lightweight-charts/)
- [Lightweight Charts package and license metadata](https://github.com/tradingview/lightweight-charts/blob/master/package.json)
- [Lightweight Charts plugin model](https://tradingview.github.io/lightweight-charts/docs/5.1/plugins/intro)
- [Apache ECharts features](https://echarts.apache.org/en/feature.html)
- [Apache ECharts repository and license](https://github.com/apache/echarts)
- [Plotly.js repository and MIT license](https://github.com/plotly/plotly.js/)
- [Highcharts commercial-use terms](https://shop.highcharts.com/license-eula)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [Browser WebSocket backpressure limitation](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

## 11. Accessibility And Visual System

### 11.1 Accessibility target

Target WCAG 2.2 AA for the application shell and all non-chart controls. Canvas content requires a
parallel accessible representation rather than an assertion that pixels are accessible.

- Full keyboard navigation with visible focus and logical order.
- Accessible names for every icon, swatch, selector, pane, and lifecycle glyph.
- Minimum 4.5:1 contrast for normal text and 3:1 for large text and essential non-text controls.
- Health, lifecycle, direction, and fidelity never rely on color alone.
- Tabular numerals and locale-safe formatting; no font-size scaling with viewport width.
- A screen-reader summary for the selected instrument/time, current OHLC, active entities, state,
  and evidence warnings. Announcements are throttled to meaningful changes.
- A keyboard-accessible evidence table mirrors the selected chart content.
- Respect `prefers-reduced-motion`; no pulsing price or health animation.
- Support 200% browser zoom without overlap; keep touch targets usable in the mobile fallback.

### 11.2 Markeitech visual direction

Use a near-black operational canvas, off-white text, restrained gold identity accents, and a
multi-hue semantic palette:

- background: near black, not blue/slate;
- primary text: off-white; secondary text: neutral gray;
- identity/selection/inferred emphasis: muted gold;
- positive/up geometry: accessible green;
- negative/down geometry: accessible coral/red;
- derived/reference evidence: cyan/blue;
- warming/degraded: amber;
- unavailable/stale: gray plus pattern;
- conflict/critical: high-contrast red plus glyph.

Use no gradients. Keep chart grid lines faint but visible. Gold must not replace semantic health or
direction colors. Use one restrained sans-serif family, tabular numeric variants, 12-14 px dense UI
text, and 16-18 px application headings. Chart labels must clip or wrap within fixed bounds and
never overlap the price scale incoherently.

## 12. Security, Local Deployment, Logging, And Failure Modes

### 12.1 Security boundary

- Bind gateway HTTP/WebSocket and runtime IPC to loopback or a local Unix-domain socket by default.
- Reject non-loopback binding unless a separately approved authentication, TLS, network, and threat
  model exists.
- Enforce same-origin checks, an ephemeral local session token, client count, request size, message
  size, rate, and timeout limits.
- Bundle frontend and chart assets locally; no runtime CDN calls, analytics, telemetry, or external
  fonts.
- Never expose IB credentials, account data, PostgreSQL DSN, Discord webhook, environment values,
  raw logs, stack traces, or arbitrary filesystem paths.
- First release has no write/control endpoint. HTTP methods other than required reads and WebSocket
  upgrade are rejected.
- Apply a restrictive Content Security Policy, `nosniff`, frame denial, no-store for live snapshots,
  and explicit WebSocket subprotocol/version negotiation.
- Treat all labels/reasons as untrusted text and render them without HTML injection.

### 12.2 Local operator setup recommendation

- Keep the existing **Markeitech V2** PyCharm run configuration unchanged.
- Add a separate **Markeitech Dashboard** run configuration only in an approved implementation
  batch. It starts the gateway/frontend but never starts IB or PostgreSQL implicitly.
- Optionally add a separately limited Docker Compose dashboard service after the process boundary is
  accepted. The service binds to loopback and receives no PostgreSQL or IB credentials.
- The dashboard may start before, during, or after V2. It shows `Runtime unavailable` and retries
  within bounds; actor startup ordering is not assumed.
- The runtime remains startable and accepted with dashboard export disabled.

### 12.3 Logging

Use separate rotating gateway logs under the existing ignored local data boundary. Log:

- process start/stop, version, bind address, and configuration identity;
- bridge/gateway connect, disconnect, schema negotiation, and reconnect;
- snapshot request/result duration and size;
- accepted, duplicate, stale, conflict, coalesced, dropped, and resnapshot counts;
- queue item/byte high-water marks, connected clients, outbound bytes, and slow-client actions;
- browser diagnostic summaries when explicitly enabled; and
- sanitized failures with correlation IDs.

Do not log every metric/entity payload, full snapshot, token, secret, hover, pan, or cursor move.
Do not persist browser activity to PostgreSQL in the initial scope.

### 12.4 Failure modes and required behavior

| Failure | Required behavior |
|---|---|
| Dashboard disabled or absent | Core runtime behavior and resources remain unchanged except zero export work |
| Gateway crash/restart | Core bridge drops/coalesces within bounds; no runtime degradation beyond projection health; gateway reboots from snapshot |
| Browser closes/crashes | Gateway releases client state and continues bounded; core unaffected |
| Slow/hidden browser | Throttle rendering; bounded client queue; disconnect and resnapshot if necessary |
| IPC disconnect | Explicit projection unavailable state; bounded reconnect; no core blocking |
| Schema/version mismatch | Fail closed for incompatible stream; show mismatch; preserve unrelated streams |
| Sequence gap/conflict | Mark affected projection partial; stop deltas; request snapshot |
| Snapshot timeout/oversize | Reject, report scope/budget, retry with bounded narrower request; no silent truncation |
| Missing/degraded/stale evidence | Preserve canonical state and reason; no interpolation or last-good masquerade |
| Configuration changes | Visible version boundary; invalidate incompatible cache and resnapshot |
| Gateway memory/CPU breach | Shed background scopes/clients by approved priority, remain observable, or terminate; core unaffected |
| Core shutdown | Render stopping/disconnected truth, close bridge within budget, retain no claim of live state |
| PostgreSQL failure | Dashboard continues from canonical transient stream where available; never substitutes DB history |

## 13. Testing And Acceptance Plan

### 13.1 Deterministic fixtures

Build versioned fixtures from accepted contract serializers, not hand-shaped anonymous JSON. Cover:

- multiple instruments, futures contracts, profiles, sessions, horizons, and timezones;
- historical/live lineage and exact overlap;
- complete, partial, missing, unsupported, stale, degraded, invalidated, expired, restored, and
  conflicting evidence;
- same-timestamp revisions and revision gaps;
- session/holiday/DST/early-close boundaries;
- opening range developing/completing;
- swing confirmation after required future evidence with no look-ahead;
- FVG formation/fill/invalidation/expiry;
- zone split/merge and constituent lineage;
- inferred volume conservation, bin boundaries, POC/value area/HVN/LVN, and unsupported volume;
- configuration/profile/parameter version changes; and
- future semantic-event fixtures kept separate from current 9D truth.

Fixture generation must use pure existing calculators or approved 9D.5/9D.6 implementations. The
frontend fixture server may replay projection contracts for UI testing, but that is not V2 replay or
market backtesting and must not enter the live runtime.

### 13.2 Boundary and protocol tests

- Contract serialization, unknown/malformed fields, major/minor version compatibility.
- Snapshot atomicity, watermark handoff, at-least-once deduplication, ordering, gap, conflict, and
  resnapshot behavior.
- Count and byte bounds at every queue/cache/client boundary.
- Coalescing preserves current revision and never removes prohibited lifecycle/health facts.
- Slow client, client disconnect, gateway restart, bridge restart, and core shutdown.
- Projection adapters prove no analytical calculation or canonical publication path exists.
- A test double rejects all PostgreSQL writes, IB/provider calls, Nautilus subscriptions, Discord
  calls, and canonical bus publications from dashboard components.

### 13.3 Visual and interaction tests

- Playwright screenshots at `1280x720`, `1440x900`, `1920x1080`, and `2560x1440`.
- Mobile fallback checks at `390x844` and `430x932`; mobile need not expose full compare mode but
  must remain coherent and non-overlapping.
- Screenshot baselines for every lifecycle, fidelity, missing, conflict, revision, timezone, and
  layer-density state.
- Canvas pixel checks verify a nonblank chart, expected candle/layer occupancy, stable framing, and
  visible differences when each layer is enabled/disabled.
- Crosshair, hit testing, pan/zoom, fit, go-live, snapshot freeze/resume, selector preservation,
  compare synchronization, keyboard navigation, focus, reduced motion, and 200% zoom.
- Accessibility checks plus manual screen-reader review of the chart companion table and selected
  evidence summary.
- External screenshot comparison records exact contract/venue, API and chart timezone, session,
  timeframe, visible bounds, study method, row/bin size, value-area percentage, source, and V2
  versions. Differences become calibration findings, not silent tuning.

### 13.4 Performance and endurance

- Instrument bridge callback duration, queue depth/bytes, serialization, gateway RSS/CPU, browser
  RSS/CPU, frame time, long tasks, payload size, and event-to-visible delay.
- Run fixture bursts above observed Stage 9C publication rates and cardinalities.
- Run at least 8 hours with one active chart, then four-pane compare, repeated tab hide/show,
  zoom/pan, snapshot/resume, gateway restart, and browser reconnect.
- Confirm memory plateaus after warmup and returns after scope/client disposal.
- Exercise queue overflow and client shedding intentionally.
- Compare dashboard-off and dashboard-on using the same runtime/market configuration. The first
  connected comparison is Markeitect-owned and requires explicit authorization.

### 13.5 Connected acceptance

No connected run is authorized by this plan. After implementation approval, Markeitect should own
a controlled acceptance that records:

- exact branch/commit, runtime/dashboard configuration versions, contracts, session, and browser;
- dashboard-off control and dashboard-on run with unchanged market/runtime settings;
- runtime resource, cache, acquisition, measurement, entity, persistence, Discord, and shutdown
  reconciliation;
- bridge/gateway/client counters and resource budgets;
- selected external-chart comparisons with exact settings; and
- unexercised session, lifecycle, horizon, and market conditions as explicit debt.

Passing UI tests does not prove provider correctness. A visually matching screenshot does not prove
general analytical calibration.

## 14. Phased Delivery Plan

Every batch remains uncommitted for local review. Create a dedicated stage branch and later PR only
after Markeitect approves the architecture, sequence, and branch. No phase below is pre-approved.

### Phase 0: Decisions and contract audit

- Resolve the open decisions in Section 15.
- Inventory exact current producers, message rates, payload sizes, snapshot capabilities, and 9D.5/
  9D.6 contract plans.
- Approve the data-flow threat model, resource budgets, and no-mutation test boundary.

**Exit:** one reviewed architecture record; no code or dependency change.

### Phase 1: Fixture-only visual benchmark

- Build a disconnected static fixture harness outside the live runtime.
- Compare Lightweight Charts and ECharts on the hardest layers and target viewports.
- Measure memory, CPU, frame time, hit testing, accessibility strategy, and pixel stability.
- Produce primary workspace screenshots for Markeitect review.

**Dependency:** Can begin before 9D.5 using versioned synthetic fixtures clearly labeled `FIXTURE`.

**Exit:** chart/library recommendation accepted or rejected; no live integration.

### Phase 2: Projection contracts and pure read model

- Define the approved completed-bar/metric bootstrap and transport envelope.
- Implement pure snapshot/delta admission, identity, revision, gap, conflict, coalescing, and bounds.
- Generate transport schemas/types and deterministic fixtures.

**Dependency:** Exact 9D.5/9D.6 payloads can be added later through the shared entity envelope, but
their fixture contracts must follow accepted stage definitions.

**Exit:** framework-independent read model passes deterministic boundary tests.

### Phase 3: Isolated bridge and gateway

- Add the minimal non-blocking runtime bridge behind disabled configuration.
- Add the separate local gateway, IPC handshake, snapshot API, WebSocket deltas, health, logging,
  auth, backpressure, and limits.
- Prove gateway failure and slow clients cannot affect a sandboxed Nautilus runtime.

**Exit:** typed fixture/current-contract projection works end to end with the dashboard export off by
default.

### Phase 4: Core Market workspace

- Implement shell, instrument/context selectors, canonical candles, sessions, prior references,
  windows, gaps, objective levels, inspector, live/snapshot modes, and screenshot metadata.
- Add evidence-health and operational status surfaces.
- Complete Playwright, accessibility, and canvas-pixel acceptance.

**Dependency:** Approved completed-bar bootstrap contract. Current 9D.3 entities can support this
phase, with acceptance debt shown honestly.

### Phase 5: Runtime-bound market state

- Add state strips for only producer-backed 9D.4 families.
- Add exact numerical evidence, policy identity, confirmation/hysteresis state, staleness, and
  conflicting-horizon presentation.
- Leave unbound families explicitly unavailable.

**Exit:** dashboard reproduces canonical state revisions without classification logic.

### Phase 6: Stage 9D.5 structure layers

- Add confirmed swings, canonical developing state if approved, FVG lifecycle, zones, lineage,
  revision comparison, and density controls.
- Validate no look-ahead presentation and bounded visible objects.

**Dependency:** 9D.5 contracts and offline acceptance. Live claims wait for 9D.5 connected evidence.

### Phase 7: Stage 9D.6 inferred distribution

- Add profile bins, POC/value area/HVN/LVN/balance/shape display and inspector.
- Make `INFERRED_FROM_BARS` persistent in every relevant visual and export.
- Validate unsupported/partial volume and prohibit observed-order-flow language.

**Dependency:** 9D.6 contract and offline acceptance. Full first-dashboard scope cannot close before
9D.6 is accepted.

### Phase 8: Endurance and connected acceptance

- Complete long-run synthetic testing and budget tuning.
- Run the explicitly authorized dashboard-off/on controlled comparison.
- Reconcile all runtime, gateway, browser, persistence, Discord, and shutdown evidence.
- Update authoritative current-status/architecture/operations documents in separately reviewed
  batches after behavior is accepted.

**Exit:** Definition of Done in Section 16 is met for the accepted scope.

### Later phases

Add Stage 9E timeline, Stage 9F option evidence, Stage 9G relationships/compare semantics, Stage 9I
Sir Loke observability, and Stage 9J plural opportunities only after their contracts are accepted.
Do not reserve empty visual prominence or implement speculative adapters now.

## 15. Open Decisions For Markeitect

| Decision gate | Recommended default | Why / tradeoff |
|---|---|---|
| Initial product scope | Human inspection through accepted 9D.6 evidence only | Delivers visual truth before events/options/agent semantics exist |
| Runtime isolation | Minimal bridge in Nautilus; gateway/browser in separate process | Contains projection failure and browser cost |
| Containerization | Develop as separate local process; add optional limited Compose service after proof | Easier profiling first; reproducible isolation later |
| Runtime-to-gateway IPC | Versioned JSON over Unix-domain socket on macOS, loopback TCP fallback | Inspectable, local, no broker; binary only if measured need |
| Completed-bar bootstrap | New approved owner-supplied projection/snapshot contract | Avoids dashboard grouping guesses and supports late join |
| Metric bootstrap | Scope to exact active chart/read-model requirements, not every metric ever published | Keeps memory and traffic bounded |
| Gateway retention | Transient current plus previous-session context for active scopes, with explicit point/byte caps | Useful comparison without durable raw storage |
| Persistence | No dashboard market-data persistence and no PostgreSQL chart reads | Preserves accepted audit/storage boundary |
| Chart engine | Benchmark-gated Lightweight Charts 5.x with required attribution | Financial Canvas fit; custom-layer risk must be proven |
| Alternative chart | Apache ECharts if identical benchmark is materially safer/easier | Broader visuals, potentially heavier/generic |
| Plotly | Offline bounded research artifacts only | Avoids repeating full-snapshot live pattern |
| Frontend | TypeScript/React shell with imperative chart adapter | Strong operational UI state without per-point React rendering |
| Gateway backend | Python 3.13 FastAPI/Uvicorn | Fits current engineering environment and typed Python contracts |
| Time axis default | Elapsed timestamps with optional explicit session-compressed mode | Maximizes truth; still supports familiar session viewing |
| Compare design | Up to four synchronized small multiples with independent scales | Preserves instrument identity and avoids false overlay meaning |
| Remote access | Prohibited; loopback/local socket only | No current auth/TLS/operator-authority design |
| Operator controls | None in first release | Dashboard remains a pure projection |
| Browser local preferences | Allowed under versioned display schema | Ergonomic without mutating runtime truth |
| Mobile scope | Diagnostic fallback only | Product is an operational desktop workstation |
| Performance budgets | Start with Section 8 proposals, then approve after fixture baseline | Converts Observatory concern into measurable gates |
| Startup ownership | Dashboard starts independently and never auto-starts IB/PostgreSQL | Preserves explicit connected-run confirmation |
| Branch/PR | Create a dedicated `v2-live-dashboard` branch only after this plan is approved | Matches repository review authority; no integration is implicit |

## 16. Definition Of Done And Known Risks

### 16.1 Definition of done

The first live dashboard is done only when:

- Markeitect has approved every architecture, product, dependency, license, security, resource, and
  configuration gate used by the implementation;
- current status, architecture, operations, configuration, implementation, and tests agree;
- the dashboard consumes only approved canonical contracts and contains no analytical calculation,
  provider access, database write, Discord call, canonical publication, or operator-control path;
- a late client receives an atomic bounded snapshot and compatible deltas, with deterministic gap,
  revision, conflict, overflow, and reconnect handling;
- price/session geometry, all actually runtime-bound state, 9D.5 structure, and 9D.6 inferred volume
  evidence render with exact identity, lineage, health, fidelity, lifecycle, missingness, and
  revision semantics;
- unavailable or unsupported evidence cannot appear as zero, healthy, observed, or inferred from
  visible pixels;
- `INFERRED_FROM_BARS` is unavoidable wherever candle-derived volume distribution appears;
- desktop workflows are dense, quiet, keyboard-usable, accessible, non-overlapping, and visually
  verified at target viewports; mobile fallback remains coherent;
- canvas pixel checks, screenshot baselines, deterministic fixtures, protocol/failure tests, and
  no-mutation tests pass;
- endurance tests demonstrate bounded bridge, gateway, and browser resources under approved
  message/cardinality fixtures;
- an explicitly authorized dashboard-off/on connected comparison proves no change to provider,
  acquisition, metric/entity correctness, persistence, Discord, global health, or shutdown;
- measured resource and event-to-visible results meet approved budgets or deviations are reviewed;
- third-party licenses, notices, attribution, bundled assets, and version pins are reviewed; and
- the complete batch is inspected for secrets, raw data, logs, generated clutter, and unrelated
  changes, then left uncommitted for local review unless commit approval is explicit.

### 16.2 Known risks

1. **Missing late-join chart contract:** Current metric streams do not provide a general snapshot;
   choosing the wrong owner could duplicate market truth or force speculative retention.
2. **Projection resource regression:** A browser can still overload a separate gateway or host even
   when the core runtime survives. Count/byte/render budgets and off/on controls are mandatory.
3. **Custom chart-layer complexity:** FVGs, zones, revision hit testing, and inferred profile bins
   may stress plugin APIs or make accessibility expensive. The benchmark must test real density.
4. **Version skew:** Runtime, bridge, gateway, and browser can disagree. Fail-closed negotiation and
   visible version boundaries are required.
5. **Visual semantic leakage:** Conventional colors or labels can accidentally imply support,
   resistance, setups, order flow, or advice. Copy and style need domain review.
6. **External-chart mismatch:** Provider source, contract, session, timezone, price source,
   resolution, profile method, and revision policy can differ. Comparison records must capture all.
7. **Inferred-volume misreading:** Profile-like graphics strongly suggest observed trade-at-price
   evidence. Permanent fidelity labeling and distinct styling are required.
8. **State-density overload:** Multiple horizons and lifecycles can obscure price. Fixed z-order,
   layer presets, density caps, and an evidence inspector are required.
9. **Transient-cache expectations:** Gateway restart can warm from bounded snapshots but cannot
   promise replay or arbitrary history under current storage policy.
10. **Session compression ambiguity:** Compressing scheduled closures aids inspection but can hide
    elapsed time. Axis mode must be explicit and included in exports.
11. **Licensing drift:** Chart-library versions, attribution, and commercial-use terms can change.
    Reverify immediately before dependency approval.
12. **Acceptance dependency:** Full first scope depends on 9D.5/9D.6 implementation and acceptance;
    fixture completeness cannot substitute for live canonical evidence.
13. **Connected-recovery debt:** Provider reconnect and evidence recovery remain a mandatory gate
    before live model/agent work and also affect dashboard truth during interruptions.
14. **Workstation variability:** Proposed CPU/RSS budgets are starting points for the current
    operator machine, not universal performance facts.

## Source Basis

This draft is grounded in the current working-tree versions of:

- `markeitech.md`;
- `docs/current-status.md`;
- `docs/development-guidelines.md`;
- `docs/README.md`;
- `docs/roadmap/v2-market-events-live-agent-plan.md`;
- `docs/roadmap/v2-stage-9d-entities-rolling-state-plan.md`;
- `docs/architecture/v2-runtime-messaging-discovery.md`;
- `docs/architecture/v2-adaptive-market-data-plane.md`;
- `docs/architecture/v2-session-evidence-health.md`;
- `docs/operations/v2-runtime-resource-telemetry.md`;
- `docs/operations/developer-setup.md`;
- `docs/operations/github-workflow.md`;
- the isolated `v2-stage-observatory` documentation and implementation only for experimental
  isolation/performance evidence, not as current V2 authority.

Where these sources describe future intent, this draft does not promote it to implemented fact.
