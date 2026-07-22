from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from markeitech.domain.base import VersionedDomainModel, require_iana_timezone


class SecurityType(StrEnum):
    FUTURE = "FUT"
    INDEX = "IND"
    STOCK = "STK"
    ETF = "ETF"
    CRYPTO = "CRYPTO"


class InstrumentRole(StrEnum):
    ACTIVE = "active"
    BACKGROUND = "background"
    DISABLED = "disabled"


class InstrumentDataMode(StrEnum):
    TICK_BY_TICK = "tick_by_tick"
    LIVE_1M_BARS = "live_1m_bars"
    HISTORICAL_WARMUP_ONLY = "historical_warmup_only"
    DISABLED = "disabled"


class AnalysisProfile(StrEnum):
    ACTIVE_TICK = "active_tick"
    BACKGROUND_BAR = "background_bar"
    SIGNALS_ONLY = "signals_only"


class SessionProfile(StrEnum):
    FULL = "full"
    REGULAR = "regular"
    CONTINUOUS = "continuous"


class WarmupTimeframe(StrEnum):
    ONE_MINUTE = "1m"
    FIVE_MINUTE = "5m"
    FIFTEEN_MINUTE = "15m"
    THIRTY_MINUTE = "30m"
    ONE_HOUR = "1h"
    DAILY = "1d"


class InstrumentWarmupConfig(VersionedDomainModel):
    lookback_sessions: int = Field(default=5, ge=1)
    lookback_sessions_by_timeframe: dict[WarmupTimeframe, int] = Field(
        default_factory=dict,
    )
    timeframes: tuple[WarmupTimeframe, ...] = Field(
        default=(
            WarmupTimeframe.ONE_MINUTE,
            WarmupTimeframe.FIVE_MINUTE,
            WarmupTimeframe.FIFTEEN_MINUTE,
            WarmupTimeframe.THIRTY_MINUTE,
        ),
        min_length=1,
    )
    annotate_support_resistance: bool = True
    annotate_emas: bool = True
    annotate_trend: bool = True
    annotate_vwap: bool = True
    annotate_fvgs: bool = True
    volume_profile_bin_size: Decimal = Field(default=Decimal("1"), gt=0)
    volume_profile_composite_sessions: tuple[int, ...] = (2, 5)

    @field_validator("lookback_sessions_by_timeframe")
    @classmethod
    def _timeframe_lookbacks_must_be_positive(
        cls,
        value: dict[WarmupTimeframe, int],
    ) -> dict[WarmupTimeframe, int]:
        if any(sessions < 1 for sessions in value.values()):
            raise ValueError("timeframe lookback sessions must be positive")
        return value

    @field_validator("volume_profile_composite_sessions")
    @classmethod
    def _composite_sessions_must_be_unique_and_bounded(
        cls,
        value: tuple[int, ...],
    ) -> tuple[int, ...]:
        if any(sessions < 2 or sessions > 20 for sessions in value):
            raise ValueError("volume profile composite sessions must be between 2 and 20")
        if len(set(value)) != len(value):
            raise ValueError("volume profile composite sessions must be unique")
        return tuple(sorted(value))

    @model_validator(mode="after")
    def _timeframe_lookbacks_must_match_configured_timeframes(
        self,
    ) -> InstrumentWarmupConfig:
        unknown = set(self.lookback_sessions_by_timeframe) - set(self.timeframes)
        if unknown:
            values = ", ".join(sorted(timeframe.value for timeframe in unknown))
            raise ValueError(f"lookbacks configured for disabled timeframes: {values}")
        return self

    def lookback_for(self, timeframe: WarmupTimeframe) -> int:
        if timeframe not in self.timeframes:
            raise ValueError(f"timeframe {timeframe.value} is not enabled for warmup")
        return self.lookback_sessions_by_timeframe.get(timeframe, self.lookback_sessions)


class AggressionOutcomeConfig(VersionedDomainModel):
    observation_window_seconds: int = Field(gt=0)
    follow_through_points: Decimal = Field(gt=0)
    trapped_points: Decimal = Field(gt=0)
    absorption_points: Decimal = Field(ge=0)
    max_open_episodes: int = Field(default=16, ge=1, le=256)

    @model_validator(mode="after")
    def _absorption_must_precede_terminal_moves(self) -> AggressionOutcomeConfig:
        if self.absorption_points >= min(self.follow_through_points, self.trapped_points):
            raise ValueError("absorption distance must be below terminal movement distances")
        return self


