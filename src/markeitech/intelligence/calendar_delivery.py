from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from markeitech.intelligence.calendar_messages import CalendarProjectionResponse


class ProjectionRequestPhase(StrEnum):
    IDLE = "IDLE"
    WAITING = "WAITING"
    BACKOFF = "BACKOFF"
    READY = "READY"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    STOPPED = "STOPPED"


@dataclass(frozen=True, slots=True)
class ProjectionRetryPolicy:
    response_timeout_ns: int
    retry_backoff_ns: int
    maximum_attempts: int
    maximum_elapsed_ns: int

    @classmethod
    def from_config(cls, values: dict[str, int]) -> ProjectionRetryPolicy:
        return cls(
            response_timeout_ns=values["response_timeout_ms"] * 1_000_000,
            retry_backoff_ns=values["retry_backoff_ms"] * 1_000_000,
            maximum_attempts=values["maximum_attempts"],
            maximum_elapsed_ns=values["maximum_elapsed_ms"] * 1_000_000,
        )

    def __post_init__(self) -> None:
        if min(
            self.response_timeout_ns,
            self.retry_backoff_ns,
            self.maximum_attempts,
            self.maximum_elapsed_ns,
        ) <= 0:
            raise ValueError("projection retry policy values must be positive")
        if self.maximum_elapsed_ns < self.response_timeout_ns:
            raise ValueError("projection maximum elapsed time must cover one response timeout")


@dataclass(frozen=True, slots=True)
class ProjectionRequestState:
    phase: ProjectionRequestPhase
    generation: int
    requester: str
    expected_source: str
    expected_source_epoch: str
    pending_calendar_ids: tuple[str, ...]
    start_ns: int | None
    end_ns: int | None
    request_id: str | None
    attempt: int
    started_at_ns: int | None
    alert_at_ns: int | None
    terminal_code: str | None

    @classmethod
    def idle(
        cls,
        *,
        requester: str,
        expected_source: str,
        expected_source_epoch: str,
    ) -> ProjectionRequestState:
        return cls(
            phase=ProjectionRequestPhase.IDLE,
            generation=0,
            requester=requester,
            expected_source=expected_source,
            expected_source_epoch=expected_source_epoch,
            pending_calendar_ids=(),
            start_ns=None,
            end_ns=None,
            request_id=None,
            attempt=0,
            started_at_ns=None,
            alert_at_ns=None,
            terminal_code=None,
        )


def start_projection_cycle(
    state: ProjectionRequestState,
    *,
    calendar_ids: tuple[str, ...],
    start_ns: int,
    end_ns: int,
    now_ns: int,
    policy: ProjectionRetryPolicy,
) -> ProjectionRequestState:
    if state.phase not in {ProjectionRequestPhase.IDLE, ProjectionRequestPhase.READY}:
        return state
    if not calendar_ids or len(calendar_ids) != len(set(calendar_ids)):
        raise ValueError("projection cycle calendar ids must be non-empty and unique")
    if end_ns <= start_ns:
        raise ValueError("projection cycle end must be after start")
    generation = state.generation + 1
    attempt = 1
    return replace(
        state,
        phase=ProjectionRequestPhase.WAITING,
        generation=generation,
        pending_calendar_ids=calendar_ids,
        start_ns=start_ns,
        end_ns=end_ns,
        request_id=_request_id(state.requester, generation, attempt, now_ns),
        attempt=attempt,
        started_at_ns=now_ns,
        alert_at_ns=now_ns + policy.response_timeout_ns,
        terminal_code=None,
    )


def classify_projection_response(
    state: ProjectionRequestState,
    response: CalendarProjectionResponse,
) -> str:
    if state.phase in {
        ProjectionRequestPhase.READY,
        ProjectionRequestPhase.FAILED,
        ProjectionRequestPhase.REJECTED,
        ProjectionRequestPhase.STOPPED,
    }:
        return "DUPLICATE"
    if state.phase is not ProjectionRequestPhase.WAITING:
        return "STALE"
    if response.requester != state.requester or response.request_id != state.request_id:
        return "STALE"
    if (
        response.source != state.expected_source
        or response.source_epoch != state.expected_source_epoch
    ):
        return "CONFLICT"
    if set(response.requested_calendar_ids) != set(state.pending_calendar_ids):
        return "CONFLICT"
    return "ACCEPT"


def retain_pending_calendars(
    state: ProjectionRequestState,
    calendar_ids: tuple[str, ...],
) -> ProjectionRequestState:
    if not set(calendar_ids) <= set(state.pending_calendar_ids):
        raise ValueError("remaining projection calendars must be a subset of pending calendars")
    return replace(state, pending_calendar_ids=calendar_ids)


def schedule_projection_retry(
    state: ProjectionRequestState,
    *,
    now_ns: int,
    policy: ProjectionRetryPolicy,
    retry_at_ns: int | None,
) -> ProjectionRequestState:
    if state.phase is not ProjectionRequestPhase.WAITING:
        return state
    if state.attempt >= policy.maximum_attempts:
        return terminal_projection_state(state, "attempts_exhausted")
    if state.started_at_ns is None:
        raise ValueError("active projection cycle is missing its start time")
    alert_at_ns = max(now_ns + policy.retry_backoff_ns, retry_at_ns or 0)
    if (
        alert_at_ns + policy.response_timeout_ns
        > state.started_at_ns + policy.maximum_elapsed_ns
    ):
        return terminal_projection_state(state, "elapsed_budget_exhausted")
    return replace(
        state,
        phase=ProjectionRequestPhase.BACKOFF,
        request_id=None,
        alert_at_ns=alert_at_ns,
    )


def begin_projection_retry(
    state: ProjectionRequestState,
    *,
    now_ns: int,
    policy: ProjectionRetryPolicy,
) -> ProjectionRequestState:
    if state.phase is not ProjectionRequestPhase.BACKOFF:
        return state
    if state.alert_at_ns is None or now_ns < state.alert_at_ns:
        return state
    attempt = state.attempt + 1
    return replace(
        state,
        phase=ProjectionRequestPhase.WAITING,
        request_id=_request_id(state.requester, state.generation, attempt, now_ns),
        attempt=attempt,
        alert_at_ns=now_ns + policy.response_timeout_ns,
    )


def ready_projection_state(state: ProjectionRequestState) -> ProjectionRequestState:
    return replace(
        state,
        phase=ProjectionRequestPhase.READY,
        pending_calendar_ids=(),
        request_id=None,
        alert_at_ns=None,
        terminal_code=None,
    )


def terminal_projection_state(
    state: ProjectionRequestState,
    code: str,
    *,
    rejected: bool = False,
) -> ProjectionRequestState:
    return replace(
        state,
        phase=(ProjectionRequestPhase.REJECTED if rejected else ProjectionRequestPhase.FAILED),
        request_id=None,
        alert_at_ns=None,
        terminal_code=code,
    )


def stop_projection_state(state: ProjectionRequestState) -> ProjectionRequestState:
    return replace(
        state,
        phase=ProjectionRequestPhase.STOPPED,
        request_id=None,
        alert_at_ns=None,
        terminal_code=state.terminal_code,
    )


def _request_id(requester: str, generation: int, attempt: int, now_ns: int) -> str:
    return f"calendar-projection:{requester}:g{generation}:a{attempt}:{now_ns}"
