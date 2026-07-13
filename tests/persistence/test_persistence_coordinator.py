from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from markeitech.persistence import (
    IdempotentPersistenceCoordinator,
    NautilusParquetTimeSeriesStore,
    PersistenceBatchStatus,
    PersistenceConfig,
    PersistenceEventKind,
    PersistenceFailurePoint,
    SQLiteMetadataStore,
)
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.enums import AggressorSide
from nautilus_trader.model.identifiers import InstrumentId, TradeId
from nautilus_trader.model.objects import Price, Quantity

BASE_NS = 1_786_360_120_000_000_000
NOW = datetime(2026, 8, 10, 11, 10, tzinfo=UTC)


def trade_tick(
    offset_ns: int,
    *,
    instrument_id: str = "NQU6.CME",
    init_offset_ns: int | None = None,
) -> TradeTick:
    event_ns = BASE_NS + offset_ns
    init_ns = BASE_NS + (init_offset_ns if init_offset_ns is not None else offset_ns + 100)
    return TradeTick(
        instrument_id=InstrumentId.from_str(instrument_id),
        price=Price.from_str("20000.25"),
        size=Quantity.from_str("1.5"),
        aggressor_side=AggressorSide.BUYER,
        trade_id=TradeId(f"trade-{offset_ns}"),
        ts_event=event_ns,
        ts_init=init_ns,
    )


class CrashOnce:
    def __init__(self, point: PersistenceFailurePoint) -> None:
        self.point = point
        self.crashed = False

    def __call__(self, point: PersistenceFailurePoint) -> None:
        if point == self.point and not self.crashed:
            self.crashed = True
            raise RuntimeError(f"crash at {point}")


@pytest.fixture
def persistence(
    tmp_path: Path,
) -> tuple[PersistenceConfig, NautilusParquetTimeSeriesStore, SQLiteMetadataStore]:
    config = PersistenceConfig(
        catalog_path=tmp_path / "catalog",
        metadata_path=tmp_path / "metadata.sqlite3",
        catalog_batch_size=100,
        persistence_batch_interval_seconds=60,
    )
    metadata = SQLiteMetadataStore(config)
    yield config, NautilusParquetTimeSeriesStore(config), metadata
    metadata.close()


def coordinator(
    persistence: tuple[PersistenceConfig, NautilusParquetTimeSeriesStore, SQLiteMetadataStore],
    *,
    crash: CrashOnce | None = None,
) -> IdempotentPersistenceCoordinator:
    config, catalog, metadata = persistence
    times = iter(NOW + timedelta(microseconds=index) for index in range(100))
    return IdempotentPersistenceCoordinator(
        config,
        catalog,
        metadata,
        clock=lambda: next(times),
        failure_injector=crash,
    )


class FailingCatalogBackend:
    def write_data(self, data: list[object]) -> None:
        raise RuntimeError("catalog unavailable")

    def query(self, data_cls: type, identifiers: list[str] | None = None) -> list[object]:
        return []


def test_batch_commit_advances_checkpoint_after_catalog(
    persistence: tuple[PersistenceConfig, NautilusParquetTimeSeriesStore, SQLiteMetadataStore],
) -> None:
    _, catalog, metadata = persistence
    events = [trade_tick(1_000), trade_tick(2_000)]

    result = coordinator(persistence).persist_closed_batch(events)

    assert result.batch is not None
    assert result.batch.status == PersistenceBatchStatus.COMMITTED
    assert result.persisted_count == 2
    assert result.duplicate_count == 0
    assert len(catalog.query_trade_ticks("NQU6.CME")) == 2
    checkpoint = metadata.load_checkpoint("ib:NQU6.CME:trade_tick")
    assert checkpoint is not None
    assert checkpoint.last_event_ts_ns == events[-1].ts_event


def test_exact_retry_is_a_noop(
    persistence: tuple[PersistenceConfig, NautilusParquetTimeSeriesStore, SQLiteMetadataStore],
) -> None:
    _, catalog, _ = persistence
    events = [trade_tick(1_000), trade_tick(2_000)]
    coordinator(persistence).persist_closed_batch(events)

    retried = coordinator(persistence).persist_closed_batch(list(reversed(events)))

    assert retried.persisted_count == 0
    assert retried.duplicate_count == 2
    assert len(catalog.query_trade_ticks("NQU6.CME")) == 2


