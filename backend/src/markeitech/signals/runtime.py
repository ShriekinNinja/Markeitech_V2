from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from threading import Condition, Thread
from traceback import format_exc
from typing import Protocol

from markeitech.domain.base import require_utc
from markeitech.domain.market_data import OneMinuteBar
from markeitech.persistence.feature_pipeline import CommittedFeatureRevision
from markeitech.signals.aggression import (
    AggressionEvaluationStatus,
    evaluate_aggression_window,
    evaluate_bar_impulse_window,
)
from markeitech.signals.arming import (
    build_armed_location_signal,
    invalidate_ended_location_signal,
    restore_location_episode,
)
from markeitech.signals.composition import (
    BoundedFeatureCommitHandoff,
    CommittedFeatureState,
)
from markeitech.signals.config import SignalDefinitionConfig, SignalRuntimeConfig
from markeitech.signals.contracts import (
    LocationQualification,
    LocationQualificationStatus,
    SignalConfirmationContext,
    SignalConfirmationMethod,
    SignalSnapshot,
    SignalStatus,
    SignalTransitionEvent,
)
from markeitech.signals.direction import (
    CommittedMarketContextBundle,
    DirectionQualification,
    DirectionQualificationStatus,
    DirectionRegimeTracker,
)
from markeitech.signals.episode import (
    LocationEpisodeDecision,
    LocationEpisodeEventType,
    LocationEpisodeObservation,
    LocationEpisodeTracker,
)
from markeitech.signals.lifecycle import transition_signal
from markeitech.signals.location import qualify_location
from markeitech.signals.projection import (
    SignalLifecycleProjection,
    SignalOperatorProjection,
    SignalRuntimeProjection,
    SignalRuntimeProjectionKind,
)


class SignalStateStore(Protocol):
    def load_signals(
        self,
        *,
        instrument_id: str | None = None,
        definition_id: str | None = None,
        status: SignalStatus | None = None,
    ) -> tuple[SignalSnapshot, ...]: ...

    def save_signal_candidate_and_transition(
        self,
        candidate: SignalSnapshot,
        event: SignalTransitionEvent,
    ) -> object: ...

    def replace_signal_with_armed_candidate(
        self,
        ended_event: SignalTransitionEvent,
        candidate: SignalSnapshot,
        armed_event: SignalTransitionEvent,
    ) -> object: ...

    def apply_signal_transition(self, event: SignalTransitionEvent) -> object: ...


class ProductSessionResolver(Protocol):
    def session_window(
        self,
        instrument_id: str,
        timestamp: datetime,
    ) -> tuple[datetime, datetime]: ...


class AggressionObservationStore(Protocol):
    @property
    def snapshot(self) -> object: ...

    def bars(
        self,
        instrument_id: str,
        source: str,
        *,
        through_ts: datetime | None = None,
    ) -> tuple[OneMinuteBar, ...]: ...


class LiveSignalRuntimeStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass(frozen=True)
class SignalEvaluationEvent:
    instrument_id: str
    definition_id: str
    evaluation_ts: datetime
    direction_status: DirectionQualificationStatus
    location_status: LocationQualificationStatus | None
    episode_event: LocationEpisodeEventType | None
    signal_id: str | None
    signal_status: SignalStatus | None
    lifecycle_events: tuple[SignalTransitionEvent, ...] = ()
    aggression_status: AggressionEvaluationStatus | None = None
    confirmation_method: SignalConfirmationMethod | None = None
    elapsed_observation_bars: int | None = None


@dataclass(frozen=True)
class _PersistedSignalDecision:
    current: SignalSnapshot | None
    lifecycle_events: tuple[SignalTransitionEvent, ...] = ()


@dataclass(frozen=True)
class _ConfirmationGate:
    direction_status: DirectionQualificationStatus
    location_status: LocationQualificationStatus
    episode_event: LocationEpisodeEventType
    is_open: bool


