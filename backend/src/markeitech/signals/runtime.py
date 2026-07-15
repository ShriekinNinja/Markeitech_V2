from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from threading import Condition, Thread
from typing import Protocol

from markeitech.domain.base import require_utc
from markeitech.persistence.feature_pipeline import CommittedFeatureRevision
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


@dataclass(frozen=True)
class _PersistedSignalDecision:
    current: SignalSnapshot | None
    lifecycle_events: tuple[SignalTransitionEvent, ...] = ()


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
    last_event: SignalEvaluationEvent | None
    last_error: str | None


class LiveSignalRuntime:
    """Consumes durable feature revisions and owns live Direction/Location state."""

    def __init__(
        self,
        config: SignalRuntimeConfig,
        store: SignalStateStore,
        session_resolver: ProductSessionResolver,
        handoff: BoundedFeatureCommitHandoff,
        *,
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
        self._config = config
        self._store = store
        self._session_resolver = session_resolver
        self._handoff = handoff
        self._clock = clock
        self._on_evaluation = on_evaluation
        self._on_projection = on_projection
        self._feature_state = CommittedFeatureState()
        self._direction_trackers = {
            key: DirectionRegimeTracker(value) for key, value in self._definitions.items()
        }
        self._episode_trackers = {
            key: LocationEpisodeTracker(value) for key, value in self._definitions.items()
        }
        self._open_signals: dict[tuple[str, str], SignalSnapshot] = {}
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
        self._last_heartbeat_ts: datetime | None = None
        self._last_event: SignalEvaluationEvent | None = None
        self._last_error: str | None = None
        self._thread: Thread | None = None

    @property
    def snapshot(self) -> LiveSignalRuntimeSnapshot:
        with self._condition:
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
                last_event=self._last_event,
                last_error=self._last_error,
            )

    def start(self) -> None:
        with self._condition:
            if self._status != LiveSignalRuntimeStatus.CREATED:
                raise RuntimeError("live signal runtime can only start once")
            self._startup_watermark = require_utc(self._clock())
        try:
            restored = self._restore_open_state()
        except Exception as exc:
            with self._condition:
                self._status = LiveSignalRuntimeStatus.FAILED
                self._last_error = f"{type(exc).__name__}: {exc}"
            raise
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
            current = tuple(
                signal
                for signal in signals
                if signal.status in {SignalStatus.ARMED, SignalStatus.TRIGGERED}
                and definition_id in enabled_instruments.get(signal.instrument_id, ())
                and signal.algorithm_version == definition.algorithm_version
                and signal.configuration_hash == definition.configuration_hash
            )
            keys = [(signal.definition_id, signal.instrument_id) for signal in current]
            if len(keys) != len(set(keys)):
                raise ValueError("multiple open signals exist for one definition/instrument")
            self._direction_trackers[definition_id].seed_open_signals(current)
            self._episode_trackers[definition_id].seed_active_episodes(
                tuple(restore_location_episode(signal) for signal in current)
            )
            for signal in current:
                self._open_signals[(definition_id, signal.instrument_id)] = signal
            restored.extend(current)
        self._restored_open_signal_count = len(restored)
        return tuple(restored)

    def _run(self) -> None:
        while True:
            revisions = self._handoff.wait_and_drain(
                self._config.evaluation_batch_size,
                self._config.evaluation_poll_seconds,
            )
            if revisions:
                try:
                    for _index, revision in enumerate(revisions):
                        self._process_revision(revision)
                except Exception as exc:
                    self._handoff.requeue_front(revisions[_index:])
                    with self._condition:
                        self._status = LiveSignalRuntimeStatus.FAILED
                        self._last_error = f"{type(exc).__name__}: {exc}"
                        self._condition.notify_all()
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
            if (
                direction_decision.qualification.status
                == DirectionQualificationStatus.MISSING_EVIDENCE
            ):
                anchor = open_signal.direction_regime_anchor
                location = LocationQualification(
                    status=LocationQualificationStatus.MISSING_EVIDENCE,
                    is_degraded=True,
                    reason_codes=("direction_evidence_unavailable",),
                )
            else:
                anchor = f"direction_ended:{bundle.evaluation_as_of.isoformat()}"
                location = LocationQualification(
                    status=LocationQualificationStatus.NOT_AT_LOCATION,
                    reason_codes=("direction_regime_ended",),
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
        episode_decision = self._episode_trackers[definition_id].evaluate(
            LocationEpisodeObservation(
                definition_id=definition_id,
                instrument_id=bundle.instrument_id,
                direction=direction,
                direction_regime_anchor=anchor,
                evaluation_ts=bundle.evaluation_as_of,
                qualification=location,
            )
        )
        persisted = self._persist_episode_decision(
            definition,
            direction_decision.qualification,
            episode_decision,
            open_signal,
            bundle.evaluation_as_of,
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
    ) -> _PersistedSignalDecision:
        key = (
            (definition.definition_id, decision.episode.instrument_id) if decision.episode else None
        )
        if decision.event_type == LocationEpisodeEventType.ENTERED:
            if decision.episode is None or open_signal is not None or key is None:
                raise RuntimeError("entered location episode conflicts with open signal state")
            setup = build_armed_location_signal(definition, decision.episode, direction)
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
            if decision.episode is None or open_signal is None or key is None:
                raise RuntimeError("replacement episode requires existing and new signal state")
            ended = invalidate_ended_location_signal(
                open_signal,
                decision,
                occurred_ts=occurred_ts,
            )
            setup = build_armed_location_signal(definition, decision.episode, direction)
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
                raise RuntimeError("exited location episode requires an open signal")
            ended = invalidate_ended_location_signal(
                open_signal,
                decision,
                occurred_ts=occurred_ts,
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
