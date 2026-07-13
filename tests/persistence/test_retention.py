from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pyarrow as arrow
import pyarrow.parquet as parquet
import pytest
from markeitech.domain.base import unix_ns_from_utc_datetime
from markeitech.persistence import (
    CatalogRetentionMaintenance,
    PersistenceConfig,
    PersistenceEventKind,
    RetentionReport,
    RetentionStatus,
)

NOW = datetime(2026, 7, 13, 10, tzinfo=UTC)
TICK_CUTOFF = datetime(2026, 7, 6, 22, tzinfo=UTC)
BAR_CUTOFF = datetime(2025, 7, 15, 13, 30, tzinfo=UTC)


class StubCalendar:
    def has_policy(self, instrument_id: str) -> bool:
        return instrument_id != "UNKNOWN.CME"

    def retention_cutoff(
        self,
        instrument_id: str,
        completed_sessions: int,
        as_of: datetime,
    ) -> datetime:
        assert as_of == NOW
        return BAR_CUTOFF if completed_sessions == 250 else TICK_CUTOFF


class StubMetadata:
    def __init__(
        self,
        *,
        incomplete: bool = False,
        streams: frozenset[tuple[PersistenceEventKind, str, str]] = frozenset(),
    ) -> None:
        self.incomplete = incomplete
        self.streams = streams
        self.cutoffs: dict[tuple[PersistenceEventKind, str, str], int] | None = None
        self.reports: list[RetentionReport] = []

    def incomplete_batches(self) -> tuple[object, ...]:
        return (object(),) if self.incomplete else ()

    def retention_streams(self) -> frozenset[tuple[PersistenceEventKind, str, str]]:
        return self.streams

    def save_retention_report(self, report: RetentionReport) -> None:
        self.reports.append(report)

    def prune_committed_history(
        self,
        cutoffs: dict[tuple[PersistenceEventKind, str, str], int],
    ) -> tuple[int, int]:
        self.cutoffs = cutoffs
        return 2, 1


def config(tmp_path: Path, *, enabled: bool = True) -> PersistenceConfig:
    return PersistenceConfig(
        catalog_path=tmp_path / "catalog",
        metadata_path=tmp_path / "runtime" / "metadata.sqlite3",
        journal_path=tmp_path / "runtime" / "journal",
        retention_maintenance_enabled=enabled,
    )


def write_catalog_file(
    root: Path,
    kind: str,
    instrument_id: str,
    name: str,
    timestamps: tuple[datetime, ...],
    *,
    source: str | None = None,
) -> Path:
    path = root / "data" / kind / instrument_id / f"{name}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    columns: dict[str, arrow.Array] = {
        "ts_event": arrow.array(
            [unix_ns_from_utc_datetime(value) for value in timestamps],
            type=arrow.int64(),
        )
    }
    if source is not None:
        columns["source"] = arrow.array([source] * len(timestamps))
    parquet.write_table(arrow.table(columns), path)
    return path


def test_retention_deletes_wholly_expired_files_before_pruning_metadata(
    tmp_path: Path,
) -> None:
    persistence_config = config(tmp_path)
    old = write_catalog_file(
        persistence_config.catalog_path,
        "trade_tick",
        "NQU6.CME",
        "old",
        (TICK_CUTOFF - timedelta(minutes=2), TICK_CUTOFF - timedelta(minutes=1)),
    )
    mixed_floor = TICK_CUTOFF - timedelta(seconds=30)
    mixed = write_catalog_file(
        persistence_config.catalog_path,
        "trade_tick",
        "NQU6.CME",
        "mixed",
        (mixed_floor, TICK_CUTOFF + timedelta(seconds=30)),
    )
    bar = write_catalog_file(
        persistence_config.catalog_path,
        "custom_canonical_one_minute_bar_record",
        "NQU6.CME",
        "old-bar",
        (BAR_CUTOFF - timedelta(days=1),),
        source="ib",
    )
    unmanaged = write_catalog_file(
        persistence_config.catalog_path,
        "quote_tick",
        "UNKNOWN.CME",
        "unmanaged",
        (TICK_CUTOFF - timedelta(days=30),),
    )
    metadata = StubMetadata()

    report = CatalogRetentionMaintenance(
        persistence_config,
        StubCalendar(),
        metadata,
    ).run(NOW)

    assert report.status == RetentionStatus.COMPLETED
    assert report.deleted_file_count == 2
    assert report.catalog_bytes_before > report.catalog_bytes_after
    assert report.catalog_bytes_before - report.catalog_bytes_after == report.deleted_bytes
    assert report.pruned_identity_count == 2
    assert report.pruned_batch_count == 1
    assert report.unmanaged_instruments == ("UNKNOWN.CME",)
    assert report.reason_codes == ("unmanaged_instruments_retained",)
    assert metadata.reports == [report]
    assert not old.exists()
    assert not bar.exists()
    assert mixed.exists()
    assert unmanaged.exists()
    assert metadata.cutoffs is not None
    assert metadata.cutoffs[
        (PersistenceEventKind.TRADE_TICK, "NQU6.CME", "ib")
    ] == unix_ns_from_utc_datetime(mixed_floor)
    assert metadata.cutoffs[
        (PersistenceEventKind.ONE_MINUTE_BAR, "NQU6.CME", "ib")
    ] == unix_ns_from_utc_datetime(BAR_CUTOFF)


