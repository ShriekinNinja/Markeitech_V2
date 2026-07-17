from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from markeitech.persistence import NotificationOutboxRecord
from markeitech.signals import SignalTransitionEvent
from markeitech.signals.projection import (
    SignalLifecycleProjection,
    format_signal_operator_projection,
)

SIGNAL_LIFECYCLE_DESTINATION = "signal-lifecycle"
_MAX_DISCORD_CONTENT = 2000


def build_signal_transition_notification(
    event: SignalTransitionEvent,
    *,
    role: str,
) -> NotificationOutboxRecord:
    detail = format_signal_operator_projection(
        SignalLifecycleProjection.transitioned(event),
        role_resolver=lambda _instrument_id: role,
    )
    heading = (
        f"**SHADOW DLA {event.to_status.value.upper()} | "
        f"{event.current.instrument_id} {event.current.direction.value.upper()}**"
    )
    suffix = "\nDecision support only. No execution authority."
    available = _MAX_DISCORD_CONTENT - len(heading) - len(suffix) - 2
    content = f"{heading}\n{detail[:available]}{suffix}"
    now = event.occurred_ts
    return NotificationOutboxRecord(
        outbox_id=uuid5(
            NAMESPACE_URL,
            f"markeitech:discord:{SIGNAL_LIFECYCLE_DESTINATION}:{event.transition_id}",
        ),
        topic="discord",
        destination_key=SIGNAL_LIFECYCLE_DESTINATION,
        aggregate_key=event.signal_id,
        event_type="signal.transition",
        event_schema_version=event.schema_version,
        payload={"content": content, "allowed_mentions": {"parse": []}},
        dedupe_key=f"discord:{SIGNAL_LIFECYCLE_DESTINATION}:{event.transition_id}",
        available_ts=now,
        created_ts=now,
        updated_ts=now,
    )
