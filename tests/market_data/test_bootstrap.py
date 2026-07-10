from datetime import date
from typing import Any

import pytest
from markeitech.domain import (
    AnalysisProfile,
    InstrumentDataMode,
    InstrumentRegistryConfig,
    InstrumentRole,
    InstrumentRuntimeConfig,
    NQContractConfig,
)
from markeitech.market_data import (
    LIVE_NODE_START_CONFIRMATION,
    InteractiveBrokersConnectionConfig,
    MarketDataRuntimeConfig,
    build_live_node,
    build_livenode_bootstrap_summary,
    build_prepared_market_data_live_node,
    start_live_node,
)
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
        return "started"


def nq_contract() -> NQContractConfig:
    return NQContractConfig(
        expiry=date(2026, 9, 18),
        instrument_id="NQU6.CME",
        ib_last_trade_date_or_contract_month="20260918",
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
    actors: list[tuple[Any, Any]] = []

    def actor_factory(action_plan: Any, *, on_warmup_ready: Any) -> object:
        actors.append((action_plan, on_warmup_ready))
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
