"""Pure bounded reconciliation for calendar current-state delivery."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from markeitech.intelligence.calendar_messages import (
    CalendarCurrentState,
    CalendarDefinitionExpectation,
    CalendarStateSnapshotRequest,
    CalendarStateSnapshotResponse,
    CalendarTransitionV2,
)


class SessionStateDeliveryPhase(StrEnum):
    """Describe the consumer's bounded current-state synchronization phase.

    ``CONFLICT`` is terminal for the source run, while ``STOPPED`` absorbs all late work. A
    ``DEGRADED`` state may recover only through its bounded in-cycle reconciliation or retry path.
    """

    IDLE = "IDLE"
    WAITING = "WAITING"
    BACKOFF = "BACKOFF"
    LIVE = "LIVE"
    DEGRADED = "DEGRADED"
    CONFLICT = "CONFLICT"
    STOPPED = "STOPPED"


class SessionStateDeliveryDisposition(StrEnum):
    """Classify the effect of one pure synchronization input."""

    BUFFERED = "BUFFERED"
    APPLIED = "APPLIED"
    ACCEPTED = "ACCEPTED"
    DUPLICATE = "DUPLICATE"
    STALE = "STALE"
    GAP = "GAP"
    CONFLICT = "CONFLICT"
    OVERFLOW = "OVERFLOW"
    RETRY_SCHEDULED = "RETRY_SCHEDULED"
    RETRY_STARTED = "RETRY_STARTED"
    EXHAUSTED = "EXHAUSTED"
    STOPPED = "STOPPED"
    IGNORED = "IGNORED"


@dataclass(frozen=True, slots=True)
class SessionStateDeliveryPolicy:
    """Bound synchronization deadlines, retries, buffers, and boundary grace.

    Nanosecond fields are elapsed durations, not UTC timestamps. These values are startup policy;
    the pure state machine performs no clock reads and creates no timers itself.

    Attributes:
        policy_version: Positive identity of the complete delivery policy.
        response_timeout_ns: Maximum elapsed nanoseconds for one request attempt.
        maximum_attempts: Maximum attempts permitted within one cycle.
        retry_backoff_ns: Minimum elapsed nanoseconds before a retry.
        maximum_elapsed_ns: Maximum elapsed nanoseconds across the whole cycle.
        maximum_buffered_transitions_per_calendar: Per-calendar transition capacity.
        maximum_total_buffered_transitions: Aggregate transition capacity.
        boundary_delivery_grace_ns: Grace after a known boundary before resynchronization.

    Raises:
        ValueError: If a value is non-positive or aggregate limits are internally inconsistent.
    """

    policy_version: int
    response_timeout_ns: int
    maximum_attempts: int
    retry_backoff_ns: int
    maximum_elapsed_ns: int
    maximum_buffered_transitions_per_calendar: int
    maximum_total_buffered_transitions: int
    boundary_delivery_grace_ns: int

    def __post_init__(self) -> None:
        values = (
            self.policy_version,
            self.response_timeout_ns,
            self.maximum_attempts,
            self.retry_backoff_ns,
            self.maximum_elapsed_ns,
            self.maximum_buffered_transitions_per_calendar,
            self.maximum_total_buffered_transitions,
            self.boundary_delivery_grace_ns,
        )
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value <= 0
            for value in values
        ):
            raise ValueError("session-state delivery policy values must be positive integers")
        if self.maximum_elapsed_ns < self.response_timeout_ns:
            raise ValueError("delivery maximum elapsed time must cover one response timeout")
        if (
            self.maximum_total_buffered_transitions
            < self.maximum_buffered_transitions_per_calendar
        ):
            raise ValueError("total transition capacity must cover the per-calendar capacity")


@dataclass(frozen=True, slots=True)
class SessionStateDeliveryState:
    """Hold immutable, framework-independent consumer synchronization state.

    Watermarks contain only admitted gap-free calendar states. Buffered transitions remain bounded
    and are never silently evicted. ``accepted_response`` retains at most one immutable response so
    duplicate identity can be distinguished from conflicting content. This value owns no actor,
    timer, provider, persistence, or domain behavior.
    """

    phase: SessionStateDeliveryPhase
    generation: int
    requester: str
    expected_source: str
    expected_source_epoch: str
    delivery_policy_version: int
    calendar_expectations: tuple[CalendarDefinitionExpectation, ...]
    cycle_id: str | None
    request_id: str | None
    attempt: int
    requested_as_of_ns: int | None
    requested_ts_ns: int | None
    deadline_ts_ns: int | None
    started_at_ns: int | None
    alert_at_ns: int | None
    watermarks: tuple[CalendarCurrentState, ...]
    buffered_transitions: tuple[CalendarTransitionV2, ...]
    affected_calendar_ids: tuple[str, ...]
    terminal_code: str | None
    accepted_response: CalendarStateSnapshotResponse | None

    @classmethod
    def idle(
        cls,
        *,
        requester: str,
        expected_source: str,
        expected_source_epoch: str,
        delivery_policy_version: int,
    ) -> SessionStateDeliveryState:
        """Create an empty delivery state for one expected source run.

        Args:
            requester: Exact consumer actor identity.
            expected_source: Exact canonical producer identity.
            expected_source_epoch: Runtime run UUID expected for the revision stream.
            delivery_policy_version: Version required for every request and response.

        Returns:
            A new immutable state in ``IDLE``.

        Raises:
            ValueError: If an identity is empty or the policy version is not positive.
        """

        for value, label in (
            (requester, "requester"),
            (expected_source, "expected_source"),
            (expected_source_epoch, "expected_source_epoch"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label} must be a non-empty string")
        if (
            not isinstance(delivery_policy_version, int)
            or isinstance(delivery_policy_version, bool)
            or delivery_policy_version <= 0
        ):
            raise ValueError("delivery_policy_version must be a positive integer")
        return cls(
            phase=SessionStateDeliveryPhase.IDLE,
            generation=0,
            requester=requester,
            expected_source=expected_source,
            expected_source_epoch=expected_source_epoch,
            delivery_policy_version=delivery_policy_version,
            calendar_expectations=(),
            cycle_id=None,
            request_id=None,
            attempt=0,
            requested_as_of_ns=None,
            requested_ts_ns=None,
            deadline_ts_ns=None,
            started_at_ns=None,
            alert_at_ns=None,
            watermarks=(),
            buffered_transitions=(),
            affected_calendar_ids=(),
            terminal_code=None,
            accepted_response=None,
        )


@dataclass(frozen=True, slots=True)
class SessionStateDeliveryUpdate:
    """Return a new state and the classified effect of one pure input.

    Attributes:
        state: Immutable state after processing the input.
        disposition: Admission, recovery, rejection, or terminal classification.
        installed_calendar_ids: Calendars whose watermarks advanced during this input.
    """

    state: SessionStateDeliveryState
    disposition: SessionStateDeliveryDisposition
    installed_calendar_ids: tuple[str, ...] = ()


def start_session_state_cycle(
    state: SessionStateDeliveryState,
    *,
    calendar_expectations: tuple[CalendarDefinitionExpectation, ...],
    now_ns: int,
    policy: SessionStateDeliveryPolicy,
) -> SessionStateDeliveryState:
    """Start one bounded snapshot cycle without publishing or scheduling work.

    The function starts only from ``IDLE`` or ``LIVE``. Active, degraded, conflicted, and stopped
    states are returned unchanged so callers cannot bypass retry limits or erase conflict evidence.
    The caller supplies ``now_ns`` from its runtime clock; it becomes the requested-as-of time,
    creation time, and start of the elapsed budget.

    Args:
        state: Existing immutable consumer state.
        calendar_expectations: Complete exact definition population to synchronize.
        now_ns: Current UTC Unix time in nanoseconds from the consumer clock.
        policy: Bounded policy whose version must match the state.

    Returns:
        A ``WAITING`` state with stable cycle identity and first-attempt identity, or the unchanged
        input when a new cycle is not admissible.

    Raises:
        ValueError: If policy identity, time, or expectation population is invalid.
    """

    if state.phase in {
        SessionStateDeliveryPhase.WAITING,
        SessionStateDeliveryPhase.BACKOFF,
        SessionStateDeliveryPhase.DEGRADED,
        SessionStateDeliveryPhase.CONFLICT,
        SessionStateDeliveryPhase.STOPPED,
    }:
        return state
    _policy_matches(state, policy)
    _non_negative(now_ns, "now_ns")
    calendar_ids = tuple(item.calendar_id for item in calendar_expectations)
    if not calendar_ids or len(calendar_ids) != len(set(calendar_ids)):
        raise ValueError("session-state cycle calendar expectations must be non-empty and unique")
    generation = state.generation + 1
    cycle_id = f"calendar-state:{state.requester}:g{generation}:{now_ns}"
    return replace(
        state,
        phase=SessionStateDeliveryPhase.WAITING,
        generation=generation,
        calendar_expectations=calendar_expectations,
        cycle_id=cycle_id,
        request_id=_request_id(cycle_id, 1),
        attempt=1,
        requested_as_of_ns=now_ns,
        requested_ts_ns=now_ns,
        deadline_ts_ns=now_ns + policy.response_timeout_ns,
        started_at_ns=now_ns,
        alert_at_ns=now_ns + policy.response_timeout_ns,
        buffered_transitions=(),
        affected_calendar_ids=(),
        terminal_code=None,
        accepted_response=None,
    )


def current_snapshot_request(state: SessionStateDeliveryState) -> CalendarStateSnapshotRequest:
    """Materialize the immutable request represented by a waiting state.

    Args:
        state: Consumer state for one outstanding attempt.

    Returns:
        A strict snapshot request carrying the state's exact correlation identity and deadline.

    Raises:
        ValueError: If the state is not waiting or lacks complete request identity.
    """

    if state.phase is not SessionStateDeliveryPhase.WAITING:
        raise ValueError("snapshot request is available only while waiting")
    if None in (
        state.cycle_id,
        state.request_id,
        state.requested_as_of_ns,
        state.requested_ts_ns,
        state.deadline_ts_ns,
    ):
        raise ValueError("waiting delivery state is missing request identity")
    return CalendarStateSnapshotRequest(
        cycle_id=str(state.cycle_id),
        request_id=str(state.request_id),
        attempt=state.attempt,
        requester=state.requester,
        expected_source=state.expected_source,
        expected_source_epoch=state.expected_source_epoch,
        calendar_expectations=state.calendar_expectations,
        requested_as_of_ns=int(state.requested_as_of_ns),
        requested_ts_ns=int(state.requested_ts_ns),
        deadline_ts_ns=int(state.deadline_ts_ns),
        delivery_policy_version=state.delivery_policy_version,
    )


def resynchronize_session_state_cycle(
    state: SessionStateDeliveryState,
    *,
    now_ns: int,
    policy: SessionStateDeliveryPolicy,
) -> SessionStateDeliveryState:
    """Start a fresh bounded cycle after a live-stream gap or overflow.

    This entry point is deliberately narrower than retry. It cannot restart a failed snapshot,
    conflict, stopped state, or an arbitrary degraded state. A newly observed live-stream gap has
    no useful relationship to the elapsed budget of the startup cycle which originally installed
    the watermark, so it receives a new generation and bounded elapsed budget.

    Args:
        state: Degraded state produced by live transition reconciliation.
        now_ns: Current UTC Unix nanoseconds from the consumer clock.
        policy: Bounded policy whose version must match the state.

    Returns:
        A fresh ``WAITING`` cycle, or the unchanged state when resynchronization is not admissible.
    """

    if state.phase is not SessionStateDeliveryPhase.DEGRADED or state.terminal_code not in {
        "revision_gap",
        "buffer_overflow",
    }:
        return state
    restartable = replace(
        state,
        phase=SessionStateDeliveryPhase.LIVE,
        accepted_response=None,
    )
    return start_session_state_cycle(
        restartable,
        calendar_expectations=state.calendar_expectations,
        now_ns=now_ns,
        policy=policy,
    )


def observe_session_transition(
    state: SessionStateDeliveryState,
    transition: CalendarTransitionV2,
    *,
    policy: SessionStateDeliveryPolicy,
) -> SessionStateDeliveryUpdate:
    """Reconcile one transition without performing actor or domain side effects.

    Waiting transitions are buffered within policy limits. Live transitions advance only a
    contiguous revision watermark; stale and equal duplicates are absorbed, while source,
    definition, event, or revision identity conflicts fail closed. Out-of-order transitions may
    recover once the complete contiguous sequence is present.

    Args:
        state: Existing immutable synchronization state.
        transition: Strict transition-v2 event to classify.
        policy: Buffer policy whose version must match the state.

    Returns:
        The resulting state, disposition, and any calendar watermark advances.

    Raises:
        ValueError: If the policy version does not match the state.
    """

    if state.phase is SessionStateDeliveryPhase.STOPPED:
        return SessionStateDeliveryUpdate(state, SessionStateDeliveryDisposition.STOPPED)
    if state.phase is SessionStateDeliveryPhase.CONFLICT:
        return SessionStateDeliveryUpdate(state, SessionStateDeliveryDisposition.CONFLICT)
    _policy_matches(state, policy)
    expectation = _expectation(state, transition.calendar_id)
    if expectation is None:
        return _conflict(state, transition.calendar_id, "unexpected_calendar")
    if (
        transition.source != state.expected_source
        or transition.source_epoch != state.expected_source_epoch
    ):
        return _conflict(state, transition.calendar_id, "source_identity_conflict")
    if not _definition_matches(expectation, transition):
        return _conflict(state, transition.calendar_id, "definition_identity_conflict")

    watermark = _watermark(state, transition.calendar_id)
    if watermark is not None:
        if (
            transition.event_id == watermark.last_transition_event_id
            and not _transition_matches_state(transition, watermark)
        ):
            return _conflict(state, transition.calendar_id, "event_identity_conflict")
        if transition.revision < watermark.revision:
            return SessionStateDeliveryUpdate(state, SessionStateDeliveryDisposition.STALE)
        if transition.revision == watermark.revision:
            disposition = (
                SessionStateDeliveryDisposition.DUPLICATE
                if _transition_matches_state(transition, watermark)
                else SessionStateDeliveryDisposition.CONFLICT
            )
            if disposition is SessionStateDeliveryDisposition.CONFLICT:
                return _conflict(state, transition.calendar_id, "revision_identity_conflict")
            return SessionStateDeliveryUpdate(state, disposition)

    existing = _buffered_revision(state, transition.calendar_id, transition.revision)
    if existing is not None:
        if existing == transition:
            return SessionStateDeliveryUpdate(state, SessionStateDeliveryDisposition.DUPLICATE)
        return _conflict(state, transition.calendar_id, "revision_identity_conflict")
    if any(
        item.event_id == transition.event_id and item != transition
        for item in state.buffered_transitions
    ):
        return _conflict(state, transition.calendar_id, "event_identity_conflict")

    calendar_count = sum(
        item.calendar_id == transition.calendar_id for item in state.buffered_transitions
    )
    if (
        calendar_count >= policy.maximum_buffered_transitions_per_calendar
        or len(state.buffered_transitions) >= policy.maximum_total_buffered_transitions
    ):
        overflowed = replace(
            state,
            phase=SessionStateDeliveryPhase.DEGRADED,
            affected_calendar_ids=_add_id(state.affected_calendar_ids, transition.calendar_id),
            terminal_code="buffer_overflow",
        )
        return SessionStateDeliveryUpdate(
            overflowed,
            SessionStateDeliveryDisposition.OVERFLOW,
        )

    buffered = replace(
        state,
        buffered_transitions=state.buffered_transitions + (transition,),
    )
    if watermark is None or state.phase in {
        SessionStateDeliveryPhase.WAITING,
        SessionStateDeliveryPhase.BACKOFF,
    }:
        return SessionStateDeliveryUpdate(buffered, SessionStateDeliveryDisposition.BUFFERED)
    return _reconcile_buffer(buffered)


def observe_session_snapshot(
    state: SessionStateDeliveryState,
    response: CalendarStateSnapshotResponse,
    *,
    now_ns: int,
) -> SessionStateDeliveryUpdate:
    """Correlate and reconcile one snapshot response at consumer observation time.

    Response payload time does not determine timely delivery: ``now_ns`` must also be within the
    attempt deadline. A ready response establishes revision watermarks and then reconciles buffered
    transitions. Failed outcomes preserve their affected calendars, retry semantics, and terminal
    conflict boundary without calculating consumer-domain effects.

    Args:
        state: Existing immutable synchronization state.
        response: Strict, completely accounted snapshot response.
        now_ns: UTC Unix nanoseconds when the consumer observes the response.

    Returns:
        The resulting state, disposition, and successfully installed calendar identifiers.

    Raises:
        ValueError: If ``now_ns`` is invalid or a waiting state lacks request identity.
    """

    _non_negative(now_ns, "now_ns")
    if state.phase is SessionStateDeliveryPhase.STOPPED:
        return SessionStateDeliveryUpdate(state, SessionStateDeliveryDisposition.STOPPED)
    if (
        state.accepted_response is not None
        and response.request_id == state.accepted_response.request_id
    ):
        if response == state.accepted_response:
            return SessionStateDeliveryUpdate(state, SessionStateDeliveryDisposition.DUPLICATE)
        return _conflict(state, "", "response_identity_conflict")
    if state.phase is not SessionStateDeliveryPhase.WAITING:
        return SessionStateDeliveryUpdate(state, SessionStateDeliveryDisposition.STALE)
    request = current_snapshot_request(state)
    if response.request_id != request.request_id or response.cycle_id != request.cycle_id:
        return SessionStateDeliveryUpdate(state, SessionStateDeliveryDisposition.STALE)
    if now_ns > request.deadline_ts_ns or response.published_ts_ns > request.deadline_ts_ns:
        return SessionStateDeliveryUpdate(state, SessionStateDeliveryDisposition.STALE)
    if (
        response.attempt != request.attempt
        or response.requester != request.requester
        or response.source != request.expected_source
        or response.source_epoch != request.expected_source_epoch
        or response.delivery_policy_version != request.delivery_policy_version
        or response.requested_calendar_ids != request.calendar_ids
        or response.requested_as_of_ns != request.requested_as_of_ns
        or response.requested_ts_ns != request.requested_ts_ns
        or response.deadline_ts_ns != request.deadline_ts_ns
    ):
        return _conflict(state, "", "response_correlation_conflict")
    expectations = {item.calendar_id: item for item in state.calendar_expectations}
    for item in response.states:
        if not _definition_matches(expectations[item.calendar_id], item):
            return _conflict(state, item.calendar_id, "definition_identity_conflict")

    accepted = replace(
        state,
        accepted_response=response,
        alert_at_ns=None,
        request_id=None,
        deadline_ts_ns=None,
    )
    if response.failures:
        hard_conflict = any(item.outcome == "CONFLICT" for item in response.failures)
        degraded = replace(
            accepted,
            phase=(
                SessionStateDeliveryPhase.CONFLICT
                if hard_conflict
                else SessionStateDeliveryPhase.DEGRADED
            ),
            affected_calendar_ids=tuple(item.calendar_id for item in response.failures),
            terminal_code=(
                "snapshot_conflict" if hard_conflict else response.failures[0].code
            ),
        )
        return SessionStateDeliveryUpdate(degraded, SessionStateDeliveryDisposition.ACCEPTED)
    installed = replace(
        accepted,
        phase=SessionStateDeliveryPhase.LIVE,
        watermarks=tuple(sorted(response.states, key=lambda item: item.calendar_id)),
        affected_calendar_ids=(),
        terminal_code=None,
    )
    reconciled = _reconcile_buffer(installed)
    if reconciled.disposition in {
        SessionStateDeliveryDisposition.CONFLICT,
        SessionStateDeliveryDisposition.GAP,
    }:
        return reconciled
    return SessionStateDeliveryUpdate(
        reconciled.state,
        SessionStateDeliveryDisposition.ACCEPTED,
        tuple(item.calendar_id for item in reconciled.state.watermarks),
    )


def schedule_session_state_retry(
    state: SessionStateDeliveryState,
    *,
    now_ns: int,
    policy: SessionStateDeliveryPolicy,
    retry_at_ns: int | None = None,
    code: str = "response_timeout",
) -> SessionStateDeliveryUpdate:
    """Schedule pure backoff state for an admissible bounded retry.

    This function records an alert time but creates no runtime timer. Accepted response failures
    can retry only when every failed calendar is explicitly retryable; their response-provided
    retry time is authoritative. Conflicts, non-retryable outcomes, premature timeout callbacks,
    and unrelated phases are left unchanged.

    Args:
        state: Waiting or degraded synchronization state.
        now_ns: Current UTC Unix time in nanoseconds from the consumer clock.
        policy: Retry policy whose version must match the state.
        retry_at_ns: Optional source-provided absolute retry time for non-response recovery inputs.
        code: Stable reason recorded while waiting in backoff.

    Returns:
        A ``BACKOFF`` update, an exhausted degraded update, or an unchanged classified update.

    Raises:
        ValueError: If policy identity or time is invalid, or active state lacks its start time.
    """

    if state.phase is SessionStateDeliveryPhase.STOPPED:
        return SessionStateDeliveryUpdate(state, SessionStateDeliveryDisposition.STOPPED)
    if state.phase not in {
        SessionStateDeliveryPhase.WAITING,
        SessionStateDeliveryPhase.DEGRADED,
    }:
        return SessionStateDeliveryUpdate(state, SessionStateDeliveryDisposition.IGNORED)
    _policy_matches(state, policy)
    _non_negative(now_ns, "now_ns")
    if code == "response_timeout" and state.alert_at_ns is not None and now_ns < state.alert_at_ns:
        return SessionStateDeliveryUpdate(state, SessionStateDeliveryDisposition.IGNORED)
    if state.accepted_response is not None and state.accepted_response.failures and not all(
        item.retryable for item in state.accepted_response.failures
    ):
        return SessionStateDeliveryUpdate(state, SessionStateDeliveryDisposition.IGNORED)
    if state.accepted_response is not None and state.accepted_response.failures:
        retry_at_ns = state.accepted_response.retry_at_ns
    if state.attempt >= policy.maximum_attempts:
        exhausted = replace(
            state,
            phase=SessionStateDeliveryPhase.DEGRADED,
            request_id=None,
            deadline_ts_ns=None,
            alert_at_ns=None,
            terminal_code="attempts_exhausted",
        )
        return SessionStateDeliveryUpdate(exhausted, SessionStateDeliveryDisposition.EXHAUSTED)
    if state.started_at_ns is None:
        raise ValueError("active session-state cycle is missing its start time")
    alert_at_ns = max(now_ns + policy.retry_backoff_ns, retry_at_ns or 0)
    if (
        alert_at_ns + policy.response_timeout_ns
        > state.started_at_ns + policy.maximum_elapsed_ns
    ):
        exhausted = replace(
            state,
            phase=SessionStateDeliveryPhase.DEGRADED,
            request_id=None,
            deadline_ts_ns=None,
            alert_at_ns=None,
            terminal_code="elapsed_budget_exhausted",
        )
        return SessionStateDeliveryUpdate(exhausted, SessionStateDeliveryDisposition.EXHAUSTED)
    backoff = replace(
        state,
        phase=SessionStateDeliveryPhase.BACKOFF,
        request_id=None,
        deadline_ts_ns=None,
        alert_at_ns=alert_at_ns,
        terminal_code=code,
    )
    return SessionStateDeliveryUpdate(backoff, SessionStateDeliveryDisposition.RETRY_SCHEDULED)


def begin_session_state_retry(
    state: SessionStateDeliveryState,
    *,
    now_ns: int,
    policy: SessionStateDeliveryPolicy,
) -> SessionStateDeliveryUpdate:
    """Begin the next attempt when the recorded backoff alert is due.

    The logical cycle identity remains stable, while attempt number and request identity advance.
    The supplied time becomes the retry's new requested-as-of time and absolute response deadline.
    No request is published and no timer is created by this function.

    Args:
        state: Existing immutable synchronization state.
        now_ns: Current UTC Unix time in nanoseconds from the consumer clock.
        policy: Retry policy whose version must match the state.

    Returns:
        A new ``WAITING`` attempt when due, otherwise an unchanged classified update.

    Raises:
        ValueError: If policy identity or time is invalid, or backoff state lacks cycle identity.
    """

    if state.phase is SessionStateDeliveryPhase.STOPPED:
        return SessionStateDeliveryUpdate(state, SessionStateDeliveryDisposition.STOPPED)
    if state.phase is not SessionStateDeliveryPhase.BACKOFF:
        return SessionStateDeliveryUpdate(state, SessionStateDeliveryDisposition.IGNORED)
    _policy_matches(state, policy)
    _non_negative(now_ns, "now_ns")
    if state.alert_at_ns is None or now_ns < state.alert_at_ns:
        return SessionStateDeliveryUpdate(state, SessionStateDeliveryDisposition.IGNORED)
    if state.cycle_id is None:
        raise ValueError("retry state is missing its cycle identity")
    attempt = state.attempt + 1
    waiting = replace(
        state,
        phase=SessionStateDeliveryPhase.WAITING,
        request_id=_request_id(state.cycle_id, attempt),
        attempt=attempt,
        requested_as_of_ns=now_ns,
        requested_ts_ns=now_ns,
        deadline_ts_ns=now_ns + policy.response_timeout_ns,
        alert_at_ns=now_ns + policy.response_timeout_ns,
        terminal_code=None,
        accepted_response=None,
    )
    return SessionStateDeliveryUpdate(waiting, SessionStateDeliveryDisposition.RETRY_STARTED)


def stop_session_state_delivery(state: SessionStateDeliveryState) -> SessionStateDeliveryState:
    """Enter absorbing terminal stop and clear all transient synchronization data.

    Args:
        state: Existing immutable synchronization state.

    Returns:
        A ``STOPPED`` state with requests, alerts, buffers, watermarks, and cached response cleared.
    """

    return replace(
        state,
        phase=SessionStateDeliveryPhase.STOPPED,
        request_id=None,
        deadline_ts_ns=None,
        alert_at_ns=None,
        watermarks=(),
        buffered_transitions=(),
        affected_calendar_ids=(),
        accepted_response=None,
    )


def _reconcile_buffer(state: SessionStateDeliveryState) -> SessionStateDeliveryUpdate:
    watermarks = {item.calendar_id: item for item in state.watermarks}
    retained: list[CalendarTransitionV2] = []
    installed: list[str] = []
    affected: list[str] = []
    for calendar_id in (item.calendar_id for item in state.calendar_expectations):
        watermark = watermarks.get(calendar_id)
        events = sorted(
            (item for item in state.buffered_transitions if item.calendar_id == calendar_id),
            key=lambda item: item.revision,
        )
        if watermark is None:
            retained.extend(events)
            continue
        for event in events:
            if event.revision < watermark.revision:
                continue
            if event.revision == watermark.revision:
                if not _transition_matches_state(event, watermark):
                    return _conflict(state, calendar_id, "revision_identity_conflict")
                continue
            if event.revision != watermark.revision + 1:
                retained.append(event)
                affected.append(calendar_id)
                continue
            watermark = _state_from_transition(event)
            watermarks[calendar_id] = watermark
            installed.append(calendar_id)
        if calendar_id in affected:
            retained.extend(
                item
                for item in events
                if item.revision > watermarks[calendar_id].revision and item not in retained
            )
    if affected:
        degraded = replace(
            state,
            phase=SessionStateDeliveryPhase.DEGRADED,
            watermarks=tuple(sorted(watermarks.values(), key=lambda item: item.calendar_id)),
            buffered_transitions=tuple(retained),
            affected_calendar_ids=tuple(dict.fromkeys(affected)),
            terminal_code="revision_gap",
        )
        return SessionStateDeliveryUpdate(
            degraded,
            SessionStateDeliveryDisposition.GAP,
            tuple(dict.fromkeys(installed)),
        )
    live = replace(
        state,
        phase=SessionStateDeliveryPhase.LIVE,
        watermarks=tuple(sorted(watermarks.values(), key=lambda item: item.calendar_id)),
        buffered_transitions=tuple(retained),
        affected_calendar_ids=(),
        terminal_code=None,
    )
    disposition = (
        SessionStateDeliveryDisposition.APPLIED
        if installed
        else SessionStateDeliveryDisposition.DUPLICATE
    )
    return SessionStateDeliveryUpdate(live, disposition, tuple(dict.fromkeys(installed)))


def _state_from_transition(event: CalendarTransitionV2) -> CalendarCurrentState:
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
        evaluated_as_of_ns=event.evaluated_as_of_ns,
        state_revision_published_ts_ns=event.published_ts_ns,
    )


def _transition_matches_state(
    transition: CalendarTransitionV2,
    state: CalendarCurrentState,
) -> bool:
    return (
        transition.calendar_id,
        transition.schedule_version,
        transition.definition_version,
        transition.definition_digest,
        transition.definition_effective_from_ns,
        transition.trade_date,
        transition.phase_memberships,
        transition.market_state,
        transition.segment_open_ns,
        transition.segment_close_ns,
        transition.next_transition_ns,
        transition.revision,
        transition.previous_revision,
        transition.event_id,
        transition.source,
        transition.source_epoch,
        transition.state_effective_from_ns,
        transition.evaluated_as_of_ns,
        transition.published_ts_ns,
    ) == (
        state.calendar_id,
        state.schedule_version,
        state.definition_version,
        state.definition_digest,
        state.definition_effective_from_ns,
        state.trade_date,
        state.phase_memberships,
        state.market_state,
        state.segment_open_ns,
        state.segment_close_ns,
        state.next_transition_ns,
        state.revision,
        state.previous_revision,
        state.last_transition_event_id,
        state.source,
        state.source_epoch,
        state.state_effective_from_ns,
        state.state_revision_evaluated_as_of_ns,
        state.state_revision_published_ts_ns,
    )


def _definition_matches(
    expectation: CalendarDefinitionExpectation,
    item: CalendarTransitionV2 | CalendarCurrentState,
) -> bool:
    return (
        item.calendar_id,
        item.definition_version,
        item.definition_digest,
        item.definition_effective_from_ns,
    ) == (
        expectation.calendar_id,
        expectation.definition_version,
        expectation.definition_digest,
        expectation.definition_effective_from_ns,
    )


def _expectation(
    state: SessionStateDeliveryState,
    calendar_id: str,
) -> CalendarDefinitionExpectation | None:
    return next(
        (item for item in state.calendar_expectations if item.calendar_id == calendar_id),
        None,
    )


def _watermark(
    state: SessionStateDeliveryState,
    calendar_id: str,
) -> CalendarCurrentState | None:
    return next((item for item in state.watermarks if item.calendar_id == calendar_id), None)


def _buffered_revision(
    state: SessionStateDeliveryState,
    calendar_id: str,
    revision: int,
) -> CalendarTransitionV2 | None:
    return next(
        (
            item
            for item in state.buffered_transitions
            if item.calendar_id == calendar_id and item.revision == revision
        ),
        None,
    )


def _conflict(
    state: SessionStateDeliveryState,
    calendar_id: str,
    code: str,
) -> SessionStateDeliveryUpdate:
    affected = state.affected_calendar_ids
    if calendar_id:
        affected = _add_id(affected, calendar_id)
    conflicted = replace(
        state,
        phase=SessionStateDeliveryPhase.CONFLICT,
        affected_calendar_ids=affected,
        terminal_code=code,
        alert_at_ns=None,
    )
    return SessionStateDeliveryUpdate(conflicted, SessionStateDeliveryDisposition.CONFLICT)


def _add_id(values: tuple[str, ...], value: str) -> tuple[str, ...]:
    return values if value in values else values + (value,)


def _request_id(cycle_id: str, attempt: int) -> str:
    return f"{cycle_id}:a{attempt}"


def _policy_matches(
    state: SessionStateDeliveryState,
    policy: SessionStateDeliveryPolicy,
) -> None:
    if state.delivery_policy_version != policy.policy_version:
        raise ValueError("session-state delivery policy version does not match state")


def _non_negative(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
