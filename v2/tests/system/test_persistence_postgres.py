from __future__ import annotations

import os
from uuid import uuid4

import pytest

from markeitech.system.messages import SystemHealthEvent
from markeitech.system.persistence import (
    HealthEventRecord,
    OperationalEventRecord,
    OperationalStore,
)

TEST_DSN_ENV = "MARKEITECH_TEST_POSTGRES_DSN"


@pytest.mark.postgres
@pytest.mark.skipif(not os.getenv(TEST_DSN_ENV), reason=f"{TEST_DSN_ENV} is not configured")
def test_postgres_migrations_restart_reads_and_duplicate_event_write() -> None:
    store = OperationalStore(os.environ[TEST_DSN_ENV], connect_timeout_seconds=3)
    store.initialize()
    store.initialize()
    run_id = uuid4()
    store.start_run("MARKEITECH-V2-POSTGRES-TEST", run_id)
    event = SystemHealthEvent(
        state="READY",
        reason="integration test prerequisites available",
        source="SYSTEM-CONTROL",
        evidence={"operational_persistence_ready": True},
    )
    record = HealthEventRecord(
        run_id=run_id,
        sequence=1,
        event=event,
        ts_event_ns=100,
        ts_init_ns=101,
    )

    store.write_health_event(record)
    store.write_health_event(record)
    operational_record = OperationalEventRecord(
        event_id="watchlist-membership:1",
        run_id=run_id,
        sequence=1,
        signal_name="markeitech.watchlist.membership",
        event_type="watchlist.membership",
        source="WATCHLIST",
        correlation_id="baseline:config",
        causation_id=None,
        payload={"membership_revision": 1, "instrument_count": 2},
        ts_event_ns=102,
        ts_init_ns=103,
        schema_version=1,
    )
    store.write_operational_event(operational_record)
    store.write_operational_event(operational_record)
    with pytest.raises(RuntimeError, match="identity collision"):
        store.write_operational_event(
            OperationalEventRecord(
                event_id=operational_record.event_id,
                run_id=run_id,
                sequence=operational_record.sequence,
                signal_name=operational_record.signal_name,
                event_type=operational_record.event_type,
                source=operational_record.source,
                correlation_id=operational_record.correlation_id,
                causation_id=operational_record.causation_id,
                payload={"membership_revision": 999},
                ts_event_ns=operational_record.ts_event_ns,
                ts_init_ns=operational_record.ts_init_ns,
                schema_version=operational_record.schema_version,
            ),
        )

    restarted_store = OperationalStore(os.environ[TEST_DSN_ENV], connect_timeout_seconds=3)
    stored_run = restarted_store.load_run(run_id)
    stored_events = restarted_store.load_health_events(run_id)
    stored_operational_events = restarted_store.load_operational_events(run_id)
    assert stored_run is not None and stored_run.terminal_state is None
    assert len(stored_events) == 1
    assert stored_events[0].sequence == 1
    assert stored_events[0].evidence == {"operational_persistence_ready": True}
    assert len(stored_operational_events) == 1
    assert stored_operational_events[0].event_id == "watchlist-membership:1"
    assert stored_operational_events[0].payload == {
        "membership_revision": 1,
        "instrument_count": 2,
    }

    restarted_store.close_run(run_id, "STOPPED", "integration test completed")
    closed_run = restarted_store.load_run(run_id)
    assert closed_run is not None and closed_run.terminal_state == "STOPPED"


@pytest.mark.postgres
@pytest.mark.skipif(not os.getenv(TEST_DSN_ENV), reason=f"{TEST_DSN_ENV} is not configured")
def test_initialize_recreates_a_dropped_applied_migration_table() -> None:
    store = OperationalStore(os.environ[TEST_DSN_ENV], connect_timeout_seconds=3)
    store.initialize()
    try:
        with store._connect() as connection:  # noqa: SLF001 - schema recovery integration test
            connection.execute("DROP TABLE operational_events")

        store.initialize()
    finally:
        store.initialize()

    with store._connect() as connection:  # noqa: SLF001 - schema integration test
        table_name = connection.execute(
            "SELECT to_regclass('operational_events')::text",
        ).fetchone()
    assert table_name == ("operational_events",)
