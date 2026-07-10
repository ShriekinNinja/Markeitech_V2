from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from markeitech.domain import ActiveInstrumentChangedEvent
from markeitech.market_data import (
    ActiveInstrumentSwitchCoordinator,
    ActiveInstrumentSwitchRequest,
    ActiveSwitchStatus,
)
from pydantic import ValidationError


class SwitchTarget:
    def __init__(self, *, fail_on: str | None = None) -> None:
        self.calls: list[str] = []
        self.fail_on = fail_on

    def subscribe_trade_ticks(self, *, instrument_id: str, data_client_name: str) -> None:
        self._call("subscribe_trade", instrument_id, data_client_name)

    def subscribe_quote_ticks(self, *, instrument_id: str, data_client_name: str) -> None:
        self._call("subscribe_quote", instrument_id, data_client_name)

    def unsubscribe_trade_ticks(self, *, instrument_id: str, data_client_name: str) -> None:
        self._call("unsubscribe_trade", instrument_id, data_client_name)

    def unsubscribe_quote_ticks(self, *, instrument_id: str, data_client_name: str) -> None:
        self._call("unsubscribe_quote", instrument_id, data_client_name)

    def _call(self, operation: str, instrument_id: str, data_client_name: str) -> None:
        call = f"{operation}:{instrument_id}:{data_client_name}"
        self.calls.append(call)
        if self.fail_on == call:
            raise RuntimeError(f"forced failure: {call}")


NOW = datetime(2026, 7, 10, 12, tzinfo=UTC)


def request(target: str = "ESU6.CME") -> ActiveInstrumentSwitchRequest:
    return ActiveInstrumentSwitchRequest(
        request_id="switch-001",
        target_instrument_id=target,
        requested_ts=NOW,
        reason="operator_switch",
    )


def coordinator(
    target: SwitchTarget,
    *,
    ready: bool = True,
    events: list[ActiveInstrumentChangedEvent] | None = None,
) -> ActiveInstrumentSwitchCoordinator:
    changed = events if events is not None else []
    return ActiveInstrumentSwitchCoordinator(
        active_instrument_id="NQU6.CME",
        enabled_instrument_ids={"NQU6.CME", "ESU6.CME"},
        data_client_name="IB",
        target=target,
        now=lambda: NOW,
        runtime_ready=lambda: ready,
        on_changed=changed.append,
        readiness_timeout=timedelta(seconds=5),
    )


def test_switch_waits_for_trade_and_quote_then_promotes() -> None:
    target = SwitchTarget()
    events: list[ActiveInstrumentChangedEvent] = []
    switch = coordinator(target, events=events)

    snapshot = switch.request_switch(request())
    assert snapshot.status == ActiveSwitchStatus.AWAITING_CANDIDATE_TICKS
    assert target.calls == ["subscribe_trade:ESU6.CME:IB", "subscribe_quote:ESU6.CME:IB"]

    assert switch.observe_trade_tick("ESU6.CME") is None
    event = switch.observe_quote_tick("ESU6.CME")

    assert event is not None
    assert event.previous_instrument_id == "NQU6.CME"
    assert event.active_instrument_id == "ESU6.CME"
    assert event.reason == "operator_switch:switch-001"
    assert switch.snapshot.active_instrument_id == "ESU6.CME"
    assert switch.snapshot.status == ActiveSwitchStatus.STABLE
    assert events == [event]
    assert target.calls[-2:] == [
        "unsubscribe_trade:NQU6.CME:IB",
        "unsubscribe_quote:NQU6.CME:IB",
    ]


def test_unrelated_ticks_do_not_ready_candidate() -> None:
    switch = coordinator(SwitchTarget())
    switch.request_switch(request())

    switch.observe_trade_tick("NQU6.CME")
    switch.observe_quote_tick("NQU6.CME")

    assert switch.snapshot.trade_tick_ready is False
    assert switch.snapshot.quote_tick_ready is False


def test_switch_rejects_unknown_same_not_ready_and_concurrent_targets() -> None:
    switch = coordinator(SwitchTarget())
    with pytest.raises(ValueError, match="not enabled"):
        switch.request_switch(request("VIX.CBOE"))
    with pytest.raises(ValueError, match="already active"):
        switch.request_switch(request("NQU6.CME"))

    unready = coordinator(SwitchTarget(), ready=False)
    with pytest.raises(RuntimeError, match="not ready"):
        unready.request_switch(request())

    switch.request_switch(request())
    with pytest.raises(RuntimeError, match="already in progress"):
        switch.request_switch(request())


def test_timeout_unsubscribes_candidate_and_keeps_previous_active() -> None:
    target = SwitchTarget()
    switch = coordinator(target)
    switch.request_switch(request())

    timed_out = switch.check_timeout(NOW + timedelta(seconds=5))

    assert timed_out is True
    assert switch.snapshot.status == ActiveSwitchStatus.STABLE
    assert switch.snapshot.active_instrument_id == "NQU6.CME"
    assert switch.snapshot.last_failure == "candidate_tick_timeout"
    assert target.calls[-2:] == [
        "unsubscribe_trade:ESU6.CME:IB",
        "unsubscribe_quote:ESU6.CME:IB",
    ]


def test_candidate_subscription_failure_rolls_back_to_previous_active() -> None:
    target = SwitchTarget(fail_on="subscribe_quote:ESU6.CME:IB")
    switch = coordinator(target)

    with pytest.raises(RuntimeError, match="forced failure"):
        switch.request_switch(request())

    assert switch.snapshot.status == ActiveSwitchStatus.STABLE
    assert switch.snapshot.active_instrument_id == "NQU6.CME"
    assert switch.snapshot.last_failure == "candidate_subscription_failed"


def test_old_active_unsubscribe_failure_repairs_old_and_rolls_back_candidate() -> None:
    target = SwitchTarget(fail_on="unsubscribe_quote:NQU6.CME:IB")
    switch = coordinator(target)
    switch.request_switch(request())
    switch.observe_trade_tick("ESU6.CME")

    with pytest.raises(RuntimeError, match="forced failure"):
        switch.observe_quote_tick("ESU6.CME")

    assert switch.snapshot.status == ActiveSwitchStatus.STABLE
    assert switch.snapshot.active_instrument_id == "NQU6.CME"
    assert switch.snapshot.last_failure == "previous_active_unsubscribe_failed"
    assert "subscribe_trade:NQU6.CME:IB" in target.calls
    assert "subscribe_quote:NQU6.CME:IB" in target.calls
    assert "unsubscribe_trade:ESU6.CME:IB" in target.calls


def test_switch_request_requires_utc_timestamp() -> None:
    with pytest.raises(ValidationError, match="UTC"):
        ActiveInstrumentSwitchRequest(
            request_id="switch-001",
            target_instrument_id="ESU6.CME",
            requested_ts=datetime(2026, 7, 10, 12),
        )
