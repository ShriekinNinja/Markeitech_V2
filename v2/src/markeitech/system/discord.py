from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from queue import Empty, Full, Queue
from threading import Lock, Thread
from time import monotonic
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId
from nautilus_trader.network import HttpResponse, http_post

from markeitech.system.control import SystemHealthState
from markeitech.system.messages import SYSTEM_HEALTH_SIGNAL, SystemHealthEvent

SYSTEM_HEALTH_WEBHOOK_ENV = "MARKEITECH_DISCORD_SYSTEM_HEALTH_WEBHOOK"

_RESULT_TIMER = "discord-health-delivery-results"
_RESULT_POLL_INTERVAL_NS = 1_000_000_000
_QUEUE_CAPACITY = len(SystemHealthState)
_STOP = object()

_STATE_COLORS = {
    SystemHealthState.STARTING.value: 0xF1C40F,
    SystemHealthState.READY.value: 0x2ECC71,
    SystemHealthState.DEGRADED.value: 0xE67E22,
    SystemHealthState.FAILED.value: 0xE74C3C,
    SystemHealthState.STOPPING.value: 0x95A5A6,
}

PostCallable = Callable[..., HttpResponse]


@dataclass(frozen=True, slots=True)
class DiscordDelivery:
    state: str
    body: bytes


@dataclass(frozen=True, slots=True)
class DiscordDeliveryResult:
    state: str
    delivered: bool
    status: int | None = None
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class DiscordWorkerStats:
    accepted: int
    delivered: int
    failed: int
    rejected: int

    @property
    def pending(self) -> int:
        return self.accepted - self.delivered - self.failed


