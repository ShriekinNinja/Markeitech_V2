from __future__ import annotations

import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from threading import Event

from markeitech.domain import OneMinuteBar
from markeitech.domain.base import unix_ns_from_utc_datetime
from markeitech.persistence import (
    BoundedPersistenceWriter,
    IdempotentPersistenceCoordinator,
    NautilusParquetTimeSeriesStore,
    PersistenceConfig,
    PersistenceSubmissionStatus,
    PersistenceWriteResult,
    PersistenceWriterStatus,
    SQLiteMetadataStore,
)
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.enums import AggressorSide
from nautilus_trader.model.identifiers import InstrumentId, TradeId
from nautilus_trader.model.objects import Price, Quantity

BASE_NS = 1_786_360_120_000_000_000
FUTURE = datetime(2026, 8, 11, tzinfo=UTC)


def trade_tick(offset_ns: int) -> TradeTick:
    return TradeTick(
        instrument_id=InstrumentId.from_str("NQU6.CME"),
        price=Price.from_str("20000.25"),
        size=Quantity.from_str("1"),
        aggressor_side=AggressorSide.BUYER,
        trade_id=TradeId(f"trade-{offset_ns}"),
        ts_event=BASE_NS + offset_ns,
        ts_init=BASE_NS + offset_ns + 100,
    )


def provisional_bar() -> OneMinuteBar:
    return OneMinuteBar(
        instrument_id="NQU6.CME",
        event_ts=datetime(2026, 8, 10, 11, 9, tzinfo=UTC),
        ts_init=datetime(2026, 8, 10, 11, 8, tzinfo=UTC),
        open_ts=datetime(2026, 8, 10, 11, 8, tzinfo=UTC),
        close_ts=datetime(2026, 8, 10, 11, 9, tzinfo=UTC),
        open=Decimal("20000"),
        high=Decimal("20001"),
        low=Decimal("19999"),
        close=Decimal("20000.25"),
        volume=Decimal("1"),
        buy_volume=Decimal("0"),
        sell_volume=Decimal("0"),
        unknown_volume=Decimal("1"),
        source="classified_ticks",
        is_complete=False,
    )


class RecordingCoordinator:
    def __init__(self) -> None:
        self.batches: list[list[object]] = []

    def persist_closed_batch(self, events: list[object]) -> PersistenceWriteResult:
        self.batches.append(events)
        return PersistenceWriteResult(
            batch=None,
            persisted_count=len(events),
            duplicate_count=0,
        )


class BlockingCoordinator(RecordingCoordinator):
    def __init__(self, *, fail: bool = False) -> None:
        super().__init__()
        self.entered = Event()
        self.release = Event()
        self.fail = fail

    def persist_closed_batch(self, events: list[object]) -> PersistenceWriteResult:
        self.entered.set()
        self.release.wait(2)
        if self.fail:
            raise RuntimeError("disk unavailable")
        return super().persist_closed_batch(events)


def catalog(tmp_path: Path, config: PersistenceConfig) -> NautilusParquetTimeSeriesStore:
    return NautilusParquetTimeSeriesStore(config)


def wait_for_status(
    writer: BoundedPersistenceWriter,
    status: PersistenceWriterStatus,
) -> None:
    deadline = time.monotonic() + 2
    while writer.snapshot.status != status:
        if time.monotonic() >= deadline:
            raise AssertionError(f"writer did not reach {status}: {writer.snapshot}")
        time.sleep(0.005)


