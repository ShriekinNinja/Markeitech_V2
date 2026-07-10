from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from markeitech.market_data import NautilusActorActionTarget, conservative_warmup_start


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

    assert request_id == "request-id"
    assert str(actor.calls[0][1][0]) == "NQU6.CME-1-MINUTE-LAST-EXTERNAL"
    assert actor.calls[0][2]["start"] == now - timedelta(days=5)
    assert actor.calls[0][2]["end"] == now
    assert str(actor.calls[1][1][0]) == "NQU6.CME"
    assert str(actor.calls[3][1][0]) == "ESU6.CME-1-MINUTE-LAST-EXTERNAL"
    assert all(str(call[2]["client_id"]) == "IB" for call in actor.calls)


def test_default_warmup_window_overfetches_calendar_days() -> None:
    end = datetime(2026, 7, 10, 12, tzinfo=UTC)

    assert conservative_warmup_start(5, end) == end - timedelta(days=10)
