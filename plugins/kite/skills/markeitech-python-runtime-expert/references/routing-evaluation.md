# Python Runtime Advisor Routing Evaluation

Last reviewed: 2026-08-25.

This matrix defines forward-routing acceptance for the advisor. Independent static contract review
checks whether the skill description, body, custom-agent role, and generic router express each
expected boundary; it does not observe normal-task dormancy or explicit-Kite selection.
Activation and delegated execution remain `PENDING` until Kite is cache-busted, reinstalled, and
exercised in fresh Codex tasks.

| Request | Expected routing | Required boundary | Contract check | Installed result |
|---|---|---|---|---|
| Review an asyncio queue worker for cancellation, bounded drain, late results, and restart | Python runtime advisor | Return the ownership-and-lifecycle table | ALIGNED | PENDING |
| Diagnose unexplained RSS growth and design a representative profiling plan | Python runtime advisor | Separate RSS, Python allocations, native work, and profiler effects | ALIGNED | PENDING |
| Review a consequential typing or package boundary without moving product responsibility | Python runtime advisor | Do not claim runtime validation from annotations | ALIGNED | PENDING |
| Move a public interface or canonical fact between component owners | Architecture boundaries specialist; Python advisor only for package, import, type, or execution consequences | Do not assign component authority from module layout | ALIGNED | PENDING |
| Define accepted-work meaning, event ordering, acknowledgement, retries, or backpressure | Event-driven architecture specialist; Python advisor only for Python execution mechanics | Do not convert queue behavior into product delivery policy | ALIGNED | PENDING |
| Diagnose an implementation defect in an already accepted `asyncio.Queue` contract | Python runtime advisor | Preserve the established delivery policy while checking task and queue execution | ALIGNED | PENDING |
| Fix an import cycle without moving product responsibility or authority | Python runtime advisor | Limit the recommendation to Python package and dependency mechanics | ALIGNED | PENDING |
| Rename a local variable or change a small synchronous helper | No specialist | Ordinary work must not trigger this advisor | ALIGNED | PENDING |
| Review blocking work inside a Nautilus actor callback | Nautilus advisor first; Python advisor only for generic Python behavior after the callback contract is verified | No independent framework claim | ALIGNED | PENDING |
| Decide whether Nautilus owns a timer, cache, lifecycle, or message-bus contract | Nautilus advisor | Python advisor must defer | ALIGNED | PENDING |
| Change PostgreSQL schema, retention, or database operations | PostgreSQL specialist or missing-coverage gate | Python advisor may cover only worker or driver-integration behavior outside database semantics | ALIGNED | PENDING |
| Define a trading signal, market-state meaning, or options decision | Applicable market or product specialist | Python advisor must not define semantics | ALIGNED | PENDING |

Fresh-thread acceptance must also verify that the delegated advisor loads
`$kite:markeitech-python-runtime-expert`, labels consequential claims with the required evidence
classes, and includes the ownership-and-lifecycle table for a concurrency case. Record observed
results here without converting a static expectation into measured behavior.
