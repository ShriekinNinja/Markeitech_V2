from __future__ import annotations

from pathlib import Path
from typing import Any

from markeitech.market_data import LIVE_NODE_START_CONFIRMATION, run_smoke_with_factory


class FakeNode:
    def __init__(self, *, config: Any) -> None:
        self.config = config
        self.started = False
        self.built = False
        self.trader = self
        self.actors: list[Any] = []

    def add_actor(self, actor: Any) -> None:
        self.actors.append(actor)

    def add_data_client_factory(self, name: str, factory: type[Any]) -> None:
        del name, factory

    def build(self) -> None:
        self.built = True

    def run(self) -> str:
        self.started = True
        return "fake-started"


def write_config(
    path: Path,
    *,
    run_live_node: bool,
    manual_live_node_start: bool,
) -> None:
    path.write_text(f"""
[runtime]
active_instrument_id = "NQU6.CME"
trader_id = "MARK-001"
data_client_name = "IB"
data_only = true
build_nautilus_node = true
manual_live_node_start = {str(manual_live_node_start).lower()}
run_live_node = {str(run_live_node).lower()}

[ib]
host = "127.0.0.1"
port = 7497
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
timeframes = ["1m", "5m", "15m", "30m"]
""".strip())


def test_smoke_refuses_when_config_does_not_enable_manual_start(tmp_path: Path) -> None:
    config_path = tmp_path / "market-data.toml"
    write_config(config_path, run_live_node=False, manual_live_node_start=False)

    result = run_smoke_with_factory(
        config_path,
        confirmation=LIVE_NODE_START_CONFIRMATION,
        node_factory=FakeNode,
    )

    assert result["status"] == "refused"
    assert result["reason"] == "config_does_not_enable_manual_livenode_start"
    assert result["plan"]["bootstrap"]["will_start_node"] is False


def test_smoke_refuses_without_confirmation(tmp_path: Path) -> None:
    config_path = tmp_path / "market-data.toml"
    write_config(config_path, run_live_node=True, manual_live_node_start=True)

    result = run_smoke_with_factory(
        config_path,
        confirmation="wrong",
        node_factory=FakeNode,
    )

    assert result["status"] == "refused"
    assert result["reason"] == "missing_or_invalid_confirmation"
    assert result["required_confirmation"] == LIVE_NODE_START_CONFIRMATION
    assert result["plan"]["bootstrap"]["will_start_node"] is True


def test_smoke_starts_fake_node_only_with_confirmation(tmp_path: Path) -> None:
    config_path = tmp_path / "market-data.toml"
    write_config(config_path, run_live_node=True, manual_live_node_start=True)

    result = run_smoke_with_factory(
        config_path,
        confirmation=LIVE_NODE_START_CONFIRMATION,
        node_factory=FakeNode,
    )

    assert result["status"] == "started"
    assert result["result"] == "fake-started"
    assert result["plan"]["execution_clients"] == []
