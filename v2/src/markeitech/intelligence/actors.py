from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId, CustomData, DataType

from markeitech.acquisition import FeedKind, FeedRequirement, NautilusSubscriptionPort
from markeitech.intelligence.calendar_delivery import (
    ProjectionRequestPhase,
    ProjectionRequestState,
    ProjectionRetryPolicy,
    begin_projection_retry,
    classify_projection_response,
    ready_projection_state,
    retain_pending_calendars,
    schedule_projection_retry,
    start_projection_cycle,
    stop_projection_state,
    terminal_projection_state,
)
from markeitech.intelligence.calendar_messages import (
    CALENDAR_PROJECTION_REQUEST_TYPE_NAME,
    CALENDAR_PROJECTION_RESPONSE_TYPE_NAME,
    CALENDAR_TRANSITION_TYPE_NAME,
    CalendarProjectionFailure,
    CalendarProjectionRequest,
    CalendarProjectionResponse,
    CalendarTransition,
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
    CalendarProjectionView,
    CanonicalCalendar,
    CanonicalSessionSnapshot,
    canonical_definition_from_config,
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
_EVIDENCE_CALENDAR_RETRY_ALERT = "evidence-health-calendar-projection-retry"


@dataclass(frozen=True, slots=True)
class _SessionContext:
    calendar_id: str
    trade_date: str | None
    phase: str
    is_open: bool


class SessionStateActorConfig(DataActorConfig):
    def __new__(
        cls,
        calendars: list[dict[str, object]],
        evaluation_interval_ms: int,
        source_epoch: str,
        maximum_projection_days: int,
        maximum_calendars_per_request: int,
        actor_id: str | ActorId = "SESSION-STATE",
    ) -> SessionStateActorConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        obj = super().__new__(cls, actor_id=resolved)
        obj.calendars = tuple(calendars)
        obj.evaluation_interval_ms = evaluation_interval_ms
        obj.source_epoch = source_epoch
        obj.maximum_projection_days = maximum_projection_days
        obj.maximum_calendars_per_request = maximum_calendars_per_request
        return obj


class SessionStateActor(DataActor):
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
        self._request_type = DataType(CALENDAR_PROJECTION_REQUEST_TYPE_NAME)
        self._response_type = DataType(CALENDAR_PROJECTION_RESPONSE_TYPE_NAME)
        self._transition_type = DataType(CALENDAR_TRANSITION_TYPE_NAME)
        self._snapshots: dict[str, CanonicalSessionSnapshot] = {}
        self._revisions: defaultdict[str, int] = defaultdict(int)
        self._projection_requests = 0
        self._projection_rejections = 0
        self._projection_failures = 0
        self._started = False

    def on_start(self) -> None:
        self.subscribe_data(self._request_type)
        self.subscribe_signal(PERSISTENCE_READY_SIGNAL)
        self.publish_signal(
            PERSISTENCE_READY_REQUEST_SIGNAL,
            PersistenceReadyRequest(requester=str(self.actor_id)).to_signal_value(),
        )

    def on_data(self, data) -> None:  # noqa: ANN001
        payload = data.data if isinstance(data, CustomData) else data
        if isinstance(payload, CalendarProjectionRequest):
            self._publish_projection(payload)

    def on_signal(self, signal: Signal) -> None:
        if signal.name != PERSISTENCE_READY_SIGNAL:
            return
        try:
            PersistenceReadyEvent.from_signal_value(signal.value)
        except ValueError as exc:
            self.log.error(f"SESSION_PERSISTENCE_READY_REJECTED | error={type(exc).__name__}")
            return
        if self._started:
            return
        self._started = True
        self._evaluate(None)
        self.clock.set_timer_ns(_SESSION_TIMER, self._interval_ns, callback=self._evaluate)

    def on_stop(self) -> None:
        self.unsubscribe_data(self._request_type)
        self.unsubscribe_signal(PERSISTENCE_READY_SIGNAL)
        for timer_name in (_SESSION_TIMER, _SESSION_BOUNDARY_ALERT):
            if timer_name in self.clock.timer_names():
                self.clock.cancel_timer(timer_name)
        self.log.info(
            f"SESSION_STATE_STOPPED | calendars={len(self._calendars)}"
            f" | transitions={sum(self._revisions.values())}"
            f" | projection_requests={self._projection_requests}"
            f" | projection_rejections={self._projection_rejections}"
            f" | projection_failures={self._projection_failures}",
        )

    def _evaluate(self, _event) -> None:  # noqa: ANN001
        now_ns = self.clock.timestamp_ns()
        next_boundary_ns: int | None = None
        for calendar_id, calendar in self._calendars.items():
            snapshot = calendar.evaluate(now_ns)
            previous = self._snapshots.get(calendar_id)
            identity = (
                snapshot.trade_date,
                snapshot.phase_memberships,
                snapshot.market_state,
                snapshot.segment_open_ns,
                snapshot.segment_close_ns,
                snapshot.next_transition_ns,
                snapshot.definition_digest,
            )
            previous_identity = None if previous is None else (
                previous.trade_date,
                previous.phase_memberships,
                previous.market_state,
                previous.segment_open_ns,
                previous.segment_close_ns,
                previous.next_transition_ns,
                previous.definition_digest,
            )
            if identity == previous_identity:
                self._snapshots[calendar_id] = snapshot
            else:
                self._revisions[calendar_id] += 1
                revision = self._revisions[calendar_id]
                definition = self._definitions[calendar_id]
                event = CalendarTransition(
                    event_id=f"calendar:{self._source_epoch}:{calendar_id}:{revision}",
                    calendar_id=calendar_id,
                    schedule_version=snapshot.schedule_version,
                    definition_version=snapshot.definition_version,
                    definition_digest=snapshot.definition_digest,
                    effective_from_ns=definition.effective_from_ns,
                    trade_date=snapshot.trade_date.isoformat() if snapshot.trade_date else None,
                    previous_trade_date=(
                        previous.trade_date.isoformat()
                        if previous is not None and previous.trade_date is not None
                        else None
                    ),
                    phase_memberships=snapshot.phase_memberships,
                    previous_phase_memberships=(
                        previous.phase_memberships if previous is not None else ()
                    ),
                    market_state=snapshot.market_state,
                    previous_market_state=(
                        previous.market_state if previous is not None else None
                    ),
                    segment_open_ns=snapshot.segment_open_ns,
                    segment_close_ns=snapshot.segment_close_ns,
                    next_transition_ns=snapshot.next_transition_ns,
                    source=str(self.actor_id),
                    source_epoch=self._source_epoch,
                    effective_ts_ns=now_ns,
                    evaluated_ts_ns=now_ns,
                    published_ts_ns=self.clock.timestamp_ns(),
                    reason=(
                        "definition activated" if previous is None else "calendar state changed"
                    ),
                    revision=revision,
                    previous_revision=revision - 1 if revision > 1 else None,
                )
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
                self._snapshots[calendar_id] = snapshot
            if snapshot.next_transition_ns is not None and snapshot.next_transition_ns > now_ns:
                next_boundary_ns = (
                    snapshot.next_transition_ns
                    if next_boundary_ns is None
                    else min(next_boundary_ns, snapshot.next_transition_ns)
                )
        self._schedule_boundary(next_boundary_ns)

    def _schedule_boundary(self, next_boundary_ns: int | None) -> None:
        if _SESSION_BOUNDARY_ALERT in self.clock.timer_names():
            self.clock.cancel_timer(_SESSION_BOUNDARY_ALERT)
        if next_boundary_ns is not None:
            self.clock.set_time_alert_ns(
                _SESSION_BOUNDARY_ALERT,
                next_boundary_ns,
                callback=self._evaluate,
            )

    def _publish_projection(self, request: CalendarProjectionRequest) -> None:
        self._projection_requests += 1
        requested_days = (request.end_ns - request.start_ns) // 86_400_000_000_000 + 1
        requested = tuple(request.calendar_ids)
        unavailable = tuple(item for item in requested if item not in self._calendars)
        status = "READY"
        projections = []
        failures = []
        retry_at_ns = None
        if not self._started:
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
        self.publish_data(self._response_type, CustomData(self._response_type, response))


class EvidenceHealthActorConfig(DataActorConfig):
    def __new__(
        cls,
        feeds: list[dict[str, str]],
        policies: list[dict[str, object]],
        evaluation_interval_ms: int,
        consumer_retry_interval_ms: int,
        provider_id: str,
        profile_checkpoint_samples: int,
        recency_profiles: list[dict[str, object]],
        projection_lookback_days: int,
        projection_lookahead_days: int,
        expected_calendar_digests: dict[str, str],
        calendar_source: str,
        calendar_source_epoch: str,
        projection_retry: dict[str, int],
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
        obj.projection_lookback_days = projection_lookback_days
        obj.projection_lookahead_days = projection_lookahead_days
        obj.expected_calendar_digests = dict(expected_calendar_digests)
        obj.calendar_source = calendar_source
        obj.calendar_source_epoch = calendar_source_epoch
        obj.projection_retry = dict(projection_retry)
        return obj


class EvidenceHealthActor(DataActor):
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
        self._projection_lookback_ns = config.projection_lookback_days * 86_400_000_000_000
        self._projection_lookahead_ns = config.projection_lookahead_days * 86_400_000_000_000
        self._expected_calendar_digests = dict(config.expected_calendar_digests)
        self._projection_policy = ProjectionRetryPolicy.from_config(config.projection_retry)
        self._projection_state = ProjectionRequestState.idle(
            requester=str(self.actor_id),
            expected_source=config.calendar_source,
            expected_source_epoch=config.calendar_source_epoch,
        )
        self._projection_counts: defaultdict[str, int] = defaultdict(int)
        self._provider_id = config.provider_id
        self._profile_checkpoint_samples = config.profile_checkpoint_samples
        self._port = NautilusSubscriptionPort(self)
        self._event_ts: dict[tuple[str, str, str], int] = {}
        self._receive_ts: dict[tuple[str, str, str], int] = {}
        self._subscription_states: dict[tuple[str, str, str], str] = {
            item.stream_key: "REQUESTED" for item in self._requirements
        }
        self._session_by_calendar: dict[str, _SessionContext | CalendarTransition] = {}
        self._calendar_ids = tuple(sorted(set(self._calendar_by_instrument.values())))
        self._calendar_request_type = DataType(CALENDAR_PROJECTION_REQUEST_TYPE_NAME)
        self._calendar_response_type = DataType(CALENDAR_PROJECTION_RESPONSE_TYPE_NAME)
        self._calendar_transition_type = DataType(CALENDAR_TRANSITION_TYPE_NAME)
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
        self._started = False

    def on_start(self) -> None:
        for signal_name in (
            PERSISTENCE_READY_SIGNAL,
            ACQUISITION_STREAM_SIGNAL,
            EVIDENCE_HEALTH_SNAPSHOT_REQUEST_SIGNAL,
        ):
            self.subscribe_signal(signal_name)
        self.subscribe_data(self._calendar_response_type)
        self.subscribe_data(self._calendar_transition_type)
        self._reconcile_consumer_attachments(None)
        self._begin_calendar_projection_cycle()
        self.publish_signal(
            PERSISTENCE_READY_REQUEST_SIGNAL,
            PersistenceReadyRequest(requester=str(self.actor_id)).to_signal_value(),
        )

    def on_signal(self, signal: Signal) -> None:
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
        payload = data.data if isinstance(data, CustomData) else data
        if isinstance(payload, CalendarTransition):
            expected_digest = self._expected_calendar_digests.get(payload.calendar_id)
            if (
                expected_digest != payload.definition_digest
                or payload.source != self._projection_state.expected_source
                or payload.source_epoch != self._projection_state.expected_source_epoch
            ):
                self._projection_counts["conflict"] += 1
                self.log.error(
                    "EVIDENCE_CALENDAR_TRANSITION_CONFLICT"
                    f" | calendar_id={payload.calendar_id}",
                )
                return
            self._retain_calendar_context(payload)
            return
        if not isinstance(payload, CalendarProjectionResponse):
            return
        self._observe_calendar_projection(payload)

    def on_quote(self, quote) -> None:  # noqa: ANN001
        self._observe((str(quote.instrument_id), "quotes", "default"), quote.ts_event)

    def on_bar(self, bar) -> None:  # noqa: ANN001
        instrument_id = str(bar.bar_type.instrument_id)
        keys = [
            key for key in self._subscription_states if key[0] == instrument_id and key[1] == "bars"
        ]
        for key in keys:
            self._observe(key, bar.ts_event)

    def on_stop(self) -> None:
        self._projection_state = stop_projection_state(self._projection_state)
        for profile_key in sorted(self._dirty_profiles):
            self._publish_profile(profile_key)
        for signal_name in (
            PERSISTENCE_READY_SIGNAL,
            ACQUISITION_STREAM_SIGNAL,
            EVIDENCE_HEALTH_SNAPSHOT_REQUEST_SIGNAL,
        ):
            self.unsubscribe_signal(signal_name)
        self.unsubscribe_data(self._calendar_response_type)
        self.unsubscribe_data(self._calendar_transition_type)
        if _EVIDENCE_TIMER in self.clock.timer_names():
            self.clock.cancel_timer(_EVIDENCE_TIMER)
        if _EVIDENCE_CONSUMER_RETRY_TIMER in self.clock.timer_names():
            self.clock.cancel_timer(_EVIDENCE_CONSUMER_RETRY_TIMER)
        if _EVIDENCE_CALENDAR_RETRY_ALERT in self.clock.timer_names():
            self.clock.cancel_timer(_EVIDENCE_CALENDAR_RETRY_ALERT)
        self.log.info(
            f"EVIDENCE_HEALTH_STOPPED | streams={len(self._requirements)}"
            f" | transitions={sum(self._revisions.values())}"
            f" | projection_state={self._projection_state.phase.value}"
            f" | projection_requests={self._projection_counts['requests']}"
            f" | projection_timeouts={self._projection_counts['timeouts']}"
            f" | projection_stale={self._projection_counts['stale']}"
            f" | projection_terminal={self._projection_counts['terminal']}",
        )

    def _release_startup(self) -> None:
        if self._started:
            return
        self._started = True
        self._evaluate_all(None)
        self.clock.set_timer_ns(_EVIDENCE_TIMER, self._interval_ns, callback=self._evaluate_all)

    def _reconcile_consumer_attachments(self, _event) -> None:  # noqa: ANN001
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

    def _begin_calendar_projection_cycle(self) -> None:
        missing = tuple(
            calendar_id
            for calendar_id in self._calendar_ids
            if calendar_id not in self._session_by_calendar
        )
        if not missing:
            return
        now_ns = self.clock.timestamp_ns()
        self._projection_state = start_projection_cycle(
            self._projection_state,
            calendar_ids=missing,
            start_ns=max(0, now_ns - self._projection_lookback_ns),
            end_ns=now_ns + self._projection_lookahead_ns,
            now_ns=now_ns,
            policy=self._projection_policy,
        )
        if self._projection_state.phase is ProjectionRequestPhase.WAITING:
            self._publish_calendar_projection_request()

    def _publish_calendar_projection_request(self) -> None:
        state = self._projection_state
        if (
            state.phase is not ProjectionRequestPhase.WAITING
            or state.request_id is None
            or state.start_ns is None
            or state.end_ns is None
        ):
            return
        self._set_calendar_projection_alert()
        request = CalendarProjectionRequest(
            request_id=state.request_id,
            requester=state.requester,
            calendar_ids=state.pending_calendar_ids,
            start_ns=state.start_ns,
            end_ns=state.end_ns,
            requested_ts_ns=self.clock.timestamp_ns(),
        )
        self._projection_counts["requests"] += 1
        self.publish_data(
            self._calendar_request_type,
            CustomData(self._calendar_request_type, request),
        )

    def _observe_calendar_projection(self, response: CalendarProjectionResponse) -> None:
        disposition = classify_projection_response(self._projection_state, response)
        if disposition != "ACCEPT":
            self._projection_counts[disposition.lower()] += 1
            return
        self._cancel_calendar_projection_alert()
        state = self._projection_state
        accepted_ids: set[str] = set()
        now_ns = self.clock.timestamp_ns()
        for projection in response.projections:
            expected_digest = self._expected_calendar_digests.get(projection.calendar_id)
            if (
                expected_digest != projection.definition_digest
                or state.start_ns is None
                or state.end_ns is None
                or projection.coverage_start_ns > state.start_ns
                or projection.coverage_end_ns < state.end_ns
            ):
                self._projection_counts["conflict"] += 1
                self._projection_state = terminal_projection_state(
                    state,
                    "projection_identity_conflict",
                )
                self._projection_counts["terminal"] += 1
                self.log.error(
                    "EVIDENCE_CALENDAR_PROJECTION_CONFLICT"
                    f" | calendar_id={projection.calendar_id}",
                )
                return
            snapshot = CalendarProjectionView(projection).evaluate(now_ns)
            accepted_ids.add(projection.calendar_id)
            self._retain_calendar_context(
                _SessionContext(
                    calendar_id=projection.calendar_id,
                    trade_date=(
                        snapshot.trade_date.isoformat() if snapshot.trade_date is not None else None
                    ),
                    phase=snapshot.phase,
                    is_open=snapshot.is_open,
                ),
            )
        remaining = tuple(
            item for item in state.pending_calendar_ids if item not in accepted_ids
        )
        if not remaining:
            self._projection_state = ready_projection_state(state)
            self._projection_counts["accepted"] += 1
            return
        failures = {item.calendar_id: item for item in response.failures}
        retryable = bool(remaining) and all(
            calendar_id in failures and failures[calendar_id].retryable
            for calendar_id in remaining
        )
        if response.status == "NOT_READY" or retryable:
            self._projection_state = retain_pending_calendars(state, remaining)
            self._projection_state = schedule_projection_retry(
                self._projection_state,
                now_ns=now_ns,
                policy=self._projection_policy,
                retry_at_ns=response.retry_at_ns,
            )
            self._finish_calendar_projection_transition()
            return
        self._projection_state = terminal_projection_state(
            state,
            "projection_rejected" if response.status == "REJECTED" else "projection_unavailable",
            rejected=response.status == "REJECTED",
        )
        self._projection_counts["terminal"] += 1
        self.log.error(
            f"EVIDENCE_CALENDAR_PROJECTION_TERMINAL | status={response.status}"
            f" | pending={','.join(remaining)}",
        )

    def _on_calendar_projection_alert(self, _event) -> None:  # noqa: ANN001
        state = self._projection_state
        if state.phase is ProjectionRequestPhase.STOPPED:
            return
        now_ns = self.clock.timestamp_ns()
        if state.alert_at_ns is None or now_ns < state.alert_at_ns:
            return
        if state.phase is ProjectionRequestPhase.WAITING:
            self._projection_counts["timeouts"] += 1
            self._projection_state = schedule_projection_retry(
                state,
                now_ns=now_ns,
                policy=self._projection_policy,
                retry_at_ns=None,
            )
            self._finish_calendar_projection_transition()
            return
        if state.phase is ProjectionRequestPhase.BACKOFF:
            self._projection_state = begin_projection_retry(
                state,
                now_ns=now_ns,
                policy=self._projection_policy,
            )
            self._publish_calendar_projection_request()

    def _finish_calendar_projection_transition(self) -> None:
        if self._projection_state.phase is ProjectionRequestPhase.BACKOFF:
            self._projection_counts["retries"] += 1
            self._set_calendar_projection_alert()
            return
        if self._projection_state.phase in {
            ProjectionRequestPhase.FAILED,
            ProjectionRequestPhase.REJECTED,
        }:
            self._projection_counts["terminal"] += 1
            self.log.error(
                "EVIDENCE_CALENDAR_PROJECTION_EXHAUSTED"
                f" | code={self._projection_state.terminal_code}",
            )

    def _set_calendar_projection_alert(self) -> None:
        self._cancel_calendar_projection_alert()
        alert_at_ns = self._projection_state.alert_at_ns
        if alert_at_ns is not None:
            self.clock.set_time_alert_ns(
                _EVIDENCE_CALENDAR_RETRY_ALERT,
                alert_at_ns,
                callback=self._on_calendar_projection_alert,
            )

    def _cancel_calendar_projection_alert(self) -> None:
        if _EVIDENCE_CALENDAR_RETRY_ALERT in self.clock.timer_names():
            self.clock.cancel_timer(_EVIDENCE_CALENDAR_RETRY_ALERT)

    def _retain_calendar_context(
        self,
        event: _SessionContext | CalendarTransition,
    ) -> None:
        if event.calendar_id not in self._calendar_ids:
            return
        self._session_by_calendar[event.calendar_id] = event
        if not set(self._calendar_ids) - set(self._session_by_calendar):
            if self._projection_state.phase in {
                ProjectionRequestPhase.WAITING,
                ProjectionRequestPhase.BACKOFF,
            }:
                self._cancel_calendar_projection_alert()
                self._projection_state = ready_projection_state(self._projection_state)
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
        session: _SessionContext | CalendarTransition | None,
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
