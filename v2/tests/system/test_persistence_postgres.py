from __future__ import annotations

import os
from uuid import uuid4

import pytest

from markeitech.system.messages import SystemHealthEvent
from markeitech.system.persistence import HealthEventRecord, OperationalStore

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

    restarted_store = OperationalStore(os.environ[TEST_DSN_ENV], connect_timeout_seconds=3)
    stored_run = restarted_store.load_run(run_id)
    stored_events = restarted_store.load_health_events(run_id)
    assert stored_run is not None and stored_run.terminal_state is None
    assert len(stored_events) == 1
    assert stored_events[0].sequence == 1
    assert stored_events[0].evidence == {"operational_persistence_ready": True}

    restarted_store.close_run(run_id, "STOPPED", "integration test completed")
    closed_run = restarted_store.load_run(run_id)
    assert closed_run is not None and closed_run.terminal_state == "STOPPED"
