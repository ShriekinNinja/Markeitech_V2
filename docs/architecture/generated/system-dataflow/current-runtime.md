# Current V3 ES Runtime Topology

> Offline architecture documentation. No current order submission or execution.

Profile-specific implemented and enabled topology for the tracked V3 ES review profile.

- View ID: `view.current-runtime`
- Profile: `profile.v3-es-minimal`
- Manifest: `markeitech-v3-system-dataflow` schema 1
- Checkout evidence: `c6fe2ad89ae2da077d08c55998cc9ff639c5f0ce`
- Review status: `proposed`

## Components

| ID | Component | Kind | Implementation | Composition | Order | Active profile | Semantic owner | Boundary |
|---|---|---|---|---|---:|---|---|---|
| `actor.data-acquisition` | Data Acquisition | markeitech_actor | implemented | always | 12 | enabled | `actor.data-acquisition` | `boundary.acquisition` |
| `actor.evidence-health` | Evidence Health | markeitech_actor | implemented | always | 3 | enabled | `actor.evidence-health` | `boundary.intelligence` |
| `actor.operational-persistence` | Operational Persistence | markeitech_actor | implemented | always | 17 | enabled | `actor.operational-persistence` | `boundary.system` |
| `actor.session-metrics` | Session Metrics | markeitech_actor | implemented | conditional | 7 | enabled | `actor.session-metrics` | `boundary.intelligence` |
| `actor.session-state` | Session State | markeitech_actor | implemented | always | 2 | enabled | `actor.session-state` | `boundary.intelligence` |
| `actor.system-control` | System Control | markeitech_actor | implemented | always | 1 | enabled | `actor.system-control` | `boundary.system` |
| `actor.visual-debug` | Visual Debug Capture | markeitech_actor | implemented | conditional | 5 | enabled | `actor.visual-debug` | `boundary.intelligence` |
| `actor.watchlist` | Watchlist | markeitech_actor | implemented | always | 11 | enabled | `actor.watchlist` | `boundary.acquisition` |
| `component.cache` | Nautilus Cache | engine | implemented | always | not applicable | enabled | `component.cache` | `boundary.nautilus` |
| `component.data-engine` | Nautilus Data Engine | engine | implemented | always | not applicable | enabled | `component.data-engine` | `boundary.nautilus` |
| `component.live-node` | Nautilus LiveNode | framework | implemented | always | not applicable | enabled | `component.live-node` | `boundary.nautilus` |
| `operator.markeitect` | Markeitect / Operator | operator | external | external | not applicable | not_applicable | `operator.markeitect` | `boundary.projections` |
| `projection.visual-files` | Visual Debug Files | projection | external | external | not applicable | not_applicable | `projection.visual-files` | `boundary.projections` |
| `provider.interactive-brokers` | Interactive Brokers / TWS / Gateway | provider | external | external | not applicable | not_applicable | `provider.interactive-brokers` | `boundary.providers` |
| `queue.persistence` | Persistence Admission Queue | queue | implemented | not_composed | not applicable | enabled | `queue.persistence` | `boundary.workers` |
| `store.postgres` | PostgreSQL Operational Audit | data_store | external | external | not applicable | not_applicable | `store.postgres` | `boundary.persistence` |
| `worker.persistence` | Persistence Writer Worker | worker | implemented | not_composed | not applicable | enabled | `worker.persistence` | `boundary.workers` |

## Configuration-gated capabilities

| ID | Owning component | Capability | Implementation | Composition | Active profile | Configuration |
|---|---|---|---|---|---|---|
| `capability.acquisition.historical-bars` | `actor.data-acquisition` | Bounded analytical historical bar requests | implemented | conditional | enabled | historical plus consumer AnalyticalDemand |
| `capability.acquisition.watchlist-last` | `actor.data-acquisition` | Watchlist last-price bar acquisition | implemented | conditional | enabled | watchlist.members[].capabilities contains watchlist_last |
| `capability.session-metrics.completed-bars` | `actor.session-metrics` | Completed-bar foundation | implemented | conditional | enabled | metrics.session_measurements.enabled |
| `capability.session-metrics.rolling` | `actor.session-metrics` | Rolling measurements | implemented | conditional | disabled | metrics.session_measurements.rolling_measurements.enabled |
| `capability.session-metrics.session-references` | `actor.session-metrics` | Session reference measurements | implemented | conditional | disabled | metrics.session_measurements.session_references.enabled |
| `capability.session-metrics.session-windows` | `actor.session-metrics` | Calendar-relative session windows | implemented | conditional | disabled | metrics.session_measurements.session_windows.enabled |
| `capability.visual-debug.capture` | `actor.visual-debug` | Passive visual debug capture | implemented | conditional | enabled | visual_debug_capture.enabled |

## Flows

