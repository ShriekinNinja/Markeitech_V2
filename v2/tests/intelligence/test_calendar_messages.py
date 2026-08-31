from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import date

import pytest

from markeitech.intelligence.calendar_messages import (
    CalendarCurrentState,
    CalendarDefinitionExpectation,
    CalendarProjectionFailure,
    CalendarProjectionRequest,
    CalendarProjectionResponse,
    CalendarStateSnapshotFailure,
    CalendarStateSnapshotRequest,
    CalendarStateSnapshotResponse,
    CalendarTransition,
    CalendarTransitionV2,
)
from tests.calendar_fixtures import canonical_calendar


def test_calendar_projection_request_and_response_are_typed_and_immutable() -> None:
    request = CalendarProjectionRequest(
        request_id="projection:test:1",
        requester="TEST-CONSUMER",
        calendar_ids=("cme_equity",),
        start_ns=1,
        end_ns=2,
        requested_ts_ns=3,
    )
    projection = canonical_calendar("cme_equity").projection(
        date(2026, 8, 24),
        date(2026, 8, 24),
    )
    response = CalendarProjectionResponse(
        request_id=request.request_id,
        requester=request.requester,
        source="SESSION-STATE",
        source_epoch="run:test",
        status="READY",
        requested_calendar_ids=("cme_equity",),
        projections=(projection,),
        unavailable_calendar_ids=(),
        failures=(),
        generated_ts_ns=4,
    )

    assert request.ts_event == request.ts_init == 3
    assert response.ts_event == response.ts_init == 4
    assert response.projections[0].definition_digest == projection.definition_digest
    with pytest.raises(FrozenInstanceError):
        request.requester = "CHANGED"  # type: ignore[misc]


def test_calendar_projection_contract_rejects_ambiguous_or_invalid_payloads() -> None:
    projection = canonical_calendar("cme_equity").projection(
        date(2026, 8, 24),
        date(2026, 8, 24),
    )

    with pytest.raises(ValueError, match="non-empty and unique"):
        CalendarProjectionRequest("id", "consumer", (), 1, 2, 1)
    with pytest.raises(ValueError, match="exactly one projection response outcome"):
        CalendarProjectionResponse(
            request_id="id",
            requester="consumer",
            source="SESSION-STATE",
            source_epoch="run:test",
            status="INCOMPLETE",
            requested_calendar_ids=("cme_equity",),
            projections=(projection,),
            unavailable_calendar_ids=("cme_equity",),
            failures=(),
            generated_ts_ns=4,
        )

    failure = CalendarProjectionFailure(
        calendar_id="cme_equity",
        code="projection_construction_failed",
        reason="canonical calendar projection construction failed",
        retryable=False,
    )
    failed = CalendarProjectionResponse(
        request_id="id",
        requester="consumer",
        source="SESSION-STATE",
        source_epoch="run:test",
        status="FAILED",
        requested_calendar_ids=("cme_equity",),
        projections=(),
        unavailable_calendar_ids=(),
        failures=(failure,),
        generated_ts_ns=4,
    )
    assert failed.schema_version == 2


def test_calendar_transition_exposes_explicit_state_and_lineage() -> None:
    projection = canonical_calendar("cme_equity").projection(
        date(2026, 8, 24),
        date(2026, 8, 24),
    )
    event = CalendarTransition(
        event_id="calendar:run:test:cme_equity:2",
        source="SESSION-STATE",
        source_epoch="run:test",
        calendar_id="cme_equity",
        schedule_version=projection.schedule_version,
        definition_version=projection.definition_version,
        definition_digest=projection.definition_digest,
        effective_from_ns=1,
        trade_date="2026-08-24",
        previous_trade_date="2026-08-24",
        phase_memberships=("GLOBEX",),
        previous_phase_memberships=(),
        market_state="OPEN",
        previous_market_state="CLOSED",
        segment_open_ns=2,
        segment_close_ns=10,
        next_transition_ns=10,
        effective_ts_ns=2,
        evaluated_ts_ns=3,
        published_ts_ns=4,
        revision=2,
        previous_revision=1,
        reason="calendar state changed",
    )

    assert event.is_open is True
    assert event.phase == "GLOBEX"
    assert event.ts_event == 2
    assert event.ts_init == 4


def _expectation(calendar_id: str = "cme_equity") -> CalendarDefinitionExpectation:
    return CalendarDefinitionExpectation(
        calendar_id=calendar_id,
        definition_version=1,
        definition_digest="a" * 64,
        definition_effective_from_ns=1,
    )


def _current_state(
    calendar_id: str = "cme_equity",
    *,
    evaluated_as_of_ns: int = 30,
) -> CalendarCurrentState:
    return CalendarCurrentState(
        calendar_id=calendar_id,
        schedule_version="schedule-v1",
        definition_version=1,
        definition_digest="a" * 64,
        definition_effective_from_ns=1,
        trade_date="2026-08-24",
        phase_memberships=("REGULAR",),
        market_state="OPEN",
        segment_open_ns=10,
        segment_close_ns=100,
        next_transition_ns=100,
        revision=2,
        previous_revision=1,
        last_transition_event_id=f"calendar:run:test:{calendar_id}:2",
        source="SESSION-STATE",
        source_epoch="run:test",
        state_effective_from_ns=10,
        state_revision_evaluated_as_of_ns=14,
        evaluated_as_of_ns=evaluated_as_of_ns,
        state_revision_published_ts_ns=15,
    )


