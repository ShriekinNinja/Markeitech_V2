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
    NotificationOutboxRecord,
    OutboxStatus,
    PersistenceConfig,
    PersistenceEventKind,
    RecoveryRecord,
    RecoveryStatus,
    SQLiteMetadataStore,
    StreamCheckpoint,
)

NOW = datetime(2026, 7, 12, 10, 0, tzinfo=UTC)
EVENT_NS = 1_783_851_600_123_456_789
RECOVERY_ID = UUID("fd142d63-78de-40e0-b3be-00d98cd6f415")
OUTBOX_ID = UUID("c2d86f72-7e4d-4aec-92f5-d0d44891ced1")


def config(path: Path, **overrides: object) -> PersistenceConfig:
    values: dict[str, object] = {
        "catalog_path": path.parent / "catalog",
        "metadata_path": path,
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
        assert first.schema_version == 1
    with SQLiteMetadataStore(config(path)) as second:
        assert second.schema_version == 1
        row = second._connection.execute(  # noqa: SLF001
            "SELECT version FROM schema_migrations"
        ).fetchall()
        assert [item["version"] for item in row] == [1]


def test_newer_unknown_schema_fails_clearly(tmp_path: Path) -> None:
    path = tmp_path / "future.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA user_version = 99")
    connection.close()

    with pytest.raises(RuntimeError, match="newer than supported"):
        SQLiteMetadataStore(config(path))


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
