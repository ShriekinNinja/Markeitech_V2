from __future__ import annotations

import argparse
import os
import subprocess
from collections.abc import Sequence
from pathlib import Path

from dotenv import load_dotenv

from markeitech.system.config import load_system_config
from markeitech.system.node import build_system_node

IB_CONFIRMATION = "I_UNDERSTAND_THIS_CONNECTS_TO_IB"
V2_ROOT = Path(__file__).resolve().parents[3]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or run the Markeitech v2 system.")
    parser.add_argument(
        "config",
        nargs="?",
        type=Path,
        default=Path("config/system.toml"),
        help="Path to the standalone v2 system TOML.",
    )
    parser.add_argument(
        "--connect",
        metavar="CONFIRMATION",
        help="Connect to IB and run until stopped.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=V2_ROOT / ".env",
        help="Path to the V2 environment file (default: v2/.env).",
    )
    parser.add_argument(
        "--keep-awake",
        action="store_true",
        help="Keep macOS awake for the lifetime of this process.",
    )
    args = parser.parse_args(argv)

    load_dotenv(args.env_file, override=False)
    config = load_system_config(args.config)
    node = build_system_node(config)
    caffeinate = _start_caffeinate() if args.keep_awake else None
    try:
        if args.connect is None:
            print(
                "SYSTEM_BUILT"
                f" | runtime={config.runtime.name}"
                f" | instruments={len(config.instruments)}"
                " | connected=false",
            )
            return 0
        if args.connect != IB_CONFIRMATION:
            parser.error(f"--connect must equal {IB_CONFIRMATION}")

        node.run()
        return 0
    finally:
        if caffeinate is not None:
            caffeinate.terminate()
            caffeinate.wait(timeout=5)


def _start_caffeinate() -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        ["/usr/bin/caffeinate", "-dimsu", "-w", str(os.getpid())],
    )


if __name__ == "__main__":
    raise SystemExit(main())
