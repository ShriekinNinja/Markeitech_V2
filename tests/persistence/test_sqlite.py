from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from markeitech.domain import (
    GapSeverity,
    GapState,
    ReadinessState,
    ReadinessStatus,
)
from markeitech.domain.base import utc_datetime_from_unix_ns
from markeitech.persistence import (
    DataFidelity,
    NotificationOutboxRecord,
    OutboxStatus,
    PersistenceConfig,
    PersistenceEventIdentity,
    PersistenceEventKind,
    RecoveryRecord,
    RecoveryStatus,
    RetentionReport,
    RetentionStatus,
    SQLiteCompactionStatus,
    SQLiteMetadataStore,
    StreamCheckpoint,
)
from markeitech.persistence.sqlite import MIGRATIONS

NOW = datetime(2026, 7, 12, 10, 0, tzinfo=UTC)
EVENT_NS = 1_783_851_600_123_456_789
RECOVERY_ID = UUID("fd142d63-78de-40e0-b3be-00d98cd6f415")
OUTBOX_ID = UUID("c2d86f72-7e4d-4aec-92f5-d0d44891ced1")


def config(path: Path, **overrides: object) -> PersistenceConfig:
    values: dict[str, object] = {
        "catalog_path": path.parent / "catalog",
        "metadata_path": path,
        "journal_path": path.parent / "journal",
        "outbox_lease_seconds": 30,
    }
    values.update(overrides)
    return PersistenceConfig(**values)


def checkpoint() -> StreamCheckpoint:
    return StreamCheckpoint(
        instrument_id="NQU6.CME",
        event_kind=PersistenceEventKind.TRADE_TICK,
        source="ib",
        last_event_ts=utc_datetime_from_unix_ns(EVENT_NS),
        last_event_ts_ns=EVENT_NS,
        last_dedupe_key="trade:key",
        committed_ts=NOW,
    )


def recovery(status: RecoveryStatus = RecoveryStatus.RECOVERING) -> RecoveryRecord:
    terminal = status in {
        RecoveryStatus.COMPLETE,
        RecoveryStatus.DEGRADED,
        RecoveryStatus.FAILED,
    }
    return RecoveryRecord(
        recovery_id=RECOVERY_ID,
        instrument_id="ESU6.CME",
        event_kind=PersistenceEventKind.ONE_MINUTE_BAR,
        source="ib",
        status=status,
        requested_start_ts=NOW - timedelta(hours=2),
        requested_end_ts=NOW - timedelta(hours=1),
        missing_intervals=0 if status == RecoveryStatus.COMPLETE else 2,
        reason_codes=(
            ("missing_bars",) if status in {RecoveryStatus.DEGRADED, RecoveryStatus.FAILED} else ()
        ),
        started_ts=NOW,
        updated_ts=NOW + timedelta(seconds=1),
        completed_ts=NOW + timedelta(seconds=1) if terminal else None,
    )


def outbox(
    outbox_id: UUID = OUTBOX_ID, *, dedupe_key: str = "signal:NQ:1"
) -> NotificationOutboxRecord:
    return NotificationOutboxRecord(
        outbox_id=outbox_id,
        topic="signals.high",
        destination_key="discord.signals.high",
        aggregate_key="signal:NQ:1",
        event_type="signal.upsert",
        event_schema_version="1.0",
        payload={"instrument_id": "NQU6.CME", "strength": 85},
        dedupe_key=dedupe_key,
        available_ts=NOW,
        created_ts=NOW,
        updated_ts=NOW,
    )


def test_migrations_are_idempotent_and_auditable(tmp_path: Path) -> None:
    path = tmp_path / "metadata.sqlite3"
    with SQLiteMetadataStore(config(path)) as first:
        assert first.schema_version == 7
    with SQLiteMetadataStore(config(path)) as second:
        assert second.schema_version == 7
        row = second._connection.execute(  # noqa: SLF001
            "SELECT version FROM schema_migrations"
        ).fetchall()
        assert [item["version"] for item in row] == [1, 2, 3, 4, 5, 6, 7]


def test_newer_unknown_schema_fails_clearly(tmp_path: Path) -> None:
    path = tmp_path / "future.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA user_version = 99")
    connection.close()

    with pytest.raises(RuntimeError, match="newer than supported"):
        SQLiteMetadataStore(config(path))


