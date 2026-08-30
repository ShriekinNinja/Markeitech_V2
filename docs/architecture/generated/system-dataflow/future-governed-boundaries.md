# Future Governed Advisory and Controlled Boundaries

> Offline architecture documentation. No current order submission or execution.

Isolate future semantic events, plural opportunities, Sir Loke advisory intent, Markeitect approval, and a separately governed execution boundary.

- View ID: `view.future-governed-boundaries`
- Profile: `profile.v3-es-minimal`
- Manifest: `markeitech-v3-system-dataflow` schema 1
- Checkout evidence: `c6fe2ad89ae2da077d08c55998cc9ff639c5f0ce`
- Review status: `proposed`

## Components

| ID | Component | Kind | Implementation | Composition | Order | Active profile | Semantic owner | Boundary |
|---|---|---|---|---|---:|---|---|---|
| `actor.evidence-health` | Evidence Health | markeitech_actor | implemented | always | 3 | enabled | `actor.evidence-health` | `boundary.intelligence` |
| `actor.market-state-entities` | Market State Entities | markeitech_actor | implemented | conditional | 9 | disabled | `actor.market-state-entities` | `boundary.intelligence` |
| `future.controlled-execution` | Future Controlled Execution Boundary | future_component | future | not_composed | not applicable | not_applicable | `future.controlled-execution` | `boundary.future` |
| `future.opportunities` | Plural Opportunities | future_component | future | not_composed | not applicable | not_applicable | `future.opportunities` | `boundary.future` |
| `future.semantic-events` | Semantic Events | future_component | future | not_composed | not applicable | not_applicable | `future.semantic-events` | `boundary.future` |
| `future.sir-loke` | Sir Loke Advisory Agent | future_component | future | not_composed | not applicable | not_applicable | `future.sir-loke` | `boundary.future` |
| `operator.markeitect` | Markeitect / Operator | operator | external | external | not applicable | not_applicable | `operator.markeitect` | `boundary.projections` |

## Flows

| ID | Source | Target | Category | Contract | Transport | Required | Condition | Delivery |
|---|---|---|---|---|---|---|---|---|
| `edge.entity-revision-semantic` | `actor.market-state-entities` | `future.semantic-events` | publication | `contract.entity-revision` | nautilus_custom_data | no | future only | not_applicable |
| `edge.evidence-sir-loke` | `actor.evidence-health` | `future.sir-loke` | projection | `contract.evidence-health` | not_applicable | no | future only | not_applicable |
| `edge.operator-execution-approval` | `operator.markeitect` | `future.controlled-execution` | control | `contract.future-approval` | not_applicable | no | future only | not_applicable |
| `edge.opportunity-sir-loke` | `future.opportunities` | `future.sir-loke` | projection | `contract.future-opportunity` | not_applicable | no | future only | not_applicable |
| `edge.semantic-opportunity` | `future.semantic-events` | `future.opportunities` | publication | `contract.future-semantic-event` | not_applicable | no | future only | not_applicable |
| `edge.sir-loke-execution-intent` | `future.sir-loke` | `future.controlled-execution` | control | `contract.future-advisory-intent` | not_applicable | no | future only | not_applicable |
| `edge.sir-loke-operator` | `future.sir-loke` | `operator.markeitect` | projection | `contract.future-advisory-intent` | not_applicable | no | future only | not_applicable |

## Limitations

- Static source and configuration checks cannot prove connected runtime behavior.
- Provider account, entitlement, adapter request mapping, and live delivery remain unknown unless separately measured.
- Generated artifacts are documentation projections and must never be edited or treated as authority.
- Markeitech is read-only and advisory; no current order submission or execution exists.
- Every purple/dashed boundary is proposed or future and not current runtime behavior.
- Sir Loke is unrelated to the development-time Kite advisor council.
- No current order submission, execution authority, or execution implementation exists.

## Visual grammar

- Node text carries implementation, composition, and active-profile status; color is supplementary.
- The graphical DOT/SVG/PNG view uses the manifest-selected opaque dark theme; Markdown appearance follows the reviewer's viewer settings.
- Dashed nodes are disabled, historical, rejected, or future, as stated in their text.
- Edge labels state category, required/optional status, and carried contract.
- External projections consume canonical state; they do not create market truth.
- The diagram is generated from the validated TOML manifest and is never an authority itself.
