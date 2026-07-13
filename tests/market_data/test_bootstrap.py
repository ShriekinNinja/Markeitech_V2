from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from markeitech.domain import (
    AnalysisProfile,
    InstrumentDataMode,
    InstrumentRegistryConfig,
    InstrumentRole,
    InstrumentRuntimeConfig,
    NQContractConfig,
    OneMinuteBar,
)
from markeitech.market_data import (
    LIVE_NODE_START_CONFIRMATION,
    InteractiveBrokersConnectionConfig,
    MarketDataRuntimeConfig,
    PersistenceManagedLiveNode,
    build_live_node,
    build_livenode_bootstrap_summary,
    build_prepared_market_data_live_node,
    start_live_node,
)
from markeitech.persistence import (
    PersistenceConfig,
    PersistenceRuntimeStatus,
    StartupRecoveryService,
)
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.enums import AggressorSide
from nautilus_trader.model.identifiers import InstrumentId, TradeId
from nautilus_trader.model.objects import Price, Quantity
from pydantic import ValidationError


class FakeNode:
    def __init__(self, *, config: Any) -> None:
        self.config = config
        self.started = False
        self.built = False
        self.trader = self
        self.actors: list[Any] = []
        self.data_client_factories: dict[str, type[Any]] = {}

    def add_actor(self, actor: Any) -> None:
        self.actors.append(actor)

    def add_data_client_factory(self, name: str, factory: type[Any]) -> None:
        self.data_client_factories[name] = factory

    def build(self) -> None:
        self.built = True

    def run(self) -> str:
        self.started = True
        for actor in self.actors:
            emit = getattr(actor, "emit", None)
            if emit is not None:
                emit()
        return "started"


def nq_contract() -> NQContractConfig:
    return NQContractConfig(
        expiry=date(2026, 9, 18),
        instrument_id="NQU6.CME",
        ib_last_trade_date_or_contract_month="20260918",
        calendar_id="CME_Equity",
        session_profile="full",
    )


def registry() -> InstrumentRegistryConfig:
    return InstrumentRegistryConfig(
        active_instrument_id="NQU6.CME",
        instruments=(
            InstrumentRuntimeConfig(
                contract=nq_contract(),
                role=InstrumentRole.ACTIVE,
                data_mode=InstrumentDataMode.TICK_BY_TICK,
                analysis_profile=AnalysisProfile.ACTIVE_TICK,
            ),
        ),
    )


def runtime_config(**overrides: object) -> MarketDataRuntimeConfig:
    values = {
        "instrument_registry": registry(),
        "ib": InteractiveBrokersConnectionConfig(read_only=True),
        "trader_id": "MARK-001",
    }
    values.update(overrides)
    return MarketDataRuntimeConfig(**values)


def persistence_config(tmp_path: Path) -> PersistenceConfig:
    return PersistenceConfig(
        catalog_path=tmp_path / "catalog",
        metadata_path=tmp_path / "metadata.sqlite3",
        journal_path=tmp_path / "journal",
        catalog_batch_size=10,
    )


def native_trade() -> TradeTick:
    return TradeTick(
        instrument_id=InstrumentId.from_str("NQU6.CME"),
        price=Price.from_str("20000.25"),
        size=Quantity.from_str("1"),
        aggressor_side=AggressorSide.BUYER,
        trade_id=TradeId("runtime-trade"),
        ts_event=1_786_360_120_000_000_000,
        ts_init=1_786_360_120_000_000_100,
    )


def completed_bar() -> OneMinuteBar:
    return OneMinuteBar(
        instrument_id="NQU6.CME",
        event_ts=datetime(2026, 8, 10, 11, 9, tzinfo=UTC),
        ts_init=datetime(2026, 8, 10, 11, 9, 0, 123456, tzinfo=UTC),
        event_ts_ns=1_786_360_140_000_000_000,
        ts_init_ns=1_786_360_140_123_456_789,
        open_ts=datetime(2026, 8, 10, 11, 8, tzinfo=UTC),
        close_ts=datetime(2026, 8, 10, 11, 9, tzinfo=UTC),
        open=Decimal("20000"),
        high=Decimal("20001"),
        low=Decimal("19999"),
        close=Decimal("20000.25"),
        volume=Decimal("1"),
        buy_volume=Decimal("0"),
        sell_volume=Decimal("0"),
        unknown_volume=Decimal("1"),
        source="ib",
    )


