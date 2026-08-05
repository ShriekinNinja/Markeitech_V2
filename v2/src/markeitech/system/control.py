from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

from markeitech.system.messages import EvidenceValue, SystemHealthEvent


class SystemHealthState(StrEnum):
    STARTING = "STARTING"
    READY = "READY"
    FAILED = "FAILED"
    STOPPING = "STOPPING"


_ALLOWED_TRANSITIONS: dict[SystemHealthState | None, frozenset[SystemHealthState]] = {
    None: frozenset(
        {
            SystemHealthState.STARTING,
            SystemHealthState.FAILED,
            SystemHealthState.STOPPING,
        },
    ),
    SystemHealthState.STARTING: frozenset(
        {
            SystemHealthState.READY,
            SystemHealthState.FAILED,
            SystemHealthState.STOPPING,
        },
    ),
    SystemHealthState.READY: frozenset(
        {SystemHealthState.FAILED, SystemHealthState.STOPPING},
    ),
    SystemHealthState.FAILED: frozenset({SystemHealthState.STOPPING}),
    SystemHealthState.STOPPING: frozenset(),
}


class SystemHealthStateMachine:
    def __init__(self) -> None:
        self._state: SystemHealthState | None = None

    @property
    def state(self) -> SystemHealthState | None:
        return self._state

    def transition(
        self,
        target: SystemHealthState,
        *,
        reason: str,
        source: str,
        evidence: Mapping[str, EvidenceValue] | None = None,
    ) -> SystemHealthEvent | None:
        if target == self._state:
            return None
        if target not in _ALLOWED_TRANSITIONS[self._state]:
            current = self._state.value if self._state is not None else "UNINITIALIZED"
            raise ValueError(f"invalid system health transition: {current} -> {target.value}")

        previous = self._state
        event_evidence = dict(evidence or {})
        if previous is not None:
            event_evidence["previous_state"] = previous.value
        event = SystemHealthEvent(
            state=target.value,
            reason=reason,
            source=source,
            evidence=event_evidence,
        )
        self._state = target
        return event
