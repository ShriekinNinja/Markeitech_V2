from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId, CustomData, DataType

from markeitech.acquisition import FeedKind, FeedRequirement, NautilusSubscriptionPort
from markeitech.intelligence.calendar_messages import (
    CALENDAR_PROJECTION_REQUEST_TYPE_NAME,
    CALENDAR_PROJECTION_RESPONSE_TYPE_NAME,
    CALENDAR_STATE_SNAPSHOT_REQUEST_TYPE_NAME,
    CALENDAR_STATE_SNAPSHOT_RESPONSE_TYPE_NAME,
    CALENDAR_TRANSITION_V2_TYPE_NAME,
    CalendarCurrentState,
    CalendarDefinitionExpectation,
    CalendarProjectionFailure,
    CalendarProjectionRequest,
    CalendarProjectionResponse,
    CalendarStateSnapshotFailure,
    CalendarStateSnapshotRequest,
    CalendarStateSnapshotResponse,
    CalendarTransitionV2,
)
from markeitech.intelligence.evidence import EvidencePolicy, RecencyProfile, assess_evidence
from markeitech.intelligence.messages import (
    EVIDENCE_HEALTH_SIGNAL,
    EVIDENCE_HEALTH_SNAPSHOT_REQUEST_SIGNAL,
    EVIDENCE_HEALTH_SNAPSHOT_SIGNAL,
    EVIDENCE_RECENCY_PROFILE_SIGNAL,
    EvidenceHealthEvent,
    EvidenceHealthSnapshot,
    EvidenceHealthSnapshotRequest,
    EvidenceRecencyProfileEvent,
)
from markeitech.intelligence.session import (
    CalendarStateBoundaryUnavailable,
    CanonicalCalendar,
    CanonicalSessionSnapshot,
    canonical_definition_from_config,
)
from markeitech.intelligence.session_state_delivery import (
    SessionStateDeliveryDisposition,
    SessionStateDeliveryPhase,
    SessionStateDeliveryPolicy,
    SessionStateDeliveryState,
    begin_session_state_retry,
    current_snapshot_request,
    observe_session_snapshot,
    observe_session_transition,
    resynchronize_session_state_cycle,
    schedule_session_state_retry,
    start_session_state_cycle,
    stop_session_state_delivery,
)
from markeitech.system.messages import (
    ACQUISITION_STREAM_SIGNAL,
    PERSISTENCE_READY_REQUEST_SIGNAL,
    PERSISTENCE_READY_SIGNAL,
    AcquisitionStreamEvent,
    PersistenceReadyEvent,
    PersistenceReadyRequest,
)

_SESSION_TIMER = "session-state-evaluation"
_SESSION_BOUNDARY_ALERT = "session-state-next-boundary"
_EVIDENCE_TIMER = "evidence-health-evaluation"
_EVIDENCE_CONSUMER_RETRY_TIMER = "evidence-health-consumer-registration-retry"
_EVIDENCE_SESSION_STATE_ALERT = "evidence-health-session-state-retry"


@dataclass(frozen=True, slots=True)
class _SessionContext:
    calendar_id: str
    trade_date: str | None
    phase: str
    is_open: bool


@dataclass(frozen=True, slots=True)
class _CachedSnapshotAttempt:
    request: CalendarStateSnapshotRequest
    response: CalendarStateSnapshotResponse


@dataclass(slots=True)
class _SnapshotCycle:
    cycle_id: str
    started_at_ns: int
    expires_at_ns: int
    attempts: list[_CachedSnapshotAttempt]
    terminal: bool = False


class SessionStateActorConfig(DataActorConfig):
    """Configure canonical session evaluation and bounded current-state delivery.

    Args:
        calendars: Normalized canonical calendar-definition payloads.
        evaluation_interval_ms: Periodic owner evaluation interval in milliseconds.
        source_epoch: Runtime run UUID used to scope revision identity.
        maximum_projection_days: Maximum admitted historical projection span.
        maximum_calendars_per_request: Maximum calendars in projection or snapshot requests.
        current_state_delivery: Strict snapshot delivery policy and transient buffer bounds.
        allowed_current_state_requesters: Exact actor IDs admitted to request snapshots.
        actor_id: Nautilus actor identity for the sole calendar-state owner.
    """

    def __new__(
        cls,
        calendars: list[dict[str, object]],
        evaluation_interval_ms: int,
        source_epoch: str,
        maximum_projection_days: int,
        maximum_calendars_per_request: int,
        current_state_delivery: dict[str, int],
        allowed_current_state_requesters: list[str],
        actor_id: str | ActorId = "SESSION-STATE",
    ) -> SessionStateActorConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        obj = super().__new__(cls, actor_id=resolved)
        obj.calendars = tuple(calendars)
        obj.evaluation_interval_ms = evaluation_interval_ms
        obj.source_epoch = source_epoch
        obj.maximum_projection_days = maximum_projection_days
        obj.maximum_calendars_per_request = maximum_calendars_per_request
        obj.current_state_delivery = dict(current_state_delivery)
        obj.allowed_current_state_requesters = tuple(allowed_current_state_requesters)
        return obj


