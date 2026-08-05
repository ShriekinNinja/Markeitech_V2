from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from markeitech.market_data.bootstrap import LIVE_NODE_START_CONFIRMATION
from markeitech.market_data.loader import load_market_data_runtime_config
from markeitech.options.probe import IbOptionChainProbe, OptionChainProbeConfig


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe a bounded SPY 0DTE option window through the IB API.",
    )
    parser.add_argument("config", type=Path, help="Path to a market-data TOML config file.")
    parser.add_argument(
        "--confirm",
        default=None,
        help=f"Required token to connect to IB: {LIVE_NODE_START_CONFIRMATION}",
    )
    parser.add_argument(
        "--client-id",
        type=int,
        help="Dedicated IB client ID. Defaults to the runtime client ID plus 20.",
    )
    parser.add_argument("--strikes-each-side", type=int, default=3)
    parser.add_argument("--observe-seconds", type=float, default=5.0)
    args = parser.parse_args()

    if args.confirm != LIVE_NODE_START_CONFIRMATION:
        print(
            json.dumps(
                {
                    "status": "refused",
                    "reason": "missing_or_invalid_confirmation",
                    "required_confirmation": LIVE_NODE_START_CONFIRMATION,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)
    runtime = load_market_data_runtime_config(args.config)
    expiry = datetime.now(ZoneInfo("America/New_York")).date()
    config = OptionChainProbeConfig(
        host=runtime.ib.host,
        port=runtime.ib.port,
        client_id=args.client_id if args.client_id is not None else runtime.ib.client_id + 20,
        expiry=expiry,
        strikes_each_side=args.strikes_each_side,
        observation_seconds=args.observe_seconds,
        request_timeout_seconds=runtime.ib.request_timeout_seconds,
    )
    report = IbOptionChainProbe(config).execute()
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
