from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from markeitech.intelligence.calendar_messages import (
    CalendarProjectionRequest,
    CalendarProjectionResponse,
    CalendarTransition,
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
        projections=(projection,),
        unavailable_calendar_ids=(),
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
    with pytest.raises(ValueError, match="both projected and unavailable"):
        CalendarProjectionResponse(
            request_id="id",
            requester="consumer",
            source="SESSION-STATE",
            source_epoch="run:test",
            status="INCOMPLETE",
            projections=(projection,),
            unavailable_calendar_ids=("cme_equity",),
            generated_ts_ns=4,
        )


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
