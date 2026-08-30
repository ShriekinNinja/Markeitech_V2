# Bokeh Live System Visualization — Shallow Feasibility Assessment

**Status:** Reference-only research note; no architecture, dependency, implementation, runtime,
or product decision is approved by this document

**Prepared:** 2026-08-30

**Reference inspected:** [Bokeh task-scheduler demo](https://demo.bokeh.org/task-scheduler)

**Inspection depth:** Quick and shallow; no benchmark, local prototype, dependency installation,
runtime connection, or advisor consultation

## Executive Finding

A scheduler-style live representation of Markeitech's components, process boundaries, data flows,
requests, workers, queues, and health transitions is highly feasible. Bokeh is a credible candidate
for this particular operational visualization because it already supports live network graphs,
timelines, linked selection, hover details, streaming data sources, widgets, dark styling, and a
stateful Python server.

The reference is useful as an interaction pattern, not as a desired outcome or architecture to
copy. Its synthetic scheduler advances inside the Bokeh application. A live Markeitech view must
instead remain a replaceable, read-only projection in a separate process, with bounded delivery
from canonical runtime facts. It must never become a Nautilus actor, analytical owner, provider
client, persistence authority, or runtime-control surface.

## What the Reference Demonstrates

The inspected demo combines four useful presentation layers:

- a compact live summary of completed, running, ready, waiting, throughput, and unavailable work;
- worker-lane timelines showing what occupied each worker and when;
- a dependency graph whose node states change as execution advances; and
- a selected-node inspector with hover, selection, filtering, and local controls.

The implementation is meaningful but not enormous. The main application is approximately 671
lines and the separate synthetic scheduler model approximately 233 lines, plus CSS and small Jinja
templates. The application uses Bokeh `ColumnDataSource.patch()` for existing graph and timeline
records, `ColumnDataSource.stream()` for new events, `StaticLayoutProvider` for graph positions,
and a 150 ms periodic Python callback. Browser selection and controls invoke Python callbacks
through the stateful Bokeh session. See the linked
[application source](https://github.com/bokeh/demo.bokeh.org/blob/main/apps/task_scheduler/__init__.py)
and [simulation model](https://github.com/bokeh/demo.bokeh.org/blob/main/apps/task_scheduler/simulation.py).

Bokeh Server creates a document for each browser session and synchronizes model updates to the
browser. Callbacks for one session execute serially under that document's lock, while different
sessions can run concurrently. Bokeh also supplies bounded latest-update scheduling for cases
where a producer outpaces visualization work. These behaviors make live visualization practical,
but session memory, callback duration, update volume, and multi-client behavior still require
measurement. See the current
[Bokeh Server application documentation](https://docs.bokeh.org/en/latest/docs/user_guide/server/app.html).

## Possible Markeitech Representation

A future view could present:

- stable components and process boundaries from the reviewed architectural topology;
- actor composition order and enabled, disabled, external, future, or unavailable status;
- starting, ready, degraded, failed, stopping, stopped, and recovering lifecycle transitions;
- provider subscriptions and historical requests moving through requested, pending, active,
  ready, released, degraded, or failed states;
- queue depth, bounded admission, worker activity, retry, overflow, and recovery;
- evidence health, session state, persistence readiness, and system-health transitions;
- a compact time lane for requests, callbacks, persistence batches, projection delivery, and
  lifecycle events; and
- node selection exposing stable identity, responsibility, configuration identity, latest
  transition, evidence timestamp, failure state, and connected flows.

The reference's execution controls should not be copied. The first Markeitech surface should allow
only local display behavior such as filtering, selecting, highlighting related paths, freezing a
visual snapshot, choosing a time range, and pausing browser rendering. No browser action should
pause, interrupt, retry, enable, disable, acknowledge, or otherwise mutate a runtime component.

## Recommended Safety Boundary

The existing [V2 Live Dashboard Plan Draft](../roadmap/v2-live-dashboard-plan-draft.md) already
contains the appropriate high-level isolation model. For this narrower topology view, the expected
shape is:

```text
Reviewed architectural topology
    -> offline-generated topology artifact with stable component and flow IDs

Canonical runtime operational facts
    -> minimal bounded read-only projection bridge
    -> local versioned snapshot/delta transport
    -> separate Bokeh server process
    -> browser visualization
```

The existing TOML diagram generator must remain offline. A future approved generator extension
could produce a versioned topology JSON artifact from the same stable IDs, but neither Nautilus nor
the live runtime should load or invoke the diagram generator. The Bokeh process would combine the
static generated topology with a separate live status stream. Missing IDs, version disagreement,
sequence gaps, overflow, and stale data would be displayed explicitly rather than guessed away.

The live stream should provide one bounded snapshot followed by ordered or revisioned deltas.
Updates should patch or stream only changed records. It should never poll, copy, serialize, and
redraw an entire retained store for every browser refresh. Browser absence, overload, restart, or
failure must not affect acquisition, calculations, entities, persistence, Discord, readiness, or
shutdown.

This condition is important because the earlier isolated Observatory provided functional value
but was associated with severe host degradation while its browser projection was open. Root cause
was not proven; repeated full-store copying, JSON serialization, and full Plotly refreshes were the
leading hypothesis recorded in the dashboard draft. A Bokeh approach still requires a controlled
dashboard-off/dashboard-on comparison before live acceptance.

## Bokeh Fit

For a system topology and operational timeline, Bokeh appears strong:

- Python-native and relatively quick to prototype;
- built-in graph, static-layout, timeline, hover, selection, linked-source, widget, and streaming
  facilities;
- live synchronization over WebSockets;
- straightforward dark styling and custom HTML/Jinja presentation;
- standalone or embedded deployment choices; and
- permissive BSD-style licensing.

Relevant upstream references are the
[deployment guide](https://docs.bokeh.org/en/latest/docs/user_guide/server/deploy.html) and
[Bokeh license](https://github.com/bokeh/bokeh/blob/branch-3.10/LICENSE.txt).

Bokeh should not yet be selected as the universal engine for a future financial workstation.
Candlesticks, synchronized panes, dense custom market-structure layers, long sessions, and larger
application state may favor the React/Canvas alternatives already considered in the dashboard
draft. Bokeh could be excellent for an operations/topology workspace without needing to own every
future market visualization.

## Shallow Effort Estimate

The following ranges assume one experienced engineer and no major changes to existing canonical
contracts:

| Deliverable | Estimated effort |
|---|---:|
| Disconnected visual proof using generated topology IDs and synthetic state changes | 3–5 working days |
| Polished fixture-only prototype with graph, timeline, inspector, filters, deterministic scenarios, dark mode, and basic tests | 1–2 weeks |
| Live read-only MVP with a separate Bokeh process, bounded bridge, topology/version handshake, snapshot/delta delivery, reconnect, gaps, and health indication | 4–7 weeks |
| Operationally acceptable implementation with performance budgets, backpressure, multi-session tests, accessibility, packaging, documentation, endurance tests, and controlled dashboard-off/on acceptance | 8–12 weeks total |

If another approved batch first supplies the generic projection bridge, gateway, topology/version
handshake, and snapshot/delta contracts, the live visualization portion could plausibly fall to
approximately 2–4 weeks. The difficult part is not drawing the graph; it is providing trustworthy,
isolated, bounded, late-join-safe live data without affecting Markeitech.

## Main Unknowns

- Which operational facts already expose approved typed snapshots and deltas.
- Whether component lifecycle, queue, worker, request, and subscription facts have stable identities
  matching the architectural topology.
- Required timeline history and byte/count bounds.
- Expected update rate and simultaneous browser-session count.
- Bokeh per-session memory and CPU behavior on the target workstation.
- Whether the topology keeps deterministic offline positions or permits local layout changes.
- Whether this becomes one operations page in a broader dashboard or a standalone local tool.

## Recommendation

When this work is intentionally opened, begin with a fixture-only Bokeh spike. Use generated
topology identities, synthetic operational transitions, one request/worker timeline, node
selection, and explicit stale/gap/overflow states. Measure browser and server CPU, memory, render
latency, update coalescing, hidden-tab behavior, and two to four concurrent sessions.

If that spike is visually useful and resource-bounded, proceed only through the isolated projection
boundary described above. Do not embed Bokeh inside Nautilus or connect the browser directly to
canonical runtime internals.
