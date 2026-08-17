# V2 Runtime Messaging Discovery

**Status:** Discovery complete; Decision Gate 1 accepted on 2026-08-05.

**Scope:** NautilusTrader `2.0.0rc1` as installed in `v2/.venv`. This document records
available runtime communication facilities and their constraints. It does not approve a
Markeitech message contract or change runtime behavior.

## Executive Finding

Nautilus already supplies the in-process message bus. Markeitech should not build another one.

The exact release candidate installed by V2 exposes two supported communication paths to Python
`DataActor` implementations:

1. actor signals through `publish_signal`, `subscribe_signal`, and `on_signal`; and
2. custom data through `publish_data`, `subscribe_data`, and `on_data`.

Nautilus also has a lower-level `MessageBus` with direct, request-response, and publish-subscribe
patterns. However, this RC does not expose that object on ordinary Python actors or `LiveNode`.
Current online documentation shows `self.msgbus` in some examples, but that API is not present in
the installed package and cannot be treated as available.

## Exact Installed API

### Actor signals

`DataActor` provides:

- `publish_signal(name, value, ts_event=0)`
- `subscribe_signal(name="", priority=None)`
- `unsubscribe_signal(name="")`
- `on_signal(signal)` for receiving values

The received `Signal` exposes `name`, string `value`, `ts_event`, and `ts_init`. The publisher stub
accepts `Any`, while the receiver contract says `str`. The current readiness actor publishes a
dictionary, but that has not been proven safe through a subscriber or serializer. A contractual
signal payload should therefore be an explicit string unless a focused test proves otherwise.

Signals are the smallest supported mechanism for alerts and status. They have no replay or
durability by themselves.

### Custom data

`DataActor` also provides:

- `publish_data(data_type, data)`
- `subscribe_data(data_type, client_id=None, params=None)`
- `unsubscribe_data(...)`
- `on_data(data)` for receiving values

This path uses Nautilus `DataType` and `CustomData`. `DataType` carries a type name, metadata,
optional identifier, and generated topic. `CustomData` carries the value and event/init
timestamps.

Custom data gives a stronger structured envelope, but it also places system lifecycle messages
inside Nautilus data semantics. That may be unnecessary for transient health transitions and may
later couple them to data routing or persistence decisions.

### Low-level message bus

The installed `MessageBus` supports:

| Pattern | API |
|---|---|
| Direct message | `register`, `deregister`, `send` |
| Request-response | `request`, `response`, `is_pending_request` |
| Publish-subscribe | `subscribe`, `unsubscribe`, `publish` |
| Inspection | topics, endpoints, subscriptions, and counters |

Focused offline probes established that local publication is synchronous, higher subscription
priority runs first, and glob-style topic matching is supported. Subscriber exceptions do not
propagate to the publisher.

This is valuable platform capability, but V2 actors cannot currently access it through a public
Python actor property. Introducing a custom bridge or unsupported injection only to reach raw
topics would add infrastructure before a real requirement exists.

## Lifecycle Facilities And Gaps

Nautilus components have a native finite-state lifecycle including ready, starting, running,
stopping, stopped, degraded, disposed, and faulted states. Actors expose lifecycle hooks such as
`on_start`, `on_stop`, `on_degrade`, and `on_fault`.

No public native `SystemReady` event, system-health topic, actor heartbeat, or connection-state
callback was found in the installed Python API. Component state exists internally, but Nautilus
does not automatically publish the Markeitech-level operational meaning needed by consumers such
as Discord.

The smallest gap Markeitech must own is therefore a projection of accepted runtime facts into
explicit system-health events. It must not invent those facts. Stage 2 will separately define what
each system state proves.

## Startup Ordering Risk

The verified live run starts the IB client and engines before the trader and registered actors.
Actor `on_stop` runs before the IB client disconnects.

There is no installed-API guarantee for ordering among multiple actors. A producer publishing in
its `on_start` can therefore race a consumer that subscribes in its own `on_start`. The approved
design must not depend on actor registration order for the first important transition.

## Current V2 Meaning

`ReadinessActor` currently:

- checks whether all configured instrument definitions are in cache;
- requests missing definitions;
- logs startup and stop;
- publishes `system.ready` once all definitions are available.

`SYSTEM_READY` currently means only that configured instrument definitions are available. It does
not prove that live subscriptions exist, data is flowing, or a connection is healthy. Those
meanings remain open for Decision Gate 2.

## Decision Gate 1 Options

### Option A: Actor signal with a versioned string payload

Use the supported actor signal API and encode a small, versioned system event as JSON text.

Benefits:

- smallest supported V2 actor-to-actor path;
- appropriate for transient status and alert fan-out;
- no parallel bus or unsupported internals;
- enough structure for a Discord consumer.

Costs:

- schema validation belongs to Markeitech;
- the payload is string-encoded rather than a native typed object;
- no replay or durability.

### Option B: Nautilus custom data

Use `DataType` and `CustomData` for each approved system event.

Benefits:

- stronger structured Nautilus envelope;
- explicit event and initialization timestamps;
- clearer path if system events later need data-engine routing.

Costs:

- more ceremony for a small lifecycle contract;
- mixes operational control information with market/custom data semantics;
- may prematurely influence persistence design.

### Option C: Raw message-bus bridge

Create a supported boundary that injects or wraps the low-level bus for Python actors.

Benefits:

- semantically direct topics and richer messaging patterns.

Costs:

- the required actor access is absent from this installed RC;
- creates custom infrastructure around a changing pre-release API;
- request-response Python contracts are not sufficiently exposed or typed yet.

## Accepted Decision

Markeitect approved **Option A** for the first lifecycle and Discord-health slice: one versioned
JSON string carried
by actor signals. Keep the envelope deliberately small:

- `schema_version`
- `state`
- `reason`
- `source`
- `evidence`

Use the `Signal` envelope's `name`, `ts_event`, and `ts_init` rather than duplicating them inside the
payload.

The approved signal name is `markeitech.system.health`. The actor that owns a runtime fact owns its
publication. Consumers may project the event but must not redefine or republish system state.

For V2 message vocabulary:

- an **event** is an immutable fact that occurred;
- a **snapshot** represents current state for recovery or a late consumer;
- a **command** requests an action and is not part of this first contract;
- a **failure** is an event outcome with evidence, not a separate transport mechanism.

The first implementation proves string delivery through two actors in one offline `LiveNode`.
Stage 2 must define how a late-starting consumer obtains the current state; transient signals alone
do not solve that problem.

Raw bus access, custom data, commands, snapshots, replay, and durability are not introduced by this
decision.
