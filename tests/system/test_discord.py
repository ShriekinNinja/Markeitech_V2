from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from nautilus_trader.common import Signal
from requests import Response

from markeitech.system.discord import (
    DiscordDelivery,
    DiscordDeliveryWorker,
    DiscordWebhooksActor,
    render_runtime_resource_health_message,
    render_system_health_message,
)
from markeitech.system.messages import (
    SYSTEM_HEALTH_SIGNAL,
    SystemHealthEvent,
)
from markeitech.system.resource_contracts import RuntimeResourceHealthEvent


@pytest.mark.parametrize(
    ("name", "rejected"),
    [
        ("markeitech.watchlist.membership.request", False),
        ("markeitech.system.health.request", False),
        (SYSTEM_HEALTH_SIGNAL, True),
    ],
)
def test_discord_validates_only_exact_health_signal(name, rejected) -> None:
    errors = []
    actor = SimpleNamespace(_worker=object(), log=SimpleNamespace(error=errors.append))
    DiscordWebhooksActor.on_signal(actor, Signal(name, "not-json", 1, 1))
    assert bool(errors) is rejected


def test_renders_readable_health_embed_without_mentions() -> None:
    event = SystemHealthEvent(
        state="READY",
        reason="operational prerequisites are ready",
        source="SYSTEM-CONTROL",
        evidence={
            "previous_state": "STARTING",
        },
    )

    payload = json.loads(render_system_health_message(event, 1_786_000_000_000_000_000))

    assert payload["allowed_mentions"] == {"parse": []}
    assert "content" not in payload
    embed = payload["embeds"][0]
    assert embed["title"] == "Markeitech V2 | READY"
    assert embed["description"] == "operational prerequisites are ready"
    assert {field["name"]: field["value"] for field in embed["fields"]} == {
        "State": "READY",
        "Source": "SYSTEM-CONTROL",
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


def test_worker_preserves_order_and_reports_confirmed_delivery() -> None:
    calls: list[tuple[str, dict]] = []

    def post(url: str, **kwargs) -> Response:  # noqa: ANN003
        calls.append((url, kwargs))
        return _response(200)

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
    assert [call[1]["data"] for call in calls] == [b'{"sequence":1}', b'{"sequence":2}']
    assert calls[0][0].endswith("?thread_id=42&wait=true")
    assert calls[0][1]["headers"] == {"Content-Type": "application/json"}
    assert calls[0][1]["timeout"] == 1
    stats = worker.snapshot()
    assert stats.accepted == 2
    assert stats.delivered == 2
    assert stats.failed == 0
    assert stats.rejected == 0
    assert stats.pending == 0


def test_worker_reports_sanitized_failure_without_webhook_url() -> None:
    def post(_url: str, **_kwargs) -> Response:  # noqa: ANN003
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
        post=lambda *_args, **_kwargs: _response(200),
    )
    worker.start()
    assert worker.close()

    assert worker.submit(DiscordDelivery(state="READY", body=b"{}")) is False
    assert worker.snapshot().rejected == 1


def _response(status_code: int) -> Response:
    response = Response()
    response.status_code = status_code
    return response
