from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from markeitech.market_data.actions import build_livenode_action_plan
from markeitech.market_data.bootstrap import build_livenode_bootstrap_summary
from markeitech.market_data.intents import build_nautilus_request_plan
from markeitech.market_data.loader import load_market_data_runtime_config
from markeitech.market_data.nautilus import build_trading_node_config
from markeitech.market_data.planner import build_market_data_plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and print a Stage 2 market-data plan.")
    parser.add_argument("config", type=Path, help="Path to a market-data TOML config file.")
    args = parser.parse_args()

    print(json.dumps(build_plan_summary(args.config), indent=2, sort_keys=True))


def build_plan_summary(config_path: Path) -> dict[str, Any]:
    runtime_config = load_market_data_runtime_config(config_path)
    plan = build_market_data_plan(runtime_config.instrument_registry)
    request_plan = build_nautilus_request_plan(
        plan,
        data_client_name=runtime_config.data_client_name,
    )
    action_plan = build_livenode_action_plan(request_plan)
    node_config = build_trading_node_config(runtime_config)
    bootstrap_summary = build_livenode_bootstrap_summary(runtime_config)
    return {
        "active_instrument_id": plan.active_instrument_id,
        "bootstrap": bootstrap_summary.model_dump(mode="json"),
        "data_client_names": sorted(node_config.data_clients),
        "execution_clients": sorted(node_config.exec_clients),
        "run_live_node": runtime_config.run_live_node,
        "planned_warmups": [
            {
                "instrument_id": warmup.instrument_id,
                "lookback_sessions": warmup.lookback_sessions,
                "timeframes": [timeframe.value for timeframe in warmup.timeframes],
            }
            for warmup in plan.warmups
        ],
        "planned_subscriptions": [
            {
                "instrument_id": subscription.instrument_id,
                "kind": subscription.kind.value,
                "source": subscription.source,
            }
            for subscription in plan.subscriptions
        ],
        "nautilus_warmup_intents": [
            {
                "instrument_id": warmup.instrument_id,
                "kind": warmup.kind.value,
                "bar_types": list(warmup.bar_types),
            }
            for warmup in request_plan.warmups
        ],
        "nautilus_subscription_intents": [
            {
                "instrument_id": subscription.instrument_id,
                "kind": subscription.kind.value,
                "data_client_name": subscription.data_client_name,
                "bar_type": subscription.bar_type,
            }
            for subscription in request_plan.subscriptions
        ],
        "livenode_actions": [
            {
                "instrument_id": action.instrument_id,
                "kind": action.kind.value,
                "phase": action.phase.value,
                "data_client_name": action.data_client_name,
                "bar_type": action.bar_type,
                "lookback_sessions": action.lookback_sessions,
            }
            for action in action_plan.actions
        ],
    }


if __name__ == "__main__":
    main()
