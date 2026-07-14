from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from markeitech.signals.contracts import (
    SignalEvidenceReference,
    SignalSnapshot,
    SignalStatus,
    SignalTransitionEvent,
    allowed_signal_statuses,
)


def transition_signal(
    current: SignalSnapshot,
    to_status: SignalStatus,
    *,
    occurred_ts: datetime,
    reason_codes: Sequence[str],
    evidence: Sequence[SignalEvidenceReference] = (),
) -> SignalTransitionEvent:
    if to_status not in allowed_signal_statuses(current.status):
        raise ValueError(
            f"signal status cannot move from {current.status.value} to {to_status.value}"
        )
    if occurred_ts < current.updated_ts:
        raise ValueError("signal transition cannot move time backward")
    reasons = tuple(reason_codes)
    if not reasons:
        raise ValueError("signal transition requires reason codes")
    appended = tuple(evidence)
    updated_values = current.model_dump()
    updated_values.update(
        status=to_status,
        updated_ts=occurred_ts,
        evidence=(*current.evidence, *appended),
        reason_codes=reasons,
    )
    updated = SignalSnapshot.model_validate(updated_values)
    return SignalTransitionEvent(
        signal_id=current.signal_id,
        from_status=current.status,
        to_status=to_status,
        occurred_ts=occurred_ts,
        previous_content_hash=current.content_hash,
        current=updated,
        appended_evidence=appended,
        reason_codes=reasons,
    )
