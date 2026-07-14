from __future__ import annotations

from pathlib import Path

from pydantic import Field, model_validator

from markeitech.domain.base import VersionedDomainModel
from markeitech.domain.instruments import InstrumentRegistryConfig
from markeitech.persistence.config import PersistenceConfig
from markeitech.signals import SignalRuntimeConfig


class InteractiveBrokersConnectionConfig(VersionedDomainModel):
    host: str = Field(default="127.0.0.1", min_length=1)
    port: int = Field(default=7497, ge=1, le=65535)
    client_id: int = Field(default=1, ge=0)
    use_regular_trading_hours: bool = False
    market_data_type: int = Field(default=1, ge=1)
    connection_timeout_seconds: int = Field(default=300, ge=1)
    request_timeout_seconds: int = Field(default=60, ge=1)
    read_only: bool = True


class RuntimeLoggingConfig(VersionedDomainModel):
    enabled: bool = False
    console_level: str = Field(default="INFO", min_length=1)
    file_level: str = Field(default="INFO", min_length=1)
    directory: Path = Path("data/logs")
    file_name: str = Field(default="markeitech-live", min_length=1)
    max_file_size_bytes: int = Field(default=25 * 1024 * 1024, gt=0)
    max_backup_count: int = Field(default=10, ge=0)


class OperatorContextConfig(VersionedDomainModel):
    enabled: bool = True
    interval_seconds: int = Field(default=60, ge=10)


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
    persistence: PersistenceConfig | None = None
    logging: RuntimeLoggingConfig = Field(default_factory=RuntimeLoggingConfig)
    operator_context: OperatorContextConfig = Field(default_factory=OperatorContextConfig)
    signals: SignalRuntimeConfig | None = None

    @model_validator(mode="after")
    def _runtime_must_remain_data_only_for_stage_2(self) -> MarketDataRuntimeConfig:
        if not self.data_only:
            raise ValueError("Stage 2 runtime must be data-only")
        if self.run_live_node and not self.manual_live_node_start:
            raise ValueError("LiveNode start requires explicit manual_live_node_start")
        if not self.ib.read_only:
            raise ValueError("Stage 2 IB connection must be read-only")
        if self.signals is not None and self.signals.enabled_definition_ids_by_instrument:
            if self.persistence is None:
                raise ValueError("enabled signals require durable persistence")
            runtimes = {
                runtime.contract.instrument_id: runtime
                for runtime in self.instrument_registry.instruments
                if runtime.enabled
            }
            for instrument_id in self.signals.enabled_definition_ids_by_instrument:
                runtime = runtimes.get(instrument_id)
                if runtime is None:
                    raise ValueError(f"signals require enabled instrument {instrument_id!r}")
                if runtime.warmup is None:
                    raise ValueError(f"signals require warmup for {instrument_id!r}")
                configured = {timeframe.value for timeframe in runtime.warmup.timeframes}
                for definition in self.signals.enabled_definitions(instrument_id):
                    mandatory = {
                        definition.evaluation_timeframe.value,
                        *(timeframe.value for timeframe in definition.primary_direction_timeframes),
                    }
                    missing = mandatory - configured
                    if missing:
                        raise ValueError(
                            f"signal definition {definition.definition_id!r} requires "
                            f"warmup timeframes {sorted(missing)} for {instrument_id!r}"
                        )
                    confirmations = sum(
                        timeframe.value in configured
                        for timeframe in definition.confirmation_timeframes
                    )
                    if confirmations < definition.minimum_confirmation_count:
                        raise ValueError(
                            f"signal definition {definition.definition_id!r} lacks enough "
                            f"confirmation timeframes for {instrument_id!r}"
                        )
        return self
