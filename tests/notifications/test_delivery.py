from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from markeitech.notifications import (
    DiscordDeliveryConfig,
    DiscordDeliveryStatus,
    DiscordOutboxDeliveryWorker,
    DiscordRouteConfig,
    DiscordWebhookResponse,
)
from markeitech.persistence import NotificationOutboxRecord, OutboxStatus
from markeitech.persistence.config import PersistenceConfig
from markeitech.persistence.sqlite import SQLiteMetadataStore

NOW = datetime(2026, 7, 17, 8, tzinfo=UTC)
OUTBOX_ID = UUID("b8233142-d9ad-44e6-9343-60af5f82c925")


class StubTransport:
    def __init__(self, responses: list[DiscordWebhookResponse | Exception]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict[str, Any], float]] = []

    def send(
        self,
        webhook_url: str,
        payload: dict[str, Any],
        *,
        timeout_seconds: float,
    ) -> DiscordWebhookResponse:
        self.calls.append((webhook_url, payload, timeout_seconds))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def config(path: Path, *, max_attempts: int = 3) -> PersistenceConfig:
    return PersistenceConfig(
        catalog_path=path / "catalog",
        metadata_path=path / "metadata.sqlite3",
        outbox_max_attempts=max_attempts,
    )


def delivery_config() -> DiscordDeliveryConfig:
    return DiscordDeliveryConfig(
        enabled=True,
        routes=(
            DiscordRouteConfig(
                destination_key="signal-lifecycle",
                environment_variable="MARKEITECH_DISCORD_SIGNALS_WEBHOOK",
            ),
        ),
        base_retry_seconds=2,
        max_retry_seconds=30,
    )


def record(
    *,
    destination_key: str = "signal-lifecycle",
    outbox_id: UUID = OUTBOX_ID,
) -> NotificationOutboxRecord:
    return NotificationOutboxRecord(
        outbox_id=outbox_id,
        topic="discord",
        destination_key=destination_key,
        aggregate_key="signal-1",
        event_type="signal.transition",
        event_schema_version="1.0",
        payload={"content": "NQ armed"},
        dedupe_key=f"signal:{outbox_id}",
        available_ts=NOW,
        created_ts=NOW,
        updated_ts=NOW,
    )


def worker(
    store: SQLiteMetadataStore,
    transport: StubTransport,
) -> DiscordOutboxDeliveryWorker:
    return DiscordOutboxDeliveryWorker(
        store,
        delivery_config(),
        transport=transport,
        environment={"MARKEITECH_DISCORD_SIGNALS_WEBHOOK": "https://discord.test/hook"},
        clock=lambda: NOW,
    )


def test_successful_delivery_leases_and_marks_record_once(tmp_path: Path) -> None:
    with SQLiteMetadataStore(config(tmp_path)) as store:
        store.enqueue(record())
        transport = StubTransport([DiscordWebhookResponse(204)])
        subject = worker(store, transport)

        assert subject.run_once(now=NOW) == 1
        assert subject.run_once(now=NOW) == 0
        delivered = store.load_outbox(OUTBOX_ID)

    assert delivered is not None
    assert delivered.status == OutboxStatus.DELIVERED
    assert delivered.attempt_count == 1
    assert len(transport.calls) == 1
    assert subject.snapshot.delivered_count == 1


def test_delivery_worker_only_leases_its_configured_destinations(tmp_path: Path) -> None:
    other_id = UUID("f1fb5e10-6485-4e48-8302-87b7a0195a08")
    with SQLiteMetadataStore(config(tmp_path)) as store:
        store.enqueue(record(destination_key="future-transport", outbox_id=other_id))
        subject = worker(store, StubTransport([]))

        assert subject.run_once(now=NOW) == 0
        untouched = store.load_outbox(other_id)

    assert untouched is not None
    assert untouched.status == OutboxStatus.PENDING
    assert untouched.attempt_count == 0


def test_rate_limit_failure_uses_server_retry_and_then_delivers(tmp_path: Path) -> None:
    with SQLiteMetadataStore(config(tmp_path)) as store:
        store.enqueue(record())
        transport = StubTransport(
            [DiscordWebhookResponse(429, retry_after_seconds=7), DiscordWebhookResponse(204)]
        )
        subject = worker(store, transport)

        subject.run_once(now=NOW)
        failed = store.load_outbox(OUTBOX_ID)
        assert failed is not None
        assert failed.status == OutboxStatus.FAILED
        assert failed.available_ts == NOW + timedelta(seconds=7)
        assert subject.run_once(now=NOW + timedelta(seconds=6)) == 0
        assert subject.run_once(now=NOW + timedelta(seconds=7)) == 1
        delivered = store.load_outbox(OUTBOX_ID)

    assert delivered is not None
    assert delivered.status == OutboxStatus.DELIVERED
    assert delivered.attempt_count == 2


def test_transport_error_retries_exponentially_until_store_limit(tmp_path: Path) -> None:
    with SQLiteMetadataStore(config(tmp_path, max_attempts=2)) as store:
        store.enqueue(record())
        transport = StubTransport([TimeoutError("slow"), TimeoutError("still slow")])
        subject = worker(store, transport)

        subject.run_once(now=NOW)
        subject.run_once(now=NOW + timedelta(seconds=2))
        assert subject.run_once(now=NOW + timedelta(seconds=30)) == 0
        failed = store.load_outbox(OUTBOX_ID)

    assert failed is not None
    assert failed.status == OutboxStatus.FAILED
    assert failed.attempt_count == 2
    assert "TimeoutError" in (failed.last_error or "")
    assert subject.snapshot.failed_attempt_count == 2


def test_missing_secret_fails_without_exposing_environment_name_or_url(tmp_path: Path) -> None:
    with SQLiteMetadataStore(config(tmp_path)) as store:
        store.enqueue(record())
        subject = DiscordOutboxDeliveryWorker(
            store,
            delivery_config(),
            transport=StubTransport([]),
            environment={},
            clock=lambda: NOW,
        )

        subject.run_once(now=NOW)
        failed = store.load_outbox(OUTBOX_ID)

    assert failed is not None
    assert failed.status == OutboxStatus.FAILED
    assert failed.last_error == "RuntimeError: Discord route 'signal-lifecycle' is not configured"
    assert "WEBHOOK" not in failed.last_error


def test_thread_lifecycle_stops_cleanly_without_pending_records(tmp_path: Path) -> None:
    with SQLiteMetadataStore(config(tmp_path)) as store:
        subject = worker(store, StubTransport([]))
        subject.start()
        subject.stop()

    assert subject.snapshot.status == DiscordDeliveryStatus.STOPPED