@dataclass(frozen=True)
class LiveSignalRuntimeSnapshot:
    status: LiveSignalRuntimeStatus
    startup_watermark: datetime | None
    restored_open_signal_count: int
    processed_revision_count: int
    stale_evaluation_count: int
    evaluation_count: int
    lifecycle_write_count: int
    open_signal_count: int
    projection_rejected_count: int
    projection_callback_error_count: int
    confirmation_evaluation_count: int
    triggered_signal_count: int
    expired_signal_count: int
    observation_accepted_bar_count: int
    observation_retained_bar_count: int
    observation_conflicting_retry_count: int
    last_event: SignalEvaluationEvent | None
    last_error: str | None
    failure_phase: str | None
    failure_input_identity: str | None
    last_successful_commit_sequence: int | None
    last_traceback: str | None


class LiveSignalRuntime:
    """Consumes durable feature revisions and owns live Direction/Location state."""

    def __init__(
        self,
        config: SignalRuntimeConfig,
        store: SignalStateStore,
        session_resolver: ProductSessionResolver,
        handoff: BoundedFeatureCommitHandoff,
        *,
        observation_store: AggressionObservationStore | None = None,
        role_resolver: Callable[[str], str] | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        on_evaluation: Callable[[SignalEvaluationEvent], None] | None = None,
        on_projection: Callable[[SignalOperatorProjection], bool] | None = None,
    ) -> None:
        enabled_ids = {
            definition_id
            for values in config.enabled_definition_ids_by_instrument.values()
            for definition_id in values
        }
        self._definitions = {
            item.definition_id: item
            for item in config.definitions
            if item.definition_id in enabled_ids
        }
        if any(item.location_policy is None for item in self._definitions.values()):
            raise ValueError("live Direction/Location definitions require location policy")
        if any(item.aggression_policy is not None for item in self._definitions.values()) and (
            observation_store is None or role_resolver is None
        ):
            raise ValueError("live Aggression definitions require observations and role resolver")
        self._config = config
        self._store = store
        self._session_resolver = session_resolver
        self._handoff = handoff
        self._clock = clock
        self._on_evaluation = on_evaluation
        self._on_projection = on_projection
        self._observation_store = observation_store
        self._role_resolver = role_resolver
        self._feature_state = CommittedFeatureState()
        self._direction_trackers = {
            key: DirectionRegimeTracker(value) for key, value in self._definitions.items()
        }
        self._episode_trackers = {
            key: LocationEpisodeTracker(value) for key, value in self._definitions.items()
        }
        self._open_signals: dict[tuple[str, str], SignalSnapshot] = {}
        self._suppressed_episode_ids: dict[tuple[str, str], str] = {}
        self._confirmation_gates: dict[tuple[str, str], _ConfirmationGate] = {}
        self._confirmation_attempts: dict[tuple[str, str], tuple[object, ...]] = {}
        self._condition = Condition()
        self._status = LiveSignalRuntimeStatus.CREATED
        self._startup_watermark: datetime | None = None
        self._restored_open_signal_count = 0
        self._processed_revision_count = 0
        self._stale_evaluation_count = 0
        self._evaluation_count = 0
        self._lifecycle_write_count = 0
        self._projection_rejected_count = 0
        self._projection_callback_error_count = 0
        self._confirmation_evaluation_count = 0
        self._triggered_signal_count = 0
        self._expired_signal_count = 0
        self._last_observation_accepted_count = 0
        self._last_heartbeat_ts: datetime | None = None
        self._last_event: SignalEvaluationEvent | None = None
        self._last_error: str | None = None
        self._failure_phase: str | None = None
        self._failure_input_identity: str | None = None
        self._last_successful_commit_sequence: int | None = None
        self._last_traceback: str | None = None
        self._thread: Thread | None = None

    @property
    def snapshot(self) -> LiveSignalRuntimeSnapshot:
        with self._condition:
            observation = (
                None if self._observation_store is None else self._observation_store.snapshot
            )
            return LiveSignalRuntimeSnapshot(
                status=self._status,
                startup_watermark=self._startup_watermark,
                restored_open_signal_count=self._restored_open_signal_count,
                processed_revision_count=self._processed_revision_count,
                stale_evaluation_count=self._stale_evaluation_count,
                evaluation_count=self._evaluation_count,
                lifecycle_write_count=self._lifecycle_write_count,
                open_signal_count=len(self._open_signals),
                projection_rejected_count=self._projection_rejected_count,
                projection_callback_error_count=self._projection_callback_error_count,
                confirmation_evaluation_count=self._confirmation_evaluation_count,
                triggered_signal_count=self._triggered_signal_count,
                expired_signal_count=self._expired_signal_count,
                observation_accepted_bar_count=(
                    0 if observation is None else observation.accepted_bar_count
                ),
                observation_retained_bar_count=(
                    0 if observation is None else observation.retained_bar_count
                ),
                observation_conflicting_retry_count=(
                    0 if observation is None else observation.conflicting_retry_count
                ),
                last_event=self._last_event,
                last_error=self._last_error,
                failure_phase=self._failure_phase,
                failure_input_identity=self._failure_input_identity,
                last_successful_commit_sequence=self._last_successful_commit_sequence,
                last_traceback=self._last_traceback,
            )

    def start(self) -> None:
        with self._condition:
            if self._status != LiveSignalRuntimeStatus.CREATED:
                raise RuntimeError("live signal runtime can only start once")
            self._startup_watermark = require_utc(self._clock())
        try:
            restored = self._restore_open_state()
        except Exception as exc:
            self._record_failure(exc, phase="startup_restore", input_identity="open_signals")
            raise
        if self._observation_store is not None:
            self._last_observation_accepted_count = (
                self._observation_store.snapshot.accepted_bar_count
            )
        with self._condition:
            self._status = LiveSignalRuntimeStatus.RUNNING
        self._offer_runtime_projection(SignalRuntimeProjectionKind.STARTED)
        assert self._startup_watermark is not None
        for signal in restored:
            self._offer_projection(
                SignalLifecycleProjection.restored(signal, self._startup_watermark)
            )
        with self._condition:
            self._thread = Thread(
                target=self._run,
                name="markeitech-signal-runtime",
                daemon=True,
            )
            self._thread.start()

    def stop(self, timeout: float) -> bool:
        if timeout <= 0:
            raise ValueError("signal runtime stop timeout must be positive")
        with self._condition:
            if self._status == LiveSignalRuntimeStatus.STOPPED:
                return True
            if self._status == LiveSignalRuntimeStatus.CREATED:
                self._status = LiveSignalRuntimeStatus.STOPPED
                self._handoff.close()
                return True
            if self._status != LiveSignalRuntimeStatus.FAILED:
                self._status = LiveSignalRuntimeStatus.STOPPING
            thread = self._thread
        self._handoff.close()
        if thread is not None:
            thread.join(timeout)
        return thread is None or not thread.is_alive()

    def _restore_open_state(self) -> tuple[SignalSnapshot, ...]:
        restored = []
        enabled_instruments = self._config.enabled_definition_ids_by_instrument
        for definition_id, definition in self._definitions.items():
            signals = self._store.load_signals(definition_id=definition_id)
            compatible = tuple(
                signal
                for signal in signals
                if definition_id in enabled_instruments.get(signal.instrument_id, ())
                and signal.algorithm_version == definition.algorithm_version
                and signal.configuration_hash == definition.configuration_hash
            )
            latest_by_instrument: dict[str, SignalSnapshot] = {}
            for signal in compatible:
                current_latest = latest_by_instrument.get(signal.instrument_id)
                if current_latest is None or (signal.updated_ts, signal.signal_id) > (
                    current_latest.updated_ts,
                    current_latest.signal_id,
                ):
                    latest_by_instrument[signal.instrument_id] = signal
            latest = tuple(latest_by_instrument.values())
            current = tuple(
                signal
                for signal in latest
                if signal.status in {SignalStatus.ARMED, SignalStatus.TRIGGERED}
            )
            suppressed = tuple(signal for signal in latest if signal.status == SignalStatus.EXPIRED)
            keys = [(signal.definition_id, signal.instrument_id) for signal in current]
            if len(keys) != len(set(keys)):
                raise ValueError("multiple open signals exist for one definition/instrument")
            self._direction_trackers[definition_id].seed_open_signals(
                (*current, *suppressed), include_expired=True
            )
            self._episode_trackers[definition_id].seed_active_episodes(
                tuple(restore_location_episode(signal) for signal in (*current, *suppressed))
            )
            for signal in current:
                self._open_signals[(definition_id, signal.instrument_id)] = signal
            for signal in suppressed:
                assert signal.location_episode_id is not None
                self._suppressed_episode_ids[(definition_id, signal.instrument_id)] = (
                    signal.location_episode_id
                )
            restored.extend(current)
        self._restored_open_signal_count = len(restored)
        return tuple(restored)

    def _run(self) -> None:
        while True:
            try:
                revisions = self._handoff.wait_and_drain(
                    self._config.evaluation_batch_size,
                    self._config.evaluation_poll_seconds,
                )
            except Exception as exc:
                self._record_failure(exc, phase="feature_handoff", input_identity="wait_and_drain")
                self._offer_runtime_projection(SignalRuntimeProjectionKind.FAILED)
                return
            if revisions:
                try:
                    for _index, revision in enumerate(revisions):
                        self._process_revision(revision)
                        with self._condition:
                            self._last_successful_commit_sequence = revision.commit_sequence
                except Exception as exc:
                    try:
                        self._handoff.requeue_front(revisions[_index:])
                    except Exception as requeue_exc:
                        failure = RuntimeError(
                            f"{type(exc).__name__}: {exc}; durable revision requeue also failed: "
                            f"{type(requeue_exc).__name__}: {requeue_exc}"
                        )
                        failure.__cause__ = requeue_exc
                    else:
                        failure = exc
                    self._record_failure(
                        failure,
                        phase="feature_revision",
                        input_identity=_feature_revision_identity(revision),
                    )
                    self._offer_runtime_projection(SignalRuntimeProjectionKind.FAILED)
                    return
            try:
                self._process_observation_updates()
            except Exception as exc:
                observation = (
                    None if self._observation_store is None else self._observation_store.snapshot
                )
                accepted = 0 if observation is None else observation.accepted_bar_count
                self._record_failure(
                    exc,
                    phase="observation_update",
                    input_identity=f"accepted_bars={accepted};open_signals={len(self._open_signals)}",
                )
                self._offer_runtime_projection(SignalRuntimeProjectionKind.FAILED)
                return
            with self._condition:
                if (
                    self._status == LiveSignalRuntimeStatus.STOPPING
                    and self._handoff.snapshot.pending_count == 0
                ):
                    self._status = LiveSignalRuntimeStatus.STOPPED
                    self._condition.notify_all()
                    self._offer_runtime_projection(SignalRuntimeProjectionKind.STOPPED)
                    return

    def _record_failure(self, exc: Exception, *, phase: str, input_identity: str) -> None:
        with self._condition:
            self._status = LiveSignalRuntimeStatus.FAILED
            self._last_error = f"{type(exc).__name__}: {exc}"
            self._failure_phase = phase
            self._failure_input_identity = input_identity
            self._last_traceback = format_exc()
            self._condition.notify_all()

    def _process_revision(self, revision: CommittedFeatureRevision) -> None:
        changed = self._feature_state.apply(revision)
        with self._condition:
            self._processed_revision_count += 1
        if not changed:
            return
        feature = revision.feature
        for definition in self._config.enabled_definitions(feature.snapshot.instrument_id):
            if definition.definition_id not in self._definitions:
                continue
            bundle = self._feature_state.compose(revision, definition)
            if bundle is None:
                continue
            assert self._startup_watermark is not None
            if bundle.evaluation_as_of <= self._startup_watermark:
                with self._condition:
                    self._stale_evaluation_count += 1
                continue
            event = self._evaluate(definition, bundle)
            with self._condition:
                self._evaluation_count += 1
                self._last_event = event
            for lifecycle_event in event.lifecycle_events:
                self._offer_projection(SignalLifecycleProjection.transitioned(lifecycle_event))
            self._offer_heartbeat(bundle.evaluation_as_of)
            if self._on_evaluation is not None:
                self._on_evaluation(event)

    def _process_observation_updates(self) -> None:
        if self._observation_store is None:
            return
        accepted = self._observation_store.snapshot.accepted_bar_count
        if accepted == self._last_observation_accepted_count:
            return
        self._last_observation_accepted_count = accepted
        for key, signal in tuple(self._open_signals.items()):
            if signal.status != SignalStatus.ARMED:
                continue
            definition = self._definitions[key[0]]
            bundle = self._feature_state.latest_bundle(signal.instrument_id, definition)
            gate = self._confirmation_gates.get(key)
            if bundle is None or gate is None or not gate.is_open:
                continue
            event = self._confirm_signal(definition, bundle, signal, gate)
            if event is not None:
                self._record_event(event)

    def _record_event(self, event: SignalEvaluationEvent) -> None:
        with self._condition:
            self._evaluation_count += 1
            self._last_event = event
        for lifecycle_event in event.lifecycle_events:
            self._offer_projection(SignalLifecycleProjection.transitioned(lifecycle_event))
        if self._on_evaluation is not None:
            self._on_evaluation(event)

    def _evaluate(
        self,
        definition: SignalDefinitionConfig,
        bundle: CommittedMarketContextBundle,
    ) -> SignalEvaluationEvent:
        definition_id = definition.definition_id
        direction_decision = self._direction_trackers[definition_id].evaluate(bundle)
        direction = direction_decision.qualification.direction
        open_key = (definition_id, bundle.instrument_id)
        open_signal = self._open_signals.get(open_key)
        if direction is None and open_signal is None:
            return SignalEvaluationEvent(
                instrument_id=bundle.instrument_id,
                definition_id=definition_id,
                evaluation_ts=bundle.evaluation_as_of,
                direction_status=direction_decision.qualification.status,
                location_status=None,
                episode_event=None,
                signal_id=None,
                signal_status=None,
            )

        if direction is None:
            assert open_signal is not None
            direction = open_signal.direction
            anchor = open_signal.direction_regime_anchor
            reason = (
                "direction_evidence_unavailable"
                if direction_decision.qualification.status
                == DirectionQualificationStatus.MISSING_EVIDENCE
                else "direction_entry_qualification_degraded_"
                f"{direction_decision.qualification.status.value}"
            )
            location = LocationQualification(
                status=LocationQualificationStatus.MISSING_EVIDENCE,
                is_degraded=True,
                reason_codes=(reason, "trigger_blocked_by_direction_degradation"),
            )
        else:
            anchor = direction_decision.regime_anchor
            session_start, _ = self._session_resolver.session_window(
                bundle.instrument_id,
                bundle.evaluation_as_of,
            )
            location = qualify_location(
                bundle,
                definition,
                direction,
                session_start=session_start,
            )
        if anchor is None:
            raise RuntimeError("Direction decision did not expose a regime anchor")
        evaluation = bundle.feature(definition.evaluation_timeframe)
        observed_price = (
            evaluation.snapshot.close
            if evaluation is not None and evaluation.snapshot.as_of == bundle.evaluation_as_of
            else None
        )
        episode_decision = self._episode_trackers[definition_id].evaluate(
            LocationEpisodeObservation(
                definition_id=definition_id,
                instrument_id=bundle.instrument_id,
                direction=direction,
                direction_regime_anchor=anchor,
                evaluation_ts=bundle.evaluation_as_of,
                observed_price=observed_price,
                qualification=location,
            )
        )
        persisted = self._persist_episode_decision(
            definition,
            direction_decision.qualification,
            episode_decision,
            open_signal,
            bundle.evaluation_as_of,
            bundle,
        )
        gate = _ConfirmationGate(
            direction_status=direction_decision.qualification.status,
            location_status=location.status,
            episode_event=episode_decision.event_type,
            is_open=(
                direction_decision.qualification.status == DirectionQualificationStatus.QUALIFIED
                and episode_decision.event_type
                in {
                    LocationEpisodeEventType.ENTERED,
                    LocationEpisodeEventType.ACTIVE,
                    LocationEpisodeEventType.FAVORABLE_DEPARTURE,
                    LocationEpisodeEventType.DEPARTURE_UNRESOLVED,
                }
            ),
        )
        self._confirmation_gates[open_key] = gate
        confirmation = None
        if persisted.current is not None and persisted.current.status == SignalStatus.ARMED:
            confirmation = self._confirm_signal(
                definition,
                bundle,
                persisted.current,
                gate,
            )
        if confirmation is not None:
            return SignalEvaluationEvent(
                instrument_id=bundle.instrument_id,
                definition_id=definition_id,
                evaluation_ts=bundle.evaluation_as_of,
                direction_status=direction_decision.qualification.status,
                location_status=location.status,
                episode_event=episode_decision.event_type,
                signal_id=confirmation.signal_id,
                signal_status=confirmation.signal_status,
                lifecycle_events=(*persisted.lifecycle_events, *confirmation.lifecycle_events),
                aggression_status=confirmation.aggression_status,
                confirmation_method=confirmation.confirmation_method,
                elapsed_observation_bars=confirmation.elapsed_observation_bars,
            )
        return SignalEvaluationEvent(
            bundle.instrument_id,
            definition_id,
            bundle.evaluation_as_of,
            direction_decision.qualification.status,
            location.status,
            episode_decision.event_type,
            None if persisted.current is None else persisted.current.signal_id,
            None if persisted.current is None else persisted.current.status,
            persisted.lifecycle_events,
        )

    def _persist_episode_decision(
        self,
        definition: SignalDefinitionConfig,
        direction: DirectionQualification,
        decision: LocationEpisodeDecision,
        open_signal: SignalSnapshot | None,
        occurred_ts: datetime,
        bundle: CommittedMarketContextBundle,
    ) -> _PersistedSignalDecision:
        key = (definition.definition_id, bundle.instrument_id)
        if decision.episode is not None and (
            decision.episode.definition_id != definition.definition_id
            or decision.episode.instrument_id != bundle.instrument_id
        ):
            raise RuntimeError("location episode identity conflicts with evaluation state")
        if decision.event_type == LocationEpisodeEventType.ENTERED:
            if decision.episode is None or open_signal is not None:
                raise RuntimeError("entered location episode conflicts with open signal state")
            setup = build_armed_location_signal(
                definition,
                decision.episode,
                direction,
                self._confirmation_context(definition, bundle),
            )
            self._store.save_signal_candidate_and_transition(
                setup.candidate,
                setup.armed_transition,
            )
            current = setup.armed_transition.current
            with self._condition:
                self._open_signals[key] = current
                self._lifecycle_write_count += 1
            return _PersistedSignalDecision(current, (setup.armed_transition,))
        if decision.event_type == LocationEpisodeEventType.REPLACED:
            if decision.episode is None:
                raise RuntimeError("replacement episode requires new signal state")
            suppressed_id = self._suppressed_episode_ids.get(key)
            if open_signal is None and suppressed_id == decision.ended_episode_id:
                setup = build_armed_location_signal(
                    definition,
                    decision.episode,
                    direction,
                    self._confirmation_context(definition, bundle),
                )
                self._store.save_signal_candidate_and_transition(
                    setup.candidate,
                    setup.armed_transition,
                )
                current = setup.armed_transition.current
                with self._condition:
                    self._suppressed_episode_ids.pop(key, None)
                    self._open_signals[key] = current
                    self._lifecycle_write_count += 1
                return _PersistedSignalDecision(current, (setup.armed_transition,))
            if open_signal is None:
                raise RuntimeError("replacement episode requires existing signal state")
            ended = invalidate_ended_location_signal(
                open_signal,
                decision,
                occurred_ts=occurred_ts,
            )
            setup = build_armed_location_signal(
                definition,
                decision.episode,
                direction,
                self._confirmation_context(definition, bundle),
            )
            self._store.replace_signal_with_armed_candidate(
                ended,
                setup.candidate,
                setup.armed_transition,
            )
            current = setup.armed_transition.current
            with self._condition:
                self._open_signals[key] = current
                self._lifecycle_write_count += 1
            return _PersistedSignalDecision(
                current,
                (ended, setup.armed_transition),
            )
        if decision.event_type == LocationEpisodeEventType.EXITED:
            if open_signal is None:
                if self._suppressed_episode_ids.get(key) == decision.ended_episode_id:
                    self._suppressed_episode_ids.pop(key, None)
                    self._confirmation_gates.pop(key, None)
                    return _PersistedSignalDecision(None)
                raise RuntimeError("exited location episode requires an open signal")
            ended = invalidate_ended_location_signal(
                open_signal,
                decision,
                occurred_ts=occurred_ts,
                reason_codes=decision.reason_codes,
            )
            self._store.apply_signal_transition(ended)
            with self._condition:
                self._open_signals.pop(
                    (open_signal.definition_id, open_signal.instrument_id),
                    None,
                )
                self._lifecycle_write_count += 1
            return _PersistedSignalDecision(ended.current, (ended,))
        return _PersistedSignalDecision(open_signal)

    def _confirmation_context(
        self,
        definition: SignalDefinitionConfig,
        bundle: CommittedMarketContextBundle,
    ) -> SignalConfirmationContext | None:
        policy = definition.aggression_policy
        if policy is None:
            return None
        evaluation = bundle.feature(definition.evaluation_timeframe)
        if evaluation is None or evaluation.snapshot.atr_14 <= 0:
            raise RuntimeError("Aggression arming requires positive evaluation ATR")
        assert self._role_resolver is not None
        role = self._role_resolver(bundle.instrument_id).strip().upper()
        if role == "ACTIVE":
            method = policy.active_confirmation_method
        elif role == "BACKGROUND":
            method = policy.background_confirmation_method
        else:
            raise ValueError(f"unsupported signal instrument role {role!r}")
        return SignalConfirmationContext(
            method=method,
            window_started_ts=bundle.evaluation_as_of,
            atr_at_arm=evaluation.snapshot.atr_14,
        )

    def _confirm_signal(
        self,
        definition: SignalDefinitionConfig,
        bundle: CommittedMarketContextBundle,
        signal: SignalSnapshot,
        gate: _ConfirmationGate,
    ) -> SignalEvaluationEvent | None:
        policy = definition.aggression_policy
        context = signal.confirmation_context
        if policy is None or context is None or not gate.is_open:
            return None
        assert self._observation_store is not None
        cadence = self._observation_store.bars(
            signal.instrument_id,
            "ib",
            through_ts=bundle.evaluation_as_of,
        )
        elapsed = sum(bar.open_ts >= context.window_started_ts for bar in cadence)
        source = (
            "classified_ticks"
            if context.method == SignalConfirmationMethod.TICK_AGGRESSION
            else "ib"
        )
        observations = self._observation_store.bars(
            signal.instrument_id,
            source,
            through_ts=bundle.evaluation_as_of,
        )
        key = (signal.definition_id, signal.instrument_id)
        signature = (
            signal.signal_id,
            bundle.evaluation_as_of,
            len(cadence),
            None if not cadence else cadence[-1].close_ts,
            len(observations),
            None if not observations else observations[-1].close_ts,
        )
        if self._confirmation_attempts.get(key) == signature:
            return None
        self._confirmation_attempts[key] = signature
        if context.method == SignalConfirmationMethod.TICK_AGGRESSION:
            result = evaluate_aggression_window(
                signal,
                policy,
                observations,
                evaluated_ts=bundle.evaluation_as_of,
                elapsed_observation_bars=elapsed,
                atr_at_arm=context.atr_at_arm,
                pace_baseline_bars=observations,
            )
        else:
            result = evaluate_bar_impulse_window(
                signal,
                policy,
                observations,
                evaluated_ts=bundle.evaluation_as_of,
                elapsed_observation_bars=elapsed,
                atr_at_arm=context.atr_at_arm,
                pace_baseline_bars=observations,
            )
        with self._condition:
            self._confirmation_evaluation_count += 1
        if result.status not in {
            AggressionEvaluationStatus.QUALIFIED,
            AggressionEvaluationStatus.EXPIRED,
        }:
            return None
        terminal_status = (
            SignalStatus.TRIGGERED
            if result.status == AggressionEvaluationStatus.QUALIFIED
            else SignalStatus.EXPIRED
        )
        reasons = result.reason_codes
        if (
            terminal_status == SignalStatus.EXPIRED
            and "armed_observation_window_expired" not in reasons
        ):
            reasons = ("armed_observation_window_expired", *reasons)
        event = transition_signal(
            signal,
            terminal_status,
            occurred_ts=result.evaluated_ts,
            reason_codes=reasons,
            evidence=result.evidence,
        )
        self._store.apply_signal_transition(event)
        with self._condition:
            self._lifecycle_write_count += 1
            if terminal_status == SignalStatus.TRIGGERED:
                self._open_signals[key] = event.current
                self._triggered_signal_count += 1
            else:
                self._open_signals.pop(key, None)
                assert signal.location_episode_id is not None
                self._suppressed_episode_ids[key] = signal.location_episode_id
                self._expired_signal_count += 1
        return SignalEvaluationEvent(
            instrument_id=signal.instrument_id,
            definition_id=signal.definition_id,
            evaluation_ts=bundle.evaluation_as_of,
            direction_status=gate.direction_status,
            location_status=gate.location_status,
            episode_event=gate.episode_event,
            signal_id=event.current.signal_id,
            signal_status=event.current.status,
            lifecycle_events=(event,),
            aggression_status=result.status,
            confirmation_method=context.method,
            elapsed_observation_bars=result.elapsed_observation_bars,
        )

    def _offer_heartbeat(self, evaluation_ts: datetime) -> None:
        interval = timedelta(seconds=self._config.operator_heartbeat_interval_seconds)
        if (
            self._last_heartbeat_ts is not None
            and evaluation_ts < self._last_heartbeat_ts + interval
        ):
            return
        self._last_heartbeat_ts = evaluation_ts
        self._offer_runtime_projection(
            SignalRuntimeProjectionKind.HEARTBEAT,
            occurred_ts=evaluation_ts,
        )

    def _offer_runtime_projection(
        self,
        kind: SignalRuntimeProjectionKind,
        *,
        occurred_ts: datetime | None = None,
    ) -> None:
        snapshot = self.snapshot
        self._offer_projection(
            SignalRuntimeProjection(
                kind=kind,
                occurred_ts=require_utc(occurred_ts or self._clock()),
                status=snapshot.status.value,
                startup_watermark=snapshot.startup_watermark,
                restored_open_signal_count=snapshot.restored_open_signal_count,
                processed_revision_count=snapshot.processed_revision_count,
                stale_evaluation_count=snapshot.stale_evaluation_count,
                evaluation_count=snapshot.evaluation_count,
                lifecycle_write_count=snapshot.lifecycle_write_count,
                open_signal_count=snapshot.open_signal_count,
                projection_rejected_count=snapshot.projection_rejected_count,
                projection_callback_error_count=snapshot.projection_callback_error_count,
                confirmation_evaluation_count=snapshot.confirmation_evaluation_count,
                triggered_signal_count=snapshot.triggered_signal_count,
                expired_signal_count=snapshot.expired_signal_count,
                observation_accepted_bar_count=snapshot.observation_accepted_bar_count,
                observation_retained_bar_count=snapshot.observation_retained_bar_count,
                observation_conflicting_retry_count=(snapshot.observation_conflicting_retry_count),
                last_error=snapshot.last_error,
                failure_phase=snapshot.failure_phase,
                failure_input_identity=snapshot.failure_input_identity,
                last_successful_commit_sequence=snapshot.last_successful_commit_sequence,
                error_traceback=snapshot.last_traceback,
            )
        )

    def _offer_projection(self, projection: SignalOperatorProjection) -> None:
        if self._on_projection is None:
            return
        try:
            accepted = self._on_projection(projection)
        except Exception:
            with self._condition:
                self._projection_callback_error_count += 1
            return
        if not accepted:
            with self._condition:
                self._projection_rejected_count += 1


def _feature_revision_identity(revision: CommittedFeatureRevision) -> str:
    snapshot = revision.feature.snapshot
    return (
        f"commit_sequence={revision.commit_sequence};instrument={snapshot.instrument_id};"
        f"timeframe={snapshot.timeframe.value};as_of={snapshot.as_of.isoformat()};"
        f"feature_id={revision.feature.feature_id}"
    )
