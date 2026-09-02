from __future__ import annotations

from dataclasses import replace

from markeitech.intelligence.calendar_delivery import (
    ProjectionRequestPhase,
    ProjectionRequestState,
    ProjectionRetryPolicy,
    begin_projection_retry,
    classify_projection_response,
    ready_projection_state,
    schedule_projection_retry,
    start_projection_cycle,
    stop_projection_state,
)
from markeitech.intelligence.calendar_messages import CalendarProjectionResponse


def _policy(*, attempts: int = 3) -> ProjectionRetryPolicy:
    return ProjectionRetryPolicy(
        response_timeout_ns=5,
        retry_backoff_ns=2,
        maximum_attempts=attempts,
        maximum_elapsed_ns=30,
    )


def _idle() -> ProjectionRequestState:
    return ProjectionRequestState.idle(
        requester="TEST-CONSUMER",
        expected_source="SESSION-STATE",
        expected_source_epoch="run:test",
    )


def _waiting() -> ProjectionRequestState:
    return start_projection_cycle(
        _idle(),
        calendar_ids=("cme_equity",),
        start_ns=1,
        end_ns=10,
        now_ns=10,
        policy=_policy(),
    )


def _not_ready(state: ProjectionRequestState, *, request_id: str | None = None):  # noqa: ANN202
    return CalendarProjectionResponse(
        request_id=request_id or str(state.request_id),
        requester=state.requester,
        source=state.expected_source,
        source_epoch=state.expected_source_epoch,
        status="NOT_READY",
        requested_calendar_ids=state.pending_calendar_ids,
        projections=(),
        unavailable_calendar_ids=state.pending_calendar_ids,
        failures=(),
        generated_ts_ns=11,
        retry_at_ns=13,
    )


def test_projection_cycle_has_one_correlated_outstanding_attempt() -> None:
    state = _waiting()

    repeated = start_projection_cycle(
        state,
        calendar_ids=("cme_equity",),
        start_ns=1,
        end_ns=10,
        now_ns=11,
        policy=_policy(),
    )

    assert repeated is state
    assert state.phase is ProjectionRequestPhase.WAITING
    assert state.attempt == 1
    assert state.request_id is not None
    assert classify_projection_response(state, _not_ready(state)) == "ACCEPT"
    assert classify_projection_response(state, _not_ready(state, request_id="stale")) == "STALE"
    assert (
        classify_projection_response(
            state,
            replace(_not_ready(state), source_epoch="old-run"),
        )
        == "CONFLICT"
    )


def test_timeout_and_not_ready_retry_are_bounded_and_get_new_request_ids() -> None:
    first = _waiting()
    backoff = schedule_projection_retry(
        first,
        now_ns=15,
        policy=_policy(),
        retry_at_ns=18,
    )
    second = begin_projection_retry(backoff, now_ns=18, policy=_policy())

    assert backoff.phase is ProjectionRequestPhase.BACKOFF
    assert backoff.alert_at_ns == 18
    assert second.phase is ProjectionRequestPhase.WAITING
    assert second.attempt == 2
    assert second.request_id != first.request_id

    final_backoff = schedule_projection_retry(
        second,
        now_ns=23,
        policy=_policy(attempts=2),
        retry_at_ns=None,
    )
    assert final_backoff.phase is ProjectionRequestPhase.FAILED
    assert final_backoff.terminal_code == "attempts_exhausted"
    assert final_backoff.alert_at_ns is None


def test_retry_at_beyond_elapsed_budget_fails_instead_of_retrying_early() -> None:
    state = _waiting()

    exhausted = schedule_projection_retry(
        state,
        now_ns=15,
        policy=_policy(),
        retry_at_ns=36,
    )

    assert exhausted.phase is ProjectionRequestPhase.FAILED
    assert exhausted.terminal_code == "elapsed_budget_exhausted"


def test_ready_and_stopped_states_absorb_late_responses() -> None:
    waiting = _waiting()
    response = _not_ready(waiting)
    ready = ready_projection_state(waiting)
    stopped = stop_projection_state(waiting)

    assert classify_projection_response(ready, response) == "DUPLICATE"
    assert classify_projection_response(stopped, response) == "DUPLICATE"
    assert stop_projection_state(stopped) == stopped