def test_retention_skips_before_inspection_when_wal_or_incomplete_batches_exist(
    tmp_path: Path,
) -> None:
    persistence_config = config(tmp_path)
    old = write_catalog_file(
        persistence_config.catalog_path,
        "trade_tick",
        "NQU6.CME",
        "old",
        (TICK_CUTOFF - timedelta(days=1),),
    )
    persistence_config.journal_path.mkdir(parents=True)
    wal = persistence_config.journal_path / "pending.wal"
    wal.write_bytes(b"pending")
    metadata = StubMetadata()

    wal_report = CatalogRetentionMaintenance(
        persistence_config,
        StubCalendar(),
        metadata,
    ).run(NOW)
    wal.unlink()
    metadata.incomplete = True
    incomplete_report = CatalogRetentionMaintenance(
        persistence_config,
        StubCalendar(),
        metadata,
    ).run(NOW)

    assert wal_report.status == RetentionStatus.SKIPPED_UNSAFE
    assert wal_report.reason_codes == ("journal_replay_required",)
    assert incomplete_report.status == RetentionStatus.SKIPPED_UNSAFE
    assert incomplete_report.reason_codes == ("incomplete_persistence_batches",)
    assert metadata.reports == [wal_report, incomplete_report]
    assert old.exists()
    assert metadata.cutoffs is None


def test_retention_finishes_metadata_pruning_after_last_file_was_already_deleted(
    tmp_path: Path,
) -> None:
    stream = (PersistenceEventKind.TRADE_TICK, "NQU6.CME", "ib")
    metadata = StubMetadata(streams=frozenset({stream}))

    report = CatalogRetentionMaintenance(
        config(tmp_path),
        StubCalendar(),
        metadata,
    ).run(NOW)

    assert report.status == RetentionStatus.COMPLETED
    assert report.inspected_file_count == 0
    assert metadata.cutoffs == {stream: unix_ns_from_utc_datetime(TICK_CUTOFF)}


def test_retention_is_disabled_until_explicitly_configured(tmp_path: Path) -> None:
    metadata = StubMetadata()

    report = CatalogRetentionMaintenance(
        config(tmp_path, enabled=False),
        StubCalendar(),
        metadata,
    ).run(NOW)

    assert report.status == RetentionStatus.DISABLED
    assert metadata.cutoffs is None
    assert metadata.reports == []


def test_retention_records_failure_without_masking_original_error(tmp_path: Path) -> None:
    persistence_config = config(tmp_path)
    corrupt = (
        persistence_config.catalog_path / "data" / "trade_tick" / "NQU6.CME" / "corrupt.parquet"
    )
    corrupt.parent.mkdir(parents=True)
    corrupt.write_bytes(b"not parquet")
    metadata = StubMetadata()

    with pytest.raises(Exception, match="Parquet"):
        CatalogRetentionMaintenance(
            persistence_config,
            StubCalendar(),
            metadata,
        ).run(NOW)

    assert len(metadata.reports) == 1
    assert metadata.reports[0].status == RetentionStatus.FAILED
    assert metadata.reports[0].error is not None
