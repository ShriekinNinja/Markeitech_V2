# V2 Runtime Control Plane

**Status:** Stage 2 accepted after live review on 2026-08-05.

> **Initial Stage 2 decision record:** The four-state table and explicit omissions below describe
> the first control-plane slice. Later accepted supervision, persistence, evidence-health, and
> recovery work added truthful `DEGRADED` and recovery behavior. Use `docs/current-status.md` and
> the focused later architecture documents for current runtime semantics.

## Purpose

The runtime control plane converts facts observable by Markeitech into immutable system-health
events. It does not supervise Interactive Brokers, duplicate Nautilus connection management, or
claim that future market-data services are ready.

## Approved States

| State | Exact meaning |
|---|---|
| `STARTING` | The system control actor began evaluating its current prerequisites. |
| `READY` | The actor is running and every configured instrument definition is available. |
| `FAILED` | The system control actor entered its Nautilus fault lifecycle. |
| `STOPPING` | The system control actor received its stop lifecycle callback. |

`READY` does not mean that market data is subscribed, current, or flowing. Future components must
publish their own approved readiness facts before the system can make stronger claims.

## Explicit Omissions

- `DEGRADED` and `RECOVERED` are not emitted because V2 does not yet own a reversible runtime
  condition that can support those claims.
- `STOPPED` is not emitted by the actor because `on_stop` means stopping, not stopped. After the
  actor has stopped, the in-process consumer may no longer be available.
- No heartbeat, retained-message service, replay, raw-bus bridge, or persistence was added.
- Connection loss is not projected because the installed Nautilus RC exposes no public connection
  callback to ordinary Python actors.

## Transition Rules

The control plane accepts only these paths:

- uninitialized to `STARTING`, `FAILED`, or `STOPPING`;
- `STARTING` to `READY`, `FAILED`, or `STOPPING`;
- `READY` to `FAILED` or `STOPPING`;
- `FAILED` to `STOPPING`.

Repeating the current state produces no event. Invalid transitions fail visibly instead of
silently rewriting history. Every transition includes its reason, source, current instrument
evidence, and previous state when one exists.

## Startup Delivery

All current actors are statically composed before `LiveNode.run()`. The control actor requests any
missing instrument definitions immediately, then queues initial state evaluation for the node's
event loop. This lets statically composed consumers subscribe in `on_start` before `STARTING` and
an immediately available `READY` are published.

Dynamic actor attachment and late-consumer resynchronization are not current requirements. They
must receive a separate design if V2 later supports runtime composition changes.

## Ownership

`SystemControlActor` owns only the state machine and configured-instrument prerequisite. It
publishes through the accepted `markeitech.system.health` signal contract. Consumers such as the
future Discord actor may present these events but cannot determine or redefine runtime state.
