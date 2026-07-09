from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from markeitech.domain.base import VersionedDomainModel, require_iana_timezone


class SecurityType(StrEnum):
    FUTURE = "FUT"
    INDEX = "IND"
    STOCK = "STK"
    ETF = "ETF"


class InstrumentRole(StrEnum):
    ACTIVE = "active"
    BACKGROUND = "background"
    DISABLED = "disabled"


class InstrumentDataMode(StrEnum):
    TICK_BY_TICK = "tick_by_tick"
    HISTORICAL_1M = "historical_1m"
    DISABLED = "disabled"


class AnalysisProfile(StrEnum):
    ACTIVE_TICK = "active_tick"
    BACKGROUND_BAR = "background_bar"
    SIGNALS_ONLY = "signals_only"


class InstrumentContractConfig(VersionedDomainModel):
    root_symbol: str = Field(min_length=1)
    exchange: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    security_type: SecurityType
    ib_symbol: str = Field(min_length=1)
    ib_exchange: str = Field(min_length=1)
    ib_security_type: str = Field(min_length=2)
    session_timezone: str = Field(default="America/New_York")

    @field_validator("root_symbol", "exchange", "ib_symbol", "ib_exchange", "ib_security_type")
    @classmethod
    def _uppercase_identity_fields(cls, value: str) -> str:
        return value.upper()

    @field_validator("session_timezone")
    @classmethod
    def _session_timezone_must_be_iana(cls, value: str) -> str:
        return require_iana_timezone(value)

    @model_validator(mode="after")
    def _identity_fields_must_be_consistent(self) -> InstrumentContractConfig:
        if self.ib_symbol != self.root_symbol:
            raise ValueError("IB symbol must match root symbol")
        if self.ib_exchange != self.exchange:
            raise ValueError("IB exchange must match contract exchange")
        if self.ib_security_type != self.security_type.value:
            raise ValueError("IB security type must match contract security type")
        return self

    @property
    def identity_key(self) -> str:
        return f"{self.root_symbol}.{self.exchange}.{self.security_type}.{self.instrument_id}"


class FuturesContractConfig(InstrumentContractConfig):
    security_type: SecurityType = Field(default=SecurityType.FUTURE)
    expiry: date
    ib_security_type: str = Field(default="FUT")
    ib_last_trade_date_or_contract_month: str = Field(min_length=6)

    @field_validator("ib_security_type")
    @classmethod
    def _security_type_must_be_future(cls, value: str) -> str:
        value = value.upper()
        if value != "FUT":
            raise ValueError("futures contracts require individual FUT security type")
        return value

    @model_validator(mode="after")
    def _reject_continuous_or_front_month_identity(self) -> FuturesContractConfig:
        instrument_id_upper = self.instrument_id.upper()
        root_upper = self.root_symbol.upper()
        exchange_upper = self.exchange.upper()
        if self.security_type != SecurityType.FUTURE or self.ib_security_type != "FUT":
            raise ValueError("futures contracts require individual FUT security type")
        if instrument_id_upper in {
            f"{root_upper}.{exchange_upper}",
            f"{root_upper}.X{exchange_upper}",
        }:
            raise ValueError("front-month or continuous futures identity is prohibited")
        if not instrument_id_upper.startswith(root_upper):
            raise ValueError("futures instrument id must start with root symbol")
        expiry_text = self.expiry.strftime("%Y%m%d")
        if self.ib_last_trade_date_or_contract_month not in {
            expiry_text,
            expiry_text[:6],
        }:
            raise ValueError("IB expiry must match the configured contract expiry")
        return self

    @property
    def identity_key(self) -> str:
        return f"{self.root_symbol}.{self.exchange}.{self.expiry:%Y%m%d}.{self.instrument_id}"


class EquityLikeContractConfig(InstrumentContractConfig):
    security_type: SecurityType = Field(default=SecurityType.STOCK)
    currency: str = Field(default="USD", min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def _currency_must_be_uppercase(cls, value: str) -> str:
        return value.upper()


class InstrumentRuntimeConfig(VersionedDomainModel):
    contract: FuturesContractConfig | EquityLikeContractConfig | InstrumentContractConfig
    role: InstrumentRole
    data_mode: InstrumentDataMode
    analysis_profile: AnalysisProfile
    enabled: bool = True
    priority: int = Field(default=100, ge=0)
    historical_refresh_interval_seconds: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _role_and_data_mode_must_match(self) -> InstrumentRuntimeConfig:
        if not self.enabled and self.role != InstrumentRole.DISABLED:
            raise ValueError("disabled instruments must use disabled role")
        if self.role == InstrumentRole.ACTIVE and self.data_mode != InstrumentDataMode.TICK_BY_TICK:
            raise ValueError("active instrument must use tick-by-tick data mode")
        if self.role == InstrumentRole.BACKGROUND:
            if self.data_mode != InstrumentDataMode.HISTORICAL_1M:
                raise ValueError("background instruments must use historical 1m data mode")
            if self.historical_refresh_interval_seconds is None:
                raise ValueError("background instruments require a historical refresh interval")
        if self.role == InstrumentRole.DISABLED and self.data_mode != InstrumentDataMode.DISABLED:
            raise ValueError("disabled instruments must use disabled data mode")
        return self


class InstrumentRegistryConfig(VersionedDomainModel):
    instruments: tuple[InstrumentRuntimeConfig, ...] = Field(min_length=1)
    active_instrument_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def _registry_must_have_one_active_instrument(self) -> InstrumentRegistryConfig:
        instrument_ids = [instrument.contract.instrument_id for instrument in self.instruments]
        if len(instrument_ids) != len(set(instrument_ids)):
            raise ValueError("instrument ids must be unique")
        active = [
            instrument
            for instrument in self.instruments
            if instrument.enabled and instrument.role == InstrumentRole.ACTIVE
        ]
        if len(active) != 1:
            raise ValueError("registry must have exactly one active instrument")
        if active[0].contract.instrument_id != self.active_instrument_id:
            raise ValueError("active instrument id must match the active runtime config")
        if self.active_instrument_id not in instrument_ids:
            raise ValueError("active instrument id must be configured")
        return self

    @property
    def active_runtime(self) -> InstrumentRuntimeConfig:
        for instrument in self.instruments:
            if instrument.contract.instrument_id == self.active_instrument_id:
                return instrument
        raise RuntimeError("validated registry missing active runtime")


class NQContractConfig(FuturesContractConfig):
    root_symbol: str = Field(default="NQ")
    exchange: str = Field(default="CME")
    ib_symbol: str = Field(default="NQ")
    ib_exchange: str = Field(default="CME")
