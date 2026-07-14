from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from markeitech.domain.base import VersionedDomainModel, require_utc


class AnalyticsTimeframe(StrEnum):
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    DAILY = "1d"

    @property
    def duration(self) -> timedelta:
        return {
            AnalyticsTimeframe.ONE_MINUTE: timedelta(minutes=1),
            AnalyticsTimeframe.FIVE_MINUTES: timedelta(minutes=5),
            AnalyticsTimeframe.FIFTEEN_MINUTES: timedelta(minutes=15),
            AnalyticsTimeframe.THIRTY_MINUTES: timedelta(minutes=30),
            AnalyticsTimeframe.ONE_HOUR: timedelta(hours=1),
            AnalyticsTimeframe.DAILY: timedelta(days=1),
        }[self]

    @classmethod
    def from_duration(cls, duration: timedelta) -> AnalyticsTimeframe:
        for timeframe in cls:
            if timeframe.duration == duration:
                return timeframe
        raise ValueError(f"unsupported analytics timeframe: {duration}")


class TrendState(StrEnum):
    INSUFFICIENT_DATA = "insufficient_data"
    BULLISH = "bullish"
    BEARISH = "bearish"
    RANGE = "range"


class VwapPosition(StrEnum):
    UNAVAILABLE = "unavailable"
    ABOVE = "above"
    BELOW = "below"
    AT = "at"


class AnalyticsInputFidelity(StrEnum):
    REPORTED = "reported"
    INFERRED = "inferred"
    MIXED = "mixed"


class LevelKind(StrEnum):
    SWING_SUPPORT = "swing_support"
    SWING_RESISTANCE = "swing_resistance"
    SESSION_LOW = "session_low"
    SESSION_HIGH = "session_high"


class FairValueGapDirection(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"


class ProfileLocation(StrEnum):
    UNAVAILABLE = "unavailable"
    BELOW_VALUE = "below_value"
    LOWER_VALUE = "lower_value"
    AT_POC = "at_poc"
    UPPER_VALUE = "upper_value"
    ABOVE_VALUE = "above_value"


class AnalysisBar(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    timeframe: AnalyticsTimeframe
    open_ts: datetime
    close_ts: datetime
    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)
    volume: Decimal = Field(ge=0)
    source: str = Field(min_length=1)
    input_fidelity: AnalyticsInputFidelity

    @field_validator("open_ts", "close_ts")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _bar_must_be_consistent(self) -> AnalysisBar:
        if self.close_ts - self.open_ts != self.timeframe.duration:
            raise ValueError("analysis bar duration must match timeframe")
        if self.low > self.high or not self.low <= self.open <= self.high:
            raise ValueError("analysis bar open must be inside high/low")
        if not self.low <= self.close <= self.high:
            raise ValueError("analysis bar close must be inside high/low")
        return self


class ContextLevel(VersionedDomainModel):
    kind: LevelKind
    price: Decimal = Field(gt=0)
    observed_ts: datetime
    touches: int = Field(default=1, ge=1)

    @field_validator("observed_ts")
    @classmethod
    def _timestamp_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)


class ContextRange(VersionedDomainModel):
    label: str = Field(min_length=1)
    start_ts: datetime
    end_ts: datetime
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    is_complete: bool

    @field_validator("start_ts", "end_ts")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _range_must_be_consistent(self) -> ContextRange:
        if self.end_ts <= self.start_ts:
            raise ValueError("context range end must be after start")
        if self.low > self.high:
            raise ValueError("context range low cannot exceed high")
        return self


class FairValueGap(VersionedDomainModel):
    direction: FairValueGapDirection
    timeframe: AnalyticsTimeframe
    lower: Decimal = Field(gt=0)
    upper: Decimal = Field(gt=0)
    detected_ts: datetime
    is_filled: bool = False

    @field_validator("detected_ts")
    @classmethod
    def _timestamp_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _gap_must_be_consistent(self) -> FairValueGap:
        if self.lower >= self.upper:
            raise ValueError("fair value gap lower bound must be below upper bound")
        return self