def test_metadata_pruning_removes_only_expired_identities_and_empty_batches(
    persistence: tuple[PersistenceConfig, NautilusParquetTimeSeriesStore, SQLiteMetadataStore],
) -> None:
    _, catalog, metadata = persistence
    old = trade_tick(1_000)
    retained = trade_tick(2_000)
    old_result = coordinator(persistence).persist_closed_batch([old])
    retained_result = coordinator(persistence).persist_closed_batch([retained])

    identity_count, batch_count = metadata.prune_committed_history(
        {
            (PersistenceEventKind.TRADE_TICK, "NQU6.CME", "ib"): BASE_NS + 1_500,
        }
    )

    assert identity_count == 1
    assert batch_count == 1
    assert old_result.batch is not None
    assert retained_result.batch is not None
    assert metadata.load_batch(old_result.batch.batch_id) is None
    assert metadata.load_batch(retained_result.batch.batch_id) is not None
    identities = catalog.identify((old, retained))
    assert metadata.committed_dedupe_keys(identities) == frozenset({identities[1].dedupe_key})


def test_metadata_pruning_refuses_incomplete_batches(
    persistence: tuple[PersistenceConfig, NautilusParquetTimeSeriesStore, SQLiteMetadataStore],
) -> None:
    _, _, metadata = persistence
    crashing = coordinator(
        persistence,
        crash=CrashOnce(PersistenceFailurePoint.AFTER_PREPARE),
    )
    with pytest.raises(RuntimeError, match="crash at after_prepare"):
        crashing.persist_closed_batch([trade_tick(1_000)])

    with pytest.raises(RuntimeError, match="batches are incomplete"):
        metadata.prune_committed_history(
            {
                (PersistenceEventKind.TRADE_TICK, "NQU6.CME", "ib"): BASE_NS + 2_000,
            }
        )
    with pytest.raises(RuntimeError, match="batches are incomplete"):
        metadata.compact_database(0)


def test_historical_live_overlap_writes_only_new_tail(
    persistence: tuple[PersistenceConfig, NautilusParquetTimeSeriesStore, SQLiteMetadataStore],
) -> None:
    _, catalog, _ = persistence
    first = trade_tick(1_000)
    overlap = trade_tick(2_000)
    last = trade_tick(3_000)
    coordinator(persistence).persist_closed_batch([first, overlap])

    result = coordinator(persistence).persist_closed_batch([overlap, last])

    assert result.persisted_count == 1
    assert result.duplicate_count == 1
    assert len(catalog.query_trade_ticks("NQU6.CME")) == 3


@pytest.mark.parametrize(
    "point,expected_status",
    [
        (PersistenceFailurePoint.AFTER_PREPARE, PersistenceBatchStatus.PREPARED),
        (PersistenceFailurePoint.AFTER_CATALOG_WRITE, PersistenceBatchStatus.PREPARED),
        (
            PersistenceFailurePoint.AFTER_CATALOG_ACK,
            PersistenceBatchStatus.CATALOG_WRITTEN,
        ),
        (PersistenceFailurePoint.AFTER_COMMIT, PersistenceBatchStatus.COMMITTED),
    ],
)
def test_restart_recovers_every_crash_window(
    persistence: tuple[PersistenceConfig, NautilusParquetTimeSeriesStore, SQLiteMetadataStore],
    point: PersistenceFailurePoint,
    expected_status: PersistenceBatchStatus,
) -> None:
    _, catalog, metadata = persistence
    events = [trade_tick(1_000), trade_tick(2_000)]
    crashing = CrashOnce(point)

    with pytest.raises(RuntimeError, match="crash at"):
        coordinator(persistence, crash=crashing).persist_closed_batch(events)

    batches = metadata.incomplete_batches()
    if expected_status == PersistenceBatchStatus.COMMITTED:
        assert batches == ()
    else:
        assert len(batches) == 1
        assert batches[0].status == expected_status

    result = coordinator(persistence).persist_closed_batch(events)

    assert len(catalog.query_trade_ticks("NQU6.CME")) == 2
    checkpoint = metadata.load_checkpoint("ib:NQU6.CME:trade_tick")
    assert checkpoint is not None
    if expected_status == PersistenceBatchStatus.COMMITTED:
        assert result.persisted_count == 0
        assert result.duplicate_count == 2
    else:
        assert result.batch is not None
        assert result.batch.status == PersistenceBatchStatus.COMMITTED


def test_retransmitted_event_with_later_receipt_time_is_duplicate(
    persistence: tuple[PersistenceConfig, NautilusParquetTimeSeriesStore, SQLiteMetadataStore],
) -> None:
    original = trade_tick(1_000, init_offset_ns=1_100)
    retransmission = trade_tick(1_000, init_offset_ns=1_200)
    coordinator(persistence).persist_closed_batch([original])

    result = coordinator(persistence).persist_closed_batch([retransmission])

    assert result.persisted_count == 0
    assert result.duplicate_count == 1
    assert len(persistence[1].query_trade_ticks("NQU6.CME")) == 1


