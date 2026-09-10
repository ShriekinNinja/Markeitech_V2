"""Explicitly invoked IB-only native backfill probe; never collected by pytest.

Uses a diagnostic DataAcquisitionActor subclass and the installed native data engine.
Raw observations remain in memory; the result contains counts, timestamps and comparisons.
This does not start the production system or change its provider/configuration policy.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from dataclasses import asdict, replace
from datetime import UTC, datetime
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path
from time import monotonic

from nautilus_trader.adapters.interactive_brokers import InteractiveBrokersDataClientFactory
from nautilus_trader.common import CacheConfig, Environment, LoggerConfig, LogLevel
from nautilus_trader.live import LiveDataEngineConfig, LiveNode
from nautilus_trader.model import BarType, ClientId, InstrumentId, TraderId

from markeitech.system.acquisition import DataAcquisitionActor, DataAcquisitionActorConfig
from markeitech.system.config import load_system_config
from markeitech.system.node import build_ib_data_client_config

SECOND = 1_000_000_000
MINUTE = 60 * SECOND


def _values(bar) -> tuple[Decimal, ...]:  # noqa: ANN001
    return tuple(
        Decimal(str(getattr(bar, name))) for name in ("open", "high", "low", "close", "volume")
    )


def _aggregate_values(inputs: list) -> tuple[Decimal, ...]:
    values = [_values(b) for b in inputs]
    return (
        values[0][0],
        max(v[1] for v in values),
        min(v[2] for v in values),
        values[-1][3],
        sum(v[4] for v in values),
    )


def _comparison(target, sources: list) -> dict:  # noqa: ANN001
    end = target.ts_event
    inputs = sorted(
        (b for b in sources if end - MINUTE < b.ts_event <= end), key=lambda b: b.ts_event
    )
    counts = Counter(b.ts_event for b in inputs)
    complete = len(inputs) == 12 and all(counts[end - i * 5 * SECOND] == 1 for i in range(12))
    result = {"close_ns": str(end), "input_count": len(inputs), "complete_5s_coverage": complete}
    if complete:
        expected = _aggregate_values(inputs)
        result["ohlcv_match"] = _values(target) == expected
        result["mismatched_fields"] = [
            name
            for name, actual, reference in zip(
                ("open", "high", "low", "close", "volume"), _values(target), expected, strict=True
            )
            if actual != reference
        ]
    return result


class _LiveBackfillAcquisition(DataAcquisitionActor):
    """Diagnostic lifecycle only; all provider operations remain on acquisition."""

    def __init__(self, config: DataAcquisitionActorConfig) -> None:
        super().__init__(config)
        instrument_id = config.instrument_ids[0]
        self.instrument_id = InstrumentId.from_str(instrument_id)
        self.source_type = BarType.from_str(f"{instrument_id}-5-SECOND-LAST-EXTERNAL")
        self.target_type = BarType.from_str(
            f"{instrument_id}-1-MINUTE-LAST-INTERNAL@5-SECOND-EXTERNAL"
        )
        self.phase = "waiting_for_instrument"
        self.history: list = []
        self.historical_targets: list = []
        self.live_sources: list = []
        self.live_targets: list = []
        self.target_delivery: list[dict] = []
        self.source_delivery: dict[int, int] = {}
        self.cache_samples: list[dict] = []
        self.subscribed = False
        self.request_bounds: dict = {}
        self.started_monotonic = monotonic()

    def on_start(self) -> None:
        self.clock.set_timer_ns("native-backfill-probe", 250_000_000, callback=self._poll)

    def on_instrument(self, _instrument) -> None:  # noqa: ANN001
        pass  # Provider preloads the one admitted instrument into native cache.

    def on_signal(self, _signal) -> None:  # noqa: ANN001
        pass

    def _cached_targets(self) -> list:
        return list(
            self.cache.bars(self.target_type) or self.cache.bars(self.target_type.standard()) or []
        )

    def _poll(self, _event) -> None:  # noqa: ANN001
        if self.phase == "waiting_for_instrument" and self.cache.instrument(self.instrument_id):
            now = self.clock.timestamp_ns()
            end = now // (5 * SECOND) * (5 * SECOND)
            start = end // MINUTE * MINUTE - 3 * MINUTE
            self.phase = "requesting_history"
            self.request_bounds = {"start_ns": str(start), "end_ns": str(end), "limit": 60}
            # Seed native aggregation BEFORE its live subscription starts.
            self.request_bars(
                self.source_type,
                start=datetime.fromtimestamp(start / SECOND, UTC),
                end=datetime.fromtimestamp(end / SECOND, UTC),
                limit=60,
                client_id=ClientId.from_str("IB"),
                params={"bar_types": [str(self.target_type)], "update_subscriptions": True},
            )
            print("HISTORY_REQUESTED | one ES 5s window, native 1m aggregation", flush=True)
        elif self.phase == "history_received":
            self.historical_targets = self._cached_targets()
            # Native calls occur on a timer, outside the historical callback's bus borrow.
            self.subscribe_bars(self.source_type, client_id=ClientId.from_str("IB"))
            self.subscribe_bars(self.target_type, client_id=ClientId.from_str("IB"))
            self.subscribed = True
            self.phase = "live"
            print(
                f"LIVE_STARTED | historical_inputs={len(self.history)} "
                f"native_history_candles={len(self.historical_targets)}",
                flush=True,
            )
        if self.phase == "live" and len(self.cache_samples) < 700:
            bars = self._cached_targets()
            latest = max(bars, key=lambda b: b.ts_event) if bars else None
            # Keep comparison state transient; only change counts enter the report.
            self.cache_samples.append(
                {
                    "at_ns": self.clock.timestamp_ns(),
                    "source_count": len(self.live_sources),
                    "latest": None if latest is None else (latest.ts_event, _values(latest)),
                }
            )

    def on_historical_bars(self, bars) -> None:  # noqa: ANN001
        self.history = list(bars)
        self.phase = "history_received" if bars else "empty_history"
        print(f"HISTORY_RECEIVED | count={len(self.history)}", flush=True)

    def on_bar(self, bar) -> None:  # noqa: ANN001
        if bar.bar_type == self.source_type:
            if len(self.live_sources) < 80:
                self.live_sources.append(bar)
                self.source_delivery[bar.ts_event] = self.clock.timestamp_ns()
        elif bar.bar_type.standard() == self.target_type.standard():
            self.live_targets.append(bar)
            available = sorted(
                (
                    b
                    for b in self.history + self.live_sources
                    if bar.ts_event - MINUTE < b.ts_event <= bar.ts_event
                ),
                key=lambda b: b.ts_event,
            )
            self.target_delivery.append(
                {
                    "close_ns": str(bar.ts_event),
                    "received_ns": str(self.clock.timestamp_ns()),
                    "available_input_count": len(available),
                    "matches_available_inputs": bool(available)
                    and _values(bar) == _aggregate_values(available),
                }
            )
            print(
                f"NATIVE_MINUTE_CLOSED | close_ns={bar.ts_event} "
                f"live_5s_inputs={len(self.live_sources)}",
                flush=True,
            )

    def on_stop(self) -> None:
        if "native-backfill-probe" in self.clock.timer_names():
            self.clock.cancel_timer("native-backfill-probe")
        if self.subscribed:
            self.unsubscribe_bars(self.target_type, client_id=ClientId.from_str("IB"))
            self.unsubscribe_bars(self.source_type, client_id=ClientId.from_str("IB"))
            self.subscribed = False

    def on_dispose(self) -> None:
        self.on_stop()

    def report(self) -> dict:
        all_sources = self.history + self.live_sources
        history_checks = [_comparison(b, self.history) for b in self.historical_targets]
        live_checks = [_comparison(b, all_sources) for b in self.live_targets]
        source_stamps = sorted(set(b.ts_event for b in all_sources))
        gaps = sum(
            b - a != 5 * SECOND for a, b in zip(source_stamps, source_stamps[1:], strict=False)
        )
        timestamps = [b.ts_event for b in self.live_targets]
        changes_same_candle = sum(
            a["latest"] is not None
            and b["latest"] is not None
            and a["latest"][0] == b["latest"][0]
            and a["latest"][1] != b["latest"][1]
            for a, b in zip(self.cache_samples, self.cache_samples[1:], strict=False)
        )
        return {
            "schema_version": 1,
            "nautilus_version": version("nautilus_trader"),
            "instrument_id": str(self.instrument_id),
            "phase": self.phase,
            "elapsed_seconds": round(monotonic() - self.started_monotonic, 2),
            "request": self.request_bounds,
            "history_source_bars": len(self.history),
            "history_target_bars": len(self.historical_targets),
            "live_source_bars": len(self.live_sources),
            "live_target_bars": len(self.live_targets),
            "historical_checks": history_checks,
            "live_checks": live_checks,
            "target_delivery": [
                {
                    **delivery,
                    "closing_5s_received_ns": (
                        str(self.source_delivery[int(delivery["close_ns"])])
                        if int(delivery["close_ns"]) in self.source_delivery
                        else None
                    ),
                }
                for delivery in self.target_delivery
            ],
            "duplicate_live_target_timestamps": len(timestamps) - len(set(timestamps)),
            "duplicate_source_timestamps": len(all_sources) - len(source_stamps),
            "source_5s_gap_count": gaps,
            "cache_samples": len(self.cache_samples),
            "observed_same_candle_cache_mutations": changes_same_candle,
            "limits": [
                "One instrument and 1m timeframe only; not 4h/daily/session validation.",
                "Historical and realtime IB filtering may differ.",
                "No partial-state API is inferred from completed-cache observations.",
            ],
        }


async def _run(args: argparse.Namespace) -> dict:
    config = load_system_config(args.config)
    if args.instrument not in config.instrument_ids:
        raise ValueError("instrument must already be enabled in the reviewed watchlist")
    if args.client_id == config.ib.client_id:
        raise ValueError("probe client ID must differ from the running system's configured ID")
    member = next(m for m in config.watchlist.members if m.instrument_id == args.instrument)
    config = replace(
        config,
        ib=replace(config.ib, client_id=args.client_id),
        watchlist=replace(config.watchlist, members=(member,)),
    )
    actor = _LiveBackfillAcquisition(
        DataAcquisitionActorConfig(
            instrument_ids=[args.instrument], historical=asdict(config.historical)
        ),
    )
    node = (
        LiveNode.builder(
            "NATIVE-BACKFILL-PROBE", TraderId.from_str("BACKFILL-PROBE-001"), Environment.LIVE
        )
        .with_logging(LoggerConfig(stdout_level=LogLevel.ERROR))
        .with_cache_config(CacheConfig(bar_capacity=200, save_market_data=False))
        .with_data_engine_config(LiveDataEngineConfig(time_bars_build_with_no_updates=False))
        .with_delay_post_stop_secs(0)
        .add_data_client(
            None, InteractiveBrokersDataClientFactory(), build_ib_data_client_config(config)
        )
        .build()
    )
    node.add_actor(actor)
    task = asyncio.create_task(node.run_async())
    deadline = monotonic() + args.timeout_seconds
    try:
        while monotonic() < deadline and not task.done():
            # A timer close can precede IB's final 5s delivery. Keep observing until
            # that source arrives so the comparison cannot pass with missing input.
            enough = (
                len(actor.live_targets) >= 2
                and actor.live_sources
                and actor.live_sources[-1].ts_event >= actor.live_targets[-1].ts_event
            )
            if enough or actor.phase == "empty_history":
                break
            await asyncio.sleep(0.25)
    finally:
        node.handle().stop()
        await asyncio.wait_for(task, timeout=40)
    result = actor.report()
    result["connection"] = {
        "host": config.ib.host,
        "port": config.ib.port,
        "client_id": args.client_id,
    }
    result["node_stopped"] = not node.is_running
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--instrument", required=True)
    parser.add_argument("--client-id", type=int, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=140)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--connect", choices=["I_UNDERSTAND_THIS_CONNECTS_TO_IB"], required=True)
    args = parser.parse_args()
    if not 1 <= args.client_id <= 999 or not 30 <= args.timeout_seconds <= 160:
        parser.error("client ID must be 1..999 and timeout 30..160 seconds")
    result = asyncio.run(_run(args))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)
    checks = result["historical_checks"] + result["live_checks"]
    # A closed-candle pass requires every observed comparison, including handoff.
    # Forming-cache observations remain a separate result, never inferred by this exit code.
    passed = (
        result["history_target_bars"] > 0
        and result["live_target_bars"] >= 2
        and all(r["complete_5s_coverage"] and r.get("ohlcv_match", False) for r in checks)
        and result["source_5s_gap_count"] == 0
        and result["duplicate_source_timestamps"] == 0
        and result["duplicate_live_target_timestamps"] == 0
        and result["node_stopped"]
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
