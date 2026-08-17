from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from markeitech.acquisition.historical import (
    HistoricalDependencyRef,
    HistoricalRequest,
)


class HistoricalExecutionState(StrEnum):
    QUEUED = "QUEUED"
    SUBMITTED = "SUBMITTED"
    RETRY_SCHEDULED = "RETRY_SCHEDULED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"


class HistoricalReadinessState(StrEnum):
    READY = "READY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"


class HistoricalExecutionPort(Protocol):
    def submit(self, request: HistoricalRequest) -> None: ...

    def cancel(self, request: HistoricalRequest) -> None: ...


@dataclass(frozen=True, slots=True)
class HistoricalExecutionPolicy:
    maximum_queued_requests: int
    maximum_in_flight_requests: int
    timeout_ns: int
    maximum_attempts: int
    retry_backoff_ns: int

    def __post_init__(self) -> None:
        _positive_int(self.maximum_queued_requests, "maximum_queued_requests")
        _positive_int(self.maximum_in_flight_requests, "maximum_in_flight_requests")
        _positive_int(self.timeout_ns, "timeout_ns")
        _positive_int(self.maximum_attempts, "maximum_attempts")
        _positive_int(self.retry_backoff_ns, "retry_backoff_ns")


@dataclass(frozen=True, slots=True)
class HistoricalExecutionEvent:
    request_id: str
    state: HistoricalExecutionState
    attempt: int
    occurred_at_ns: int
    detail: str


@dataclass(frozen=True, slots=True)
class HistoricalBatch:
    request: HistoricalRequest
    observations: tuple[object, ...]
    received_at_ns: int

    @property
    def observation_count(self) -> int:
        return len(self.observations)


@dataclass(frozen=True, slots=True)
class HistoricalDependencyResult:
    request_id: str
    dependency: HistoricalDependencyRef
    state: HistoricalReadinessState
    observed_count: int
    completed_at_ns: int
    reason: str


@dataclass(frozen=True, slots=True)
class HistoricalExecutionUpdate:
    events: tuple[HistoricalExecutionEvent, ...] = ()
    batches: tuple[HistoricalBatch, ...] = ()
    results: tuple[HistoricalDependencyResult, ...] = ()

    def extend(self, other: HistoricalExecutionUpdate) -> HistoricalExecutionUpdate:
        return HistoricalExecutionUpdate(
            events=self.events + other.events,
            batches=self.batches + other.batches,
            results=self.results + other.results,
        )


@dataclass(slots=True)
class _PendingRequest:
    request: HistoricalRequest
    attempt: int
    available_at_ns: int


@dataclass(slots=True)
class _ActiveRequest:
    request: HistoricalRequest
    attempt: int
    submitted_at_ns: int


class HistoricalExecutionError(ValueError):
    pass


