"""Immutable calendar projection, transition, and current-state delivery contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from markeitech.intelligence.session import CalendarProjection

CALENDAR_PROJECTION_REQUEST_TYPE_NAME = "markeitech.calendar.projection.request.v1"
CALENDAR_PROJECTION_RESPONSE_TYPE_NAME = "markeitech.calendar.projection.response.v2"
CALENDAR_TRANSITION_TYPE_NAME = "markeitech.calendar.transition.v1"
CALENDAR_TRANSITION_V2_TYPE_NAME = "markeitech.calendar.transition.v2"
CALENDAR_STATE_SNAPSHOT_REQUEST_TYPE_NAME = "markeitech.calendar.state.snapshot.request.v1"
CALENDAR_STATE_SNAPSHOT_RESPONSE_TYPE_NAME = "markeitech.calendar.state.snapshot.response.v1"
CALENDAR_PROJECTION_REQUEST_SCHEMA_VERSION = 1
CALENDAR_PROJECTION_RESPONSE_SCHEMA_VERSION = 2
CALENDAR_TRANSITION_SCHEMA_VERSION = 1
CALENDAR_TRANSITION_V2_SCHEMA_VERSION = 2
CALENDAR_STATE_SNAPSHOT_REQUEST_SCHEMA_VERSION = 1
CALENDAR_STATE_SNAPSHOT_RESPONSE_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class CalendarProjectionRequest:
    request_id: str
    requester: str
    calendar_ids: tuple[str, ...]
    start_ns: int
    end_ns: int
    requested_ts_ns: int
    schema_version: int = CALENDAR_PROJECTION_REQUEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _text(self.request_id, "request_id")
        _text(self.requester, "requester")
        _schema(
            self.schema_version,
            CALENDAR_PROJECTION_REQUEST_SCHEMA_VERSION,
            "calendar projection request",
        )
        if not self.calendar_ids or len(self.calendar_ids) != len(set(self.calendar_ids)):
            raise ValueError("calendar_ids must be non-empty and unique")
        for calendar_id in self.calendar_ids:
            _text(calendar_id, "calendar_id")
        _timestamp(self.start_ns, "start_ns")
        _timestamp(self.end_ns, "end_ns")
        _timestamp(self.requested_ts_ns, "requested_ts_ns")
        if self.end_ns <= self.start_ns:
            raise ValueError("projection request end_ns must be after start_ns")

    @property
    def ts_event(self) -> int:
        return self.requested_ts_ns

    @property
    def ts_init(self) -> int:
        return self.requested_ts_ns


@dataclass(frozen=True, slots=True)
class CalendarProjectionFailure:
    calendar_id: str
    code: str
    reason: str
    retryable: bool

    def __post_init__(self) -> None:
        _text(self.calendar_id, "calendar_id")
        if (
            not isinstance(self.code, str)
            or re.fullmatch(r"[a-z][a-z0-9_]{0,63}", self.code) is None
        ):
            raise ValueError("calendar projection failure code must be stable snake_case")
        if (
            not isinstance(self.reason, str)
            or not self.reason.strip()
            or len(self.reason) > 160
            or "\n" in self.reason
            or "\r" in self.reason
        ):
            raise ValueError("calendar projection failure reason must be one bounded line")
        if not isinstance(self.retryable, bool):
            raise ValueError("calendar projection failure retryable must be a boolean")


@dataclass(frozen=True, slots=True)
class CalendarProjectionResponse:
    request_id: str
    requester: str
    source: str
    source_epoch: str
    status: str
    requested_calendar_ids: tuple[str, ...]
    projections: tuple[CalendarProjection, ...]
    unavailable_calendar_ids: tuple[str, ...]
    failures: tuple[CalendarProjectionFailure, ...]
    generated_ts_ns: int
    retry_at_ns: int | None = None
    schema_version: int = CALENDAR_PROJECTION_RESPONSE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field in ("request_id", "requester", "source", "source_epoch"):
            _text(getattr(self, field), field)
        _schema(
            self.schema_version,
            CALENDAR_PROJECTION_RESPONSE_SCHEMA_VERSION,
            "calendar projection response",
        )
        if self.status not in {"READY", "NOT_READY", "REJECTED", "FAILED", "INCOMPLETE"}:
            raise ValueError("unsupported calendar projection response status")
        _unique_ids(self.requested_calendar_ids, "requested_calendar_ids")
        projected_ids = tuple(item.calendar_id for item in self.projections)
        failure_ids = tuple(item.calendar_id for item in self.failures)
        _unique_ids(projected_ids, "projected calendar ids", allow_empty=True)
        _unique_ids(self.unavailable_calendar_ids, "unavailable_calendar_ids", allow_empty=True)
        _unique_ids(failure_ids, "failure calendar ids", allow_empty=True)
        accounting = (
            set(projected_ids),
            set(self.unavailable_calendar_ids),
            set(failure_ids),
        )
        if any(
            accounting[index] & accounting[other]
            for index in range(3)
            for other in range(index + 1, 3)
        ):
            raise ValueError("calendar must have exactly one projection response outcome")
        if set().union(*accounting) != set(self.requested_calendar_ids):
            raise ValueError("projection response must account for every requested calendar")
        if self.status == "READY" and (self.unavailable_calendar_ids or self.failures):
            raise ValueError(
                "READY projection response cannot report unavailable or failed calendars",
            )
        if self.status == "NOT_READY" and (
            self.projections
            or self.failures
            or set(self.unavailable_calendar_ids) != set(self.requested_calendar_ids)
        ):
            raise ValueError("NOT_READY projection response must mark every calendar unavailable")
        if self.status == "REJECTED" and (
            self.projections
            or self.failures
            or set(self.unavailable_calendar_ids) != set(self.requested_calendar_ids)
        ):
            raise ValueError("REJECTED projection response must mark every calendar unavailable")
        if self.status == "FAILED" and (
            self.projections
            or self.unavailable_calendar_ids
            or set(failure_ids) != set(self.requested_calendar_ids)
        ):
            raise ValueError("FAILED projection response must fail every requested calendar")
        if self.status == "INCOMPLETE" and not (
            self.unavailable_calendar_ids or self.failures
        ):
            raise ValueError("INCOMPLETE projection response requires non-success outcomes")
        _timestamp(self.generated_ts_ns, "generated_ts_ns")
        if self.retry_at_ns is not None:
            _timestamp(self.retry_at_ns, "retry_at_ns")
            if self.retry_at_ns <= self.generated_ts_ns:
                raise ValueError("retry_at_ns must be after generated_ts_ns")
        retryable = self.status == "NOT_READY" or any(item.retryable for item in self.failures)
        if retryable != (self.retry_at_ns is not None):
            raise ValueError("retry_at_ns must be present exactly for retryable responses")

    @property
    def ts_event(self) -> int:
        return self.generated_ts_ns

    @property
    def ts_init(self) -> int:
        return self.generated_ts_ns


@dataclass(frozen=True, slots=True)
class CalendarTransition:
    event_id: str
    source: str
    source_epoch: str
    calendar_id: str
    schedule_version: str
    definition_version: int
    definition_digest: str
    effective_from_ns: int
    trade_date: str | None
    previous_trade_date: str | None
    phase_memberships: tuple[str, ...]
    previous_phase_memberships: tuple[str, ...]
    market_state: str
    previous_market_state: str | None
    segment_open_ns: int | None
    segment_close_ns: int | None
    next_transition_ns: int | None
    effective_ts_ns: int
    evaluated_ts_ns: int
    published_ts_ns: int
    revision: int
    previous_revision: int | None
    reason: str
    schema_version: int = CALENDAR_TRANSITION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field in (
            "event_id",
            "source",
            "source_epoch",
            "calendar_id",
            "schedule_version",
            "definition_digest",
            "reason",
        ):
            _text(getattr(self, field), field)
        _schema(
            self.schema_version,
            CALENDAR_TRANSITION_SCHEMA_VERSION,
            "calendar transition",
        )
        if self.definition_version <= 0 or self.revision <= 0:
            raise ValueError("definition_version and revision must be positive")
        if re.fullmatch(r"[0-9a-f]{64}", self.definition_digest) is None:
            raise ValueError("definition_digest must be lowercase SHA-256")
        if self.previous_revision is not None and self.previous_revision != self.revision - 1:
            raise ValueError("previous_revision must immediately precede revision")
        if self.market_state not in {"OPEN", "BREAK", "CLOSED"}:
            raise ValueError("unsupported calendar market state")
        if self.previous_market_state is not None and self.previous_market_state not in {
            "OPEN",
            "BREAK",
            "CLOSED",
        }:
            raise ValueError("unsupported previous calendar market state")
        for field in ("phase_memberships", "previous_phase_memberships"):
            memberships = getattr(self, field)
            if len(memberships) != len(set(memberships)) or any(
                not isinstance(item, str) or not item.strip() for item in memberships
            ):
                raise ValueError(f"{field} must contain unique non-empty strings")
        for field in ("trade_date", "previous_trade_date"):
            value = getattr(self, field)
            if value is not None:
                try:
                    date.fromisoformat(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"{field} must be an ISO date") from exc
        for field in (
            "effective_from_ns",
            "effective_ts_ns",
            "evaluated_ts_ns",
            "published_ts_ns",
        ):
            _timestamp(getattr(self, field), field)
        for field in ("segment_open_ns", "segment_close_ns", "next_transition_ns"):
            value = getattr(self, field)
            if value is not None:
                _timestamp(value, field)
        if (self.segment_open_ns is None) != (self.segment_close_ns is None):
            raise ValueError("segment bounds must both be present or absent")
        if (
            self.segment_open_ns is not None
            and self.segment_close_ns is not None
            and self.segment_close_ns <= self.segment_open_ns
        ):
            raise ValueError("segment_close_ns must be after segment_open_ns")
        if self.evaluated_ts_ns < self.effective_ts_ns:
            raise ValueError("evaluated_ts_ns must not precede effective_ts_ns")
        if self.published_ts_ns < self.evaluated_ts_ns:
            raise ValueError("published_ts_ns must not precede evaluated_ts_ns")

    @property
    def phase(self) -> str:
        if self.phase_memberships:
            return "+".join(self.phase_memberships)
        return "CLOSED" if self.market_state == "CLOSED" else self.market_state

    @property
    def is_open(self) -> bool:
        return self.market_state == "OPEN"

    @property
    def phase_open_ns(self) -> int | None:
        return self.segment_open_ns

    @property
    def phase_close_ns(self) -> int | None:
        return self.segment_close_ns

    @property
    def ts_event(self) -> int:
        return self.effective_ts_ns

    @property
    def ts_init(self) -> int:
        return self.published_ts_ns


@dataclass(frozen=True, slots=True)
class CalendarDefinitionExpectation:
    """Identify the exact canonical calendar definition required by a consumer.

    All timestamps are UTC Unix nanoseconds. The digest is the lowercase SHA-256 identity of the
    normalized definition; ``schedule_version`` labels are intentionally not part of this
    reconciliation key.

    Attributes:
        calendar_id: Canonical calendar identifier expected in the snapshot.
        definition_version: Positive schema-local definition revision.
        definition_digest: Exact normalized-definition SHA-256 digest.
        definition_effective_from_ns: Instant at which the definition became authoritative.

    Raises:
        ValueError: If the identifier, version, digest, or timestamp is invalid.
    """

    calendar_id: str
    definition_version: int
    definition_digest: str
    definition_effective_from_ns: int

    def __post_init__(self) -> None:
        _text(self.calendar_id, "calendar_id")
        _positive(self.definition_version, "definition_version")
        _digest(self.definition_digest, "definition_digest")
        _timestamp(self.definition_effective_from_ns, "definition_effective_from_ns")


@dataclass(frozen=True, slots=True)
class CalendarTransitionV2:
    """Represent one immutable definition-identified calendar-state revision.

    This contract is defined in Slice 2 but is not the canonical published transition until the
    producer performs the atomic v1-to-v2 cutover in Slice 3. It records three distinct UTC Unix
    nanosecond clocks: definition authority, the exact canonical state boundary, and the owner
    evaluation cut. ``published_ts_ns`` records transport availability and never substitutes for
    either semantic time.

    Revision identity is scoped by ``(source, source_epoch, calendar_id, revision)``. The source
    epoch is the runtime run UUID; this contract intentionally contains no producer-incarnation
    identity. ``schedule_version`` is descriptive and is not a reconciliation key.

    Raises:
        ValueError: If schema, definition, state, revision, or timestamp invariants are invalid.
    """

    event_id: str
    source: str
    source_epoch: str
    calendar_id: str
    schedule_version: str
    definition_version: int
    definition_digest: str
    definition_effective_from_ns: int
    trade_date: str | None
    previous_trade_date: str | None
    phase_memberships: tuple[str, ...]
    previous_phase_memberships: tuple[str, ...]
    market_state: str
    previous_market_state: str | None
    segment_open_ns: int | None
    segment_close_ns: int | None
    next_transition_ns: int | None
    state_effective_from_ns: int
    evaluated_as_of_ns: int
    published_ts_ns: int
    revision: int
    previous_revision: int | None
    reason: str
    schema_version: int = CALENDAR_TRANSITION_V2_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field in (
            "event_id",
            "source",
            "source_epoch",
            "calendar_id",
            "schedule_version",
            "reason",
        ):
            _text(getattr(self, field), field)
        _schema(
            self.schema_version,
            CALENDAR_TRANSITION_V2_SCHEMA_VERSION,
            "calendar transition v2",
        )
        _definition_identity(
            self.definition_version,
            self.definition_digest,
            self.definition_effective_from_ns,
        )
        _revision(self.revision, self.previous_revision)
        _calendar_state(
            trade_date=self.trade_date,
            phase_memberships=self.phase_memberships,
            market_state=self.market_state,
            segment_open_ns=self.segment_open_ns,
            segment_close_ns=self.segment_close_ns,
            next_transition_ns=self.next_transition_ns,
        )
        _optional_trade_date(self.previous_trade_date, "previous_trade_date")
        _memberships(self.previous_phase_memberships, "previous_phase_memberships")
        _market_state(self.previous_market_state, "previous_market_state", allow_none=True)
        _timestamp(self.state_effective_from_ns, "state_effective_from_ns")
        _timestamp(self.evaluated_as_of_ns, "evaluated_as_of_ns")
        _timestamp(self.published_ts_ns, "published_ts_ns")
        if not (
            self.definition_effective_from_ns
            <= self.state_effective_from_ns
            <= self.evaluated_as_of_ns
            <= self.published_ts_ns
        ):
            raise ValueError("calendar transition timestamps must follow canonical ordering")
        if (
            self.next_transition_ns is not None
            and self.next_transition_ns <= self.evaluated_as_of_ns
        ):
            raise ValueError("next_transition_ns must be after evaluated_as_of_ns")

    @property
    def phase(self) -> str:
        """Return the ordered phase memberships, or the market state when none exist."""

        if self.phase_memberships:
            return "+".join(self.phase_memberships)
        return "CLOSED" if self.market_state == "CLOSED" else self.market_state

    @property
    def is_open(self) -> bool:
        """Return whether the canonical market state is explicitly ``OPEN``."""

        return self.market_state == "OPEN"

    @property
    def ts_event(self) -> int:
        """Return the exact state-effective boundary as Nautilus event time."""

        return self.state_effective_from_ns

    @property
    def ts_init(self) -> int:
        """Return publication time as Nautilus initialization time."""

        return self.published_ts_ns


@dataclass(frozen=True, slots=True)
class CalendarStateSnapshotRequest:
    """Request a bounded current-state snapshot from the canonical calendar owner.

    This is a current-state synchronization request, not a historical query. Retries preserve
    ``cycle_id``, increment ``attempt``, and use a new ``request_id``. Every time field is a UTC
    Unix nanosecond value from the same runtime clock domain.

    Attributes:
        cycle_id: Stable identity of one synchronization cycle.
        request_id: Unique identity of this delivery attempt.
        attempt: Positive attempt number within the configured delivery policy.
        requester: Exact allowed consumer actor identity.
        expected_source: Canonical producer identity expected by the consumer.
        expected_source_epoch: Runtime run UUID expected for the revision stream.
        calendar_expectations: Complete exact definition population requested.
        requested_as_of_ns: Earliest acceptable owner evaluation cut.
        requested_ts_ns: Attempt creation and publication time.
        deadline_ts_ns: Absolute consumer-observation deadline.
        delivery_policy_version: Version of the bounded synchronization policy.
        schema_version: Strict wire-schema version.

    Raises:
        ValueError: If identity, population, policy, schema, or timestamp invariants are invalid.
    """

    cycle_id: str
    request_id: str
    attempt: int
    requester: str
    expected_source: str
    expected_source_epoch: str
    calendar_expectations: tuple[CalendarDefinitionExpectation, ...]
    requested_as_of_ns: int
    requested_ts_ns: int
    deadline_ts_ns: int
    delivery_policy_version: int
    schema_version: int = CALENDAR_STATE_SNAPSHOT_REQUEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field in (
            "cycle_id",
            "request_id",
            "requester",
            "expected_source",
            "expected_source_epoch",
        ):
            _text(getattr(self, field), field)
        _positive(self.attempt, "attempt")
        _positive(self.delivery_policy_version, "delivery_policy_version")
        _schema(
            self.schema_version,
            CALENDAR_STATE_SNAPSHOT_REQUEST_SCHEMA_VERSION,
            "calendar state snapshot request",
        )
        calendar_ids = tuple(item.calendar_id for item in self.calendar_expectations)
        _unique_ids(calendar_ids, "calendar expectation ids")
        _timestamp(self.requested_as_of_ns, "requested_as_of_ns")
        _timestamp(self.requested_ts_ns, "requested_ts_ns")
        _timestamp(self.deadline_ts_ns, "deadline_ts_ns")
        if not self.requested_as_of_ns <= self.requested_ts_ns < self.deadline_ts_ns:
            raise ValueError("snapshot request timestamps must follow canonical ordering")

    @property
    def calendar_ids(self) -> tuple[str, ...]:
        """Return requested calendar identifiers in expectation order."""

        return tuple(item.calendar_id for item in self.calendar_expectations)

    @property
    def ts_event(self) -> int:
        """Return request creation time as Nautilus event time."""

        return self.requested_ts_ns

    @property
    def ts_init(self) -> int:
        """Return request creation time as Nautilus initialization time."""

        return self.requested_ts_ns


@dataclass(frozen=True, slots=True)
class CalendarCurrentState:
    """Carry one reconciliable current calendar state within a snapshot response.

    ``state_effective_from_ns`` is the exact canonical boundary that produced the revision.
    ``state_revision_evaluated_as_of_ns`` and ``state_revision_published_ts_ns`` preserve the
    revision's original owner-evaluation and availability lineage. ``evaluated_as_of_ns`` is the
    later common owner-clock cut of the containing snapshot. All are UTC Unix nanoseconds and none
    is a candle or historical-request boundary.

    Revision identity is scoped by ``source``, runtime-run ``source_epoch``, ``calendar_id``, and
    ``revision``. The item is deterministic calendar-derived state, not provider-observed exchange
    status.

    Raises:
        ValueError: If definition, state, revision, source, or temporal lineage is invalid.
    """

    calendar_id: str
    schedule_version: str
    definition_version: int
    definition_digest: str
    definition_effective_from_ns: int
    trade_date: str | None
    phase_memberships: tuple[str, ...]
    market_state: str
    segment_open_ns: int | None
    segment_close_ns: int | None
    next_transition_ns: int | None
    revision: int
    previous_revision: int | None
    last_transition_event_id: str
    source: str
    source_epoch: str
    state_effective_from_ns: int
    state_revision_evaluated_as_of_ns: int
    evaluated_as_of_ns: int
    state_revision_published_ts_ns: int

    def __post_init__(self) -> None:
        for field in (
            "calendar_id",
            "schedule_version",
            "last_transition_event_id",
            "source",
            "source_epoch",
        ):
            _text(getattr(self, field), field)
        _definition_identity(
            self.definition_version,
            self.definition_digest,
            self.definition_effective_from_ns,
        )
        _revision(self.revision, self.previous_revision)
        _calendar_state(
            trade_date=self.trade_date,
            phase_memberships=self.phase_memberships,
            market_state=self.market_state,
            segment_open_ns=self.segment_open_ns,
            segment_close_ns=self.segment_close_ns,
            next_transition_ns=self.next_transition_ns,
        )
        _timestamp(self.state_effective_from_ns, "state_effective_from_ns")
        _timestamp(
            self.state_revision_evaluated_as_of_ns,
            "state_revision_evaluated_as_of_ns",
        )
        _timestamp(self.evaluated_as_of_ns, "evaluated_as_of_ns")
        _timestamp(self.state_revision_published_ts_ns, "state_revision_published_ts_ns")
        if not (
            self.definition_effective_from_ns
            <= self.state_effective_from_ns
            <= self.state_revision_evaluated_as_of_ns
            <= self.state_revision_published_ts_ns
        ):
            raise ValueError("current-state timestamps must follow canonical ordering")
        if self.evaluated_as_of_ns < self.state_effective_from_ns:
            raise ValueError("current-state evaluation cannot precede its state boundary")
        if self.evaluated_as_of_ns < self.state_revision_evaluated_as_of_ns:
            raise ValueError("snapshot evaluation cannot precede revision evaluation")
        if self.state_revision_published_ts_ns < self.state_effective_from_ns:
            raise ValueError("state revision publication cannot precede its state boundary")
        if (
            self.next_transition_ns is not None
            and self.next_transition_ns <= self.evaluated_as_of_ns
        ):
            raise ValueError("next_transition_ns must be after evaluated_as_of_ns")


@dataclass(frozen=True, slots=True)
class CalendarStateSnapshotFailure:
    """Describe one explicit calendar outcome when current state cannot be supplied.

    The failure contains no manufactured trade date, phase, state, or revision. Retryability is
    admitted only for ``NOT_READY`` and ``UNAVAILABLE`` outcomes and requires an explicit UTC Unix
    nanosecond ``retry_at_ns``. Actual definition identity is optional conflict evidence and must be
    wholly present when supplied.

    Raises:
        ValueError: If outcome, code, reason, retry, or definition evidence is malformed.
    """

    calendar_id: str
    outcome: str
    code: str
    reason: str
    retryable: bool
    retry_at_ns: int | None = None
    actual_definition_version: int | None = None
    actual_definition_digest: str | None = None
    actual_definition_effective_from_ns: int | None = None

    def __post_init__(self) -> None:
        _text(self.calendar_id, "calendar_id")
        if self.outcome not in {
            "NOT_READY",
            "UNAVAILABLE",
            "CONFLICT",
            "REJECTED",
            "EVALUATION_FAILED",
        }:
            raise ValueError("unsupported calendar state snapshot failure outcome")
        _failure_code(self.code, "calendar state snapshot failure")
        _bounded_reason(self.reason, "calendar state snapshot failure")
        if not isinstance(self.retryable, bool):
            raise ValueError("calendar state snapshot failure retryable must be a boolean")
        if self.retry_at_ns is not None:
            _timestamp(self.retry_at_ns, "retry_at_ns")
        if self.retryable != (self.retry_at_ns is not None):
            raise ValueError("retry_at_ns must be present exactly for retryable failures")
        if self.retryable and self.outcome not in {"NOT_READY", "UNAVAILABLE"}:
            raise ValueError("only not-ready or unavailable failures may be retryable")
        if self.outcome == "NOT_READY" and not self.retryable:
            raise ValueError("not-ready failures must carry bounded retry information")
        actual = (
            self.actual_definition_version,
            self.actual_definition_digest,
            self.actual_definition_effective_from_ns,
        )
        if any(value is not None for value in actual) and not all(
            value is not None for value in actual
        ):
            raise ValueError("actual definition identity must be wholly present or absent")
        if all(value is not None for value in actual):
            _definition_identity(
                self.actual_definition_version,
                self.actual_definition_digest,
                self.actual_definition_effective_from_ns,
            )


@dataclass(frozen=True, slots=True)
class CalendarStateSnapshotResponse:
    """Return a completely accounted point-in-time calendar-state population.

    Every requested calendar appears exactly once as a state or failure. Overall ``status`` is
    derived from those outcomes. Successful states share one ``evaluated_as_of_ns`` owner-clock
    cut and the response preserves request receipt, generation, publication, and deadline times as
    distinct UTC Unix nanosecond values.

    A structurally complete response may still be state-incomplete. Consumers must additionally
    correlate request, source, run UUID, definition population, policy version, deadline, and
    revision continuity before admitting state.

    Raises:
        ValueError: If correlation identity, accounting, status, retry, source, schema, or temporal
            invariants are invalid.
    """

    cycle_id: str
    request_id: str
    attempt: int
    requester: str
    source: str
    source_epoch: str
    status: str
    requested_calendar_ids: tuple[str, ...]
    states: tuple[CalendarCurrentState, ...]
    failures: tuple[CalendarStateSnapshotFailure, ...]
    requested_as_of_ns: int
    requested_ts_ns: int
    deadline_ts_ns: int
    request_received_ts_ns: int
    evaluated_as_of_ns: int
    generated_ts_ns: int
    published_ts_ns: int
    delivery_policy_version: int
    retry_at_ns: int | None = None
    schema_version: int = CALENDAR_STATE_SNAPSHOT_RESPONSE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field in ("cycle_id", "request_id", "requester", "source", "source_epoch"):
            _text(getattr(self, field), field)
        _positive(self.attempt, "attempt")
        _positive(self.delivery_policy_version, "delivery_policy_version")
        _schema(
            self.schema_version,
            CALENDAR_STATE_SNAPSHOT_RESPONSE_SCHEMA_VERSION,
            "calendar state snapshot response",
        )
        _unique_ids(self.requested_calendar_ids, "requested_calendar_ids")
        state_ids = tuple(item.calendar_id for item in self.states)
        failure_ids = tuple(item.calendar_id for item in self.failures)
        _unique_ids(state_ids, "current-state calendar ids", allow_empty=True)
        _unique_ids(failure_ids, "current-state failure ids", allow_empty=True)
        if set(state_ids) & set(failure_ids):
            raise ValueError("calendar must have exactly one snapshot response outcome")
        if set(state_ids) | set(failure_ids) != set(self.requested_calendar_ids):
            raise ValueError("snapshot response must account for every requested calendar")
        derived_status = _snapshot_status(self.states, self.failures)
        if self.status != derived_status:
            raise ValueError(f"snapshot response status must be derived as {derived_status}")
        for field in (
            "requested_as_of_ns",
            "requested_ts_ns",
            "deadline_ts_ns",
            "request_received_ts_ns",
            "evaluated_as_of_ns",
            "generated_ts_ns",
            "published_ts_ns",
        ):
            _timestamp(getattr(self, field), field)
        ordered_in_time = (
            self.requested_as_of_ns
            <= self.requested_ts_ns
            <= self.request_received_ts_ns
            <= self.evaluated_as_of_ns
            <= self.generated_ts_ns
            <= self.published_ts_ns
            <= self.deadline_ts_ns
        )
        expired_rejection = bool(self.failures) and all(
            item.outcome == "REJECTED" and item.code == "request_deadline_expired"
            for item in self.failures
        )
        expired_ordering = (
            self.requested_as_of_ns
            <= self.requested_ts_ns
            < self.deadline_ts_ns
            < self.request_received_ts_ns
            <= self.evaluated_as_of_ns
            <= self.generated_ts_ns
            <= self.published_ts_ns
        )
        if not ordered_in_time and not (expired_rejection and expired_ordering):
            raise ValueError("snapshot response timestamps must follow canonical ordering")
        if any(item.evaluated_as_of_ns != self.evaluated_as_of_ns for item in self.states):
            raise ValueError("snapshot states must share the response evaluated_as_of_ns")
        if any(
            item.source != self.source or item.source_epoch != self.source_epoch
            for item in self.states
        ):
            raise ValueError("snapshot state source identity must match response")
        if any(
            item.state_revision_published_ts_ns > self.published_ts_ns for item in self.states
        ):
            raise ValueError("state revision publication cannot follow response publication")
        retry_times = tuple(
            item.retry_at_ns
            for item in self.failures
            if item.retryable and item.retry_at_ns is not None
        )
        if any(
            item.retry_at_ns is not None
            and not (self.generated_ts_ns < item.retry_at_ns <= self.deadline_ts_ns)
            for item in self.failures
        ):
            raise ValueError("failure retry_at_ns must be after generation and within the deadline")
        expected_retry_at = min(retry_times) if retry_times else None
        if self.retry_at_ns != expected_retry_at:
            raise ValueError("response retry_at_ns must equal the earliest retryable failure time")
        if self.retry_at_ns is not None and not (
            self.generated_ts_ns < self.retry_at_ns <= self.deadline_ts_ns
        ):
            raise ValueError("retry_at_ns must be after generation and within the deadline")

    @property
    def ts_event(self) -> int:
        """Return the common owner evaluation cut as Nautilus event time."""

        return self.evaluated_as_of_ns

    @property
    def ts_init(self) -> int:
        """Return response publication time as Nautilus initialization time."""

        return self.published_ts_ns


def _text(value: object, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")


def _timestamp(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")


def _unique_ids(values: tuple[str, ...], label: str, *, allow_empty: bool = False) -> None:
    if (not values and not allow_empty) or len(values) != len(set(values)):
        raise ValueError(f"{label} must be {'unique' if allow_empty else 'non-empty and unique'}")
    for value in values:
        _text(value, label)


def _schema(value: object, expected: int, label: str) -> None:
    if value != expected:
        raise ValueError(f"unsupported {label} schema version: {value!r}")


def _positive(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _digest(value: object, label: str) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{label} must be lowercase SHA-256")


def _definition_identity(version: object, digest: object, effective_from_ns: object) -> None:
    _positive(version, "definition_version")
    _digest(digest, "definition_digest")
    _timestamp(effective_from_ns, "definition_effective_from_ns")


def _revision(revision: object, previous_revision: object) -> None:
    _positive(revision, "revision")
    if previous_revision is None:
        if revision != 1:
            raise ValueError("previous_revision is required after revision 1")
        return
    _positive(previous_revision, "previous_revision")
    if previous_revision != revision - 1:
        raise ValueError("previous_revision must immediately precede revision")


def _optional_trade_date(value: object, label: str) -> None:
    if value is None:
        return
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be an ISO date") from exc


def _memberships(value: object, label: str) -> None:
    if not isinstance(value, tuple) or len(value) != len(set(value)) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError(f"{label} must contain unique non-empty strings")


def _market_state(value: object, label: str, *, allow_none: bool = False) -> None:
    allowed: set[object] = {"OPEN", "BREAK", "CLOSED"}
    if allow_none:
        allowed.add(None)
    if value not in allowed:
        raise ValueError(f"unsupported {label}")


def _calendar_state(
    *,
    trade_date: object,
    phase_memberships: object,
    market_state: object,
    segment_open_ns: object,
    segment_close_ns: object,
    next_transition_ns: object,
) -> None:
    _optional_trade_date(trade_date, "trade_date")
    _memberships(phase_memberships, "phase_memberships")
    _market_state(market_state, "market_state")
    if (segment_open_ns is None) != (segment_close_ns is None):
        raise ValueError("segment bounds must both be present or absent")
    if segment_open_ns is not None and segment_close_ns is not None:
        _timestamp(segment_open_ns, "segment_open_ns")
        _timestamp(segment_close_ns, "segment_close_ns")
        if segment_close_ns <= segment_open_ns:
            raise ValueError("segment_close_ns must be after segment_open_ns")
    if next_transition_ns is not None:
        _timestamp(next_transition_ns, "next_transition_ns")


def _failure_code(value: object, label: str) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[a-z][a-z0-9_]{0,63}", value) is None:
        raise ValueError(f"{label} code must be stable snake_case")


def _bounded_reason(value: object, label: str) -> None:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > 160
        or "\n" in value
        or "\r" in value
    ):
        raise ValueError(f"{label} reason must be one bounded line")


def _snapshot_status(
    states: tuple[CalendarCurrentState, ...],
    failures: tuple[CalendarStateSnapshotFailure, ...],
) -> str:
    if states and not failures:
        return "READY"
    if states:
        return "INCOMPLETE"
    if failures and all(item.outcome == "NOT_READY" and item.retryable for item in failures):
        return "NOT_READY"
    if failures and all(item.outcome == "REJECTED" for item in failures):
        return "REJECTED"
    return "FAILED"