def test_transition_v2_distinguishes_definition_boundary_state_boundary_and_owner_cut() -> None:
    event = CalendarTransitionV2(
        event_id="calendar:run:test:cme_equity:2",
        source="SESSION-STATE",
        source_epoch="run:test",
        calendar_id="cme_equity",
        schedule_version="schedule-v1",
        definition_version=1,
        definition_digest="a" * 64,
        definition_effective_from_ns=1,
        trade_date="2026-08-24",
        previous_trade_date="2026-08-24",
        phase_memberships=("REGULAR",),
        previous_phase_memberships=(),
        market_state="OPEN",
        previous_market_state="CLOSED",
        segment_open_ns=10,
        segment_close_ns=100,
        next_transition_ns=100,
        state_effective_from_ns=10,
        evaluated_as_of_ns=30,
        published_ts_ns=31,
        revision=2,
        previous_revision=1,
        reason="calendar state changed",
    )

    assert event.state_effective_from_ns < event.evaluated_as_of_ns
    assert event.ts_event == 10
    assert event.ts_init == 31
    with pytest.raises(ValueError, match="canonical ordering"):
        replace(event, state_effective_from_ns=32)


def test_snapshot_request_and_response_enforce_exact_population_and_one_owner_cut() -> None:
    request = CalendarStateSnapshotRequest(
        cycle_id="cycle:1",
        request_id="cycle:1:a1",
        attempt=1,
        requester="EVIDENCE-HEALTH",
        expected_source="SESSION-STATE",
        expected_source_epoch="run:test",
        calendar_expectations=(_expectation(),),
        requested_as_of_ns=20,
        requested_ts_ns=21,
        deadline_ts_ns=40,
        delivery_policy_version=1,
    )
    response = CalendarStateSnapshotResponse(
        cycle_id=request.cycle_id,
        request_id=request.request_id,
        attempt=request.attempt,
        requester=request.requester,
        source=request.expected_source,
        source_epoch=request.expected_source_epoch,
        status="READY",
        requested_calendar_ids=request.calendar_ids,
        states=(_current_state(),),
        failures=(),
        requested_as_of_ns=request.requested_as_of_ns,
        requested_ts_ns=request.requested_ts_ns,
        deadline_ts_ns=request.deadline_ts_ns,
        request_received_ts_ns=22,
        evaluated_as_of_ns=30,
        generated_ts_ns=31,
        published_ts_ns=32,
        delivery_policy_version=1,
    )

    assert request.ts_event == 21
    assert response.ts_event == 30
    assert response.ts_init == 32
    assert response.states[0].state_revision_published_ts_ns < response.evaluated_as_of_ns
    with pytest.raises(FrozenInstanceError):
        response.status = "FAILED"  # type: ignore[misc]
    with pytest.raises(ValueError, match="account for every requested calendar"):
        replace(response, states=(), failures=())
    with pytest.raises(ValueError, match="cannot follow response publication"):
        replace(
            response,
            states=(
                replace(
                    response.states[0],
                    state_revision_published_ts_ns=33,
                ),
            ),
        )
    with pytest.raises(ValueError, match="cannot precede revision evaluation"):
        replace(
            response.states[0],
            state_revision_evaluated_as_of_ns=31,
            state_revision_published_ts_ns=31,
        )


def test_snapshot_failure_derives_retry_and_overall_status() -> None:
    failure = CalendarStateSnapshotFailure(
        calendar_id="cme_equity",
        outcome="NOT_READY",
        code="source_not_ready",
        reason="calendar source is not ready",
        retryable=True,
        retry_at_ns=35,
    )
    response = CalendarStateSnapshotResponse(
        cycle_id="cycle:1",
        request_id="cycle:1:a1",
        attempt=1,
        requester="EVIDENCE-HEALTH",
        source="SESSION-STATE",
        source_epoch="run:test",
        status="NOT_READY",
        requested_calendar_ids=("cme_equity",),
        states=(),
        failures=(failure,),
        requested_as_of_ns=20,
        requested_ts_ns=21,
        deadline_ts_ns=40,
        request_received_ts_ns=22,
        evaluated_as_of_ns=30,
        generated_ts_ns=31,
        published_ts_ns=32,
        delivery_policy_version=1,
        retry_at_ns=35,
    )

    assert response.status == "NOT_READY"
    assert response.retry_at_ns == 35
    with pytest.raises(ValueError, match="derived as NOT_READY"):
        replace(response, status="FAILED")
    with pytest.raises(ValueError, match="present exactly"):
        replace(failure, retry_at_ns=None)
    with pytest.raises(ValueError, match="only not-ready or unavailable"):
        replace(failure, outcome="CONFLICT")
    with pytest.raises(ValueError, match="bounded retry information"):
        replace(failure, retryable=False, retry_at_ns=None)
