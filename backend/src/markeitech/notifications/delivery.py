from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from threading import Event, Lock, Thread
from typing import Any, Protocol
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from markeitech.notifications.config import DiscordDeliveryConfig
from markeitech.persistence import NotificationOutboxRecord, NotificationOutboxStore


@dataclass(frozen=True)
class DiscordWebhookResponse:
    status_code: int
    retry_after_seconds: float | None = None


class DiscordWebhookTransport(Protocol):
    def send(
        self,
        webhook_url: str,
        payload: dict[str, Any],
        *,
        timeout_seconds: float,
    ) -> DiscordWebhookResponse: ...


class UrllibDiscordWebhookTransport:
    def send(
        self,
        webhook_url: str,
        payload: dict[str, Any],
        *,
        timeout_seconds: float,
    ) -> DiscordWebhookResponse:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = Request(
            webhook_url,
            data=body,
            headers={"Content-Type": "application/json", "User-Agent": "Markeitech/0.1"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
                return DiscordWebhookResponse(status_code=response.status)
        except HTTPError as exc:
            return DiscordWebhookResponse(
                status_code=exc.code,
                retry_after_seconds=_retry_after_seconds(exc),
            )


class DiscordDeliveryStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass(frozen=True)
class DiscordDeliverySnapshot:
    status: DiscordDeliveryStatus
    leased_count: int
    delivered_count: int
    failed_attempt_count: int
    last_error: str | None


class DiscordOutboxDeliveryWorker:
    def __init__(
        self,
        store: NotificationOutboxStore,
        config: DiscordDeliveryConfig,
        *,
        transport: DiscordWebhookTransport | None = None,
        environment: Mapping[str, str] | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        lease_owner: str = "discord-webhook-worker",
    ) -> None:
        if not config.enabled:
            raise ValueError("Discord delivery worker requires enabled configuration")
        if not lease_owner:
            raise ValueError("Discord delivery lease owner must not be empty")
        self._store = store
        self._config = config
        self._transport = transport or UrllibDiscordWebhookTransport()
        self._environment = os.environ if environment is None else environment
        self._clock = clock
        self._lease_owner = lease_owner
        self._routes = {
            route.destination_key: route.environment_variable for route in config.routes
        }
        self._stop = Event()
        self._thread: Thread | None = None
        self._lock = Lock()
        self._status = DiscordDeliveryStatus.CREATED
        self._leased_count = 0
        self._delivered_count = 0
        self._failed_attempt_count = 0
        self._last_error: str | None = None

    @property
    def snapshot(self) -> DiscordDeliverySnapshot:
        with self._lock:
            return DiscordDeliverySnapshot(
                status=self._status,
                leased_count=self._leased_count,
                delivered_count=self._delivered_count,
                failed_attempt_count=self._failed_attempt_count,
                last_error=self._last_error,
            )

    def start(self) -> None:
        for destination_key in self._routes:
            self._webhook_url(destination_key)
        with self._lock:
            if self._status != DiscordDeliveryStatus.CREATED:
                raise RuntimeError("Discord delivery worker can only start once")
            self._status = DiscordDeliveryStatus.RUNNING
            self._thread = Thread(target=self._run, name="discord-outbox", daemon=True)
            thread = self._thread
        thread.start()

    def stop(self, timeout_seconds: float = 10.0) -> None:
        with self._lock:
            if self._status in {DiscordDeliveryStatus.CREATED, DiscordDeliveryStatus.STOPPED}:
                self._status = DiscordDeliveryStatus.STOPPED
                return
            if self._status != DiscordDeliveryStatus.FAILED:
                self._status = DiscordDeliveryStatus.STOPPING
            thread = self._thread
        self._stop.set()
        if thread is not None:
            thread.join(timeout_seconds)
            if thread.is_alive():
                raise TimeoutError("Discord delivery worker did not stop")

    def run_once(self, *, now: datetime | None = None) -> int:
        observed_now = self._clock() if now is None else now
        leased = self._store.lease_pending(
            lease_owner=self._lease_owner,
            now=observed_now,
            limit=self._config.batch_size,
            destination_keys=tuple(self._routes),
        )
        with self._lock:
            self._leased_count += len(leased)
        for record in leased:
            self._deliver(record, observed_now)
        return len(leased)

    def _run(self) -> None:
        try:
            while not self._stop.is_set():
                self.run_once()
                self._stop.wait(self._config.poll_interval_seconds)
        except Exception as exc:
            with self._lock:
                self._status = DiscordDeliveryStatus.FAILED
                self._last_error = f"{type(exc).__name__}: {exc}"
            return
        with self._lock:
            self._status = DiscordDeliveryStatus.STOPPED

    def _deliver(self, record: NotificationOutboxRecord, now: datetime) -> None:
        try:
            webhook_url = self._webhook_url(record.destination_key)
            response = self._transport.send(
                webhook_url,
                record.payload,
                timeout_seconds=self._config.request_timeout_seconds,
            )
            if 200 <= response.status_code < 300:
                self._store.mark_delivered(
                    outbox_id=record.outbox_id,
                    lease_owner=self._lease_owner,
                    delivered_ts=now,
                )
                with self._lock:
                    self._delivered_count += 1
                return
            retry_after = response.retry_after_seconds
            error = f"Discord HTTP {response.status_code}"
        except Exception as exc:
            retry_after = None
            error = f"{type(exc).__name__}: {exc}"
        retry_seconds = self._retry_seconds(record.attempt_count, retry_after)
        self._store.mark_failed(
            outbox_id=record.outbox_id,
            lease_owner=self._lease_owner,
            failed_ts=now,
            retry_ts=now + timedelta(seconds=retry_seconds),
            error=error,
        )
        with self._lock:
            self._failed_attempt_count += 1
            self._last_error = error

    def _webhook_url(self, destination_key: str) -> str:
        variable = self._routes[destination_key]
        value = self._environment.get(variable)
        if not value:
            raise RuntimeError(f"Discord route {destination_key!r} is not configured")
        if not value.startswith("https://"):
            raise RuntimeError(f"Discord route {destination_key!r} must use HTTPS")
        return value

    def _retry_seconds(self, attempt_count: int, retry_after: float | None) -> float:
        if retry_after is not None and retry_after > 0:
            return min(retry_after, self._config.max_retry_seconds)
        exponential = self._config.base_retry_seconds * (2 ** max(0, attempt_count - 1))
        return min(exponential, self._config.max_retry_seconds)


def _retry_after_seconds(error: HTTPError) -> float | None:
    header = error.headers.get("Retry-After")
    if header is not None:
        try:
            return float(header)
        except ValueError:
            pass
    try:
        payload = json.loads(error.read().decode("utf-8"))
        value = payload.get("retry_after")
        return float(value) if value is not None else None
    except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
        return None
