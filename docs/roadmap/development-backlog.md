# Markeitech Development Backlog

The [live foundation plan](live-foundation-plan.md) owns direction. The selected GitHub issue owns
work and acceptance. This inventory supplies candidates only when Markeitect requests task
selection; it does not add prerequisites to an active issue.

## Immediate Priority

Bring up the native execution engine and account monitoring, then exercise an explicitly authorized
live order lifecycle. Define the exact account, client configuration, actions and limits in that
issue. The current runtime does not implement these capabilities.

## Subsequent Foundation Work

- Compose the actors and strategies needed by selected live consumers with explicit configuration
  and lifecycle ownership.
- Run indicators on admitted native data with the warmup, freshness and output semantics required
  by those consumers.
- Demonstrate concurrent operation and inspect actual health, resource use and output in live use.

## Observed Debt And Optional Work

Address these only when selected or when they directly block the current issue:

- provider subscription/reconnect recovery and interrupted historical requests;
- shared historical reuse and request cancellation/correlation;
- account/order/fill/position reconciliation and recovery after the execution path exists;
- indicator production, late-consumer state and historical/live warmup;
- persistence or webhook delivery failures encountered in operation;
- dynamic watchlist membership, additional feeds, options evidence or interfaces required by a
  named consumer.

Existing issues retain their own scope and decisions. The list does not authorize new storage,
providers, schemas, policy or dependencies. Use existing foundations until concrete behavior
requires improvement. Replay, backtesting, model training and speculative raw-data retention are
outside the current plan.

## Delivery

Use focused local tests and PR CI. Reach a practical live scenario quickly for runtime changes;
record failures and fix them in the relevant issue. Keep completed history in Git/PRs and current
implementation in [current status](../current-status.md).
