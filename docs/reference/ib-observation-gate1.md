# Gate 1 Native IB Observation Evidence

**Status:** Native order-listener component and build-only IB composition implemented offline;
synthetic projection/construction and signal forwarding verified. Connected acceptance remains open.

**Current correction:** Python `Strategy` order/position callbacks are available in installed rc4.
The earlier raw-report investigation did not evaluate that separate path and did not establish a
need for a custom native bridge. The native-patch recommendation is withdrawn. See the
[corrected native decision](#corrected-decision-before-harness-implementation) for the current scope and remaining evidence.

**Repository baseline:** `ba7088a6302430a9b1acd8c55938536078a47bd1`

**Dependency baseline:** `nautilus_trader==2.0.0rc4`

This reference records the bounded Gate 1A evidence for evaluating NautilusTrader's native
Interactive Brokers execution path as a possible future source of broker observations. It is not
a production design or an activation record. Markeitech still composes only the IB data client and
has no broker-observation owner, execution client, trade lifecycle, or order-action path.

The candidate API connection is `client_id=1`. Markeitect reports that TWS has Master API Client
ID `1`; that user-owned setting was not inspected. The connection ID and the TWS Master setting
have different owners and meanings. Master `1` does not turn connection client `1` into IB's
special client `0`.

## Decision

Gate 1A supports continuing evaluation of the native adapter; it does not support activating it.

| Dimension | Gate 1A result |
|---|---|
| Native client-1 compiled construction | **VERIFIED OFFLINE** on the recorded macOS arm64 wheel |
| Native client-0 construction | **REJECTED BY PINNED CONSTRUCTOR**, specifically because `0` is a multiple of 1000 |
| Named source inventory | **INSPECTED** for the files and regions listed below |
| Current production composition | **VERIFIED DATA-ONLY** by an AST-based regression guard |
| Native startup or lifecycle | **NOT RUN** |
| Native network egress isolation | **NOT ESTABLISHED** |
| Runtime no-binding/no-order-action behavior | **NOT ESTABLISHED** |
| Manual TWS lifecycle coverage with user-reported Master `1` | **UNVERIFIED** |
| Connected paper probe | **NOT AUTHORIZED BY GATE 1A** |

Construction proves that the installed Python/Rust boundary accepts the configuration and creates
a `LiveNode`. It does not prove what the compiled adapter would send after `start`, `run`,
`run_async`, or `connect`, and it does not sandbox native syscalls. The tests therefore guard the
characterization fixture against explicit lifecycle/report calls but make no network-isolation
claim.

## Artifact Identity

The implementation checkout had no root `.venv`. An existing compatible Python 3.13 environment
was selected without synchronizing, installing, or changing dependencies. Public evidence is kept
portable; no machine-local interpreter path is recorded here.

| Artifact | Measured identity |
|---|---|
| Repository head | `ba7088a6302430a9b1acd8c55938536078a47bd1` |
| Python | CPython `3.13.3` |
| Platform | macOS `26.6.2`, arm64 |
| Installed distribution | `nautilus_trader 2.0.0rc4` |
| Locked macOS arm64 wheel | SHA-256 `d9a6a87baa5132d7b898b117e5e0ae5e00d7b3d96da6731091335ae6a76ea0cf` |
| Installed native extension | SHA-256 `8d3d1007b73bdb898e484b77efe3103e63d2fb9c617a6a492a373300b69749f9` |
| Installed IB Python export module | SHA-256 `11ccf4e9508f137f16ab406d2b5b48ff1b7c9a00ca6bf26c047cf6f8925bbed6` |
| Installed IB type stub | SHA-256 `edf80aacbf93888ad7f9b518f660e0b1f874263e16d5dcbe9c582d601cfec7f6` |
| Nautilus tag | Annotated `v2.0.0rc4` object `9e3bbeb68ec1d40ecc63655211f00ce70407ed1f`; peeled commit `a0400251110653b6d8ae6a9b5b89c4543fa85a2d` |
| Rust IB dependency | crates.io `ibapi 3.3.0`; Cargo checksum `fc5651f11bacdf138a1a910dc075c21e425912ff767e7f3e237b9fe14d9f3f76` |

The focused dependency test compares the root exact pin, `uv.lock`, installed distribution
metadata, and the fixed Gate 1A version. It also re-hashes the installed native extension, IB
export module, and type stub against their wheel `RECORD` entries. Missing file inventory, hash,
size, or installed artifact is a test failure. Platform wheel hashes remain in `uv.lock`; the test
does not pretend that one macOS hash applies to Linux or Windows.

The tagged source and installed wheel identify the same release, but this review did not reproduce
the wheel build. A matching tag/version is not proof that the published wheel is reproducible from
that source.

## Offline Construction Evidence

The focused test launches a bounded subprocess with:

- the genuine `InteractiveBrokersExecutionClientConfig` and
  `InteractiveBrokersExecutionClientFactory`;
- `LiveExecutionEngineConfig` and `LiveNodeBuilder.add_exec_client`;
- explicit synthetic account identity `GATE1A-SYNTHETIC`;
- client `1`, loopback host, a non-service synthetic port, and an empty instrument-provider load;
- `Environment.SANDBOX` and `LoggerConfig(bypass_logging=True)`; and
- no node/client lifecycle or report-generation call.

Client `1` constructed successfully and the built node reported `is_running is False`. Repeating
the same seam with client `0` failed before connection with the pinned validation:
`client_id` must not be a multiple of 1000 because order-ID partitioning uses
`client_id % 1000`. This is a client-0 regression case, not a blanket rejection of the native
adapter.

The source guard rejects explicit calls to start/run/connect, report generation, reconciliation,
disconnect, stop, or shutdown in the construction script. Adversarial fixtures demonstrate that
the guard fails on injected forbidden calls while allowing configuration-object construction. A
bounded timeout and nonzero child exit both fail with explicit diagnostics. This source guard does
not intercept Rust behavior or prove absence of native egress.

## Measured Public Configuration Contract

Installed rc4 produced these defaults:

| Field | Measured default | Evidence limit |
|---|---:|---|
| `client_id` | `1` | Connection identity only; not the TWS Master setting |
| `account_id` | `None` | The factory otherwise uses its native fallback; production must supply explicit identity |
| `fetch_all_open_orders` | `False` | Does not suppress the separately inspected startup `all_open_orders()` call |
| `track_option_exercise_from_position_update` | `False` | Disables that optional position-update path only |
| `host` | `127.0.0.1` | A default address is not a connection or paper/live proof |
| `port` | `4002` | A port does not establish account environment |
| `connection_timeout` | `300` seconds | Runtime behavior was not exercised |
| `request_timeout` | `60` seconds | Runtime behavior was not exercised |

The installed public execution config has no Master-client-ID, observation-only, read-only, or
read-only-API field. The separately installed Dockerized Gateway configuration has a field named
`read_only_api`; that is not an execution-client capability guarantee and was not used here.

Tagged `config.rs` describes `fetch_all_open_orders` as choosing `reqAllOpenOrders` versus
`reqOpenOrders`, but the inspected rc4 execution source only logs the field and calls
`all_open_orders()` in the identified startup/report/query paths regardless of its default. This
is a source/documentation inconsistency for later resolution. It is not evidence of connected
provider behavior.

## Exact Source Set

All Nautilus paths below are at peeled commit
`a0400251110653b6d8ae6a9b5b89c4543fa85a2d` from tag `v2.0.0rc4`.

| Source | SHA-256 |
|---|---|
| `crates/adapters/interactive_brokers/src/config.rs` | `262aa42098af97f81cd22438f744fde82be7d18935d3b811d96643099409155f` |
| `crates/adapters/interactive_brokers/src/factories.rs` | `97c5098d84f03d3ee7cfc7382c200fe0048f19f82998c413bcda417887ae6e6a` |
| `crates/adapters/interactive_brokers/src/execution/core.rs` | `432036955ccb66f11f89e73bcada01569e2e969d792ced6c7baa06dd19268d12` |
| `crates/adapters/interactive_brokers/src/execution/core_updates.rs` | `d3eefd07a800a0be3642bd7fe18fb2e44fde81896bdf8213218b665a29e20027` |
| `crates/adapters/interactive_brokers/src/execution/parse.rs` | `8af6cbded28e3fed1e6d980a44197390448d0f6aae0854d25aa54a44fb6548b4` |
| `crates/live/src/node/mod.rs` | `655cd17d480dced84dac0ed67064924ed307c3717e678124a241b94948795abe` |
| `crates/live/src/execution/manager.rs` | `68cdce4ae8e854f21443a431d18441bfc4d9798bf228b2185abc78fcb2dafade` |
| `Cargo.lock` | `cf6ed1b45f399490a94e3fc72ec8802d4c7bee7c2ccedfca77cb4bd2b16f770e` |

The named `ibapi 3.3.0` transport source was inspected at its `v3.3.0` tag:

| Source | SHA-256 |
|---|---|
| `src/transport/async.rs` | `8a765ff3cc3f6e9b86054461261286532985f8f117668daedf77b4dfbe8ab040` |
| `src/orders/async.rs` | `e70fc62cc16ac52758cb694debef01384fdfb1b26cfd0e6496c195baf7ae07e2` |
| `src/accounts/async.rs` | `3bf855e24866c743d6d8c09de5bf91a8a1f3d710c0588c3eb15f8797c2771357` |
| `src/client/async.rs` | `4357d09cb34b46ca04c249a14411d6ea30d67651794e6d65ed3a503e67122485` |

## Construction, Startup, Request, And Shutdown Inventory

`INSPECTED` means the named source region was read. It does not mean the code was executed or that
the provider effect was measured.

| Region and source | Trigger and outbound behavior | Scope and origin | Disposition and limit |
|---|---|---|---|
| Config, `config.rs:143-175` | Supplies the defaults above. | Local configuration object. | **INSPECTED**; no Master/read-only/observation-only execution field. |
| Factory, `factories.rs:130-216` | Resolves explicit account identity, creates the instrument provider and `ExecutionClientCore`, then calls the native constructor. | Named execution client and one account ID. | **INSPECTED** and exercised through `LiveNodeBuilder.add_exec_client`; no lifecycle call. |
| Constructor, `core.rs:252-297` | Validates the modulo-1000 client partition, substitutes the explicit account, and allocates local task/maps/caches. | Client and account local state. | **INSPECTED** and exercised for clients 1/0; no provider request found in this constructor. |
| Node startup, `node/mod.rs:344-470` and `1003-1285` | Connects data clients first, connects execution clients, waits for engines, requests mass status, reconciles, then starts the trader. | Every configured execution client. | **INSPECTED, NOT RUN**. Construction does not traverse this path. |
| Execution connect, `core.rs:598-803` | `get_or_connect`, provider initialization, `next_valid_order_id()` (`RequestIds`), `all_open_orders()` (`RequestAllOpenOrders`) for the order-ID baseline, passive `order_update_stream()`, account summary, initial positions, PnL, and optional position-update tracking. | Configured client ID and account, except provider/account calls whose exact TWS accessible-account behavior needs connected evidence. | **INSPECTED, NOT RUN**. The all-open-orders baseline occurs independently of the logged `fetch_all_open_orders` value. |
| Passive update stream, `core_updates.rs:24-370` | `order_update_stream()` registers a local receiver for routed `OrderStatus`, `ExecutionData`, `CommissionReport`, and `OpenOrder` messages; the inspected function encodes no `RequestOpenOrders`, `RequestAllOpenOrders`, or `RequestAutoOpenOrders`. | Messages delivered to the connected API client; exact TWS/Master coverage unknown. | **INSPECTED, NOT RUN**. Local receiver registration is not a provider subscription and does not prove future manual-order delivery. |
| Order reports, `core.rs:824-1057` | `all_open_orders()` / `RequestAllOpenOrders`; with `open_only=False`, also `positions()` / `RequestPositions` and may create filled market/FOK order reports for residual position quantity. | Order rows are filtered with `raw_ib_account_code`; position rows by raw account code. | **INSPECTED, NOT RUN**. Residual-position reports are synthetic reconciliation state, not an observed order or fill. |
| Fill reports, `core.rs:1059-1151` | `executions(filter)` / execution request; pairs execution rows with commission rows and skips pending executions lacking a matching commission report. | The filter uses `self.core.account_id.to_string()` rather than the raw-account normalization used by order/position reports. | **INSPECTED, NOT RUN**. Record as a possible account-filter defect; no provider failure was measured. |
| Position reports, `core.rs:1152-1276` | `positions()` / `RequestPositions`; may emit an instrument-specific flat report when the requested instrument has no returned position. | Raw configured account comparison; instrument ID resolution through the provider. | **INSPECTED, NOT RUN**. Position reports do not establish a specific order, fill, or thesis. |
| Mass status, `core.rs:1277-1333` | Concurrently generates order, fill, and position reports and combines them in `ExecutionMassStatus`. | Native client, account, venue, and requested lookback. | **INSPECTED, NOT RUN**. The aggregate can mix provider-derived and synthetic reports. |
| Startup reconciliation, `node/mod.rs:792-940`; manager `manager.rs:632-1252` | Requests mass status, publishes raw report topics, adjusts/reconciles reports, creates local external-order state when allowed, and initializes cache/portfolio state. | Configured execution clients and admitted reports. | **INSPECTED, NOT RUN**. Local external-order materialization/registration is not IB order binding, but it is derived mutable local state and must not be mislabeled as direct provider observation. |
| Continuous reconciliation, `manager.rs:1990-3290`; node maintenance loop `node/mod.rs:1344-1800` | Bulk/targeted order, fill, and position report checks can generate reconciliation events and inferred fills/orders. | Cache state, client coverage, configured filters/lookbacks/retries. | **INSPECTED, NOT RUN**. Exact runtime ordering, omissions, and recovery remain unknown. |
| Transport reconnect, `ibapi src/transport/async.rs:307-458` | On a connection error, calls transport `reconnect()`, marks connected, and resets request/order/execution channels; failure requests shutdown. | One underlying transport/message bus. | **INSPECTED, NOT RUN**. No inspected automatic full mass reconciliation, subscription restoration, or gap-recovery proof follows from transport reconnection alone. |
| Disconnect, `core.rs:804-822`, `440-474`; `node/mod.rs:2280-2330` | Node shutdown disconnects clients; the IB client begins task shutdown, drops its shared-client handle, waits for tasks, and marks the core disconnected. | Node clients and local task groups/shared connection handle. | **INSPECTED, NOT RUN**. Provider-side completion and shared-handle behavior need lifecycle evidence. |

The installed adapter also contains submit, modify, cancel, exercise, and related execution
methods. Their presence is why construction cannot be treated as observation-only capability and
why future downstream code must receive immutable facts rather than an execution client or mutable
order object. Gate 1A did not call these methods and did not add them to production.

## IB Request Semantics Revalidated

Current official IB documentation distinguishes the following:

- [`reqOpenOrders`](https://www.interactivebrokers.com/docs/tws-api/doc/order-management/requesting-currently-active-orders/api-clients-orders)
  returns active orders submitted by the same API client. When invoked by client `0`, it also
  binds existing manual TWS orders; it is not generally a binding request for every client.
- [`reqAllOpenOrders`](https://www.interactivebrokers.com/docs/tws-api/doc/order-management/requesting-currently-active-orders/all-submitted-orders)
  returns a one-time snapshot of current open orders in associated accounts and does not create a
  future-order subscription. IB's current page does not label that snapshot as a bind operation.
- [`reqAutoOpenOrders`](https://www.interactivebrokers.com/docs/tws-api/doc/order-management/requesting-currently-active-orders/manually-submitted-tws-orders)
  is restricted to client `0`; `true` associates and assigns API IDs to future manual TWS orders.
- [`orderBound`](https://www.interactivebrokers.com/docs/tws-api/doc/order-management/requesting-currently-active-orders/order-binding-notification)
  is the response to an API bind-order-control message.
- [TWS API settings](https://www.interactivebrokers.com/docs/tws-api/protobuf/api-settings-config)
  separately define `readOnlyApi`, automatic open-order download, binding-ID behavior, and
  `masterClientId`. A settings checkbox is not evidence that a particular adapter call graph is
  safe.
- [Client ID 0 and Master Client ID](https://www.interactivebrokers.com/docs/tws-api/doc/order-management/client-id-0-and-the-master-client-id)
  describes Master visibility and client-0 special behavior separately. The user-reported Master
  `1` setting has not been verified, and its manual TWS lifecycle coverage remains unknown.

The current [Nautilus rc4 Python API](https://nautechsystems.github.io/nautilus_docs/python-api-nightly/adapters/interactive_brokers.html)
lists the measured execution config fields and factory but does not establish the runtime
no-control property needed by Markeitech.

## Report Fidelity And Admission Limits

The public rc4 report signatures and tagged parser establish the following structural facts:

- `ExecutionMassStatus` identifies native client, account, venue, report ID, and initialization
  time, then contains order/fill/position report collections.
- `OrderStatusReport` preserves account, instrument, venue order ID, side/type/time-in-force,
  status, quantities, selected prices, and local report times. The parser prefers IB `perm_id` as
  `PERM-<id>` for `venue_order_id`, otherwise uses the API order ID. It may include a normalized
  `order_ref` as `client_order_id`. It does not expose separate raw `perm_id`, connection client
  ID, or a provider event timestamp for the order-status snapshot.
- `FillReport` preserves account, instrument, venue order identity, IB execution ID as trade ID,
  side, last quantity/price, commission, parsed execution event time, and receive/init time. The
  current parser sets no venue position ID and cannot establish the trader's thesis or paper/live
  environment by itself.
- `PositionStatusReport` preserves account, instrument, side, quantity, optional average open
  price, and report times. The inspected IB path sets no venue position ID. A position report does
  not identify the contributing broker orders/fills.

Provider-originated rows, parser projections, residual-position synthetic order reports, flat
position responses, execution-manager adjustments, inferred reconciliation fills/orders, and
cache state are distinct evidence classes. A future broker-observation owner must preserve at
least account alias and verified environment, source/client identity, contract/instrument,
provider order/permanent/execution identifiers when available, direction and quantities, event
versus receive time, report/snapshot boundary, revision, reconciliation origin, and
missing/duplicate/conflict state. It must never fill missing broker identity from an imagined
trade or infer paper/live from port, prefix, `Environment.SANDBOX`, or `Environment.LIVE`.

Exact production placement, sanitized schema, persistence, retention, and downstream access are
not decided here. The accepted requirement remains one narrow owner publishing immutable
fact-only observations while hiding native clients and mutable order handles.

## Production Composition Guard

The Gate 1A test parses every production Python file under `src/` and rejects exact imports or
qualified references to the native IB execution config/factory, `add_exec_client` registration,
and named Nautilus submit/modify/cancel command producers. Adversarial fixtures cover direct,
aliased, and qualified imports and execution registration. The guard deliberately ignores generic
uses of words such as `execution`, `reconcile`, and `close`.

This proves only that the current Python composition remains data-only at this head. It cannot
prove isolation of future Sir Loke, Discord, policy, broker-observation, or trade-lifecycle
components which do not yet exist.

## Verification

The following offline hierarchy was used with the pre-existing compatible interpreter and this
checkout's `src` selected:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  <verified-python> -B -m pytest -p no:cacheprovider -q \
  tests/system/test_gate1a_native_ib_offline.py \
  tests/system/test_node.py::test_maps_provider_boundary_to_installed_ib_config \
  tests/system/test_v3_es_minimal_config.py
PYTHONPATH=src <verified-python> -B -m markeitech verify all
git diff --check
```

Focused result: `26 passed`. Complete offline result: Ruff passed, then `723 passed, 2 deselected`.
The changed-document link check and `git diff --check` also passed. No PostgreSQL, IB/TWS, Discord,
model, fake server, or other connected path was run.

## Conditional Gate 1 Paper Protocol

This protocol is design only. It is not executable code and does not authorize connection.

Before a paper run, separately approve the exact startup/recovery/disconnect behavior and an
actual outbound-request audit method. Resolve the `fetch_all_open_orders` inconsistency and the
fill-filter account-normalization concern, decide how synthetic/reconciliation state will be
admitted, and complete the required provenance/retention review for any captured facts.

Record the exact repository and native artifact, TWS build/API version, verified paper account and
accessible-account scope, non-secret account alias, connection client `1`, separately inspected
Master `1`, read-only API setting, automatic-download/association settings, contract/session
identity, UTC clock relationship, configuration digest, and audit completeness. Neither a port nor
Master status proves account environment or manual coverage.

With Markeitect performing every broker mutation manually, compare one preexisting manual TWS
order with a new post-connect manual order. Exercise only the approved manual changes, partial and
complete fills, cancellation/replacement, scale changes, closure, and bounded recovery cases.
Correlate audited outbound requests, TWS logs, callbacks, order/permanent/execution identity,
binding changes, and manual actions. Absence of a callback does not prove absence of an attempted
request. Unobserved races and partials remain unaccepted.

The allowlist must name each permitted observation request. Prohibit submission, modification,
cancellation, global cancellation, replacement, exercise, close, client-0 binding requests,
automatic manual-order association, and compensating order cleanup. A rejected prohibited request
still fails the no-attempt requirement.

Abort on a wrong/live account, unapproved setting or request, attributable binding/control change,
resubmission, modification, cancellation, audit loss, synthetic state represented as observation,
or unbounded recovery. Disconnect the observer without altering orders; Markeitect handles any
remaining paper orders manually.

Even a successful session would prove only its recorded paper scope. It would not authorize live
money, implement Sir Loke, complete full Gate 1 automatically, or create order authority.

## Remaining Gate

Gate 1A ends at offline characterization. Before production broker observation can be designed or
activated, Markeitect must review this evidence and separately authorize the bounded paper probe
after the source concerns and outbound-audit method are resolved. Full Gate 1 remains open until
that connected evidence is accepted.

## Gate 1 Completion Work: Native Ingress Decision

PR #44 merged at `72e324b7fff5b4a1816bc529d2e8f8eab84918d7`. The remaining work is tracked in
[issue #45](https://github.com/ShriekinNinja/Markeitech_V2/issues/45) as one Gate 1 completion PR,
including offline preparation, separately authorized paper testing, fixes, and acceptance. There
are no additional numbered preparation stages. The original raw-report investigation below is
bounded evidence, corrected by the Strategy findings; it does not mark Gate 1 complete.

### Installed Python Surface

On 2026-09-07, isolated introspection of the existing CPython `3.13.3` / Nautilus `2.0.0rc4`
environment verified the following named surfaces without constructing or starting a node:

| Surface | Verified installed contract |
|---|---|
| `Strategy` | Has aggregate and specific order/position callbacks, and `publish_signal`. `LiveNode.add_strategy` registers a Python subclass offline. Native dispatch and manual TWS delivery are not exercised by this construction proof. |
| `DataActor` | No `msgbus`, `on_report`, `on_order_status_report`, `on_fill_report`, `on_position_status_report`, or `on_order_event` member. |
| `LiveNode` | No `msgbus`, `execution_engine`, `get_execution_client`, `generate_mass_status`, or `add_stream_processor` member. |
| `LiveNodeBuilder` | No `add_stream_processor` member. |
| `InteractiveBrokersExecutionClientFactory` | No public Python `create` method. Native builder construction remains available. |
| IB Python adapter module | Does not export `InteractiveBrokersExecutionClient`. |
| Python execution module | Does not export `ExecutionEngine` for a native reconciliation reproduction. |

The version-bound regression is
[`test_gate1_native_observation_surface.py`](../../tests/system/test_gate1_native_observation_surface.py).
It checks these exact interfaces. It does not prove that every alternative native integration is
impossible, and it must be reviewed if the dependency changes.

The [nightly events guide](https://nautilustrader.io/docs/nightly/concepts/events/) directs Python
execution-event consumers to Strategy callbacks, with signals for actor consumers. Installed rc4
exports those callbacks. Exact rc4
[`strategy.rs:439`](https://github.com/nautechsystems/nautilus_trader/blob/a0400251110653b6d8ae6a9b5b89c4543fa85a2d/crates/trading/src/python/strategy.rs#L439)
converts native order events to Python objects before calling `on_order_event`; the same file's
specific fill and position dispatchers also convert native values. This is a separate mechanism
from the generic `PyMessage` handler below. Source presence establishes the implementation path,
not measured end-to-end delivery on the installed wheel.

### Native Source Limits

The following findings are **INSPECTED SOURCE**, not measured connected delivery failures. Source
references are fixed to rc4 commit `a0400251110653b6d8ae6a9b5b89c4543fa85a2d`:

1. The Python message-bus callable handler accepts only `PyMessage`. A native Rust report passed
   to that handler takes its non-`PyMessage` error branch instead of invoking the Python callback.
   See [`common/src/python/msgbus.rs:285-335`](https://github.com/nautechsystems/nautilus_trader/blob/a0400251110653b6d8ae6a9b5b89c4543fa85a2d/crates/common/src/python/msgbus.rs#L285).
   The file was retrieved directly at that commit and matched the inspected archive, SHA-256
   `4f74602e8ef23ab1be4765f4f53826092a6266da3556840cfebea8aa465130be`.
   Native report topics therefore do not by themselves establish a Python observation ingress.
   Publishing a report from Python is not a reproduction of this limitation: that path wraps the
   Python object in `PyMessage`, changing the dispatch path being tested.
2. The IB live order-status handler returns without emitting an observation when the incoming API
   order ID is absent from its `venue_order_id_map`. The `OpenOrder` path likewise has no generic
   observation fallback when the normalized order reference is empty and no map entry exists.
   See [`core_updates.rs:284-370`](https://github.com/nautechsystems/nautilus_trader/blob/a0400251110653b6d8ae6a9b5b89c4543fa85a2d/crates/adapters/interactive_brokers/src/execution/core_updates.rs#L284)
   and [the unknown-order return](https://github.com/nautechsystems/nautilus_trader/blob/a0400251110653b6d8ae6a9b5b89c4543fa85a2d/crates/adapters/interactive_brokers/src/execution/core_updates.rs#L479).
   The file hash is recorded in the original source inventory above. This makes untracked manual
   order coverage a separate problem from transporting an already-created report to Python.
3. The inspected order-status report implementation requests open orders; `open_only=False` adds
   position-based synthetic residual reports. It does not request the provider's completed-order
   roster. The existing fill-account normalization and commission-pairing concerns also remain
   unresolved. A report-bus extension alone would not close these adapter-fidelity questions.

**Correction:** the generic report-handler limitation cannot reject Python observation generally.
Strategy event dispatch was omitted from the earlier assessment. Whether the required manual TWS
events reach a suitable Strategy configuration remains unverified. The adapter findings above
remain source-level concerns; they do not establish that every native configuration fails.

### Provider And Documentation Limits

Official IB sources refreshed on 2026-09-07 continue to distinguish
[Master visibility from client-0 manual TWS behavior](https://www.interactivebrokers.com/docs/tws-api/doc/order-management/client-id-0-and-the-master-client-id).
The [all-open-orders request](https://www.interactivebrokers.com/docs/tws-api/doc/order-management/requesting-currently-active-orders/all-submitted-orders)
is a snapshot, not a subscription. No continuing manual TWS lifecycle guarantee for Master 1 was
established. `reqCompletedOrders(apiOnly=False)` is documented to include TWS orders in the
[completed-order request](https://www.interactivebrokers.com/docs/tws-api/doc/order-management/retrieving-completed-orders/requesting-completed-orders);
that provider capability is not evidence that the pinned adapter exposes it.

IB's execution-history descriptions differ: the
[request page](https://www.interactivebrokers.com/docs/tws-api/doc/order-management/execution-details/request-execution-details)
says current day since midnight, the
[introduction](https://www.interactivebrokers.com/docs/tws-api/doc/order-management/execution-details/introduction)
describes a TWS Trade Log setting permitting up to seven days while limiting Gateway to the
current day, and the
[callback page](https://www.interactivebrokers.com/docs/tws-api/doc/order-management/execution-details/receive-execution-details)
says the last 24 hours. Exact build/settings/filter and time-boundary evidence must govern any
recovery claim; no cross-midnight recovery guarantee is accepted.

The nightly guide/API roots were refreshed on 2026-09-07. The current
[live API page](https://nautechsystems.github.io/nautilus_docs/python-api-nightly/live.html)
describes an `add_stream_processor` interface absent from installed rc4. It is comparison
evidence, not authority to call that interface on the current pin. That method processes external
ingress; its existence would not by itself establish raw native report delivery. A candidate
version or native extension needs its own source, artifact, adapter, and acceptance review.

### Native Alignment Decision Matrix

| Requirement | Native candidate | Installed-version evidence | Adapter/provider evidence | Semantic fit | Proposed owner | Decision | Rejection or extension rationale | Acceptance evidence |
|---|---|---|---|---|---|---|---|---|
| Construct one native connection | IB config/factory and node builder | Existing rc4 client-1 construction passes | Provider behavior unmeasured | Fits construction only | Nautilus | `USE_NATIVE` for construction | No replacement justified | Existing Gate 1A tests |
| Receive raw native reports through a generic Python handler | Raw reconciliation topics and Python bus handler | Handler accepts only `PyMessage` | Adapter raw reports include synthetic rows | Limited to this handler | Native report boundary, placement undecided | `DEFER` | Does not reject Strategy event callbacks | Source inspection and installed-surface tests only |
| Receive execution events in Python | Strategy callbacks and native registration | Callbacks exist; subclass registers offline; rc4 source converts native events | Manual TWS delivery not measured | Relevant alternative; requirement coverage unverified | Native Strategy; product boundary undecided | `UNKNOWN` | No custom bridge justified by the earlier omitted-candidate review | Positive interface/registration tests; dispatch proof pending |
| Observe untracked manual order updates | Native IB passive update stream | Unmapped status and blank-reference/unmapped open-order paths suppress output | Master-1 manual delivery unverified | Incomplete for named source cases | Native adapter | `DEFER` | A report bridge cannot recover events not emitted | Source inspection; paper coverage absent |
| Preserve fills and terminal recovery | Native fill/order/position reports | Account-filter mismatch; commission-gated output; no completed-order roster request | Provider history bounds require verification | Unresolved fidelity | Native adapter and future fact admission | `DEFER` | Positions/synthetic reports cannot reconstruct missing broker history | No connected acceptance |
| Prove no prohibited attempts | Native transport writes and observable lifecycle | No adequate Python interception seam established | TWS log receipt alone has bounded coverage | Audit boundary undecided | Native lifecycle and observation boundary | `UNKNOWN` | Security review completed for the earlier proposal; Strategy callbacks do not establish an audit | No accepted audit mechanism or run |

### Corrected Decision Before Harness Implementation

Evaluate the existing Strategy event path before any native bridge, fork, or dependency proposal.
The proof remains outside ordinary production startup and uses the existing dependency. A minimal
offline registration example is implemented in the characterization tests; it is not a connected
observation harness or a dispatch test. Resolve actual event routing and the required observation
boundary with exact-role review before selecting runtime configuration. See the
[corrected native decision](#corrected-decision-before-harness-implementation). Any remaining native limitation needs its own
precise evidence; it does not automatically activate the withdrawn patch specification.

The architecture, IB-provider, and Nautilus consultations ran read-only. At the initial PR head,
the required security consultation could not launch because the host reported
`agent thread limit reached`; no audit design was accepted or substituted by the primary agent.
Detailed lineage and capture/retention consultations were then pending the native/audit boundary.
A fresh task needed to restore exact-role coverage before those affected decisions or any real
capture. The continuation below records that
restoration and the later correction to the resulting proposal. The earlier failure was an execution limitation of
the consultation, not proof that the security role is absent from the installed plugin.

No native lifecycle, broker connection, fake TWS server, raw data capture, production execution
wiring, dependency change, or persistence change occurred in this follow-up. Gate 1 remains open.

### Follow-up Offline Verification

Using the same pre-existing Python `3.13.3` / Nautilus `2.0.0rc4` environment without installing or
synchronizing dependencies:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  <verified-python> -B -m pytest -p no:cacheprovider -q \
  tests/system/test_gate1_native_observation_surface.py \
  tests/system/test_gate1a_native_ib_offline.py \
  tests/system/test_node.py::test_maps_provider_boundary_to_installed_ib_config \
  tests/system/test_v3_es_minimal_config.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  <verified-python> -B -m markeitech verify all
git diff --check
```

Focused result: `33 passed`, including the existing dependency/installed-`RECORD` integrity check.
Full offline verification: Ruff passed; `730 passed, 2 deselected`. All `27` relative link paths
across the three changed Markdown documents resolved, and `git diff --check` passed. These results
verify the characterized Python surface and repository consistency, not compiled report delivery,
provider coverage, security isolation, a working observation harness, or Gate 1 acceptance.

## Implemented Order Listener And Native IB Composition

Markeitect subsequently explicitly requested an actual order-listener actor/Strategy in this PR.
That authorizes the component and offline native composition; it does not authorize a TWS run.
The audit gap below is a connected-acceptance gate, not a prohibition on implementing or building
the listener offline.

[`tools/gate1/order_listener.py`](../../tools/gate1/order_listener.py) now contains:

- `OrderListenerStrategy`, with aggregate order and position callbacks and no order commands;
- frozen scalar observations with native field names, local sequence/receipt time, separate absent
  and null fields, explicit unverified environment/broker origin, and engine-position provenance;
- exact account/instrument checks, bounded record/field sizes, and visible rejection/overflow;
- `InteractiveBrokersExecutionClientConfig`, the genuine native factory, execution engine and node
  composition, with the Strategy registered for explicitly configured instrument claims; and
- a synthetic build-only command with no lifecycle, provider request, real capture or run option.

The [tool guide](../../tools/gate1/README.md) documents use and limitations. The native execution
client is now present in actual implementation code, rather than only the earlier construction
test. Normal `src/markeitech` startup remains data-only.

The dedicated [listener tests](../../tests/system/test_gate1_order_listener.py) use genuine native
order/fill/position event objects with synthetic values. They directly exercise callback projection
for acceptance, updates, cancellation, fills/corrections and opened/changed/closed positions;
they do not claim to drive the native execution-event dispatcher. Tests preserve quantity units,
missing commissions, immutable snapshots after native Position mutation, repeated occurrences,
identity rejection, overflow and sanitized failure output. A subprocess builds the genuine native
IB client plus listener and verifies that the node/listener remain stopped and the listener is
ready. No provider contract loading occurs.

Native and security delta reviews identified and resolved two concrete issues: the updated-order
quantity unit flag is copied, and unknown CLI arguments are rejected without echoing their values.
The correction projection excludes free-text reason/info. The same exact-role advisors were reused;
no new advisor slots, dependency changes or control infrastructure were introduced.

**Offline validation:** 32 dedicated listener tests; 66 focused Gate 1 tests including the existing
native-surface and Gate 1A files. The tool and tests pass Ruff. Full verification results are
reported on the published PR head. Native request/audit execution, contract resolution, manual-TWS
delivery, real capture and recovery remain unmeasured. Keep the PR draft until acceptance completes.

## Native Strategy Continuation: Measured Scope And Remaining Gaps

This section records the preceding forwarding-only batch; the implemented listener above supersedes
its implementation status. Its measured limits and source findings remain applicable.

On 2026-09-07, continuation from `ea4296e016315b41f0e215d821cdd8cf22eaa893` preserved the four
incoming uncommitted edits, including both approved native-first rule additions. The smallest
supported implementation in this batch is the executable offline native-forwarding example in
[`test_gate1_native_observation_surface.py`](../../tests/system/test_gate1_native_observation_surface.py),
not an IB observation harness. No provider or production component was added.

### Measured Native Forwarding

`test_gate1_strategy_signal_reaches_actor_through_native_dispatch` constructs a node with no
provider, registers a Strategy and DataActor, subscribes the actor after registration, and starts
only those two components. A synthetic immutable string passes through
`Strategy.publish_signal` to the actor's native-dispatched `on_signal`; the test checks the copied
value and timestamp, stops both components, and verifies that the node never ran. Neither order
nor position callback is invoked. The subprocess is bounded to 15 seconds.

Explicit no-op `on_start`/`on_stop` hooks and subscribing outside `on_start` permit this direct
component-lifecycle fixture on the installed wheel. The advisor measured borrow errors in other
direct-start arrangements. This does not establish failure or success of node-managed startup.
The test is a forwarding demonstration, not a capability sandbox or an attempt-audit mechanism.

The exact rc4 source separately establishes typed execution routing:

- [`trader.rs:461`](https://github.com/nautechsystems/nautilus_trader/blob/a0400251110653b6d8ae6a9b5b89c4543fa85a2d/crates/system/src/trader.rs#L461)
  installs strategy-specific order and position subscriptions using typed native handlers.
- [`strategy.rs:439`](https://github.com/nautechsystems/nautilus_trader/blob/a0400251110653b6d8ae6a9b5b89c4543fa85a2d/crates/trading/src/python/strategy.rs#L439)
  converts native order values for Python callbacks. Native handlers require a running Strategy;
  position lifecycle callbacks exclude `PositionAdjusted` and describe engine-derived state.
- [`msgbus.rs:695`](https://github.com/nautechsystems/nautilus_trader/blob/a0400251110653b6d8ae6a9b5b89c4543fa85a2d/crates/common/src/python/msgbus.rs#L695)
  wraps generic Python publication in `PyMessage`. It is not a public typed execution-event
  injection seam. Directly calling a Python callback would not close the missing dispatch proof.

The [nightly events guide](https://nautilustrader.io/docs/nightly/concepts/events/) was freshly
retrieved and agrees on Strategy callbacks and actor signals. Installed wheel behavior governs
the measured example; changing nightly documentation is not an exact artifact test.

### Native Candidate And Explicit Dispositions

Use native Strategy/event facilities as the candidate; no custom execution-event bridge is
justified. Exact-instrument external claims and engine reconciliation are candidates for later
configuration review, not selected paper settings. Internal claims assign framework ownership;
they are distinct from IB binding and do not prove the complete lifecycle free of broker actions.

| Requirement or concern | Current evidence and disposition for the Strategy path |
|---|---|
| Native Python execution ingress | Callbacks, registration and typed native source are available. Installed order/position dispatch remains **UNMEASURED**; only signal forwarding is **MEASURED**. |
| External-order routing | Source supports instrument-specific claims. In `manager.rs:4909`, a claim selects the strategy; `4932` then filters non-synthetic external orders whenever `filter_unclaimed_external=True`, without checking that claim. Do not use this flag as a proven claimed-only filter or account-scope control. |
| Blank-reference/unmapped manual updates | Adapter bookkeeping can suppress these before Strategy dispatch. Claims downstream do not establish recovery of those callbacks. **UNRESOLVED** for required manual lifecycle coverage. |
| Fill account identity | Fill requests use the full Nautilus account string while order/position reporting normalizes it. **SOURCE CONCERN**, provider effect unmeasured; no complete-fill claim. |
| Commission-dependent fills | Missing paired commissions can suppress fill reports. **UNRESOLVED**; neither zero commission nor an empty result proves completeness. |
| Reconciliation origin | Residual orders, inferred fills and flat reports remain synthetic/derived even when delivered to a claimed Strategy. Position lifecycle callbacks are engine state, not raw broker position reports. |
| Terminal history and recovery | Open orders/current positions do not reconstruct every missed change or closing fill. Receive loss, reconnect epochs and history horizons remain **UNACCEPTED**. |
| Immutable downstream facts | Scalar native forwarding is demonstrated. A complete bounded observation projection preserving required raw identities/origins has **NOT BEEN IMPLEMENTED**; discarded upstream fields cannot be recreated by a serializer. |
| No prohibited attempts and complete writes | Disabled management flags leave execution APIs reachable on Strategy/native internals. No adequate compiled attempt/write audit has been established. **BLOCKS CONNECTED HARNESS ACCEPTANCE** independently of signal forwarding. |
| Provider delivery and capture | No IB/TWS run or real capture. Prior capture/rights and exact-run approval gates remain applicable before any real evidence acquisition. |

The external-claim filter finding is source-bound to the recorded manager hash
`68cdce4ae8e854f21443a431d18441bfc4d9798bf228b2185abc78fcb2dafade`, independently checked again
by the advisor. It is not a measured rejection of every native configuration. The source extract
has no Git metadata; matching inspected file hashes does not prove whole-build reproducibility.

### Exact Audit Blocker And Next Decision

The security consultation accepts the new fixture's bounded offline scope and returns
**`REQUIRED_HANDOFF`** for an executable connected candidate. Primary Kite independently inspected
these decisive source cases:

- [`strategy/mod.rs:158`](https://github.com/nautechsystems/nautilus_trader/blob/a0400251110653b6d8ae6a9b5b89c4543fa85a2d/crates/trading/src/strategy/mod.rs#L158)
  rejects an invalid submission state before generating an event. The upstream regression
  [`test_submit_order_rejects_non_initialized_without_events`](https://github.com/nautechsystems/nautilus_trader/blob/a0400251110653b6d8ae6a9b5b89c4543fa85a2d/crates/trading/src/strategy/mod.rs#L3529)
  asserts that no event was emitted. This Rust test was inspected, not executed here.
- The existing IB core readiness/cache checks and ibapi pre-encode validation can likewise reject
  before a transmitted frame. A callback, command-only log or wire trace cannot observe every
  such attempt, including direct base-method/internal native calls outside a Python override.
- ibapi's [`recorder.rs:59`](https://github.com/wboayue/rust-ibapi/blob/v3.3.0/src/transport/recorder.rs#L59)
  warns on recording failure without failing the caller. Its records are not a fail-closed audit.
  Handshake/StartApi and asynchronous Drop writes remain the separate paths identified below.

The smallest sufficient logical control boundary needs **both** an audit before every reachable
prohibited action can reject or encode, and a correlated fail-closed audit of every native write
through startup, operation, reconnect and shutdown. No inspected public rc4 configuration or
callback supplies both. This is a precise missing facility, not a rejection of Strategy event
observation or a recommendation to restore the former bridge/patch proposal.

The next consequential decision is a bounded **audit-facility feasibility/change scope** for
those two control points. Any proposed implementation must identify its exact entry points,
coverage, audit-loss behavior, artifact/build changes and maintenance cost before adoption. Keep
native Strategy as the observation candidate. No fork, dependency upgrade, proxy, new bridge or
broad patch has been selected or shown sufficient. Deferring the connected harness pending a
sufficient facility is the supported alternative; relaxing issue #45 is not implicit authority.
Manual-event fidelity and capture/recovery gates remain independent even if audit is solved.

### Advisor Capacity And Evidence

The installed router/dispatch policy `2026-09-07-v7` was used with its matching installed scripts;
those files matched the current `master` checkout. The PR's older plugin source was not upgraded
incidentally. Both approved native-first rule edits remain exactly as handed off; the source-only
skill supplement was supplied explicitly to the Nautilus advisor without claiming cache refresh.

The full selected plan was preflighted before launch: host capacity was four including the
primary, inventory initially contained only the primary, and no close operation was callable.
Two required roles fit the three free slots. Native consultation preceded security because the
latter needed its concrete candidate. Fresh inventory and `DISPATCH_READY` preceded each
serialized launch; the completed native advisor still occupied a slot for the security launch.
No capacity refusal, retry, role substitution or unrelated task closure occurred.

| Exact role | Owned question | Requested allocation | Decision ID |
|---|---|---|---|
| `markeitech_nautilus_advisor` | Installed Strategy routing and smallest public offline demonstration | `gpt-6-astra`, `high` | `8797b032944f0bade934c18130106e27e6aecc2ba8921f48810b400089abc900` |
| `markeitech_security_tool_boundary_advisor` | Actual candidate capability exposure and sufficient native attempt/write audit | `gpt-6-astra`, `high` | `9d36adf151d2240c58647ad5562cfe0b3cb7efc33b10c0545e0b1761d6d42a41` |

Both exact roles returned, and completion receipts validated with `EXECUTION_UNVERIFIED` because
host-effective model/effort metadata was unavailable. That label concerns allocation metadata;
it neither invalidates inspected evidence nor establishes effective tool isolation. Primary Kite
independently ran the forwarding fixture and checked the decisive routing/audit source findings.

The advisor could not retrieve the nightly live API page; primary subsequently retrieved it via
verified-TLS curl (SHA-256 `196901c0dd1cd7316933fc60c2b70118e8f6c665ed3ade1f6406e44ec3065a4f`).
The linked reconciliation guide was unavailable through the documentation tool. No connected
reconciliation configuration is selected from incomplete documentation or from nightly defaults.

### Continuation Verification

Using the pre-existing CPython 3.13.3 / Nautilus rc4 environment without installation or sync:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  <verified-python> -B -m pytest -p no:cacheprovider -q \
  tests/system/test_gate1_native_observation_surface.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  PYTEST_ADDOPTS='-p no:cacheprovider' <verified-python> -B -m markeitech verify all
python3 -B plugins/kite/scripts/validate_advisor_council.py
python3 -B -m unittest discover -s plugins/kite/tests -q
git diff --check
```

Results: **11 surface tests passed**; full verification passed Ruff and **734 tests, 2 deselected**;
Kite council validation passed and **54 plugin tests passed**. Ruff used a temporary cache because
the existing PR worktree is outside the task's default writable root. No dependency, production
configuration, persistence, IDE state, node/provider lifecycle, IB/TWS connection, or real capture
changed. The two PostgreSQL tests remain CI-owned acceptance. Read CI for the published head.

## Prior Proposal: Withdrawn, Evidence Retained

The continuation at PR head `ea4296e016315b41f0e215d821cdd8cf22eaa893` prematurely
recommended a patched rc4 proof artifact and custom native ingress. That recommendation is
**withdrawn**: it omitted the separate native Strategy execution-event path. No patch, dependency
change, Rust host, or new observation architecture was approved or implemented. The latest
[PR #46 handoff](https://github.com/ShriekinNinja/Markeitech_V2/pull/46#issuecomment-5572003557)
supersedes the old PR description and implementation proposal.

The old patch specification, proposed resource limits, and patch-dependent implementation sequence
remain recoverable at that Git revision. They are removed from current recommendations. The
source findings and bounded security, lineage, and capture consultations below remain evidence
for evaluating the actual native candidate; they do not make every former proposed control or
source change mandatory. Each applicable gap needs an explicit disposition before a paper run.

### Additional Source Evidence And Audit Coverage

The published [ibapi 3.3.0 crate](https://crates.io/crates/ibapi/3.3.0) was downloaded for source
inspection only. Its archive SHA-256 is
`fc5651f11bacdf138a1a910dc075c21e425912ff767e7f3e237b9fe14d9f3f76`, matching the inspected Cargo lock.
The previously recorded transport source also matches the published crate. No source was built,
installed, or connected. Additional Nautilus files were retrieved at the exact rc4 commit and
matched the inspected source archive:

| Exact source path | SHA-256 |
|---|---|
| Nautilus `crates/adapters/interactive_brokers/src/execution/account.rs` | `2d9b488c67819d8c575184e96684ddb28066cbcac434a27eb81436705065c324` |
| Nautilus `crates/adapters/interactive_brokers/src/providers/instruments.rs` | `bec7480c13dd51502c10ee01e285ada65ff18bbe5b96c9a54baaaad7554e15b0` |
| Nautilus `crates/adapters/interactive_brokers/src/common/shared_client.rs` | `7c02c98bd39a7a3eba42c36deb72d450c66d8dc0983eb31129d02e51dbf6944c` |
| ibapi `src/connection/async.rs` | `81cd8690bcd3d3c5593efbfafc7e146083726cc20989fda3145c5c3b4e0e04a0` |
| ibapi `src/transport/async/io.rs` | `81c0bcffdfc01cbe6855614c84cc270c5b89d140e59555e7837dcbc2a2cb91e7` |
| ibapi `src/subscriptions/async.rs` | `3497221f888592652b3e13d1a9b22d8ebeaeaa216b048a9f4a9d38c5119e9fe0` |
| ibapi `src/messages.rs` | `a3f74b91beedf1ccfd6aa4a67199205f3af04b9e7ab751a7fd03793813024884` |

The following are inspected-source findings and proposed controls, not executed audit guarantees:

- Nautilus `execution/core.rs` action entry points include `submit_order`, `submit_order_list`,
  `modify_order`, `cancel_order`, `cancel_all_orders` and `batch_cancel_orders`. Audit/reject at
  entry, before readiness, cache lookup or target validation. Otherwise an attempted action may
  disappear before encoding. Reachable direct ibapi action methods need the same treatment.
  An allowed observation request used as a prelude to modification has a prohibited parent intent.
- ibapi `transport/async.rs:688-769` routes all six inspected message-bus send/cancel variants to
  `AsyncConnection::write_message`. This is not a universal sink: `connection/async.rs:209-252`
  sends handshake directly to `socket.write_all`, and StartApi through `write_raw`; reconnect
  repeats connection establishment. The inspected production async sink is
  `AsyncTcpSocket::write_all` in `transport/async/io.rs:68-71`. A candidate audit must cover both
  typed intent and every actual write, with explicit handshake/protobuf protocol states.
- `subscriptions/async.rs:421-475` encodes cancellation and may spawn an asynchronous send on
  Drop. Audit the cleanup intent before encoding and keep supervision/audit alive until all owned
  cleanup tasks finish or the observer transport is closed. The inner subscription's local map
  cleanup is not the outer subscription's provider cancellation.
- Both `transport/async.rs:140-176` and `subscriptions/async.rs`'s `poll_next` can skip lag errors.
  Complete-interval claims require loss visibility at those seams; no patch is selected here.
- `transport/async/io.rs:58` allocates the advertised incoming frame length without a bound at
  that inspected seam. Bound the frame before allocation and the decoder/queues before admission.
- The built-in recorder is controlled by `IBAPI_RECORDING_DIR`; logging/recording can contain raw
  requests, responses, account configuration and PnL. Recorder errors that only warn do not meet
  audit-failure requirements. Scrub inherited recording/debug configuration, disable uncontrolled
  raw logging, and test native diagnostics as well as final record serialization.

Audit records must distinguish attempted, policy-denied, encoded, write-attempted, write-completed,
write-failed/partial, provider-rejected and unknown outcomes. A socket write is not provider
acceptance. Any prohibited action attempt fails the run even if denied locally or by TWS.
Failure to record, sequence loss, buffer exhaustion or an unrecognized protocol message makes the
evidence invalid and closes observer egress; no further broker request is justified as cleanup.
Correlate records by run, process/connection epoch, client, lifecycle intent, request and sequence.
TWS logs and the operator's manual action ledger corroborate observer traffic; they do not replace
the native attempt audit. Hashes detect changes to identified artifacts, not malicious tampering
by a process able to rewrite the evidence; effective isolation needs its own validation.

### Proposed Request Inventory And Remaining Closure

This is the named candidate inventory for review, not an executable allowlist or connection
authorization. Numeric values below are the `ibapi 3.3.0` outgoing enum identities; protocol framing
and protobuf encoding must be validated against the approved TWS/API version, not guessed from a
leading byte. Defaults do not confer authority to send a request.

| Lifecycle/capability | Named candidate request | Required bound/disposition |
|---|---|---|
| Establish and reconnect | Raw handshake; `StartApi` (71) | Exact endpoint/client, protocol state and connection epoch. Audit both raw paths; initial account/next-ID replies are responses, not invented outgoing requests. |
| Native order-ID bootstrap | `RequestIds` (8) | Existing startup requirement only; obtaining an ID grants no order action. |
| Startup/open-order reports | `RequestAllOpenOrders` (16) | Explicit non-binding snapshot purpose. `fetch_all_open_orders=False` is not used as a safety control; do not substitute `RequestOpenOrders`. |
| Instrument initialization and report contract resolution | `RequestContractData` (9), conditionally `CancelContractData` (106) | Explicit contracts and bounded lookups; prohibit broad chain expansion, wildcard discovery and disk-cache writes in the proof profile. Reconcile actual drop behavior/server support in compiled tests. |
| Account initialization/query | `RequestAccountSummary` (62), `CancelAccountSummary` (63) | Native group is `All`, followed by local filtering; all accessible-account acquisition needs explicit scope. Preserve end/error state. |
| Initial/current positions and reports | `RequestPositions` (61), `CancelPositions` (64) | Accessible-account scope precedes filtering. Cancellation releases an observation subscription, never a broker order. |
| Native PnL startup | `RequestPnL` (92), `CancelPnL` (93) | Existing startup behavior, account-scoped. Decide explicit admission or a reviewed proof-only suppression; do not silently allow extra capture. |
| Executions/recovery | `RequestExecutions` (7) | Normalized account, exact filters and verified history horizon. Execution completion and commission completion remain distinct. |
| Proposed completed-order recovery | `RequestCompletedOrders` (99) | New adapter request, `apiOnly=False`, bounded invocation and explicit completion/horizon. No claim that it is already called by rc4. |
| Passive update receiver | No outgoing subscription in inspected `order_update_stream()` | Local receiver registration does not establish TWS delivery; preserve callback gaps and unsupported cases. |
| Reconciliation, retry, disconnect and Drop | Only the individually admitted requests above, with approved causal purpose | Reconciliation origins remain explicit; scheduled recovery/cleanup may not outlive the audit or authorized run. |

Default-deny everything else. Explicitly prohibit `PlaceOrder` (3), `CancelOrder` (4),
`RequestGlobalCancel` (58), `ExerciseOptions` (21), `RequestAutoOpenOrders` (15), and
`RequestOpenOrders` (5) in this candidate, as well as native modify/replace/close/what-if paths,
binding, automatic association, and compensating order cleanup. Client 0 remains outside the
candidate. Broad FA/settings changes, market data, options-chain requests, scanners and arbitrary
callbacks/configuration are not admitted incidentally.

The selected executable composition still needs a transitive inventory from configuration through
native call sites, encoders, background tasks, protocol framing and the write sink. In particular,
provider loading/cache behavior, automatic reconnection callbacks, concurrent report requests and
subscription lifetimes must match the selected native configuration. Unknown paths must fail closed; the table
cannot be treated as proof that the unmodified adapter only sends these requests. Complete this
closure for the selected path and before presenting an exact connected run package.

### Evidence Lineage And Completeness Requirements

The lineage consultation supports preparing the following contract and returns **STOP** for
claims of complete manual lifecycle, gap-free delivery, closure or recovery on current evidence.
This is a proof-envelope proposal, not an accepted trade-episode or persistence schema.

| Evidence dimension | Required preservation/admission rule |
|---|---|
| Run and source | Repository/native artifact/configuration/schema identity; provider, independently verified paper environment and account alias; connection client and separately verified Master setting; process, connection and request epochs. |
| Raw identity before normalization | Privately preserve account code, conId and contract fields, API order ID, permanent ID, source client ID, execution ID, order reference and their presence/validity. A normalized `PERM-...` identifier cannot replace the separate source fields. Arbitrary reference text stays inside the protected boundary. |
| Quantities and state | Preserve raw status, side, quantity, fill/remaining quantity, prices, position and commission fields with units/currency and parse validity. Keep missing commission distinct from zero. A position change or flat synthetic report cannot identify a particular closing fill. |
| Clocks | Preserve provider timestamp text/format/timezone where supplied, parsed UTC and parse outcome, local receive UTC and monotonic time/sequence. Local report timestamps are not provider event times. Ambiguous provider time remains unresolved. |
| Snapshot coverage | Exact request kind/filter/account scope/time horizon; begin, typed provider end marker, error/timeout and counts. OpenOrderEnd, execution end, PositionEnd and completed-order end are distinct. No end marker or an unrelated marker cannot establish an empty complete snapshot. |
| Evidence origin | Distinguish passive callback, requested provider row, parser projection, residual synthetic order, synthetic flat response, inferred reconciliation and cache state. Never deduplicate source evidence with a synthetic object as if they were the same fact. |
| Missingness and loss | Preserve lag/drop/decode/mapping failures and pending/unmatched records, including losses before Python ingress. Loss invalidates the affected interval even when the final queue has no visible gap. |
| Identity joins and revisions | Account/client/connection-scoped API IDs; preserve permanent/execution identities separately. Record duplicate occurrences, conflicting values and correction candidates without overwriting evidence or assuming an execution-ID suffix defines correction semantics. Keep one-to-many or ambiguous joins explicit. |
| Recovery and closure | Fence old epochs; keep reconnect overlap, missing intervals and snapshot horizons. Current position recovery does not reconstruct missed modifications, fills or trader intent. Closure requires the admitted order/fill/position evidence for its named scope, not absence from an open-order list. |

Synthetic native fixtures must include blank/normalized-colliding references, unmapped callbacks,
status-before-openOrder, cross-account/client ID collisions, missing/late/conflicting commissions,
correction-like execution IDs, source/synthetic collisions, wrong/missing/late snapshot terminators,
zero rows with and without a valid terminator, more than the native 1,024-message broadcast capacity,
reconnect overlap and unrecoverable gaps, ambiguous clocks, and unresolved one-to-many joins.
Record failures explicitly rather than repairing them with provider or trader assumptions.
No schema validator or fixture suite can establish delivery of manual TWS callbacks in a real run.
The exact provider scope/uniqueness of identifiers, execution-correction targeting, callback and
terminator guarantees, and history/timezone boundaries remain required IB-provider handoffs before
those semantic conclusions. Until supplied, preserve candidate joins and correction-like IDs as
unresolved. Unknown status/side/type/time-in-force values and timestamp parse assumptions must also
survive before native parser defaults can make them appear observed.

### Capture, Retention And Publication Requirements

The exact-role licensing/provenance consultation returns **`REQUIRED_HANDOFF` for real capture**.
Public synthetic preparation can proceed. The account's contracting entity, accepted agreements,
paper-user relationship, accessible-account roster and applicable subscriptions/terms were not
inspected. Public terms and software licenses do not establish account-specific rights. The
advisor requires a private rights/qualified-legal-review disposition before the first real
capture, including incidental market data, retention and any real-derived publication. This
remains a pre-capture gate; private account documents are not needed for the present proposal.

| Evidence class | Proposed handling; requires approval before real use |
|---|---|
| Public source/patch identities, field definitions, request names, synthetic fixtures and offline results | Suitable for this PR, preserving relevant software notices. Never populate fixtures from real captured rows. |
| Native callback and audit evidence | Local private capture only after its exact source, fields, account scope, purpose, recipients, byte cap and expiry are approved. Preserve required identifiers privately; expose aliases through the reviewed projection. |
| TWS logs, screenshots and wire traces | Exceptional corroboration only where needed for the acceptance claim. They may contain other accounts or market data; an order-observation purpose does not make the whole artifact safe. Disable optional market-data logging. |
| Real-derived hashes, counts, timestamps, sanitized manifests and verdicts | Keep private until the rights disposition permits an exact public subset. Redaction, hashing and pseudonymization do not establish redistribution rights. |

The capture proposal must identify the IB entity/account owner and authorized operator, all
accounts exposed to the username, relevant agreement versions, subscriptions and market-data
classification where applicable, TWS/API build/settings, source and filter inventory, local
processors/recipients, and retention/deletion responsibilities. Every accessible account must
be covered by the approved purpose or collection must be narrowed through a reviewed mechanism;
filtering after collection does not close this gate. No real evidence enters Git, Codex/model
prompts, Discord, cloud sync, telemetry or support uploads under the current authorization.

For retention review, the advisor proposes raw corroboration lasting at most 24 hours after
operator review and a private sanitized provenance/verdict lasting at most 90 days or until
superseded, whichever comes first. These are conditional ceilings, not selected policy or
permission to collect/delete: exact agreements and audit duties may require different limits.
The capture package must have an absolute expiry so an unfinished review cannot retain evidence
indefinitely. No retention interval or byte cap is approved by this record.

Preserve the distinction between software and data rights: Nautilus's
[exact-tag LGPL license](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc4/LICENSE)
and [ibapi's MIT license](https://github.com/wboayue/rust-ibapi/blob/v3.3.0/LICENSE) govern the
native source/distribution. They grant no IB account or exchange-data rights. The
[IB API software terms](https://interactivebrokers.github.io/) require an applicability review
if covered official API Code is included; do not assume the independent Rust implementation has
the same license. [IB logging documentation](https://www.interactivebrokers.com/docs/tws-api/doc/troubleshooting-support/log-files/introduction)
describes operational logging, not public reuse rights or an approved retention policy.

### Remaining Exact-Run Gate

Complete feasible offline evaluation of the selected native configuration and component before
preparing a connected package. Any demonstrated need for a dependency, native, provider-owner,
or architecture change still requires Markeitect's concrete decision. The former patch proposal
is not that decision, and an unavailable audit seam does not by itself select a broad patch.

A run package must identify the reviewed repository and binary, configuration, complete lifecycle
request inventory, actual audit mechanism, TWS/API settings, independently verified paper and
accessible-account scope, private capture handling, time/resource limits, manual scenarios,
recovery and abort procedure. It must demonstrate audit of prohibited attempts as well as sends,
including startup, recovery and shutdown. An unknown or missing prerequisite is a blocker, not an
empty approved value. Do not issue prohibited requests to TWS to test rejection.

Markeitect performs every paper-order mutation. Required manual lifecycle, identity, fidelity,
no-action/no-binding and recovery evidence remain issue #45's acceptance criteria. Gate 1 stays
open and PR #46 stays draft until that evidence is accepted. No IB/TWS run or real capture is
authorized by offline implementation or verification.

### Historical Consultation Continuation And Verification

The initial architecture, IB-provider and Nautilus findings above were reused against the
unchanged starting head and exact dependency identities, as requested. This continuation restored
the exact security, data-quality/lineage and vendor-data licensing/provenance roles. All three
ran read-only; their conditional recommendations and capture/acceptance handoffs remain gates.
No advisor granted architecture, dependency, legal, provider or release approval.

Before dispatch, the task's agent tree contained only the primary. The host declared four slots;
the three remaining slots were reserved for these consultations. No close-agent operation was
exposed, and completed advisors remained visible. No capacity was inferred from completion,
archival, or interruption, and no unrelated task was closed. This is task-tree capacity evidence,
not a claim of a global host census.

Route mode was `MULTI`: security owned compiled attempt/write controls; lineage owned source
identity/completeness; licensing owned conditional real-capture and public-evidence rights.
Security and lineage proceeded independently from the reused native findings. Licensing's
initial public/synthetic scope check ran independently because it admitted no real use; final
capture synthesis incorporates both roles' broader-account and loss findings. This scoped
dependency choice does not waive either role before real-capture advice.

| Exact role | Validated requested allocation | Allocation decision ID |
|---|---|---|
| `markeitech_security_tool_boundary_advisor` | `gpt-6-astra`, `high` | `0da94d78d525dbe5beae0641b8638c48bb1e579a9853fb1a2c56e95163329123` |
| `markeitech_data_quality_lineage_advisor` | `gpt-5.6-sol`, `xhigh` | `e5d84b312e9ec19c6351fe186bfcd6a7f66fefe85b57a783e365b90ea5cca7ec` |
| `markeitech_vendor_data_licensing_provenance_advisor` | `gpt-5.6-sol`, `high` | `ed90cda78943608fd45b1275599226550bd938b5bf63fd7c04ae4762006eeeed` |

The source/installed Kite packages matched. Resolver requests and completion receipts were
validated under policy `2026-09-05-v6`. Host-effective model/effort metadata was absent, so receipt
status remains `EXECUTION_UNVERIFIED`; this does not negate the returned consultation, establish
allocation effectiveness, or prove effective read-only tool isolation.

The existing focused command above passed **33 tests**. `markeitech verify all` passed Ruff and
**730 tests, 2 deselected**, using pre-existing CPython 3.13.3/Nautilus rc4 without sync or install.
The three changed documents' **29 relative link targets** resolve, and `git diff --check` passes.
The continuation changes only those documents; earlier characterization tests are preserved.
No native lifecycle, fake server, IB/TWS/account access, real capture, broker action, database,
Discord or model runtime was run. CI must be read for the published PR head; local checks are
offline evidence only.
