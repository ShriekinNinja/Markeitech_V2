# Complete Component and Capability Inventory

> Offline architecture documentation. No current order submission or execution.

Show implemented, conditional, disabled, external, and future components without implying runtime flow.

- View ID: `view.complete-inventory`
- Profile: `profile.v3-es-minimal`
- Manifest: `markeitech-v3-system-dataflow` schema 1
- Checkout evidence: `5b00af3e4e61b8b1f32aa5680b267f9f7904814d`
- Review status: `proposed`

## Components

| ID | Component | Kind | Implementation | Composition | Order | Active profile | Semantic owner | Boundary |
|---|---|---|---|---|---:|---|---|---|
| `actor.data-acquisition` | Data Acquisition | markeitech_actor | implemented | always | 13 | enabled | `actor.data-acquisition` | `boundary.acquisition` |
| `actor.discord-health` | Discord Health Projection | markeitech_actor | implemented | conditional | 4 | disabled | `actor.discord-health` | `boundary.system` |
| `actor.evidence-health` | Evidence Health | markeitech_actor | implemented | always | 3 | enabled | `actor.evidence-health` | `boundary.intelligence` |
| `actor.historical-planner` | Historical Evidence Planner | markeitech_actor | implemented | always | 11 | enabled | `actor.historical-planner` | `boundary.intelligence` |
| `actor.historical-probe` | Historical Dependency Probe | markeitech_actor | implemented | conditional | 14 | disabled | `actor.historical-probe` | `boundary.acquisition` |
| `actor.market-state-entities` | Market State Entities | markeitech_actor | implemented | conditional | 9 | disabled | `actor.market-state-entities` | `boundary.intelligence` |
| `actor.market-structure-entities` | Market Structure Entities | markeitech_actor | implemented | conditional | 10 | disabled | `actor.market-structure-entities` | `boundary.intelligence` |
| `actor.native-consumer-probe` | Native Consumer Probe | markeitech_actor | implemented | conditional | 15 | disabled | `actor.native-consumer-probe` | `boundary.system` |
| `actor.operational-persistence` | Operational Persistence | markeitech_actor | implemented | always | 18 | enabled | `actor.operational-persistence` | `boundary.system` |
| `actor.quote-quality` | Quote Quality Metrics | markeitech_actor | implemented | conditional | 6 | disabled | `actor.quote-quality` | `boundary.intelligence` |
| `actor.runtime-resource-health` | Runtime Resource Health | markeitech_actor | implemented | conditional | 17 | disabled | `actor.runtime-resource-health` | `boundary.system` |
| `actor.runtime-resources` | Runtime Resources | markeitech_actor | implemented | conditional | 16 | disabled | `actor.runtime-resources` | `boundary.system` |
| `actor.session-metrics` | Session Metrics | markeitech_actor | implemented | conditional | 7 | disabled | `actor.session-metrics` | `boundary.intelligence` |
| `actor.session-reference-entities` | Session Reference Entities | markeitech_actor | implemented | conditional | 8 | disabled | `actor.session-reference-entities` | `boundary.intelligence` |
| `actor.session-state` | Session State | markeitech_actor | implemented | always | 2 | enabled | `actor.session-state` | `boundary.intelligence` |
| `actor.system-control` | System Control | markeitech_actor | implemented | always | 1 | enabled | `actor.system-control` | `boundary.system` |
| `actor.visual-debug` | Visual Debug Capture | markeitech_actor | implemented | conditional | 5 | disabled | `actor.visual-debug` | `boundary.intelligence` |
| `actor.watchlist` | Watchlist | markeitech_actor | implemented | always | 12 | enabled | `actor.watchlist` | `boundary.acquisition` |
| `component.cache` | Nautilus Cache | engine | implemented | always | not applicable | enabled | `component.cache` | `boundary.nautilus` |
| `component.canonical-calendar` | Canonical Calendar | engine | implemented | not_composed | not applicable | enabled | `actor.session-state` | `boundary.intelligence` |
| `component.data-engine` | Nautilus Data Engine | engine | implemented | always | not applicable | enabled | `component.data-engine` | `boundary.nautilus` |
| `component.live-node` | Nautilus LiveNode | framework | implemented | always | not applicable | enabled | `component.live-node` | `boundary.nautilus` |
| `future.controlled-execution` | Future Controlled Execution Boundary | future_component | future | not_composed | not applicable | not_applicable | `future.controlled-execution` | `boundary.future` |
| `future.opportunities` | Plural Opportunities | future_component | future | not_composed | not applicable | not_applicable | `future.opportunities` | `boundary.future` |
| `future.semantic-events` | Semantic Events | future_component | future | not_composed | not applicable | not_applicable | `future.semantic-events` | `boundary.future` |
| `future.sir-loke` | Sir Loke Advisory Agent | future_component | future | not_composed | not applicable | not_applicable | `future.sir-loke` | `boundary.future` |
| `operator.markeitect` | Markeitect / Operator | operator | external | external | not applicable | not_applicable | `operator.markeitect` | `boundary.projections` |
| `projection.discord` | Discord | projection | external | external | not applicable | not_applicable | `projection.discord` | `boundary.projections` |
| `projection.visual-files` | Visual Debug Files | projection | external | external | not applicable | not_applicable | `projection.visual-files` | `boundary.projections` |
| `provider.interactive-brokers` | Interactive Brokers / TWS / Gateway | provider | external | external | not applicable | not_applicable | `provider.interactive-brokers` | `boundary.providers` |
| `queue.discord` | Discord Delivery Queue | queue | implemented | not_composed | not applicable | disabled | `queue.discord` | `boundary.workers` |
| `queue.persistence` | Persistence Admission Queue | queue | implemented | not_composed | not applicable | enabled | `queue.persistence` | `boundary.workers` |
| `store.postgres` | PostgreSQL Operational Audit | data_store | external | external | not applicable | not_applicable | `store.postgres` | `boundary.persistence` |
| `worker.discord` | Discord Delivery Worker | worker | implemented | not_composed | not applicable | disabled | `worker.discord` | `boundary.workers` |
| `worker.persistence` | Persistence Writer Worker | worker | implemented | not_composed | not applicable | enabled | `worker.persistence` | `boundary.workers` |

