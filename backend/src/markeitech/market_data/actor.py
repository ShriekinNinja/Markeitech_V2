from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, Protocol

from nautilus_trader.common.actor import Actor
from nautilus_trader.model.data import BarType
from nautilus_trader.model.identifiers import ClientId, InstrumentId

from markeitech.domain.events import ActiveInstrumentChangedEvent
from markeitech.market_data.actions import LiveNodeActionPhase, LiveNodeActionPlan
from markeitech.market_data.coordinator import (
    WarmupCoordinator,
    WarmupReadyHandler,
    WarmupState,
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
        lookback_sessions: int,
        data_client_name: str,
        callback: Callable[[Any], None] | None = None,
    ) -> Any:
        del instrument_id
        end = self._now()
        return self._actor.request_bars(
            BarType.from_str(bar_type),
            start=self._resolve_warmup_start(lookback_sessions, end),
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
        resolve_warmup_start: WarmupStartResolver | None = None,
    ) -> None:
        super().__init__()
        target = NautilusActorActionTarget(
            self,
            now=lambda: self.clock.utc_now(),
            resolve_warmup_start=resolve_warmup_start,
        )
        self._warmup = WarmupCoordinator(
            action_plan,
            target,
            on_warmup_ready=on_warmup_ready,
        )
        enabled_instrument_ids = {
            action.instrument_id
            for action in action_plan.actions
            if action.phase == LiveNodeActionPhase.WARMUP
        }
        data_client_names = {action.data_client_name for action in action_plan.actions}
        if len(data_client_names) != 1:
            raise ValueError("market-data actor requires exactly one data client")
        self._switch_timer_name: str | None = None
        self._last_active_instrument_changed_event: ActiveInstrumentChangedEvent | None = None
        self._on_active_instrument_changed = on_active_instrument_changed
        self._switch = ActiveInstrumentSwitchCoordinator(
            active_instrument_id=action_plan.active_instrument_id,
            enabled_instrument_ids=enabled_instrument_ids,
            data_client_name=next(iter(data_client_names)),
            target=target,
            now=lambda: self.clock.utc_now(),
            runtime_ready=lambda: self._warmup.state == WarmupState.LIVE,
            on_changed=self._handle_active_instrument_changed,
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

    def on_start(self) -> None:
        self._warmup.start()

    def on_historical_data(self, data: Any) -> None:
        bar_type = getattr(data, "bar_type", None)
        if bar_type is not None:
            self._warmup.record_historical_data(bar_type=str(bar_type), data=data)

    def on_trade_tick(self, tick: Any) -> None:
        event = self._switch.observe_trade_tick(str(tick.instrument_id))
        if event is not None:
            self._cancel_switch_timer()

    def on_quote_tick(self, tick: Any) -> None:
        event = self._switch.observe_quote_tick(str(tick.instrument_id))
        if event is not None:
            self._cancel_switch_timer()

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
        self._last_active_instrument_changed_event = event
        if self._on_active_instrument_changed is not None:
            self._on_active_instrument_changed(event)

    def _cancel_switch_timer(self) -> None:
        if self._switch_timer_name is not None:
            self.clock.cancel_timer(self._switch_timer_name)
            self._switch_timer_name = None


def conservative_warmup_start(lookback_sessions: int, end: datetime) -> datetime:
    # Over-fetch calendar days so weekends and common holiday closures do not reduce coverage.
    calendar_days = max(lookback_sessions * 2, lookback_sessions + 4)
    return end - timedelta(days=calendar_days)
