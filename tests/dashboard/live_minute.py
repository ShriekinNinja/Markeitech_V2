"""Explicit ES live diagnostic of production minute delivery, with isolated startup gates.

No database, Discord or execution clients are constructed. Only fixture startup/membership
and calendar synchronization are isolated; demand planning, acquisition, history execution,
minute projection, dashboard and HTTP/SSE are production code. Not collected by pytest.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, replace
from pathlib import Path
from time import monotonic
from types import SimpleNamespace
from uuid import uuid4

import httpx
from nautilus_trader.adapters.interactive_brokers import InteractiveBrokersDataClientFactory
from nautilus_trader.common import CacheConfig, Environment, LoggerConfig, LogLevel
from nautilus_trader.live import LiveNode
from nautilus_trader.model import TraderId

from markeitech.acquisition import HISTORICAL_DEPENDENCY_DEMAND_SIGNAL
from markeitech.dashboard.actor import DashboardActor, DashboardActorConfig
from markeitech.system.acquisition import DataAcquisitionActor, DataAcquisitionActorConfig
from markeitech.system.composition import StartupPrerequisites, build_actor_plan
from markeitech.system.config import load_system_config
from markeitech.system.historical_planner import (
    HistoricalEvidencePlannerActor,
    HistoricalEvidencePlannerActorConfig,
)
from markeitech.system.messages import WATCHLIST_MEMBERSHIP_SIGNAL, WatchlistMembershipEvent
from markeitech.system.node import build_ib_data_client_config
from tests.dashboard.live_backfill import _comparison


class _Acquisition(DataAcquisitionActor):
    def on_start(self) -> None:
        self.raw_history = []
        self.raw_live = []
        super().on_start()
        self._release_startup()  # Diagnostic waiver only; no claim of durable startup audit.

    def on_bar(self, bar) -> None:  # noqa: ANN001
        self.raw_live.append(bar)
        super().on_bar(bar)

    def on_historical_bars(self, bars) -> None:  # noqa: ANN001
        self.raw_history.extend(bars)
        super().on_historical_bars(bars)
        print(f"HISTORY_DELIVERED | source_bars={len(bars)}", flush=True)


class _Planner(HistoricalEvidencePlannerActor):
    def on_start(self) -> None:
        # Recent-completed windows need no session projection. Definitions still come
        # from the reviewed config via the production composition/compiler.
        self._active = True
        self.subscribe_signal(HISTORICAL_DEPENDENCY_DEMAND_SIGNAL)

    def on_stop(self) -> None:
        self._active = False
        self.unsubscribe_signal(HISTORICAL_DEPENDENCY_DEMAND_SIGNAL)


class _Dashboard(DashboardActor):
    def on_start(self) -> None:
        super().on_start()
        self.on_signal(
            SimpleNamespace(
                name=WATCHLIST_MEMBERSHIP_SIGNAL, value=self.probe_membership.to_signal_value()
            )
        )


async def _run(args: argparse.Namespace) -> dict:
    config = load_system_config(args.config)
    if args.client_id == config.ib.client_id or args.port == config.dashboard.port:
        raise ValueError("diagnostic client and dashboard port must differ from the running system")
    member = next(m for m in config.watchlist.members if m.instrument_id == args.instrument)
    member = replace(member, capabilities=("watchlist_last",))
    config = replace(
        config,
        ib=replace(config.ib, client_id=args.client_id),
        watchlist=replace(config.watchlist, members=(member,)),
        dashboard=replace(config.dashboard, port=args.port),
    )
    configs = {
        r.key: r.config.config
        for r in build_actor_plan(config, StartupPrerequisites(uuid4(), True))
    }
    acquisition = _Acquisition(DataAcquisitionActorConfig(**configs["data_acquisition"]))
    planner = _Planner(
        HistoricalEvidencePlannerActorConfig(**configs["historical_evidence_planner"])
    )
    dashboard = _Dashboard(DashboardActorConfig(**configs["dashboard"]))
    dashboard.probe_membership = WatchlistMembershipEvent(
        "live-minute-diagnostic", 1, "WATCHLIST", "reviewed ES diagnostic scope", (asdict(member),)
    )
    acquisition.bind_dashboard_consumer(
        dashboard,
        {(args.instrument, "bars")},
        config.dashboard.acquisition_retry_interval_ms,
        config.dashboard.candles_per_instrument,
    )
    node = (
        LiveNode.builder(
            "MINUTE-DASHBOARD-PROBE", TraderId.from_str("MINUTE-PROBE-001"), Environment.LIVE
        )
        .with_logging(LoggerConfig(stdout_level=LogLevel.ERROR))
        .with_cache_config(CacheConfig(bar_capacity=500, save_market_data=False))
        .with_delay_post_stop_secs(0)
        .add_data_client(
            None, InteractiveBrokersDataClientFactory(), build_ib_data_client_config(config)
        )
        .build()
    )
    for actor in (acquisition, planner, dashboard):
        node.add_actor(actor)
    task = asyncio.create_task(node.run_async())
    started = monotonic()
    previous = None
    mutations = 0
    http_samples = 0
    view = {}
    seen_closes = set()
    print(f"LIVE_DASHBOARD | url=http://127.0.0.1:{args.port}", flush=True)
    try:
        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{args.port}") as client:
            while monotonic() - started < args.timeout_seconds and not task.done():
                try:
                    response = await client.get("/api/snapshot")
                    response.raise_for_status()
                    view = response.json()
                except httpx.HTTPError:
                    await asyncio.sleep(0.25)
                    continue
                http_samples += 1
                candles = view["candles"]
                latest = candles[-1] if candles else None
                if latest and previous and latest["time"] == previous["time"]:
                    if any(
                        latest[k] != previous[k] for k in ("open", "high", "low", "close", "volume")
                    ):
                        mutations += 1
                previous = latest
                if acquisition.raw_live:
                    first = acquisition.raw_live[0].ts_event
                    for candle in candles:
                        if candle["status"] == "COMPLETE" and int(candle["ts_event_ns"]) > first:
                            end = candle["ts_event_ns"]
                            if end not in seen_closes:
                                seen_closes.add(end)
                                print(f"MINUTE_COMPLETE | close_ns={end} inputs=12", flush=True)
                if len(seen_closes) >= 2 and mutations >= 2:
                    break
                await asyncio.sleep(0.25)
    finally:
        node.handle().stop()
        await asyncio.wait_for(task, timeout=40)
    # Same overlap rule as the delivery contract, independently reaggregate each minute.
    inputs = {bar.ts_event: bar for bar in acquisition.raw_history}
    inputs.update({bar.ts_event: bar for bar in acquisition.raw_live})
    comparisons = []
    for candle in view.get("candles", []):
        if candle["status"] == "COMPLETE":
            comparisons.append(
                _comparison(
                    SimpleNamespace(
                        ts_event=int(candle["ts_event_ns"]),
                        **{k: candle[k] for k in ("open", "high", "low", "close", "volume")},
                    ),
                    list(inputs.values()),
                )
            )
    passed = (
        len(seen_closes) >= 2
        and mutations >= 2
        and bool(acquisition.raw_history)
        and all(c["complete_5s_coverage"] and c.get("ohlcv_match") for c in comparisons)
        and not node.is_running
        and not dashboard._server.ready.is_set()
    )
    return {
        "passed": passed,
        "elapsed_seconds": round(monotonic() - started, 2),
        "instrument": args.instrument,
        "client_id": args.client_id,
        "port": args.port,
        "historical_inputs": len(acquisition.raw_history),
        "live_inputs": len(acquisition.raw_live),
        "live_minute_closes": len(seen_closes),
        "same_candle_http_changes": mutations,
        "http_samples": http_samples,
        "comparisons": comparisons,
        "node_stopped": not node.is_running,
        "server_stopped": not dashboard._server.ready.is_set(),
        "scope": "Production data path; isolated startup, membership and calendar synchronization",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--instrument", required=True)
    parser.add_argument("--client-id", type=int, required=True)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--timeout-seconds", type=int, default=140)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--connect", choices=["I_UNDERSTAND_THIS_CONNECTS_TO_IB"], required=True)
    args = parser.parse_args()
    if (
        not 1 <= args.client_id <= 999
        or not 1024 <= args.port <= 65535
        or not 30 <= args.timeout_seconds <= 160
    ):
        parser.error("client must be 1..999, port 1024..65535, timeout 30..160 seconds")
    result = asyncio.run(_run(args))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
