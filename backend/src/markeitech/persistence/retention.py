from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol

import pyarrow.parquet as parquet

from markeitech.domain.base import require_utc, unix_ns_from_utc_datetime
from markeitech.persistence.config import PersistenceConfig
from markeitech.persistence.contracts import PersistenceBatch, PersistenceEventKind

_CATALOG_KINDS = {
    "trade_tick": PersistenceEventKind.TRADE_TICK,
    "quote_tick": PersistenceEventKind.QUOTE_TICK,
    "custom_canonical_one_minute_bar_record": PersistenceEventKind.ONE_MINUTE_BAR,
}

RetentionStream = tuple[PersistenceEventKind, str, str]


class RetentionStatus(StrEnum):
    DISABLED = "disabled"
    SKIPPED_UNSAFE = "skipped_unsafe"
    NOOP = "noop"
    COMPLETED = "completed"


@dataclass(frozen=True)
class RetentionReport:
    status: RetentionStatus
    inspected_file_count: int = 0
    catalog_bytes_before: int = 0
    catalog_bytes_after: int = 0
    deleted_file_count: int = 0
    deleted_bytes: int = 0
    pruned_identity_count: int = 0
    pruned_batch_count: int = 0
    unmanaged_instruments: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class _CatalogFile:
    path: Path
    event_kind: PersistenceEventKind
    instrument_id: str
    sources: tuple[str, ...]
    minimum_event_ts_ns: int
    maximum_event_ts_ns: int
    size_bytes: int


class RetentionCalendar(Protocol):
    def has_policy(self, instrument_id: str) -> bool: ...

    def retention_cutoff(
        self,
        instrument_id: str,
        completed_sessions: int,
        as_of: datetime,
    ) -> datetime: ...


class RetentionMetadataStore(Protocol):
    def incomplete_batches(self) -> tuple[PersistenceBatch, ...]: ...

    def retention_streams(self) -> frozenset[RetentionStream]: ...

    def prune_committed_history(
        self,
        cutoffs: dict[RetentionStream, int],
    ) -> tuple[int, int]: ...


