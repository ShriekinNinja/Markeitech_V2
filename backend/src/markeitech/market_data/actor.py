from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, Protocol

from nautilus_trader.common.actor import Actor
from nautilus_trader.model.data import BarType
from nautilus_trader.model.identifiers import ClientId, InstrumentId

from markeitech.domain.events import ActiveInstrumentChangedEvent
from markeitech.domain.market_data import OneMinuteBar
from markeitech.market_data.actions import (
    LiveNodeAction,
    LiveNodeActionKind,
    LiveNodeActionPhase,
    LiveNodeActionPlan,
)
from markeitech.market_data.coordinator import (
    WarmupCoordinator,
    WarmupReadyHandler,
    WarmupState,
)
from markeitech.market_data.health import (
    MarketDataHealthMonitor,
    MarketDataHealthSink,
    MarketDataHealthSnapshot,
    SessionOpenResolver,
)
from markeitech.market_data.normalization import normalize_one_minute_bar
from markeitech.market_data.routing import (
    InstrumentMarketDataSnapshot,
    LiveMarketDataRouter,
    MarketDataEventSink,
)
from markeitech.market_data.switching import (
    ActiveInstrumentSwitchCoordinator,
    ActiveInstrumentSwitchRequest,
    ActiveSwitchSnapshot,
)


class NautilusActorApi(Protocol):
    def request_bars(self, bar_type: Any, start: datetime, **kwargs: Any) -> Any: ...

    def subscribe_trade_ticks(self, instrument_id: Any, **kwargs: Any) -> Any: ...

    def subscribe_quote_ticks(self, instrument_id: Any, **kwargs: Any) -> Any: ...

    def subscribe_bars(self, bar_type: Any, **kwargs: Any) -> Any: ...

    def unsubscribe_trade_ticks(self, instrument_id: Any, **kwargs: Any) -> Any: ...

    def unsubscribe_quote_ticks(self, instrument_id: Any, **kwargs: Any) -> Any: ...


WarmupStartResolver = Callable[[int, datetime], datetime]
NativeMarketDataSink = Callable[[object], None]
HistoricalBarSink = Callable[[OneMinuteBar], bool]


class StartupRecoveryServiceLike(Protocol):
    @property
    def snapshot(self) -> Any: ...

    def observe_bar(self, bar: OneMinuteBar, *, accepted: bool) -> None: ...

    def prepare(self, now: datetime) -> tuple[Any, ...]: ...

    def finish(self, now: datetime) -> Any: ...


class ActorStartupRecoveryHook:
    def __init__(
        self,
        service: StartupRecoveryServiceLike,
        *,
        data_client_name: str,
        now: Callable[[], datetime],
    ) -> None:
        self._service = service
        self._data_client_name = data_client_name
        self._now = now

    def prepare(self) -> tuple[LiveNodeAction, ...]:
        return tuple(
            LiveNodeAction(
                instrument_id=request.instrument_id,
                kind=LiveNodeActionKind.REQUEST_HISTORICAL_BARS,
                phase=LiveNodeActionPhase.WARMUP,
                data_client_name=self._data_client_name,
                bar_type=f"{request.instrument_id}-1-MINUTE-LAST-EXTERNAL",
                request_start_ts=request.start_ts,
                request_end_ts=request.end_ts,
                recovery_request_id=request.request_id,
            )
            for request in self._service.prepare(self._now())
        )

    def finish(self) -> None:
        self._service.finish(self._now())


