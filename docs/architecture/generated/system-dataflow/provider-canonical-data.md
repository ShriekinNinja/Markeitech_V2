# Provider to Canonical Data Flow

> Offline architecture documentation. No current order submission or execution.

Show provider capability, native Nautilus boundary, acquisition ownership, historical/live convergence, metrics input, and evidence health.

- View ID: `view.provider-canonical-data`
- Profile: `profile.v3-es-minimal`
- Manifest: `markeitech-v3-system-dataflow` schema 1
- Checkout evidence: `5b00af3e4e61b8b1f32aa5680b267f9f7904814d`
- Review status: `proposed`

## Components

| ID | Component | Kind | Implementation | Composition | Order | Active profile | Semantic owner | Boundary |
|---|---|---|---|---|---:|---|---|---|
| `actor.data-acquisition` | Data Acquisition | markeitech_actor | implemented | always | 13 | enabled | `actor.data-acquisition` | `boundary.acquisition` |
| `actor.evidence-health` | Evidence Health | markeitech_actor | implemented | always | 3 | enabled | `actor.evidence-health` | `boundary.intelligence` |
| `actor.historical-planner` | Historical Evidence Planner | markeitech_actor | implemented | always | 11 | enabled | `actor.historical-planner` | `boundary.intelligence` |
| `actor.session-metrics` | Session Metrics | markeitech_actor | implemented | conditional | 7 | enabled | `actor.session-metrics` | `boundary.intelligence` |
| `actor.session-state` | Session State | markeitech_actor | implemented | always | 2 | enabled | `actor.session-state` | `boundary.intelligence` |
| `actor.watchlist` | Watchlist | markeitech_actor | implemented | always | 12 | enabled | `actor.watchlist` | `boundary.acquisition` |
| `component.cache` | Nautilus Cache | engine | implemented | always | not applicable | enabled | `component.cache` | `boundary.nautilus` |
| `component.canonical-calendar` | Canonical Calendar | engine | implemented | not_composed | not applicable | enabled | `actor.session-state` | `boundary.intelligence` |
| `component.data-engine` | Nautilus Data Engine | engine | implemented | always | not applicable | enabled | `component.data-engine` | `boundary.nautilus` |
| `provider.interactive-brokers` | Interactive Brokers / TWS / Gateway | provider | external | external | not applicable | not_applicable | `provider.interactive-brokers` | `boundary.providers` |

## Configuration-gated capabilities

| ID | Owning component | Capability | Implementation | Composition | Active profile | Configuration |
|---|---|---|---|---|---|---|
| `capability.acquisition.historical-bars` | `actor.data-acquisition` | Bounded analytical historical bar requests | implemented | conditional | enabled | historical plus consumer AnalyticalDemand |
| `capability.acquisition.watchlist-last` | `actor.data-acquisition` | Watchlist last-price bar acquisition | implemented | conditional | enabled | watchlist.members[].capabilities contains watchlist_last |
| `capability.session-metrics.completed-bars` | `actor.session-metrics` | Completed-bar foundation | implemented | conditional | enabled | metrics.session_measurements.enabled |
| `capability.session-metrics.rolling` | `actor.session-metrics` | Rolling measurements | implemented | conditional | disabled | metrics.session_measurements.rolling_measurements.enabled |
| `capability.session-metrics.session-references` | `actor.session-metrics` | Session reference measurements | implemented | conditional | disabled | metrics.session_measurements.session_references.enabled |
| `capability.session-metrics.session-windows` | `actor.session-metrics` | Calendar-relative session windows | implemented | conditional | disabled | metrics.session_measurements.session_windows.enabled |

## Flows

