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

from markeitech.acquisition.historical_messages import (
    HISTORICAL_DEPENDENCY_DEMAND_SIGNAL,
    HISTORICAL_READINESS_SIGNAL,
    HistoricalDependencyDemandEvent,
    HistoricalReadinessEvent,
)
from markeitech.system.control import SystemHealthState
from markeitech.system.messages import (
    SYSTEM_HEALTH_SIGNAL,
    WATCHLIST_LIFECYCLE_SIGNAL,
    WATCHLIST_MEMBERSHIP_SIGNAL,
    SystemHealthEvent,
    WatchlistLifecycleEvent,
    WatchlistMembershipEvent,
)
from markeitech.system.resource_contracts import (
    RUNTIME_RESOURCE_HEALTH_SIGNAL,
    RuntimeResourceHealthEvent,
)

SYSTEM_HEALTH_WEBHOOK_ENV = "MARKEITECH_DISCORD_SYSTEM_HEALTH_WEBHOOK"
OPERATIONAL_EVENTS_WEBHOOK_ENV = "MARKEITECH_DISCORD_OPERATIONAL_EVENTS_WEBHOOK"

_RESULT_TIMER = "discord-health-delivery-results"
_RESULT_POLL_INTERVAL_NS = 1_000_000_000
_STOP = object()

_STATE_COLORS = {
    SystemHealthState.STARTING.value: 0xF1C40F,
    SystemHealthState.READY.value: 0x2ECC71,
    SystemHealthState.DEGRADED.value: 0xE67E22,
    SystemHealthState.FAILED.value: 0xE74C3C,
    SystemHealthState.STOPPING.value: 0x95A5A6,
}
_RESOURCE_STATE_COLORS = {
    "NORMAL": 0x2ECC71,
    "WARNING": 0xE67E22,
    "CRITICAL": 0xE74C3C,
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
        queue_capacity: int = 32,
        *,
        post: PostCallable = http_post,
    ) -> None:
        self._webhook_url = _with_wait_confirmation(webhook_url)
        self._timeout_seconds = timeout_seconds
        self._post = post
        self._pending: Queue[DiscordDelivery | object] = Queue(maxsize=queue_capacity)
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
        queue_capacity: int,
        ping_critical_resource_alerts: bool,
        actor_id: str | ActorId = "DISCORD-HEALTH",
        webhook_env: str = SYSTEM_HEALTH_WEBHOOK_ENV,
        operational_events_webhook_env: str = OPERATIONAL_EVENTS_WEBHOOK_ENV,
    ) -> DiscordHealthActorConfig:
        resolved_actor_id = (
            actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        )
        obj = super().__new__(cls, actor_id=resolved_actor_id)
        obj.request_timeout_seconds = request_timeout_seconds
        obj.queue_capacity = queue_capacity
        obj.ping_critical_resource_alerts = ping_critical_resource_alerts
        obj.webhook_env = webhook_env
        obj.operational_events_webhook_env = operational_events_webhook_env
        return obj


type HistoricalDependencyKey = tuple[str, str, int, str, str, str]


@dataclass(frozen=True, slots=True)
class OperationalReadinessSnapshot:
    system_state: str
    observed_watchlist_count: int
    expected_watchlist_count: int
    historical_state_counts: dict[str, int]
    completed_at_ns: int

    @property
    def historical_total(self) -> int:
        return sum(self.historical_state_counts.values())

    @property
    def is_ready(self) -> bool:
        return set(self.historical_state_counts) == {"READY"}


