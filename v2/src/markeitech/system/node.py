from __future__ import annotations

from nautilus_trader.adapters.interactive_brokers import (
    InteractiveBrokersDataClientConfig,
    InteractiveBrokersDataClientFactory,
    InteractiveBrokersInstrumentProviderConfig,
    MarketDataType,
)
from nautilus_trader.common import (
    Environment,
    FileWriterConfig,
    ImportableActorConfig,
    LoggerConfig,
    LogLevel,
)
from nautilus_trader.live import LiveNode
from nautilus_trader.model import InstrumentId, TraderId

from markeitech.system.config import SystemConfig

_MARKET_DATA_TYPES = {
    "realtime": MarketDataType.REALTIME,
    "frozen": MarketDataType.FROZEN,
    "delayed": MarketDataType.DELAYED,
    "delayed_frozen": MarketDataType.DELAYED_FROZEN,
}

_ENVIRONMENTS = {
    "live": Environment.LIVE,
    "sandbox": Environment.SANDBOX,
}


def build_system_node(config: SystemConfig) -> LiveNode:
    config.logging.directory.mkdir(parents=True, exist_ok=True)
    instrument_ids = [InstrumentId.from_str(item.id) for item in config.instruments]
    provider_config = InteractiveBrokersInstrumentProviderConfig(load_ids=set(instrument_ids))
    data_config = InteractiveBrokersDataClientConfig(
        host=config.ib.host,
        port=config.ib.port,
        client_id=config.ib.client_id,
        use_regular_trading_hours=config.ib.use_regular_trading_hours,
        market_data_type=_MARKET_DATA_TYPES[config.ib.market_data_type],
        connection_timeout=config.ib.connection_timeout_seconds,
        request_timeout=config.ib.request_timeout_seconds,
        instrument_provider=provider_config,
    )

    node = (
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
        .build()
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="markeitech.system.actor:SystemControlActor",
            config_path="markeitech.system.actor:SystemControlActorConfig",
            config={
                "actor_id": "SYSTEM-CONTROL",
                "instrument_ids": [str(value) for value in instrument_ids],
            },
        ),
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="markeitech.system.discord:DiscordHealthActor",
            config_path="markeitech.system.discord:DiscordHealthActorConfig",
            config={
                "actor_id": "DISCORD-HEALTH",
                "request_timeout_seconds": config.discord.request_timeout_seconds,
                "webhook_env": "MARKEITECH_DISCORD_SYSTEM_HEALTH_WEBHOOK",
            },
        ),
    )
    return node
