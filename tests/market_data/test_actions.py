from datetime import date
from typing import Any

import pytest
from markeitech.domain import (
    AnalysisProfile,
    FuturesContractConfig,
    InstrumentDataMode,
    InstrumentRegistryConfig,
    InstrumentRole,
    InstrumentRuntimeConfig,
    NQContractConfig,
)
from markeitech.market_data import (
    LiveNodeAction,
    LiveNodeActionKind,
    LiveNodeActionPhase,
    LiveNodeActionPlan,
    build_livenode_action_plan,
    build_market_data_plan,
    build_nautilus_request_plan,
    execute_livenode_action_plan,
)
from pydantic import ValidationError


class FakeActionTarget:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def request_historical_bars(
        self,
        *,
        instrument_id: str,
        bar_type: str,
        lookback_sessions: int,
        data_client_name: str,
    ) -> str:
        payload = {
            "instrument_id": instrument_id,
            "bar_type": bar_type,
            "lookback_sessions": lookback_sessions,
            "data_client_name": data_client_name,
        }
        self.calls.append(("request_historical_bars", payload))
        return "historical"

    def subscribe_trade_ticks(self, *, instrument_id: str, data_client_name: str) -> str:
        payload = {"instrument_id": instrument_id, "data_client_name": data_client_name}
        self.calls.append(("subscribe_trade_ticks", payload))
        return "trade_ticks"

    def subscribe_quote_ticks(self, *, instrument_id: str, data_client_name: str) -> str:
        payload = {"instrument_id": instrument_id, "data_client_name": data_client_name}
        self.calls.append(("subscribe_quote_ticks", payload))
        return "quote_ticks"

    def subscribe_bars(self, *, instrument_id: str, bar_type: str, data_client_name: str) -> str:
        payload = {
            "instrument_id": instrument_id,
            "bar_type": bar_type,
            "data_client_name": data_client_name,
        }
        self.calls.append(("subscribe_bars", payload))
        return "bars"


def nq_contract() -> NQContractConfig:
    return NQContractConfig(
        expiry=date(2026, 9, 18),
        instrument_id="NQU6.CME",
        ib_last_trade_date_or_contract_month="20260918",
    )


def es_contract() -> FuturesContractConfig:
    return FuturesContractConfig(
        root_symbol="ES",
        exchange="CME",
        expiry=date(2026, 9, 18),
        instrument_id="ESU6.CME",
        ib_symbol="ES",
        ib_exchange="CME",
        ib_last_trade_date_or_contract_month="20260918",
    )


def action_plan() -> LiveNodeActionPlan:
    registry = InstrumentRegistryConfig(
        active_instrument_id="NQU6.CME",
        instruments=(
            InstrumentRuntimeConfig(
                contract=nq_contract(),
                role=InstrumentRole.ACTIVE,
                data_mode=InstrumentDataMode.TICK_BY_TICK,
                analysis_profile=AnalysisProfile.ACTIVE_TICK,
            ),
            InstrumentRuntimeConfig(
                contract=es_contract(),
                role=InstrumentRole.BACKGROUND,
                data_mode=InstrumentDataMode.LIVE_1M_BARS,
                analysis_profile=AnalysisProfile.BACKGROUND_BAR,
            ),
        ),
    )
    plan = build_market_data_plan(registry)
    request_plan = build_nautilus_request_plan(plan, data_client_name="IB")
    return build_livenode_action_plan(request_plan)


def test_livenode_actions_are_warmup_first_then_live_subscriptions() -> None:
    plan = action_plan()

    phases = [action.phase for action in plan.actions]
    first_live_index = phases.index(LiveNodeActionPhase.LIVE_SUBSCRIPTION)

    assert all(phase == LiveNodeActionPhase.WARMUP for phase in phases[:first_live_index])
    assert all(
        phase == LiveNodeActionPhase.LIVE_SUBSCRIPTION for phase in phases[first_live_index:]
    )
    assert any(action.kind == LiveNodeActionKind.SUBSCRIBE_TRADE_TICKS for action in plan.actions)
    assert any(action.kind == LiveNodeActionKind.SUBSCRIBE_QUOTE_TICKS for action in plan.actions)
    assert ("ESU6.CME", LiveNodeActionKind.SUBSCRIBE_TRADE_TICKS) not in {
        (action.instrument_id, action.kind) for action in plan.actions
    }


def test_livenode_action_plan_rejects_duplicate_actions() -> None:
    plan = action_plan()

    with pytest.raises(ValidationError, match="duplicate actions"):
        LiveNodeActionPlan(
            active_instrument_id=plan.active_instrument_id,
            actions=(
                *plan.actions,
                plan.actions[0],
            ),
        )


def test_execute_livenode_action_plan_records_fake_calls() -> None:
    plan = action_plan()
    target = FakeActionTarget()

    results = execute_livenode_action_plan(plan, target)

    assert results.count("historical") == len(
        [action for action in plan.actions if action.phase == LiveNodeActionPhase.WARMUP]
    )
    assert (
        "subscribe_trade_ticks",
        {"instrument_id": "NQU6.CME", "data_client_name": "IB"},
    ) in target.calls
    assert (
        "subscribe_quote_ticks",
        {"instrument_id": "NQU6.CME", "data_client_name": "IB"},
    ) in target.calls
    assert (
        "subscribe_bars",
        {
            "instrument_id": "ESU6.CME",
            "bar_type": "ESU6.CME-1-MINUTE-LAST-EXTERNAL",
            "data_client_name": "IB",
        },
    ) in target.calls


def test_bar_actions_require_bar_type() -> None:
    with pytest.raises(ValidationError, match="bar actions require bar_type"):
        LiveNodeAction(
            instrument_id="NQU6.CME",
            kind=LiveNodeActionKind.SUBSCRIBE_BARS,
            phase=LiveNodeActionPhase.LIVE_SUBSCRIPTION,
        )
