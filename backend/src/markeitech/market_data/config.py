from __future__ import annotations

from pydantic import Field, model_validator

from markeitech.domain.base import VersionedDomainModel
from markeitech.domain.instruments import InstrumentRegistryConfig


class InteractiveBrokersConnectionConfig(VersionedDomainModel):
    host: str = Field(default="127.0.0.1", min_length=1)
    port: int = Field(default=7497, ge=1, le=65535)
    client_id: int = Field(default=1, ge=0)
    use_regular_trading_hours: bool = False
    market_data_type: int = Field(default=1, ge=1)
    connection_timeout_seconds: int = Field(default=300, ge=1)
    request_timeout_seconds: int = Field(default=60, ge=1)
    read_only: bool = True


class MarketDataRuntimeConfig(VersionedDomainModel):
    instrument_registry: InstrumentRegistryConfig
    ib: InteractiveBrokersConnectionConfig = Field(
        default_factory=InteractiveBrokersConnectionConfig,
    )
    trader_id: str = Field(default="MARKEITECH-001", min_length=1)
    data_client_name: str = Field(default="IB", min_length=1)
    data_only: bool = True
    build_nautilus_node: bool = True
    manual_live_node_start: bool = False
    run_live_node: bool = False

    @model_validator(mode="after")
    def _runtime_must_remain_data_only_for_stage_2(self) -> MarketDataRuntimeConfig:
        if not self.data_only:
            raise ValueError("Stage 2 runtime must be data-only")
        if self.run_live_node and not self.manual_live_node_start:
            raise ValueError("LiveNode start requires explicit manual_live_node_start")
        if not self.ib.read_only:
            raise ValueError("Stage 2 IB connection must be read-only")
        return self
