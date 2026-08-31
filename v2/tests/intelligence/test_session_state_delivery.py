from __future__ import annotations

from dataclasses import replace

from markeitech.intelligence.calendar_messages import (
    CalendarCurrentState,
    CalendarDefinitionExpectation,
    CalendarStateSnapshotFailure,
    CalendarStateSnapshotResponse,
    CalendarTransitionV2,
)
from markeitech.intelligence.session_state_delivery import (
    SessionStateDeliveryDisposition,
    SessionStateDeliveryPhase,
    SessionStateDeliveryPolicy,
    SessionStateDeliveryState,
    begin_session_state_retry,
    current_snapshot_request,
    observe_session_snapshot,
    observe_session_transition,
    schedule_session_state_retry,
    start_session_state_cycle,
    stop_session_state_delivery,
)


def _policy(
    *,
    attempts: int = 3,
    per_calendar: int = 4,
    total: int = 8,
) -> SessionStateDeliveryPolicy:
    return SessionStateDeliveryPolicy(
        policy_version=1,
        response_timeout_ns=10,
        maximum_attempts=attempts,
        retry_backoff_ns=2,
        maximum_elapsed_ns=50,
        maximum_buffered_transitions_per_calendar=per_calendar,
        maximum_total_buffered_transitions=total,
        boundary_delivery_grace_ns=2,
    )


def _expectation() -> CalendarDefinitionExpectation:
    return CalendarDefinitionExpectation(
        calendar_id="cme_equity",
        definition_version=1,
        definition_digest="a" * 64,
        definition_effective_from_ns=1,
    )


def _waiting(
    *,
    policy: SessionStateDeliveryPolicy | None = None,
) -> SessionStateDeliveryState:
    selected = policy or _policy()
    idle = SessionStateDeliveryState.idle(
        requester="EVIDENCE-HEALTH",
        expected_source="SESSION-STATE",
        expected_source_epoch="run:test",
        delivery_policy_version=1,
    )
    return start_session_state_cycle(
        idle,
        calendar_expectations=(_expectation(),),
        now_ns=10,
        policy=selected,
    )


def _transition(revision: int) -> CalendarTransitionV2:
    state_effective_from_ns = {2: 5, 3: 15, 4: 18}[revision]
    evaluated_as_of_ns = {2: 7, 3: 16, 4: 18}[revision]
    published_ts_ns = {2: 14, 3: 17, 4: 19}[revision]
    is_open = revision != 3
    return CalendarTransitionV2(
        event_id=f"calendar:run:test:cme_equity:{revision}",
        source="SESSION-STATE",
        source_epoch="run:test",
        calendar_id="cme_equity",
        schedule_version="schedule-v1",
        definition_version=1,
        definition_digest="a" * 64,
        definition_effective_from_ns=1,
        trade_date="2026-08-24",
        previous_trade_date="2026-08-24",
        phase_memberships=(("REGULAR",) if is_open else ()),
        previous_phase_memberships=(),
        market_state=("OPEN" if is_open else "CLOSED"),
        previous_market_state="CLOSED",
        segment_open_ns=(2 if is_open else None),
        segment_close_ns=(30 if is_open else None),
        next_transition_ns=30,
        state_effective_from_ns=state_effective_from_ns,
        evaluated_as_of_ns=evaluated_as_of_ns,
        published_ts_ns=published_ts_ns,
        revision=revision,
        previous_revision=revision - 1,
        reason="calendar state changed",
    )


def _state(revision: int = 2) -> CalendarCurrentState:
    event = _transition(revision)
    return CalendarCurrentState(
        calendar_id=event.calendar_id,
        schedule_version=event.schedule_version,
        definition_version=event.definition_version,
        definition_digest=event.definition_digest,
        definition_effective_from_ns=event.definition_effective_from_ns,
        trade_date=event.trade_date,
        phase_memberships=event.phase_memberships,
        market_state=event.market_state,
        segment_open_ns=event.segment_open_ns,
        segment_close_ns=event.segment_close_ns,
        next_transition_ns=event.next_transition_ns,
        revision=event.revision,
        previous_revision=event.previous_revision,
        last_transition_event_id=event.event_id,
        source=event.source,
        source_epoch=event.source_epoch,
        state_effective_from_ns=event.state_effective_from_ns,
        state_revision_evaluated_as_of_ns=event.evaluated_as_of_ns,
        evaluated_as_of_ns=12,
        state_revision_published_ts_ns=event.published_ts_ns,
    )


