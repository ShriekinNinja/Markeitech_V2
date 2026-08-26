# Event-Driven Architecture Advisor Routing Evaluation

Last reviewed: 2026-08-25.

This matrix defines forward-routing acceptance. Static review checks whether the skill description,
body, custom-agent role, and generic router express each boundary; it does not prove normal-task
dormancy or selection after explicit Kite activation. Record installed behavior only after Kite is
cache-busted, reinstalled, and exercised in fresh Codex tasks.

| Request | Expected routing | Required boundary | Static contract | Installed result |
|---|---|---|---|---|
| Review retry and idempotency in an existing accepted actor topology | Event-driven; Nautilus if framework behavior matters | Do not reopen accepted placement | ALIGNED | PENDING |
| Move responsibility between actors and define shutdown | Architecture first; event-driven for lifecycle semantics; Nautilus and Python as applicable | Separate placement, delivery policy, framework contract, and mechanics | ALIGNED | PENDING |
| Add a queue between two owners | Architecture for boundary justification; Nautilus for native capability; event-driven for admission and delivery policy; Python for mechanics | Do not assume a custom queue or collapse policy into implementation | ALIGNED | PENDING |
| Review asyncio cancellation without changing event meaning | Python runtime; event-driven only if accepted-work or cancellation semantics are unresolved | Python execution is not generic event authority | ALIGNED | PENDING |
| Classify market observations as duplicate, conflicting, revised, or stale | Market-evidence validation first; event-driven only for delivery consequences | Evidence meaning is not transport identity | ALIGNED | PENDING |
| Define Sir Loke approvals, tools, or abstention | Live-agent governance; event-driven only for an approved channel contract | Agent authority is not event delivery | ALIGNED | PENDING |
| Add a private helper without changing a material contract | No event-driven specialist | Avoid incidental triggering | ALIGNED | PENDING |

Fresh-thread acceptance must record skill discovery, delegated role availability, advisor order,
required handoffs, evidence labels, and proportional output. A narrow retry question should not
produce exhaustive matrices for immaterial domains.
