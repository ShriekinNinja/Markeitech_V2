from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, Protocol

from nautilus_trader.common.actor import Actor
from nautilus_trader.model.data import BarType
from nautilus_trader.model.identifiers import ClientId, InstrumentId

from markeitech.market_data.actions import LiveNodeActionPlan
from markeitech.market_data.coordinator import (
    WarmupCoordinator,
    WarmupReadyHandler,
    WarmupState,
)


class NautilusActorApi(Protocol):
    def request_bars(self, bar_type: Any, start: datetime, **kwargs: Any) -> Any: ...

    def subscribe_trade_ticks(self, instrument_id: Any, **kwargs: Any) -> Any: ...

    def subscribe_quote_ticks(self, instrument_id: Any, **kwargs: Any) -> Any: ...

    def subscribe_bars(self, bar_type: Any, **kwargs: Any) -> Any: ...


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


class MarkeitechMarketDataActor(Actor):
    def __init__(
        self,
        action_plan: LiveNodeActionPlan,
        *,
        on_warmup_ready: WarmupReadyHandler,
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

    @property
    def warmup_state(self) -> WarmupState:
        return self._warmup.state

    def on_start(self) -> None:
        self._warmup.start()

    def on_historical_data(self, data: Any) -> None:
        bar_type = getattr(data, "bar_type", None)
        if bar_type is not None:
            self._warmup.record_historical_data(bar_type=str(bar_type), data=data)


def conservative_warmup_start(lookback_sessions: int, end: datetime) -> datetime:
    # Over-fetch calendar days so weekends and common holiday closures do not reduce coverage.
    calendar_days = max(lookback_sessions * 2, lookback_sessions + 4)
    return end - timedelta(days=calendar_days)
