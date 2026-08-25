from __future__ import annotations

import json

from nautilus_trader.network import HttpResponse

from markeitech.acquisition import (
    HistoricalDependencyDemandEvent,
    HistoricalReadinessEvent,
)
from markeitech.system.discord import (
    DiscordDelivery,
    DiscordDeliveryWorker,
    OperationalReadinessProjection,
    OperationalReadinessSnapshot,
    render_operational_readiness_message,
    render_runtime_resource_health_message,
    render_system_health_message,
)
from markeitech.system.messages import (
    SystemHealthEvent,
    WatchlistLifecycleEvent,
    WatchlistMember,
    WatchlistMembershipEvent,
)
from markeitech.system.resource_contracts import RuntimeResourceHealthEvent


def test_renders_readable_health_embed_without_mentions() -> None:
    event = SystemHealthEvent(
        state="READY",
        reason="configured instrument definitions are available",
        source="SYSTEM-CONTROL",
        evidence={
            "available_instrument_count": 2,
            "expected_instrument_count": 2,
            "expected_instruments": "ESU6.CME,SPY.ARCA",
            "previous_state": "STARTING",
        },
    )

    payload = json.loads(render_system_health_message(event, 1_786_000_000_000_000_000))

    assert payload["allowed_mentions"] == {"parse": []}
    assert "content" not in payload
    embed = payload["embeds"][0]
    assert embed["title"] == "Markeitech V2 | READY"
    assert embed["description"] == "configured instrument definitions are available"
    assert {field["name"]: field["value"] for field in embed["fields"]} == {
        "State": "READY",
        "Instruments": "2/2",
        "Source": "SYSTEM-CONTROL",
        "Configured instruments": "ESU6.CME,SPY.ARCA",
        "Previous state": "STARTING",
    }


def test_renders_critical_resource_transition_with_explicit_here_ping() -> None:
    event = RuntimeResourceHealthEvent(
        event_id="runtime-resource-health:RESOURCE-HEALTH:1:CRITICAL",
        source="RESOURCE-HEALTH",
        observed_ts_ns=1,
        state="CRITICAL",
        previous_state="WARNING",
        reason_codes=("disk_free_percent",),
        observations={"disk_free_percent": 4.5},
        thresholds={"disk_free_percent": 5.0},
        notification_eligible=True,
        threshold_version="test-v1",
    )

    payload = json.loads(render_runtime_resource_health_message(event, 1, ping_critical=True))

    assert payload["content"] == "@here"
    assert payload["allowed_mentions"] == {"parse": ["everyone"]}
    assert payload["embeds"][0]["title"] == "Markeitech V2 | Host Resources Critical"
    assert "Disk Free Percent" in payload["embeds"][0]["description"]


def test_renders_resource_recovery_without_mentions() -> None:
    event = RuntimeResourceHealthEvent(
        event_id="runtime-resource-health:RESOURCE-HEALTH:2:NORMAL",
        source="RESOURCE-HEALTH",
        observed_ts_ns=2,
        state="NORMAL",
        previous_state="WARNING",
        reason_codes=("resources_recovered",),
        observations={"host_memory_available_percent": 40.0},
        thresholds={"host_memory_available_percent": 15.0},
        notification_eligible=True,
        threshold_version="test-v1",
    )

    payload = json.loads(render_runtime_resource_health_message(event, 2, ping_critical=False))

    assert "content" not in payload
    assert payload["allowed_mentions"] == {"parse": []}


def test_operational_readiness_waits_for_every_existing_evidence_source() -> None:
    projection = OperationalReadinessProjection()
    health = SystemHealthEvent(
        state="READY",
        reason="system ready",
        source="SYSTEM-CONTROL",
        evidence={},
    )
    membership = WatchlistMembershipEvent(
        event_id="watchlist-membership:1",
        membership_revision=1,
        source="WATCHLIST",
        reason="configured baseline established",
        members=(
            WatchlistMember(
                instrument_id="ESU6.CME",
                calendar_id="cme_equity",
                capabilities=("watchlist_last",),
                owner_ids=("config:system",),
            ),
            WatchlistMember(
                instrument_id="NQU6.CME",
                calendar_id="cme_equity",
                capabilities=("watchlist_last",),
                owner_ids=("config:system",),
            ),
        ),
    )
    demands = (_demand("ESU6.CME"), _demand("NQU6.CME"))

    assert projection.accept_system_health(health) is None
    assert projection.accept_membership(membership) is None
    assert projection.accept_lifecycle(_observed("ESU6.CME")) is None
    for demand in demands:
        assert projection.accept_demand(demand) is None
    assert projection.accept_readiness(_readiness("ESU6.CME", "READY", 10)) is None
    assert projection.accept_lifecycle(_observed("NQU6.CME")) is None

    snapshot = projection.accept_readiness(_readiness("NQU6.CME", "READY", 20))

    assert snapshot is not None
    assert snapshot.is_ready is True
    assert snapshot.expected_watchlist_count == 2
    assert snapshot.observed_watchlist_count == 2
    assert snapshot.historical_state_counts == {"READY": 2}
    assert snapshot.completed_at_ns == 20
    assert projection.accept_readiness(_readiness("NQU6.CME", "READY", 30)) is None