class DiscordDeliveryWorker:
    def __init__(
        self,
        webhook_url: str,
        timeout_seconds: int,
        *,
        post: PostCallable = http_post,
    ) -> None:
        self._webhook_url = _with_wait_confirmation(webhook_url)
        self._timeout_seconds = timeout_seconds
        self._post = post
        self._pending: Queue[DiscordDelivery | object] = Queue(maxsize=_QUEUE_CAPACITY)
        self.results: Queue[DiscordDeliveryResult] = Queue()
        self._closed = False
        self._stop_enqueued = False
        self._counter_lock = Lock()
        self._accepted = 0
        self._delivered = 0
        self._failed = 0
        self._rejected = 0
        self._thread = Thread(
            target=self._run,
            name="markeitech-discord-health",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def submit(self, delivery: DiscordDelivery) -> bool:
        if self._closed:
            self._increment("_rejected")
            return False
        try:
            self._pending.put_nowait(delivery)
        except Full:
            self._increment("_rejected")
            return False
        self._increment("_accepted")
        return True

    def close(self) -> bool:
        self._closed = True
        deadline = monotonic() + self._timeout_seconds
        if not self._stop_enqueued:
            try:
                self._pending.put(_STOP, timeout=max(0.0, deadline - monotonic()))
            except Full:
                return False
            self._stop_enqueued = True
        self._thread.join(timeout=max(0.0, deadline - monotonic()))
        return not self._thread.is_alive()

    def snapshot(self) -> DiscordWorkerStats:
        with self._counter_lock:
            return DiscordWorkerStats(
                accepted=self._accepted,
                delivered=self._delivered,
                failed=self._failed,
                rejected=self._rejected,
            )

    def _run(self) -> None:
        while True:
            item = self._pending.get()
            try:
                if item is _STOP:
                    return
                assert isinstance(item, DiscordDelivery)
                result = self._deliver(item)
                self._increment("_delivered" if result.delivered else "_failed")
                self.results.put(result)
            finally:
                self._pending.task_done()

    def _increment(self, field_name: str) -> None:
        with self._counter_lock:
            setattr(self, field_name, getattr(self, field_name) + 1)

    def _deliver(self, delivery: DiscordDelivery) -> DiscordDeliveryResult:
        try:
            response = self._post(
                self._webhook_url,
                headers={"Content-Type": "application/json"},
                body=delivery.body,
                timeout_secs=self._timeout_seconds,
            )
        except Exception as exc:  # Discord must not affect the runtime.
            return DiscordDeliveryResult(
                state=delivery.state,
                delivered=False,
                error_code=type(exc).__name__,
            )
        return DiscordDeliveryResult(
            state=delivery.state,
            delivered=200 <= response.status < 300,
            status=response.status,
            error_code=None if 200 <= response.status < 300 else "http_status",
        )


class DiscordHealthActorConfig(DataActorConfig):
    def __new__(
        cls,
        request_timeout_seconds: int,
        actor_id: str | ActorId = "DISCORD-HEALTH",
        webhook_env: str = SYSTEM_HEALTH_WEBHOOK_ENV,
    ) -> DiscordHealthActorConfig:
        resolved_actor_id = (
            actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        )
        obj = super().__new__(cls, actor_id=resolved_actor_id)
        obj.request_timeout_seconds = request_timeout_seconds
        obj.webhook_env = webhook_env
        return obj


class DiscordHealthActor(DataActor):
    def __init__(self, config: DiscordHealthActorConfig) -> None:
        super().__init__(config)
        self._timeout_seconds = config.request_timeout_seconds
        self._webhook_env = config.webhook_env
        self._worker: DiscordDeliveryWorker | None = None
        self._subscribed = False
        self._summary_logged = False

    def on_start(self) -> None:
        webhook_url = os.getenv(self._webhook_env, "").strip()
        if not webhook_url:
            self.log.warning(
                f"DISCORD_HEALTH_DISABLED | reason=missing_environment"
                f" | variable={self._webhook_env}",
            )
            return

        self._worker = DiscordDeliveryWorker(webhook_url, self._timeout_seconds)
        self._worker.start()
        self.subscribe_signal(SYSTEM_HEALTH_SIGNAL)
        self._subscribed = True
        self.clock.set_timer_ns(
            _RESULT_TIMER,
            _RESULT_POLL_INTERVAL_NS,
            callback=self._drain_results,
        )
        self.log.info("DISCORD_HEALTH_READY")

    def on_signal(self, signal: Signal) -> None:
        if self._worker is None:
            return
        try:
            event = SystemHealthEvent.from_signal_value(signal.value)
        except ValueError as exc:
            self.log.error(
                f"DISCORD_HEALTH_REJECTED | reason=invalid_event"
                f" | error={type(exc).__name__}",
            )
            return
        if event.state not in _STATE_COLORS:
            self.log.warning(f"DISCORD_HEALTH_IGNORED | state={event.state}")
            return

        delivery = DiscordDelivery(
            state=event.state,
            body=render_system_health_message(event, signal.ts_event),
        )
        if not self._worker.submit(delivery):
            self.log.error(f"DISCORD_HEALTH_DROPPED | state={event.state} | reason=queue_full")

    def on_stop(self) -> None:
        if self._subscribed:
            self.unsubscribe_signal(SYSTEM_HEALTH_SIGNAL)
            self._subscribed = False
        if _RESULT_TIMER in self.clock.timer_names():
            self.clock.cancel_timer(_RESULT_TIMER)
        self._close_worker()
        self._drain_results(None)
        self._log_summary()

    def on_dispose(self) -> None:
        self._close_worker()

    def _close_worker(self) -> None:
        if self._worker is None:
            return
        if not self._worker.close():
            self.log.error("DISCORD_HEALTH_WORKER_TIMEOUT")

    def _drain_results(self, _event) -> None:  # noqa: ANN001
        if self._worker is None:
            return
        while True:
            try:
                result = self._worker.results.get_nowait()
            except Empty:
                return
            if result.delivered:
                self.log.info(
                    f"DISCORD_HEALTH_DELIVERED | state={result.state} | status={result.status}",
                )
            else:
                self.log.error(
                    f"DISCORD_HEALTH_DELIVERY_FAILED | state={result.state}"
                    f" | status={result.status} | error={result.error_code}",
                )

    def _log_summary(self) -> None:
        if self._summary_logged:
            return
        self._summary_logged = True
        if self._worker is None:
            self.log.info(
                "DISCORD_HEALTH_SUMMARY | accepted=0 | delivered=0"
                " | failed=0 | rejected=0 | pending=0",
            )
            return
        stats = self._worker.snapshot()
        self.log.info(
            "DISCORD_HEALTH_SUMMARY"
            f" | accepted={stats.accepted} | delivered={stats.delivered}"
            f" | failed={stats.failed} | rejected={stats.rejected}"
            f" | pending={stats.pending}",
        )


def render_system_health_message(event: SystemHealthEvent, ts_event: int) -> bytes:
    available = event.evidence.get("available_instrument_count", "unknown")
    expected = event.evidence.get("expected_instrument_count", "unknown")
    instruments = event.evidence.get("expected_instruments", "not reported")
    fields: list[dict[str, Any]] = [
        {"name": "State", "value": event.state, "inline": True},
        {"name": "Instruments", "value": f"{available}/{expected}", "inline": True},
        {"name": "Source", "value": event.source, "inline": True},
        {"name": "Configured instruments", "value": str(instruments) or "none"},
    ]
    previous = event.evidence.get("previous_state")
    if previous is not None:
        fields.append({"name": "Previous state", "value": str(previous), "inline": True})

    embed: dict[str, Any] = {
        "title": f"Markeitech V2 | {event.state}",
        "description": event.reason,
        "color": _STATE_COLORS[event.state],
        "fields": fields,
        "footer": {"text": "System health"},
    }
    if ts_event > 0:
        embed["timestamp"] = datetime.fromtimestamp(ts_event / 1_000_000_000, UTC).isoformat()

    return json.dumps(
        {
            "allowed_mentions": {"parse": []},
            "embeds": [embed],
        },
        separators=(",", ":"),
    ).encode()


def _with_wait_confirmation(webhook_url: str) -> str:
    parts = urlsplit(webhook_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["wait"] = "true"
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
