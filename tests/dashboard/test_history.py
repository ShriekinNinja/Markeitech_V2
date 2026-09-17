from dataclasses import asdict
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from nautilus_trader.model import Bar, BarType

from markeitech.acquisition import HistoricalDependencyCompiler, HistoricalResourcePolicy
from markeitech.acquisition.dashboard_history import (
    DashboardHistoryRequest,
    project_history_page,
)
from markeitech.dashboard.actor import DashboardActor, DashboardActorConfig
from markeitech.dashboard.config import DashboardConfig
from markeitech.dashboard.server import DashboardServer
from markeitech.dashboard.state import DashboardState
from markeitech.system.historical_planner import compile_historical_demand
from tests.dashboard.test_dashboard import ID, MEMBERS, bar

START = 1_700_000_040
SECOND = 1_000_000_000


def request(minutes=2):  # noqa: ANN001, ANN201
    return DashboardHistoryRequest(str(uuid4()), ID, START, START + minutes * 60)


def batch(command, observations):  # noqa: ANN001, ANN201
    compiler = HistoricalDependencyCompiler(HistoricalResourcePolicy(4, 5000, 20000))
    return SimpleNamespace(
        request=compile_historical_demand(command.demand(), compiler), observations=observations
    )


def server(capacity=2):  # noqa: ANN001, ANN201
    config = DashboardConfig(maximum_history_requests=capacity)
    display = DashboardState(config)
    display.set_members(MEMBERS)
    return DashboardServer(config, display.snapshot())


def test_operator_window_compiles_to_exact_native_bounds_and_unique_correlation() -> None:
    command = request()
    compiled = batch(command, ()).request
    assert compiled.start_ns == START * SECOND
    assert compiled.end_ns == (START + 120) * SECOND - 1
    assert compiled.limit == 2
    assert compiled.selector == "1-MINUTE-LAST-EXTERNAL"
    assert compiled.dependencies[0].consumer_id == command.consumer_id
    with pytest.raises(ValueError):
        DashboardHistoryRequest(str(uuid4()), ID, START + 1, START + 120)
    with pytest.raises(ValueError):
        request(1001)


def test_acquisition_page_uses_only_its_window_and_does_not_invent_missing_inputs() -> None:
    command = request()
    # Only one of two provider intervals exists. Do not fabricate the absent candle.
    source = bar((START + 60) * SECOND)
    observation = Bar(
        BarType.from_str(f"{ID}-1-MINUTE-LAST-EXTERNAL"),
        source.open,
        source.high,
        source.low,
        source.close,
        source.volume,
        source.ts_event,
        source.ts_init,
    )
    page = project_history_page(batch(command, [observation]), command.consumer_id, 10)
    assert [c.time for c in page.candles] == [START]
    assert page.candles[0].volume == str(source.volume)
    assert page.candles[0].status == "COMPLETE"
    assert page.candles[0].historical_inputs == 1
    assert page.candles[0].provenance == "provider_history"
    assert page.candles[0].selector == "1-MINUTE-LAST-EXTERNAL"
    empty = project_history_page(batch(command, ()), command.consumer_id, 11)
    assert empty.candles == ()


def test_http_history_admission_is_bounded_same_origin_and_retains_unread_results() -> None:
    worker = server(1)
    command = request()
    payload = {k: v for k, v in asdict(command).items() if k != "request_id"}
    with TestClient(worker.app, base_url="http://127.0.0.1:8765") as client:
        assert (
            client.post(
                "/api/history", json=payload, headers={"Origin": "http://evil.invalid"}
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/history", content="x" * 1025, headers={"Content-Type": "application/json"}
            ).status_code
            == 413
        )
        assert (
            client.post("/api/history", json={**payload, "instrument_id": "BAD.CME"}).status_code
            == 404
        )
        assert (
            client.post("/api/history", json={**payload, "end": START + 201 * 60}).status_code
            == 422
        )
        response = client.post("/api/history", json=payload)
        assert response.status_code == 202
        job = response.json()
        assert client.post("/api/history", json=payload).json()["request_id"] == job["request_id"]
        queued = worker.take_history_requests()
        assert len(queued) == 1
        later = {**payload, "start": START + 60, "end": START + 180}
        assert client.post("/api/history", json=later).status_code == 429
        worker.finish_history(
            {"request_id": job["request_id"], "status": "COMPLETED", "candles": []}
        )
        # A new client cannot discard a result its requester has not fetched yet.
        assert client.post("/api/history", json=later).status_code == 429
        result = client.get(f"/api/history/{job['request_id']}")
        assert result.json()["status"] == "COMPLETED"
        assert client.post("/api/history", json=later).status_code == 202