class CatalogRetentionMaintenance:
    """Retire whole catalog files before pruning their idempotency evidence."""

    def __init__(
        self,
        config: PersistenceConfig,
        calendar: RetentionCalendar,
        metadata: RetentionMetadataStore,
        *,
        native_tick_source: str = "ib",
    ) -> None:
        self._config = config
        self._calendar = calendar
        self._metadata = metadata
        self._native_tick_source = native_tick_source

    def run(self, as_of: datetime) -> RetentionReport:
        as_of = require_utc(as_of)
        if not self._config.retention_maintenance_enabled:
            return RetentionReport(status=RetentionStatus.DISABLED)
        if any(self._config.journal_path.glob("*.wal")):
            return RetentionReport(
                status=RetentionStatus.SKIPPED_UNSAFE,
                reason_codes=("journal_replay_required",),
            )
        if self._metadata.incomplete_batches():
            return RetentionReport(
                status=RetentionStatus.SKIPPED_UNSAFE,
                reason_codes=("incomplete_persistence_batches",),
            )

        files = self._inspect_catalog()
        streams = self._metadata.retention_streams() | frozenset(
            stream for item in files for stream in self._streams(item)
        )
        policy_cutoffs, unmanaged = self._policy_cutoffs(streams, as_of)
        candidates = {
            item.path
            for item in files
            if all(stream in policy_cutoffs for stream in self._streams(item))
            and all(
                item.maximum_event_ts_ns < policy_cutoffs[stream] for stream in self._streams(item)
            )
        }
        deleted_bytes = sum(item.size_bytes for item in files if item.path in candidates)
        for path in sorted(candidates):
            path.unlink()
            _sync_directory(path.parent)

        retained_files = self._inspect_catalog()
        safe_cutoffs = self._safe_metadata_cutoffs(policy_cutoffs, retained_files)
        identities, batches = self._metadata.prune_committed_history(safe_cutoffs)
        changed = bool(candidates or identities or batches)
        return RetentionReport(
            status=RetentionStatus.COMPLETED if changed else RetentionStatus.NOOP,
            inspected_file_count=len(files),
            catalog_bytes_before=sum(item.size_bytes for item in files),
            catalog_bytes_after=sum(item.size_bytes for item in retained_files),
            deleted_file_count=len(candidates),
            deleted_bytes=deleted_bytes,
            pruned_identity_count=identities,
            pruned_batch_count=batches,
            unmanaged_instruments=tuple(sorted(unmanaged)),
            reason_codes=(("unmanaged_instruments_retained",) if unmanaged else ()),
        )

    def _inspect_catalog(self) -> tuple[_CatalogFile, ...]:
        root = self._config.catalog_path / "data"
        if not root.exists():
            return ()
        inspected: list[_CatalogFile] = []
        for kind_name, event_kind in _CATALOG_KINDS.items():
            kind_path = root / kind_name
            if not kind_path.exists():
                continue
            for path in sorted(kind_path.glob("*/*.parquet")):
                minimum, maximum = _event_bounds(path)
                sources = (
                    _bar_sources(path)
                    if event_kind == PersistenceEventKind.ONE_MINUTE_BAR
                    else (self._native_tick_source,)
                )
                inspected.append(
                    _CatalogFile(
                        path=path,
                        event_kind=event_kind,
                        instrument_id=path.parent.name,
                        sources=sources,
                        minimum_event_ts_ns=minimum,
                        maximum_event_ts_ns=maximum,
                        size_bytes=path.stat().st_size,
                    )
                )
        return tuple(inspected)

    def _policy_cutoffs(
        self,
        streams: frozenset[RetentionStream],
        as_of: datetime,
    ) -> tuple[dict[RetentionStream, int], set[str]]:
        cutoffs: dict[RetentionStream, int] = {}
        unmanaged: set[str] = set()
        for stream in streams:
            event_kind, instrument_id, _ = stream
            if not self._calendar.has_policy(instrument_id):
                unmanaged.add(instrument_id)
                continue
            sessions = (
                self._config.bar_retention_sessions
                if event_kind == PersistenceEventKind.ONE_MINUTE_BAR
                else self._config.tick_retention_sessions
            )
            cutoff = unix_ns_from_utc_datetime(
                self._calendar.retention_cutoff(instrument_id, sessions, as_of)
            )
            cutoffs[stream] = cutoff
        return cutoffs, unmanaged

    @staticmethod
    def _safe_metadata_cutoffs(
        policy_cutoffs: dict[RetentionStream, int],
        retained_files: tuple[_CatalogFile, ...],
    ) -> dict[RetentionStream, int]:
        retained_floors: dict[RetentionStream, int] = defaultdict(lambda: 2**63 - 1)
        for item in retained_files:
            for stream in CatalogRetentionMaintenance._streams(item):
                retained_floors[stream] = min(
                    retained_floors[stream],
                    item.minimum_event_ts_ns,
                )
        return {
            stream: min(cutoff, retained_floors[stream])
            for stream, cutoff in policy_cutoffs.items()
        }

    @staticmethod
    def _streams(item: _CatalogFile) -> tuple[RetentionStream, ...]:
        return tuple((item.event_kind, item.instrument_id, source) for source in item.sources)


def _event_bounds(path: Path) -> tuple[int, int]:
    file = parquet.ParquetFile(path)
    minimum: int | None = None
    maximum: int | None = None
    for row_group_index in range(file.metadata.num_row_groups):
        row_group = file.metadata.row_group(row_group_index)
        for column_index in range(row_group.num_columns):
            column = row_group.column(column_index)
            if column.path_in_schema != "ts_event" or column.statistics is None:
                continue
            column_minimum = int(column.statistics.min)
            column_maximum = int(column.statistics.max)
            minimum = column_minimum if minimum is None else min(minimum, column_minimum)
            maximum = column_maximum if maximum is None else max(maximum, column_maximum)
    if minimum is None or maximum is None:
        values = parquet.read_table(path, columns=["ts_event"])["ts_event"].to_pylist()
        if not values:
            raise ValueError(f"catalog file has no event timestamps: {path}")
        minimum, maximum = min(values), max(values)
    return minimum, maximum


def _bar_sources(path: Path) -> tuple[str, ...]:
    values = parquet.read_table(path, columns=["source"])["source"].to_pylist()
    sources = tuple(sorted({str(value) for value in values if value}))
    if not sources:
        raise ValueError(f"canonical bar file has no source: {path}")
    return sources


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