def test_same_batch_retransmission_keeps_earliest_receipt(
    persistence: tuple[PersistenceConfig, NautilusParquetTimeSeriesStore, SQLiteMetadataStore],
) -> None:
    later = trade_tick(1_000, init_offset_ns=1_200)
    earlier = trade_tick(1_000, init_offset_ns=1_100)

    result = coordinator(persistence).persist_closed_batch([later, earlier])

    assert result.persisted_count == 1
    assert result.duplicate_count == 1
    stored = persistence[1].query_trade_ticks("NQU6.CME")
    assert len(stored) == 1
    assert stored[0].ts_init == earlier.ts_init


def test_same_dedupe_key_with_different_logical_identity_fails(
    persistence: tuple[PersistenceConfig, NautilusParquetTimeSeriesStore, SQLiteMetadataStore],
) -> None:
    event = trade_tick(1_000)
    coordinator(persistence).persist_closed_batch([event])
    identity = persistence[1].identify([event])[0]
    conflict = identity.model_copy(
        update={
            "event_ts": identity.event_ts + timedelta(microseconds=1),
            "event_ts_ns": identity.event_ts_ns + 1_000,
        }
    )

    with pytest.raises(ValueError, match="conflicts with a different event identity"):
        persistence[2].committed_dedupe_keys((conflict,))


def test_mixed_stream_and_bucket_batches_are_rejected(
    persistence: tuple[PersistenceConfig, NautilusParquetTimeSeriesStore, SQLiteMetadataStore],
) -> None:
    with pytest.raises(ValueError, match="exactly one stream"):
        coordinator(persistence).persist_closed_batch(
            [trade_tick(1_000), trade_tick(2_000, instrument_id="ESU6.CME")]
        )

    with pytest.raises(ValueError, match="one fixed initialization-time bucket"):
        coordinator(persistence).persist_closed_batch(
            [trade_tick(1_000), trade_tick(61_000_000_000)]
        )


def test_stream_failure_does_not_advance_another_stream(
    persistence: tuple[PersistenceConfig, NautilusParquetTimeSeriesStore, SQLiteMetadataStore],
) -> None:
    _, _, metadata = persistence
    coordinator(persistence).persist_closed_batch([trade_tick(1_000, instrument_id="NQU6.CME")])
    crash = CrashOnce(PersistenceFailurePoint.AFTER_PREPARE)

    with pytest.raises(RuntimeError, match="crash at"):
        coordinator(persistence, crash=crash).persist_closed_batch(
            [trade_tick(2_000, instrument_id="ESU6.CME")]
        )

    assert metadata.load_checkpoint("ib:NQU6.CME:trade_tick") is not None
    assert metadata.load_checkpoint("ib:ESU6.CME:trade_tick") is None


def test_catalog_failure_leaves_prepared_batch_without_checkpoint(tmp_path: Path) -> None:
    config = PersistenceConfig(
        catalog_path=tmp_path / "catalog",
        metadata_path=tmp_path / "metadata.sqlite3",
    )
    metadata = SQLiteMetadataStore(config)
    catalog = NautilusParquetTimeSeriesStore(config, catalog=FailingCatalogBackend())
    coordinator_under_test = IdempotentPersistenceCoordinator(
        config,
        catalog,
        metadata,
        clock=lambda: NOW,
    )
    try:
        with pytest.raises(RuntimeError, match="catalog unavailable"):
            coordinator_under_test.persist_closed_batch([trade_tick(1_000)])

        assert len(metadata.incomplete_batches()) == 1
        assert metadata.incomplete_batches()[0].status == PersistenceBatchStatus.PREPARED
        assert metadata.load_checkpoint("ib:NQU6.CME:trade_tick") is None
    finally:
        metadata.close()


def test_delayed_event_commits_without_moving_checkpoint_backward(
    persistence: tuple[PersistenceConfig, NautilusParquetTimeSeriesStore, SQLiteMetadataStore],
) -> None:
    _, catalog, metadata = persistence
    current = trade_tick(2_000, init_offset_ns=2_100)
    delayed = trade_tick(1_000, init_offset_ns=3_000)
    coordinator(persistence).persist_closed_batch([current])
    checkpoint_before = metadata.load_checkpoint("ib:NQU6.CME:trade_tick")

    result = coordinator(persistence).persist_closed_batch([delayed])
    checkpoint_after = metadata.load_checkpoint("ib:NQU6.CME:trade_tick")

    assert result.persisted_count == 1
    assert result.batch is not None
    assert result.batch.status == PersistenceBatchStatus.COMMITTED
    assert len(catalog.query_trade_ticks("NQU6.CME")) == 2
    assert checkpoint_after == checkpoint_before