def test_schema_one_upgrades_without_losing_checkpoint(tmp_path: Path) -> None:
    path = tmp_path / "version-one.sqlite3"
    expected = checkpoint()
    connection = sqlite3.connect(path)
    for statement in MIGRATIONS[0][1].split(";"):
        if statement.strip():
            connection.execute(statement)
    connection.execute(
        "INSERT INTO schema_migrations VALUES (?, ?)",
        (1, EVENT_NS),
    )
    connection.execute(
        "INSERT INTO stream_checkpoints VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            expected.stream_key,
            expected.schema_version,
            expected.instrument_id,
            expected.event_kind.value,
            expected.source,
            expected.last_event_ts_ns,
            expected.last_dedupe_key,
            int(expected.committed_ts.timestamp() * 1_000_000_000),
        ),
    )
    connection.execute("PRAGMA user_version = 1")
    connection.commit()
    connection.close()

    with SQLiteMetadataStore(config(path)) as upgraded:
        assert upgraded.schema_version == 7
        assert upgraded.load_checkpoint(expected.stream_key) == expected


def test_schema_three_compacts_identity_without_losing_dedupe(tmp_path: Path) -> None:
    path = tmp_path / "version-three.sqlite3"
    identity = PersistenceEventIdentity(
        event_kind=PersistenceEventKind.TRADE_TICK,
        instrument_id="NQU6.CME",
        source="ib",
        fidelity=DataFidelity.REPORTED,
        dedupe_key="trade:NQU6.CME:legacy",
        event_ts=utc_datetime_from_unix_ns(EVENT_NS),
        event_ts_ns=EVENT_NS,
        init_ts=utc_datetime_from_unix_ns(EVENT_NS + 100),
        init_ts_ns=EVENT_NS + 100,
    )
    connection = sqlite3.connect(path)
    for version, sql in MIGRATIONS[:3]:
        for statement in sql.split(";"):
            if statement.strip():
                connection.execute(statement)
        connection.execute("INSERT INTO schema_migrations VALUES (?, ?)", (version, EVENT_NS))
    connection.execute(
        "INSERT INTO persistence_batches VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "a" * 64,
            "1.0",
            "NQU6.CME",
            "trade_tick",
            "ib",
            EVENT_NS,
            EVENT_NS + 60_000_000_000,
            1,
            "b" * 64,
            "committed",
            EVENT_NS,
            EVENT_NS,
            EVENT_NS,
            EVENT_NS,
            None,
        ),
    )
    connection.execute(
        "INSERT INTO persisted_event_identities VALUES (?, ?, ?, ?)",
        (identity.dedupe_key, "a" * 64, identity.model_dump_json(), EVENT_NS),
    )
    connection.execute("PRAGMA user_version = 3")
    connection.commit()
    connection.close()

    with SQLiteMetadataStore(config(path)) as upgraded:
        columns = {
            row["name"]
            for row in upgraded._connection.execute(  # noqa: SLF001
                "PRAGMA table_info(persisted_event_identities)"
            )
        }
        restored = upgraded.committed_dedupe_keys((identity,))

    assert restored == frozenset({identity.dedupe_key})
    assert "dedupe_hash" in columns
    assert "identity_hash" in columns
    assert "identity_json" not in columns


def test_retention_report_round_trip_is_immutable_audit_evidence(tmp_path: Path) -> None:
    path = tmp_path / "metadata.sqlite3"
    report = RetentionReport(
        maintenance_ts=NOW,
        status=RetentionStatus.COMPLETED,
        inspected_file_count=12,
        catalog_bytes_before=10_000,
        catalog_bytes_after=8_000,
        deleted_file_count=2,
        deleted_bytes=2_000,
        pruned_identity_count=20,
        pruned_batch_count=2,
        unmanaged_instruments=("OLD.CME",),
        reason_codes=("unmanaged_instruments_retained",),
    )

    with SQLiteMetadataStore(config(path)) as metadata:
        metadata.save_retention_report(report)
        restored = metadata.load_retention_report(report.run_id)
        with pytest.raises(sqlite3.IntegrityError):
            metadata.save_retention_report(report)

    assert restored == report


