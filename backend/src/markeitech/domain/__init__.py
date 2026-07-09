"""Versioned domain contracts for Markeitech."""

from markeitech.domain.classification import classify_trade
from markeitech.domain.events import (
    ActiveInstrumentChangedEvent,
    GatewayEvent,
    GatewayEventType,
    StrategyState,
    StrategyStateEvent,
)
from markeitech.domain.instruments import (
    AnalysisProfile,
    EquityLikeContractConfig,
    FuturesContractConfig,
    InstrumentContractConfig,
    InstrumentDataMode,
    InstrumentRegistryConfig,
    InstrumentRole,
    InstrumentRuntimeConfig,
    NQContractConfig,
    SecurityType,
)
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
    "ActiveInstrumentChangedEvent",
    "AnalysisProfile",
    "CanonicalQuoteTick",
    "CanonicalTradeTick",
    "ClassifiedTrade",
    "EquityLikeContractConfig",
    "FuturesContractConfig",
    "GapSeverity",
    "GapState",
    "GatewayEvent",
    "GatewayEventType",
    "InstrumentContractConfig",
    "InstrumentDataMode",
    "InstrumentRegistryConfig",
    "InstrumentRole",
    "InstrumentRuntimeConfig",
    "NQContractConfig",
    "OneMinuteBar",
    "ReadinessState",
    "ReadinessStatus",
    "SecurityType",
    "SourceHealth",
    "SourceStatus",
    "StrategyState",
    "StrategyStateEvent",
    "TradeSide",
    "classify_trade",
]
