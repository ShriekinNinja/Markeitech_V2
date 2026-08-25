# Architecture Boundaries Advisor Routing Evaluation

Last reviewed: 2026-08-25.

This matrix defines forward-routing acceptance for the advisor. Independent static contract review
checks whether the skill description, body, custom-agent role, and generic router express each
expected boundary; it does not observe automatic selection.
Actual automatic discovery, cross-advisor ordering, and delegated execution remain `PENDING` until
Kite is cache-busted, reinstalled, and exercised in a fresh Codex thread.

| Request | Expected routing | Required boundary | Contract check | Installed result |
|---|---|---|---|---|
| A new component would copy canonical entity state; review duplicate authority and removal cost | Architecture boundaries advisor | Map owners, canonical scope, drift, and change cost | ALIGNED | PENDING |
| Authority says one actor owns health but code lets another actor mutate it | Architecture boundaries advisor | Defect-first ownership and drift review | ALIGNED | PENDING |
| Move subscription ownership from acquisition to individual consumers | Architecture boundaries plus Nautilus; provider specialist if provider behavior matters | No independent framework or provider claim | ALIGNED | PENDING |
| Review actor responsibility placement and its shutdown contract | Architecture for placement; event-driven for executable lifecycle; Nautilus if framework behavior matters | Separate accountable owner from execution semantics | ALIGNED; neighboring event-driven discovery must also remain topology-scoped | PENDING |
| Assign recovery ownership after partial failure | Architecture for recovery-owner assignment; event-driven for recovery execution | Do not define runtime recovery from structural ownership alone | ALIGNED; neighboring event-driven discovery must also remain topology-scoped | PENDING |
| Define event ordering, idempotency, retries, acknowledgements, and backpressure | Event-driven architecture specialist | Architecture advisor participates only if topology or ownership also changes | ALIGNED | PENDING |
| Review an existing actor retry implementation without changing owners | Event-driven architecture specialist | Accepted topology is outside this advisor's trigger | ALIGNED | PENDING |
| Add a queue between two actors | Architecture for whether the boundary is justified; event-driven for queue semantics; Nautilus for native capability | Preserve specialist order and do not assume a custom queue | ALIGNED | PENDING |
| Decide whether a Nautilus bus, cache, timer, or lifecycle capability replaces a wrapper | Nautilus advisor first; architecture advisor consumes its matrix | No remembered or independent capability claim | ALIGNED | PENDING |
| Decide whether a derived fact has an approved reason to be durable | Architecture boundaries first; PostgreSQL after durability and owner approval, or only to identify mechanics and unknowns | Separate logical durability from database implementation | ALIGNED | PENDING |
| Design PostgreSQL migrations, constraints, transactions, retention, or restore | PostgreSQL persistence specialist | Architecture advisor may report cross-owner consequences only | ALIGNED | PENDING |
| Persist Sir Loke advisory state and recover it after restart | Governance for advisory-state meaning; architecture for durable owner; PostgreSQL after approval; event-driven if recovery delivery matters | No specialist may absorb the others' semantics | ALIGNED | PENDING |
| Classify conflicting timestamps, revisions, gaps, or stale evidence | Data-quality and lineage specialist | Architecture advisor may assign structural ownership only | ALIGNED | PENDING |
| Move a Python worker into a new component and review cancellation | Architecture plus Python runtime; Nautilus first if an actor callback contract controls execution | Separate ownership placement from Python mechanics | ALIGNED | PENDING |
| Review asyncio cancellation and worker shutdown without changing owners | Python runtime advisor | Architecture advisor must not trigger for accepted topology | ALIGNED | PENDING |
| Define Sir Loke approvals, tools, or advisory-state semantics | Live-agent governance specialist | Architecture advisor may map owners but not define semantics | ALIGNED | PENDING |
| Split a Python module without moving responsibility or public authority | Python runtime advisor only if package correctness is consequential | No architecture trigger from file layout alone | ALIGNED | PENDING |
| Add a private helper without changing contracts or authority | No architecture specialist | Ordinary implementation must not trigger this advisor | ALIGNED | PENDING |

Fresh-thread acceptance must verify proportional output: a narrow ownership question should not
produce exhaustive matrices for immaterial domains. Record observed selection, advisor order,
skill loading, evidence labels, and output scope here without promoting static expectations into
measured behavior.
