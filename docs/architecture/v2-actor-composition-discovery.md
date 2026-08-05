# V2 Actor Composition And Ownership Discovery

**Status:** Discovery complete; Decision Gate 5 is open.

**Scope:** Current V2 actors and the actor-registration facilities exposed by NautilusTrader
`2.0.0rc1`. This document proposes composition rules; it does not change runtime behavior.

## Executive Finding

V2 currently needs three actors, not a general plugin system:

1. `SystemControlActor` is mandatory and owns Markeitech system-health state.
2. `OperationalPersistenceActor` is mandatory and owns operational writes while Nautilus runs.
3. `DiscordHealthActor` is an optional, read-only projection.

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
| `SystemControlActor` | Yes | System-health transitions and readiness decision | Instrument definitions and persistence status | `markeitech.system.health` | Database writes, Discord delivery, long-term data acquisition ownership |
| `OperationalPersistenceActor` | Yes | Ordered operational writes during a live node | `markeitech.system.health` | Persistence readiness/failure facts | System-health decisions, market data, schema policy outside its boundary |
| `DiscordHealthActor` | No | Human-readable Discord projection | `markeitech.system.health` | External HTTP requests only | System state, persistence, retry supervision |

## Dependency Graph

```text
PostgreSQL preflight ----> SystemControlActor readiness
          |                         |
          v                         v
OperationalPersistenceActor <--- system-health events ---> DiscordHealthActor
          |
          +--- persistence failure fact ---> SystemControlActor ---> DEGRADED
```

This feedback path is intentional, not an ownership cycle. Persistence reports a storage fact;
only the control actor decides that the system is `DEGRADED`. The persistence actor latches its
first failure so a failed `DEGRADED` write cannot create an event loop.

## Required And Optional Composition

### Mandatory core

`SystemControlActor` and `OperationalPersistenceActor` are runtime invariants. Configuration must
not pretend they are safely disableable. A V2 run without either actor is a different product and
requires a separate architecture decision.

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

- always include exactly one system-control actor and one operational-persistence actor;
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
2. instrument definitions observed by the control actor.

This does not create a generic actor-readiness protocol. Future asynchronous components may need
one, but Stage 5 should not design it before such a component exists. Stage 6 remains responsible
for supervision and runtime recovery policy.

`SystemControlActor` currently requests configured instrument definitions because no acquisition
owner exists yet. Stage 5 leaves that behavior in place. Stage 8 should move the request to the
approved acquisition owner and let control consume the resulting readiness fact.

## Explicit Non-Goals

- No arbitrary actor or module paths in TOML.
- No dependency-injection container.
- No dynamic actor loading or removal.
- No second message bus.
- No generic plugin framework.
- No analytics, market-data, or trading actors.
- No retry, recovery, heartbeat, or broad supervision policy.

## Known Shutdown Boundary

Current live evidence shows consumers receive the control actor's synchronous `STOPPING` event,
but the installed API does not document actor stop ordering as a dependency guarantee. The
authoritative clean terminal fact remains the CLI's post-node `STOPPED` update. Stage 6 should
decide whether best-effort `STOPPING` projections require any stronger shutdown coordination.

## Decision Gate 5

1. Accept system control and operational persistence as non-disableable core actors?
2. Accept Discord as the only currently optional actor, controlled by a typed `enabled` setting?
   When enabled, a missing webhook fails pre-connection configuration validation; later delivery
   failure remains isolated.
3. Accept a small code-owned registry and pure actor plan instead of arbitrary TOML import paths or
   a plugin framework?
4. Replace the transient persistence-ready signal with immutable, preflighted startup
   prerequisites while retaining the persistence-failure signal?
5. Defer dynamic composition and generic actor-readiness protocols until a real component requires
   them?

No Stage 5 implementation should begin before these decisions are accepted.
