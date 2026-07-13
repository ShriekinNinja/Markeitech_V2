from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest
from markeitech.persistence import (
    DataFidelity,
    NotificationOutboxRecord,
    OutboxStatus,
    PersistenceConfig,
    PersistenceEventIdentity,
    PersistenceEventKind,
    RecoveryRecord,
    RecoveryStatus,
    StreamCheckpoint,
)
from pydantic import ValidationError

NOW = datetime(2026, 7, 12, 8, 0, tzinfo=UTC)
OUTBOX_ID = UUID("4f2e28ab-4d46-467b-a311-e3e90c29a57b")
RECOVERY_ID = UUID("d8743161-6490-44f9-9ffc-1cd04e0e466c")


def test_reported_event_identity_rejects_derivation_method() -> None:
    with pytest.raises(ValidationError, match="reported data cannot define"):
        PersistenceEventIdentity(
            event_kind=PersistenceEventKind.TRADE_TICK,
            instrument_id="NQU6.CME",
            source="ib",
            fidelity=DataFidelity.REPORTED,
            dedupe_key="trade:key",
            event_ts=NOW,
            init_ts=NOW,
            derivation_method="quote_test",
        )


def test_inferred_event_identity_requires_derivation_method() -> None:
    with pytest.raises(ValidationError, match="requires a derivation method"):
        PersistenceEventIdentity(
            event_kind=PersistenceEventKind.ONE_MINUTE_BAR,
            instrument_id="NQU6.CME",
            source="ib",
            fidelity=DataFidelity.INFERRED,
            dedupe_key="bar:key",
            event_ts=NOW,
            init_ts=NOW,
        )


def test_stream_checkpoint_has_stable_source_scoped_key() -> None:
    checkpoint = StreamCheckpoint(
        instrument_id="NQU6.CME",
        event_kind=PersistenceEventKind.TRADE_TICK,
        source="ib",
        last_event_ts=NOW,
        last_dedupe_key="trade:key",
        committed_ts=NOW + timedelta(seconds=1),
    )

    assert checkpoint.stream_key == "ib:NQU6.CME:trade_tick"


def test_recovery_terminal_state_requires_completion_timestamp() -> None:
    with pytest.raises(ValidationError, match="terminal recovery state"):
        RecoveryRecord(
            recovery_id=RECOVERY_ID,
            instrument_id="ESU6.CME",
            event_kind=PersistenceEventKind.ONE_MINUTE_BAR,
            source="ib",
            status=RecoveryStatus.COMPLETE,
            requested_start_ts=NOW,
            requested_end_ts=NOW + timedelta(hours=1),
            started_ts=NOW,
            updated_ts=NOW,
        )


def test_outbox_delivery_state_is_explicit() -> None:
    record = NotificationOutboxRecord(
        outbox_id=OUTBOX_ID,
        topic="signals.high",
        destination_key="discord.signals.high",
        aggregate_key="signal:NQ:123",
        event_type="signal.upsert",
        event_schema_version="1.0",
        payload={"instrument_id": "NQU6.CME"},
        dedupe_key="signal:NQ:123:v1",
        status=OutboxStatus.DELIVERED,
        attempt_count=1,
        available_ts=NOW,
        created_ts=NOW,
        updated_ts=NOW + timedelta(seconds=1),
        delivered_ts=NOW + timedelta(seconds=1),
    )

    assert record.status == OutboxStatus.DELIVERED


def test_outbox_rejects_lease_without_expiry() -> None:
    with pytest.raises(ValidationError, match="requires lease owner and expiry"):
        NotificationOutboxRecord(
            outbox_id=OUTBOX_ID,
            topic="signals.high",
            destination_key="discord.signals.high",
            aggregate_key="signal:NQ:123",
            event_type="signal.upsert",
            event_schema_version="1.0",
            payload={},
            dedupe_key="signal:NQ:123:v1",
            status=OutboxStatus.LEASED,
            available_ts=NOW,
            created_ts=NOW,
            updated_ts=NOW,
        )


def test_outbox_rejects_nested_delivery_secret() -> None:
    with pytest.raises(ValidationError, match="cannot contain delivery secrets"):
        NotificationOutboxRecord(
            outbox_id=OUTBOX_ID,
            topic="signals.high",
            destination_key="discord.signals.high",
            aggregate_key="signal:NQ:123",
            event_type="signal.upsert",
            event_schema_version="1.0",
            payload={"delivery": {"webhook_url": "https://discord.invalid/secret"}},
            dedupe_key="signal:NQ:123:v1",
            available_ts=NOW,
            created_ts=NOW,
            updated_ts=NOW,
        )


def test_persistence_config_enforces_retention_and_bounded_batching() -> None:
    config = PersistenceConfig()

    assert config.tick_retention_sessions == 5
    assert config.bar_retention_sessions > config.tick_retention_sessions
    assert config.catalog_batch_size <= config.catalog_writer_queue_size
    assert config.catalog_flush_poll_seconds == 0.25
    assert config.sqlite_busy_timeout_ms == 5_000

    with pytest.raises(ValidationError, match="writer queue size"):
        PersistenceConfig(catalog_writer_queue_size=10, catalog_batch_size=11)

    with pytest.raises(ValidationError):
        PersistenceConfig(catalog_flush_poll_seconds=0)


def test_persistence_contracts_reject_non_utc_timestamps() -> None:
    with pytest.raises(ValidationError, match="timestamp must be UTC"):
        StreamCheckpoint(
            instrument_id="NQU6.CME",
            event_kind=PersistenceEventKind.QUOTE_TICK,
            source="ib",
            last_event_ts=NOW.astimezone(timezone(timedelta(hours=3))),
            last_dedupe_key="quote:key",
            committed_ts=NOW,
        )