class SessionStateActor(DataActor):
    """Own active canonical-calendar evaluation and bounded snapshot delivery.

    Markeitech Metadata:
        architecture.component.id: actor.session-state
        architecture.component.label: Session State
        architecture.component.kind: markeitech_actor
        architecture.component.boundary: boundary.intelligence
        architecture.component.responsibilities:
            - Sole runtime owner of active CanonicalCalendar instances.
            - Publish definition-identified calendar transitions and bounded immutable projections.
            - Contain ordinary per-calendar projection construction failures without redefining
              provider data.
    """

    def __init__(self, config: SessionStateActorConfig) -> None:
        super().__init__(config)
        self._calendars = {
            definition.calendar_id: CanonicalCalendar(definition)
            for definition in (
                canonical_definition_from_config(dict(value)) for value in config.calendars
            )
        }
        self._definitions = {
            calendar_id: calendar.definition for calendar_id, calendar in self._calendars.items()
        }
        self._interval_ns = config.evaluation_interval_ms * 1_000_000
        self._source_epoch = config.source_epoch
        self._maximum_projection_days = config.maximum_projection_days
        self._maximum_calendars_per_request = config.maximum_calendars_per_request
        self._delivery_policy = dict(config.current_state_delivery)
        self._allowed_snapshot_requesters = frozenset(config.allowed_current_state_requesters)
        self._request_type = DataType(CALENDAR_PROJECTION_REQUEST_TYPE_NAME)
        self._response_type = DataType(CALENDAR_PROJECTION_RESPONSE_TYPE_NAME)
        self._snapshot_request_type = DataType(CALENDAR_STATE_SNAPSHOT_REQUEST_TYPE_NAME)
        self._snapshot_response_type = DataType(CALENDAR_STATE_SNAPSHOT_RESPONSE_TYPE_NAME)
        self._transition_type = DataType(CALENDAR_TRANSITION_V2_TYPE_NAME)
        self._snapshots: dict[str, CanonicalSessionSnapshot] = {}
        self._current_transitions: dict[str, CalendarTransitionV2] = {}
        self._revisions: defaultdict[str, int] = defaultdict(int)
        self._snapshot_cycles: dict[str, _SnapshotCycle] = {}
        self._projection_requests = 0
        self._projection_rejections = 0
        self._projection_failures = 0
        self._snapshot_requests = 0
        self._snapshot_replays = 0
        self._snapshot_rejections = 0
        self._active = False
        self._ready = False
        self._terminal = False

    def on_start(self) -> None:
        if self._terminal:
            raise RuntimeError("SessionStateActor cannot restart after terminal stop")
        self._active = True
        self.subscribe_data(self._request_type)
        self.subscribe_data(self._snapshot_request_type)
        self.subscribe_signal(PERSISTENCE_READY_SIGNAL)
        self.publish_signal(
            PERSISTENCE_READY_REQUEST_SIGNAL,
            PersistenceReadyRequest(requester=str(self.actor_id)).to_signal_value(),
        )

    def on_data(self, data) -> None:  # noqa: ANN001
        if not self._active:
            return
        payload = data.data if isinstance(data, CustomData) else data
        if isinstance(payload, CalendarProjectionRequest):
            self._publish_projection(payload)
        elif isinstance(payload, CalendarStateSnapshotRequest):
            self._publish_current_state(payload)

    def on_signal(self, signal: Signal) -> None:
        if not self._active or signal.name != PERSISTENCE_READY_SIGNAL:
            return
        try:
            PersistenceReadyEvent.from_signal_value(signal.value)
        except ValueError as exc:
            self.log.error(f"SESSION_PERSISTENCE_READY_REJECTED | error={type(exc).__name__}")
            return
        if self._ready:
            return
        self._ready = True
        self._evaluate(None)
        if self._active:
            self.clock.set_timer_ns(_SESSION_TIMER, self._interval_ns, callback=self._evaluate)

    def on_stop(self) -> None:
        self._active = False
        self._ready = False
        self._terminal = True
        self.unsubscribe_data(self._request_type)
        self.unsubscribe_data(self._snapshot_request_type)
        self.unsubscribe_signal(PERSISTENCE_READY_SIGNAL)
        for timer_name in (_SESSION_TIMER, _SESSION_BOUNDARY_ALERT):
            if timer_name in self.clock.timer_names():
                self.clock.cancel_timer(timer_name)
        self._snapshot_cycles.clear()
        self.log.info(
            f"SESSION_STATE_STOPPED | calendars={len(self._calendars)}"
            f" | transitions={sum(self._revisions.values())}"
            f" | projection_requests={self._projection_requests}"
            f" | projection_rejections={self._projection_rejections}"
            f" | projection_failures={self._projection_failures}"
            f" | snapshot_requests={self._snapshot_requests}"
            f" | snapshot_replays={self._snapshot_replays}"
            f" | snapshot_rejections={self._snapshot_rejections}",
        )

    def _evaluate(self, _event) -> None:  # noqa: ANN001
        if not self._active or not self._ready:
            return
        now_ns = self.clock.timestamp_ns()
        next_boundary_ns: int | None = None
        for calendar_id in self._calendars:
            if not self._active:
                return
            try:
                self._update_calendar_state(calendar_id, now_ns)
            except Exception as exc:  # noqa: BLE001
                self.log.error(
                    "CALENDAR_STATE_EVALUATION_FAILED"
                    f" | calendar_id={calendar_id} | error={type(exc).__name__}",
                )
                continue
            snapshot = self._snapshots[calendar_id]
            if snapshot.next_transition_ns is not None and snapshot.next_transition_ns > now_ns:
                next_boundary_ns = (
                    snapshot.next_transition_ns
                    if next_boundary_ns is None
                    else min(next_boundary_ns, snapshot.next_transition_ns)
                )
        self._schedule_boundary(next_boundary_ns)

    def _update_calendar_state(
        self,
        calendar_id: str,
        evaluated_as_of_ns: int,
    ) -> CalendarTransitionV2:
        if not self._active:
            raise RuntimeError("session-state producer is inactive")
        snapshot = self._calendars[calendar_id].evaluate(evaluated_as_of_ns)
        previous = self._snapshots.get(calendar_id)
        identity = _session_snapshot_identity(snapshot)
        previous_identity = None if previous is None else _session_snapshot_identity(previous)
        if identity == previous_identity:
            self._snapshots[calendar_id] = snapshot
            return self._current_transitions[calendar_id]
        if not self._active:
            raise RuntimeError("session-state producer became inactive during evaluation")
        revision = self._revisions[calendar_id] + 1
        definition = self._definitions[calendar_id]
        published_ts_ns = self.clock.timestamp_ns()
        event = CalendarTransitionV2(
            event_id=f"calendar:{self._source_epoch}:{calendar_id}:{revision}",
            calendar_id=calendar_id,
            schedule_version=snapshot.schedule_version,
            definition_version=snapshot.definition_version,
            definition_digest=snapshot.definition_digest,
            definition_effective_from_ns=definition.effective_from_ns,
            trade_date=snapshot.trade_date.isoformat() if snapshot.trade_date else None,
            previous_trade_date=(
                previous.trade_date.isoformat()
                if previous is not None and previous.trade_date is not None
                else None
            ),
            phase_memberships=snapshot.phase_memberships,
            previous_phase_memberships=(previous.phase_memberships if previous is not None else ()),
            market_state=snapshot.market_state,
            previous_market_state=previous.market_state if previous is not None else None,
            segment_open_ns=snapshot.segment_open_ns,
            segment_close_ns=snapshot.segment_close_ns,
            next_transition_ns=snapshot.next_transition_ns,
            source=str(self.actor_id),
            source_epoch=self._source_epoch,
            state_effective_from_ns=snapshot.state_effective_from_ns,
            evaluated_as_of_ns=evaluated_as_of_ns,
            published_ts_ns=published_ts_ns,
            reason="definition activated" if previous is None else "calendar state changed",
            revision=revision,
            previous_revision=revision - 1 if revision > 1 else None,
        )
        self._revisions[calendar_id] = revision
        self._snapshots[calendar_id] = snapshot
        self._current_transitions[calendar_id] = event
        if not self._active:
            return event
        self.publish_data(
            self._transition_type,
            CustomData(self._transition_type, event),
        )
        self.log.info(
            f"CALENDAR_TRANSITION | calendar={event.calendar_id}"
            f" | trade_date={event.trade_date} | phase={event.phase}"
            f" | market_state={event.previous_market_state or 'UNINITIALIZED'}"
            f"->{event.market_state} | next_transition_ns={event.next_transition_ns}",
        )
        return event

    def _schedule_boundary(self, next_boundary_ns: int | None) -> None:
        if not self._active:
            return
        if _SESSION_BOUNDARY_ALERT in self.clock.timer_names():
            self.clock.cancel_timer(_SESSION_BOUNDARY_ALERT)
        if next_boundary_ns is not None:
            self.clock.set_time_alert_ns(
                _SESSION_BOUNDARY_ALERT,
                next_boundary_ns,
                callback=self._evaluate,
            )

    def _publish_projection(self, request: CalendarProjectionRequest) -> None:
        if not self._active:
            return
        self._projection_requests += 1
        requested_days = (request.end_ns - request.start_ns) // 86_400_000_000_000 + 1
        requested = tuple(request.calendar_ids)
        unavailable = tuple(item for item in requested if item not in self._calendars)
        status = "READY"
        projections = []
        failures = []
        retry_at_ns = None
        if not self._ready:
            status = "NOT_READY"
            unavailable = requested
            retry_at_ns = self.clock.timestamp_ns() + self._interval_ns
        elif (
            len(requested) > self._maximum_calendars_per_request
            or requested_days > self._maximum_projection_days
        ):
            status = "REJECTED"
            unavailable = requested
            self._projection_rejections += 1
        else:
            start = datetime.fromtimestamp(request.start_ns / 1_000_000_000, UTC).date()
            end = datetime.fromtimestamp((request.end_ns - 1) / 1_000_000_000, UTC).date()
            for calendar_id in requested:
                calendar = self._calendars.get(calendar_id)
                if calendar is None:
                    continue
                try:
                    projections.append(
                        calendar.projection(
                            start - timedelta(days=2),
                            end + timedelta(days=2),
                        ),
                    )
                except Exception as exc:  # noqa: BLE001
                    self._projection_failures += 1
                    failures.append(
                        CalendarProjectionFailure(
                            calendar_id=calendar_id,
                            code="projection_construction_failed",
                            reason="canonical calendar projection construction failed",
                            retryable=False,
                        ),
                    )
                    self.log.error(
                        "CALENDAR_PROJECTION_FAILED"
                        f" | request_id={request.request_id}"
                        f" | calendar_id={calendar_id}"
                        f" | definition_digest={calendar.definition.definition_digest}"
                        f" | source_epoch={self._source_epoch}"
                        f" | error={type(exc).__name__}",
                    )
            if len(projections) == len(requested):
                status = "READY"
            elif len(failures) == len(requested):
                status = "FAILED"
            else:
                status = "INCOMPLETE"
        response = CalendarProjectionResponse(
            request_id=request.request_id,
            requester=request.requester,
            source=str(self.actor_id),
            source_epoch=self._source_epoch,
            status=status,
            requested_calendar_ids=requested,
            projections=tuple(projections),
            unavailable_calendar_ids=unavailable,
            failures=tuple(failures),
            generated_ts_ns=self.clock.timestamp_ns(),
            retry_at_ns=retry_at_ns,
        )
        if self._active:
            self.publish_data(self._response_type, CustomData(self._response_type, response))

    def _publish_current_state(self, request: CalendarStateSnapshotRequest) -> None:
        if not self._active:
            return
        self._snapshot_requests += 1
        received_ns = self.clock.timestamp_ns()
        action, cached = self._admit_snapshot_request(request, received_ns)
        if action == "replay" and cached is not None:
            self._snapshot_replays += 1
            if self._active:
                self.publish_data(
                    self._snapshot_response_type,
                    CustomData(self._snapshot_response_type, cached),
                )
            return
        if action != "process":
            self._snapshot_rejections += 1
            response = self._snapshot_rejection(request, received_ns, action)
            cycle = self._snapshot_cycles.get(request.requester)
            if (
                cycle is not None
                and cycle.cycle_id == request.cycle_id
                and not cycle.attempts
            ):
                self._cache_snapshot_response(request, response)
            if self._active:
                self.publish_data(
                    self._snapshot_response_type,
                    CustomData(self._snapshot_response_type, response),
                )
            return

        cut_ns = self.clock.timestamp_ns()
        if received_ns > request.deadline_ts_ns:
            response = self._snapshot_rejection(
                request,
                received_ns,
                "request_deadline_expired",
                evaluated_as_of_ns=cut_ns,
            )
        elif not self._ready:
            response = self._not_ready_snapshot(request, received_ns, cut_ns)
        else:
            response = self._evaluate_snapshot_request(request, received_ns, cut_ns)
        self._cache_snapshot_response(request, response)
        if self._active:
            self.publish_data(
                self._snapshot_response_type,
                CustomData(self._snapshot_response_type, response),
            )

    def _admit_snapshot_request(
        self,
        request: CalendarStateSnapshotRequest,
        received_ns: int,
    ) -> tuple[str, CalendarStateSnapshotResponse | None]:
        if request.requester not in self._allowed_snapshot_requesters:
            return "requester_not_allowed", None
        cycle = self._snapshot_cycles.get(request.requester)
        if cycle is not None and received_ns > cycle.expires_at_ns:
            del self._snapshot_cycles[request.requester]
            cycle = None
        if cycle is not None:
            for attempt in cycle.attempts:
                if attempt.request.request_id != request.request_id:
                    continue
                if attempt.request == request:
                    return "replay", attempt.response
                return "request_identity_conflict", None
        if request.attempt > self._delivery_policy["maximum_attempts"]:
            return "request_identity_conflict", None
        if (
            request.deadline_ts_ns - request.requested_ts_ns
            > self._delivery_policy["response_timeout_ms"] * 1_000_000
        ):
            return "request_identity_conflict", None
        if cycle is not None and cycle.cycle_id != request.cycle_id:
            if not cycle.terminal and received_ns <= cycle.expires_at_ns:
                return "request_identity_conflict", None
            del self._snapshot_cycles[request.requester]
            cycle = None
        if cycle is None:
            self._snapshot_cycles[request.requester] = _SnapshotCycle(
                cycle_id=request.cycle_id,
                started_at_ns=request.requested_ts_ns,
                expires_at_ns=request.deadline_ts_ns,
                attempts=[],
            )
        else:
            last_attempt = cycle.attempts[-1].request.attempt if cycle.attempts else 0
            if cycle.terminal or request.attempt != last_attempt + 1:
                return "request_identity_conflict", None
            maximum_cycle_deadline_ns = (
                cycle.started_at_ns
                + self._delivery_policy["maximum_elapsed_ms"] * 1_000_000
            )
            if request.deadline_ts_ns > maximum_cycle_deadline_ns:
                return "request_identity_conflict", None
            cycle.expires_at_ns = max(cycle.expires_at_ns, request.deadline_ts_ns)
        if request.expected_source != str(self.actor_id):
            return "request_identity_conflict", None
        if request.expected_source_epoch != self._source_epoch:
            return "request_identity_conflict", None
        if request.delivery_policy_version != self._delivery_policy["policy_version"]:
            return "request_identity_conflict", None
        if len(request.calendar_expectations) > self._maximum_calendars_per_request:
            return "request_population_exceeded", None
        return "process", None

    def _not_ready_snapshot(
        self,
        request: CalendarStateSnapshotRequest,
        received_ns: int,
        cut_ns: int,
    ) -> CalendarStateSnapshotResponse:
        generated_floor_ns = self.clock.timestamp_ns()
        retry_at_ns = generated_floor_ns + self._delivery_policy["retry_backoff_ms"] * 1_000_000
        if retry_at_ns > request.deadline_ts_ns:
            return self._snapshot_rejection(
                request,
                received_ns,
                "request_deadline_expired",
                evaluated_as_of_ns=cut_ns,
            )
        failures = tuple(
            CalendarStateSnapshotFailure(
                calendar_id=calendar_id,
                outcome="NOT_READY",
                code="source_not_ready",
                reason="canonical session state is not ready",
                retryable=True,
                retry_at_ns=retry_at_ns,
            )
            for calendar_id in request.calendar_ids
        )
        return self._snapshot_response(
            request,
            received_ns,
            cut_ns,
            states=(),
            failures=failures,
            generated_floor_ns=generated_floor_ns,
        )

    def _evaluate_snapshot_request(
        self,
        request: CalendarStateSnapshotRequest,
        received_ns: int,
        cut_ns: int,
    ) -> CalendarStateSnapshotResponse:
        states: list[CalendarCurrentState] = []
        failures: list[CalendarStateSnapshotFailure] = []
        for expectation in request.calendar_expectations:
            calendar = self._calendars.get(expectation.calendar_id)
            if calendar is None:
                failures.append(
                    CalendarStateSnapshotFailure(
                        calendar_id=expectation.calendar_id,
                        outcome="REJECTED",
                        code="unknown_calendar_id",
                        reason="requested calendar is not configured",
                        retryable=False,
                    ),
                )
                continue
            definition = calendar.definition
            if (
                expectation.definition_version != definition.definition_version
                or expectation.definition_digest != definition.definition_digest
                or expectation.definition_effective_from_ns != definition.effective_from_ns
            ):
                failures.append(
                    CalendarStateSnapshotFailure(
                        calendar_id=expectation.calendar_id,
                        outcome="CONFLICT",
                        code="definition_identity_conflict",
                        reason="requested calendar definition does not match the producer",
                        retryable=False,
                        actual_definition_version=definition.definition_version,
                        actual_definition_digest=definition.definition_digest,
                        actual_definition_effective_from_ns=definition.effective_from_ns,
                    ),
                )
                continue
            try:
                transition = self._update_calendar_state(expectation.calendar_id, cut_ns)
            except CalendarStateBoundaryUnavailable:
                failures.append(
                    CalendarStateSnapshotFailure(
                        calendar_id=expectation.calendar_id,
                        outcome="EVALUATION_FAILED",
                        code="state_effective_boundary_unavailable",
                        reason="canonical state boundary is unavailable",
                        retryable=False,
                        actual_definition_version=definition.definition_version,
                        actual_definition_digest=definition.definition_digest,
                        actual_definition_effective_from_ns=definition.effective_from_ns,
                    ),
                )
                continue
            except Exception as exc:  # noqa: BLE001
                failures.append(
                    CalendarStateSnapshotFailure(
                        calendar_id=expectation.calendar_id,
                        outcome="EVALUATION_FAILED",
                        code="current_state_evaluation_failed",
                        reason="canonical current-state evaluation failed",
                        retryable=False,
                        actual_definition_version=definition.definition_version,
                        actual_definition_digest=definition.definition_digest,
                        actual_definition_effective_from_ns=definition.effective_from_ns,
                    ),
                )
                self.log.error(
                    "CALENDAR_CURRENT_STATE_FAILED"
                    f" | request_id={request.request_id}"
                    f" | calendar_id={expectation.calendar_id}"
                    f" | error={type(exc).__name__}",
                )
                continue
            states.append(_calendar_current_state(transition, cut_ns))
        return self._snapshot_response(
            request,
            received_ns,
            cut_ns,
            states=tuple(states),
            failures=tuple(failures),
        )

    def _snapshot_rejection(
        self,
        request: CalendarStateSnapshotRequest,
        received_ns: int,
        code: str,
        *,
        evaluated_as_of_ns: int | None = None,
    ) -> CalendarStateSnapshotResponse:
        reasons = {
            "requester_not_allowed": "requester is not allowed to synchronize current state",
            "request_population_exceeded": "requested calendar population exceeds the bound",
            "request_deadline_expired": "snapshot request deadline expired",
            "request_identity_conflict": "snapshot request identity or policy conflicts",
        }
        failures = tuple(
            CalendarStateSnapshotFailure(
                calendar_id=calendar_id,
                outcome="REJECTED",
                code=code,
                reason=reasons[code],
                retryable=False,
            )
            for calendar_id in request.calendar_ids
        )
        cut_ns = self.clock.timestamp_ns() if evaluated_as_of_ns is None else evaluated_as_of_ns
        return self._snapshot_response(
            request,
            received_ns,
            cut_ns,
            states=(),
            failures=failures,
        )

    def _snapshot_response(
        self,
        request: CalendarStateSnapshotRequest,
        received_ns: int,
        evaluated_as_of_ns: int,
        *,
        states: tuple[CalendarCurrentState, ...],
        failures: tuple[CalendarStateSnapshotFailure, ...],
        generated_floor_ns: int | None = None,
    ) -> CalendarStateSnapshotResponse:
        generated_ts_ns = max(
            evaluated_as_of_ns,
            generated_floor_ns or 0,
            self.clock.timestamp_ns(),
        )
        published_ts_ns = max(generated_ts_ns, self.clock.timestamp_ns())
        if published_ts_ns > request.deadline_ts_ns and (
            states
            or not failures
            or any(item.code != "request_deadline_expired" for item in failures)
        ):
            failures = tuple(
                CalendarStateSnapshotFailure(
                    calendar_id=calendar_id,
                    outcome="REJECTED",
                    code="request_deadline_expired",
                    reason="snapshot request deadline expired",
                    retryable=False,
                )
                for calendar_id in request.calendar_ids
            )
            states = ()
        retry_times = tuple(
            item.retry_at_ns
            for item in failures
            if item.retryable and item.retry_at_ns is not None
        )
        return CalendarStateSnapshotResponse(
            cycle_id=request.cycle_id,
            request_id=request.request_id,
            attempt=request.attempt,
            requester=request.requester,
            source=str(self.actor_id),
            source_epoch=self._source_epoch,
            status=_snapshot_response_status(states, failures),
            requested_calendar_ids=request.calendar_ids,
            states=states,
            failures=failures,
            requested_as_of_ns=request.requested_as_of_ns,
            requested_ts_ns=request.requested_ts_ns,
            deadline_ts_ns=request.deadline_ts_ns,
            request_received_ts_ns=received_ns,
            evaluated_as_of_ns=evaluated_as_of_ns,
            generated_ts_ns=generated_ts_ns,
            published_ts_ns=published_ts_ns,
            delivery_policy_version=self._delivery_policy["policy_version"],
            retry_at_ns=min(retry_times) if retry_times else None,
        )

    def _cache_snapshot_response(
        self,
        request: CalendarStateSnapshotRequest,
        response: CalendarStateSnapshotResponse,
    ) -> None:
        cycle = self._snapshot_cycles.get(request.requester)
        if cycle is None or cycle.cycle_id != request.cycle_id:
            return
        if len(cycle.attempts) >= self._delivery_policy["maximum_attempts"]:
            cycle.terminal = True
            return
        cycle.attempts.append(_CachedSnapshotAttempt(request=request, response=response))
        cycle.terminal = request.attempt >= self._delivery_policy["maximum_attempts"]


