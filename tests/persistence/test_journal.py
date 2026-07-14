from __future__ import annotations

import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from markeitech.domain import OneMinuteBar
from markeitech.persistence import (
    BoundedPersistenceWriter,
    IdempotentPersistenceCoordinator,
    NautilusParquetTimeSeriesStore,
    PersistenceConfig,
    PersistenceFailurePoint,
    PersistenceSubmissionStatus,
    PersistenceWriterStatus,
    SQLiteMetadataStore,
)
from markeitech.persistence.journal import (
    DurableIngressJournal,
    JournalCapacityError,
    JournalCorruptionError,
)
from nautilus_trader.model.data import QuoteTick, TradeTick
from nautilus_trader.model.enums import AggressorSide
from nautilus_trader.model.identifiers import InstrumentId, TradeId
from nautilus_trader.model.objects import Price, Quantity

BASE_NS = 1_786_360_120_000_000_000


def config(tmp_path: Path, **updates: object) -> PersistenceConfig:
    values = {
        "catalog_path": tmp_path / "catalog",
        "metadata_path": tmp_path / "metadata.sqlite3",
        "journal_path": tmp_path / "journal",
        "catalog_batch_size": 10,
        **updates,
    }
    return PersistenceConfig(**values)


def trade_tick(offset_ns: int = 100, *, init_offset_ns: int | None = None) -> TradeTick:
    return TradeTick(
        instrument_id=InstrumentId.from_str("NQU6.CME"),
        price=Price.from_str("20000.25"),
        size=Quantity.from_str("1.5"),
        aggressor_side=AggressorSide.BUYER,
        trade_id=TradeId(f"trade-{offset_ns}"),
        ts_event=BASE_NS + offset_ns,
        ts_init=BASE_NS + (init_offset_ns if init_offset_ns is not None else offset_ns + 100),
    )


def quote_tick() -> QuoteTick:
    return QuoteTick(
        instrument_id=InstrumentId.from_str("NQU6.CME"),
        bid_price=Price.from_str("20000.00"),
        ask_price=Price.from_str("20000.50"),
        bid_size=Quantity.from_str("2.25"),
        ask_size=Quantity.from_str("3.75"),
        ts_event=BASE_NS + 200,
        ts_init=BASE_NS + 300,
    )


def bar() -> OneMinuteBar:
    return OneMinuteBar(
        instrument_id="NQU6.CME",
        event_ts=datetime(2026, 8, 10, 11, 9, tzinfo=UTC),
        ts_init=datetime(2026, 8, 10, 11, 9, 0, 123456, tzinfo=UTC),
        event_ts_ns=1_786_360_140_000_000_000,
        ts_init_ns=1_786_360_140_123_456_789,
        open_ts=datetime(2026, 8, 10, 11, 8, tzinfo=UTC),
        close_ts=datetime(2026, 8, 10, 11, 9, tzinfo=UTC),
        open=Decimal("20000.125"),
        high=Decimal("20002.875"),
        low=Decimal("19999.625"),
        close=Decimal("20001.375"),
        volume=Decimal("12.5"),
        buy_volume=Decimal("7.25"),
        sell_volume=Decimal("4.25"),
        unknown_volume=Decimal("1"),
        source="classified_ticks",
    )


def append_events(
    journal: DurableIngressJournal,
    catalog: NautilusParquetTimeSeriesStore,
    events: list[object],
) -> tuple[Path, ...]:
    identities = catalog.identify(events)
    return tuple(
        entry.path for entry in journal.append(tuple(zip(events, identities, strict=True)))
    )


def wait_for_writer(writer: BoundedPersistenceWriter, status: PersistenceWriterStatus) -> None:
    deadline = time.monotonic() + 2
    while writer.snapshot.status != status:
        if time.monotonic() >= deadline:
            raise AssertionError(f"writer did not reach {status}: {writer.snapshot}")
        time.sleep(0.005)