class NautilusActorActionTarget:
    def __init__(
        self,
        actor: NautilusActorApi,
        *,
        now: Callable[[], datetime],
        resolve_warmup_start: WarmupStartResolver | None = None,
    ) -> None:
        self._actor = actor
        self._now = now
        self._resolve_warmup_start = resolve_warmup_start or conservative_warmup_start

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
    ) -> Any:
        del instrument_id
        end = request_end_ts or self._now()
        start = request_start_ts
        if start is None:
            if lookback_sessions is None:
                raise ValueError("historical request requires lookback sessions or exact range")
            start = self._resolve_warmup_start(lookback_sessions, end)
        return self._actor.request_bars(
            BarType.from_str(bar_type),
            start=start,
            end=end,
            client_id=ClientId(data_client_name),
            callback=callback,
        )

    def subscribe_trade_ticks(
        self,
        *,
        instrument_id: str,
        data_client_name: str,
    ) -> Any:
        return self._actor.subscribe_trade_ticks(
            InstrumentId.from_str(instrument_id),
            client_id=ClientId(data_client_name),
        )

    def subscribe_quote_ticks(
        self,
        *,
        instrument_id: str,
        data_client_name: str,
    ) -> Any:
        return self._actor.subscribe_quote_ticks(
            InstrumentId.from_str(instrument_id),
            client_id=ClientId(data_client_name),
        )

    def subscribe_bars(
        self,
        *,
        instrument_id: str,
        bar_type: str,
        data_client_name: str,
    ) -> Any:
        del instrument_id
        return self._actor.subscribe_bars(
            BarType.from_str(bar_type),
            client_id=ClientId(data_client_name),
        )

    def unsubscribe_trade_ticks(
        self,
        *,
        instrument_id: str,
        data_client_name: str,
    ) -> Any:
        return self._actor.unsubscribe_trade_ticks(
            InstrumentId.from_str(instrument_id),
            client_id=ClientId(data_client_name),
        )

    def unsubscribe_quote_ticks(
        self,
        *,
        instrument_id: str,
        data_client_name: str,
    ) -> Any:
        return self._actor.unsubscribe_quote_ticks(
            InstrumentId.from_str(instrument_id),
            client_id=ClientId(data_client_name),
        )


