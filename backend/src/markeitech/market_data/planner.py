from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from markeitech.domain.base import VersionedDomainModel
from markeitech.domain.instruments import (
    InstrumentDataMode,
    InstrumentRegistryConfig,
    InstrumentRole,
    WarmupTimeframe,
)


class WarmupKind(StrEnum):
    HISTORICAL_BARS = "historical_bars"


class SubscriptionKind(StrEnum):
    TICK_LAST = "tick_last"
    TICK_BID_ASK = "tick_bid_ask"
    BAR_1M = "bar_1m"


class PlannedWarmup(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    kind: WarmupKind
    lookback_sessions: int = Field(ge=1)
    timeframes: tuple[WarmupTimeframe, ...] = Field(min_length=1)
    annotate_support_resistance: bool
    annotate_emas: bool
    annotate_trend: bool
    annotate_vwap: bool
    annotate_fvgs: bool


class PlannedSubscription(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    kind: SubscriptionKind
    source: str = Field(default="nautilus_ib", min_length=1)
    owned_by: str = Field(default="market_data_runtime", min_length=1)


class MarketDataRuntimePlan(VersionedDomainModel):
    active_instrument_id: str = Field(min_length=1)
    warmups: tuple[PlannedWarmup, ...] = Field(default_factory=tuple)
    subscriptions: tuple[PlannedSubscription, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _plan_must_not_duplicate_subscription_ownership(self) -> MarketDataRuntimePlan:
        keys = [
            (subscription.instrument_id, subscription.kind) for subscription in self.subscriptions
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("subscription plan contains duplicate stream ownership")
        return self


def build_market_data_plan(registry: InstrumentRegistryConfig) -> MarketDataRuntimePlan:
    warmups: list[PlannedWarmup] = []
    subscriptions: list[PlannedSubscription] = []

    for runtime in registry.instruments:
        if not runtime.enabled:
            continue
        if runtime.warmup is None:
            raise ValueError("enabled instruments require warmup configuration")
        warmups.append(
            PlannedWarmup(
                instrument_id=runtime.contract.instrument_id,
                kind=WarmupKind.HISTORICAL_BARS,
                lookback_sessions=runtime.warmup.lookback_sessions,
                timeframes=runtime.warmup.timeframes,
                annotate_support_resistance=runtime.warmup.annotate_support_resistance,
                annotate_emas=runtime.warmup.annotate_emas,
                annotate_trend=runtime.warmup.annotate_trend,
                annotate_vwap=runtime.warmup.annotate_vwap,
                annotate_fvgs=runtime.warmup.annotate_fvgs,
            )
        )
        if runtime.role == InstrumentRole.ACTIVE:
            subscriptions.extend(
                [
                    PlannedSubscription(
                        instrument_id=runtime.contract.instrument_id,
                        kind=SubscriptionKind.TICK_LAST,
                    ),
                    PlannedSubscription(
                        instrument_id=runtime.contract.instrument_id,
                        kind=SubscriptionKind.TICK_BID_ASK,
                    ),
                    PlannedSubscription(
                        instrument_id=runtime.contract.instrument_id,
                        kind=SubscriptionKind.BAR_1M,
                    ),
                ]
            )
        elif runtime.role == InstrumentRole.BACKGROUND:
            if runtime.data_mode != InstrumentDataMode.LIVE_1M_BARS:
                raise ValueError("background instruments must track live 1m bars")
            subscriptions.append(
                PlannedSubscription(
                    instrument_id=runtime.contract.instrument_id,
                    kind=SubscriptionKind.BAR_1M,
                )
            )

    return MarketDataRuntimePlan(
        active_instrument_id=registry.active_instrument_id,
        warmups=tuple(warmups),
        subscriptions=tuple(subscriptions),
    )