def test_sqlite_compaction_is_thresholded_and_reports_reclaimed_pages(tmp_path: Path) -> None:
    path = tmp_path / "metadata.sqlite3"
    with SQLiteMetadataStore(config(path)) as metadata:
        skipped = metadata.compact_database(2**63 - 1)
        metadata._connection.execute(  # noqa: SLF001
            "CREATE TABLE compaction_payload (payload BLOB NOT NULL)"
        )
        metadata._connection.executemany(  # noqa: SLF001
            "INSERT INTO compaction_payload VALUES (?)",
            [(b"x" * 4096,)] * 256,
        )
        metadata._connection.execute("DROP TABLE compaction_payload")  # noqa: SLF001
        compacted = metadata.compact_database(0)
        restored_skipped = metadata.load_compaction_report(skipped.run_id)
        restored_compacted = metadata.load_compaction_report(compacted.run_id)

    assert skipped.status == SQLiteCompactionStatus.SKIPPED_THRESHOLD
    assert skipped.reclaimed_bytes == 0
    assert compacted.status == SQLiteCompactionStatus.COMPLETED
    assert compacted.free_page_count_before > 0
    assert compacted.free_page_count_after == 0
    assert compacted.page_count_after < compacted.page_count_before
    assert compacted.reclaimed_bytes > 0
    assert restored_skipped == skipped
    assert restored_compacted == compacted


def test_sqlite_compaction_refuses_pending_ingress_wal(tmp_path: Path) -> None:
    path = tmp_path / "metadata.sqlite3"
    persistence_config = config(
        path,
        journal_path=tmp_path / "journal",
    )
    persistence_config.journal_path.mkdir(parents=True)
    (persistence_config.journal_path / "pending.wal").write_bytes(b"pending")

    with SQLiteMetadataStore(persistence_config) as metadata:
        with pytest.raises(RuntimeError, match="ingress WAL"):
            metadata.compact_database(0)


def test_checkpoint_round_trip_preserves_nanoseconds_and_restart(tmp_path: Path) -> None:
    path = tmp_path / "metadata.sqlite3"
    expected = checkpoint()
    with SQLiteMetadataStore(config(path)) as store:
        store.save_checkpoint(expected)

    with SQLiteMetadataStore(config(path)) as reopened:
        restored = reopened.load_checkpoint(expected.stream_key)

    assert restored == expected
    assert restored is not None
    assert restored.last_event_ts_ns == EVENT_NS


def test_checkpoint_cannot_move_stream_progress_backward(tmp_path: Path) -> None:
    current = checkpoint()
    older_ns = EVENT_NS - 1_000_000_000
    older = current.model_copy(
        update={
            "last_event_ts": utc_datetime_from_unix_ns(older_ns),
            "last_event_ts_ns": older_ns,
            "committed_ts": NOW + timedelta(seconds=1),
        }
    )
    with SQLiteMetadataStore(config(tmp_path / "metadata.sqlite3")) as store:
        store.save_checkpoint(current)
        with pytest.raises(ValueError, match="cannot move stream progress backward"):
            store.save_checkpoint(older)

        assert store.load_checkpoint(current.stream_key) == current


def test_provider_empty_intervals_require_repeated_durable_observations(
    tmp_path: Path,
) -> None:
    path = tmp_path / "metadata.sqlite3"
    open_ts = datetime(2026, 7, 13, 12, 4, tzinfo=UTC)
    with SQLiteMetadataStore(config(path)) as store:
        assert (
            store.record_provider_empty_interval(
                instrument_id="SPY.ARCA",
                source="ib",
                open_ts=open_ts,
                observed_ts=NOW,
            )
            == 1
        )
        assert (
            store.load_confirmed_provider_empty_opens(
                instrument_id="SPY.ARCA",
                source="ib",
                start_ts=open_ts - timedelta(minutes=1),
                end_ts=open_ts + timedelta(minutes=1),
                minimum_attempts=2,
            )
            == ()
        )
        assert (
            store.record_provider_empty_interval(
                instrument_id="SPY.ARCA",
                source="ib",
                open_ts=open_ts,
                observed_ts=NOW + timedelta(seconds=1),
            )
            == 2
        )
        assert store.load_confirmed_provider_empty_opens(
            instrument_id="SPY.ARCA",
            source="ib",
            start_ts=open_ts - timedelta(minutes=1),
            end_ts=open_ts + timedelta(minutes=1),
            minimum_attempts=2,
        ) == (open_ts,)


def test_recovery_lifecycle_round_trip(tmp_path: Path) -> None:
    with SQLiteMetadataStore(config(tmp_path / "metadata.sqlite3")) as store:
        store.save_recovery(recovery())
        completed = recovery(RecoveryStatus.COMPLETE)
        store.save_recovery(completed)

        assert store.load_recovery(RECOVERY_ID) == completed


