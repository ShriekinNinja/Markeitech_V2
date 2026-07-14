from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
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

    for bar_type in (
        "NQU6.CME-1-MINUTE-LAST-EXTERNAL",
        "ESU6.CME-1-DAY-LAST-EXTERNAL",
    ):
        coordinator.record_historical_data(bar_type=bar_type, data=f"bar:{bar_type}")
        callback = target.callbacks[bar_type]
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

    bar_type = "NQU6.CME-1-MINUTE-LAST-EXTERNAL"
    with pytest.raises(RuntimeError, match="after 3 attempts"):
        for _ in range(3):
            target.callbacks[bar_type]("request")

    assert coordinator.state == WarmupState.FAILED
    assert not any(call.startswith(("trades:", "bars:")) for call in target.calls)


def test_empty_warmup_retries_same_request_before_advancing() -> None:
    target = DeferredTarget()
    retries: list[tuple[str, int, int]] = []
    coordinator = WarmupCoordinator(
        action_plan(),
        target,
        on_warmup_ready=require_historical_coverage,
        on_warmup_retry=lambda action, attempt, maximum: retries.append(
            (action.bar_type or "", attempt, maximum)
        ),
    )
    first = "NQU6.CME-1-MINUTE-LAST-EXTERNAL"

    coordinator.start()
    target.callbacks[first]("empty-request")

    assert target.calls == [f"request:{first}", f"request:{first}"]
    assert retries == [(first, 2, 3)]
    coordinator.record_historical_data(bar_type=first, data="bar")
    target.callbacks[first]("successful-retry")
    assert target.calls[-1] == "request:ESU6.CME-1-DAY-LAST-EXTERNAL"


def test_warmups_are_issued_sequentially() -> None:
    target = DeferredTarget()
    coordinator = WarmupCoordinator(
        action_plan(),
        target,
        on_warmup_ready=lambda _snapshot: None,
    )
    first = "NQU6.CME-1-MINUTE-LAST-EXTERNAL"
    second = "ESU6.CME-1-DAY-LAST-EXTERNAL"

    coordinator.start()
    assert target.calls == [f"request:{first}"]
    coordinator.record_historical_data(bar_type=first, data="bar")
    target.callbacks[first]("first")
    assert target.calls == [f"request:{first}", f"request:{second}"]


def test_coordinator_rejects_second_start() -> None:
    coordinator = WarmupCoordinator(
        action_plan(),
        DeferredTarget(),
        on_warmup_ready=lambda snapshot: None,
    )
    coordinator.start()

    with pytest.raises(RuntimeError, match="cannot start"):
        coordinator.start()


def test_recovery_requests_run_sequentially_before_analysis_and_subscriptions() -> None:
    class SequentialTarget(DeferredTarget):
        def __init__(self) -> None:
            super().__init__()
            self.recovery_callbacks: list[Callable[[str], None]] = []

        def request_historical_bars(
            self,
            *,
            instrument_id: str,
            bar_type: str,
            lookback_sessions: int | None,
            data_client_name: str,
            callback: Callable[[str], None] | None = None,
            request_start_ts: datetime | None = None,
            request_end_ts: datetime | None = None,
        ) -> str:
            if request_start_ts is None:
                assert lookback_sessions is not None
                return super().request_historical_bars(
                    instrument_id=instrument_id,
                    bar_type=bar_type,
                    lookback_sessions=lookback_sessions,
                    data_client_name=data_client_name,
                    callback=callback,
                )
            assert request_end_ts is not None
            assert callback is not None
            self.calls.append(f"recover:{instrument_id}:{request_start_ts.minute}")
            self.recovery_callbacks.append(callback)
            return f"recovery-{instrument_id}"

    class RecoveryHook:
        def __init__(self) -> None:
            self.finished = False

        def prepare(self) -> tuple[LiveNodeAction, ...]:
            return tuple(
                LiveNodeAction(
                    instrument_id=instrument_id,
                    kind=LiveNodeActionKind.REQUEST_HISTORICAL_BARS,
                    phase=LiveNodeActionPhase.WARMUP,
                    bar_type=f"{instrument_id}-1-MINUTE-LAST-EXTERNAL",
                    request_start_ts=datetime(2026, 7, 13, 12, minute, tzinfo=UTC),
                    request_end_ts=datetime(2026, 7, 13, 12, minute, tzinfo=UTC)
                    + timedelta(minutes=1),
                    recovery_request_id=f"recovery-{instrument_id}",
                )
                for instrument_id, minute in (("NQU6.CME", 1), ("ESU6.CME", 2))
            )

        def finish(self) -> None:
            self.finished = True

    target = SequentialTarget()
    recovery = RecoveryHook()
    analyzed: list[bool] = []
    coordinator = WarmupCoordinator(
        action_plan(),
        target,
        on_warmup_ready=lambda _snapshot: analyzed.append(recovery.finished),
        startup_recovery=recovery,
    )
    coordinator.start()
    for bar_type in (
        "NQU6.CME-1-MINUTE-LAST-EXTERNAL",
        "ESU6.CME-1-DAY-LAST-EXTERNAL",
    ):
        coordinator.record_historical_data(bar_type=bar_type, data=f"bar:{bar_type}")
        callback = target.callbacks[bar_type]
        callback(f"request-{bar_type}")

    assert coordinator.state == WarmupState.RECOVERING
    assert target.calls[-1] == "recover:NQU6.CME:1"
    assert len(target.recovery_callbacks) == 1

    target.recovery_callbacks[0]("recovery-NQ")
    assert target.calls[-1] == "recover:ESU6.CME:2"
    assert len(target.recovery_callbacks) == 2
    assert analyzed == []

    target.recovery_callbacks[1]("recovery-ES")
    assert coordinator.state == WarmupState.LIVE
    assert analyzed == [True]
    assert target.calls[-2:] == [
        "trades:NQU6.CME",
        "bars:ESU6.CME:ESU6.CME-1-MINUTE-LAST-EXTERNAL",
    ]
