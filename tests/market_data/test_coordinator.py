from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from markeitech.market_data import (
    LiveNodeAction,
    LiveNodeActionKind,
    LiveNodeActionPhase,
    LiveNodeActionPlan,
    WarmupCoordinator,
    WarmupState,
    require_historical_coverage,
)


class DeferredTarget:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.callbacks: dict[str, Callable[[Any], None]] = {}

    def request_historical_bars(
        self,
        *,
        instrument_id: str,
        bar_type: str,
        lookback_sessions: int,
        data_client_name: str,
        callback: Callable[[Any], None] | None = None,
    ) -> str:
        del instrument_id, lookback_sessions, data_client_name
        self.calls.append(f"request:{bar_type}")
        assert callback is not None
        self.callbacks[bar_type] = callback
        return f"request-{bar_type}"

    def subscribe_trade_ticks(self, *, instrument_id: str, data_client_name: str) -> None:
        del data_client_name
        self.calls.append(f"trades:{instrument_id}")

    def subscribe_quote_ticks(self, *, instrument_id: str, data_client_name: str) -> None:
        del data_client_name
        self.calls.append(f"quotes:{instrument_id}")

    def subscribe_bars(
        self,
        *,
        instrument_id: str,
        bar_type: str,
        data_client_name: str,
    ) -> None:
        del data_client_name
        self.calls.append(f"bars:{instrument_id}:{bar_type}")


def action_plan() -> LiveNodeActionPlan:
    warmup_bar_types = ("NQU6.CME-1-MINUTE-LAST-EXTERNAL", "ESU6.CME-1-DAY-LAST-EXTERNAL")
    return LiveNodeActionPlan(
        active_instrument_id="NQU6.CME",
        actions=(
            *(
                LiveNodeAction(
                    instrument_id=bar_type.split("-")[0],
                    kind=LiveNodeActionKind.REQUEST_HISTORICAL_BARS,
                    phase=LiveNodeActionPhase.WARMUP,
                    bar_type=bar_type,
                    lookback_sessions=5,
                )
                for bar_type in warmup_bar_types
            ),
            LiveNodeAction(
                instrument_id="NQU6.CME",
                kind=LiveNodeActionKind.SUBSCRIBE_TRADE_TICKS,
                phase=LiveNodeActionPhase.LIVE_SUBSCRIPTION,
            ),
            LiveNodeAction(
                instrument_id="ESU6.CME",
                kind=LiveNodeActionKind.SUBSCRIBE_BARS,
                phase=LiveNodeActionPhase.LIVE_SUBSCRIPTION,
                bar_type="ESU6.CME-1-MINUTE-LAST-EXTERNAL",
            ),
        ),
    )


def test_coordinator_waits_for_all_warmups_and_analysis_before_subscribing() -> None:
    target = DeferredTarget()
    events: list[str] = []
    coordinator = WarmupCoordinator(
        action_plan(),
        target,
        on_warmup_ready=lambda snapshot: events.append(f"analyze:{len(snapshot.data_by_bar_type)}"),
    )

    coordinator.start()
    assert coordinator.state == WarmupState.REQUESTING
    assert not any(call.startswith(("trades:", "bars:")) for call in target.calls)

    for bar_type, callback in target.callbacks.items():
        coordinator.record_historical_data(bar_type=bar_type, data=f"bar:{bar_type}")
        callback(f"request-{bar_type}")

    assert events == ["analyze:2"]
    assert coordinator.state == WarmupState.LIVE
    assert target.calls[-2:] == [
        "trades:NQU6.CME",
        "bars:ESU6.CME:ESU6.CME-1-MINUTE-LAST-EXTERNAL",
    ]


def test_analysis_failure_blocks_live_subscriptions() -> None:
    target = DeferredTarget()
    coordinator = WarmupCoordinator(
        action_plan(),
        target,
        on_warmup_ready=require_historical_coverage,
    )
    coordinator.start()

    callbacks = list(target.callbacks.items())
    with pytest.raises(RuntimeError, match="returned no data"):
        for _bar_type, callback in callbacks:
            callback("request")

    assert coordinator.state == WarmupState.FAILED
    assert not any(call.startswith(("trades:", "bars:")) for call in target.calls)


def test_coordinator_rejects_second_start() -> None:
    coordinator = WarmupCoordinator(
        action_plan(),
        DeferredTarget(),
        on_warmup_ready=lambda snapshot: None,
    )
    coordinator.start()

    with pytest.raises(RuntimeError, match="cannot start"):
        coordinator.start()
