from __future__ import annotations

import argparse
import asyncio
import json
import signal
from collections.abc import Callable
from pathlib import Path
from typing import Any

from markeitech.market_data.bootstrap import (
    LIVE_NODE_START_CONFIRMATION,
    LiveNodeLike,
    build_livenode_bootstrap_summary,
    build_prepared_market_data_live_node,
    start_live_node,
)
from markeitech.market_data.cli import build_plan_summary
from markeitech.market_data.loader import load_market_data_runtime_config


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manual Interactive Brokers smoke-test entry point.",
    )
    parser.add_argument("config", type=Path, help="Path to a market-data TOML config file.")
    parser.add_argument(
        "--confirm",
        default=None,
        help=f"Required token to start the LiveNode: {LIVE_NODE_START_CONFIRMATION}",
    )
    args = parser.parse_args()

    print(json.dumps(run_smoke(args.config, confirmation=args.confirm), indent=2, sort_keys=True))


def run_smoke(
    config_path: Path,
    *,
    confirmation: str | None,
) -> dict[str, Any]:
    return run_smoke_with_factory(
        config_path,
        confirmation=confirmation,
        continuous_runner=run_until_shutdown_signal,
    )


def run_smoke_with_factory(
    config_path: Path,
    *,
    confirmation: str | None,
    node_factory: Any | None = None,
    continuous_runner: Callable[[LiveNodeLike], Any] | None = None,
) -> dict[str, Any]:
    runtime_config = load_market_data_runtime_config(config_path)
    summary = build_plan_summary(config_path)
    bootstrap = build_livenode_bootstrap_summary(runtime_config)

    if not bootstrap.will_start_node:
        return {
            "status": "refused",
            "reason": "config_does_not_enable_manual_livenode_start",
            "required_confirmation": LIVE_NODE_START_CONFIRMATION,
            "plan": summary,
        }

    if confirmation != LIVE_NODE_START_CONFIRMATION:
        return {
            "status": "refused",
            "reason": "missing_or_invalid_confirmation",
            "required_confirmation": LIVE_NODE_START_CONFIRMATION,
            "plan": summary,
        }

    node = _build_node(runtime_config, node_factory=node_factory)
    if continuous_runner is None:
        result = start_live_node(runtime_config, node, confirmation=confirmation)
        status = "started"
    else:
        result = continuous_runner(node)
        status = "stopped"
    return {
        "status": status,
        "result": result,
        "plan": summary,
    }


def _build_node(runtime_config: Any, *, node_factory: Any | None) -> LiveNodeLike:
    if node_factory is None:
        return build_prepared_market_data_live_node(runtime_config)
    return build_prepared_market_data_live_node(runtime_config, node_factory=node_factory)


def run_until_shutdown_signal(node: LiveNodeLike) -> str | None:
    get_event_loop = getattr(node, "get_event_loop", None)
    if not callable(get_event_loop):
        raise TypeError("continuous LiveNode requires access to its event loop")
    loop = get_event_loop()
    if loop is None:
        raise RuntimeError("continuous LiveNode did not provide an event loop")
    if loop.is_running():
        raise RuntimeError("continuous LiveNode event loop is already running")
    return loop.run_until_complete(_run_until_shutdown_signal(node))


async def _run_until_shutdown_signal(
    node: LiveNodeLike,
    *,
    shutdown_requested: asyncio.Event | None = None,
) -> str | None:
    run_async = getattr(node, "run_async", None)
    stop_async = getattr(node, "stop_async", None)
    if not callable(run_async) or not callable(stop_async):
        raise TypeError("continuous LiveNode requires run_async and stop_async")

    loop = asyncio.get_running_loop()
    shutdown_requested = shutdown_requested or asyncio.Event()
    received_signal: list[signal.Signals] = []

    def request_shutdown(received: signal.Signals) -> None:
        if not received_signal:
            received_signal.append(received)
            print(f"SHUTDOWN_REQUESTED | signal={received.name}", flush=True)
        shutdown_requested.set()

    installed_signals: list[signal.Signals] = []
    for shutdown_signal in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        try:
            loop.add_signal_handler(shutdown_signal, request_shutdown, shutdown_signal)
        except (NotImplementedError, RuntimeError):
            continue
        installed_signals.append(shutdown_signal)

    run_task = asyncio.create_task(run_async())
    shutdown_task = asyncio.create_task(shutdown_requested.wait())
    try:
        done, _ = await asyncio.wait(
            (run_task, shutdown_task),
            return_when=asyncio.FIRST_COMPLETED,
        )
        if shutdown_task in done and not run_task.done():
            await stop_async()
        await run_task
        if received_signal:
            print(f"SHUTDOWN_COMPLETE | signal={received_signal[0].name}", flush=True)
            return received_signal[0].name
        return None
    finally:
        shutdown_task.cancel()
        await asyncio.gather(shutdown_task, return_exceptions=True)
        for shutdown_signal in installed_signals:
            loop.remove_signal_handler(shutdown_signal)
