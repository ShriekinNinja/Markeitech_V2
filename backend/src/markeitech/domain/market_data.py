from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import Field, computed_field, field_validator, model_validator

from markeitech.domain.base import InstrumentEvent, require_utc


class TradeSide(StrEnum):
    BUY = "buy"
    SELL = "sell"
    UNKNOWN = "unknown"


class BarInterval(StrEnum):
    ONE_MINUTE = "1m"


class CanonicalTradeTick(InstrumentEvent):
    price: Decimal = Field(gt=0)
    size: Decimal = Field(gt=0)
    sequence: int | None = Field(default=None, ge=0)
    source_trade_id: str | None = Field(default=None, min_length=1)
    source: str = Field(default="ib", min_length=1)

    @computed_field
    @property
    def dedupe_key(self) -> str:
        sequence = "none" if self.sequence is None else str(self.sequence)
        source_trade_id = self.source_trade_id or "none"
        event_time = self.event_ts_ns if self.event_ts_ns is not None else self.event_ts.isoformat()
        return (
            f"trade:{self.instrument_id}:{event_time}:"
            f"{self.price}:{self.size}:{sequence}:{source_trade_id}:{self.source}"
        )


class CanonicalQuoteTick(InstrumentEvent):
    bid_price: Decimal = Field(gt=0)
    ask_price: Decimal = Field(gt=0)
    bid_size: Decimal = Field(ge=0)
    ask_size: Decimal = Field(ge=0)
    sequence: int | None = Field(default=None, ge=0)
    source: str = Field(default="ib", min_length=1)

    @model_validator(mode="after")
    def _ask_must_not_be_below_bid(self) -> CanonicalQuoteTick:
        if self.ask_price < self.bid_price:
            raise ValueError("ask price must be greater than or equal to bid price")
        return self

    @computed_field
    @property
    def dedupe_key(self) -> str:
        sequence = "none" if self.sequence is None else str(self.sequence)
        event_time = self.event_ts_ns if self.event_ts_ns is not None else self.event_ts.isoformat()
        return (
            f"quote:{self.instrument_id}:{event_time}:"
            f"{self.bid_price}:{self.ask_price}:{self.bid_size}:{self.ask_size}:"
            f"{sequence}:{self.source}"
        )


class ClassifiedTrade(InstrumentEvent):
    trade: CanonicalTradeTick
    side: TradeSide
    quote: CanonicalQuoteTick | None = None
    classification_reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def _trade_identity_must_match_event(self) -> ClassifiedTrade:
        if self.trade.instrument_id != self.instrument_id:
            raise ValueError("classified trade instrument must match source trade")
        if self.trade.event_ts != self.event_ts:
            raise ValueError("classified trade timestamp must match source trade")
        if self.quote is not None and self.quote.instrument_id != self.instrument_id:
            raise ValueError("quote instrument must match classified trade")
        return self

    @computed_field
    @property
    def buy_volume(self) -> Decimal:
        return self.trade.size if self.side == TradeSide.BUY else Decimal("0")

    @computed_field
    @property
    def sell_volume(self) -> Decimal:
        return self.trade.size if self.side == TradeSide.SELL else Decimal("0")

    @computed_field
    @property
    def unknown_volume(self) -> Decimal:
        return self.trade.size if self.side == TradeSide.UNKNOWN else Decimal("0")

    @computed_field
    @property
    def delta(self) -> Decimal:
        return self.buy_volume - self.sell_volume

    @computed_field
    @property
    def classified_volume_ratio(self) -> Decimal:
        if self.side == TradeSide.UNKNOWN:
            return Decimal("0")
        return Decimal("1")


class OneMinuteBar(InstrumentEvent):
    interval: BarInterval = Field(default=BarInterval.ONE_MINUTE)
    open_ts: datetime
    close_ts: datetime
    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)
    volume: Decimal = Field(ge=0)
    buy_volume: Decimal = Field(ge=0)
    sell_volume: Decimal = Field(ge=0)
    unknown_volume: Decimal = Field(ge=0)
    source: str = Field(default="ib", min_length=1)
    is_revision: bool = False
    is_complete: bool = True

    @field_validator("open_ts", "close_ts")
    @classmethod
    def _bar_timestamps_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _bar_values_must_be_consistent(self) -> OneMinuteBar:
        if self.close_ts <= self.open_ts:
            raise ValueError("bar close timestamp must be after open timestamp")
        if self.low > self.high:
            raise ValueError("bar low cannot be above high")
        if not (self.low <= self.open <= self.high):
            raise ValueError("bar open must be inside high/low range")
        if not (self.low <= self.close <= self.high):
            raise ValueError("bar close must be inside high/low range")
        classified_total = self.buy_volume + self.sell_volume + self.unknown_volume
        if classified_total != self.volume:
            raise ValueError("classified volumes must equal total bar volume")
        return self

    @computed_field
    @property
    def delta(self) -> Decimal:
        return self.buy_volume - self.sell_volume

    @computed_field
    @property
    def classified_volume_ratio(self) -> Decimal:
        if self.volume == 0:
            return Decimal("0")
        return (self.buy_volume + self.sell_volume) / self.volume

    @computed_field
    @property
    def dedupe_key(self) -> str:
        return f"bar:{self.instrument_id}:{self.interval}:{self.open_ts.isoformat()}"
