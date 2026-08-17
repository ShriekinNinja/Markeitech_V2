from __future__ import annotations

import argparse
import os
import subprocess
from collections.abc import Sequence
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

from markeitech.system.composition import StartupPrerequisites, validate_runtime_environment
from markeitech.system.config import load_system_config
from markeitech.system.node import build_system_node
from markeitech.system.persistence import OperationalStore

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
    if args.connect is None:
        build_system_node(
            config,
            StartupPrerequisites(
                run_id=uuid4(),
                operational_persistence_ready=True,
            ),
        )
        print(
            "SYSTEM_BUILT"
            f" | runtime={config.runtime.name}"
            f" | instruments={len(config.instrument_ids)}"
            " | connected=false",
        )
        return 0
    if args.connect != IB_CONFIRMATION:
        parser.error(f"--connect must equal {IB_CONFIRMATION}")

    validate_runtime_environment(config, os.environ)
    store = OperationalStore.from_environment(
        config.persistence.dsn_env,
        config.persistence.connect_timeout_seconds,
    )
    store.initialize()
    recency_profiles = store.load_evidence_recency_profiles(
        config.evidence_health.provider_id,
    )
    run_id = uuid4()
    node = build_system_node(
        config,
        StartupPrerequisites(
            run_id=run_id,
            operational_persistence_ready=True,
            evidence_recency_profiles=recency_profiles,
        ),
    )
    store.start_run(config.runtime.name, run_id)
    caffeinate = _start_caffeinate() if args.keep_awake else None
    try:
        node.run()
    except BaseException:
        raise
    else:
        store.close_run(run_id, "STOPPED", "Nautilus LiveNode returned cleanly")
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
