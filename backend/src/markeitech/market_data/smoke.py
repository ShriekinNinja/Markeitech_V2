from __future__ import annotations

import argparse
import json
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

    print(
        json.dumps(
            run_smoke(args.config, confirmation=args.confirm),
            indent=2,
            sort_keys=True,
        )
    )


def run_smoke(
    config_path: Path,
    *,
    confirmation: str | None,
) -> dict[str, Any]:
    return run_smoke_with_factory(config_path, confirmation=confirmation)


def run_smoke_with_factory(
    config_path: Path,
    *,
    confirmation: str | None,
    node_factory: Any | None = None,
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
    result = start_live_node(runtime_config, node, confirmation=confirmation)
    return {
        "status": "started",
        "result": result,
        "plan": summary,
    }


def _build_node(runtime_config: Any, *, node_factory: Any | None) -> LiveNodeLike:
    if node_factory is None:
        return build_prepared_market_data_live_node(runtime_config)
    return build_prepared_market_data_live_node(runtime_config, node_factory=node_factory)
