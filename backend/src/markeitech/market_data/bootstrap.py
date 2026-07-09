from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from nautilus_trader.live.node import TradingNode
from pydantic import Field

from markeitech.domain.base import VersionedDomainModel
from markeitech.market_data.config import MarketDataRuntimeConfig
from markeitech.market_data.nautilus import build_trading_node_config

LIVE_NODE_START_CONFIRMATION = "I_UNDERSTAND_THIS_CONNECTS_TO_IB"


class LiveNodeLike(Protocol):
    def run(self) -> Any: ...


class LiveNodeBootstrapSummary(VersionedDomainModel):
    can_build_node: bool
    will_start_node: bool
    data_only: bool
    read_only_ib: bool
    execution_clients_enabled: bool
    data_client_name: str = Field(min_length=1)


def build_livenode_bootstrap_summary(
    config: MarketDataRuntimeConfig,
) -> LiveNodeBootstrapSummary:
    node_config = build_trading_node_config(config)
    return LiveNodeBootstrapSummary(
        can_build_node=config.build_nautilus_node,
        will_start_node=config.run_live_node and config.manual_live_node_start,
        data_only=config.data_only,
        read_only_ib=config.ib.read_only,
        execution_clients_enabled=bool(node_config.exec_clients),
        data_client_name=config.data_client_name,
    )


def build_live_node(
    config: MarketDataRuntimeConfig,
    *,
    node_factory: Callable[..., LiveNodeLike] = TradingNode,
) -> LiveNodeLike:
    if not config.build_nautilus_node:
        raise RuntimeError("Nautilus LiveNode construction is disabled by config")
    node_config = build_trading_node_config(config)
    return node_factory(config=node_config)


def start_live_node(
    config: MarketDataRuntimeConfig,
    node: LiveNodeLike,
    *,
    confirmation: str | None,
) -> Any:
    if not config.run_live_node:
        raise RuntimeError("Nautilus LiveNode start is disabled by config")
    if not config.manual_live_node_start:
        raise RuntimeError("Nautilus LiveNode start requires manual_live_node_start")
    if confirmation != LIVE_NODE_START_CONFIRMATION:
        raise RuntimeError(
            "Nautilus LiveNode start requires explicit confirmation token "
            f"{LIVE_NODE_START_CONFIRMATION!r}"
        )
    return node.run()