| ID | Source | Target | Category | Contract | Transport | Required | Condition | Delivery |
|---|---|---|---|---|---|---|---|---|
| `edge.acquisition-status-watchlist` | `actor.data-acquisition` | `actor.watchlist` | response | `contract.acquisition-status` | nautilus_signal | yes | always | unknown |
| `edge.acquisition-stream-health` | `actor.data-acquisition` | `actor.evidence-health` | publication | `contract.acquisition-stream` | nautilus_signal | yes | always | unknown |
| `edge.acquisition-subscribe` | `actor.data-acquisition` | `component.data-engine` | subscription_command | `contract.native-subscription-command` | method_call | yes | watchlist.capabilities.watchlist_last | at_most_once_attempt |
| `edge.calendar-request-health` | `actor.evidence-health` | `actor.session-state` | query | `contract.calendar-projection-request` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-request-metrics` | `actor.session-metrics` | `actor.session-state` | query | `contract.calendar-projection-request` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-request-planner` | `actor.historical-planner` | `actor.session-state` | query | `contract.calendar-projection-request` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-response-health` | `actor.session-state` | `actor.evidence-health` | response | `contract.calendar-projection-response` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-response-metrics` | `actor.session-state` | `actor.session-metrics` | response | `contract.calendar-projection-response` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-response-planner` | `actor.session-state` | `actor.historical-planner` | response | `contract.calendar-projection-response` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-transition-health` | `actor.session-state` | `actor.evidence-health` | publication | `contract.calendar-transition` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-transition-metrics` | `actor.session-state` | `actor.session-metrics` | publication | `contract.calendar-transition` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-transition-planner` | `actor.session-state` | `actor.historical-planner` | publication | `contract.calendar-transition` | nautilus_custom_data | yes | always | unknown |
| `edge.data-engine-live-callback` | `component.data-engine` | `actor.data-acquisition` | callback | `contract.native-bar` | nautilus_callback | yes | always | unknown |
| `edge.data-engine-metric-bars` | `component.data-engine` | `actor.session-metrics` | native_observation | `contract.native-bar` | nautilus_native_data | yes | always | unknown |
| `edge.historical-batch` | `actor.data-acquisition` | `actor.session-metrics` | response | `contract.historical-batch` | nautilus_custom_data | yes | metrics.session_measurements.enabled | unknown |
| `edge.historical-demand-planner` | `actor.session-metrics` | `actor.historical-planner` | query | `contract.historical-demand` | nautilus_signal | yes | always | unknown |
| `edge.historical-plan-acquisition` | `actor.historical-planner` | `actor.data-acquisition` | publication | `contract.historical-request-plan` | nautilus_custom_data | yes | always | unknown |
| `edge.historical-provider-response` | `provider.interactive-brokers` | `component.data-engine` | response | `contract.native-bar` | nautilus_native_data | yes | historical.enabled | unknown |
| `edge.historical-readiness` | `actor.data-acquisition` | `actor.session-metrics` | readiness | `contract.historical-readiness` | nautilus_signal | yes | metrics.session_measurements.enabled | unknown |
| `edge.ib-native-bars` | `provider.interactive-brokers` | `component.data-engine` | native_observation | `contract.native-bar` | nautilus_native_data | yes | always | unknown |
| `edge.native-historical-request` | `actor.data-acquisition` | `component.data-engine` | query | `contract.native-historical-request` | method_call | yes | historical.enabled | at_most_once_attempt |
| `edge.watchlist-demand` | `actor.watchlist` | `actor.data-acquisition` | publication | `contract.watchlist-demand` | nautilus_signal | yes | always | unknown |
| `edge.watchlist-status-request` | `actor.watchlist` | `actor.data-acquisition` | query | `contract.acquisition-status-request` | nautilus_signal | yes | always | unknown |

## Limitations

- Static source and configuration checks cannot prove connected runtime behavior.
- Provider account, entitlement, adapter request mapping, and live delivery remain unknown unless separately measured.
- Generated artifacts are documentation projections and must never be edited or treated as authority.
- Markeitech is read-only and advisory; no current order submission or execution exists.
- Exact IB request methods, callbacks, qualification, entitlement, delivery mode, request IDs, and cancellation are unknown.
- Native subscription command issuance is not provider acknowledgement.
- Historical and live observations are distinct lineage sources; general equality and gap-free delivery are not claimed.

## Visual grammar

- Node text carries implementation, composition, and active-profile status; color is supplementary.
- The graphical DOT/SVG/PNG view uses the manifest-selected opaque dark theme; Markdown appearance follows the reviewer's viewer settings.
- Graphical cards, relationships, and nested boundaries use Diagrams C4 primitives with escaped Graphviz-native labels and no external assets.
- Dashed nodes are disabled, historical, rejected, or future, as stated in their text.
- Edge labels state category, required/optional status, and carried contract.
- External projections consume canonical state; they do not create market truth.
- The diagram is generated from the validated TOML manifest and is never an authority itself.