def _session_snapshot_identity(snapshot: CanonicalSessionSnapshot) -> tuple[object, ...]:
    return (
        snapshot.trade_date,
        snapshot.phase_memberships,
        snapshot.market_state,
        snapshot.segment_open_ns,
        snapshot.segment_close_ns,
        snapshot.next_transition_ns,
        snapshot.definition_digest,
        snapshot.state_effective_from_ns,
    )


def _calendar_current_state(
    event: CalendarTransitionV2,
    evaluated_as_of_ns: int,
) -> CalendarCurrentState:
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
        evaluated_as_of_ns=evaluated_as_of_ns,
        state_revision_published_ts_ns=event.published_ts_ns,
    )


def _snapshot_response_status(
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


class EvidenceHealthActorConfig(DataActorConfig):
    """Configure evidence assessment and canonical current-state synchronization.

    Args:
        feeds: Instrument feed registrations and their calendar ownership.
        policies: Evidence-health threshold policies.
        evaluation_interval_ms: Periodic evidence evaluation interval in milliseconds.
        consumer_retry_interval_ms: Feed-registration retry interval in milliseconds.
        provider_id: Stable observation provider identity.
        profile_checkpoint_samples: Samples between recency-profile publications.
        recency_profiles: Restored bounded recency profiles.
        calendar_source: Canonical session-state producer identity.
        calendar_source_epoch: Runtime run UUID expected from the producer.
        current_state_delivery: Bounded current-state synchronization policy.
        calendar_expectations: Exact calendar definitions required for current-state use.
        actor_id: Nautilus actor identity.
    """

    def __new__(
        cls,
        feeds: list[dict[str, str]],
        policies: list[dict[str, object]],
        evaluation_interval_ms: int,
        consumer_retry_interval_ms: int,
        provider_id: str,
        profile_checkpoint_samples: int,
        recency_profiles: list[dict[str, object]],
        calendar_source: str,
        calendar_source_epoch: str,
        current_state_delivery: dict[str, int],
        calendar_expectations: list[dict[str, object]],
        actor_id: str | ActorId = "EVIDENCE-HEALTH",
    ) -> EvidenceHealthActorConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        obj = super().__new__(cls, actor_id=resolved)
        obj.feeds = tuple(feeds)
        obj.policies = tuple(policies)
        obj.evaluation_interval_ms = evaluation_interval_ms
        obj.consumer_retry_interval_ms = consumer_retry_interval_ms
        obj.provider_id = provider_id
        obj.profile_checkpoint_samples = profile_checkpoint_samples
        obj.recency_profiles = tuple(recency_profiles)
        obj.calendar_source = calendar_source
        obj.calendar_source_epoch = calendar_source_epoch
        obj.current_state_delivery = dict(current_state_delivery)
        obj.calendar_expectations = tuple(calendar_expectations)
        return obj


class EvidenceHealthActor(DataActor):
    """Evaluate bounded observation freshness and availability.

    Markeitech Metadata:
        architecture.component.id: actor.evidence-health
        architecture.component.label: Evidence Health
        architecture.component.kind: markeitech_actor
        architecture.component.boundary: boundary.intelligence
        architecture.component.responsibilities:
            - Evaluate observation freshness and availability.
            - Consume definition-identified calendar context without owning mcal.
            - Synchronize bounded current state without inferring calendar phase from silence.
    """

    def __init__(self, config: EvidenceHealthActorConfig) -> None:
        super().__init__(config)
        self._feeds = tuple(dict(item) for item in config.feeds)
        self._requirements = tuple(
            FeedRequirement(
                instrument_id=item["instrument_id"],
                kind=FeedKind(item["kind"]),
                selector=item["selector"],
            )
            for item in self._feeds
        )
        self._calendar_by_instrument = {
            item["instrument_id"]: item["calendar_id"] for item in self._feeds
        }
        self._policy_by_stream = {
            (str(item["feed_kind"]), str(item["selector"])): EvidencePolicy(
                feed_kind=str(item["feed_kind"]),
                selector=str(item["selector"]),
                fresh_for_ms=int(item["fresh_for_ms"]),
                stale_after_ms=int(item["stale_after_ms"]),
                unavailable_after_ms=int(item["unavailable_after_ms"]),
                adaptive=bool(item["adaptive"]),
                minimum_samples=int(item["minimum_samples"]),
                decay_factor=float(item["decay_factor"]),
                fresh_stddev_multiplier=float(item["fresh_stddev_multiplier"]),
                stale_stddev_multiplier=float(item["stale_stddev_multiplier"]),
                unavailable_stddev_multiplier=float(item["unavailable_stddev_multiplier"]),
                min_fresh_ms=int(item["min_fresh_ms"]),
                max_fresh_ms=int(item["max_fresh_ms"]),
                min_stale_ms=int(item["min_stale_ms"]),
                max_stale_ms=int(item["max_stale_ms"]),
                min_unavailable_ms=int(item["min_unavailable_ms"]),
                max_unavailable_ms=int(item["max_unavailable_ms"]),
            )
            for item in config.policies
        }
        self._interval_ns = config.evaluation_interval_ms * 1_000_000
        self._consumer_retry_interval_ns = config.consumer_retry_interval_ms * 1_000_000
        delivery = config.current_state_delivery
        self._session_state_policy = SessionStateDeliveryPolicy(
            policy_version=delivery["policy_version"],
            response_timeout_ns=delivery["response_timeout_ms"] * 1_000_000,
            maximum_attempts=delivery["maximum_attempts"],
            retry_backoff_ns=delivery["retry_backoff_ms"] * 1_000_000,
            maximum_elapsed_ns=delivery["maximum_elapsed_ms"] * 1_000_000,
            maximum_buffered_transitions_per_calendar=delivery[
                "maximum_buffered_transitions_per_calendar"
            ],
            maximum_total_buffered_transitions=delivery[
                "maximum_total_buffered_transitions"
            ],
            boundary_delivery_grace_ns=delivery["boundary_delivery_grace_ms"]
            * 1_000_000,
        )
        self._calendar_expectations = tuple(
            CalendarDefinitionExpectation(
                calendar_id=str(item["calendar_id"]),
                definition_version=int(item["definition_version"]),
                definition_digest=str(item["definition_digest"]),
                definition_effective_from_ns=int(item["definition_effective_from_ns"]),
            )
            for item in config.calendar_expectations
        )
        self._session_state = SessionStateDeliveryState.idle(
            requester=str(self.actor_id),
            expected_source=config.calendar_source,
            expected_source_epoch=config.calendar_source_epoch,
            delivery_policy_version=self._session_state_policy.policy_version,
        )
        self._provider_id = config.provider_id
        self._profile_checkpoint_samples = config.profile_checkpoint_samples
        self._port = NautilusSubscriptionPort(self)
        self._event_ts: dict[tuple[str, str, str], int] = {}
        self._receive_ts: dict[tuple[str, str, str], int] = {}
        self._subscription_states: dict[tuple[str, str, str], str] = {
            item.stream_key: "REQUESTED" for item in self._requirements
        }
        self._session_by_calendar: dict[str, _SessionContext] = {}
        self._calendar_ids = tuple(sorted(set(self._calendar_by_instrument.values())))
        self._calendar_transition_type = DataType(CALENDAR_TRANSITION_V2_TYPE_NAME)
        self._session_state_request_type = DataType(CALENDAR_STATE_SNAPSHOT_REQUEST_TYPE_NAME)
        self._session_state_response_type = DataType(CALENDAR_STATE_SNAPSHOT_RESPONSE_TYPE_NAME)
        self._states: dict[tuple[str, str, str], str] = {}
        self._latest_events: dict[tuple[str, str, str], EvidenceHealthEvent] = {}
        self._profiles: dict[tuple[str, str, str, str, str, str], RecencyProfile] = {}
        self._dirty_profiles: set[tuple[str, str, str, str, str, str]] = set()
        for item in config.recency_profiles:
            key = (
                str(item["instrument_id"]),
                str(item["feed_kind"]),
                str(item["selector"]),
                str(item["provider_id"]),
                str(item["session_phase"]),
                str(item["policy_version"]),
            )
            self._profiles[key] = RecencyProfile(
                sample_count=int(item["sample_count"]),
                mean_interval_ms=float(item["mean_interval_ms"]),
                variance_ms2=float(item["variance_ms2"]),
                last_observed_ns=int(item["last_observed_ns"]),
            )
        self._revisions: defaultdict[tuple[str, str, str], int] = defaultdict(int)
        self._attached_stream_keys: set[tuple[str, str, str]] = set()
        self._attachment_failure_keys: set[tuple[str, str, str]] = set()
        self._active = False
        self._started = False

    def on_start(self) -> None:
        self._active = True
        self._prepare_session_state_cycle()
        for signal_name in (
            PERSISTENCE_READY_SIGNAL,
            ACQUISITION_STREAM_SIGNAL,
            EVIDENCE_HEALTH_SNAPSHOT_REQUEST_SIGNAL,
        ):
            self.subscribe_signal(signal_name)
        self.subscribe_data(self._calendar_transition_type)
        self.subscribe_data(self._session_state_response_type)
        self._publish_session_state_request()
        self._reconcile_consumer_attachments(None)
        self.publish_signal(
            PERSISTENCE_READY_REQUEST_SIGNAL,
            PersistenceReadyRequest(requester=str(self.actor_id)).to_signal_value(),
        )

    def on_signal(self, signal: Signal) -> None:
        if not self._active:
            return
        if signal.name == EVIDENCE_HEALTH_SNAPSHOT_REQUEST_SIGNAL:
            self._publish_snapshot(signal.value)
            return
        if signal.name == PERSISTENCE_READY_SIGNAL:
            try:
                PersistenceReadyEvent.from_signal_value(signal.value)
            except ValueError as exc:
                self.log.error(f"EVIDENCE_PERSISTENCE_READY_REJECTED | error={type(exc).__name__}")
                return
            self._release_startup()
            return
        if signal.name == ACQUISITION_STREAM_SIGNAL:
            try:
                event = AcquisitionStreamEvent.from_signal_value(signal.value)
            except ValueError as exc:
                self.log.error(f"EVIDENCE_ACQUISITION_REJECTED | error={type(exc).__name__}")
                return
            key = (event.instrument_id, event.feed_kind, event.selector)
            if key in self._subscription_states:
                self._subscription_states[key] = event.state
                if self._started:
                    self._evaluate_key(key, self.clock.timestamp_ns())

    def on_data(self, data) -> None:  # noqa: ANN001
        if not self._active:
            return
        payload = data.data if isinstance(data, CustomData) else data
        if isinstance(payload, CalendarTransitionV2):
            self._observe_session_transition(payload)
            return
        if isinstance(payload, CalendarStateSnapshotResponse):
            self._observe_session_snapshot(payload)
            return
        return

    def on_quote(self, quote) -> None:  # noqa: ANN001
        if not self._active:
            return
        self._observe((str(quote.instrument_id), "quotes", "default"), quote.ts_event)

    def on_bar(self, bar) -> None:  # noqa: ANN001
        if not self._active:
            return
        instrument_id = str(bar.bar_type.instrument_id)
        keys = [
            key for key in self._subscription_states if key[0] == instrument_id and key[1] == "bars"
        ]
        for key in keys:
            self._observe(key, bar.ts_event)

    def on_stop(self) -> None:
        self._active = False
        self._session_state = stop_session_state_delivery(self._session_state)
        for profile_key in sorted(self._dirty_profiles):
            self._publish_profile(profile_key)
        for signal_name in (
            PERSISTENCE_READY_SIGNAL,
            ACQUISITION_STREAM_SIGNAL,
            EVIDENCE_HEALTH_SNAPSHOT_REQUEST_SIGNAL,
        ):
            self.unsubscribe_signal(signal_name)
        self.unsubscribe_data(self._calendar_transition_type)
        self.unsubscribe_data(self._session_state_response_type)
        if _EVIDENCE_TIMER in self.clock.timer_names():
            self.clock.cancel_timer(_EVIDENCE_TIMER)
        if _EVIDENCE_CONSUMER_RETRY_TIMER in self.clock.timer_names():
            self.clock.cancel_timer(_EVIDENCE_CONSUMER_RETRY_TIMER)
        if _EVIDENCE_SESSION_STATE_ALERT in self.clock.timer_names():
            self.clock.cancel_timer(_EVIDENCE_SESSION_STATE_ALERT)
        self.log.info(
            f"EVIDENCE_HEALTH_STOPPED | streams={len(self._requirements)}"
            f" | transitions={sum(self._revisions.values())}"
            f" | session_state={self._session_state.phase.value}",
        )

    def _release_startup(self) -> None:
        if not self._active or self._started:
            return
        self._started = True
        self._evaluate_all(None)
        self.clock.set_timer_ns(_EVIDENCE_TIMER, self._interval_ns, callback=self._evaluate_all)

    def _begin_session_state_cycle(self) -> None:
        if not self._active:
            return
        self._prepare_session_state_cycle()
        self._publish_session_state_request()

    def _prepare_session_state_cycle(self) -> None:
        self._session_state = start_session_state_cycle(
            self._session_state,
            calendar_expectations=self._calendar_expectations,
            now_ns=self.clock.timestamp_ns(),
            policy=self._session_state_policy,
        )

    def _publish_session_state_request(self) -> None:
        if not self._active or self._session_state.phase is not SessionStateDeliveryPhase.WAITING:
            return
        self._set_session_state_alert()
        request = current_snapshot_request(self._session_state)
        self.publish_data(
            self._session_state_request_type,
            CustomData(self._session_state_request_type, request),
        )

    def _observe_session_transition(self, event: CalendarTransitionV2) -> None:
        previous_phase = self._session_state.phase
        update = observe_session_transition(
            self._session_state,
            event,
            policy=self._session_state_policy,
        )
        self._session_state = update.state
        self._install_session_states(update.installed_calendar_ids)
        if self._session_state.phase is SessionStateDeliveryPhase.CONFLICT:
            self._cancel_session_state_alert()
            if previous_phase is not SessionStateDeliveryPhase.CONFLICT:
                self.log.error(
                    "EVIDENCE_SESSION_STATE_CONFLICT"
                    f" | code={self._session_state.terminal_code}",
                )
            return
        if update.disposition is SessionStateDeliveryDisposition.APPLIED:
            self._set_session_state_boundary_alert()
        if update.disposition in {
            SessionStateDeliveryDisposition.GAP,
            SessionStateDeliveryDisposition.OVERFLOW,
        }:
            self._session_state = resynchronize_session_state_cycle(
                self._session_state,
                now_ns=self.clock.timestamp_ns(),
                policy=self._session_state_policy,
            )
            self._publish_session_state_request()

    def _observe_session_snapshot(self, response: CalendarStateSnapshotResponse) -> None:
        previous_phase = self._session_state.phase
        update = observe_session_snapshot(
            self._session_state,
            response,
            now_ns=self.clock.timestamp_ns(),
        )
        self._session_state = update.state
        self._install_session_states(update.installed_calendar_ids)
        if self._session_state.phase is SessionStateDeliveryPhase.CONFLICT:
            self._cancel_session_state_alert()
            if previous_phase is not SessionStateDeliveryPhase.CONFLICT:
                self.log.error(
                    "EVIDENCE_SESSION_STATE_CONFLICT"
                    f" | code={self._session_state.terminal_code}",
                )
            return
        if self._session_state.phase is SessionStateDeliveryPhase.LIVE:
            self._set_session_state_boundary_alert()
            return
        if self._session_state.phase is SessionStateDeliveryPhase.DEGRADED:
            self._schedule_session_state_retry(
                self._session_state.terminal_code or "snapshot_degraded",
            )

    def _install_session_states(self, calendar_ids: tuple[str, ...]) -> None:
        if not self._active:
            return
        by_calendar = {item.calendar_id: item for item in self._session_state.watermarks}
        for calendar_id in calendar_ids:
            state = by_calendar.get(calendar_id)
            if state is None:
                continue
            self._retain_calendar_context(
                _SessionContext(
                    calendar_id=state.calendar_id,
                    trade_date=state.trade_date,
                    phase=(
                        "+".join(state.phase_memberships)
                        if state.phase_memberships
                        else state.market_state
                    ),
                    is_open=state.market_state == "OPEN",
                ),
            )

    def _schedule_session_state_retry(self, code: str) -> None:
        if not self._active:
            return
        update = schedule_session_state_retry(
            self._session_state,
            now_ns=self.clock.timestamp_ns(),
            policy=self._session_state_policy,
            code=code,
        )
        self._session_state = update.state
        self._set_session_state_alert()

    def _on_session_state_alert(self, _event) -> None:  # noqa: ANN001
        if not self._active:
            return
        now_ns = self.clock.timestamp_ns()
        if self._session_state.phase is SessionStateDeliveryPhase.LIVE:
            self._begin_session_state_cycle()
            return
        if self._session_state.phase is SessionStateDeliveryPhase.WAITING:
            self._schedule_session_state_retry("response_timeout")
            return
        update = begin_session_state_retry(
            self._session_state,
            now_ns=now_ns,
            policy=self._session_state_policy,
        )
        self._session_state = update.state
        if update.disposition is SessionStateDeliveryDisposition.RETRY_STARTED:
            self._publish_session_state_request()

    def _set_session_state_alert(self) -> None:
        if not self._active:
            return
        self._cancel_session_state_alert()
        alert_at_ns = self._session_state.alert_at_ns
        if alert_at_ns is not None:
            self.clock.set_time_alert_ns(
                _EVIDENCE_SESSION_STATE_ALERT,
                alert_at_ns,
                callback=self._on_session_state_alert,
            )

    def _set_session_state_boundary_alert(self) -> None:
        if not self._active:
            return
        next_boundaries = tuple(
            item.next_transition_ns
            for item in self._session_state.watermarks
            if item.next_transition_ns is not None
        )
        self._cancel_session_state_alert()
        if next_boundaries:
            prior_attempt_expired_ns = (
                self._session_state.accepted_response.deadline_ts_ns + 1
                if self._session_state.accepted_response is not None
                else 0
            )
            self.clock.set_time_alert_ns(
                _EVIDENCE_SESSION_STATE_ALERT,
                max(
                    min(next_boundaries)
                    + self._session_state_policy.boundary_delivery_grace_ns,
                    prior_attempt_expired_ns,
                ),
                callback=self._on_session_state_alert,
            )

    def _cancel_session_state_alert(self) -> None:
        if _EVIDENCE_SESSION_STATE_ALERT in self.clock.timer_names():
            self.clock.cancel_timer(_EVIDENCE_SESSION_STATE_ALERT)

    def _reconcile_consumer_attachments(self, _event) -> None:  # noqa: ANN001
        if not self._active:
            return
        for requirement in self._requirements:
            key = requirement.stream_key
            if key in self._attached_stream_keys:
                continue
            try:
                self._port.subscribe(requirement)
            except Exception as exc:  # noqa: BLE001
                if key not in self._attachment_failure_keys:
                    self._attachment_failure_keys.add(key)
                    self.log.error(
                        "EVIDENCE_CONSUMER_REGISTRATION_FAILED"
                        f" | stream={key[0]}/{key[1]}/{key[2]}"
                        f" | error={type(exc).__name__}: {exc}",
                    )
                continue
            self._attached_stream_keys.add(key)
            if key in self._attachment_failure_keys:
                self._attachment_failure_keys.remove(key)
                self.log.info(
                    f"EVIDENCE_CONSUMER_REGISTRATION_RECOVERED | stream={key[0]}/{key[1]}/{key[2]}",
                )
                if self._started:
                    self._evaluate_key(key, self.clock.timestamp_ns())
        if len(self._attached_stream_keys) == len(self._requirements):
            if _EVIDENCE_CONSUMER_RETRY_TIMER in self.clock.timer_names():
                self.clock.cancel_timer(_EVIDENCE_CONSUMER_RETRY_TIMER)
        elif _EVIDENCE_CONSUMER_RETRY_TIMER not in self.clock.timer_names():
            self.clock.set_timer_ns(
                _EVIDENCE_CONSUMER_RETRY_TIMER,
                self._consumer_retry_interval_ns,
                callback=self._reconcile_consumer_attachments,
            )

    def _retain_calendar_context(
        self,
        event: _SessionContext,
    ) -> None:
        if event.calendar_id not in self._calendar_ids:
            return
        self._session_by_calendar[event.calendar_id] = event
        if self._started:
            now_ns = self.clock.timestamp_ns()
            for key in self._subscription_states:
                instrument_id = key[0]
                if self._calendar_by_instrument[instrument_id] == event.calendar_id:
                    self._evaluate_key(key, now_ns)

    def _observe(self, key: tuple[str, str, str], event_ts_ns: int) -> None:
        if key not in self._subscription_states:
            return
        receive_ts_ns = self.clock.timestamp_ns()
        if event_ts_ns < self._event_ts.get(key, -1):
            return
        previous_receive_ts_ns = self._receive_ts.get(key)
        self._learn_recency(key, previous_receive_ts_ns, receive_ts_ns)
        self._event_ts[key] = event_ts_ns
        self._receive_ts[key] = receive_ts_ns
        self._evaluate_key(key, receive_ts_ns)

    def _evaluate_all(self, _event) -> None:  # noqa: ANN001
        if not self._active:
            return
        now_ns = self.clock.timestamp_ns()
        for key in self._subscription_states:
            self._evaluate_key(key, now_ns)

    def _evaluate_key(self, key: tuple[str, str, str], now_ns: int) -> None:
        instrument_id, feed_kind, selector = key
        policy = self._policy_by_stream[(feed_kind, selector)]
        calendar_id = self._calendar_by_instrument[instrument_id]
        session = self._session_by_calendar.get(calendar_id)
        profile_key = self._profile_key(key, session)
        effective_policy = policy.effective(self._profiles.get(profile_key))
        effective_subscription_state = (
            "FAILED" if key in self._attachment_failure_keys else self._subscription_states[key]
        )
        assessment = assess_evidence(
            effective_policy,
            evaluated_ts_ns=now_ns,
            receive_ts_ns=self._receive_ts.get(key),
            subscription_state=effective_subscription_state,
            session_is_open=session.is_open if session is not None else None,
        )
        previous = self._states.get(key)
        if assessment.state == previous:
            return
        self._revisions[key] += 1
        revision = self._revisions[key]
        alignment = "UNKNOWN"
        if session is not None:
            alignment = "IN_SESSION" if session.is_open else "OUTSIDE_SESSION"
        event = EvidenceHealthEvent(
            event_id=f"evidence:{instrument_id}:{feed_kind}:{selector}:{revision}",
            instrument_id=instrument_id,
            calendar_id=calendar_id,
            feed_kind=feed_kind,
            selector=selector,
            state=assessment.state,
            previous_state=previous,
            reason=assessment.reason,
            fidelity="REPORTED" if key in self._event_ts else "UNAVAILABLE",
            subscription_state=effective_subscription_state,
            event_ts_ns=self._event_ts.get(key),
            receive_ts_ns=self._receive_ts.get(key),
            evaluated_ts_ns=now_ns,
            age_ms=assessment.age_ms,
            session_phase=session.phase if session is not None else None,
            session_trade_date=session.trade_date if session is not None else None,
            session_alignment=alignment,
            source=str(self.actor_id),
            policy_version=policy.version,
            revision=revision,
        )
        self.publish_signal(EVIDENCE_HEALTH_SIGNAL, event.to_signal_value())
        self._latest_events[key] = event
        self.log.info(
            f"EVIDENCE_HEALTH | instrument={instrument_id} | feed={feed_kind}/{selector}"
            f" | state={previous or 'UNINITIALIZED'}->{event.state}"
            f" | age_ms={event.age_ms} | session={event.session_phase or 'UNKNOWN'}"
            f" | thresholds_ms={effective_policy.fresh_for_ms}/"
            f"{effective_policy.stale_after_ms}/{effective_policy.unavailable_after_ms}"
            f" | reason={event.reason}",
        )
        self._states[key] = assessment.state

    def _publish_snapshot(self, value: str) -> None:
        try:
            request = EvidenceHealthSnapshotRequest.from_signal_value(value)
        except ValueError as exc:
            self.log.error(f"EVIDENCE_SNAPSHOT_REQUEST_REJECTED | error={type(exc).__name__}")
            return
        requested = set(request.instrument_ids)
        events = tuple(
            event
            for key, event in self._latest_events.items()
            if key[0] in requested and key[1] == request.feed_kind and key[2] == request.selector
        )
        snapshot = EvidenceHealthSnapshot(
            requester=request.requester,
            source=str(self.actor_id),
            events=events,
            snapshot_ts_ns=self.clock.timestamp_ns(),
        )
        self.publish_signal(EVIDENCE_HEALTH_SNAPSHOT_SIGNAL, snapshot.to_signal_value())

    def _learn_recency(
        self,
        key: tuple[str, str, str],
        previous_receive_ts_ns: int | None,
        receive_ts_ns: int,
    ) -> None:
        instrument_id, feed_kind, selector = key
        policy = self._policy_by_stream[(feed_kind, selector)]
        calendar_id = self._calendar_by_instrument[instrument_id]
        session = self._session_by_calendar.get(calendar_id)
        if (
            not policy.adaptive
            or previous_receive_ts_ns is None
            or session is None
            or not session.is_open
            or self._subscription_states[key] not in {"SUBSCRIBED", "ACTIVE"}
            or self._states.get(key) not in {"HEALTHY", "DEGRADED"}
        ):
            return
        profile_key = self._profile_key(key, session)
        assert profile_key is not None
        profile = self._profiles.setdefault(profile_key, RecencyProfile())
        interval_ms = max(0, (receive_ts_ns - previous_receive_ts_ns) // 1_000_000)
        profile.observe(interval_ms, receive_ts_ns, policy.decay_factor)
        self._dirty_profiles.add(profile_key)
        if profile.sample_count % self._profile_checkpoint_samples == 0:
            self._publish_profile(profile_key)

    def _profile_key(
        self,
        key: tuple[str, str, str],
        session: _SessionContext | None,
    ) -> tuple[str, str, str, str, str, str] | None:
        if session is None:
            return None
        policy = self._policy_by_stream[(key[1], key[2])]
        return (*key, self._provider_id, session.phase, policy.version)

    def _publish_profile(self, key: tuple[str, str, str, str, str, str]) -> None:
        profile = self._profiles[key]
        instrument_id, feed_kind, selector, provider_id, session_phase, policy_version = key
        policy = self._policy_by_stream[(feed_kind, selector)]
        effective = policy.effective(profile)
        assert profile.last_observed_ns is not None
        event = EvidenceRecencyProfileEvent(
            event_id=(
                f"evidence-profile:{instrument_id}:{feed_kind}:{selector}:"
                f"{provider_id}:{session_phase}:{profile.sample_count}"
            ),
            instrument_id=instrument_id,
            feed_kind=feed_kind,
            selector=selector,
            provider_id=provider_id,
            session_phase=session_phase,
            policy_version=policy_version,
            sample_count=profile.sample_count,
            mean_interval_ms=profile.mean_interval_ms,
            variance_ms2=profile.variance_ms2,
            last_observed_ns=profile.last_observed_ns,
            fresh_for_ms=effective.fresh_for_ms,
            stale_after_ms=effective.stale_after_ms,
            unavailable_after_ms=effective.unavailable_after_ms,
            source=str(self.actor_id),
        )
        self.publish_signal(EVIDENCE_RECENCY_PROFILE_SIGNAL, event.to_signal_value())
        self._dirty_profiles.discard(key)
