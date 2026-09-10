from __future__ import annotations

from nautilus_trader.adapters.interactive_brokers import (
    InteractiveBrokersDataClientConfig,
    InteractiveBrokersDataClientFactory,
    InteractiveBrokersExecutionClientConfig,
    InteractiveBrokersExecutionClientFactory,
    InteractiveBrokersInstrumentProviderConfig,
    MarketDataType,
    SymbologyMethod,
)
from nautilus_trader.common import (
    Environment,
    FileWriterConfig,
    LoggerConfig,
    LogLevel,
)
from nautilus_trader.live import LiveNode, LiveRiskEngineConfig
from nautilus_trader.model import InstrumentId, TraderId

from markeitech.system.composition import StartupPrerequisites, build_actor_plan
from markeitech.system.config import SystemConfig

_MARKET_DATA_TYPES = {
    "realtime": MarketDataType.REALTIME,
    "frozen": MarketDataType.FROZEN,
    "delayed": MarketDataType.DELAYED,
    "delayed_frozen": MarketDataType.DELAYED_FROZEN,
}

_SYMBOLOGY_METHODS = {
    "raw": SymbologyMethod.RAW,
    "simplified": SymbologyMethod.SIMPLIFIED,
}

_ENVIRONMENTS = {
    "live": Environment.LIVE,
    "sandbox": Environment.SANDBOX,
}


def _build_ib_instrument_provider_config(
    config: SystemConfig,
) -> InteractiveBrokersInstrumentProviderConfig:
    instrument_ids = [InstrumentId.from_str(value) for value in config.instrument_ids]
    return InteractiveBrokersInstrumentProviderConfig(
        symbology_method=_SYMBOLOGY_METHODS[config.ib.symbology_method],
        load_ids=set(instrument_ids),
        convert_exchange_to_mic_venue=config.ib.convert_exchange_to_mic_venue,
    )


def build_ib_data_client_config(config: SystemConfig) -> InteractiveBrokersDataClientConfig:
    return InteractiveBrokersDataClientConfig(
        host=config.ib.host,
        port=config.ib.port,
        client_id=config.ib.client_id,
        use_regular_trading_hours=config.ib.use_regular_trading_hours,
        market_data_type=_MARKET_DATA_TYPES[config.ib.market_data_type],
        ignore_quote_tick_size_updates=config.ib.ignore_quote_tick_size_updates,
        connection_timeout=config.ib.connection_timeout_seconds,
        request_timeout=config.ib.request_timeout_seconds,
        handle_revised_bars=config.ib.handle_revised_bars,
        batch_quotes=config.ib.batch_quotes,
        instrument_provider=_build_ib_instrument_provider_config(config),
    )


def build_ib_execution_client_config(
    config: SystemConfig,
) -> InteractiveBrokersExecutionClientConfig:
    """Map validated account/client selection and shared IB settings without connecting.

    Args:
        config: System configuration with an explicit execution account identity.

    Returns:
        Native execution configuration with untouched defaults for other settings.

    Raises:
        ValueError: If the execution account is empty or client IDs conflict.
    """

    if not config.ib_execution.account_id:
        raise ValueError("ib_execution.account_id must be nonempty to construct the client")
    if config.ib_execution.client_id == config.ib.client_id:
        raise ValueError("ib_execution.client_id must differ from ib.client_id")
    return InteractiveBrokersExecutionClientConfig(
        host=config.ib.host,
        port=config.ib.port,
        client_id=config.ib_execution.client_id,
        account_id=config.ib_execution.account_id,
        connection_timeout=config.ib.connection_timeout_seconds,
        request_timeout=config.ib.request_timeout_seconds,
        instrument_provider=_build_ib_instrument_provider_config(config),
    )


def build_live_risk_engine_config(config: SystemConfig) -> LiveRiskEngineConfig:
    """Map risk bypass to native configuration without starting any runtime component.

    Args:
        config: Validated system configuration.

    Returns:
        Native risk configuration; unexposed fields keep installed-version defaults.
    """

    return LiveRiskEngineConfig(bypass=config.risk_engine.bypass)


def build_system_node(config: SystemConfig, prerequisites: StartupPrerequisites) -> LiveNode:
    """Construct the configured Nautilus live node without starting it.

    The function creates the configured log directory, registers the IB data
    client, optionally registers the native IB execution client and risk settings,
    and composes validated actors. It does not connect to IB or run the node lifecycle.

    Args:
        config: Validated V2 system configuration.
        prerequisites: Startup evidence required by actor composition.

    Returns:
        A fully built but not started Nautilus ``LiveNode``.

    Raises:
        ValueError: If identifiers, provider settings, or actor prerequisites are invalid.
        OSError: If the configured logging directory cannot be created.
    """

    config.logging.directory.mkdir(parents=True, exist_ok=True)
    data_config = build_ib_data_client_config(config)

    builder = (
        LiveNode.builder(
            config.runtime.name,
            TraderId.from_str(config.runtime.trader_id),
            _ENVIRONMENTS[config.runtime.environment],
        )
        .with_logging(
            LoggerConfig(
                stdout_level=LogLevel.INFO,
                fileout_level=LogLevel.INFO,
                file_config=FileWriterConfig(
                    directory=str(config.logging.directory),
                    file_name=config.logging.file_name,
                ),
                clear_log_file=False,
                fileout_sync_on_flush=True,
            ),
        )
        .add_data_client(None, InteractiveBrokersDataClientFactory(), data_config)
    )
    if config.ib_execution.enabled:
        builder = builder.with_risk_engine_config(
            build_live_risk_engine_config(config)
        ).add_exec_client(
            "IB_EXECUTION",
            InteractiveBrokersExecutionClientFactory(),
            build_ib_execution_client_config(config),
        )
    node = builder.build()
    plan = build_actor_plan(config, prerequisites)
    if config.dashboard.enabled:
        # Explicit composition keeps provider operations inside acquisition while
        # registering the dashboard's own native handlers. No global actor lookup.
        from markeitech.dashboard.actor import DashboardActor, DashboardActorConfig
        from markeitech.system.acquisition import DataAcquisitionActor, DataAcquisitionActorConfig

        configs = {item.key: item.config.config for item in plan}
        dashboard = DashboardActor(DashboardActorConfig(**configs["dashboard"]))
        acquisition = DataAcquisitionActor(
            DataAcquisitionActorConfig(**configs["data_acquisition"])
        )
        acquisition.bind_dashboard_consumer(
            dashboard,
            {
                (member.instrument_id, {"top_of_book": "quotes", "watchlist_last": "bars"}[cap])
                for member in config.watchlist.members
                for cap in member.capabilities
            },
            config.dashboard.acquisition_retry_interval_ms,
        )
        for registration in plan:
            if registration.key == "data_acquisition":
                node.add_actor(acquisition)
            elif registration.key == "dashboard":
                node.add_actor(dashboard)
            else:
                node.add_actor_from_config(registration.config)
    else:
        for registration in plan:
            node.add_actor_from_config(registration.config)
    return node
