from __future__ import annotations

import json

from nautilus_trader.network import HttpResponse

from markeitech.system.discord import (
    DiscordDelivery,
    DiscordDeliveryWorker,
    render_system_health_message,
)
from markeitech.system.messages import SystemHealthEvent


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
