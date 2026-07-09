from __future__ import annotations

from nautilus_trader.adapters.interactive_brokers.config import (
    InteractiveBrokersDataClientConfig,
)
from nautilus_trader.live.config import TradingNodeConfig
from nautilus_trader.model.identifiers import TraderId

from markeitech.market_data.config import MarketDataRuntimeConfig


def build_trading_node_config(config: MarketDataRuntimeConfig) -> TradingNodeConfig:
    ib_config = InteractiveBrokersDataClientConfig(
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
    )
