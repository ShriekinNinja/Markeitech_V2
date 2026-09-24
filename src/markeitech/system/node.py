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
from nautilus_trader.live import LiveNode
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
) -> InteractiveBrokersExecutionClientConfig | None:
    account_id = config.ib.execution_account_id
    if account_id is None:
        return None
    return InteractiveBrokersExecutionClientConfig(
        host=config.ib.host,
        port=config.ib.port,
        client_id=config.ib.client_id,
        account_id=account_id,
        connection_timeout=config.ib.connection_timeout_seconds,
        request_timeout=config.ib.request_timeout_seconds,
        instrument_provider=_build_ib_instrument_provider_config(config),
    )


def build_system_node(config: SystemConfig, prerequisites: StartupPrerequisites) -> LiveNode:
    """Construct the configured Nautilus live node without starting it.

    The function creates the configured log directory, registers the IB data
    client and optional IB execution client, then composes validated actors.
    It does not connect to IB or run the node lifecycle.

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
    execution_config = build_ib_execution_client_config(config)

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
    if execution_config is not None:
        builder.add_exec_client(
            None,
            InteractiveBrokersExecutionClientFactory(),
            execution_config,
        )
    node = builder.build()
    plan = build_actor_plan(config, prerequisites)
    for registration in plan:
        node.add_actor_from_config(registration.config)
    return node
