from __future__ import annotations

from types import MappingProxyType

import pytest

from markeitech.acquisition import (
    FeedKind,
    HistoricalBatch,
    HistoricalDependencyRef,
    HistoricalDependencyResult,
    HistoricalExecutionCoordinator,
    HistoricalExecutionError,
    HistoricalExecutionPolicy,
    HistoricalExecutionState,
    HistoricalReadinessState,
    HistoricalRequest,
    HistoricalWindow,
)


class RecordingHistoricalPort:
    def __init__(self) -> None:
        self.submitted: list[str] = []
        self.canceled: list[str] = []
        self.fail_submissions = 0

    provider_id = "IB"
    adapter_id = "nautilus-ib"
    source_stream_id = "historical-bars"
    source_schema_id = "nautilus.bar.v1"

    def submit(self, request: HistoricalRequest) -> None:
        self.submitted.append(request.request_id)
        if self.fail_submissions > 0:
            self.fail_submissions -= 1
            raise RuntimeError("provider unavailable")

    def cancel(self, request: HistoricalRequest) -> None:
        self.canceled.append(request.request_id)


def _dependency(consumer: str, minimum: int) -> HistoricalDependencyRef:
    return HistoricalDependencyRef(
        consumer_id=consumer,
        capability_id="test-capability",
        capability_version=1,
        requirement_index=0,
        minimum_observations=minimum,
        purpose="test historical execution",
    )


def _request(
    request_id: str,
    *,
    priority: int = 50,
    dependencies: tuple[HistoricalDependencyRef, ...] | None = None,
) -> HistoricalRequest:
    return HistoricalRequest(
        request_id=request_id,
        instrument_id="ESU6.CME",
        kind=FeedKind.BARS,
        selector="1-MINUTE-LAST-EXTERNAL",
        window=HistoricalWindow.RECENT_COMPLETED,
        start_ns=100,
        end_ns=200,
        limit=100,
        priority=priority,
        parameters=MappingProxyType({}),
        dependencies=dependencies or (_dependency("metric:test", 2),),
    )


def _coordinator(
    port: RecordingHistoricalPort,
    **overrides: int,
) -> HistoricalExecutionCoordinator:
    values = {
        "maximum_queued_requests": 10,
        "maximum_in_flight_requests": 1,
        "timeout_ns": 100,
        "maximum_attempts": 2,
        "retry_backoff_ns": 10,
    }
    values.update(overrides)
    return HistoricalExecutionCoordinator(port, HistoricalExecutionPolicy(**values))


def test_single_lane_queues_by_priority_and_dispatches_after_completion() -> None:
    port = RecordingHistoricalPort()
    coordinator = _coordinator(port)
    low = _request("low", priority=10)
    high = _request("high", priority=90)

    update = coordinator.enqueue((low, high), now_ns=1)

    assert [event.state for event in update.events] == [
        HistoricalExecutionState.QUEUED,
        HistoricalExecutionState.QUEUED,
        HistoricalExecutionState.SUBMITTED,
    ]
    assert all(event.detail for event in update.events)
    assert port.submitted == ["high"]
    assert coordinator.pending_request_ids == ("low",)
    assert coordinator.active_request_ids == ("high",)

    completed = coordinator.complete("high", ("bar-1", "bar-2"), now_ns=2)

    assert [event.state for event in completed.events] == [
        HistoricalExecutionState.COMPLETED,
        HistoricalExecutionState.SUBMITTED,
    ]
    assert port.submitted == ["high", "low"]


def test_completion_fans_out_one_batch_with_independent_readiness() -> None:
    port = RecordingHistoricalPort()
    coordinator = _coordinator(port)
    request = _request(
        "shared",
        dependencies=(_dependency("metric:a", 2), _dependency("metric:b", 4)),
    )
    coordinator.enqueue((request,), now_ns=1)

    update = coordinator.complete("shared", ("a", "b", "c"), now_ns=5)

    assert update.batches == (
        HistoricalBatch(
            request,
            ("a", "b", "c"),
            5,
            "IB",
            "nautilus-ib",
            "historical-bars",
            "nautilus.bar.v1",
        ),
    )
    assert tuple((result.dependency.consumer_id, result.state) for result in update.results) == (
        ("metric:a", HistoricalReadinessState.READY),
        ("metric:b", HistoricalReadinessState.DEGRADED),
    )


def test_completion_uses_authority_snapshotted_before_request_lifecycle() -> None:
    port = RecordingHistoricalPort()
    coordinator = _coordinator(port)
    request = _request("snapshotted")
    coordinator.enqueue((request,), now_ns=1)
    port.provider_id = "MUTATED-AFTER-SUBMISSION"
    port.adapter_id = "mutated-adapter"
    port.source_stream_id = "mutated-stream"
    port.source_schema_id = "mutated.schema.v1"

    update = coordinator.complete("snapshotted", ("a", "b"), now_ns=2)

    batch = update.batches[0]
    assert (
        batch.provider_id,
        batch.adapter_id,
        batch.source_stream_id,
        batch.source_schema_id,
    ) == ("IB", "nautilus-ib", "historical-bars", "nautilus.bar.v1")


