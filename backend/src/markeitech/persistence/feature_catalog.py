from __future__ import annotations

import hashlib
import os
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from urllib.parse import quote
from uuid import uuid4

import pyarrow as pa
import pyarrow.parquet as pq

from markeitech.analytics.contracts import AnalyticsTimeframe
from markeitech.analytics.features import MarketContextFeatureSnapshot
from markeitech.domain.base import unix_ns_from_utc_datetime
from markeitech.persistence.config import PersistenceConfig

_FEATURE_SCHEMA = pa.schema(
    [
        ("instrument_id", pa.string()),
        ("feature_id", pa.string()),
        ("content_hash", pa.string()),
        ("envelope_schema_version", pa.string()),
        ("feature_set", pa.string()),
        ("calculation_version", pa.string()),
        ("configuration_hash", pa.string()),
        ("timeframe", pa.string()),
        ("as_of_ns", pa.int64()),
        ("source", pa.string()),
        ("input_fidelity", pa.string()),
        ("envelope_json", pa.string()),
    ]
)


@dataclass(frozen=True)
class MarketContextFeatureRecord:
    instrument_id: str
    feature_id: str
    content_hash: str
    envelope_schema_version: str
    feature_set: str
    calculation_version: str
    configuration_hash: str
    timeframe: str
    as_of_ns: int
    source: str
    input_fidelity: str
    envelope_json: str


@dataclass(frozen=True)
class FeatureCatalogWriteResult:
    submitted_count: int
    written_count: int
    duplicate_count: int
    feature_ids: tuple[str, ...]


class ParquetFeatureStore:
    """Single-writer, append-only catalog for deterministic feature snapshots."""

    def __init__(self, config: PersistenceConfig) -> None:
        self._root = Path(config.catalog_path) / "features" / "market_context"
        self._write_lock = Lock()

    def write(
        self,
        features: Sequence[MarketContextFeatureSnapshot],
    ) -> FeatureCatalogWriteResult:
        if not features:
            return FeatureCatalogWriteResult(0, 0, 0, ())
        unique = _unique_features(features)
        with self._write_lock:
            existing = self._query_existing(tuple(unique.values()))
            pending: list[MarketContextFeatureSnapshot] = []
            for feature_id, feature in unique.items():
                stored = existing.get(feature_id)
                if stored is None:
                    pending.append(feature)
                    continue
                if not _same_feature(stored, feature):
                    raise ValueError(
                        "feature identity conflicts with different persisted content: "
                        f"{feature_id}"
                    )
            written_count = self._write_pending(pending)
        return FeatureCatalogWriteResult(
            submitted_count=len(features),
            written_count=written_count,
            duplicate_count=len(features) - written_count,
            feature_ids=tuple(feature.feature_id for feature in features),
        )

    def query_history(
        self,
        instrument_id: str,
        *,
        timeframe: AnalyticsTimeframe | None = None,
        calculation_version: str | None = None,
        configuration_hash: str | None = None,
    ) -> tuple[MarketContextFeatureSnapshot, ...]:
        with self._write_lock:
            values = self._query_instrument(instrument_id)
        filtered = (
            value
            for value in values
            if (timeframe is None or value.snapshot.timeframe == timeframe)
            and (calculation_version is None or value.calculation_version == calculation_version)
            and (configuration_hash is None or value.configuration_hash == configuration_hash)
        )
        return tuple(
            sorted(
                filtered,
                key=lambda value: (value.snapshot.as_of, value.feature_id),
            )
        )

    def query_latest_variants(
        self,
        instrument_id: str,
        *,
        timeframe: AnalyticsTimeframe,
        calculation_version: str | None = None,
        configuration_hash: str | None = None,
    ) -> tuple[MarketContextFeatureSnapshot, ...]:
        history = self.query_history(
            instrument_id,
            timeframe=timeframe,
            calculation_version=calculation_version,
            configuration_hash=configuration_hash,
        )
        if not history:
            return ()
        latest_as_of = history[-1].snapshot.as_of
        return tuple(value for value in history if value.snapshot.as_of == latest_as_of)

    def _write_pending(self, features: Sequence[MarketContextFeatureSnapshot]) -> int:
        grouped: dict[Path, list[MarketContextFeatureSnapshot]] = defaultdict(list)
        for feature in features:
            grouped[self._partition(feature)].append(feature)
        written = 0
        for partition, values in grouped.items():
            ordered = sorted(values, key=lambda value: value.feature_id)
            batch_id = hashlib.sha256(
                "\n".join(value.feature_id for value in ordered).encode()
            ).hexdigest()
            target = partition / f"{batch_id}.parquet"
            if target.exists():
                stored = tuple(record_to_feature(record) for record in _read_records(target))
                if not _same_feature_batch(stored, ordered):
                    raise ValueError(
                        f"feature batch path conflicts with persisted content: {target}"
                    )
                continue
            records = [feature_to_record(value) for value in ordered]
            _write_atomic(target, records)
            written += len(records)
        return written

    def _query_existing(
        self,
        features: Sequence[MarketContextFeatureSnapshot],
    ) -> dict[str, MarketContextFeatureSnapshot]:
        instrument_ids = sorted({feature.snapshot.instrument_id for feature in features})
        wanted = {feature.feature_id for feature in features}
        existing: dict[str, MarketContextFeatureSnapshot] = {}
        for instrument_id in instrument_ids:
            for value in self._query_instrument(instrument_id):
                if value.feature_id not in wanted:
                    continue
                prior = existing.get(value.feature_id)
                if prior is not None and not _same_feature(prior, value):
                    raise ValueError(
                        "feature catalog contains conflicting persisted identity: "
                        f"{value.feature_id}"
                    )
                existing[value.feature_id] = value
        return existing

    def _query_instrument(
        self,
        instrument_id: str,
    ) -> tuple[MarketContextFeatureSnapshot, ...]:
        instrument_path = self._root / f"instrument={_partition_token(instrument_id)}"
        values: dict[str, MarketContextFeatureSnapshot] = {}
        for path in sorted(instrument_path.rglob("*.parquet")):
            for record in _read_records(path):
                value = record_to_feature(record)
                if value.snapshot.instrument_id != instrument_id:
                    raise ValueError(f"feature partition contains wrong instrument: {path}")
                prior = values.get(value.feature_id)
                if prior is not None and not _same_feature(prior, value):
                    raise ValueError(
                        "feature catalog contains conflicting persisted identity: "
                        f"{value.feature_id}"
                    )
                values[value.feature_id] = value
        return tuple(values.values())

    def _partition(self, feature: MarketContextFeatureSnapshot) -> Path:
        snapshot = feature.snapshot
        return (
            self._root
            / f"instrument={_partition_token(snapshot.instrument_id)}"
            / f"timeframe={_partition_token(snapshot.timeframe.value)}"
            / f"date={snapshot.as_of.date().isoformat()}"
        )