def _ready_response(waiting: SessionStateDeliveryState) -> CalendarStateSnapshotResponse:
    request = current_snapshot_request(waiting)
    return CalendarStateSnapshotResponse(
        cycle_id=request.cycle_id,
        request_id=request.request_id,
        attempt=request.attempt,
        requester=request.requester,
        source=request.expected_source,
        source_epoch=request.expected_source_epoch,
        status="READY",
        requested_calendar_ids=request.calendar_ids,
        states=(_state(),),
        failures=(),
        requested_as_of_ns=request.requested_as_of_ns,
        requested_ts_ns=request.requested_ts_ns,
        deadline_ts_ns=request.deadline_ts_ns,
        request_received_ts_ns=11,
        evaluated_as_of_ns=12,
        generated_ts_ns=13,
        published_ts_ns=14,
        delivery_policy_version=request.delivery_policy_version,
    )


def _live() -> SessionStateDeliveryState:
    waiting = _waiting()
    update = observe_session_snapshot(waiting, _ready_response(waiting), now_ns=14)
    assert update.state.phase is SessionStateDeliveryPhase.LIVE
    return update.state


def test_snapshot_reconciles_a_transition_buffered_before_response() -> None:
    waiting = _waiting()
    buffered = observe_session_transition(waiting, _transition(3), policy=_policy())
    accepted = observe_session_snapshot(
        buffered.state,
        _ready_response(waiting),
        now_ns=14,
    )

    assert buffered.disposition is SessionStateDeliveryDisposition.BUFFERED
    assert accepted.disposition is SessionStateDeliveryDisposition.ACCEPTED
    assert accepted.state.phase is SessionStateDeliveryPhase.LIVE
    assert accepted.state.watermarks[0].revision == 3
    assert accepted.state.buffered_transitions == ()


def test_duplicate_stale_and_equal_revision_conflict_do_not_reapply_state() -> None:
    live = _live()
    duplicate_snapshot = observe_session_snapshot(
        live,
        _ready_response(_waiting()),
        now_ns=14,
    )
    stale = observe_session_transition(
        live,
        replace(
            _transition(2),
            event_id="calendar:run:test:cme_equity:1",
            revision=1,
            previous_revision=None,
        ),
        policy=_policy(),
    )
    conflict = observe_session_transition(
        live,
        replace(_transition(2), market_state="CLOSED", phase_memberships=()),
        policy=_policy(),
    )

    assert duplicate_snapshot.disposition is SessionStateDeliveryDisposition.DUPLICATE
    assert stale.disposition is SessionStateDeliveryDisposition.STALE
    assert conflict.disposition is SessionStateDeliveryDisposition.CONFLICT
    assert conflict.state.phase is SessionStateDeliveryPhase.CONFLICT
    assert conflict.state.watermarks == live.watermarks


def test_revision_evaluation_lineage_conflict_is_terminal_for_the_run() -> None:
    live = _live()
    conflict = observe_session_transition(
        live,
        replace(_transition(2), evaluated_as_of_ns=8),
        policy=_policy(),
    )
    restarted = start_session_state_cycle(
        conflict.state,
        calendar_expectations=(_expectation(),),
        now_ns=15,
        policy=_policy(),
    )
    retry = schedule_session_state_retry(
        conflict.state,
        now_ns=15,
        policy=_policy(),
        code="conflict_retry",
    )

    assert conflict.disposition is SessionStateDeliveryDisposition.CONFLICT
    assert conflict.state.terminal_code == "event_identity_conflict"
    assert restarted is conflict.state
    assert retry.disposition is SessionStateDeliveryDisposition.IGNORED
    assert retry.state is conflict.state


def test_out_of_order_contiguous_transitions_converge_without_skipping_a_gap() -> None:
    live = _live()
    gap = observe_session_transition(live, _transition(4), policy=_policy())
    recovered = observe_session_transition(gap.state, _transition(3), policy=_policy())

    assert gap.disposition is SessionStateDeliveryDisposition.GAP
    assert gap.state.phase is SessionStateDeliveryPhase.DEGRADED
    assert gap.state.watermarks[0].revision == 2
    assert recovered.disposition is SessionStateDeliveryDisposition.APPLIED
    assert recovered.state.phase is SessionStateDeliveryPhase.LIVE
    assert recovered.state.watermarks[0].revision == 4
    assert recovered.state.buffered_transitions == ()


