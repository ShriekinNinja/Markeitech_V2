"""Native Gate 1 order listener and offline-only IB composition.

This diagnostic tool is outside production startup. Building never starts the node
or contacts IB. Callback projections are not proof of provider delivery or a native
request audit. Only immutable snapshots belong on the downstream boundary.
"""

from __future__ import annotations

import argparse
import ipaddress
import math
import re
import time
from dataclasses import dataclass, field

from nautilus_trader import model
from nautilus_trader.adapters.interactive_brokers import (
    InteractiveBrokersExecutionClientConfig,
    InteractiveBrokersExecutionClientFactory,
    InteractiveBrokersInstrumentProviderConfig,
)
from nautilus_trader.common import Environment, LoggerConfig
from nautilus_trader.core import UUID4
from nautilus_trader.live import LiveExecutionEngineConfig, LiveNode
from nautilus_trader.trading import Strategy, StrategyConfig

Scalar = str | int | float | bool | None
_ORDER_EVENTS = (
    model.OrderInitialized, model.OrderSubmitted, model.OrderAccepted,
    model.OrderRejected, model.OrderUpdated, model.OrderCanceled, model.OrderExpired,
    model.OrderTriggered, model.OrderFilled, model.OrderFillVoided, model.OrderPendingUpdate,
    model.OrderPendingCancel, model.OrderModifyRejected, model.OrderCancelRejected,
)
_POSITION_EVENTS = (model.PositionOpened, model.PositionChanged, model.PositionClosed)
_NATIVE_SCALARS = (
    model.TraderId, model.StrategyId, model.InstrumentId, model.ClientOrderId,
    model.VenueOrderId, model.PositionId, model.TradeId, UUID4,
    model.Quantity, model.Price, model.Money, model.Currency,
    model.OrderSide, model.OrderType, model.PositionSide, model.LiquiditySide,
)
_FIELDS = (
    "event_id", "trader_id", "strategy_id", "instrument_id", "client_order_id",
    "venue_order_id", "trade_id", "position_id", "opening_order_id", "closing_order_id",
    "order_side", "order_type", "side", "entry", "quantity", "signed_qty", "price",
    "trigger_price", "last_qty", "last_px", "currency", "commission", "liquidity_side",
    "avg_px_open", "avg_px_close", "realized_pnl", "ts_event", "ts_init", "reconciliation",
    "is_quote_quantity", "correction_id", "voided_qty", "commission_voided", "is_reopened",
    "causation_id",
)


@dataclass(frozen=True)
class ListenerConfig:
    """Explicit diagnostic scope; account identity is never inferred or printed.

    Limits bound retained records and each copied scalar's UTF-8 bytes. Client 1
    is the previously characterized candidate. Environment verification is outside
    this offline tool. Empty native provider loads are deliberate construction-only
    settings; actual contract loading belongs to the later exact run package.
    """

    account_id: str = field(repr=False)
    account_alias: str
    instrument_ids: tuple[str, ...]
    host: str = "127.0.0.1"
    port: int = 1
    client_id: int = 1
    max_records: int = 256
    max_field_bytes: int = 256
    connection_timeout_seconds: int = 30
    request_timeout_seconds: int = 30

    def __post_init__(self) -> None:
        try:
            valid = (
                type(self.account_id) is str and 1 <= len(self.account_id) <= 128
                and type(self.account_alias) is str
                and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", self.account_alias) is not None
                and type(self.instrument_ids) is tuple and 1 <= len(self.instrument_ids) <= 32
                and all(type(x) is str and 1 <= len(x) <= 128 for x in self.instrument_ids)
                and len(set(self.instrument_ids)) == len(self.instrument_ids)
                and type(self.host) is str and ipaddress.ip_address(self.host).is_loopback
                and type(self.port) is int and 1 <= self.port <= 65535
                and type(self.client_id) is int and self.client_id == 1
                and type(self.max_records) is int and 1 <= self.max_records <= 4096
                and type(self.max_field_bytes) is int and 32 <= self.max_field_bytes <= 1024
                and type(self.connection_timeout_seconds) is int
                and 1 <= self.connection_timeout_seconds <= 60
                and type(self.request_timeout_seconds) is int
                and 1 <= self.request_timeout_seconds <= 60
            )
            if not valid:
                raise ValueError
            model.AccountId(self.account_id)
            for instrument_id in self.instrument_ids:
                model.InstrumentId.from_str(instrument_id)
        except (TypeError, ValueError):
            raise ValueError("Invalid offline listener configuration") from None


@dataclass(frozen=True)
class ListenerObservation:
    """Copied event projection, with local receipt time and explicit missingness.

    Native venue/trade IDs retain their native names, not invented IB API/permanent
    identity semantics. Position events are engine-derived lifecycle projections.
    Duplicate callback occurrences remain separate sequence-numbered observations.
    """

    sequence: int
    event_type: str
    origin: str
    account_alias: str
    received_ns: int
    values: tuple[tuple[str, Scalar], ...]
    absent_fields: tuple[str, ...]
    null_fields: tuple[str, ...]
    broker_origin: str = "unverified"
    account_environment: str = "unverified"


@dataclass(frozen=True)
class ListenerStatus:
    """Local collection counts; zero rejections does not prove upstream completeness."""

    retained: int
    rejected: int
    overflowed: int
    last_rejection: str | None


