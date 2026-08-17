from __future__ import annotations

from collections import defaultdict

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId

from markeitech.acquisition import FeedKind, FeedRequirement, NautilusSubscriptionPort
from markeitech.intelligence.evidence import EvidencePolicy, RecencyProfile, assess_evidence
from markeitech.intelligence.messages import (
    EVIDENCE_HEALTH_SIGNAL,
    EVIDENCE_RECENCY_PROFILE_SIGNAL,
    SESSION_STATE_SIGNAL,
    EvidenceHealthEvent,
    EvidenceRecencyProfileEvent,
    SessionStateEvent,
)
from markeitech.intelligence.session import SessionCalendar, definition_from_config
from markeitech.system.messages import (
    ACQUISITION_STREAM_SIGNAL,
    PERSISTENCE_READY_REQUEST_SIGNAL,
    PERSISTENCE_READY_SIGNAL,
    AcquisitionStreamEvent,
    PersistenceReadyEvent,
    PersistenceReadyRequest,
)

_SESSION_TIMER = "session-state-evaluation"
_EVIDENCE_TIMER = "evidence-health-evaluation"
_EVIDENCE_CONSUMER_RETRY_TIMER = "evidence-health-consumer-registration-retry"


class SessionStateActorConfig(DataActorConfig):
    def __new__(
        cls,
        calendars: list[dict[str, object]],
        evaluation_interval_ms: int,
        actor_id: str | ActorId = "SESSION-STATE",
    ) -> SessionStateActorConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        obj = super().__new__(cls, actor_id=resolved)
        obj.calendars = tuple(calendars)
        obj.evaluation_interval_ms = evaluation_interval_ms
        return obj


