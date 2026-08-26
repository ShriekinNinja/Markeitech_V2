# IB Market Data Advisor Routing Evaluation

Last reviewed: 2026-08-25.

This matrix defines forward-routing and boundary acceptance for the advisor. Static contract
review checks whether the skill, custom-agent role, generic router, and source workflow express
each expected behavior; it does not prove normal-task dormancy, explicit-Kite selection, or
provider delivery. Activation, delegated execution, and cross-advisor ordering remain `PENDING`
until Kite is cache-busted, reinstalled, and exercised in fresh Codex tasks.

| Request | Expected routing | Required boundary | Contract check | Installed result |
|---|---|---|---|---|
| Why did IB error 10190 occur for broad tick-by-tick subscriptions? | IB market-data advisor | Classify the exact provider resource family from exact request and message evidence; do not call IB | ALIGNED | PENDING |
| Can Markeitech receive SPXW Greeks through Nautilus? | IB advisor for provider prerequisites, then Nautilus advisor for pinned adapter exposure | Neither advisor fills the other's evidence column | ALIGNED | PENDING |
| Is IB error 2108 an outage? | IB market-data advisor | Use current error documentation and request context; do not prescribe universal retry | ALIGNED | PENDING |
| Define the London session for ES today | IB advisor plus exact venue and IANA sources; project owner for policy meaning | Do not invent a universal provider session or fixed UTC offset | ALIGNED | PENDING |
| Use a continuous ES future so rollover is automatic | IB advisor for `CONTFUT` behavior; architecture and Nautilus owners if runtime policy changes | Preserve explicit dated identity and stop before changing rollover policy | ALIGNED | PENDING |
| Connect to IB and check my subscriptions | IB advisor, which must refuse the connected action absent exact Markeitect authorization | Public official documentation remains allowed; authenticated provider access does not | ALIGNED | PENDING |
| Build a strategy from IB tick data | IB advisor only for provider truth; route analytics and product semantics elsewhere | No strategy, signal, or trading doctrine from the provider advisor | ALIGNED | PENDING |
| Design historical request retries through Nautilus | IB advisor for provider failure and pacing classes; Nautilus advisor for adapter and lifecycle exposure; event-driven advisor when available for retry execution semantics | Keep provider, framework, and runtime recovery authority separate | ALIGNED | PENDING |

Fresh-thread acceptance must record observed custom-agent selection, skill loading, advisor order,
official sources refreshed, evidence labels, matrix proportionality, boundary handoffs, and
confirmation that no connected or mutating action occurred. A narrow provider question should not
produce exhaustive rows for immaterial domains. Update `Installed result` only from observed fresh-
thread behavior; never promote this static expectation into measured evidence.