class HistoricalExecutionCoordinator:
    """Runs bounded asynchronous history without coupling consumers to the provider."""

    def __init__(
        self,
        port: HistoricalExecutionPort,
        policy: HistoricalExecutionPolicy,
    ) -> None:
        self._port = port
        self._policy = policy
        self._pending: dict[str, _PendingRequest] = {}
        self._active: dict[str, _ActiveRequest] = {}
        self._terminal: set[str] = set()

    @property
    def pending_request_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._pending))

    @property
    def active_request_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._active))

    def enqueue(
        self,
        requests: tuple[HistoricalRequest, ...],
        *,
        now_ns: int,
    ) -> HistoricalExecutionUpdate:
        _non_negative_int(now_ns, "now_ns")
        events: list[HistoricalExecutionEvent] = []
        for request in requests:
            if request.request_id in self._pending or request.request_id in self._active:
                continue
            if request.request_id in self._terminal:
                raise HistoricalExecutionError(
                    f"cannot enqueue terminal historical request: {request.request_id}",
                )
            if len(self._pending) + len(self._active) >= self._policy.maximum_queued_requests:
                raise HistoricalExecutionError("historical execution queue capacity exceeded")
            self._pending[request.request_id] = _PendingRequest(request, 1, now_ns)
            events.append(self._event(request, HistoricalExecutionState.QUEUED, 1, now_ns))
        return HistoricalExecutionUpdate(events=tuple(events)).extend(self._dispatch(now_ns))

    def advance(self, *, now_ns: int) -> HistoricalExecutionUpdate:
        _non_negative_int(now_ns, "now_ns")
        update = HistoricalExecutionUpdate()
        expired = [
            active
            for active in self._active.values()
            if now_ns - active.submitted_at_ns >= self._policy.timeout_ns
        ]
        for active in sorted(expired, key=lambda item: item.request.request_id):
            del self._active[active.request.request_id]
            cancel_detail = self._cancel_port(active.request)
            update = update.extend(
                self._retry_or_finish(
                    active,
                    now_ns=now_ns,
                    terminal_state=HistoricalExecutionState.EXPIRED,
                    readiness_state=HistoricalReadinessState.EXPIRED,
                    detail=f"provider request timed out{cancel_detail}",
                ),
            )
        return update.extend(self._dispatch(now_ns))

    def complete(
        self,
        request_id: str,
        observations: tuple[object, ...],
        *,
        now_ns: int,
    ) -> HistoricalExecutionUpdate:
        _non_negative_int(now_ns, "now_ns")
        active = self._active.pop(request_id, None)
        if active is None:
            raise HistoricalExecutionError(f"historical request is not active: {request_id}")
        self._terminal.add(request_id)
        batch = HistoricalBatch(active.request, tuple(observations), now_ns)
        results = tuple(
            self._readiness_result(
                active.request,
                dependency,
                batch.observation_count,
                now_ns,
            )
            for dependency in active.request.dependencies
        )
        completed = HistoricalExecutionUpdate(
            events=(
                self._event(
                    active.request,
                    HistoricalExecutionState.COMPLETED,
                    active.attempt,
                    now_ns,
                    detail=f"provider returned {batch.observation_count} observations",
                ),
            ),
            batches=(batch,),
            results=results,
        )
        return completed.extend(self._dispatch(now_ns))

    def fail(
        self,
        request_id: str,
        reason: str,
        *,
        now_ns: int,
        retryable: bool = True,
    ) -> HistoricalExecutionUpdate:
        _non_negative_int(now_ns, "now_ns")
        active = self._active.pop(request_id, None)
        if active is None:
            raise HistoricalExecutionError(f"historical request is not active: {request_id}")
        detail = _required_text(reason, "reason")
        if retryable:
            update = self._retry_or_finish(
                active,
                now_ns=now_ns,
                terminal_state=HistoricalExecutionState.FAILED,
                readiness_state=HistoricalReadinessState.FAILED,
                detail=detail,
            )
        else:
            update = self._finish_failure(
                active,
                now_ns=now_ns,
                execution_state=HistoricalExecutionState.FAILED,
                readiness_state=HistoricalReadinessState.FAILED,
                detail=detail,
            )
        return update.extend(self._dispatch(now_ns))

    def cancel(self, request_id: str, *, now_ns: int) -> HistoricalExecutionUpdate:
        _non_negative_int(now_ns, "now_ns")
        pending = self._pending.pop(request_id, None)
        if pending is not None:
            update = self._finish_failure(
                _ActiveRequest(pending.request, pending.attempt, now_ns),
                now_ns=now_ns,
                execution_state=HistoricalExecutionState.CANCELED,
                readiness_state=HistoricalReadinessState.CANCELED,
                detail="request canceled before provider submission",
            )
            return update.extend(self._dispatch(now_ns))
        active = self._active.pop(request_id, None)
        if active is None:
            return HistoricalExecutionUpdate()
        detail = f"request canceled during provider execution{self._cancel_port(active.request)}"
        update = self._finish_failure(
            active,
            now_ns=now_ns,
            execution_state=HistoricalExecutionState.CANCELED,
            readiness_state=HistoricalReadinessState.CANCELED,
            detail=detail,
        )
        return update.extend(self._dispatch(now_ns))

    def _dispatch(self, now_ns: int) -> HistoricalExecutionUpdate:
        events: list[HistoricalExecutionEvent] = []
        while len(self._active) < self._policy.maximum_in_flight_requests:
            eligible = [
                pending
                for pending in self._pending.values()
                if pending.available_at_ns <= now_ns
            ]
            if not eligible:
                break
            pending = min(
                eligible,
                key=lambda item: (-item.request.priority, item.request.request_id),
            )
            del self._pending[pending.request.request_id]
            try:
                self._port.submit(pending.request)
            except Exception as exc:  # Provider ports define their own exception types.
                active = _ActiveRequest(pending.request, pending.attempt, now_ns)
                update = self._retry_or_finish(
                    active,
                    now_ns=now_ns,
                    terminal_state=HistoricalExecutionState.FAILED,
                    readiness_state=HistoricalReadinessState.FAILED,
                    detail=f"provider submission failed: {type(exc).__name__}",
                )
                events.extend(update.events)
                continue
            self._active[pending.request.request_id] = _ActiveRequest(
                pending.request,
                pending.attempt,
                now_ns,
            )
            events.append(
                self._event(
                    pending.request,
                    HistoricalExecutionState.SUBMITTED,
                    pending.attempt,
                    now_ns,
                ),
            )
        return HistoricalExecutionUpdate(events=tuple(events))

    def _retry_or_finish(
        self,
        active: _ActiveRequest,
        *,
        now_ns: int,
        terminal_state: HistoricalExecutionState,
        readiness_state: HistoricalReadinessState,
        detail: str,
    ) -> HistoricalExecutionUpdate:
        if active.attempt >= self._policy.maximum_attempts:
            return self._finish_failure(
                active,
                now_ns=now_ns,
                execution_state=terminal_state,
                readiness_state=readiness_state,
                detail=detail,
            )
        next_attempt = active.attempt + 1
        self._pending[active.request.request_id] = _PendingRequest(
            active.request,
            next_attempt,
            now_ns + self._policy.retry_backoff_ns,
        )
        return HistoricalExecutionUpdate(
            events=(
                self._event(
                    active.request,
                    HistoricalExecutionState.RETRY_SCHEDULED,
                    next_attempt,
                    now_ns,
                    detail=detail,
                ),
            ),
        )

    def _finish_failure(
        self,
        active: _ActiveRequest,
        *,
        now_ns: int,
        execution_state: HistoricalExecutionState,
        readiness_state: HistoricalReadinessState,
        detail: str,
    ) -> HistoricalExecutionUpdate:
        self._terminal.add(active.request.request_id)
        return HistoricalExecutionUpdate(
            events=(
                self._event(
                    active.request,
                    execution_state,
                    active.attempt,
                    now_ns,
                    detail=detail,
                ),
            ),
            results=tuple(
                HistoricalDependencyResult(
                    request_id=active.request.request_id,
                    dependency=dependency,
                    state=readiness_state,
                    observed_count=0,
                    completed_at_ns=now_ns,
                    reason=detail,
                )
                for dependency in active.request.dependencies
            ),
        )

    def _cancel_port(self, request: HistoricalRequest) -> str:
        try:
            self._port.cancel(request)
        except Exception as exc:  # Provider ports define their own exception types.
            return f"; provider cancellation failed: {type(exc).__name__}"
        return ""

    @staticmethod
    def _event(
        request: HistoricalRequest,
        state: HistoricalExecutionState,
        attempt: int,
        now_ns: int,
        detail: str = "",
    ) -> HistoricalExecutionEvent:
        return HistoricalExecutionEvent(request.request_id, state, attempt, now_ns, detail)

    @staticmethod
    def _readiness_result(
        request: HistoricalRequest,
        dependency: HistoricalDependencyRef,
        observed_count: int,
        now_ns: int,
    ) -> HistoricalDependencyResult:
        if observed_count >= dependency.minimum_observations:
            state = HistoricalReadinessState.READY
            reason = "minimum historical evidence satisfied"
        else:
            state = HistoricalReadinessState.DEGRADED
            reason = (
                "historical response below consumer minimum: "
                f"observed={observed_count}, required={dependency.minimum_observations}"
            )
        return HistoricalDependencyResult(
            request_id=request.request_id,
            dependency=dependency,
            state=state,
            observed_count=observed_count,
            completed_at_ns=now_ns,
            reason=reason,
        )


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _positive_int(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _non_negative_int(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