def test_journal_round_trip_preserves_native_ticks_and_canonical_bar(tmp_path: Path) -> None:
    persistence_config = config(tmp_path)
    catalog = NautilusParquetTimeSeriesStore(persistence_config)
    journal = DurableIngressJournal(persistence_config)
    events = [trade_tick(), quote_tick(), bar()]

    paths = append_events(journal, catalog, events)
    recovered = tuple(entry.event for entry in journal.recover())
    recovered_by_type = {type(event): event for event in recovered}

    assert len(recovered) == 3
    assert recovered_by_type[TradeTick] == events[0]
    assert recovered_by_type[QuoteTick] == events[1]
    assert recovered_by_type[OneMinuteBar] == events[2]
    assert recovered_by_type[TradeTick].ts_event == BASE_NS + 100
    assert recovered_by_type[QuoteTick].bid_size.as_decimal() == Decimal("2.25")
    assert recovered_by_type[OneMinuteBar].ts_init_ns == 1_786_360_140_123_456_789
    assert journal.total_bytes > 0

    for path in set(paths):
        journal.acknowledge(path)
    assert journal.total_bytes == 0


def test_recovery_repairs_only_a_torn_final_record(tmp_path: Path) -> None:
    persistence_config = config(tmp_path)
    catalog = NautilusParquetTimeSeriesStore(persistence_config)
    journal = DurableIngressJournal(persistence_config)
    path = append_events(journal, catalog, [trade_tick()])[0]
    valid_size = path.stat().st_size
    with path.open("ab") as stream:
        stream.write(b"\x00\x00")

    recovered = journal.recover()

    assert tuple(entry.event for entry in recovered) == (trade_tick(),)
    assert path.stat().st_size == valid_size


def test_checksum_corruption_fails_closed(tmp_path: Path) -> None:
    persistence_config = config(tmp_path)
    catalog = NautilusParquetTimeSeriesStore(persistence_config)
    journal = DurableIngressJournal(persistence_config)
    path = append_events(journal, catalog, [trade_tick()])[0]
    with path.open("r+b") as stream:
        stream.seek(-1, 2)
        byte = stream.read(1)
        stream.seek(-1, 2)
        stream.write(bytes([byte[0] ^ 0xFF]))

    with pytest.raises(JournalCorruptionError, match="checksum mismatch"):
        journal.recover()


def test_torn_initial_header_is_removed(tmp_path: Path) -> None:
    persistence_config = config(tmp_path)
    journal = DurableIngressJournal(persistence_config)
    path = persistence_config.journal_path / "partial.wal"
    path.write_bytes(b"MKW")

    assert journal.recover() == ()
    assert not path.exists()
    assert journal.total_bytes == 0


def test_header_only_file_is_removed(tmp_path: Path) -> None:
    persistence_config = config(tmp_path)
    journal = DurableIngressJournal(persistence_config)
    path = persistence_config.journal_path / "header-only.wal"
    path.write_bytes(b"MKWAL1\n")

    assert journal.recover() == ()
    assert not path.exists()
    assert journal.total_bytes == 0


def test_writer_start_reports_corrupt_journal_as_failed(tmp_path: Path) -> None:
    persistence_config = config(tmp_path)
    catalog = NautilusParquetTimeSeriesStore(persistence_config)
    journal = DurableIngressJournal(persistence_config)
    path = append_events(journal, catalog, [trade_tick()])[0]
    with path.open("r+b") as stream:
        stream.seek(-1, 2)
        byte = stream.read(1)
        stream.seek(-1, 2)
        stream.write(bytes([byte[0] ^ 0xFF]))
    metadata = SQLiteMetadataStore(persistence_config)
    writer = BoundedPersistenceWriter(
        persistence_config,
        IdempotentPersistenceCoordinator(persistence_config, catalog, metadata),
        catalog,
        journal=journal,
    )

    with pytest.raises(JournalCorruptionError, match="checksum mismatch"):
        writer.start()

    assert writer.snapshot.status == PersistenceWriterStatus.FAILED
    assert "JournalCorruptionError" in (writer.snapshot.last_error or "")
    metadata.close()


