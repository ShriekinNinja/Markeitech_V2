# Metrics, Entities, Intelligence, and State

> Offline architecture documentation. No current order submission or execution.

Show implemented metrics/state and profile-disabled entity capabilities with their canonical contracts.

- View ID: `view.metrics-entities-intelligence`
- Profile: `profile.v3-es-minimal`
- Manifest: `markeitech-v3-system-dataflow` schema 1
- Checkout evidence: `4a414d0c5ce9b3eead005b674e6ce1997fe966b1`
- Review status: `proposed`

## Components

| ID | Component | Kind | Implementation | Composition | Order | Active profile | Semantic owner | Boundary |
|---|---|---|---|---|---:|---|---|---|
| `actor.evidence-health` | Evidence Health | markeitech_actor | implemented | always | 3 | enabled | `actor.evidence-health` | `boundary.intelligence` |
| `actor.historical-planner` | Historical Evidence Planner | markeitech_actor | implemented | always | 11 | enabled | `actor.historical-planner` | `boundary.intelligence` |
| `actor.market-state-entities` | Market State Entities | markeitech_actor | implemented | conditional | 9 | disabled | `actor.market-state-entities` | `boundary.intelligence` |
| `actor.market-structure-entities` | Market Structure Entities | markeitech_actor | implemented | conditional | 10 | disabled | `actor.market-structure-entities` | `boundary.intelligence` |
| `actor.quote-quality` | Quote Quality Metrics | markeitech_actor | implemented | conditional | 6 | disabled | `actor.quote-quality` | `boundary.intelligence` |
| `actor.session-metrics` | Session Metrics | markeitech_actor | implemented | conditional | 7 | disabled | `actor.session-metrics` | `boundary.intelligence` |
| `actor.session-reference-entities` | Session Reference Entities | markeitech_actor | implemented | conditional | 8 | disabled | `actor.session-reference-entities` | `boundary.intelligence` |
| `actor.session-state` | Session State | markeitech_actor | implemented | always | 2 | enabled | `actor.session-state` | `boundary.intelligence` |
| `actor.visual-debug` | Visual Debug Capture | markeitech_actor | implemented | conditional | 5 | disabled | `actor.visual-debug` | `boundary.intelligence` |
| `actor.watchlist` | Watchlist | markeitech_actor | implemented | always | 12 | enabled | `actor.watchlist` | `boundary.acquisition` |
| `component.canonical-calendar` | Canonical Calendar | engine | implemented | not_composed | not applicable | enabled | `actor.session-state` | `boundary.intelligence` |
| `component.data-engine` | Nautilus Data Engine | engine | implemented | always | not applicable | enabled | `component.data-engine` | `boundary.nautilus` |

## Configuration-gated capabilities

| ID | Owning component | Capability | Implementation | Composition | Active profile | Configuration |
|---|---|---|---|---|---|---|
| `capability.session-metrics.completed-bars` | `actor.session-metrics` | Completed-bar foundation | implemented | conditional | disabled | metrics.session_measurements.enabled |
| `capability.session-metrics.rolling` | `actor.session-metrics` | Rolling measurements | implemented | conditional | disabled | metrics.session_measurements.rolling_measurements.enabled |
| `capability.session-metrics.session-references` | `actor.session-metrics` | Session reference measurements | implemented | conditional | disabled | metrics.session_measurements.session_references.enabled |
| `capability.session-metrics.session-windows` | `actor.session-metrics` | Calendar-relative session windows | implemented | conditional | disabled | metrics.session_measurements.session_windows.enabled |
| `capability.visual-debug.capture` | `actor.visual-debug` | Passive visual debug capture | implemented | conditional | disabled | visual_debug_capture.enabled |

## Flows

| ID | Source | Target | Category | Contract | Transport | Required | Condition | Delivery |
|---|---|---|---|---|---|---|---|---|
| `edge.calendar-request-health` | `actor.evidence-health` | `actor.session-state` | query | `contract.calendar-state-snapshot-request` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-request-metrics` | `actor.session-metrics` | `actor.session-state` | query | `contract.calendar-projection-request` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-request-planner` | `actor.historical-planner` | `actor.session-state` | query | `contract.calendar-projection-request` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-response-health` | `actor.session-state` | `actor.evidence-health` | response | `contract.calendar-state-snapshot-response` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-response-metrics` | `actor.session-state` | `actor.session-metrics` | response | `contract.calendar-projection-response` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-response-planner` | `actor.session-state` | `actor.historical-planner` | response | `contract.calendar-projection-response` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-transition-health` | `actor.session-state` | `actor.evidence-health` | publication | `contract.calendar-transition` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-transition-planner` | `actor.session-state` | `actor.historical-planner` | publication | `contract.calendar-transition` | nautilus_custom_data | yes | always | unknown |
| `edge.completed-bars-session-entities` | `actor.session-metrics` | `actor.session-reference-entities` | publication | `contract.completed-bar` | nautilus_custom_data | no | metrics.entity_analysis.enabled | unknown |
| `edge.completed-bars-visual` | `actor.session-metrics` | `actor.visual-debug` | projection | `contract.completed-bar` | nautilus_custom_data | yes | visual_debug_capture.enabled | unknown |
| `edge.data-engine-metric-bars` | `component.data-engine` | `actor.session-metrics` | native_observation | `contract.native-bar` | nautilus_native_data | yes | always | unknown |
| `edge.health-snapshot` | `actor.evidence-health` | `actor.market-state-entities` | response | `contract.evidence-health-snapshot` | nautilus_signal | no | metrics.entity_analysis.enabled | unknown |
| `edge.health-snapshot-request` | `actor.market-state-entities` | `actor.evidence-health` | query | `contract.evidence-health-snapshot-request` | nautilus_signal | no | metrics.entity_analysis.enabled | unknown |
| `edge.metrics-market-state` | `actor.session-metrics` | `actor.market-state-entities` | publication | `contract.metric-value` | nautilus_custom_data | no | metrics.entity_analysis.enabled | unknown |
| `edge.metrics-market-structure` | `actor.session-metrics` | `actor.market-structure-entities` | publication | `contract.metric-value` | nautilus_custom_data | no | metrics.entity_analysis.enabled | unknown |
| `edge.metrics-visual` | `actor.session-metrics` | `actor.visual-debug` | projection | `contract.metric-value` | nautilus_custom_data | yes | visual_debug_capture.enabled | unknown |
| `edge.recency-profile` | `actor.session-metrics` | `actor.evidence-health` | publication | `contract.evidence-recency-profile` | nautilus_signal | yes | metrics.session_measurements.enabled | unknown |

## Limitations

- Static source and configuration checks cannot prove connected runtime behavior.
- Provider account, entitlement, adapter request mapping, and live delivery remain unknown unless separately measured.
- Generated artifacts are documentation projections and must never be edited or treated as authority.
- Markeitech is read-only and advisory; no current order submission or execution exists.
- Entity actors and quote-quality metrics are implemented but disabled in the named profile.
- Dependencies do not imply causality, confidence, ranking, advice, or trading intent.

## Visual grammar

- Node text carries implementation, composition, and active-profile status; color is supplementary.
- The graphical DOT/SVG/PNG view uses the manifest-selected opaque dark theme; Markdown appearance follows the reviewer's viewer settings.
- Graphical cards, relationships, and nested boundaries use Diagrams C4 primitives with escaped Graphviz-native labels and no external assets.
- Dashed nodes are disabled, historical, rejected, or future, as stated in their text.
- Edge labels state category, required/optional status, and carried contract.
- External projections consume canonical state; they do not create market truth.
- The diagram is generated from the validated TOML manifest and is never an authority itself.