class OperationalReadinessProjection:
    def __init__(self) -> None:
        self._system_state: str | None = None
        self._membership_revision: int | None = None
        self._expected_watchlist: set[str] = set()
        self._observed_watchlist: set[str] = set()
        self._demands: dict[HistoricalDependencyKey, HistoricalDependencyDemandEvent] = {}
        self._readiness: dict[HistoricalDependencyKey, HistoricalReadinessEvent] = {}
        self._emitted = False

    def accept_system_health(self, event: SystemHealthEvent) -> OperationalReadinessSnapshot | None:
        self._system_state = event.state
        return self._snapshot_if_complete()

    def accept_membership(
        self,
        event: WatchlistMembershipEvent,
    ) -> OperationalReadinessSnapshot | None:
        if event.membership_revision != self._membership_revision:
            self._membership_revision = event.membership_revision
            self._observed_watchlist.clear()
        self._expected_watchlist = {member.instrument_id for member in event.members}
        return self._snapshot_if_complete()

    def accept_lifecycle(
        self,
        event: WatchlistLifecycleEvent,
    ) -> OperationalReadinessSnapshot | None:
        if (
            event.membership_revision == self._membership_revision
            and event.state == "INSTRUMENT_OBSERVED"
            and event.instrument_id is not None
        ):
            self._observed_watchlist.add(event.instrument_id)
        return self._snapshot_if_complete()

    def accept_demand(
        self,
        event: HistoricalDependencyDemandEvent,
    ) -> OperationalReadinessSnapshot | None:
        self._demands[_historical_key(event)] = event
        return self._snapshot_if_complete()

    def accept_readiness(
        self,
        event: HistoricalReadinessEvent,
    ) -> OperationalReadinessSnapshot | None:
        self._readiness[_historical_key(event)] = event
        return self._snapshot_if_complete()

    def _snapshot_if_complete(self) -> OperationalReadinessSnapshot | None:
        if self._emitted or self._system_state != SystemHealthState.READY.value:
            return None
        if not self._expected_watchlist or not self._expected_watchlist.issubset(
            self._observed_watchlist,
        ):
            return None
        if not self._demands or not set(self._demands).issubset(self._readiness):
            return None
        readiness = [self._readiness[key] for key in self._demands]
        counts: dict[str, int] = {}
        for event in readiness:
            counts[event.state] = counts.get(event.state, 0) + 1
        self._emitted = True
        return OperationalReadinessSnapshot(
            system_state=self._system_state,
            observed_watchlist_count=len(self._expected_watchlist & self._observed_watchlist),
            expected_watchlist_count=len(self._expected_watchlist),
            historical_state_counts=dict(sorted(counts.items())),
            completed_at_ns=max(event.completed_at_ns for event in readiness),
        )