def test_renders_operational_readiness_without_mentions() -> None:
    snapshot = OperationalReadinessSnapshot(
        system_state="READY",
        observed_watchlist_count=18,
        expected_watchlist_count=18,
        historical_state_counts={"READY": 49},
        completed_at_ns=1_787_578_567_090_742_016,
    )

    payload = json.loads(render_operational_readiness_message(snapshot))

    assert payload["allowed_mentions"] == {"parse": []}
    assert "content" not in payload
    embed = payload["embeds"][0]
    assert embed["title"] == "Markeitech V2 | Ready for Sir Loke"
    assert {field["name"]: field["value"] for field in embed["fields"]} == {
        "State": "READY",
        "Watchlist": "18/18 observed",
        "Historical warmup": "49/49 ready",
        "Historical outcomes": "Ready: 49",
        "System control": "READY",
    }


def test_worker_preserves_order_and_reports_confirmed_delivery() -> None:
    calls: list[tuple[str, dict]] = []

    def post(url: str, **kwargs) -> HttpResponse:  # noqa: ANN003
        calls.append((url, kwargs))
        return HttpResponse(200, b"{}")

    worker = DiscordDeliveryWorker(
        "https://discord.test/api/webhooks/id/token?thread_id=42",
        1,
        post=post,
    )
    worker.start()
    assert worker.submit(DiscordDelivery(state="STARTING", body=b'{"sequence":1}'))
    assert worker.submit(DiscordDelivery(state="READY", body=b'{"sequence":2}'))
    assert worker.close()

    results = [worker.results.get_nowait(), worker.results.get_nowait()]
    assert [result.state for result in results] == ["STARTING", "READY"]
    assert all(result.delivered for result in results)
    assert all(result.status == 200 for result in results)
    assert [call[1]["body"] for call in calls] == [b'{"sequence":1}', b'{"sequence":2}']
    assert calls[0][0].endswith("?thread_id=42&wait=true")
    assert calls[0][1]["timeout_secs"] == 1
    stats = worker.snapshot()
    assert stats.accepted == 2
    assert stats.delivered == 2
    assert stats.failed == 0
    assert stats.rejected == 0
    assert stats.pending == 0


def test_worker_reports_sanitized_failure_without_webhook_url() -> None:
    def post(_url: str, **_kwargs) -> HttpResponse:  # noqa: ANN003
        raise RuntimeError("secret webhook URL would appear here")

    worker = DiscordDeliveryWorker(
        "https://discord.test/api/webhooks/id/very-secret-token",
        1,
        post=post,
    )
    worker.start()
    assert worker.submit(DiscordDelivery(state="FAILED", body=b"{}"))
    assert worker.close()

    result = worker.results.get_nowait()
    assert result.delivered is False
    assert result.error_code == "RuntimeError"
    assert "secret" not in repr(result)
    stats = worker.snapshot()
    assert stats.accepted == 1
    assert stats.delivered == 0
    assert stats.failed == 1
    assert stats.pending == 0


def test_worker_rejects_delivery_after_close_and_counts_it() -> None:
    worker = DiscordDeliveryWorker(
        "https://discord.test/api/webhooks/id/token",
        1,
        post=lambda *_args, **_kwargs: HttpResponse(200, b"{}"),
    )
    worker.start()
    assert worker.close()

    assert worker.submit(DiscordDelivery(state="READY", body=b"{}")) is False
    assert worker.snapshot().rejected == 1


def _demand(instrument_id: str) -> HistoricalDependencyDemandEvent:
    return HistoricalDependencyDemandEvent(
        demand_id=f"warmup:{instrument_id}",
        consumer_id="SESSION-METRICS",
        capability_id="session.baseline",
        capability_version=1,
        instrument_id=instrument_id,
        selector="1-MINUTE-LAST-EXTERNAL",
        window="recent_completed",
        minimum_observations=5,
        maximum_observations=10,
        priority=10,
        purpose="initial warmup",
        as_of_ns=1,
    )


def _readiness(
    instrument_id: str,
    state: str,
    completed_at_ns: int,
) -> HistoricalReadinessEvent:
    return HistoricalReadinessEvent(
        event_id=f"warmup:{instrument_id}:{state}",
        request_id=f"request:{instrument_id}",
        consumer_id="SESSION-METRICS",
        capability_id="session.baseline",
        capability_version=1,
        state=state,
        instrument_id=instrument_id,
        selector="1-MINUTE-LAST-EXTERNAL",
        window="recent_completed",
        minimum_observations=5,
        observed_count=10,
        completed_at_ns=completed_at_ns,
        source="DATA-ACQUISITION",
        reason="terminal",
    )


def _observed(instrument_id: str) -> WatchlistLifecycleEvent:
    return WatchlistLifecycleEvent(
        event_id=f"watchlist-observed:{instrument_id}",
        membership_revision=1,
        state="INSTRUMENT_OBSERVED",
        source="WATCHLIST",
        reason="all configured watchlist capabilities observed",
        instrument_id=instrument_id,
    )