def test_dashboard_routes_only_matching_acquisition_pages_to_the_web_mailbox() -> None:
    actor = DashboardActor(DashboardActorConfig(dashboard=asdict(DashboardConfig())))
    actor._active = True
    command = request()
    actor._page_requests[command.consumer_id] = (command, 1, True)
    wrong = request()
    actor.on_data(project_history_page(batch(wrong, ()), wrong.consumer_id, 2))
    assert command.consumer_id in actor._page_requests
    page = project_history_page(batch(command, ()), command.consumer_id, 2)
    actor.on_data(page)
    assert not actor._page_requests
    result = actor._server._history_results.get_nowait()
    assert result["request_id"] == command.request_id and result["candles"] == ()
    assert result["status"] == "COMPLETED"


def test_history_session_budget_bounds_executor_metadata_after_results_are_consumed() -> None:
    from dataclasses import replace

    worker = server(1)
    worker.config = replace(worker.config, maximum_history_requests_per_session=1)
    command = request()
    payload = {k: v for k, v in asdict(command).items() if k != "request_id"}
    with TestClient(worker.app, base_url="http://127.0.0.1:8765") as client:
        job = client.post("/api/history", json=payload).json()
        worker.take_history_requests()
        worker.finish_history(
            {"request_id": job["request_id"], "status": "COMPLETED", "candles": []}
        )
        assert client.get(f"/api/history/{job['request_id']}").json()["status"] == "COMPLETED"
        result = client.post("/api/history", json={**payload, "end": START + 180})
        assert result.status_code == 429 and "session budget" in result.json()["detail"]


def test_expired_web_requests_never_reach_provider_demand(monkeypatch) -> None:
    clock = [10.0]
    monkeypatch.setattr("markeitech.dashboard.server.monotonic", lambda: clock[0])
    worker = server()
    command = request()
    payload = {k: v for k, v in asdict(command).items() if k != "request_id"}
    with TestClient(worker.app, base_url="http://127.0.0.1:8765") as client:
        job = client.post("/api/history", json=payload).json()
        clock[0] += worker.config.history_request_timeout_seconds + 1
        assert worker.take_history_requests() == ()
        assert client.get(f"/api/history/{job['request_id']}").status_code == 404


def test_repeated_window_has_fresh_execution_identity_but_retries_keep_the_same_id() -> None:
    first = request()
    second = request()
    initial = batch(first, ()).request
    retried = batch(first, ()).request
    repeated = batch(second, ()).request
    assert initial.request_key == repeated.request_key
    assert initial.request_id == retried.request_id
    assert initial.request_id != repeated.request_id
    assert initial.dependencies[0].consumer_id == first.consumer_id
    assert repeated.dependencies[0].consumer_id == second.consumer_id


def test_completed_window_can_be_fetched_again_through_existing_executor() -> None:
    from tests.acquisition.test_historical_execution import RecordingHistoricalPort, _coordinator

    port = RecordingHistoricalPort()
    executor = _coordinator(port)
    first, second = batch(request(), ()).request, batch(request(), ()).request
    executor.enqueue((first,), now_ns=1)
    executor.complete(first.request_id, (), now_ns=2)
    executor.enqueue((second,), now_ns=3)
    assert port.submitted == [first.request_id, second.request_id]
    assert executor.active_request_ids == (second.request_id,)
