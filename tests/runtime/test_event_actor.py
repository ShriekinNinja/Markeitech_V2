from datetime import UTC, datetime

from markeitech.runtime.actor import (
    BoundedEventIdentityWindow,
    render_context_transition_notice,
)
from markeitech.runtime.events import (
    CommittedContextTransitionNotice,
    MarkeitechBusTopic,
)


def test_identity_window_suppresses_duplicates_and_bounds_memory() -> None:
    identities = BoundedEventIdentityWindow(2)

    assert identities.observe("event-1")
    assert identities.observe("event-2")
    assert not identities.observe("event-1")
    assert identities.duplicate_count == 1

    assert identities.observe("event-3")
    assert identities.observe("event-2")
    assert identities.duplicate_count == 1


def test_context_transition_projection_is_operator_readable() -> None:
    event = CommittedContextTransitionNotice(
        topic=MarkeitechBusTopic.CONTEXT_EVENT,
        event_id="a" * 64,
        occurred_ts=datetime(2026, 7, 16, 10, 0, tzinfo=UTC),
        aggregate_id="NQU6.CME:market_context:1m",
        payload_type="ContextTransitionEvent",
        payload_id="a" * 64,
        instrument_id="NQU6.CME",
        commit_sequence=42,
        transition_kind="trend_changed",
        timeframe="1m",
        previous_value="bullish",
        current_value="bearish",
        previous_input_fidelity="inferred",
        current_input_fidelity="inferred",
    )

    rendered = render_context_transition_notice(event)

    assert "kind=TREND_CHANGED" in rendered
    assert "NQU6.CME" in rendered
    assert "bullish->bearish" in rendered
    assert "sequence=42" in rendered
