"""Versioned domain contracts for Markeitech."""

from markeitech.domain.classification import classify_trade
from markeitech.domain.events import (
    GatewayEvent,
    GatewayEventType,
    StrategyState,
    StrategyStateEvent,
)
from markeitech.domain.instruments import NQContractConfig
from markeitech.domain.market_data import (
    BarInterval,
    CanonicalQuoteTick,
    CanonicalTradeTick,
    ClassifiedTrade,
    OneMinuteBar,
    TradeSide,
)
from markeitech.domain.state import (
    GapSeverity,
    GapState,
    ReadinessState,
    ReadinessStatus,
    SourceHealth,
    SourceStatus,
)

__all__ = [
    "BarInterval",
    "CanonicalQuoteTick",
    "CanonicalTradeTick",
    "ClassifiedTrade",
    "GapSeverity",
    "GapState",
    "GatewayEvent",
    "GatewayEventType",
    "NQContractConfig",
    "OneMinuteBar",
    "ReadinessState",
    "ReadinessStatus",
    "SourceHealth",
    "SourceStatus",
    "StrategyState",
    "StrategyStateEvent",
    "TradeSide",
    "classify_trade",
]