def test_journal_capacity_fails_before_creating_a_record(tmp_path: Path) -> None:
    persistence_config = config(tmp_path, journal_max_bytes=16)
    catalog = NautilusParquetTimeSeriesStore(persistence_config)
    journal = DurableIngressJournal(persistence_config)

    with pytest.raises(JournalCapacityError, match="capacity exhausted"):
        append_events(journal, catalog, [trade_tick()])

    assert journal.total_bytes == 0
    assert list(persistence_config.journal_path.glob("*.wal")) == []


def test_writer_never_splits_a_shared_receipt_timestamp_across_catalog_chunks(
    tmp_path: Path,
) -> None:
    persistence_config = config(tmp_path, catalog_batch_size=2)
    catalog = NautilusParquetTimeSeriesStore(persistence_config)
    metadata = SQLiteMetadataStore(persistence_config)
    writer = BoundedPersistenceWriter(
        persistence_config,
        IdempotentPersistenceCoordinator(persistence_config, catalog, metadata),
        catalog,
    )
    events = (
        trade_tick(100, init_offset_ns=200),
        trade_tick(200, init_offset_ns=300),
        trade_tick(201, init_offset_ns=300),
    )

    writer.start()
    for event in events:
        assert writer.submit(event) == PersistenceSubmissionStatus.ACCEPTED
    assert writer.stop(timeout=2)

    assert writer.snapshot.status == PersistenceWriterStatus.STOPPED, writer.snapshot
    assert writer.snapshot.persisted_count == 3
    assert len(catalog.query_trade_ticks("NQU6.CME")) == 3
    metadata.close()


@pytest.mark.parametrize(
    "failure_point",
    [
        PersistenceFailurePoint.AFTER_PREPARE,
        PersistenceFailurePoint.AFTER_CATALOG_WRITE,
        PersistenceFailurePoint.AFTER_CATALOG_ACK,
        PersistenceFailurePoint.AFTER_COMMIT,
    ],
)
def test_restart_replays_every_coordinator_crash_boundary_from_durable_wal(
    tmp_path: Path,
    failure_point: PersistenceFailurePoint,
) -> None:
    persistence_config = config(tmp_path)
    catalog = NautilusParquetTimeSeriesStore(persistence_config)
    metadata = SQLiteMetadataStore(persistence_config)

    def crash_once(point: PersistenceFailurePoint) -> None:
        if point == failure_point:
            raise RuntimeError("simulated process crash")

    first = BoundedPersistenceWriter(
        persistence_config,
        IdempotentPersistenceCoordinator(
            persistence_config,
            catalog,
            metadata,
            failure_injector=crash_once,
        ),
        catalog,
        clock=lambda: datetime(2026, 8, 10, tzinfo=UTC),
    )
    first.start()
    assert first.submit(trade_tick(100)) == PersistenceSubmissionStatus.ACCEPTED
    assert first.submit(trade_tick(200)) == PersistenceSubmissionStatus.ACCEPTED
    assert first.stop(timeout=2)
    assert first.snapshot.status == PersistenceWriterStatus.FAILED
    assert first.snapshot.journal_bytes > 0
    expected_before_recovery = 0 if failure_point == PersistenceFailurePoint.AFTER_PREPARE else 2
    assert len(catalog.query_trade_ticks("NQU6.CME")) == expected_before_recovery
    metadata.close()

    recovered_metadata = SQLiteMetadataStore(persistence_config)
    recovered = BoundedPersistenceWriter(
        persistence_config,
        IdempotentPersistenceCoordinator(
            persistence_config,
            catalog,
            recovered_metadata,
        ),
        catalog,
    )
    recovered.start()
    wait_for_writer(recovered, PersistenceWriterStatus.RUNNING)

    assert recovered.snapshot.recovered_count == 2
    assert recovered.snapshot.pending_count == 0
    assert recovered.snapshot.journal_bytes == 0
    assert len(catalog.query_trade_ticks("NQU6.CME")) == 2
    assert recovered.stop(timeout=2)
    recovered_metadata.close()