def feature_to_record(feature: MarketContextFeatureSnapshot) -> MarketContextFeatureRecord:
    return MarketContextFeatureRecord(
        instrument_id=feature.snapshot.instrument_id,
        feature_id=feature.feature_id,
        content_hash=feature.content_hash,
        envelope_schema_version=feature.schema_version,
        feature_set=feature.feature_set,
        calculation_version=feature.calculation_version,
        configuration_hash=feature.configuration_hash,
        timeframe=feature.snapshot.timeframe.value,
        as_of_ns=unix_ns_from_utc_datetime(feature.snapshot.as_of),
        source=feature.snapshot.source,
        input_fidelity=feature.snapshot.input_fidelity.value,
        envelope_json=feature.model_dump_json(),
    )


def record_to_feature(record: MarketContextFeatureRecord) -> MarketContextFeatureSnapshot:
    feature = MarketContextFeatureSnapshot.model_validate_json(record.envelope_json)
    if record != feature_to_record(feature):
        raise ValueError("stored feature record metadata does not match its envelope")
    return feature


def _write_atomic(target: Path, records: Sequence[MarketContextFeatureRecord]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
    table = pa.Table.from_pylist(
        [record.__dict__ for record in records],
        schema=_FEATURE_SCHEMA,
    )
    try:
        pq.write_table(table, temporary, compression="zstd")
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        try:
            os.link(temporary, target)
        except FileExistsError:
            stored = _read_records(target)
            stored_features = tuple(record_to_feature(record) for record in stored)
            submitted_features = tuple(record_to_feature(record) for record in records)
            if not _same_feature_batch(stored_features, submitted_features):
                raise ValueError(
                    f"feature batch path conflicts with persisted content: {target}"
                ) from None
        _fsync_directory(target.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _read_records(path: Path) -> tuple[MarketContextFeatureRecord, ...]:
    table = pq.ParquetFile(path).read()
    if table.schema != _FEATURE_SCHEMA:
        raise ValueError(f"unsupported feature parquet schema: {path}")
    return tuple(MarketContextFeatureRecord(**row) for row in table.to_pylist())


def _unique_features(
    features: Sequence[MarketContextFeatureSnapshot],
) -> dict[str, MarketContextFeatureSnapshot]:
    unique: dict[str, MarketContextFeatureSnapshot] = {}
    for feature in features:
        existing = unique.get(feature.feature_id)
        if existing is not None and not _same_feature(existing, feature):
            raise ValueError(
                "feature identity conflicts with different submitted content: "
                f"{feature.feature_id}"
            )
        unique[feature.feature_id] = feature
    return unique


def _same_feature(
    left: MarketContextFeatureSnapshot,
    right: MarketContextFeatureSnapshot,
) -> bool:
    return left.feature_id == right.feature_id and left.content_hash == right.content_hash


def _same_feature_batch(
    left: Sequence[MarketContextFeatureSnapshot],
    right: Sequence[MarketContextFeatureSnapshot],
) -> bool:
    return sorted((value.feature_id, value.content_hash) for value in left) == sorted(
        (value.feature_id, value.content_hash) for value in right
    )


def _partition_token(value: str) -> str:
    return quote(value, safe="._-")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
