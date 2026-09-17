# Dashboard History Request and Projection

> Offline architecture documentation. No current order submission or execution.

Candle-count-bounded selected-timeframe native history and detached intraday projection.

- View ID: `view.dashboard-history`
- Profile: `profile.example`
- Manifest: `markeitech-v3-system-dataflow` schema 1
- Checkout evidence: `a382f2e0636cdb3148b451e3e0e8239a684438e5`
- Review status: `proposed`

## Components

| ID | Component | Kind | Implementation | Composition | Order | Active profile | Semantic owner | Boundary |
|---|---|---|---|---|---:|---|---|---|
| `actor.dashboard` | Dashboard | markeitech_actor | implemented | conditional | 11 | enabled | `actor.dashboard` | `boundary.system` |
| `actor.data-acquisition` | Data Acquisition | markeitech_actor | implemented | always | 7 | enabled | `actor.data-acquisition` | `boundary.acquisition` |
| `actor.historical-planner` | Historical Evidence Planner | markeitech_actor | implemented | always | 5 | enabled | `actor.historical-planner` | `boundary.intelligence` |
| `component.data-engine` | Nautilus Data Engine | engine | implemented | always | not applicable | enabled | `component.data-engine` | `boundary.nautilus` |
| `projection.dashboard-ui` | Dashboard UI | projection | implemented | conditional | not applicable | enabled | `actor.dashboard` | `boundary.projections` |
| `provider.interactive-brokers` | Interactive Brokers / TWS / Gateway | provider | external | external | not applicable | not_applicable | `provider.interactive-brokers` | `boundary.providers` |
| `worker.dashboard-server` | Dashboard Server | worker | implemented | conditional | not applicable | enabled | `actor.dashboard` | `boundary.workers` |

## Configuration-gated capabilities

| ID | Owning component | Capability | Implementation | Composition | Active profile | Configuration |
|---|---|---|---|---|---|---|
| `capability.acquisition.historical-bars` | `actor.data-acquisition` | Bounded analytical historical bar requests | implemented | conditional | enabled | historical plus consumer AnalyticalDemand |
| `capability.acquisition.watchlist-last` | `actor.data-acquisition` | Watchlist last-price bar acquisition | implemented | conditional | enabled | watchlist.members[].capabilities contains watchlist_last |

## Flows

| ID | Source | Target | Category | Contract | Transport | Required | Condition | Delivery |
|---|---|---|---|---|---|---|---|---|
| `edge.dashboard-history-demand` | `actor.dashboard` | `actor.historical-planner` | command | `contract.historical-demand` | nautilus_signal | yes | always | unknown |
| `edge.dashboard-history-http` | `projection.dashboard-ui` | `worker.dashboard-server` | command | `contract.dashboard-history-http` | external_http | yes | always | unknown |
| `edge.dashboard-history-lifecycle` | `actor.data-acquisition` | `actor.dashboard` | event | `contract.historical-execution` | nautilus_signal | yes | always | unknown |
| `edge.dashboard-history-mailbox` | `worker.dashboard-server` | `actor.dashboard` | command | `contract.dashboard-history-mailbox` | thread_queue | yes | always | unknown |
| `edge.dashboard-history-page` | `actor.data-acquisition` | `actor.dashboard` | event | `contract.dashboard-history-page` | nautilus_custom_data | yes | always | unknown |
| `edge.dashboard-history-result-http` | `worker.dashboard-server` | `projection.dashboard-ui` | projection | `contract.dashboard-history-result-http` | external_http | yes | always | unknown |
| `edge.dashboard-history-result-mailbox` | `actor.dashboard` | `worker.dashboard-server` | projection | `contract.dashboard-history-result-mailbox` | thread_queue | yes | always | unknown |
| `edge.historical-plan-acquisition` | `actor.historical-planner` | `actor.data-acquisition` | publication | `contract.historical-request-plan` | nautilus_custom_data | yes | always | unknown |
| `edge.historical-provider-response` | `provider.interactive-brokers` | `component.data-engine` | response | `contract.native-bar` | nautilus_native_data | yes | historical.enabled | unknown |
| `edge.native-historical-request` | `actor.data-acquisition` | `component.data-engine` | query | `contract.native-historical-request` | method_call | yes | historical.enabled | at_most_once_attempt |

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