class DiscordHealthActor(DataActor):
    def __init__(self, config: DiscordHealthActorConfig) -> None:
        super().__init__(config)
        self._timeout_seconds = config.request_timeout_seconds
        self._queue_capacity = config.queue_capacity
        self._ping_critical_resource_alerts = config.ping_critical_resource_alerts
        self._webhook_env = config.webhook_env
        self._operational_events_webhook_env = config.operational_events_webhook_env
        self._worker: DiscordDeliveryWorker | None = None
        self._operational_worker: DiscordDeliveryWorker | None = None
        self._operational_readiness = OperationalReadinessProjection()
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

        self._worker = DiscordDeliveryWorker(
            webhook_url,
            self._timeout_seconds,
            self._queue_capacity,
        )
        self._worker.start()
        operational_webhook_url = os.getenv(self._operational_events_webhook_env, "").strip()
        if operational_webhook_url:
            self._operational_worker = DiscordDeliveryWorker(
                operational_webhook_url,
                self._timeout_seconds,
                self._queue_capacity,
            )
            self._operational_worker.start()
        else:
            self.log.warning(
                "DISCORD_OPERATIONAL_DISABLED | reason=missing_environment"
                f" | variable={self._operational_events_webhook_env}",
            )
        self.subscribe_signal(SYSTEM_HEALTH_SIGNAL)
        self.subscribe_signal(RUNTIME_RESOURCE_HEALTH_SIGNAL)
        if self._operational_worker is not None:
            self.subscribe_signal(WATCHLIST_MEMBERSHIP_SIGNAL)
            self.subscribe_signal(WATCHLIST_LIFECYCLE_SIGNAL)
            self.subscribe_signal(HISTORICAL_DEPENDENCY_DEMAND_SIGNAL)
            self.subscribe_signal(HISTORICAL_READINESS_SIGNAL)
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
        if signal.name in {
            WATCHLIST_MEMBERSHIP_SIGNAL,
            WATCHLIST_LIFECYCLE_SIGNAL,
            HISTORICAL_DEPENDENCY_DEMAND_SIGNAL,
            HISTORICAL_READINESS_SIGNAL,
        }:
            self._handle_operational_readiness(signal)
            return
        if signal.name == RUNTIME_RESOURCE_HEALTH_SIGNAL:
            self._handle_resource_health(signal)
            return
        try:
            event = SystemHealthEvent.from_signal_value(signal.value)
        except ValueError as exc:
            self.log.error(
                f"DISCORD_HEALTH_REJECTED | reason=invalid_event | error={type(exc).__name__}",
            )
            return
        if event.state not in _STATE_COLORS:
            self.log.warning(f"DISCORD_HEALTH_IGNORED | state={event.state}")
            return

        self._submit_operational_snapshot(self._operational_readiness.accept_system_health(event))

        delivery = DiscordDelivery(
            state=event.state,
            body=render_system_health_message(event, signal.ts_event),
        )
        if not self._worker.submit(delivery):
            self.log.error(f"DISCORD_HEALTH_DROPPED | state={event.state} | reason=queue_full")

    def on_stop(self) -> None:
        if self._subscribed:
            self.unsubscribe_signal(SYSTEM_HEALTH_SIGNAL)
            self.unsubscribe_signal(RUNTIME_RESOURCE_HEALTH_SIGNAL)
            if self._operational_worker is not None:
                self.unsubscribe_signal(WATCHLIST_MEMBERSHIP_SIGNAL)
                self.unsubscribe_signal(WATCHLIST_LIFECYCLE_SIGNAL)
                self.unsubscribe_signal(HISTORICAL_DEPENDENCY_DEMAND_SIGNAL)
                self.unsubscribe_signal(HISTORICAL_READINESS_SIGNAL)
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
        if self._operational_worker is not None and not self._operational_worker.close():
            self.log.error("DISCORD_OPERATIONAL_WORKER_TIMEOUT")

    def _drain_results(self, _event) -> None:  # noqa: ANN001
        self._drain_worker_results(self._worker, "DISCORD_HEALTH")
        self._drain_worker_results(self._operational_worker, "DISCORD_OPERATIONAL")

    def _drain_worker_results(
        self,
        worker: DiscordDeliveryWorker | None,
        label: str,
    ) -> None:
        if worker is None:
            return
        while True:
            try:
                result = worker.results.get_nowait()
            except Empty:
                return
            if result.delivered:
                self.log.info(f"{label}_DELIVERED | state={result.state} | status={result.status}")
            else:
                self.log.error(
                    f"{label}_DELIVERY_FAILED | state={result.state}"
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
        if self._operational_worker is not None:
            operational = self._operational_worker.snapshot()
            self.log.info(
                "DISCORD_OPERATIONAL_SUMMARY"
                f" | accepted={operational.accepted} | delivered={operational.delivered}"
                f" | failed={operational.failed} | rejected={operational.rejected}"
                f" | pending={operational.pending}",
            )

    def _handle_operational_readiness(self, signal: Signal) -> None:
        try:
            if signal.name == WATCHLIST_MEMBERSHIP_SIGNAL:
                snapshot = self._operational_readiness.accept_membership(
                    WatchlistMembershipEvent.from_signal_value(signal.value),
                )
            elif signal.name == WATCHLIST_LIFECYCLE_SIGNAL:
                snapshot = self._operational_readiness.accept_lifecycle(
                    WatchlistLifecycleEvent.from_signal_value(signal.value),
                )
            elif signal.name == HISTORICAL_DEPENDENCY_DEMAND_SIGNAL:
                snapshot = self._operational_readiness.accept_demand(
                    HistoricalDependencyDemandEvent.from_signal_value(signal.value),
                )
            else:
                snapshot = self._operational_readiness.accept_readiness(
                    HistoricalReadinessEvent.from_signal_value(signal.value),
                )
        except ValueError as exc:
            self.log.error(
                f"DISCORD_OPERATIONAL_REJECTED | signal={signal.name} | error={type(exc).__name__}",
            )
            return
        self._submit_operational_snapshot(snapshot)

    def _submit_operational_snapshot(
        self,
        snapshot: OperationalReadinessSnapshot | None,
    ) -> None:
        if snapshot is None or self._operational_worker is None:
            return
        state = "READY" if snapshot.is_ready else "DEGRADED"
        if not self._operational_worker.submit(
            DiscordDelivery(state=state, body=render_operational_readiness_message(snapshot)),
        ):
            self.log.error(
                f"DISCORD_OPERATIONAL_DROPPED | state={state} | reason=queue_full",
            )

    def _handle_resource_health(self, signal: Signal) -> None:
        assert self._worker is not None
        try:
            event = RuntimeResourceHealthEvent.from_signal_value(signal.value)
        except ValueError as exc:
            self.log.error(
                "DISCORD_RESOURCE_HEALTH_REJECTED"
                f" | reason=invalid_event | error={type(exc).__name__}",
            )
            return
        if not event.notification_eligible:
            self.log.info(
                f"DISCORD_RESOURCE_HEALTH_SUPPRESSED | state={event.state} | reason=cooldown",
            )
            return
        delivery = DiscordDelivery(
            state=f"RESOURCE_{event.state}",
            body=render_runtime_resource_health_message(
                event,
                signal.ts_event,
                ping_critical=(self._ping_critical_resource_alerts and event.state == "CRITICAL"),
            ),
        )
        if not self._worker.submit(delivery):
            self.log.error(
                f"DISCORD_RESOURCE_HEALTH_DROPPED | state={event.state} | reason=queue_full",
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


def render_runtime_resource_health_message(
    event: RuntimeResourceHealthEvent,
    ts_event: int,
    *,
    ping_critical: bool,
) -> bytes:
    state_label = "Recovered" if event.state == "NORMAL" else event.state.title()
    observations = []
    for reason in event.reason_codes:
        if reason == "resources_recovered":
            continue
        observed = event.observations.get(reason)
        threshold = event.thresholds.get(reason)
        observations.append(f"**{_display_name(reason)}:** {observed} (limit {threshold})")
    if not observations:
        observations.append("All monitored resources are within configured limits.")
    embed: dict[str, Any] = {
        "title": f"Markeitech V2 | Host Resources {state_label}",
        "description": "\n".join(observations),
        "color": _RESOURCE_STATE_COLORS[event.state],
        "fields": [
            {"name": "State", "value": event.state, "inline": True},
            {"name": "Previous", "value": event.previous_state, "inline": True},
            {"name": "Policy", "value": event.threshold_version, "inline": True},
        ],
        "footer": {"text": "Runtime resource health"},
    }
    if ts_event > 0:
        embed["timestamp"] = datetime.fromtimestamp(
            ts_event / 1_000_000_000,
            UTC,
        ).isoformat()
    payload: dict[str, Any] = {
        "allowed_mentions": {"parse": ["everyone"] if ping_critical else []},
        "embeds": [embed],
    }
    if ping_critical:
        payload["content"] = "@here"
    return json.dumps(payload, separators=(",", ":")).encode()


def render_operational_readiness_message(snapshot: OperationalReadinessSnapshot) -> bytes:
    state = "READY" if snapshot.is_ready else "DEGRADED"
    title = (
        "Markeitech V2 | Ready for Sir Loke"
        if snapshot.is_ready
        else "Markeitech V2 | Warmup Complete with Gaps"
    )
    historical_counts = " · ".join(
        f"{name.title()}: {count}" for name, count in snapshot.historical_state_counts.items()
    )
    embed: dict[str, Any] = {
        "title": title,
        "description": (
            "Initial historical warmup is complete and every configured watchlist instrument "
            "has been observed."
        ),
        "color": _STATE_COLORS[state],
        "fields": [
            {"name": "State", "value": state, "inline": True},
            {
                "name": "Watchlist",
                "value": (
                    f"{snapshot.observed_watchlist_count}/"
                    f"{snapshot.expected_watchlist_count} observed"
                ),
                "inline": True,
            },
            {
                "name": "Historical warmup",
                "value": (
                    f"{snapshot.historical_state_counts.get('READY', 0)}/"
                    f"{snapshot.historical_total} ready"
                ),
                "inline": True,
            },
            {"name": "Historical outcomes", "value": historical_counts},
            {"name": "System control", "value": snapshot.system_state, "inline": True},
        ],
        "footer": {"text": "Operational readiness · Evidence, not execution"},
    }
    if snapshot.completed_at_ns > 0:
        embed["timestamp"] = datetime.fromtimestamp(
            snapshot.completed_at_ns / 1_000_000_000,
            UTC,
        ).isoformat()
    return json.dumps(
        {"allowed_mentions": {"parse": []}, "embeds": [embed]},
        separators=(",", ":"),
    ).encode()


def _historical_key(
    event: HistoricalDependencyDemandEvent | HistoricalReadinessEvent,
) -> HistoricalDependencyKey:
    return (
        event.consumer_id,
        event.capability_id,
        event.capability_version,
        event.instrument_id,
        event.selector,
        event.window,
    )


def _display_name(value: str) -> str:
    return value.replace("_", " ").title()


def _with_wait_confirmation(webhook_url: str) -> str:
    parts = urlsplit(webhook_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["wait"] = "true"
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