def test_readiness_and_gap_states_round_trip(tmp_path: Path) -> None:
    readiness = ReadinessState(
        instrument_id="NQU6.CME",
        status=ReadinessStatus.DEGRADED,
        reason_codes=("open_gap",),
        required_sessions=5,
        complete_sessions=4,
        updated_ts=NOW,
    )
    gap = GapState(
        instrument_id="NQU6.CME",
        severity=GapSeverity.DEGRADED,
        open_ts=NOW - timedelta(minutes=2),
        close_ts=NOW,
        missing_intervals=2,
        reason_codes=("missing_1m_bars",),
        updated_ts=NOW,
    )
    with SQLiteMetadataStore(config(tmp_path / "metadata.sqlite3")) as store:
        store.save_readiness(readiness)
        store.save_gap(gap)

        assert store.load_readiness("NQU6.CME") == readiness
        assert store.load_gap("NQU6.CME") == gap


def test_duplicate_outbox_enqueue_is_ignored_by_dedupe_key(tmp_path: Path) -> None:
    with SQLiteMetadataStore(config(tmp_path / "metadata.sqlite3")) as store:
        assert store.enqueue(outbox()) is True
        duplicate = outbox(
            UUID("5801b17f-aa07-4dac-972f-f8fe66fd70d4"),
            dedupe_key="signal:NQ:1",
        )
        assert store.enqueue(duplicate) is False
        assert store.load_outbox(OUTBOX_ID) == outbox()


def test_two_connections_cannot_lease_same_outbox_record(tmp_path: Path) -> None:
    path = tmp_path / "metadata.sqlite3"
    with SQLiteMetadataStore(config(path)) as setup:
        setup.enqueue(outbox())

    first = SQLiteMetadataStore(config(path))
    second = SQLiteMetadataStore(config(path))
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            one = executor.submit(first.lease_pending, lease_owner="worker-1", now=NOW, limit=1)
            two = executor.submit(second.lease_pending, lease_owner="worker-2", now=NOW, limit=1)
            claims = [*one.result(), *two.result()]
    finally:
        first.close()
        second.close()

    assert len(claims) == 1
    assert claims[0].lease_owner in {"worker-1", "worker-2"}
    assert claims[0].attempt_count == 1


def test_expired_lease_becomes_claimable(tmp_path: Path) -> None:
    with SQLiteMetadataStore(config(tmp_path / "metadata.sqlite3")) as store:
        store.enqueue(outbox())
        first = store.lease_pending(lease_owner="worker-1", now=NOW, limit=1)[0]
        second = store.lease_pending(
            lease_owner="worker-2",
            now=NOW + timedelta(seconds=31),
            limit=1,
        )[0]

    assert first.lease_owner == "worker-1"
    assert second.lease_owner == "worker-2"
    assert second.attempt_count == 2


def test_only_active_lease_owner_can_complete_or_fail(tmp_path: Path) -> None:
    with SQLiteMetadataStore(config(tmp_path / "metadata.sqlite3")) as store:
        store.enqueue(outbox())
        store.lease_pending(lease_owner="worker-1", now=NOW, limit=1)

        with pytest.raises(RuntimeError, match="active lease owner"):
            store.mark_delivered(
                outbox_id=OUTBOX_ID,
                lease_owner="worker-2",
                delivered_ts=NOW + timedelta(seconds=1),
            )

        failed = store.mark_failed(
            outbox_id=OUTBOX_ID,
            lease_owner="worker-1",
            failed_ts=NOW + timedelta(seconds=1),
            retry_ts=NOW + timedelta(seconds=10),
            error="rate limited",
        )
        assert failed.status == OutboxStatus.FAILED
        assert failed.last_error == "rate limited"

        leased = store.lease_pending(
            lease_owner="worker-2",
            now=NOW + timedelta(seconds=10),
            limit=1,
        )[0]
        delivered = store.mark_delivered(
            outbox_id=OUTBOX_ID,
            lease_owner="worker-2",
            delivered_ts=NOW + timedelta(seconds=11),
        )

    assert leased.attempt_count == 2
    assert delivered.status == OutboxStatus.DELIVERED
    assert delivered.delivered_ts == NOW + timedelta(seconds=11)


def test_transaction_rolls_back_all_changes_on_failure(tmp_path: Path) -> None:
    with SQLiteMetadataStore(config(tmp_path / "metadata.sqlite3")) as store:
        with pytest.raises(RuntimeError, match="abort transaction"):
            with store._transaction() as connection:  # noqa: SLF001
                connection.execute(
                    "INSERT INTO readiness_states VALUES (?, ?, ?)",
                    ("NQU6.CME", "{}", 1),
                )
                raise RuntimeError("abort transaction")

        row = store._connection.execute(  # noqa: SLF001
            "SELECT COUNT(*) FROM readiness_states"
        ).fetchone()
        assert row[0] == 0