def test_identical_active_requests_share_provider_call_and_merge_consumers() -> None:
    port = RecordingHistoricalPort()
    coordinator = _coordinator(port)
    first = _request("shared", dependencies=(_dependency("metric:a", 2),))
    second = _request("shared", dependencies=(_dependency("metric:b", 4),))

    coordinator.enqueue((first,), now_ns=1)
    shared = coordinator.enqueue((second,), now_ns=2)
    completed = coordinator.complete("shared", ("a", "b", "c"), now_ns=3)

    assert port.submitted == ["shared"]
    assert [event.state for event in shared.events] == [HistoricalExecutionState.SHARED]
    assert tuple(result.dependency.consumer_id for result in completed.results) == (
        "metric:a",
        "metric:b",
    )
    assert tuple(result.state for result in completed.results) == (
        HistoricalReadinessState.READY,
        HistoricalReadinessState.DEGRADED,
    )


def test_submission_failure_retries_after_backoff_without_blocking_queue() -> None:
    port = RecordingHistoricalPort()
    port.fail_submissions = 1
    coordinator = _coordinator(port)
    first = _request("first", priority=90)
    second = _request("second", priority=20)

    update = coordinator.enqueue((first, second), now_ns=1)

    assert [event.state for event in update.events] == [
        HistoricalExecutionState.QUEUED,
        HistoricalExecutionState.QUEUED,
        HistoricalExecutionState.RETRY_SCHEDULED,
        HistoricalExecutionState.SUBMITTED,
    ]
    assert coordinator.active_request_ids == ("second",)
    assert coordinator.pending_request_ids == ("first",)

    coordinator.complete("second", ("bar", "bar"), now_ns=2)
    retried = coordinator.advance(now_ns=11)

    assert [event.state for event in retried.events] == [HistoricalExecutionState.SUBMITTED]
    assert retried.events[0].attempt == 2


def test_timeout_retries_then_expires_only_affected_request() -> None:
    port = RecordingHistoricalPort()
    coordinator = _coordinator(port, maximum_attempts=2)
    coordinator.enqueue((_request("timed"),), now_ns=0)

    first_timeout = coordinator.advance(now_ns=100)
    retry = coordinator.advance(now_ns=110)
    final_timeout = coordinator.advance(now_ns=210)

    assert first_timeout.events[0].state is HistoricalExecutionState.RETRY_SCHEDULED
    assert retry.events[0].state is HistoricalExecutionState.SUBMITTED
    assert final_timeout.events[0].state is HistoricalExecutionState.EXPIRED
    assert final_timeout.results[0].state is HistoricalReadinessState.EXPIRED
    assert port.canceled == ["timed", "timed"]


def test_cancel_pending_and_active_publish_terminal_consumer_results() -> None:
    port = RecordingHistoricalPort()
    coordinator = _coordinator(port)
    coordinator.enqueue((_request("active"), _request("pending")), now_ns=1)

    pending = coordinator.cancel("pending", now_ns=2)
    active = coordinator.cancel("active", now_ns=3)

    assert pending.events[0].state is HistoricalExecutionState.CANCELED
    assert pending.results[0].state is HistoricalReadinessState.CANCELED
    assert active.events[0].state is HistoricalExecutionState.CANCELED
    assert active.results[0].state is HistoricalReadinessState.CANCELED
    assert port.canceled == ["active"]


def test_non_retryable_failure_is_terminal() -> None:
    port = RecordingHistoricalPort()
    coordinator = _coordinator(port)
    coordinator.enqueue((_request("failed"),), now_ns=1)

    update = coordinator.fail("failed", "provider rejected request", now_ns=2, retryable=False)

    assert update.events[0].state is HistoricalExecutionState.FAILED
    assert update.results == (
        HistoricalDependencyResult(
            request_id="failed",
            dependency=_dependency("metric:test", 2),
            state=HistoricalReadinessState.FAILED,
            observed_count=0,
            completed_at_ns=2,
            reason="provider rejected request",
        ),
    )


def test_duplicate_active_enqueue_is_idempotent_but_terminal_reuse_is_rejected() -> None:
    port = RecordingHistoricalPort()
    coordinator = _coordinator(port)
    request = _request("stable")

    coordinator.enqueue((request,), now_ns=1)
    duplicate = coordinator.enqueue((request,), now_ns=2)
    coordinator.complete("stable", ("a", "b"), now_ns=3)

    assert duplicate.events == ()
    with pytest.raises(HistoricalExecutionError, match="terminal historical request"):
        coordinator.enqueue((request,), now_ns=4)
