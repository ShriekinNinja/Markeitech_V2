from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from markeitech.domain.instruments import InstrumentRuntimeConfig
from markeitech.market_data.loader import load_market_data_runtime_config
from markeitech.persistence import (
    NautilusParquetTimeSeriesStore,
    PandasMarketSessionCalendar,
    ParquetFeatureStore,
    SQLiteMetadataStore,
)
from markeitech.research.outcomes import SignalAuditHistory
from markeitech.research.references import (
    enrich_reference_annotations,
    render_reference_report,
    sync_reference_csv,
    write_reference_artifacts,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync and enrich Markeitect reference annotations without mutating live state.",
    )
    parser.add_argument("config", type=Path, help="Path to a market-data TOML config file.")
    parser.add_argument(
        "workspace",
        type=Path,
        help="Ignored reference-set directory containing the CSV and screenshots/.",
    )
    parser.add_argument(
        "--sync-only",
        action="store_true",
        help="Sync screenshot-derived draft rows without querying persisted evidence.",
    )
    parser.add_argument("--output", type=Path, help="Enriched artifact directory.")
    args = parser.parse_args()

    config = load_market_data_runtime_config(args.config)
    aliases = _instrument_aliases(config.instrument_registry.instruments)
    annotations = sync_reference_csv(args.workspace, instrument_aliases=aliases)
    if args.sync_only:
        print(
            f"REFERENCE_SET_SYNC | annotations={len(annotations)} "
            f"| csv={(args.workspace / 'markeitect-reference-set.csv').resolve()}"
        )
        return
    if config.persistence is None:
        raise ValueError("reference enrichment requires configured persistence")

    instruments = sorted({item.instrument_id for item in annotations})
    feature_catalog = ParquetFeatureStore(config.persistence)
    features = {
        instrument_id: feature_catalog.query_history(instrument_id)
        for instrument_id in instruments
    }
    with SQLiteMetadataStore(config.persistence, read_only=True) as metadata:
        histories = tuple(
            SignalAuditHistory(
                current=signal,
                transitions=metadata.load_signal_transitions(signal.signal_id),
            )
            for signal in metadata.load_signals()
            if signal.instrument_id in instruments
        )
        committed_feature_ids = metadata.committed_feature_ids(
            tuple(feature for values in features.values() for feature in values)
        )
    catalog = NautilusParquetTimeSeriesStore(config.persistence)
    bars = {
        instrument_id: catalog.query_one_minute_bars(instrument_id)
        for instrument_id in instruments
    }
    records = enrich_reference_annotations(
        annotations,
        bars_by_instrument=bars,
        features_by_instrument=features,
        committed_feature_ids=committed_feature_ids,
        histories=histories,
        calendar=PandasMarketSessionCalendar.from_registry(config.instrument_registry),
    )
    report = render_reference_report(records)
    output = args.output or args.workspace / "output"
    dataset_path, report_path = write_reference_artifacts(
        records,
        report=report,
        output_directory=output,
    )
    complete = sum(not item.missing_human_fields for item in records)
    print(
        f"REFERENCE_SET_ENRICH | annotations={len(records)} | complete={complete} "
        f"| drafts={len(records) - complete} | dataset={dataset_path.resolve()} "
        f"| report={report_path.resolve()}"
    )


def _instrument_aliases(runtimes: Sequence[InstrumentRuntimeConfig]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    roots: dict[str, set[str]] = {}
    for runtime in runtimes:
        contract = runtime.contract
        instrument_id = contract.instrument_id
        aliases[instrument_id.upper()] = instrument_id
        roots.setdefault(contract.root_symbol.upper(), set()).add(instrument_id)
    for root, instrument_ids in roots.items():
        if len(instrument_ids) == 1:
            aliases[root] = next(iter(instrument_ids))
    return aliases
