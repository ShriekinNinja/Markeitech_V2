from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from markeitech.domain.base import VersionedDomainModel
from markeitech.domain.instruments import WarmupTimeframe
from markeitech.market_data.planner import (
    MarketDataRuntimePlan,
    PlannedSubscription,
    PlannedWarmup,
    SubscriptionKind,
)


class NautilusIntentKind(StrEnum):
    HISTORICAL_BARS = "historical_bars"
    SUBSCRIBE_TRADE_TICKS = "subscribe_trade_ticks"
    SUBSCRIBE_QUOTE_TICKS = "subscribe_quote_ticks"
    SUBSCRIBE_BARS = "subscribe_bars"


class NautilusBarPriceType(StrEnum):
    LAST = "LAST"


class NautilusBarAggregation(StrEnum):
    MINUTE = "MINUTE"
    HOUR = "HOUR"
    DAY = "DAY"


class NautilusWarmupIntent(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    kind: NautilusIntentKind = Field(default=NautilusIntentKind.HISTORICAL_BARS)
    lookback_sessions: int = Field(ge=1)
    lookback_sessions_by_timeframe: dict[WarmupTimeframe, int] = Field(
        default_factory=dict,
    )
    timeframes: tuple[WarmupTimeframe, ...] = Field(min_length=1)
    bar_types: tuple[str, ...] = Field(min_length=1)

    def lookback_for(self, timeframe: WarmupTimeframe) -> int:
        if timeframe not in self.timeframes:
            raise ValueError(f"timeframe {timeframe.value} is not requested for warmup")
        return self.lookback_sessions_by_timeframe.get(timeframe, self.lookback_sessions)


class NautilusSubscriptionIntent(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    kind: NautilusIntentKind
    subscription_kind: SubscriptionKind
    data_client_name: str = Field(default="IB", min_length=1)
    bar_type: str | None = None

    @model_validator(mode="after")
    def _bar_subscriptions_must_include_bar_type(self) -> NautilusSubscriptionIntent:
        if self.kind == NautilusIntentKind.SUBSCRIBE_BARS and self.bar_type is None:
            raise ValueError("bar subscription intents require bar_type")
        if self.kind != NautilusIntentKind.SUBSCRIBE_BARS and self.bar_type is not None:
            raise ValueError("tick subscription intents must not include bar_type")
        return self


class NautilusRequestPlan(VersionedDomainModel):
    active_instrument_id: str = Field(min_length=1)
    warmups: tuple[NautilusWarmupIntent, ...] = Field(default_factory=tuple)
    subscriptions: tuple[NautilusSubscriptionIntent, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _request_plan_must_not_duplicate_subscription_intents(self) -> NautilusRequestPlan:
        keys = [
            (subscription.instrument_id, subscription.kind, subscription.bar_type)
            for subscription in self.subscriptions
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("Nautilus request plan contains duplicate subscription intents")
        return self


def build_nautilus_request_plan(
    plan: MarketDataRuntimePlan,
    *,
    data_client_name: str = "IB",
) -> NautilusRequestPlan:
    return NautilusRequestPlan(
        active_instrument_id=plan.active_instrument_id,
        warmups=tuple(_warmup_intent(warmup) for warmup in plan.warmups),
        subscriptions=tuple(
            _subscription_intent(subscription, data_client_name=data_client_name)
            for subscription in plan.subscriptions
        ),
    )


def _warmup_intent(warmup: PlannedWarmup) -> NautilusWarmupIntent:
    return NautilusWarmupIntent(
        instrument_id=warmup.instrument_id,
        lookback_sessions=warmup.lookback_sessions,
        lookback_sessions_by_timeframe={
            timeframe: warmup.lookback_for(timeframe) for timeframe in warmup.timeframes
        },
        timeframes=warmup.timeframes,
        bar_types=tuple(
            _bar_type(warmup.instrument_id, timeframe) for timeframe in warmup.timeframes
        ),
    )


def _subscription_intent(
    subscription: PlannedSubscription,
    *,
    data_client_name: str,
) -> NautilusSubscriptionIntent:
    if subscription.kind == SubscriptionKind.TICK_LAST:
        return NautilusSubscriptionIntent(
            instrument_id=subscription.instrument_id,
            kind=NautilusIntentKind.SUBSCRIBE_TRADE_TICKS,
            subscription_kind=subscription.kind,
            data_client_name=data_client_name,
        )
    if subscription.kind == SubscriptionKind.TICK_BID_ASK:
        return NautilusSubscriptionIntent(
            instrument_id=subscription.instrument_id,
            kind=NautilusIntentKind.SUBSCRIBE_QUOTE_TICKS,
            subscription_kind=subscription.kind,
            data_client_name=data_client_name,
        )
    if subscription.kind == SubscriptionKind.BAR_1M:
        return NautilusSubscriptionIntent(
            instrument_id=subscription.instrument_id,
            kind=NautilusIntentKind.SUBSCRIBE_BARS,
            subscription_kind=subscription.kind,
            data_client_name=data_client_name,
            bar_type=_bar_type(subscription.instrument_id, WarmupTimeframe.ONE_MINUTE),
        )
    raise ValueError(f"unsupported subscription kind: {subscription.kind}")


def _bar_type(instrument_id: str, timeframe: WarmupTimeframe) -> str:
    amount, aggregation = {
        WarmupTimeframe.ONE_MINUTE: (1, NautilusBarAggregation.MINUTE),
        WarmupTimeframe.FIVE_MINUTE: (5, NautilusBarAggregation.MINUTE),
        WarmupTimeframe.FIFTEEN_MINUTE: (15, NautilusBarAggregation.MINUTE),
        WarmupTimeframe.THIRTY_MINUTE: (30, NautilusBarAggregation.MINUTE),
        WarmupTimeframe.ONE_HOUR: (1, NautilusBarAggregation.HOUR),
        WarmupTimeframe.DAILY: (1, NautilusBarAggregation.DAY),
    }[timeframe]
    return f"{instrument_id}-{amount}-{aggregation}-{NautilusBarPriceType.LAST}-EXTERNAL"