## Configuration-gated capabilities

| ID | Owning component | Capability | Implementation | Composition | Active profile | Configuration |
|---|---|---|---|---|---|---|
| `capability.acquisition.historical-bars` | `actor.data-acquisition` | Bounded analytical historical bar requests | implemented | conditional | enabled | historical plus consumer AnalyticalDemand |
| `capability.acquisition.watchlist-last` | `actor.data-acquisition` | Watchlist last-price bar acquisition | implemented | conditional | enabled | watchlist.members[].capabilities contains watchlist_last |
| `capability.discord.notifications` | `actor.discord-health` | Queued Discord health notifications | implemented | conditional | disabled | discord.enabled |
| `capability.runtime-resources.health` | `actor.runtime-resource-health` | Runtime resource health classification | implemented | conditional | disabled | runtime_resources.enabled and runtime_resources.health.enabled |
| `capability.runtime-resources.telemetry` | `actor.runtime-resources` | Runtime resource telemetry | implemented | conditional | disabled | runtime_resources.enabled |
| `capability.session-metrics.completed-bars` | `actor.session-metrics` | Completed-bar foundation | implemented | conditional | enabled | metrics.session_measurements.enabled |
| `capability.session-metrics.rolling` | `actor.session-metrics` | Rolling measurements | implemented | conditional | disabled | metrics.session_measurements.rolling_measurements.enabled |
| `capability.session-metrics.session-references` | `actor.session-metrics` | Session reference measurements | implemented | conditional | disabled | metrics.session_measurements.session_references.enabled |
| `capability.session-metrics.session-windows` | `actor.session-metrics` | Calendar-relative session windows | implemented | conditional | disabled | metrics.session_measurements.session_windows.enabled |
| `capability.visual-debug.capture` | `actor.visual-debug` | Passive visual debug capture | implemented | conditional | enabled | visual_debug_capture.enabled |

## Historical removed or rejected identities

| ID | Former component | Disposition | Former boundary | Removed at commit |
|---|---|---|---|---|
| `tombstone.direct-historical-demand-edge` | Direct Session Metrics to Data Acquisition historical demand | removed | `boundary.acquisition` | `b09e7ddf75b730f23aefa4c263d64b5dc3961979` |
| `tombstone.historical-release-edge` | Session Metrics historical execution release | removed | `boundary.acquisition` | `b09e7ddf75b730f23aefa4c263d64b5dc3961979` |
| `tombstone.legacy-session-state-contract` | Legacy SessionStateEvent signal | removed | `boundary.intelligence` | `b09e7ddf75b730f23aefa4c263d64b5dc3961979` |
| `tombstone.live-evidence-review-actor` | Live Evidence Review Actor | rejected | `boundary.historical` | `c6fe2ad89ae2da077d08c55998cc9ff639c5f0ce` |
| `tombstone.visual-acceptance-actor` | Visual Acceptance Actor | rejected | `boundary.historical` | `c6fe2ad89ae2da077d08c55998cc9ff639c5f0ce` |

## Flows

| ID | Source | Target | Category | Contract | Transport | Required | Condition | Delivery |
|---|---|---|---|---|---|---|---|---|

## Limitations

- Static source and configuration checks cannot prove connected runtime behavior.
- Provider account, entitlement, adapter request mapping, and live delivery remain unknown unless separately measured.
- Generated artifacts are documentation projections and must never be edited or treated as authority.
- Markeitech is read-only and advisory; no current order submission or execution exists.
- Removed and rejected implementation identities are represented as tombstones in the manifest and companion record, not as active nodes.
- Configuration-gated subcapabilities are listed in the accessible Markdown companion under their owning components rather than duplicated as visual nodes.
- Inventory adjacency and clustering do not imply data flow.

## Visual grammar

- Node text carries implementation, composition, and active-profile status; color is supplementary.
- The graphical DOT/SVG/PNG view uses the manifest-selected opaque dark theme; Markdown appearance follows the reviewer's viewer settings.
- Graphical cards, relationships, and nested boundaries use Diagrams C4 primitives with escaped Graphviz-native labels and no external assets.
- Dashed nodes are disabled, historical, rejected, or future, as stated in their text.
- Edge labels state category, required/optional status, and carried contract.
- External projections consume canonical state; they do not create market truth.
- The diagram is generated from the validated TOML manifest and is never an authority itself.
