# V2 Actor Composition And Ownership Discovery

**Status:** Decision Gate 5 accepted and implemented; Stage 8A acquisition ownership added on
2026-08-09 and ready for review.

**Scope:** Current V2 actors and the actor-registration facilities exposed by NautilusTrader
`2.0.0rc1`. This document proposes composition rules; it does not change runtime behavior.

## Executive Finding

V2 currently needs four actors, not a general plugin system:

1. `SystemControlActor` is mandatory and owns Markeitech system-health state.
2. `DataAcquisitionActor` is mandatory and owns provider-facing instrument-definition requests.
3. `OperationalPersistenceActor` is mandatory and owns operational writes while Nautilus runs.
4. `DiscordHealthActor` is an optional, read-only projection.

The recommended composition mechanism is a small, pure `build_actor_plan` function backed by a
code-owned actor registry. Required actors are always present. Optional actors have explicit typed
configuration. TOML selects approved components; it does not contain arbitrary Python import
paths.

## Exact Nautilus Boundary

The installed `LiveNode` exposes `add_actor_from_config(ImportableActorConfig)` before startup.
`ImportableActorConfig` contains an actor path, config path, and dictionary. The RC does not expose
a public Python API for dynamic actor removal, dependency declaration, startup ordering, or an
actor-readiness graph.

V2 should therefore use Nautilus for actor construction and lifecycle, while owning only the small
amount of composition validation Nautilus cannot infer from Markeitech requirements.

## Current Actor Inventory

| Actor | Required | Owns | Consumes | Publishes | Must not own |
|---|---:|---|---|---|---|
| `SystemControlActor` | Yes | System-health transitions and readiness decision | Acquisition status and persistence status | `markeitech.system.health`, acquisition status requests | Provider requests, database writes, Discord delivery |
| `DataAcquisitionActor` | Yes | Instrument-definition discovery, request deduplication, availability status | Configured instrument IDs, cache instruments, status requests | Versioned acquisition status and component failures | Global health decisions, persistence, bars, analytics |
| `OperationalPersistenceActor` | Yes | Ordered operational writes during a live node | `markeitech.system.health` | Persistence readiness/failure facts | System-health decisions, market data, schema policy outside its boundary |
| `DiscordHealthActor` | No | Human-readable Discord projection | `markeitech.system.health` | External HTTP requests only | System state, persistence, retry supervision |

## Dependency Graph

```text
PostgreSQL preflight ----> SystemControlActor readiness <---- acquisition status
          |                         |                              ^
          v                         v                              |
OperationalPersistenceActor <--- system-health events ---> DiscordHealthActor
          |
          +--- persistence failure fact ---> SystemControlActor ---> DEGRADED

IB/cache ---> DataAcquisitionActor --- instrument status ---+
                    ^
                    +--- status request from SystemControlActor
```

This feedback path is intentional, not an ownership cycle. Persistence reports a storage fact;
only the control actor decides that the system is `DEGRADED`. The persistence actor latches its
first failure so a failed `DEGRADED` write cannot create an event loop.

## Required And Optional Composition

### Mandatory core

`SystemControlActor`, `DataAcquisitionActor`, and `OperationalPersistenceActor` are runtime
invariants. Configuration must not pretend they are safely disableable. A V2 run without any one
of them is a different product and requires a separate architecture decision.

### Optional projection

Discord health projection may be explicitly enabled or disabled in its own configuration. When
disabled, the actor is not registered. When enabled, a missing webhook is rejected as invalid
configuration before IB startup. Once the configuration is valid, connection or delivery failures
are logged without blocking runtime state. This distinguishes configuration correctness from the
accepted rule that Discord transport cannot become a runtime dependency.

Future optional actors should follow the same pattern: a typed configuration section and a
code-owned registration function. Required dependencies are validated before IB startup.

## Recommended Composition Plan

Create a pure composition layer with two concepts:

- `StartupPrerequisites`: immutable facts established before `LiveNode.run()`, initially the run ID
  and successful operational-persistence preflight.
- `ActorRegistration`: a code-owned actor key plus its `ImportableActorConfig`.

`build_actor_plan(system_config, prerequisites)` returns the complete ordered tuple of approved
registrations. It must:

- always include exactly one system-control actor, one data-acquisition actor, and one
  operational-persistence actor;
- include Discord only when configured;
- reject duplicate actor IDs;
- reject missing required prerequisite facts;
- reject enabled actors with missing required configuration;
- build actor dictionaries in one place rather than inside `node.py`; and
- remain a pure function that can be tested without PostgreSQL, IB, or a `LiveNode`.

`node.py` then builds Nautilus clients and registers the returned plan. It does not decide actor
ownership or optionality.

## Readiness Without Startup Timing

The current runtime has both an approved PostgreSQL preflight and a transient persistence-ready
signal. A transient signal is vulnerable to actor startup ordering and duplicates a fact already
proved before node construction.

The recommendation is to make successful persistence preflight an immutable
`StartupPrerequisites` input to the control actor. The persistence actor still publishes runtime
failure facts, but the ready signal is removed. `READY` then depends on:

1. a composition-time PostgreSQL prerequisite that cannot be missed; and
2. a complete acquisition status accepted by the control actor.

This does not create a generic actor-readiness protocol. Future asynchronous components may need
one, but Stage 5 should not design it before such a component exists. Stage 6 remains responsible
for supervision and runtime recovery policy.

Stage 8A completes that ownership transfer. `DataAcquisitionActor` now checks the Nautilus cache,
requests each missing configured instrument definition once, and publishes a versioned status.
`SystemControlActor` consumes that status and never calls the provider-facing request API.

The status exchange is startup-order safe. Acquisition publishes its current status when it
starts; control requests the current status when it starts and repeats that request from its
1 ms initial-evaluation callback, after actor startup. Duplicate requests and duplicate status
facts are harmless. Neither actor assumes that registration order is a readiness guarantee.

## Explicit Non-Goals

- No arbitrary actor or module paths in TOML.
- No dependency-injection container.
- No dynamic actor loading or removal.
- No second message bus.
- No generic plugin framework.
- No bar, quote, trade, options, analytics, or trading actors.
- No retry, recovery, heartbeat, or broad supervision policy.

## Known Shutdown Boundary

Current live evidence shows consumers receive the control actor's synchronous `STOPPING` event,
but the installed API does not document actor stop ordering as a dependency guarantee. The
authoritative clean terminal fact remains the CLI's post-node `STOPPED` update. Stage 6 should
decide whether best-effort `STOPPING` projections require any stronger shutdown coordination.

## Accepted Decisions

1. System control, data acquisition, and operational persistence are non-disableable core actors.
2. Discord is the only currently optional actor and uses a typed `enabled` setting. When enabled,
   a missing webhook fails pre-connection configuration validation; later delivery failure remains
   isolated.
3. A small code-owned registry and pure actor plan own topology. TOML cannot supply arbitrary
   Python import paths.
4. Immutable preflighted startup prerequisites replace the transient persistence-ready signal.
   Runtime persistence failures remain explicit facts consumed by system control.
5. Dynamic composition and a generic actor-readiness protocol remain deferred until a real
   component requires them.
6. Instrument-definition requests belong exclusively to `DataAcquisitionActor`; system control
   consumes its status and remains the sole global-health transition owner.
