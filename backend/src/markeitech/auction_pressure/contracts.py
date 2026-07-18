from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import Field, computed_field, field_validator, model_validator

from markeitech.domain.base import VersionedDomainModel, require_utc


class AuctionPressureFidelity(StrEnum):
    INFERRED = "inferred"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class BarPressureDirection(StrEnum):
    UPWARD = "upward"
    DOWNWARD = "downward"
    MIXED = "mixed"


class BarPressureProxySnapshot(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    start_ts: datetime
    end_ts: datetime
    as_of: datetime
    source: str = Field(default="ib", min_length=1)
    fidelity: AuctionPressureFidelity = AuctionPressureFidelity.PARTIAL
    direction: BarPressureDirection
    window_bars: int = Field(ge=1)
    up_bar_count: int = Field(ge=0)
    down_bar_count: int = Field(ge=0)
    flat_bar_count: int = Field(ge=0)
    price_change: Decimal
    atr_fraction: Decimal | None = None
    close_location: Decimal = Field(ge=0, le=1)
    total_volume: Decimal = Field(ge=0)
    pace_ratio: Decimal | None = Field(default=None, gt=0)

    @field_validator("start_ts", "end_ts", "as_of")
    @classmethod
    def _bar_pressure_timestamps_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _bar_pressure_counts_must_be_consistent(self) -> BarPressureProxySnapshot:
        if self.end_ts <= self.start_ts:
            raise ValueError("bar-pressure end must follow start")
        if self.end_ts > self.as_of:
            raise ValueError("bar-pressure window cannot end after as-of")
        if self.up_bar_count + self.down_bar_count + self.flat_bar_count != self.window_bars:
            raise ValueError("bar-pressure counts must equal window bars")
        if self.source != "ib" or self.fidelity != AuctionPressureFidelity.PARTIAL:
            raise ValueError("bar-pressure proxy must remain partial reported IB evidence")
        return self


class SessionAuctionPressureSnapshot(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    session_start: datetime
    session_end: datetime
    as_of: datetime
    source: str = Field(min_length=1)
    method: str = Field(default="quote_test_with_tick_rule", min_length=1)
    fidelity: AuctionPressureFidelity
    trade_count: int = Field(ge=1)
    classified_trade_count: int = Field(ge=0)
    unknown_trade_count: int = Field(ge=0)
    buy_volume: Decimal = Field(ge=0)
    sell_volume: Decimal = Field(ge=0)
    unknown_volume: Decimal = Field(ge=0)
    sequence_gap_count: int = Field(default=0, ge=0)
    duplicate_count: int = Field(default=0, ge=0)
    stale_count: int = Field(default=0, ge=0)
    classification_reason_counts: dict[str, int] = Field(default_factory=dict)

    @field_validator("session_start", "session_end", "as_of")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _snapshot_must_be_consistent(self) -> SessionAuctionPressureSnapshot:
        if self.session_end <= self.session_start:
            raise ValueError("auction-pressure session end must follow start")
        if not self.session_start <= self.as_of < self.session_end:
            raise ValueError("auction-pressure as-of must belong to its session")
        if self.classified_trade_count + self.unknown_trade_count != self.trade_count:
            raise ValueError("auction-pressure trade counts must conserve total trades")
        if any(count <= 0 for count in self.classification_reason_counts.values()):
            raise ValueError("classification reason counts must be positive")
        if sum(self.classification_reason_counts.values()) != self.trade_count:
            raise ValueError("classification reason counts must conserve total trades")
        if self.total_volume <= 0:
            raise ValueError("auction-pressure snapshot requires positive observed volume")
        expected_fidelity = _expected_fidelity(
            classified_volume=self.classified_volume,
            unknown_volume=self.unknown_volume,
            sequence_gap_count=self.sequence_gap_count,
        )
        if self.fidelity != expected_fidelity:
            raise ValueError(
                f"auction-pressure fidelity must be {expected_fidelity.value!r} "
                "for the observed coverage and gaps"
            )
        return self

    @computed_field
    @property
    def classified_volume(self) -> Decimal:
        return self.buy_volume + self.sell_volume

    @computed_field
    @property
    def total_volume(self) -> Decimal:
        return self.classified_volume + self.unknown_volume

    @computed_field
    @property
    def delta(self) -> Decimal:
        return self.buy_volume - self.sell_volume

    @computed_field
    @property
    def cvd(self) -> Decimal:
        """Product-session CVD; the session reset makes this cumulative delta."""
        return self.delta

    @computed_field
    @property
    def delta_ratio(self) -> Decimal | None:
        if self.classified_volume == 0:
            return None
        return self.delta / self.classified_volume

    @computed_field
    @property
    def classified_volume_ratio(self) -> Decimal:
        if self.total_volume == 0:
            return Decimal("0")
        return self.classified_volume / self.total_volume



def _expected_fidelity(
    *,
    classified_volume: Decimal,
    unknown_volume: Decimal,
    sequence_gap_count: int,
) -> AuctionPressureFidelity:
    if classified_volume == 0:
        return AuctionPressureFidelity.UNAVAILABLE
    if unknown_volume > 0 or sequence_gap_count > 0:
        return AuctionPressureFidelity.PARTIAL
    return AuctionPressureFidelity.INFERRED
