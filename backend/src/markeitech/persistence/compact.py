from __future__ import annotations

import argparse
import json
from pathlib import Path

from markeitech.market_data.loader import load_market_data_runtime_config
from markeitech.persistence.contracts import SQLiteCompactionReport
from markeitech.persistence.sqlite import SQLiteMetadataStore

SQLITE_COMPACTION_CONFIRMATION = "I_UNDERSTAND_THIS_REWRITES_SQLITE"


def run_sqlite_compaction(
    config_path: Path,
    *,
    confirmation: str | None,
    minimum_reclaimable_bytes: int | None = None,
) -> SQLiteCompactionReport:
    if confirmation != SQLITE_COMPACTION_CONFIRMATION:
        raise RuntimeError(
            "SQLite compaction requires explicit confirmation and a stopped LiveNode"
        )
    runtime = load_market_data_runtime_config(config_path)
    if runtime.persistence is None:
        raise RuntimeError("market-data configuration does not enable persistence")
    threshold = (
        runtime.persistence.sqlite_compaction_min_reclaimable_bytes
        if minimum_reclaimable_bytes is None
        else minimum_reclaimable_bytes
    )
    with SQLiteMetadataStore(runtime.persistence) as metadata:
        return metadata.compact_database(threshold)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compact Markeitech SQLite metadata while the LiveNode is stopped.",
    )
    parser.add_argument("config", type=Path, help="Path to a market-data TOML config.")
    parser.add_argument(
        "--minimum-reclaim-mib",
        type=int,
        default=None,
        help="Override the configured minimum reclaimable space in MiB.",
    )
    parser.add_argument(
        "--confirm",
        default=None,
        help=f"Required token: {SQLITE_COMPACTION_CONFIRMATION}",
    )
    args = parser.parse_args()
    if args.minimum_reclaim_mib is not None and args.minimum_reclaim_mib < 0:
        parser.error("--minimum-reclaim-mib cannot be negative")
    report = run_sqlite_compaction(
        args.config,
        confirmation=args.confirm,
        minimum_reclaimable_bytes=(
            None if args.minimum_reclaim_mib is None else args.minimum_reclaim_mib * 1024 * 1024
        ),
    )
    print(json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