def test_definition_source_and_capacity_fail_closed_without_dropping_buffered_data() -> None:
    waiting = _waiting(policy=_policy(per_calendar=1, total=1))
    buffered = observe_session_transition(
        waiting,
        _transition(3),
        policy=_policy(per_calendar=1, total=1),
    )
    overflow = observe_session_transition(
        buffered.state,
        _transition(4),
        policy=_policy(per_calendar=1, total=1),
    )
    wrong_source = observe_session_transition(
        waiting,
        replace(_transition(3), source_epoch="run:other"),
        policy=_policy(per_calendar=1, total=1),
    )

    assert overflow.disposition is SessionStateDeliveryDisposition.OVERFLOW
    assert overflow.state.phase is SessionStateDeliveryPhase.DEGRADED
    assert overflow.state.terminal_code == "buffer_overflow"
    assert overflow.state.buffered_transitions == buffered.state.buffered_transitions
    assert wrong_source.disposition is SessionStateDeliveryDisposition.CONFLICT
    assert wrong_source.state.terminal_code == "source_identity_conflict"


def test_retry_is_bounded_keeps_cycle_identity_and_uses_a_new_attempt_identity() -> None:
    first = _waiting(policy=_policy(attempts=2))
    backoff = schedule_session_state_retry(
        first,
        now_ns=20,
        policy=_policy(attempts=2),
    )
    second = begin_session_state_retry(
        backoff.state,
        now_ns=22,
        policy=_policy(attempts=2),
    )
    exhausted = schedule_session_state_retry(
        second.state,
        now_ns=32,
        policy=_policy(attempts=2),
    )

    assert backoff.disposition is SessionStateDeliveryDisposition.RETRY_SCHEDULED
    assert second.disposition is SessionStateDeliveryDisposition.RETRY_STARTED
    assert second.state.cycle_id == first.cycle_id
    assert second.state.request_id != first.request_id
    assert second.state.attempt == 2
    assert exhausted.disposition is SessionStateDeliveryDisposition.EXHAUSTED
    assert exhausted.state.terminal_code == "attempts_exhausted"


def test_response_observed_after_the_attempt_deadline_is_stale() -> None:
    waiting = _waiting()
    response = _ready_response(waiting)

    update = observe_session_snapshot(waiting, response, now_ns=21)

    assert response.published_ts_ns < response.deadline_ts_ns
    assert update.disposition is SessionStateDeliveryDisposition.STALE
    assert update.state is waiting


def test_non_retryable_snapshot_failure_cannot_enter_backoff() -> None:
    waiting = _waiting()
    request = current_snapshot_request(waiting)
    failure = CalendarStateSnapshotFailure(
        calendar_id="cme_equity",
        outcome="EVALUATION_FAILED",
        code="current_state_evaluation_failed",
        reason="current state evaluation failed",
        retryable=False,
    )
    response = CalendarStateSnapshotResponse(
        cycle_id=request.cycle_id,
        request_id=request.request_id,
        attempt=request.attempt,
        requester=request.requester,
        source=request.expected_source,
        source_epoch=request.expected_source_epoch,
        status="FAILED",
        requested_calendar_ids=request.calendar_ids,
        states=(),
        failures=(failure,),
        requested_as_of_ns=request.requested_as_of_ns,
        requested_ts_ns=request.requested_ts_ns,
        deadline_ts_ns=request.deadline_ts_ns,
        request_received_ts_ns=11,
        evaluated_as_of_ns=12,
        generated_ts_ns=13,
        published_ts_ns=14,
        delivery_policy_version=request.delivery_policy_version,
    )
    accepted = observe_session_snapshot(waiting, response, now_ns=14)
    retry = schedule_session_state_retry(
        accepted.state,
        now_ns=14,
        policy=_policy(),
        code="snapshot_failure",
    )
    restarted = start_session_state_cycle(
        accepted.state,
        calendar_expectations=(_expectation(),),
        now_ns=15,
        policy=_policy(),
    )

    assert accepted.state.phase is SessionStateDeliveryPhase.DEGRADED
    assert accepted.state.terminal_code == "current_state_evaluation_failed"
    assert retry.disposition is SessionStateDeliveryDisposition.IGNORED
    assert retry.state is accepted.state
    assert restarted is accepted.state


def test_stopped_state_absorbs_late_transition_response_and_retry() -> None:
    waiting = _waiting()
    response = _ready_response(waiting)
    stopped = stop_session_state_delivery(waiting)

    transition = observe_session_transition(stopped, _transition(3), policy=_policy())
    snapshot = observe_session_snapshot(stopped, response, now_ns=21)
    retry = schedule_session_state_retry(stopped, now_ns=20, policy=_policy())

    assert stopped.phase is SessionStateDeliveryPhase.STOPPED
    assert stopped.buffered_transitions == ()
    assert transition.disposition is SessionStateDeliveryDisposition.STOPPED
    assert snapshot.disposition is SessionStateDeliveryDisposition.STOPPED
    assert retry.disposition is SessionStateDeliveryDisposition.STOPPED
    assert transition.state == snapshot.state == retry.state == stopped
