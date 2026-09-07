# Gate 1A Native IB Observation Characterization

**Status:** Offline construction and source characterization complete for the exact evidence below;
native lifecycle and connected acceptance not run

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
are no additional numbered preparation stages. This section records a decision needed before an
executable observation harness can be selected; it does not mark Gate 1 complete.

### Installed Python Surface

On 2026-09-07, isolated introspection of the existing CPython `3.13.3` / Nautilus `2.0.0rc4`
environment verified the following named surfaces without constructing or starting a node:

| Surface | Verified installed limitation |
|---|---|
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

**Inference:** a plain Python callback harness using those inspected rc4 interfaces is not a
supported completion path for Gate 1. The evidence does not reject native client 1 construction,
all native integration approaches, or the provider's non-binding snapshot capability.

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
| Receive native reports in Python | Raw reconciliation topics and Python bus handler | Handler accepts only `PyMessage`; no named direct public ingress | Adapter raw reports include synthetic rows | Missing current Python bridge | Native report boundary, placement undecided | `DEFER` | Python-originated publish is a different path | Source inspection and installed-surface tests only |
| Observe untracked manual order updates | Native IB passive update stream | Unmapped status and blank-reference/unmapped open-order paths suppress output | Master-1 manual delivery unverified | Incomplete for named source cases | Native adapter | `DEFER` | A report bridge cannot recover events not emitted | Source inspection; paper coverage absent |
| Preserve fills and terminal recovery | Native fill/order/position reports | Account-filter mismatch; commission-gated output; no completed-order roster request | Provider history bounds require verification | Unresolved fidelity | Native adapter and future fact admission | `DEFER` | Positions/synthetic reports cannot reconstruct missing broker history | No connected acceptance |
| Prove no prohibited attempts | Native transport writes and observable lifecycle | No adequate Python interception seam established | TWS log receipt alone has bounded coverage | Audit boundary undecided | Required security consultation | `UNKNOWN` | Exact-role consultation could not launch | No accepted audit mechanism or run |

### Concrete Decision Before Harness Implementation

The smallest architectural candidate remains a repository-only proof harness outside `src/`,
with a narrow immutable observation boundary and unchanged ordinary data-only startup. Selecting
its native ingress and exact observation/audit contract remains open.

The next work is a bounded native compatibility proposal covering:

- a supported typed Rust-to-Python report ingress, or an explicitly reviewed native proof host;
- observation of untracked manual order status/open-order callbacks without claiming or binding
  orders for control;
- fill account normalization, commission completeness, terminal-order coverage, and report origin;
- exact request-audit coverage, failure handling, and downstream capability isolation; and
- the smallest dependency/native-source change, if one is required, with its maintenance and
  verification cost made explicit before adoption.

Read-only investigation remains within issue #45. These are candidate requirements, not an
approved patch, upgrade, Rust host, raw IB replacement, polling fallback, or new product schema.
The current evidence does not justify choosing between them. Present the concrete native change
and its consequences for Markeitect's decision before adopting it. Keep the work on this PR.

The architecture, IB-provider, and Nautilus consultations ran read-only. The required security
consultation could not launch because the host reported `agent thread limit reached`; no audit
design was accepted or substituted by the primary agent. Detailed lineage and capture/retention
consultations remain pending the native/audit boundary. A fresh task must restore the exact-role
coverage before those affected decisions or any real capture. This is an execution limitation of
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
