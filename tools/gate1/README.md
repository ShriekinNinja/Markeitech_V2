# Native order listener

This is the Gate 1 diagnostic component for observing native order and position events.
It lives outside ordinary Markeitech production startup. The command below builds the genuine
IB execution client and registers `OrderListenerStrategy` without starting or connecting them.

From the repository root, using the already provisioned rc4 Python environment:

```sh
.venv/bin/python -B tools/gate1/order_listener.py
```

Expected output:

```text
OFFLINE_LISTENER_BUILT; NOT CONNECTED; ACCOUNT ENVIRONMENT UNVERIFIED
```

The command uses synthetic account identity, loopback port 1 and an explicit QQQ instrument ID.
It accepts no account, connection or run arguments and reads no runtime configuration or secrets.
No provider contract is loaded or resolved by this build. Importing the module also does not build
or start anything. There is no connected-run entry point in this batch.

## Component

`OrderListenerStrategy` overrides aggregate `on_order_event` and `on_position_event` callbacks.
It copies available order, fill, fill-correction and position lifecycle fields into frozen
`ListenerObservation` records. It does not issue requests or order commands in its callbacks or
lifecycle hooks. Its native inherited execution capabilities remain inside the trusted composition;
consumers receive only immutable observation/status snapshots.

`observations()` preserves callback occurrences in arrival order, including duplicates. Each record
has a local sequence, receipt time, event type, configured account alias, origin label, selected
scalar values, and separate absent-property and present-null field lists. Native timestamps retain
their names; they are not relabeled as verified broker timestamps. Paper/live environment and direct
broker origin stay `unverified`. Position events are labeled `engine_position_lifecycle`.

The listener preserves native client/venue/trade/position identities without inventing IB API or
permanent-order ID mappings. It keeps missing commissions distinct from zero and retains the
`OrderUpdated.is_quote_quantity` unit flag. `OrderFillVoided` includes correction identity/quantity
and missing commission state. Free-text reasons, `info`, raw account ID, tags and native objects
are excluded from records.

A row is retained only when its native account ID exactly matches the supplied scope and its
instrument is explicitly listed. Missing identity is rejected, including `OrderInitialized` and
account-less updates. Other unsupported event types, including Denied/Emulated/Released, are
rejected. `listener_status()` reports rejection count and a fixed last-rejection reason without
payloads. Native `PositionAdjusted` is not delivered through these Strategy callbacks.

Record count and per-field UTF-8 bytes are configurable and bounded. When full, the listener
retains existing rows and increments `overflowed`; it never silently evicts. These are local
collection diagnostics, not proof that the provider supplied every event. Use the native owner
thread for callbacks and snapshot reads; cross-thread/live consumption is not established here.

## Native composition

`ListenerConfig` supplies an explicit account ID and display alias, exact instrument IDs, literal
loopback host, port, characterized client ID 1, timeouts and buffer limits. `build_listener_node`
creates `InteractiveBrokersExecutionClientConfig`, its native factory, execution-engine config and
`LiveNode`, then registers the real listener. Returned node/Strategy handles belong to the trusted
composition owner and are not downstream observation values.

Strategy management and event/command logging are disabled; node logging is bypassed. Engine
reconciliation is configured but never executed by this command; cache loading and missing-order
generation are disabled. The external-order filter stays false to avoid the characterized rc4
claim/filter problem. Instrument claims are local framework routing, not broker binding or proof
of account-limited acquisition. Empty provider loads are construction-only settings.

These settings are an inspectable offline candidate. They do not establish correct provider
contract resolution, runtime recovery, complete manual-TWS visibility or a native attempt audit.
Before a connected run, the exact account/settings/contracts, lifecycle, audit and capture package
still needs review and Markeitect's explicit authorization. See the
[Gate 1 evidence record](../../docs/reference/ib-observation-gate1.md).

## Verification

The dedicated test file exercises real native event objects through direct callback calls to test
projection, and builds the real client/listener in a bounded subprocess. Direct calls are synthetic
projection tests, not evidence of native order-event dispatch or IB delivery. The earlier native
signal-dispatch test remains separate. No test contacts TWS.
