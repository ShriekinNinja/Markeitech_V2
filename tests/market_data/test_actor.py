from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from markeitech.analytics import (
    AnalyticsInputFidelity,
    AnalyticsTimeframe,
    MarketContextSnapshot,
    TrendState,
    VwapPosition,
)
from markeitech.domain import OneMinuteBar
from markeitech.market_data import NautilusActorActionTarget, conservative_warmup_start
from markeitech.market_data.actor import (
    ActorStartupRecoveryHook,
    format_market_context,
    should_update_market_context,
)


class FakeActorApi:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def request_bars(self, *args: Any, **kwargs: Any) -> str:
        self.calls.append(("request_bars", args, kwargs))
        return "request-id"

    def subscribe_trade_ticks(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("subscribe_trade_ticks", args, kwargs))

    def subscribe_quote_ticks(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("subscribe_quote_ticks", args, kwargs))

    def subscribe_bars(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("subscribe_bars", args, kwargs))

    def unsubscribe_trade_ticks(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("unsubscribe_trade_ticks", args, kwargs))

    def unsubscribe_quote_ticks(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("unsubscribe_quote_ticks", args, kwargs))


def test_actor_target_converts_action_values_to_nautilus_objects() -> None:
    actor = FakeActorApi()
    now = datetime(2026, 7, 10, 12, tzinfo=UTC)
    target = NautilusActorActionTarget(
        actor,
        now=lambda: now,
        resolve_warmup_start=lambda sessions, end: end - timedelta(days=sessions),
    )

    request_id = target.request_historical_bars(
        instrument_id="NQU6.CME",
        bar_type="NQU6.CME-1-MINUTE-LAST-EXTERNAL",
        lookback_sessions=5,
        data_client_name="IB",
    )
    target.subscribe_trade_ticks(instrument_id="NQU6.CME", data_client_name="IB")
    target.subscribe_quote_ticks(instrument_id="NQU6.CME", data_client_name="IB")
    target.subscribe_bars(
        instrument_id="ESU6.CME",
        bar_type="ESU6.CME-1-MINUTE-LAST-EXTERNAL",
        data_client_name="IB",
    )
    target.unsubscribe_trade_ticks(instrument_id="NQU6.CME", data_client_name="IB")
    target.unsubscribe_quote_ticks(instrument_id="NQU6.CME", data_client_name="IB")

    assert request_id == "request-id"
    assert str(actor.calls[0][1][0]) == "NQU6.CME-1-MINUTE-LAST-EXTERNAL"
    assert actor.calls[0][2]["start"] == now - timedelta(days=5)
    assert actor.calls[0][2]["end"] == now
    assert str(actor.calls[1][1][0]) == "NQU6.CME"
    assert str(actor.calls[3][1][0]) == "ESU6.CME-1-MINUTE-LAST-EXTERNAL"
    assert str(actor.calls[4][1][0]) == "NQU6.CME"
    assert str(actor.calls[5][1][0]) == "NQU6.CME"
    assert all(str(call[2]["client_id"]) == "IB" for call in actor.calls)


def test_default_warmup_window_overfetches_calendar_days() -> None:
    end = datetime(2026, 7, 10, 12, tzinfo=UTC)

    assert conservative_warmup_start(5, end) == end - timedelta(days=10)


def test_context_uses_tick_bars_for_active_and_provider_bars_for_background() -> None:
    open_ts = datetime(2026, 7, 13, 12, tzinfo=UTC)
    provider_bar = OneMinuteBar(
        instrument_id="NQU6.CME",
        event_ts=open_ts + timedelta(minutes=1),
        ts_init=open_ts + timedelta(minutes=1),
        open_ts=open_ts,
        close_ts=open_ts + timedelta(minutes=1),
        open=Decimal("20000"),
        high=Decimal("20001"),
        low=Decimal("19999"),
        close=Decimal("20000.25"),
        volume=Decimal("1"),
        buy_volume=Decimal("0"),
        sell_volume=Decimal("0"),
        unknown_volume=Decimal("1"),
        source="ib",
    )
    tick_bar = provider_bar.model_copy(update={"source": "classified_ticks"})
    background_bar = provider_bar.model_copy(update={"instrument_id": "ESU6.CME"})

    assert not should_update_market_context(
        provider_bar,
        active_instrument_id="NQU6.CME",
    )
    assert should_update_market_context(
        tick_bar,
        active_instrument_id="NQU6.CME",
    )
    assert should_update_market_context(
        background_bar,
        active_instrument_id="NQU6.CME",
    )


def test_market_context_log_is_compact_and_human_scannable() -> None:
    snapshot = MarketContextSnapshot(
        instrument_id="NQU6.CME",
        timeframe=AnalyticsTimeframe.FIVE_MINUTES,
        as_of=datetime(2026, 7, 13, 12, 5, tzinfo=UTC),
        source="classified_ticks",
        input_fidelity=AnalyticsInputFidelity.INFERRED,
        bar_count=220,
        close=Decimal("25010.25"),
        ema_20=Decimal("25000.5"),
        ema_50=Decimal("24980.25"),
        ema_200=Decimal("24800"),
        atr_14=Decimal("18.75"),
        session_open=Decimal("24900"),
        session_high=Decimal("25050"),
        session_low=Decimal("24850"),
        session_vwap=Decimal("24975.5"),
        session_range_position=Decimal("0.80125"),
        vwap_position=VwapPosition.ABOVE,
        trend=TrendState.BULLISH,
        trend_reason_codes=("close_above_ema_stack", "ema20_rising"),
    )

    message = format_market_context(snapshot)

    assert message.startswith("MARKET_CONTEXT | NQU6.CME 5m | trend=BULLISH")
    assert "EMA[20=25000.5 50=24980.25 200=24800]" in message
    assert "VWAP[24975.5 above] | ATR14=18.75" in message
    assert "position=80.1%" in message
    assert "input=inferred:classified_ticks" in message
    assert "\n" not in message


def test_actor_target_uses_exact_recovery_range() -> None:
    actor = FakeActorApi()
    now = datetime(2026, 7, 13, 12, tzinfo=UTC)
    start = now - timedelta(minutes=3)
    target = NautilusActorActionTarget(actor, now=lambda: now)

    target.request_historical_bars(
        instrument_id="NQU6.CME",
        bar_type="NQU6.CME-1-MINUTE-LAST-EXTERNAL",
        lookback_sessions=None,
        request_start_ts=start,
        request_end_ts=now,
        data_client_name="IB",
    )

    assert actor.calls[0][2]["start"] == start
    assert actor.calls[0][2]["end"] == now


def test_actor_recovery_hook_maps_provider_requests_to_exact_actions() -> None:
    now = datetime(2026, 7, 13, 12, tzinfo=UTC)

    class Request:
        instrument_id = "SPY.ARCA"
        start_ts = now - timedelta(minutes=2)
        end_ts = now
        request_id = "request-id"

    class Service:
        snapshot = None

        def observe_bar(self, bar: Any, *, accepted: bool) -> None:
            del bar, accepted

        def prepare(self, requested_now: datetime) -> tuple[Request, ...]:
            assert requested_now == now
            return (Request(),)

        def finish(self, requested_now: datetime) -> None:
            assert requested_now == now

    hook = ActorStartupRecoveryHook(Service(), data_client_name="IB", now=lambda: now)

    action = hook.prepare()[0]
    assert action.instrument_id == "SPY.ARCA"
    assert action.request_start_ts == Request.start_ts
    assert action.request_end_ts == now
    assert action.recovery_request_id == "request-id"
    hook.finish()