class VolumeProfileSnapshot(VersionedDomainModel):
    bin_size: Decimal = Field(gt=0)
    value_area_fraction: Decimal = Field(gt=0, le=1)
    poc: Decimal = Field(gt=0)
    value_area_low: Decimal = Field(gt=0)
    value_area_high: Decimal = Field(gt=0)
    total_volume: Decimal = Field(gt=0)
    input_fidelity: AnalyticsInputFidelity
    methodology: str = Field(min_length=1)

    @model_validator(mode="after")
    def _profile_must_be_consistent(self) -> VolumeProfileSnapshot:
        if not self.value_area_low <= self.poc <= self.value_area_high:
            raise ValueError("profile POC must be inside its value area")
        return self


class CompositeVolumeProfileSnapshot(VersionedDomainModel):
    session_count: int = Field(ge=2)
    start_ts: datetime
    end_ts: datetime
    is_complete: bool
    profile: VolumeProfileSnapshot

    @field_validator("start_ts", "end_ts")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _window_must_be_consistent(self) -> CompositeVolumeProfileSnapshot:
        if self.end_ts <= self.start_ts:
            raise ValueError("composite profile end must be after start")
        return self


class MarketContextSnapshot(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    timeframe: AnalyticsTimeframe
    as_of: datetime
    source: str = Field(min_length=1)
    input_fidelity: AnalyticsInputFidelity
    bar_count: int = Field(ge=0)
    close: Decimal = Field(gt=0)
    ema_20: Decimal | None = None
    ema_50: Decimal | None = None
    ema_200: Decimal | None = None
    atr_14: Decimal | None = Field(default=None, ge=0)
    session_open: Decimal = Field(gt=0)
    session_high: Decimal = Field(gt=0)
    session_low: Decimal = Field(gt=0)
    session_vwap: Decimal | None = Field(default=None, gt=0)
    session_range_position: Decimal = Field(ge=0, le=1)
    vwap_position: VwapPosition
    trend: TrendState
    trend_reason_codes: tuple[str, ...] = Field(min_length=1)
    nearest_support: ContextLevel | None = None
    nearest_resistance: ContextLevel | None = None
    prior_session_high: Decimal | None = Field(default=None, gt=0)
    prior_session_low: Decimal | None = Field(default=None, gt=0)
    london_range: ContextRange | None = None
    new_york_range: ContextRange | None = None
    london_opening_range_15: ContextRange | None = None
    london_opening_range_30: ContextRange | None = None
    new_york_opening_range_15: ContextRange | None = None
    new_york_opening_range_30: ContextRange | None = None
    fair_value_gaps: tuple[FairValueGap, ...] = Field(default_factory=tuple)
    volume_profile: VolumeProfileSnapshot | None = None
    prior_volume_profile: VolumeProfileSnapshot | None = None
    london_volume_profile: VolumeProfileSnapshot | None = None
    new_york_volume_profile: VolumeProfileSnapshot | None = None
    composite_volume_profiles: tuple[CompositeVolumeProfileSnapshot, ...] = Field(
        default_factory=tuple,
    )
    profile_location: ProfileLocation = ProfileLocation.UNAVAILABLE
    location_reason_codes: tuple[str, ...] = Field(default_factory=tuple)
    direction_score: int = Field(default=0, ge=-2, le=2)
    direction_location_reason_codes: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("as_of")
    @classmethod
    def _as_of_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _levels_and_session_must_be_consistent(self) -> MarketContextSnapshot:
        if self.session_low > self.session_high:
            raise ValueError("session low cannot exceed session high")
        if self.nearest_support is not None and self.nearest_support.price > self.close:
            raise ValueError("nearest support cannot be above close")
        if self.nearest_resistance is not None and self.nearest_resistance.price < self.close:
            raise ValueError("nearest resistance cannot be below close")
        if (
            self.prior_session_low is not None
            and self.prior_session_high is not None
            and self.prior_session_low > self.prior_session_high
        ):
            raise ValueError("prior session low cannot exceed high")
        return self
