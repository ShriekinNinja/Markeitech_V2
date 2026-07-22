from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import Field, computed_field, field_validator, model_validator

from markeitech.domain.base import VersionedDomainModel, require_utc
from markeitech.domain.market_data import TradeSide


class AggressionOutcome(StrEnum):
    PENDING = "pending"
    WITH_FLOW = "with_flow"
    ABSORBED = "absorbed"
    TRAPPED = "trapped"
    UNRESOLVED = "unresolved"


class AggressionEpisode(VersionedDomainModel):
    origin_id: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    side: TradeSide
    anchor_price: Decimal = Field(gt=0)
    observed_size: Decimal = Field(gt=0)
    print_count: int = Field(ge=1)
    opened_ts: datetime
    expires_ts: datetime
    as_of: datetime
    baseline_cvd: Decimal
    latest_cvd: Decimal
    latest_price: Decimal = Field(gt=0)
    max_favorable_excursion: Decimal = Field(default=Decimal("0"), ge=0)
    max_adverse_excursion: Decimal = Field(default=Decimal("0"), ge=0)
    observed_trade_count: int = Field(default=0, ge=0)
    outcome: AggressionOutcome = AggressionOutcome.PENDING
    location_label: str | None = None
    location_price: Decimal | None = Field(default=None, gt=0)
    source: str = Field(min_length=1)
    fidelity: str = Field(min_length=1)
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator("opened_ts", "expires_ts", "as_of")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _episode_must_be_temporally_consistent(self) -> AggressionEpisode:
        if self.expires_ts <= self.opened_ts:
            raise ValueError("aggression episode expiry must follow its opening")
        if self.as_of < self.opened_ts:
            raise ValueError("aggression episode cannot precede its opening")
        if (self.location_label is None) != (self.location_price is None):
            raise ValueError("aggression location label and price must appear together")
        return self

    @computed_field
    @property
    def episode_id(self) -> str:
        payload = (
            f"{self.instrument_id}|{self.side.value}|{self.origin_id}|"
            f"{self.opened_ts.isoformat()}"
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    @computed_field
    @property
    def cvd_change(self) -> Decimal:
        return self.latest_cvd - self.baseline_cvd