def test_force_flush_sorts_bucket_and_splits_stable_chunks(tmp_path: Path) -> None:
    config = PersistenceConfig(
        catalog_path=tmp_path / "catalog",
        metadata_path=tmp_path / "metadata.sqlite3",
        journal_path=tmp_path / "journal",
        catalog_batch_size=2,
    )
    coordinator = RecordingCoordinator()
    writer = BoundedPersistenceWriter(
        config,
        coordinator,
        catalog(tmp_path, config),
        clock=lambda: datetime(2026, 8, 10, tzinfo=UTC),
    )
    writer.start()

    for offset in (300, 100, 200):
        assert writer.submit(trade_tick(offset)) == PersistenceSubmissionStatus.ACCEPTED

    assert writer.flush(timeout=2)
    assert writer.stop(timeout=2)
    assert [[str(event.trade_id) for event in batch] for batch in coordinator.batches] == [
        ["trade-100", "trade-200"],
        ["trade-300"],
    ]
    assert writer.snapshot.persisted_count == 3
    assert writer.snapshot.pending_count == 0
    assert writer.snapshot.status == PersistenceWriterStatus.STOPPED


def test_post_commit_sink_only_receives_successfully_committed_chunks(tmp_path: Path) -> None:
    config = PersistenceConfig(
        catalog_path=tmp_path / "catalog",
        metadata_path=tmp_path / "metadata.sqlite3",
        journal_path=tmp_path / "journal",
        catalog_batch_size=2,
    )
    committed: list[tuple[object, ...]] = []
    coordinator = RecordingCoordinator()
    writer = BoundedPersistenceWriter(
        config,
        coordinator,
        catalog(tmp_path, config),
        clock=lambda: FUTURE,
        post_commit_sink=lambda events: not committed.append(events),
    )
    writer.start()
    first = trade_tick(100)
    second = trade_tick(200)

    assert writer.submit(first) == PersistenceSubmissionStatus.ACCEPTED
    assert writer.submit(second) == PersistenceSubmissionStatus.ACCEPTED
    assert writer.stop(timeout=2)

    assert committed == [(first, second)]


def test_journal_recovery_reoffers_durable_batch_after_post_commit_rejection(
    tmp_path: Path,
) -> None:
    config = PersistenceConfig(
        catalog_path=tmp_path / "catalog",
        metadata_path=tmp_path / "metadata.sqlite3",
        journal_path=tmp_path / "journal",
        catalog_batch_size=10,
    )
    time_series = catalog(tmp_path, config)
    metadata = SQLiteMetadataStore(config)
    coordinator = IdempotentPersistenceCoordinator(config, time_series, metadata)
    rejected = BoundedPersistenceWriter(
        config,
        coordinator,
        time_series,
        clock=lambda: FUTURE,
        post_commit_sink=lambda _events: False,
    )
    completed = provisional_bar().model_copy(
        update={
            "is_complete": True,
            "event_ts_ns": unix_ns_from_utc_datetime(datetime(2026, 8, 10, 11, 9, tzinfo=UTC)),
            "ts_init_ns": unix_ns_from_utc_datetime(datetime(2026, 8, 10, 11, 8, tzinfo=UTC)),
        }
    )
    rejected.start()

    assert rejected.submit(completed) == PersistenceSubmissionStatus.ACCEPTED
    assert not rejected.flush(timeout=2)
    wait_for_status(rejected, PersistenceWriterStatus.FAILED)
    assert rejected.snapshot.last_error == (
        "RuntimeError: persistence post-commit handoff rejected batch"
    )
    assert len(tuple(config.journal_path.glob("*.wal"))) == 1

    recovered: list[tuple[object, ...]] = []
    replacement = BoundedPersistenceWriter(
        config,
        coordinator,
        time_series,
        clock=lambda: FUTURE,
        post_commit_sink=lambda events: not recovered.append(events),
    )
    replacement.start()
    assert replacement.wait_until_ready(timeout=2)
    assert replacement.stop(timeout=2)

    assert recovered == [(completed,)]
    assert replacement.snapshot.recovered_count == 1
    metadata.close()


