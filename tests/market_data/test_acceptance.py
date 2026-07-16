from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from markeitech.analytics import (
    AnalyticsDepthStatus,
    AnalyticsFreshnessStatus,
    AnalyticsInputFidelity,
    AnalyticsReadinessSnapshot,
    AnalyticsReadinessStatus,
    AnalyticsTimeframe,
    InstrumentAnalyticsReadiness,
    MarketContextSnapshot,
    TimeframeAnalyticsReadiness,
    TrendState,
    VwapPosition,
)
from markeitech.domain import SourceHealth, SourceStatus
from markeitech.market_data import (
    LIVE_NODE_START_CONFIRMATION,
    AcceptanceStatus,
    InstrumentMarketDataSnapshot,
    MarketDataHealthSnapshot,
    WarmupState,
)
from markeitech.market_data.acceptance import run_paper_ib_acceptance_with_factories
from markeitech.persistence import (
    InstrumentStartupRecoverySnapshot,
    RecoveryStatus,
    StartupRecoverySnapshot,
    StartupRecoveryStatus,
)


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

    def get_event_loop(self) -> asyncio.AbstractEventLoop:
        return asyncio.get_running_loop()

    async def run_async(self) -> None:
        await self.stopped.wait()

    async def stop_async(self) -> None:
        self.stopped.set()


class FakeAcceptanceActor:
    def __init__(self, action_plan: Any, **kwargs: Any) -> None:
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
        self.market_context_snapshots = tuple(
            MarketContextSnapshot(
                instrument_id=instrument_id,
                timeframe=AnalyticsTimeframe.ONE_MINUTE,
                as_of=datetime(2026, 7, 13, 12, 1, tzinfo=UTC),
                source="ib",
                input_fidelity=AnalyticsInputFidelity.REPORTED,
                bar_count=60,
                close=Decimal("20000"),
                ema_20=Decimal("19990"),
                ema_50=Decimal("19980"),
                session_open=Decimal("19900"),
                session_high=Decimal("20010"),
                session_low=Decimal("19890"),
                session_vwap=Decimal("19950"),
                session_range_position=Decimal("0.9166666667"),
                vwap_position=VwapPosition.ABOVE,
                trend=TrendState.BULLISH,
                trend_reason_codes=("close_above_ema_stack", "ema20_rising"),
            )
            for instrument_id in instrument_ids
        )
        evaluated_ts = datetime(2026, 7, 13, 12, 1, tzinfo=UTC)
        self.analytics_readiness_snapshot = AnalyticsReadinessSnapshot(
            status=AnalyticsReadinessStatus.READY,
            evaluated_ts=evaluated_ts,
            instruments=tuple(
                InstrumentAnalyticsReadiness(
                    instrument_id=instrument_id,
                    status=AnalyticsReadinessStatus.READY,
                    timeframes=(
                        TimeframeAnalyticsReadiness(
                            instrument_id=instrument_id,
                            timeframe=AnalyticsTimeframe.ONE_MINUTE,
                            evaluated_ts=evaluated_ts,
                            expected_latest_close=evaluated_ts,
                            observed_latest_close=evaluated_ts,
                            lookback_sessions=5,
                            bar_count=200,
                            freshness=AnalyticsFreshnessStatus.CURRENT,
                            lag_intervals=0,
                            depth=AnalyticsDepthStatus.FULL,
                            reason_codes=(
                                "latest_completed_interval_present",
                                "ema200_depth_available",
                            ),
                        ),
                    ),
                    reason_codes=("all_timeframes_current_and_full_depth",),
                )
                for instrument_id in instrument_ids
            ),
            reason_codes=("instrument_status_ready",),
        )
        self.market_data_health = MarketDataHealthSnapshot(
            source=SourceHealth(
                source="ib",
                status=SourceStatus.HEALTHY,
                updated_ts=datetime.now(UTC),
            ),
            instruments=(),
        )
        self.startup_recovery_snapshot = (
            StartupRecoverySnapshot(
                status=StartupRecoveryStatus.COMPLETE,
                instruments=tuple(
                    InstrumentStartupRecoverySnapshot(
                        instrument_id=instrument_id,
                        status=RecoveryStatus.COMPLETE,
                        requested_start_ts=datetime(2026, 7, 13, 10, tzinfo=UTC),
                        requested_end_ts=datetime(2026, 7, 13, 12, tzinfo=UTC),
                        missing_before=2,
                        missing_after=0,
                        request_count=1,
                    )
                    for instrument_id in instrument_ids
                ),
                total_request_count=len(instrument_ids),
            )
            if "startup_recovery" in kwargs
            else None
        )


def write_config(path: Path, *, enabled: bool, persistence: bool = False) -> None:
    persistence_block = (
        f"""
[persistence]
catalog_path = "{path.parent / 'catalog'}"
metadata_path = "{path.parent / 'metadata.sqlite3'}"
journal_path = "{path.parent / 'journal'}"
"""
        if persistence
        else ""
    )
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

{persistence_block}

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
    assert report.market_contexts[0].trend == TrendState.BULLISH
    assert report.analytics_readiness is not None
    assert report.analytics_readiness.status == AnalyticsReadinessStatus.READY
    assert any(check.name == "NQU6.CME:market_context" for check in report.checks)
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


@pytest.mark.asyncio
async def test_acceptance_reports_terminal_recovery_for_every_instrument(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "market-data.toml"
    write_config(config_path, enabled=True, persistence=True)

    report = await run_paper_ib_acceptance_with_factories(
        config_path,
        duration_seconds=1,
        confirmation=LIVE_NODE_START_CONFIRMATION,
        node_factory=FakeNode,
        actor_factory=FakeAcceptanceActor,
    )

    assert report.status == AcceptanceStatus.PASSED
    assert report.recovery_status == StartupRecoveryStatus.COMPLETE
    recovered = [
        (item.instrument_id, item.missing_before, item.missing_after) for item in report.recoveries
    ]
    assert recovered == [("NQU6.CME", 2, 0)]
    assert any(check.name == "startup_recovery_terminal" for check in report.checks)