class InstrumentContractConfig(VersionedDomainModel):
    root_symbol: str = Field(min_length=1)
    exchange: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    security_type: SecurityType
    ib_symbol: str = Field(min_length=1)
    ib_exchange: str = Field(min_length=1)
    ib_security_type: str = Field(min_length=2)
    session_timezone: str = Field(default="America/New_York")
    calendar_id: str = Field(min_length=1)
    session_profile: SessionProfile

    @field_validator("root_symbol", "exchange", "ib_symbol", "ib_exchange", "ib_security_type")
    @classmethod
    def _uppercase_identity_fields(cls, value: str) -> str:
        return value.upper()

    @field_validator("session_timezone")
    @classmethod
    def _session_timezone_must_be_iana(cls, value: str) -> str:
        return require_iana_timezone(value)

    @field_validator("calendar_id")
    @classmethod
    def _calendar_id_must_be_trimmed(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("calendar id must not contain surrounding whitespace")
        return value

    @model_validator(mode="after")
    def _identity_fields_must_be_consistent(self) -> InstrumentContractConfig:
        if self.ib_symbol != self.root_symbol:
            raise ValueError("IB symbol must match root symbol")
        if self.ib_exchange != self.exchange:
            raise ValueError("IB exchange must match contract exchange")
        if self.ib_security_type != self.security_type.value:
            raise ValueError("IB security type must match contract security type")
        if (self.calendar_id == "24/7") != (self.session_profile == SessionProfile.CONTINUOUS):
            raise ValueError("24/7 calendar and continuous session profile must be used together")
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


class CryptoContractConfig(InstrumentContractConfig):
    security_type: SecurityType = Field(default=SecurityType.CRYPTO)
    ib_security_type: str = Field(default="CRYPTO")
    quote_currency: str = Field(default="USD", min_length=3, max_length=3)

    @field_validator("quote_currency")
    @classmethod
    def _quote_currency_must_be_uppercase(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def _identity_must_be_currency_pair(self) -> CryptoContractConfig:
        expected_id = f"{self.root_symbol}/{self.quote_currency}.{self.exchange}"
        if self.instrument_id != expected_id:
            raise ValueError(f"crypto instrument id must be {expected_id}")
        return self


class InstrumentRuntimeConfig(VersionedDomainModel):
    contract: (
        FuturesContractConfig
        | EquityLikeContractConfig
        | CryptoContractConfig
        | InstrumentContractConfig
    )
    role: InstrumentRole
    data_mode: InstrumentDataMode
    analysis_profile: AnalysisProfile
    enabled: bool = True
    priority: int = Field(default=100, ge=0)
    large_trade_threshold: Decimal | None = Field(default=None, gt=0)
    large_trade_window_ms: int = Field(default=250, gt=0)
    aggression_outcome: AggressionOutcomeConfig | None = None
    warmup: InstrumentWarmupConfig | None = Field(default_factory=InstrumentWarmupConfig)

    @model_validator(mode="after")
    def _role_and_data_mode_must_match(self) -> InstrumentRuntimeConfig:
        if not self.enabled and self.role != InstrumentRole.DISABLED:
            raise ValueError("disabled instruments must use disabled role")
        if self.enabled and self.warmup is None:
            raise ValueError("enabled instruments require warmup configuration")
        if self.role == InstrumentRole.ACTIVE and self.data_mode != InstrumentDataMode.TICK_BY_TICK:
            raise ValueError("active instrument must use tick-by-tick data mode")
        if self.role == InstrumentRole.BACKGROUND and self.data_mode not in {
            InstrumentDataMode.TICK_BY_TICK,
            InstrumentDataMode.LIVE_1M_BARS,
        }:
            raise ValueError("background instruments must use tick-by-tick or live 1m bar data")
        if (
            self.large_trade_threshold is not None
            and self.data_mode != InstrumentDataMode.TICK_BY_TICK
        ):
            raise ValueError("large trade thresholds require tick-by-tick data mode")
        if self.aggression_outcome is not None and self.large_trade_threshold is None:
            raise ValueError(
                "aggression outcome configuration requires a large trade threshold"
            )
        if self.role == InstrumentRole.DISABLED and self.data_mode != InstrumentDataMode.DISABLED:
            raise ValueError("disabled instruments must use disabled data mode")
        if self.role == InstrumentRole.DISABLED and self.warmup is not None:
            raise ValueError("disabled instruments must not define warmup configuration")
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

    @property
    def order_flow_runtimes(self) -> tuple[InstrumentRuntimeConfig, ...]:
        return tuple(
            instrument
            for instrument in self.instruments
            if instrument.enabled and instrument.data_mode == InstrumentDataMode.TICK_BY_TICK
        )


class NQContractConfig(FuturesContractConfig):
    root_symbol: str = Field(default="NQ")
    exchange: str = Field(default="CME")
    ib_symbol: str = Field(default="NQ")
    ib_exchange: str = Field(default="CME")
