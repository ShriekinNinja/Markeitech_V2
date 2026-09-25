from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from nautilus_trader.adapters.interactive_brokers import (
    MarketDataType,
    SymbologyMethod,
)

from markeitech.system.composition import StartupPrerequisites
from markeitech.system.config import load_system_config
from markeitech.system.node import (
    build_ib_data_client_config,
    build_ib_execution_client_config,
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
        "ESZ6.CME",
        "NQZ6.CME",
        "CLX6.NYMEX",
        "SPY.ARCA",
        "QQQ.NASDAQ",
        "^SPX.CBOE",
        "^VIX.CBOE",
    }


def test_builds_v2_node_without_connecting() -> None:
    root = Path(__file__).parents[2]
    config = load_system_config(root / "config/system.example.toml")

    node = build_system_node(
        config,
        StartupPrerequisites(run_id=uuid4(), operational_persistence_ready=True),
    )

    assert str(node.trader_id) == config.runtime.trader_id
    assert node.is_running is False
    assert build_ib_execution_client_config(config) is None


def test_builds_native_ib_execution_client_without_connecting() -> None:
    root = Path(__file__).parents[2]
    config = load_system_config(root / "config/system.example.toml")
    config = replace(config, ib=replace(config.ib, execution_account_id="DU123456"))

    execution_config = build_ib_execution_client_config(config)
    assert execution_config is not None
    assert execution_config.account_id == "DU123456"
    assert execution_config.client_id == config.ib.execution_client_id
    assert execution_config.client_id != build_ib_data_client_config(config).client_id
    assert execution_config.track_option_exercise_from_position_update is False
    assert execution_config.fetch_all_open_orders is True
    assert execution_config.host == config.ib.host
    assert execution_config.port == config.ib.port
    assert execution_config.connection_timeout == config.ib.connection_timeout_seconds
    assert execution_config.request_timeout == config.ib.request_timeout_seconds
    assert execution_config.instrument_provider.load_ids == (
        build_ib_data_client_config(config).instrument_provider.load_ids
    )

    alternate = replace(
        config,
        ib=replace(
            config.ib,
            execution_client_id=7,
            track_option_exercise_from_position_update=True,
            fetch_all_open_orders=False,
        ),
    )
    alternate_config = build_ib_execution_client_config(alternate)
    assert alternate_config is not None
    assert alternate_config.client_id == 7
    assert alternate_config.track_option_exercise_from_position_update is True
    assert alternate_config.fetch_all_open_orders is False

    node = build_system_node(
        config,
        StartupPrerequisites(run_id=uuid4(), operational_persistence_ready=True),
    )
    assert node.is_running is False
