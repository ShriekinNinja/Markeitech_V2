from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol

from pydantic import Field, field_validator, model_validator

from markeitech.domain.base import VersionedDomainModel, require_utc
from markeitech.market_data.intents import (
    NautilusIntentKind,
    NautilusRequestPlan,
    NautilusSubscriptionIntent,
    NautilusWarmupIntent,
)


class LiveNodeActionKind(StrEnum):
    REQUEST_HISTORICAL_BARS = "request_historical_bars"
    SUBSCRIBE_TRADE_TICKS = "subscribe_trade_ticks"
    SUBSCRIBE_QUOTE_TICKS = "subscribe_quote_ticks"
    SUBSCRIBE_BARS = "subscribe_bars"


class LiveNodeActionPhase(StrEnum):
    WARMUP = "warmup"
    LIVE_SUBSCRIPTION = "live_subscription"


class LiveNodeAction(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    kind: LiveNodeActionKind
    phase: LiveNodeActionPhase
    data_client_name: str = Field(default="IB", min_length=1)
    bar_type: str | None = None
    lookback_sessions: int | None = Field(default=None, ge=1)
    request_start_ts: datetime | None = None
    request_end_ts: datetime | None = None
    recovery_request_id: str | None = Field(default=None, min_length=1)

    @field_validator("request_start_ts", "request_end_ts")
    @classmethod
    def _request_timestamps_must_be_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @model_validator(mode="after")
    def _action_shape_must_match_kind(self) -> LiveNodeAction:
        if self.kind in {
            LiveNodeActionKind.REQUEST_HISTORICAL_BARS,
            LiveNodeActionKind.SUBSCRIBE_BARS,
        }:
            if self.bar_type is None:
                raise ValueError("bar actions require bar_type")
        else:
            if self.bar_type is not None:
                raise ValueError("tick actions must not include bar_type")
        if self.kind == LiveNodeActionKind.REQUEST_HISTORICAL_BARS:
            if self.phase != LiveNodeActionPhase.WARMUP:
                raise ValueError("historical bar requests must be warmup actions")
            has_lookback = self.lookback_sessions is not None
            has_range = self.request_start_ts is not None and self.request_end_ts is not None
            if has_lookback == has_range:
                raise ValueError("historical bar requests require one lookback or exact range")
            if (
                has_range
                and self.request_start_ts is not None
                and self.request_end_ts is not None
                and self.request_end_ts <= self.request_start_ts
            ):
                raise ValueError("historical bar request range must be positive")
            if has_range != (self.recovery_request_id is not None):
                raise ValueError("exact historical range requires recovery request id")
        if self.kind != LiveNodeActionKind.REQUEST_HISTORICAL_BARS and any(
            value is not None
            for value in (
                self.lookback_sessions,
                self.request_start_ts,
                self.request_end_ts,
                self.recovery_request_id,
            )
        ):
            raise ValueError("live subscription actions must not include request range")
        return self


class LiveNodeActionPlan(VersionedDomainModel):
    active_instrument_id: str = Field(min_length=1)
    actions: tuple[LiveNodeAction, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _action_plan_must_not_duplicate_actions(self) -> LiveNodeActionPlan:
        keys = [
            (action.instrument_id, action.kind, action.bar_type, action.phase)
            + (
                action.request_start_ts,
                action.request_end_ts,
                action.recovery_request_id,
            )
            for action in self.actions
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("LiveNode action plan contains duplicate actions")
        return self


class LiveNodeActionTarget(Protocol):
    def request_historical_bars(
        self,
        *,
        instrument_id: str,
        bar_type: str,
        lookback_sessions: int | None,
        request_start_ts: datetime | None = None,
        request_end_ts: datetime | None = None,
        data_client_name: str,
        callback: Callable[[Any], None] | None = None,
    ) -> Any: ...

    def subscribe_trade_ticks(
        self,
        *,
        instrument_id: str,
        data_client_name: str,
    ) -> Any: ...

    def subscribe_quote_ticks(
        self,
        *,
        instrument_id: str,
        data_client_name: str,
    ) -> Any: ...

    def subscribe_bars(
        self,
        *,
        instrument_id: str,
        bar_type: str,
        data_client_name: str,
    ) -> Any: ...


def build_livenode_action_plan(request_plan: NautilusRequestPlan) -> LiveNodeActionPlan:
    actions: list[LiveNodeAction] = []
    for warmup in request_plan.warmups:
        actions.extend(_warmup_actions(warmup))
    for subscription in request_plan.subscriptions:
        actions.append(_subscription_action(subscription))
    return LiveNodeActionPlan(
        active_instrument_id=request_plan.active_instrument_id,
        actions=tuple(actions),
    )


def execute_livenode_action_plan(
    action_plan: LiveNodeActionPlan,
    target: LiveNodeActionTarget,
) -> list[Any]:
    results: list[Any] = []
    for action in action_plan.actions:
        results.append(_execute_action(action, target))
    return results


def execute_livenode_action(
    action: LiveNodeAction,
    target: LiveNodeActionTarget,
    *,
    callback: Callable[[Any], None] | None = None,
) -> Any:
    return _execute_action(action, target, callback=callback)


def _warmup_actions(warmup: NautilusWarmupIntent) -> list[LiveNodeAction]:
    return [
        LiveNodeAction(
            instrument_id=warmup.instrument_id,
            kind=LiveNodeActionKind.REQUEST_HISTORICAL_BARS,
            phase=LiveNodeActionPhase.WARMUP,
            bar_type=bar_type,
            lookback_sessions=warmup.lookback_for(timeframe),
        )
        for timeframe, bar_type in zip(warmup.timeframes, warmup.bar_types, strict=True)
    ]


def _subscription_action(subscription: NautilusSubscriptionIntent) -> LiveNodeAction:
    if subscription.kind == NautilusIntentKind.SUBSCRIBE_TRADE_TICKS:
        return LiveNodeAction(
            instrument_id=subscription.instrument_id,
            kind=LiveNodeActionKind.SUBSCRIBE_TRADE_TICKS,
            phase=LiveNodeActionPhase.LIVE_SUBSCRIPTION,
            data_client_name=subscription.data_client_name,
        )
    if subscription.kind == NautilusIntentKind.SUBSCRIBE_QUOTE_TICKS:
        return LiveNodeAction(
            instrument_id=subscription.instrument_id,
            kind=LiveNodeActionKind.SUBSCRIBE_QUOTE_TICKS,
            phase=LiveNodeActionPhase.LIVE_SUBSCRIPTION,
            data_client_name=subscription.data_client_name,
        )
    if subscription.kind == NautilusIntentKind.SUBSCRIBE_BARS:
        return LiveNodeAction(
            instrument_id=subscription.instrument_id,
            kind=LiveNodeActionKind.SUBSCRIBE_BARS,
            phase=LiveNodeActionPhase.LIVE_SUBSCRIPTION,
            data_client_name=subscription.data_client_name,
            bar_type=subscription.bar_type,
        )
    raise ValueError(f"unsupported Nautilus intent kind: {subscription.kind}")


def _execute_action(
    action: LiveNodeAction,
    target: LiveNodeActionTarget,
    *,
    callback: Callable[[Any], None] | None = None,
) -> Any:
    if action.kind == LiveNodeActionKind.REQUEST_HISTORICAL_BARS:
        if action.bar_type is None:
            raise RuntimeError("historical bar action missing required fields")
        request_kwargs: dict[str, Any] = dict(
            instrument_id=action.instrument_id,
            bar_type=action.bar_type,
            lookback_sessions=action.lookback_sessions,
            data_client_name=action.data_client_name,
            callback=callback,
        )
        if action.request_start_ts is not None:
            request_kwargs["request_start_ts"] = action.request_start_ts
            request_kwargs["request_end_ts"] = action.request_end_ts
        return target.request_historical_bars(**request_kwargs)
    if action.kind == LiveNodeActionKind.SUBSCRIBE_TRADE_TICKS:
        return target.subscribe_trade_ticks(
            instrument_id=action.instrument_id,
            data_client_name=action.data_client_name,
        )
    if action.kind == LiveNodeActionKind.SUBSCRIBE_QUOTE_TICKS:
        return target.subscribe_quote_ticks(
            instrument_id=action.instrument_id,
            data_client_name=action.data_client_name,
        )
    if action.kind == LiveNodeActionKind.SUBSCRIBE_BARS:
        if action.bar_type is None:
            raise RuntimeError("bar subscription action missing bar_type")
        return target.subscribe_bars(
            instrument_id=action.instrument_id,
            bar_type=action.bar_type,
            data_client_name=action.data_client_name,
        )
    raise ValueError(f"unsupported LiveNode action kind: {action.kind}")