class SessionStateActor(DataActor):
    def __init__(self, config: SessionStateActorConfig) -> None:
        super().__init__(config)
        self._calendars = tuple(
            SessionCalendar(definition_from_config(dict(value))) for value in config.calendars
        )
        self._interval_ns = config.evaluation_interval_ms * 1_000_000
        self._snapshots = {}
        self._revisions: defaultdict[str, int] = defaultdict(int)
        self._started = False

    def on_start(self) -> None:
        self.subscribe_signal(PERSISTENCE_READY_SIGNAL)
        self.publish_signal(
            PERSISTENCE_READY_REQUEST_SIGNAL,
            PersistenceReadyRequest(requester=str(self.actor_id)).to_signal_value(),
        )

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
        self.unsubscribe_signal(PERSISTENCE_READY_SIGNAL)
        if _SESSION_TIMER in self.clock.timer_names():
            self.clock.cancel_timer(_SESSION_TIMER)
        self.log.info(
            f"SESSION_STATE_STOPPED | calendars={len(self._calendars)}"
            f" | transitions={sum(self._revisions.values())}",
        )

    def _evaluate(self, _event) -> None:  # noqa: ANN001
        now_ns = self.clock.timestamp_ns()
        for calendar in self._calendars:
            snapshot = calendar.evaluate(now_ns)
            previous = self._snapshots.get(snapshot.calendar_id)
            identity = (snapshot.trade_date, snapshot.phase)
            previous_identity = None if previous is None else (previous.trade_date, previous.phase)
            if identity == previous_identity:
                self._snapshots[snapshot.calendar_id] = snapshot
                continue
            self._revisions[snapshot.calendar_id] += 1
            revision = self._revisions[snapshot.calendar_id]
            event = SessionStateEvent(
                event_id=f"session:{snapshot.calendar_id}:{revision}",
                calendar_id=snapshot.calendar_id,
                schedule_version=snapshot.schedule_version,
                timezone=snapshot.timezone,
                trade_date=snapshot.trade_date.isoformat() if snapshot.trade_date else None,
                phase=snapshot.phase,
                previous_phase=previous.phase if previous is not None else None,
                is_open=snapshot.is_open,
                phase_open_ns=snapshot.phase_open_ns,
                phase_close_ns=snapshot.phase_close_ns,
                next_transition_ns=snapshot.next_transition_ns,
                source=str(self.actor_id),
                reason=(
                    "initial session evaluation" if previous is None else "session phase changed"
                ),
                revision=revision,
            )
            self.publish_signal(SESSION_STATE_SIGNAL, event.to_signal_value())
            self.log.info(
                f"SESSION_STATE | calendar={event.calendar_id} | trade_date={event.trade_date}"
                f" | phase={event.previous_phase or 'UNINITIALIZED'}->{event.phase}"
                f" | next_transition_ns={event.next_transition_ns}",
            )
            self._snapshots[snapshot.calendar_id] = snapshot


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
        self._provider_id = config.provider_id
        self._profile_checkpoint_samples = config.profile_checkpoint_samples
        self._port = NautilusSubscriptionPort(self)
        self._event_ts: dict[tuple[str, str, str], int] = {}
        self._receive_ts: dict[tuple[str, str, str], int] = {}
        self._subscription_states: dict[tuple[str, str, str], str] = {
            item.stream_key: "REQUESTED" for item in self._requirements
        }
        self._session_by_calendar: dict[str, SessionStateEvent] = {}
        self._states: dict[tuple[str, str, str], str] = {}
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
            SESSION_STATE_SIGNAL,
        ):
            self.subscribe_signal(signal_name)
        self._reconcile_consumer_attachments(None)
        self.publish_signal(
            PERSISTENCE_READY_REQUEST_SIGNAL,
            PersistenceReadyRequest(requester=str(self.actor_id)).to_signal_value(),
        )

    def on_signal(self, signal: Signal) -> None:
        if signal.name == PERSISTENCE_READY_SIGNAL:
            try:
                PersistenceReadyEvent.from_signal_value(signal.value)
            except ValueError as exc:
                self.log.error(f"EVIDENCE_PERSISTENCE_READY_REJECTED | error={type(exc).__name__}")
                return
            self._release_startup()
            return
        if signal.name == SESSION_STATE_SIGNAL:
            try:
                event = SessionStateEvent.from_signal_value(signal.value)
            except ValueError as exc:
                self.log.error(f"EVIDENCE_SESSION_REJECTED | error={type(exc).__name__}")
                return
            self._session_by_calendar[event.calendar_id] = event
            if self._started:
                now_ns = self.clock.timestamp_ns()
                for key in self._subscription_states:
                    instrument_id = key[0]
                    if self._calendar_by_instrument[instrument_id] == event.calendar_id:
                        self._evaluate_key(key, now_ns)
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
        for profile_key in sorted(self._dirty_profiles):
            self._publish_profile(profile_key)
        for signal_name in (
            PERSISTENCE_READY_SIGNAL,
            ACQUISITION_STREAM_SIGNAL,
            SESSION_STATE_SIGNAL,
        ):
            self.unsubscribe_signal(signal_name)
        if _EVIDENCE_TIMER in self.clock.timer_names():
            self.clock.cancel_timer(_EVIDENCE_TIMER)
        if _EVIDENCE_CONSUMER_RETRY_TIMER in self.clock.timer_names():
            self.clock.cancel_timer(_EVIDENCE_CONSUMER_RETRY_TIMER)
        self.log.info(
            f"EVIDENCE_HEALTH_STOPPED | streams={len(self._requirements)}"
            f" | transitions={sum(self._revisions.values())}",
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
        self.log.info(
            f"EVIDENCE_HEALTH | instrument={instrument_id} | feed={feed_kind}/{selector}"
            f" | state={previous or 'UNINITIALIZED'}->{event.state}"
            f" | age_ms={event.age_ms} | session={event.session_phase or 'UNKNOWN'}"
            f" | thresholds_ms={effective_policy.fresh_for_ms}/"
            f"{effective_policy.stale_after_ms}/{effective_policy.unavailable_after_ms}"
            f" | reason={event.reason}",
        )
        self._states[key] = assessment.state

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
        session: SessionStateEvent | None,
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