class MarkeitechMarketDataActor(Actor):
    def __init__(
        self,
        action_plan: LiveNodeActionPlan,
        *,
        on_warmup_ready: WarmupReadyHandler,
        on_active_instrument_changed: Callable[[ActiveInstrumentChangedEvent], None] | None = None,
        on_market_data_event: MarketDataEventSink | None = None,
        on_native_market_data_event: NativeMarketDataSink | None = None,
        on_historical_bar: HistoricalBarSink | None = None,
        startup_recovery: StartupRecoveryServiceLike | None = None,
        on_market_data_health: MarketDataHealthSink | None = None,
        is_session_open: SessionOpenResolver | None = None,
        resolve_warmup_start: WarmupStartResolver | None = None,
    ) -> None:
        super().__init__()
        target = NautilusActorActionTarget(
            self,
            now=lambda: self.clock.utc_now(),
            resolve_warmup_start=resolve_warmup_start,
        )
        if startup_recovery is not None and on_historical_bar is None:
            raise ValueError("startup recovery requires a historical bar persistence sink")
        data_client_names = {action.data_client_name for action in action_plan.actions}
        if len(data_client_names) != 1:
            raise ValueError("market-data actor requires exactly one data client")
        data_client_name = next(iter(data_client_names))
        recovery_hook = (
            ActorStartupRecoveryHook(
                startup_recovery,
                data_client_name=data_client_name,
                now=lambda: self.clock.utc_now(),
            )
            if startup_recovery is not None
            else None
        )
        self._warmup = WarmupCoordinator(
            action_plan,
            target,
            on_warmup_ready=on_warmup_ready,
            startup_recovery=recovery_hook,
        )
        enabled_instrument_ids = {
            action.instrument_id
            for action in action_plan.actions
            if action.phase == LiveNodeActionPhase.WARMUP
        }
        self._switch_timer_name: str | None = None
        self._last_active_instrument_changed_event: ActiveInstrumentChangedEvent | None = None
        self._on_active_instrument_changed = on_active_instrument_changed
        self._switch = ActiveInstrumentSwitchCoordinator(
            active_instrument_id=action_plan.active_instrument_id,
            enabled_instrument_ids=enabled_instrument_ids,
            data_client_name=data_client_name,
            target=target,
            now=lambda: self.clock.utc_now(),
            runtime_ready=lambda: self._warmup.state == WarmupState.LIVE,
            on_changed=self._handle_active_instrument_changed,
        )
        self._external_market_data_sink = on_market_data_event
        self._native_market_data_sink = on_native_market_data_event
        self._historical_bar_sink = on_historical_bar
        self._startup_recovery = startup_recovery
        self._health = MarketDataHealthMonitor(
            instrument_ids=enabled_instrument_ids,
            active_instrument_id=lambda: self._switch.snapshot.active_instrument_id,
            now=lambda: self.clock.utc_now(),
            is_session_open=is_session_open or (lambda _instrument_id, _now: True),
            on_change=on_market_data_health,
        )
        self._health_timer_started = False
        self._router = LiveMarketDataRouter(
            instrument_ids=enabled_instrument_ids,
            active_instrument_id=lambda: self._switch.snapshot.active_instrument_id,
            on_event=self._handle_market_data_event,
        )

    @property
    def warmup_state(self) -> WarmupState:
        return self._warmup.state

    @property
    def active_switch(self) -> ActiveSwitchSnapshot:
        return self._switch.snapshot

    @property
    def last_active_instrument_changed_event(self) -> ActiveInstrumentChangedEvent | None:
        return self._last_active_instrument_changed_event

    @property
    def market_data_snapshots(self) -> tuple[InstrumentMarketDataSnapshot, ...]:
        return self._router.snapshots()

    @property
    def market_data_health(self) -> MarketDataHealthSnapshot:
        return self._health.current

    @property
    def startup_recovery_snapshot(self) -> Any | None:
        return None if self._startup_recovery is None else self._startup_recovery.snapshot

    def on_start(self) -> None:
        self._warmup.start()
        self.clock.set_timer(
            name="market-data-health",
            interval=timedelta(seconds=1),
            callback=lambda _event: self._health.evaluate(),
        )
        self._health_timer_started = True

    def on_stop(self) -> None:
        if self._health_timer_started:
            self.clock.cancel_timer("market-data-health")
            self._health_timer_started = False
        self._cancel_switch_timer()

    def on_historical_data(self, data: Any) -> None:
        bar_type = getattr(data, "bar_type", None)
        if bar_type is not None:
            self._warmup.record_historical_data(bar_type=str(bar_type), data=data)
            if self._startup_recovery is not None and data.bar_type.spec.timedelta == timedelta(
                minutes=1
            ):
                normalized = normalize_one_minute_bar(
                    data,
                    source="ib",
                    received_ts=self.clock.utc_now(),
                )
                accepted = self._historical_bar_sink(normalized)
                self._startup_recovery.observe_bar(normalized, accepted=accepted)

    def on_trade_tick(self, tick: Any) -> None:
        if self._router.handle_trade_tick(tick) is None:
            return
        if self._native_market_data_sink is not None:
            self._native_market_data_sink(tick)
        event = self._switch.observe_trade_tick(str(tick.instrument_id))
        if event is not None:
            self._cancel_switch_timer()

    def on_quote_tick(self, tick: Any) -> None:
        if self._router.handle_quote_tick(tick) is None:
            return
        if self._native_market_data_sink is not None:
            self._native_market_data_sink(tick)
        event = self._switch.observe_quote_tick(str(tick.instrument_id))
        if event is not None:
            self._cancel_switch_timer()

    def on_bar(self, bar: Any) -> None:
        self._router.handle_bar(bar)

    def request_active_instrument_switch(
        self,
        request: ActiveInstrumentSwitchRequest,
    ) -> ActiveSwitchSnapshot:
        snapshot = self._switch.request_switch(request)
        if snapshot.deadline is None:
            raise RuntimeError("active switch deadline is missing")
        timer_name = f"active-switch:{request.request_id}"
        self._switch_timer_name = timer_name
        self.clock.set_time_alert(
            name=timer_name,
            alert_time=snapshot.deadline,
            callback=lambda _event: self._handle_switch_timeout(),
        )
        return snapshot

    def _handle_switch_timeout(self) -> None:
        self._switch.check_timeout()
        self._switch_timer_name = None

    def _handle_active_instrument_changed(self, event: ActiveInstrumentChangedEvent) -> None:
        self._router.activate_instrument(event.active_instrument_id)
        self._health.evaluate()
        self._last_active_instrument_changed_event = event
        if self._on_active_instrument_changed is not None:
            self._on_active_instrument_changed(event)

    def _handle_market_data_event(self, event: Any) -> None:
        self._health.observe(event)
        if self._external_market_data_sink is not None:
            self._external_market_data_sink(event)

    def _cancel_switch_timer(self) -> None:
        if self._switch_timer_name is not None:
            self.clock.cancel_timer(self._switch_timer_name)
            self._switch_timer_name = None


def conservative_warmup_start(lookback_sessions: int, end: datetime) -> datetime:
    # Over-fetch calendar days so weekends and common holiday closures do not reduce coverage.
    calendar_days = max(lookback_sessions * 2, lookback_sessions + 4)
    return end - timedelta(days=calendar_days)