def test_total_pending_capacity_returns_explicit_backpressure(tmp_path: Path) -> None:
    config = PersistenceConfig(
        catalog_path=tmp_path / "catalog",
        metadata_path=tmp_path / "metadata.sqlite3",
        journal_path=tmp_path / "journal",
        catalog_writer_queue_size=2,
        catalog_batch_size=2,
        catalog_flush_poll_seconds=0.01,
    )
    coordinator = BlockingCoordinator()
    writer = BoundedPersistenceWriter(
        config,
        coordinator,
        catalog(tmp_path, config),
        clock=lambda: FUTURE,
    )
    writer.start()
    assert writer.submit(trade_tick(100)) == PersistenceSubmissionStatus.ACCEPTED
    assert coordinator.entered.wait(2)
    assert writer.submit(trade_tick(200)) == PersistenceSubmissionStatus.ACCEPTED

    assert writer.submit(trade_tick(300)) == PersistenceSubmissionStatus.QUEUE_FULL
    assert writer.snapshot.pending_count == 2
    assert writer.snapshot.rejected_full_count == 1

    coordinator.release.set()
    assert writer.stop(timeout=2)
    assert writer.snapshot.persisted_count == 2


def test_storage_failure_fails_closed_and_preserves_pending_count(tmp_path: Path) -> None:
    config = PersistenceConfig(
        catalog_path=tmp_path / "catalog",
        metadata_path=tmp_path / "metadata.sqlite3",
        journal_path=tmp_path / "journal",
        catalog_flush_poll_seconds=0.01,
    )
    coordinator = BlockingCoordinator(fail=True)
    writer = BoundedPersistenceWriter(
        config,
        coordinator,
        catalog(tmp_path, config),
        clock=lambda: FUTURE,
    )
    writer.start()
    assert writer.submit(trade_tick(100)) == PersistenceSubmissionStatus.ACCEPTED
    assert coordinator.entered.wait(2)
    coordinator.release.set()
    wait_for_status(writer, PersistenceWriterStatus.FAILED)

    snapshot = writer.snapshot
    assert snapshot.pending_count == 1
    assert snapshot.persisted_count == 0
    assert snapshot.last_error == "RuntimeError: disk unavailable"
    assert writer.submit(trade_tick(200)) == PersistenceSubmissionStatus.WRITER_FAILED
    assert not writer.flush(timeout=0.1)


def test_invalid_events_are_rejected_before_queue_capacity(tmp_path: Path) -> None:
    config = PersistenceConfig(
        catalog_path=tmp_path / "catalog",
        metadata_path=tmp_path / "metadata.sqlite3",
        journal_path=tmp_path / "journal",
    )
    writer = BoundedPersistenceWriter(
        config,
        RecordingCoordinator(),
        catalog(tmp_path, config),
    )

    assert writer.submit(object()) == PersistenceSubmissionStatus.UNSUPPORTED
    assert writer.submit(provisional_bar()) == PersistenceSubmissionStatus.PROVISIONAL
    assert writer.snapshot.pending_count == 0
    assert writer.snapshot.rejected_invalid_count == 2


def test_graceful_stop_flushes_through_real_coordinator(tmp_path: Path) -> None:
    config = PersistenceConfig(
        catalog_path=tmp_path / "catalog",
        metadata_path=tmp_path / "metadata.sqlite3",
        journal_path=tmp_path / "journal",
        catalog_batch_size=10,
    )
    time_series = catalog(tmp_path, config)
    metadata = SQLiteMetadataStore(config)
    writer = BoundedPersistenceWriter(
        config,
        IdempotentPersistenceCoordinator(config, time_series, metadata),
        time_series,
        clock=lambda: datetime(2026, 8, 10, tzinfo=UTC),
    )
    writer.start()
    assert writer.submit(trade_tick(100)) == PersistenceSubmissionStatus.ACCEPTED
    assert writer.submit(trade_tick(200)) == PersistenceSubmissionStatus.ACCEPTED

    assert writer.stop(timeout=2)
    assert len(time_series.query_trade_ticks("NQU6.CME")) == 2
    assert writer.snapshot.persisted_count == 2
    assert writer.snapshot.committed_batch_count == 1
    metadata.close()
