from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from markeitech.domain import (
    AnalysisProfile,
    CryptoContractConfig,
    EquityLikeContractConfig,
    FuturesContractConfig,
    InstrumentContractConfig,
    InstrumentDataMode,
    InstrumentRegistryConfig,
    InstrumentRole,
    InstrumentRuntimeConfig,
    InstrumentWarmupConfig,
    SecurityType,
    WarmupTimeframe,
)
from markeitech.market_data.config import (
    InteractiveBrokersConnectionConfig,
    MarketDataRuntimeConfig,
    OperatorContextConfig,
    RuntimeLoggingConfig,
)
from markeitech.persistence.config import PersistenceConfig
from markeitech.signals import SignalRuntimeConfig


def load_market_data_runtime_config(path: str | Path) -> MarketDataRuntimeConfig:
    config_path = Path(path)
    with config_path.open("rb") as file:
        raw = tomllib.load(file)
    return parse_market_data_runtime_config(raw)


def parse_market_data_runtime_config(raw: dict[str, Any]) -> MarketDataRuntimeConfig:
    ib = InteractiveBrokersConnectionConfig(**raw.get("ib", {}))
    runtime_raw = raw.get("runtime", {})
    persistence_raw = raw.get("persistence")
    logging_raw = raw.get("logging", {})
    operator_context_raw = raw.get("operator_context", {})
    signals_raw = raw.get("signals")
    instruments_raw = raw.get("instruments", [])
    if not isinstance(instruments_raw, list):
        raise ValueError("market-data config requires an instruments array")

    instruments = tuple(_parse_instrument_runtime(item) for item in instruments_raw)
    registry = InstrumentRegistryConfig(
        active_instrument_id=runtime_raw.get("active_instrument_id", ""),
        instruments=instruments,
    )
    return MarketDataRuntimeConfig(
        instrument_registry=registry,
        ib=ib,
        trader_id=runtime_raw.get("trader_id", "MARKEITECH-001"),
        data_client_name=runtime_raw.get("data_client_name", "IB"),
        data_only=runtime_raw.get("data_only", True),
        build_nautilus_node=runtime_raw.get("build_nautilus_node", True),
        manual_live_node_start=runtime_raw.get("manual_live_node_start", False),
        run_live_node=runtime_raw.get("run_live_node", False),
        persistence=(PersistenceConfig(**persistence_raw) if persistence_raw is not None else None),
        logging=RuntimeLoggingConfig(**logging_raw),
        operator_context=OperatorContextConfig(**operator_context_raw),
        signals=(SignalRuntimeConfig(**signals_raw) if signals_raw is not None else None),
    )


def _parse_instrument_runtime(raw: dict[str, Any]) -> InstrumentRuntimeConfig:
    contract = _parse_contract(raw.get("contract", {}))
    warmup_raw = raw.get("warmup")
    return InstrumentRuntimeConfig(
        contract=contract,
        role=InstrumentRole(raw["role"]),
        data_mode=InstrumentDataMode(raw["data_mode"]),
        analysis_profile=AnalysisProfile(raw["analysis_profile"]),
        enabled=raw.get("enabled", True),
        priority=raw.get("priority", 100),
        warmup=_parse_warmup(warmup_raw) if warmup_raw is not None else None,
    )


def _parse_contract(raw: dict[str, Any]) -> InstrumentContractConfig:
    security_type = SecurityType(raw["security_type"])
    if security_type == SecurityType.FUTURE:
        return FuturesContractConfig(**raw)
    if security_type == SecurityType.CRYPTO:
        return CryptoContractConfig(**raw)
    if security_type in {SecurityType.STOCK, SecurityType.ETF, SecurityType.INDEX}:
        return EquityLikeContractConfig(**raw)
    return InstrumentContractConfig(**raw)


def _parse_warmup(raw: dict[str, Any]) -> InstrumentWarmupConfig:
    values = dict(raw)
    if "timeframes" in values:
        values["timeframes"] = tuple(WarmupTimeframe(value) for value in values["timeframes"])
    return InstrumentWarmupConfig(**values)
