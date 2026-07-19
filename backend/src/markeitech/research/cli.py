from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from markeitech.market_data.loader import load_market_data_runtime_config
from markeitech.persistence import (
    NautilusParquetTimeSeriesStore,
    PandasMarketSessionCalendar,
    ParquetFeatureStore,
    SQLiteMetadataStore,
)
from markeitech.research import (
    SignalAuditHistory,
    audit_signal_outcomes,
    render_signal_outcome_report,
    write_signal_outcome_artifacts,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit persisted signal outcomes without mutating live state.",
    )
    parser.add_argument("config", type=Path, help="Path to a market-data TOML config file.")
    parser.add_argument("--start", required=True, type=_utc_datetime, help="Inclusive UTC start.")
    parser.add_argument("--end", required=True, type=_utc_datetime, help="Exclusive UTC end.")
    parser.add_argument("--output", type=Path, help="Artifact directory.")
    args = parser.parse_args()

    config = load_market_data_runtime_config(args.config)
    if config.persistence is None:
        raise ValueError("signal outcome audit requires configured persistence")
    feature_catalog = ParquetFeatureStore(config.persistence)
    with SQLiteMetadataStore(config.persistence, read_only=True) as metadata:
        histories = tuple(
            SignalAuditHistory(
                current=signal,
                transitions=metadata.load_signal_transitions(signal.signal_id),
            )
            for signal in metadata.load_signals()
        )
        instruments = {
            event.current.instrument_id
            for history in histories
            for event in history.transitions
            if args.start <= event.occurred_ts < args.end
        }
        features = tuple(
            feature
            for instrument_id in sorted(instruments)
            for feature in feature_catalog.query_history(instrument_id)
        )
        committed_feature_ids = metadata.committed_feature_ids(features)
    catalog = NautilusParquetTimeSeriesStore(config.persistence)
    bars = {
        instrument_id: catalog.query_one_minute_bars(instrument_id)
        for instrument_id in sorted(instruments)
    }
    records = audit_signal_outcomes(
        histories,
        bars,
        calendar=PandasMarketSessionCalendar.from_registry(config.instrument_registry),
        role_by_instrument={
            runtime.contract.instrument_id: (
                runtime.role.value if runtime.enabled else "unknown"
            )
            for runtime in config.instrument_registry.instruments
        },
        available_feature_ids=committed_feature_ids,
        start_ts=args.start,
        end_ts=args.end,
    )
    report = render_signal_outcome_report(records, start_ts=args.start, end_ts=args.end)
    output = args.output or Path("data/research/signal-outcomes") / args.start.date().isoformat()
    dataset_path, report_path = write_signal_outcome_artifacts(
        records,
        report=report,
        output_directory=output,
    )
    armed = sum(item.event_kind.value == "armed" for item in records)
    triggered = sum(item.event_kind.value == "triggered" for item in records)
    print(
        f"SIGNAL_OUTCOME_AUDIT | records={len(records)} | armed={armed} "
        f"| triggered={triggered} | dataset={dataset_path.resolve()} "
        f"| report={report_path.resolve()}"
    )


def _utc_datetime(value: str) -> datetime:
    normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid ISO timestamp: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise argparse.ArgumentTypeError("timestamp must be timezone-aware UTC")
    return parsed.astimezone(UTC)
