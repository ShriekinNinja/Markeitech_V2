# Detailed Visual Review

Use only the sections that address the requested question. Checklists and output tables are
optional aids for the relevant scope, not requirements to audit every category. Apply this
reference directly; no separate advisor, handoff, or new authority is required.

Use only the sections relevant to the requested view.

## Projection Integrity Gate

Before recommending acceptance of a visual design or implementation plan, build a **Projection
Integrity Matrix** scoped to the affected visible elements and materially changed contracts. Do not
generate exhaustive empty rows for a narrow question:

`Visible element | Operator question | Canonical source contract | Exact identity and timestamps | Health/fidelity/lifecycle states | Allowed presentation transform | Forbidden inference | Bootstrap/delta behavior | Accessibility equivalent | Acceptance evidence | Owner | Decision/gap`

No row may say "canonical" merely because a value appears in a log, cache, database, screenshot,
browser store, or existing chart. Trace it to the accepted owning contract. A visual element without
an authoritative source is omitted or explicitly presented as a fixture/mockup; it is never filled
with a plausible substitute.

Recommend rejection, or stop the affected advisory recommendation, when the surface would need to:

- derive OHLC bars from loose metric values without an approved atomic bar projection;
- calculate EMA, VWAP, ATR, profiles, ranges, returns, deltas, scores, levels, state, or reasoning;
- infer sessions from browser time or silently choose a "latest" definition, profile, contract,
  parameter set, source, or horizon;
- blend sources, rescale comparisons, forward-fill gaps, smooth, conflate, downsample, or interpolate
  in a way that changes analytical meaning without an explicit approved display-transform contract;
- hide conflicts, corrections, stale ages, revision gaps, missing evidence, or unsupported scope; or
- publish browser state, presentation caches, or user interaction back as canonical evidence for Sir
  Loke or another analytical consumer.

## Visual Semantics

Preserve chart timeframe, source resolution, analytical horizon, session window, and profile as
separate identities. A five-minute chart does not turn a one-hour entity into five-minute evidence.
Use synchronized small multiples when overlaid scales would mislead. Any rebasing or normalization is
a separately approved display transform with a permanent visible label.

Annotations render exact canonical geometry and revision identity. Keep pivot/event time distinct
from confirmation/publication time so the display cannot imply look-ahead knowledge. Show developing
state only when it exists canonically. Preserve terminal states for a bounded, policy-owned review
period; disappearance must not rewrite history.

Use redundant encodings. Combine text or symbols with line style, border, fill pattern, opacity, or
position so health, fidelity, lifecycle, and direction never rely on hue alone. Do not use visual
prominence to imply support, resistance, confidence, causality, prediction, action, or priority when
the source contract does not state that meaning.

When an approved Sir Loke output contract exists, map its cited evidence identities, contradictions,
abstention, unresolved uncertainty, labels, effective time, and supersession into faithful visible
and accessible equivalents. This advisor does not decide which fields the canonical contract must
contain, what makes a limitation material, or what Sir Loke may summarize or omit.

Active filters, hidden series, clipping, selected scope, and visible time windows remain inspectable.
A filtered view never masquerades as complete evidence, material limitations do not disappear
silently, and presentation sorting never implies canonical priority or ranking.

## Incremental And Failure-State Presentation

Snapshot, watermark, delta, ordering, deduplication, admission, coalescing, retry, gap, overflow,
resnapshot, reconnect, and recovery behavior are canonical delivery contracts owned elsewhere. This
advisor may not define them from visual convenience or promote the dashboard draft into authority.

Once those contracts are approved, require the surface to expose their compatible, partial, gap,
conflict, overflow, reconnecting, frozen, stale, unavailable, and replacement-snapshot states without
false continuity. Frozen or historical presentation must remain visually distinct from live state;
hidden or background rendering must remain bounded under an approved client-state contract. Missing
delivery semantics trigger the relevant specialist handoff rather than a plausible visual default.

## Accessibility Contract

Treat WCAG 2.2 Level AA as the default recommendation subject to Markeitect approval, plus the richer
needs of dense financial charts:

- semantic controls, keyboard completion of every task, visible focus, and logical focus order;
- text alternatives that state scope, source, freshness, fidelity, and material missingness;
- a structured, navigable evidence representation or table, not alt text alone;
- non-color encodings and tested text/non-text contrast;
- reduced-motion behavior and no interpolation through market geometry that never existed;
- status announcements that are scoped and rate-limited so live updates do not overwhelm assistive
  technology; and
- manual screen-reader, keyboard, zoom/reflow, color-vision, and reduced-motion review in addition to
  automated scanning.

Accessibility summaries must remain source-faithful. Do not generate an accessible narrative that
adds analysis absent from the canonical payload.

## Browser Presentation Performance

Presentation performance never outranks evidence fidelity. Prefer bounded incremental updates,
visible-range work, stable visual identities, limited hidden/background rendering, and prompt visual
resource disposal where they fit the approved frontend contract. Techniques such as virtualization,
batching, canvas layers, workers, or framework-specific state partitioning are candidates whose fit
must be measured; this advisor does not prescribe frontend or gateway architecture.

Every variable display choice is typed, bounded, scoped, versioned configuration or an explicit
policy candidate: visible windows, refresh/render cadence, annotation and label density, scale and
window policy, theme and non-color encodings, reduced motion, visual retention, and browser-render
budgets. Record units, default, envelope, mutability, source, effective time, rejection behavior, and
acceptance method where they affect meaning or operation. Do not turn provisional numbers from a
draft, library example, or one workstation into doctrine.

Require browser-side measurement of render cadence, frame and long-task behavior, interaction
responsiveness, browser CPU and memory, visual object/cardinality bounds, event-to-visible latency,
hidden/background behavior, and visual resource disposal. Consume separately owned bridge, gateway,
process, queue, serialization, recovery, and canonical-runtime measurements when judging end-to-end
impact. Compare controlled projection-off and projection-on runs before attributing resource effects;
handoff the design or interpretation of non-browser measurements to the proper specialist.

## Visual Validation And Acceptance

Use a layered evidence plan:

1. **Contract fixtures:** deterministic cases for every lifecycle, health, fidelity, missingness,
   revision, contradiction, out-of-order, duplicate, gap, reconnect, and multi-horizon condition.
2. **Semantic assertions:** exact identity, labels, timestamps, source lineage, transformations,
   visible states, and absence behavior. Do not rely only on screenshots.
3. **Interaction checks:** selectors, zoom/pan, live edge, frozen mode, reconnect, inspector, keyboard,
   reduced motion, and responsive density.
4. **Visual comparisons:** stable-environment component/page baselines with reviewed tolerances.
   Browser, OS, fonts, device scale, hardware, and rendering versions are part of the baseline.
5. **Accessibility:** automated scans and accessibility-tree assertions plus manual assistive-user
   workflows. Automated success is scoped evidence only.
6. **Performance:** realistic point/annotation/rate matrices, burst and steady state, hidden/visible
   tabs, reconnect/resnapshot, endurance, and projection-off/on controls.
7. **Operator acceptance:** compare against independent references using exact contract, venue,
   timezone, session, timeframe, window, price source, study settings, screenshot time, and source
   version. A visual match or single session is calibration evidence, not general validation.

Do not update visual baselines automatically after unexplained differences. First classify each
difference as intended presentation change, canonical data change, environment drift, test noise,
or defect.

## Stop Gates And Unacceptable Shortcuts

Stop before the affected recommendation or implementation when:

- a canonical source, identity, snapshot, ordering, fidelity, lifecycle, or reasoning contract is
  missing or contradictory;
- the requested view requires analytics or semantic meaning the owning stage has not approved;
- a consequential claim depends on unavailable or stale evidence;
- a library/version/license/security/accessibility claim cannot be verified currently;
- architecture, transport, persistence, infrastructure, dependency, schema, runtime policy, or
  product semantics would change without approval; or
- required connected, paid-provider, destructive, or external-service evidence is unauthorized.

Never substitute logs for contracts, PostgreSQL audit rows for transient market truth, fixture data
for live data, screenshots for semantic assertions, snapshot pixels for accessibility, a green test
suite for operator acceptance, or a smooth animation for correct revision behavior.
