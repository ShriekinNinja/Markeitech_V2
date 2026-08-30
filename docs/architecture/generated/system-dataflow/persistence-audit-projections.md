# Persistence, Operational Audit, and External Projections

> Offline architecture documentation. No current order submission or execution.

Separate bounded operational persistence from optional notifications and diagnostic projections.

- View ID: `view.persistence-audit-projections`
- Profile: `profile.v3-es-minimal`
- Manifest: `markeitech-v3-system-dataflow` schema 1
- Checkout evidence: `c6fe2ad89ae2da077d08c55998cc9ff639c5f0ce`
- Review status: `proposed`

## Components

| ID | Component | Kind | Implementation | Composition | Order | Active profile | Semantic owner | Boundary |
|---|---|---|---|---|---:|---|---|---|
| `actor.discord-health` | Discord Health Projection | markeitech_actor | implemented | conditional | 4 | disabled | `actor.discord-health` | `boundary.system` |
| `actor.operational-persistence` | Operational Persistence | markeitech_actor | implemented | always | 17 | enabled | `actor.operational-persistence` | `boundary.system` |
| `actor.system-control` | System Control | markeitech_actor | implemented | always | 1 | enabled | `actor.system-control` | `boundary.system` |
| `actor.visual-debug` | Visual Debug Capture | markeitech_actor | implemented | conditional | 5 | enabled | `actor.visual-debug` | `boundary.intelligence` |
| `operator.markeitect` | Markeitect / Operator | operator | external | external | not applicable | not_applicable | `operator.markeitect` | `boundary.projections` |
| `projection.discord` | Discord | projection | external | external | not applicable | not_applicable | `projection.discord` | `boundary.projections` |
| `projection.visual-files` | Visual Debug Files | projection | external | external | not applicable | not_applicable | `projection.visual-files` | `boundary.projections` |
| `queue.discord` | Discord Delivery Queue | queue | implemented | not_composed | not applicable | disabled | `queue.discord` | `boundary.workers` |
| `queue.persistence` | Persistence Admission Queue | queue | implemented | not_composed | not applicable | enabled | `queue.persistence` | `boundary.workers` |
| `store.postgres` | PostgreSQL Operational Audit | data_store | external | external | not applicable | not_applicable | `store.postgres` | `boundary.persistence` |
| `worker.discord` | Discord Delivery Worker | worker | implemented | not_composed | not applicable | disabled | `worker.discord` | `boundary.workers` |
| `worker.persistence` | Persistence Writer Worker | worker | implemented | not_composed | not applicable | enabled | `worker.persistence` | `boundary.workers` |

## Configuration-gated capabilities

| ID | Owning component | Capability | Implementation | Composition | Active profile | Configuration |
|---|---|---|---|---|---|---|
| `capability.discord.notifications` | `actor.discord-health` | Queued Discord health notifications | implemented | conditional | disabled | discord.enabled |
| `capability.visual-debug.capture` | `actor.visual-debug` | Passive visual debug capture | implemented | conditional | enabled | visual_debug_capture.enabled |

## Flows

| ID | Source | Target | Category | Contract | Transport | Required | Condition | Delivery |
|---|---|---|---|---|---|---|---|---|
| `edge.discord-external` | `worker.discord` | `projection.discord` | notification | `contract.discord-notification` | external_http | no | discord.enabled | at_least_once_attempt |
| `edge.discord-queue` | `actor.discord-health` | `queue.discord` | queue_admission | `contract.discord-notification` | thread_queue | no | discord.enabled | at_least_once_attempt |
| `edge.discord-worker` | `queue.discord` | `worker.discord` | queue_admission | `contract.discord-notification` | thread_queue | no | discord.enabled | at_least_once_attempt |
| `edge.persistence-failure` | `actor.operational-persistence` | `actor.system-control` | failure | `contract.component-failure` | nautilus_signal | yes | always | unknown |
| `edge.persistence-queue` | `actor.operational-persistence` | `queue.persistence` | queue_admission | `contract.operational-event` | thread_queue | yes | always | at_least_once_attempt |
| `edge.persistence-ready-request` | `actor.system-control` | `actor.operational-persistence` | query | `contract.persistence-ready-request` | nautilus_signal | yes | always | unknown |
| `edge.persistence-ready-response` | `actor.operational-persistence` | `actor.system-control` | readiness | `contract.persistence-ready` | nautilus_signal | yes | always | unknown |
| `edge.queue-worker` | `queue.persistence` | `worker.persistence` | queue_admission | `contract.operational-event` | thread_queue | yes | always | at_least_once_attempt |
| `edge.system-health-discord` | `actor.system-control` | `actor.discord-health` | notification | `contract.system-health` | nautilus_signal | no | discord.enabled | unknown |
| `edge.system-health-persistence` | `actor.system-control` | `actor.operational-persistence` | publication | `contract.system-health` | nautilus_signal | yes | always | unknown |
| `edge.visual-files` | `actor.visual-debug` | `projection.visual-files` | projection | `contract.visual-artifact` | filesystem | yes | visual_debug_capture.enabled | at_most_once_attempt |
| `edge.visual-review` | `projection.visual-files` | `operator.markeitect` | projection | `contract.visual-artifact` | filesystem | no | always | at_most_once_attempt |
| `edge.worker-postgres` | `worker.persistence` | `store.postgres` | persistence | `contract.operational-event` | postgres_write | yes | always | at_least_once_attempt |
| `edge.worker-result` | `worker.persistence` | `actor.operational-persistence` | worker_result | `contract.persistence-result` | thread_queue | yes | always | at_least_once_attempt |

## Limitations

- Static source and configuration checks cannot prove connected runtime behavior.
- Provider account, entitlement, adapter request mapping, and live delivery remain unknown unless separately measured.
- Generated artifacts are documentation projections and must never be edited or treated as authority.
- Markeitech is read-only and advisory; no current order submission or execution exists.
- PostgreSQL stores approved operational facts, not raw provider observations by default.
- Queue admission is not storage and storage does not acknowledge the original event producer.
- Discord and visual files are projections and never create canonical truth.
- Database-internal details are intentionally unknown.

## Visual grammar

- Node text carries implementation, composition, and active-profile status; color is supplementary.
- The graphical DOT/SVG/PNG view uses the manifest-selected opaque dark theme; Markdown appearance follows the reviewer's viewer settings.
- Dashed nodes are disabled, historical, rejected, or future, as stated in their text.
- Edge labels state category, required/optional status, and carried contract.
- External projections consume canonical state; they do not create market truth.
- The diagram is generated from the validated TOML manifest and is never an authority itself.