def test_bootstrap_summary_is_data_only_and_not_starting_by_default() -> None:
    summary = build_livenode_bootstrap_summary(runtime_config())

    assert summary.can_build_node is True
    assert summary.will_start_node is False
    assert summary.data_only is True
    assert summary.read_only_ib is True
    assert summary.execution_clients_enabled is False


def test_build_live_node_uses_node_factory_without_starting() -> None:
    node = build_live_node(runtime_config(), node_factory=FakeNode)

    assert isinstance(node, FakeNode)
    assert node.started is False
    assert str(node.config.trader_id) == "MARK-001"
    assert node.config.exec_clients == {}


def test_build_prepared_live_node_attaches_actor_and_builds_clients() -> None:
    actors: list[tuple[Any, Any, Any]] = []

    def actor_factory(
        action_plan: Any,
        *,
        on_warmup_ready: Any,
        market_context_engine: Any,
    ) -> object:
        actors.append((action_plan, on_warmup_ready, market_context_engine))
        return object()

    node = build_prepared_market_data_live_node(
        runtime_config(),
        node_factory=FakeNode,
        actor_factory=actor_factory,
        data_client_factory=type("FakeDataClientFactory", (), {}),
    )

    assert node.built is True
    assert node.started is False
    assert node.actors and node.actors[0] is not None
    assert node.data_client_factories.keys() == {"IB"}
    assert actors[0][0].active_instrument_id == "NQU6.CME"
    assert actors[0][2] is not None


def test_build_live_node_refuses_when_disabled_by_config() -> None:
    with pytest.raises(RuntimeError, match="construction is disabled"):
        build_live_node(runtime_config(build_nautilus_node=False), node_factory=FakeNode)


def test_runtime_config_rejects_start_without_manual_flag() -> None:
    with pytest.raises(ValidationError, match="manual_live_node_start"):
        runtime_config(run_live_node=True)


def test_start_live_node_refuses_when_run_disabled() -> None:
    node = FakeNode(config=None)

    with pytest.raises(RuntimeError, match="start is disabled"):
        start_live_node(runtime_config(), node, confirmation=LIVE_NODE_START_CONFIRMATION)

    assert node.started is False


def test_start_live_node_requires_confirmation_token() -> None:
    node = FakeNode(config=None)
    config = runtime_config(run_live_node=True, manual_live_node_start=True)

    with pytest.raises(RuntimeError, match="confirmation token"):
        start_live_node(config, node, confirmation="wrong")

    assert node.started is False


def test_start_live_node_calls_run_only_with_manual_confirmation() -> None:
    node = FakeNode(config=None)
    config = runtime_config(run_live_node=True, manual_live_node_start=True)

    result = start_live_node(config, node, confirmation=LIVE_NODE_START_CONFIRMATION)

    assert result == "started"
    assert node.started is True


def test_prepared_node_wires_and_flushes_persistence_runtime(tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    class EmittingActor:
        def __init__(self, action_plan: Any, **kwargs: Any) -> None:
            del action_plan
            captured.update(kwargs)

        def emit(self) -> None:
            captured["on_native_market_data_event"](native_trade())
            captured["on_market_data_event"](completed_bar())

    node = build_prepared_market_data_live_node(
        runtime_config(persistence=persistence_config(tmp_path)),
        node_factory=FakeNode,
        actor_factory=EmittingActor,
        data_client_factory=type("FakeDataClientFactory", (), {}),
    )

    assert isinstance(node, PersistenceManagedLiveNode)
    assert isinstance(captured["startup_recovery"], StartupRecoveryService)
    assert callable(captured["on_historical_bar"])
    assert node.persistence.status == PersistenceRuntimeStatus.CREATED
    assert node.run() == "started"
    assert node.persistence.status == PersistenceRuntimeStatus.STOPPED
    assert len(node.persistence.catalog.query_trade_ticks("NQU6.CME")) == 1
    assert len(node.persistence.catalog.query_one_minute_bars("NQU6.CME")) == 1
    assert node.persistence.ingress.snapshot.accepted_native_count == 1
    assert node.persistence.ingress.snapshot.accepted_bar_count == 1
