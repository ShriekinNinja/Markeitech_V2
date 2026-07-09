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
    DAY = "DAY"


class NautilusWarmupIntent(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    kind: NautilusIntentKind = Field(default=NautilusIntentKind.HISTORICAL_BARS)
    lookback_sessions: int = Field(ge=1)
    timeframes: tuple[WarmupTimeframe, ...] = Field(min_length=1)
    bar_types: tuple[str, ...] = Field(min_length=1)


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
    if timeframe == WarmupTimeframe.DAILY:
        return f"{instrument_id}-1-DAY-{NautilusBarPriceType.LAST}-EXTERNAL"
    amount = timeframe.value.removesuffix("m").removesuffix("h")
    aggregation = (
        NautilusBarAggregation.MINUTE
        if timeframe.value.endswith("m")
        else NautilusBarAggregation.MINUTE
    )
    if timeframe.value.endswith("h"):
        amount = str(int(amount) * 60)
    return f"{instrument_id}-{amount}-{aggregation}-{NautilusBarPriceType.LAST}-EXTERNAL"