class OrderListenerStrategy(Strategy):
    """Receive native order/position callbacks without issuing order commands.

    The trusted composition owns this Strategy and its inherited native capabilities.
    Consumers receive only ``observations()`` and ``listener_status()`` results.
    Callback collection is intended for the native owner thread, not concurrent reads.
    """

    def __init__(self, config: ListenerConfig) -> None:
        super().__init__(StrategyConfig(
            strategy_id=model.StrategyId("OrderListener-001"),
            order_id_tag="001",
            external_order_claims=[model.InstrumentId.from_str(x) for x in config.instrument_ids],
            manage_contingent_orders=False,
            manage_gtd_expiry=False,
            manage_stop=False,
            log_events=False,
            log_commands=False,
        ))
        self._scope = config
        self._observations: list[ListenerObservation] = []
        self._rejected = 0
        self._overflowed = 0
        self._last_rejection: str | None = None

    def on_start(self) -> None:
        """No requests or order management on component startup."""

    def on_stop(self) -> None:
        """No order cancellation or cleanup actions on component stop."""

    def on_order_event(self, event: object) -> None:
        """Copy supported, explicitly scoped native order event fields."""
        self._receive(event, _ORDER_EVENTS, "strategy_order_projection")

    def on_position_event(self, event: object) -> None:
        """Copy engine-derived opened/changed/closed position event fields."""
        self._receive(event, _POSITION_EVENTS, "engine_position_lifecycle")

    def observations(self) -> tuple[ListenerObservation, ...]:
        """Return immutable snapshots without any native event or execution handle."""
        return tuple(self._observations)

    def listener_status(self) -> ListenerStatus:
        """Report local rejection/overflow rather than silently evicting observations."""
        return ListenerStatus(
            len(self._observations), self._rejected, self._overflowed, self._last_rejection,
        )

    def _scalar(self, value: object) -> Scalar:
        if value is None or type(value) in (bool, int):
            return value
        if type(value) is float and math.isfinite(value):
            return value
        if type(value) in _NATIVE_SCALARS:
            value = str(value)
        if type(value) is str and len(value.encode("utf-8")) <= self._scope.max_field_bytes:
            return value
        raise ValueError("Unsupported or oversized listener field")

    def _reject(self, reason: str) -> None:
        self._rejected += 1
        self._last_rejection = reason

    def _receive(self, event: object, supported: tuple[type, ...], origin: str) -> None:
        if type(event) not in supported:
            self._reject("unsupported_event")
            return
        account = getattr(event, "account_id", None)
        instrument = getattr(event, "instrument_id", None)
        if (
            type(account) is not model.AccountId or str(account) != self._scope.account_id
            or type(instrument) is not model.InstrumentId
            or str(instrument) not in self._scope.instrument_ids
        ):
            self._reject("missing_or_mismatched_identity")
            return
        if len(self._observations) >= self._scope.max_records:
            self._overflowed += 1
            return
        try:
            values = tuple((name, self._scalar(getattr(event, name, None))) for name in _FIELDS)
        except (TypeError, ValueError, AttributeError):
            self._reject("unsupported_or_oversized_field")
            return
        self._observations.append(ListenerObservation(
            sequence=len(self._observations) + 1,
            event_type=type(event).__name__,
            origin=origin,
            account_alias=self._scope.account_alias,
            received_ns=time.time_ns(),
            values=values,
            absent_fields=tuple(name for name in _FIELDS if not hasattr(event, name)),
            null_fields=tuple(
                name for name, value in values if value is None and hasattr(event, name)
            ),
        ))


def build_listener_node(config: ListenerConfig) -> tuple[LiveNode, OrderListenerStrategy]:
    """Compose the genuine native IB client and listener without starting either.

    Returned native objects belong to the trusted composition owner. This function
    grants no connected-run approval and implements no native request-audit facility.
    No cached state is loaded or persisted; missing orders are not synthesized by
    the engine. Adapter-generated synthetic reports can still exist on a future run.
    """
    execution_config = InteractiveBrokersExecutionClientConfig(
        host=config.host, port=config.port, client_id=config.client_id,
        account_id=config.account_id,
        connection_timeout=config.connection_timeout_seconds,
        request_timeout=config.request_timeout_seconds,
        fetch_all_open_orders=False,
        track_option_exercise_from_position_update=False,
        instrument_provider=InteractiveBrokersInstrumentProviderConfig(
            load_ids=set(), load_contracts=[],
        ),
    )
    engine_config = LiveExecutionEngineConfig(
        load_cache=False, reconciliation=True,
        reconciliation_instrument_ids=list(config.instrument_ids),
        filter_unclaimed_external_orders=False, filter_position_reports=False,
        generate_missing_orders=False,
    )
    node = (
        LiveNode.builder("Gate1OrderListener", model.TraderId("GATE1-001"), Environment.SANDBOX)
        .with_logging(LoggerConfig(bypass_logging=True))
        .with_exec_engine_config(engine_config)
        .add_exec_client(None, InteractiveBrokersExecutionClientFactory(), execution_config)
        .build()
    )
    listener = OrderListenerStrategy(config)
    node.add_strategy(listener)
    return node, listener


class _BuildOnlyParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.exit(2, "OFFLINE_LISTENER_ARGUMENTS_REJECTED\n")


def main() -> int:
    """Build only a synthetic composition; there is intentionally no connected CLI."""
    _BuildOnlyParser(
        description="Build the synthetic IB order listener offline.",
    ).parse_args()
    try:
        config = ListenerConfig(
            account_id="GATE1-SYNTHETIC", account_alias="synthetic",
            instrument_ids=("QQQ.NASDAQ",),
        )
        node, listener = build_listener_node(config)
        if node.is_running or listener.is_running() or not listener.is_ready():
            raise RuntimeError
    except Exception:
        print("OFFLINE_LISTENER_BUILD_FAILED")
        return 1
    print("OFFLINE_LISTENER_BUILT; NOT CONNECTED; ACCOUNT ENVIRONMENT UNVERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
