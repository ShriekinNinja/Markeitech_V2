from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from markeitech.domain import SourceHealth, SourceStatus
from markeitech.market_data import (
    LIVE_NODE_START_CONFIRMATION,
    AcceptanceStatus,
    InstrumentMarketDataSnapshot,
    MarketDataHealthSnapshot,
    WarmupState,
)
from markeitech.market_data.acceptance import run_paper_ib_acceptance_with_factories


class FakeNode:
    def __init__(self, *, config: Any) -> None:
        self.config = config
        self.trader = self
        self.actors: list[Any] = []
        self.built = False
        self.stopped = asyncio.Event()

    def add_actor(self, actor: Any) -> None:
        self.actors.append(actor)

    def add_data_client_factory(self, name: str, factory: type[Any]) -> None:
        del name, factory

    def build(self) -> None:
        self.built = True

    async def run_async(self) -> None:
        await self.stopped.wait()

    async def stop_async(self) -> None:
        self.stopped.set()


class FakeAcceptanceActor:
    def __init__(self, action_plan: Any, **kwargs: Any) -> None:
        del kwargs
        instrument_ids = sorted({action.instrument_id for action in action_plan.actions})
        self.warmup_state = WarmupState.LIVE
        self.market_data_snapshots = tuple(
            InstrumentMarketDataSnapshot(
                instrument_id=instrument_id,
                is_active=instrument_id == action_plan.active_instrument_id,
                trade_tick_count=3 if instrument_id == action_plan.active_instrument_id else 0,
                quote_tick_count=4 if instrument_id == action_plan.active_instrument_id else 0,
                bar_count=1,
                dropped_event_count=0,
            )
            for instrument_id in instrument_ids
        )
        self.market_data_health = MarketDataHealthSnapshot(
            source=SourceHealth(
                source="ib",
                status=SourceStatus.HEALTHY,
                updated_ts=datetime.now(UTC),
            ),
            instruments=(),
        )


def write_config(path: Path, *, enabled: bool) -> None:
    path.write_text(f"""
[runtime]
active_instrument_id = "NQU6.CME"
trader_id = "MARK-ACCEPTANCE"
data_client_name = "IB"
data_only = true
build_nautilus_node = true
manual_live_node_start = {str(enabled).lower()}
run_live_node = {str(enabled).lower()}

[ib]
host = "127.0.0.1"
port = 4002
client_id = 1
read_only = true

[[instruments]]
role = "active"
data_mode = "tick_by_tick"
analysis_profile = "active_tick"
enabled = true

[instruments.contract]
root_symbol = "NQ"
exchange = "CME"
instrument_id = "NQU6.CME"
security_type = "FUT"
ib_symbol = "NQ"
ib_exchange = "CME"
ib_security_type = "FUT"
expiry = 2026-09-18
ib_last_trade_date_or_contract_month = "20260918"
calendar_id = "CME_Equity"
session_profile = "full"

[instruments.warmup]
lookback_sessions = 5
timeframes = ["1m"]
""".strip())


@pytest.mark.asyncio
async def test_acceptance_runs_for_duration_stops_and_reports_pass(tmp_path: Path) -> None:
    config_path = tmp_path / "market-data.toml"
    write_config(config_path, enabled=True)

    report = await run_paper_ib_acceptance_with_factories(
        config_path,
        duration_seconds=1,
        confirmation=LIVE_NODE_START_CONFIRMATION,
        node_factory=FakeNode,
        actor_factory=FakeAcceptanceActor,
    )

    assert report.status == AcceptanceStatus.PASSED
    assert report.source_status == SourceStatus.HEALTHY
    assert report.instruments[0].trade_ticks == 3
    assert report.instruments[0].dropped_events == 0
    assert all(check.status.value == "pass" for check in report.checks)


@pytest.mark.asyncio
async def test_acceptance_refuses_without_manual_config_flags(tmp_path: Path) -> None:
    config_path = tmp_path / "market-data.toml"
    write_config(config_path, enabled=False)

    report = await run_paper_ib_acceptance_with_factories(
        config_path,
        duration_seconds=1,
        confirmation=LIVE_NODE_START_CONFIRMATION,
        node_factory=FakeNode,
        actor_factory=FakeAcceptanceActor,
    )

    assert report.status == AcceptanceStatus.REFUSED
    assert "start is disabled" in report.error


@pytest.mark.asyncio
async def test_acceptance_refuses_invalid_confirmation(tmp_path: Path) -> None:
    config_path = tmp_path / "market-data.toml"
    write_config(config_path, enabled=True)

    report = await run_paper_ib_acceptance_with_factories(
        config_path,
        duration_seconds=1,
        confirmation="wrong",
        node_factory=FakeNode,
        actor_factory=FakeAcceptanceActor,
    )

    assert report.status == AcceptanceStatus.REFUSED
    assert "confirmation token" in report.error