| ID | Source | Target | Category | Contract | Transport | Required | Condition | Delivery |
|---|---|---|---|---|---|---|---|---|
| `edge.acquisition-status-system` | `actor.data-acquisition` | `actor.system-control` | publication | `contract.acquisition-status` | nautilus_signal | yes | always | unknown |
| `edge.acquisition-status-watchlist` | `actor.data-acquisition` | `actor.watchlist` | response | `contract.acquisition-status` | nautilus_signal | yes | always | unknown |
| `edge.acquisition-stream-health` | `actor.data-acquisition` | `actor.evidence-health` | publication | `contract.acquisition-stream` | nautilus_signal | yes | always | unknown |
| `edge.acquisition-subscribe` | `actor.data-acquisition` | `component.data-engine` | subscription_command | `contract.native-subscription-command` | method_call | yes | watchlist.capabilities.watchlist_last | at_most_once_attempt |
| `edge.analytical-demand` | `actor.session-metrics` | `actor.data-acquisition` | publication | `contract.analytical-demand` | nautilus_signal | yes | always | unknown |
| `edge.completed-bars-visual` | `actor.session-metrics` | `actor.visual-debug` | projection | `contract.completed-bar` | nautilus_custom_data | yes | visual_debug_capture.enabled | unknown |
| `edge.data-engine-live-callback` | `component.data-engine` | `actor.data-acquisition` | callback | `contract.native-bar` | nautilus_callback | yes | always | unknown |
| `edge.data-engine-metric-bars` | `component.data-engine` | `actor.session-metrics` | native_observation | `contract.native-bar` | nautilus_native_data | yes | always | unknown |
| `edge.historical-batch` | `actor.data-acquisition` | `actor.session-metrics` | response | `contract.historical-batch` | nautilus_custom_data | yes | metrics.session_measurements.enabled | unknown |
| `edge.historical-demand` | `actor.session-metrics` | `actor.data-acquisition` | query | `contract.historical-demand` | nautilus_signal | yes | always | unknown |
| `edge.historical-provider-response` | `provider.interactive-brokers` | `component.data-engine` | response | `contract.native-bar` | nautilus_native_data | yes | historical.enabled | unknown |
| `edge.historical-readiness` | `actor.data-acquisition` | `actor.session-metrics` | readiness | `contract.historical-readiness` | nautilus_signal | yes | metrics.session_measurements.enabled | unknown |
| `edge.historical-release` | `actor.session-metrics` | `actor.data-acquisition` | release | `contract.historical-execution` | nautilus_signal | yes | metrics.session_measurements.enabled | unknown |
| `edge.ib-native-bars` | `provider.interactive-brokers` | `component.data-engine` | native_observation | `contract.native-bar` | nautilus_native_data | yes | always | unknown |
| `edge.metrics-visual` | `actor.session-metrics` | `actor.visual-debug` | projection | `contract.metric-value` | nautilus_custom_data | yes | visual_debug_capture.enabled | unknown |
| `edge.native-historical-request` | `actor.data-acquisition` | `component.data-engine` | query | `contract.native-historical-request` | method_call | yes | historical.enabled | at_most_once_attempt |
| `edge.persistence-failure` | `actor.operational-persistence` | `actor.system-control` | failure | `contract.component-failure` | nautilus_signal | yes | always | unknown |
| `edge.persistence-queue` | `actor.operational-persistence` | `queue.persistence` | queue_admission | `contract.operational-event` | thread_queue | yes | always | at_least_once_attempt |
| `edge.persistence-ready-request` | `actor.system-control` | `actor.operational-persistence` | query | `contract.persistence-ready-request` | nautilus_signal | yes | always | unknown |
| `edge.persistence-ready-response` | `actor.operational-persistence` | `actor.system-control` | readiness | `contract.persistence-ready` | nautilus_signal | yes | always | unknown |
| `edge.queue-worker` | `queue.persistence` | `worker.persistence` | queue_admission | `contract.operational-event` | thread_queue | yes | always | at_least_once_attempt |
| `edge.session-state-health` | `actor.session-state` | `actor.evidence-health` | publication | `contract.session-state` | nautilus_signal | yes | always | unknown |
| `edge.session-state-metrics` | `actor.session-state` | `actor.session-metrics` | publication | `contract.session-state` | nautilus_signal | yes | always | unknown |
| `edge.system-health-persistence` | `actor.system-control` | `actor.operational-persistence` | publication | `contract.system-health` | nautilus_signal | yes | always | unknown |
| `edge.visual-files` | `actor.visual-debug` | `projection.visual-files` | projection | `contract.visual-artifact` | filesystem | yes | visual_debug_capture.enabled | at_most_once_attempt |
| `edge.visual-review` | `projection.visual-files` | `operator.markeitect` | projection | `contract.visual-artifact` | filesystem | no | always | at_most_once_attempt |
| `edge.watchlist-demand` | `actor.watchlist` | `actor.data-acquisition` | publication | `contract.watchlist-demand` | nautilus_signal | yes | always | unknown |
| `edge.watchlist-lifecycle-health` | `actor.watchlist` | `actor.evidence-health` | publication | `contract.watchlist-lifecycle` | nautilus_signal | yes | always | unknown |
| `edge.watchlist-membership-session` | `actor.watchlist` | `actor.session-state` | publication | `contract.watchlist-membership` | nautilus_signal | yes | always | unknown |
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
- Dashed nodes are disabled, historical, rejected, or future, as stated in their text.
- Edge labels state category, required/optional status, and carried contract.
- External projections consume canonical state; they do not create market truth.
- The diagram is generated from the validated TOML manifest and is never an authority itself.
