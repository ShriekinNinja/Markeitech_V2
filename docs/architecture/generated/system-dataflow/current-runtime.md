# Current V3 ES Runtime Topology

> Offline architecture documentation. No current order submission or execution.

Profile-specific implemented and enabled topology for the tracked V3 ES review profile.

- View ID: `view.current-runtime`
- Profile: `profile.v3-es-minimal`
- Manifest: `markeitech-v3-system-dataflow` schema 1
- Checkout evidence: `b2c5bf41d00e43dea47369e569cd4f326ea758af`
- Review status: `proposed`

## Components

| ID | Component | Kind | Implementation | Composition | Order | Active profile | Semantic owner | Boundary |
|---|---|---|---|---|---:|---|---|---|
| `actor.current-state-historical-probe` | Current-State Historical Demand Probe | markeitech_actor | implemented | conditional | 14 | enabled | `none_current` | `boundary.acquisition` |
| `actor.data-acquisition` | Data Acquisition | markeitech_actor | implemented | always | 13 | enabled | `actor.data-acquisition` | `boundary.acquisition` |
| `actor.evidence-health` | Evidence Health | markeitech_actor | implemented | always | 3 | enabled | `actor.evidence-health` | `boundary.intelligence` |
| `actor.historical-planner` | Historical Evidence Planner | markeitech_actor | implemented | always | 11 | enabled | `actor.historical-planner` | `boundary.intelligence` |
| `actor.operational-persistence` | Operational Persistence | markeitech_actor | implemented | always | 19 | enabled | `actor.operational-persistence` | `boundary.system` |
| `actor.session-state` | Session State | markeitech_actor | implemented | always | 2 | enabled | `actor.session-state` | `boundary.intelligence` |
| `actor.system-control` | System Control | markeitech_actor | implemented | always | 1 | enabled | `actor.system-control` | `boundary.system` |
| `actor.watchlist` | Watchlist | markeitech_actor | implemented | always | 12 | enabled | `actor.watchlist` | `boundary.acquisition` |
| `component.cache` | Nautilus Cache | engine | implemented | always | not applicable | enabled | `component.cache` | `boundary.nautilus` |
| `component.canonical-calendar` | Canonical Calendar | engine | implemented | not_composed | not applicable | enabled | `actor.session-state` | `boundary.intelligence` |
| `component.data-engine` | Nautilus Data Engine | engine | implemented | always | not applicable | enabled | `component.data-engine` | `boundary.nautilus` |
| `component.live-node` | Nautilus LiveNode | framework | implemented | always | not applicable | enabled | `component.live-node` | `boundary.nautilus` |
| `operator.markeitect` | Markeitect / Operator | operator | external | external | not applicable | not_applicable | `operator.markeitect` | `boundary.projections` |
| `provider.interactive-brokers` | Interactive Brokers / TWS / Gateway | provider | external | external | not applicable | not_applicable | `provider.interactive-brokers` | `boundary.providers` |
| `queue.persistence` | Persistence Admission Queue | queue | implemented | not_composed | not applicable | enabled | `queue.persistence` | `boundary.workers` |
| `store.postgres` | PostgreSQL Operational Audit | data_store | external | external | not applicable | not_applicable | `store.postgres` | `boundary.persistence` |
| `worker.persistence` | Persistence Writer Worker | worker | implemented | not_composed | not applicable | enabled | `worker.persistence` | `boundary.workers` |

## Configuration-gated capabilities

| ID | Owning component | Capability | Implementation | Composition | Active profile | Configuration |
|---|---|---|---|---|---|---|
| `capability.acquisition.historical-bars` | `actor.data-acquisition` | Bounded analytical historical bar requests | implemented | conditional | enabled | historical plus consumer AnalyticalDemand |
| `capability.acquisition.watchlist-last` | `actor.data-acquisition` | Watchlist last-price bar acquisition | implemented | conditional | enabled | watchlist.members[].capabilities contains watchlist_last |

## Flows

