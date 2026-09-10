# Calendars and Evidence Health

> Offline architecture documentation. No current order submission or execution.

Show calendar state, historical planning, and evidence-health capabilities.

- View ID: `view.metrics-entities-intelligence`
- Profile: `profile.example`
- Manifest: `markeitech-v3-system-dataflow` schema 1
- Checkout evidence: `a382f2e0636cdb3148b451e3e0e8239a684438e5`
- Review status: `proposed`

## Components

| ID | Component | Kind | Implementation | Composition | Order | Active profile | Semantic owner | Boundary |
|---|---|---|---|---|---:|---|---|---|
| `actor.evidence-health` | Evidence Health | markeitech_actor | implemented | always | 3 | enabled | `actor.evidence-health` | `boundary.intelligence` |
| `actor.historical-planner` | Historical Evidence Planner | markeitech_actor | implemented | always | 5 | enabled | `actor.historical-planner` | `boundary.intelligence` |
| `actor.session-state` | Session State | markeitech_actor | implemented | always | 2 | enabled | `actor.session-state` | `boundary.intelligence` |
| `actor.watchlist` | Watchlist | markeitech_actor | implemented | conditional | 6 | enabled | `actor.watchlist` | `boundary.acquisition` |
| `component.canonical-calendar` | Canonical Calendar | engine | implemented | not_composed | not applicable | enabled | `actor.session-state` | `boundary.intelligence` |
| `component.data-engine` | Nautilus Data Engine | engine | implemented | always | not applicable | enabled | `component.data-engine` | `boundary.nautilus` |

## Flows

| ID | Source | Target | Category | Contract | Transport | Required | Condition | Delivery |
|---|---|---|---|---|---|---|---|---|
| `edge.calendar-request-health` | `actor.evidence-health` | `actor.session-state` | query | `contract.calendar-state-snapshot-request` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-request-planner` | `actor.historical-planner` | `actor.session-state` | query | `contract.calendar-projection-request` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-response-health` | `actor.session-state` | `actor.evidence-health` | response | `contract.calendar-state-snapshot-response` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-response-planner` | `actor.session-state` | `actor.historical-planner` | response | `contract.calendar-projection-response` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-transition-health` | `actor.session-state` | `actor.evidence-health` | publication | `contract.calendar-transition` | nautilus_custom_data | yes | always | unknown |
| `edge.calendar-transition-planner` | `actor.session-state` | `actor.historical-planner` | publication | `contract.calendar-transition` | nautilus_custom_data | yes | always | unknown |

## Limitations

- Static source and configuration checks cannot prove connected runtime behavior.
- Provider account, entitlement, adapter request mapping, and live delivery remain unknown unless separately measured.
- Generated artifacts are documentation projections and must never be edited or treated as authority.
- Markeitech is read-only and advisory; no current order submission or execution exists.
- Shared metric and entity contracts have no current producer.
- Dependencies do not imply causality, confidence, ranking, advice, or trading intent.

## Visual grammar

- Node text carries implementation, composition, and active-profile status; color is supplementary.
- The graphical DOT/SVG/PNG view uses the manifest-selected opaque dark theme; Markdown appearance follows the reviewer's viewer settings.
- Graphical cards, relationships, and nested boundaries use Diagrams C4 primitives with escaped Graphviz-native labels and no external assets.
- Dashed nodes are disabled, historical, rejected, or future, as stated in their text.
- Edge labels state category, required/optional status, and carried contract.
- External projections consume canonical state; they do not create market truth.
- The diagram is generated from the validated TOML manifest and is never an authority itself.
