from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from nautilus_trader.adapters.interactive_brokers import (
    InteractiveBrokersExecutionClientFactory,
    MarketDataType,
    SymbologyMethod,
)

from markeitech.system import node as node_module
from markeitech.system.composition import StartupPrerequisites
from markeitech.system.config import load_system_config
from markeitech.system.node import (
    build_ib_data_client_config,
    build_ib_execution_client_config,
    build_live_risk_engine_config,
    build_system_node,
)


def test_maps_provider_boundary_to_installed_ib_config() -> None:
    root = Path(__file__).parents[2]
    config = load_system_config(root / "config/system.example.toml")

    data_config = build_ib_data_client_config(config)
    provider_config = data_config.instrument_provider

    assert data_config.market_data_type == MarketDataType.REALTIME
    assert data_config.use_regular_trading_hours is False
    assert data_config.batch_quotes is True
    assert data_config.ignore_quote_tick_size_updates is False
    assert data_config.handle_revised_bars is False
    assert provider_config.symbology_method == SymbologyMethod.SIMPLIFIED
    assert provider_config.convert_exchange_to_mic_venue is False
    assert {str(instrument_id) for instrument_id in provider_config.load_ids} == {
        "ESU6.CME",
        "NQU6.CME",
        "CLV6.NYMEX",
        "SPY.ARCA",
        "QQQ.NASDAQ",
        "^SPX.CBOE",
        "^VIX.CBOE",
    }


@pytest.mark.parametrize("execution_enabled", [False, True])
def test_builds_v2_node_without_connecting(tmp_path: Path, execution_enabled: bool) -> None:
    root = Path(__file__).parents[2]
    config = load_system_config(root / "config/system.example.toml")
    config = replace(
        config,
        ib=replace(config.ib, port=1),
        ib_execution=replace(
            config.ib_execution,
            enabled=execution_enabled,
            account_id="TEST-ACCOUNT",
        ),
        logging=replace(config.logging, directory=tmp_path),
    )

    node = build_system_node(
        config,
        StartupPrerequisites(run_id=uuid4(), operational_persistence_ready=True),
    )

    assert str(node.trader_id) == config.runtime.trader_id
    assert node.is_running is False


def test_execution_config_uses_shared_endpoint_timeouts_and_instrument_identity() -> None:
    root = Path(__file__).parents[2]
    config = load_system_config(root / "config/system.example.toml")
    config = replace(
        config,
        ib=replace(
            config.ib,
            host="192.0.2.1",
            port=1234,
            connection_timeout_seconds=12,
            request_timeout_seconds=13,
        ),
        ib_execution=replace(config.ib_execution, enabled=True, account_id="TEST-ACCOUNT"),
    )
    execution = build_ib_execution_client_config(config)
    data = build_ib_data_client_config(config)
    assert execution.host == data.host == "192.0.2.1"
    assert execution.port == data.port == 1234
    assert execution.connection_timeout == data.connection_timeout == 12
    assert execution.request_timeout == data.request_timeout == 13
    assert execution.client_id == 42
    assert execution.account_id == "TEST-ACCOUNT"
    assert execution.instrument_provider.load_ids == data.instrument_provider.load_ids
    assert (
        execution.instrument_provider.symbology_method == data.instrument_provider.symbology_method
    )
    assert (
        execution.instrument_provider.convert_exchange_to_mic_venue
        == data.instrument_provider.convert_exchange_to_mic_venue
    )


@pytest.mark.parametrize("bypass", [False, True])
def test_maps_risk_bypass(bypass: bool) -> None:
    root = Path(__file__).parents[2]
    config = load_system_config(root / "config/system.example.toml")
    config = replace(config, risk_engine=replace(config.risk_engine, bypass=bypass))
    assert build_live_risk_engine_config(config).bypass is bypass


@pytest.mark.parametrize("enabled", [False, True])
def test_registers_execution_client_and_risk_only_when_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    enabled: bool,
) -> None:
    config = load_system_config(Path(__file__).parents[2] / "config/system.example.toml")
    config = replace(
        config,
        ib_execution=replace(config.ib_execution, enabled=enabled, account_id="TEST-ACCOUNT"),
        logging=replace(config.logging, directory=tmp_path),
    )
    builder = MagicMock()
    for method in ("with_logging", "add_data_client", "with_risk_engine_config", "add_exec_client"):
        getattr(builder, method).return_value = builder
    node_factory = MagicMock()
    node_factory.builder.return_value = builder
    monkeypatch.setattr(node_module, "LiveNode", node_factory)

    node = build_system_node(
        config,
        StartupPrerequisites(run_id=uuid4(), operational_persistence_ready=True),
    )

    builder.add_data_client.assert_called_once()
    builder.build.assert_called_once_with()
    node.add_strategy.assert_not_called()
    node.run.assert_not_called()
    node.start.assert_not_called()
    if enabled:
        builder.with_risk_engine_config.assert_called_once()
        assert builder.with_risk_engine_config.call_args.args[0].bypass is False
        builder.add_exec_client.assert_called_once()
        name, factory, native_config = builder.add_exec_client.call_args.args
        assert name == "IB_EXECUTION"
        assert isinstance(factory, InteractiveBrokersExecutionClientFactory)
        assert native_config.account_id == "TEST-ACCOUNT"
        assert native_config.client_id != config.ib.client_id
    else:
        builder.with_risk_engine_config.assert_not_called()
        builder.add_exec_client.assert_not_called()
