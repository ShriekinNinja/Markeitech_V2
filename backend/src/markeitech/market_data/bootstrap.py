from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from nautilus_trader.adapters.interactive_brokers.factories import (
    InteractiveBrokersLiveDataClientFactory,
)
from nautilus_trader.live.node import TradingNode
from pydantic import Field

from markeitech.domain.base import VersionedDomainModel
from markeitech.market_data.actions import build_livenode_action_plan
from markeitech.market_data.actor import MarkeitechMarketDataActor
from markeitech.market_data.config import MarketDataRuntimeConfig
from markeitech.market_data.coordinator import (
    WarmupReadyHandler,
    require_historical_coverage,
)
from markeitech.market_data.intents import build_nautilus_request_plan
from markeitech.market_data.nautilus import build_trading_node_config
from markeitech.market_data.planner import build_market_data_plan
from markeitech.persistence.runtime import PersistenceRuntime

LIVE_NODE_START_CONFIRMATION = "I_UNDERSTAND_THIS_CONNECTS_TO_IB"


class LiveNodeLike(Protocol):
    def run(self) -> Any: ...


class LiveNodeTraderLike(Protocol):
    def add_actor(self, actor: Any) -> None: ...


class ConfigurableLiveNodeLike(LiveNodeLike, Protocol):
    trader: LiveNodeTraderLike

    def add_data_client_factory(self, name: str, factory: type[Any]) -> None: ...

    def build(self) -> None: ...


class LiveNodeBootstrapSummary(VersionedDomainModel):
    can_build_node: bool
    will_start_node: bool
    data_only: bool
    read_only_ib: bool
    execution_clients_enabled: bool
    data_client_name: str = Field(min_length=1)
    persistence_enabled: bool


class PersistenceManagedLiveNode:
    def __init__(self, node: ConfigurableLiveNodeLike, persistence: PersistenceRuntime) -> None:
        self._node = node
        self.persistence = persistence

    def __getattr__(self, name: str) -> Any:
        return getattr(self._node, name)

    def run(self) -> Any:
        self.persistence.start()
        try:
            return self._node.run()
        finally:
            self.persistence.stop()

    async def run_async(self) -> None:
        self.persistence.start()
        try:
            await self._node.run_async()
        finally:
            self.persistence.stop()

    async def stop_async(self) -> None:
        try:
            await self._node.stop_async()
        finally:
            self.persistence.stop()


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
        persistence_enabled=config.persistence is not None,
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


def build_prepared_market_data_live_node(
    config: MarketDataRuntimeConfig,
    *,
    node_factory: Callable[..., ConfigurableLiveNodeLike] = TradingNode,
    actor_factory: Callable[..., Any] = MarkeitechMarketDataActor,
    on_warmup_ready: WarmupReadyHandler = require_historical_coverage,
    data_client_factory: type[Any] = InteractiveBrokersLiveDataClientFactory,
) -> ConfigurableLiveNodeLike | PersistenceManagedLiveNode:
    node = build_live_node(config, node_factory=node_factory)
    runtime_plan = build_market_data_plan(config.instrument_registry)
    request_plan = build_nautilus_request_plan(
        runtime_plan,
        data_client_name=config.data_client_name,
    )
    action_plan = build_livenode_action_plan(request_plan)
    persistence = PersistenceRuntime.build(config.persistence) if config.persistence else None
    actor_kwargs: dict[str, Any] = {"on_warmup_ready": on_warmup_ready}
    if persistence is not None:
        actor_kwargs.update(
            on_native_market_data_event=persistence.ingress.submit_native,
            on_market_data_event=persistence.ingress.submit_canonical,
        )
    try:
        actor = actor_factory(action_plan, **actor_kwargs)
        node.trader.add_actor(actor)
        node.add_data_client_factory(config.data_client_name, data_client_factory)
        node.build()
    except Exception:
        if persistence is not None:
            persistence.stop()
        raise
    if persistence is None:
        return node
    return PersistenceManagedLiveNode(node, persistence)


def start_live_node(
    config: MarketDataRuntimeConfig,
    node: LiveNodeLike,
    *,
    confirmation: str | None,
) -> Any:
    validate_live_node_start(config, confirmation=confirmation)
    return node.run()


def validate_live_node_start(
    config: MarketDataRuntimeConfig,
    *,
    confirmation: str | None,
) -> None:
    if not config.run_live_node:
        raise RuntimeError("Nautilus LiveNode start is disabled by config")
    if not config.manual_live_node_start:
        raise RuntimeError("Nautilus LiveNode start requires manual_live_node_start")
    if confirmation != LIVE_NODE_START_CONFIRMATION:
        raise RuntimeError(
            "Nautilus LiveNode start requires explicit confirmation token "
            f"{LIVE_NODE_START_CONFIRMATION!r}"
        )
