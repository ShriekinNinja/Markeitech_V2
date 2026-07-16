from __future__ import annotations

from nautilus_trader.adapters.interactive_brokers.config import (
    InteractiveBrokersDataClientConfig,
    InteractiveBrokersInstrumentProviderConfig,
)
from nautilus_trader.config import LoggingConfig
from nautilus_trader.live.config import TradingNodeConfig
from nautilus_trader.model.identifiers import InstrumentId, TraderId

from markeitech.market_data.config import MarketDataRuntimeConfig


def build_trading_node_config(config: MarketDataRuntimeConfig) -> TradingNodeConfig:
    load_ids = frozenset(
        InstrumentId.from_str(runtime.contract.instrument_id)
        for runtime in config.instrument_registry.instruments
        if runtime.enabled
    )
    ib_config = InteractiveBrokersDataClientConfig(
        instrument_provider=InteractiveBrokersInstrumentProviderConfig(load_ids=load_ids),
        ibg_host=config.ib.host,
        ibg_port=config.ib.port,
        ibg_client_id=config.ib.client_id,
        use_regular_trading_hours=config.ib.use_regular_trading_hours,
        market_data_type=config.ib.market_data_type,
        connection_timeout=config.ib.connection_timeout_seconds,
        request_timeout_secs=config.ib.request_timeout_seconds,
    )
    return TradingNodeConfig(
        trader_id=TraderId(config.trader_id),
        data_clients={config.data_client_name: ib_config},
        exec_clients={},
        strategies=[],
        actors=[],
        load_state=False,
        save_state=False,
        timeout_post_stop=config.live_node.post_stop_timeout_seconds,
        timeout_disconnection=config.live_node.disconnection_timeout_seconds,
        timeout_shutdown=config.live_node.shutdown_timeout_seconds,
        logging=(
            LoggingConfig(
                log_level=config.logging.console_level,
                log_level_file=config.logging.file_level,
                log_directory=str(config.logging.directory),
                log_file_name=config.logging.file_name,
                log_file_format="JSON",
                log_file_max_size=config.logging.max_file_size_bytes,
                log_file_max_backup_count=config.logging.max_backup_count,
                fileout_sync_on_flush=True,
            )
            if config.logging.enabled
            else None
        ),
    )