| ID | Source | Target | Category | Contract | Transport | Required | Condition | Delivery |
|---|---|---|---|---|---|---|---|---|
| `edge.acquisition-status-system` | `actor.data-acquisition` | `actor.system-control` | publication | `contract.acquisition-status` | nautilus_signal | yes | always | unknown |
| `edge.acquisition-status-watchlist` | `actor.data-acquisition` | `actor.watchlist` | response | `contract.acquisition-status` | nautilus_signal | yes | always | unknown |
| `edge.acquisition-stream-health` | `actor.data-acquisition` | `actor.evidence-health` | publication | `contract.acquisition-stream` | nautilus_signal | yes | always | unknown |
| `edge.acquisition-subscribe` | `actor.data-acquisition` | `component.data-engine` | subscription_command | `contract.native-subscription-command` | method_call | yes | watchlist.capabilities.watchlist_last | at_most_once_attempt |
| `edge.calendar-request-health` | `actor.evidence-health` | `actor.session-state` | query | `contract.calendar-state-snapshot-request` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-request-planner` | `actor.historical-planner` | `actor.session-state` | query | `contract.calendar-projection-request` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-response-health` | `actor.session-state` | `actor.evidence-health` | response | `contract.calendar-state-snapshot-response` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-response-planner` | `actor.session-state` | `actor.historical-planner` | response | `contract.calendar-projection-response` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-state-request-planner` | `actor.historical-planner` | `actor.session-state` | query | `contract.calendar-state-snapshot-request` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-state-request-probe` | `actor.current-state-historical-probe` | `actor.session-state` | query | `contract.calendar-state-snapshot-request` | nautilus_custom_data | yes | historical.probe.enabled | unknown |
| `edge.calendar-state-response-planner` | `actor.session-state` | `actor.historical-planner` | response | `contract.calendar-state-snapshot-response` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-state-response-probe` | `actor.session-state` | `actor.current-state-historical-probe` | response | `contract.calendar-state-snapshot-response` | nautilus_custom_data | yes | historical.probe.enabled | unknown |
| `edge.calendar-transition-health` | `actor.session-state` | `actor.evidence-health` | publication | `contract.calendar-transition` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-transition-persistence` | `actor.session-state` | `actor.operational-persistence` | persistence | `contract.calendar-transition` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-transition-planner` | `actor.session-state` | `actor.historical-planner` | publication | `contract.calendar-transition` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-transition-probe` | `actor.session-state` | `actor.current-state-historical-probe` | publication | `contract.calendar-transition` | nautilus_custom_data | yes | historical.probe.enabled | unknown |
| `edge.current-state-probe-historical-demand` | `actor.current-state-historical-probe` | `actor.historical-planner` | query | `contract.historical-demand` | nautilus_signal | yes | historical.probe.enabled | unknown |
| `edge.data-engine-live-callback` | `component.data-engine` | `actor.data-acquisition` | callback | `contract.native-bar` | nautilus_callback | yes | always | unknown |
| `edge.historical-batch-current-state-probe` | `actor.data-acquisition` | `actor.current-state-historical-probe` | response | `contract.historical-batch` | nautilus_custom_data | yes | historical.probe.enabled | unknown |
| `edge.historical-plan-acquisition` | `actor.historical-planner` | `actor.data-acquisition` | publication | `contract.historical-request-plan` | nautilus_custom_data | yes | always | unknown |
| `edge.historical-plan-current-state-probe` | `actor.historical-planner` | `actor.current-state-historical-probe` | response | `contract.historical-request-plan` | nautilus_custom_data | yes | historical.probe.enabled | unknown |
| `edge.historical-provider-response` | `provider.interactive-brokers` | `component.data-engine` | response | `contract.native-bar` | nautilus_native_data | yes | historical.enabled | unknown |
| `edge.historical-readiness-current-state-probe` | `actor.data-acquisition` | `actor.current-state-historical-probe` | readiness | `contract.historical-readiness` | nautilus_signal | yes | historical.probe.enabled | unknown |
| `edge.ib-native-bars` | `provider.interactive-brokers` | `component.data-engine` | native_observation | `contract.native-bar` | nautilus_native_data | yes | always | unknown |
| `edge.native-historical-request` | `actor.data-acquisition` | `component.data-engine` | query | `contract.native-historical-request` | method_call | yes | historical.enabled | at_most_once_attempt |
| `edge.persistence-failure` | `actor.operational-persistence` | `actor.system-control` | failure | `contract.component-failure` | nautilus_signal | yes | always | unknown |
| `edge.persistence-queue` | `actor.operational-persistence` | `queue.persistence` | queue_admission | `contract.operational-event` | thread_queue | yes | always | at_least_once_attempt |
| `edge.persistence-ready-request` | `actor.system-control` | `actor.operational-persistence` | query | `contract.persistence-ready-request` | nautilus_signal | yes | always | unknown |
| `edge.persistence-ready-response` | `actor.operational-persistence` | `actor.system-control` | readiness | `contract.persistence-ready` | nautilus_signal | yes | always | unknown |
| `edge.queue-worker` | `queue.persistence` | `worker.persistence` | queue_admission | `contract.operational-event` | thread_queue | yes | always | at_least_once_attempt |
| `edge.system-health-persistence` | `actor.system-control` | `actor.operational-persistence` | publication | `contract.system-health` | nautilus_signal | yes | always | unknown |
| `edge.watchlist-demand` | `actor.watchlist` | `actor.data-acquisition` | publication | `contract.watchlist-demand` | nautilus_signal | yes | always | unknown |
| `edge.watchlist-status-request` | `actor.watchlist` | `actor.data-acquisition` | query | `contract.acquisition-status-request` | nautilus_signal | yes | always | unknown |
| `edge.worker-postgres` | `worker.persistence` | `store.postgres` | persistence | `contract.operational-event` | postgres_write | yes | always | at_least_once_attempt |
| `edge.worker-result` | `worker.persistence` | `actor.operational-persistence` | worker_result | `contract.persistence-result` | thread_queue | yes | always | at_least_once_attempt |

## Limitations

- Static source and configuration checks cannot prove connected runtime behavior.
- Provider account, entitlement, adapter request mapping, and live delivery remain unknown unless separately measured.
- Generated artifacts are documentation projections and must never be edited or treated as authority.
- Markeitech is read-only and advisory; no current order submission or execution exists.
- Excludes profile-disabled actors and future/removed behavior.
- A visually connected provider boundary does not prove a current live connection or entitlement.

## Visual grammar

- Node text carries implementation, composition, and active-profile status; color is supplementary.
- The graphical DOT/SVG/PNG view uses the manifest-selected opaque dark theme; Markdown appearance follows the reviewer's viewer settings.
- Graphical cards, relationships, and nested boundaries use Diagrams C4 primitives with escaped Graphviz-native labels and no external assets.
- Dashed nodes are disabled, historical, rejected, or future, as stated in their text.
- Edge labels state category, required/optional status, and carried contract.
- External projections consume canonical state; they do not create market truth.
- The diagram is generated from the validated TOML manifest and is never an authority itself.
