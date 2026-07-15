from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Event

from markeitech.analytics import (
    AnalyticsInputFidelity,
    AnalyticsTimeframe,
    ContextLevel,
    FeatureInputLineage,
    LevelKind,
    MarketContextFeatureSnapshot,
    MarketContextSnapshot,
    TrendState,
    VwapPosition,
)
from markeitech.persistence import CommittedFeatureRevision
from markeitech.signals import (
    BoundedFeatureCommitHandoff,
    BoundedSignalProjectionWriter,
    DirectionQualificationStatus,
    LiveSignalRuntime,
    LiveSignalRuntimeStatus,
    LocationEpisodeEventType,
    LocationPolicyConfig,
    LocationQualificationStatus,
    LocationSourceKind,
    LocationSourcePolicyConfig,
    SignalDefinitionConfig,
    SignalLifecycleProjection,
    SignalLifecycleProjectionKind,
    SignalRuntimeConfig,
    SignalRuntimeProjection,
    SignalRuntimeProjectionKind,
    SignalStatus,
)

STARTED = datetime(2026, 7, 14, 13, 30, tzinfo=UTC)


def definition() -> SignalDefinitionConfig:
    return SignalDefinitionConfig(
        definition_id="runtime_context",
        evaluation_timeframe=AnalyticsTimeframe.ONE_MINUTE,
        primary_direction_timeframes=(AnalyticsTimeframe.ONE_HOUR,),
        location_policy=LocationPolicyConfig(
            sources=(
                LocationSourcePolicyConfig(
                    source_kind=LocationSourceKind.STRUCTURAL_LEVEL,
                    timeframes=(AnalyticsTimeframe.FIVE_MINUTES,),
                    proximity_atr_fraction=Decimal("0.10"),
                ),
            ),
        ),
    )


def feature(
    instrument_id: str,
    timeframe: AnalyticsTimeframe,
    as_of: datetime,
    *,
    revision: str,
    direction_score: int = 1,
) -> MarketContextFeatureSnapshot:
    return MarketContextFeatureSnapshot(
        configuration_hash="a" * 64,
        input_lineage=(
            FeatureInputLineage(
                instrument_id=instrument_id,
                timeframe=timeframe,
                source="ib",
                input_fidelity=AnalyticsInputFidelity.REPORTED,
                start_ts=as_of - timeframe.duration,
                end_ts=as_of,
                event_count=1,
                identity_hash=revision * 64,
            ),
        ),
        snapshot=MarketContextSnapshot(
            instrument_id=instrument_id,
            timeframe=timeframe,
            as_of=as_of,
            source="ib",
            input_fidelity=AnalyticsInputFidelity.REPORTED,
            bar_count=251,
            close=Decimal("100"),
            atr_14=Decimal("10"),
            session_open=Decimal("98"),
            session_high=Decimal("105"),
            session_low=Decimal("95"),
            session_range_position=Decimal("0.5"),
            vwap_position=VwapPosition.ABOVE,
            trend=TrendState.BULLISH,
            trend_reason_codes=("bullish_test_context",),
            nearest_support=(
                ContextLevel(
                    kind=LevelKind.SWING_SUPPORT,
                    price=Decimal("100"),
                    observed_ts=as_of - timedelta(minutes=5),
                )
                if timeframe == AnalyticsTimeframe.FIVE_MINUTES
                else None
            ),
            direction_score=direction_score,
            direction_location_reason_codes=("bullish_direction_score",),
        ),
    )


class MemorySignalStore:
    def __init__(self) -> None:
        self.signals = {}
        self.lifecycle_writes = 0

    def load_signals(self, **filters):
        values = tuple(self.signals.values())
        return tuple(
            signal
            for signal in values
            if all(value is None or getattr(signal, key) == value for key, value in filters.items())
        )

    def save_signal_candidate_and_transition(self, candidate, event, **kwargs):
        self.signals[candidate.signal_id] = event.current
        self.lifecycle_writes += 1

    def replace_signal_with_armed_candidate(self, ended_event, candidate, armed_event):
        self.signals[ended_event.signal_id] = ended_event.current
        self.signals[candidate.signal_id] = armed_event.current
        self.lifecycle_writes += 1

    def apply_signal_transition(self, event, **kwargs):
        self.signals[event.signal_id] = event.current
        self.lifecycle_writes += 1


class FixedSessionResolver:
    def session_window(self, instrument_id, timestamp):
        return STARTED - timedelta(hours=15, minutes=30), STARTED + timedelta(hours=8)


def revisions(instrument_id: str, start_sequence: int):
    live_ts = STARTED + timedelta(minutes=1)
    values = (
        feature(instrument_id, AnalyticsTimeframe.ONE_HOUR, STARTED, revision="1"),
        feature(instrument_id, AnalyticsTimeframe.FIVE_MINUTES, STARTED, revision="2"),
        feature(instrument_id, AnalyticsTimeframe.ONE_MINUTE, STARTED, revision="3"),
        feature(instrument_id, AnalyticsTimeframe.ONE_MINUTE, live_ts, revision="4"),
    )
    return tuple(
        CommittedFeatureRevision(value, STARTED, start_sequence + index)
        for index, value in enumerate(values)
    )


def test_runtime_rebuilds_from_warmup_then_arms_on_first_live_evaluation() -> None:
    store = MemorySignalStore()
    handoff = BoundedFeatureCommitHandoff(16)
    observed = Event()
    config = SignalRuntimeConfig(
        definitions=(definition(),),
        enabled_definition_ids_by_instrument={"NQU6.CME": ("runtime_context",)},
        evaluation_poll_seconds=0.01,
    )
    runtime = LiveSignalRuntime(
        config,
        store,
        FixedSessionResolver(),
        handoff,
        clock=lambda: STARTED,
        on_evaluation=lambda event: observed.set(),
    )

    runtime.start()
    assert handoff.offer(revisions("NQU6.CME", 1))
    assert observed.wait(1)
    assert runtime.stop(1)

    snapshot = runtime.snapshot
    assert snapshot.status == LiveSignalRuntimeStatus.STOPPED
    assert snapshot.processed_revision_count == 4
    assert snapshot.stale_evaluation_count == 1
    assert snapshot.evaluation_count == 1
    assert snapshot.lifecycle_write_count == 1
    assert snapshot.open_signal_count == 1
    assert store.lifecycle_writes == 1
    assert {signal.status for signal in store.signals.values()} == {SignalStatus.ARMED}


def test_runtime_preserves_armed_episode_during_soft_direction_degradation() -> None:
    store = MemorySignalStore()
    handoff = BoundedFeatureCommitHandoff(16)
    observed = []
    completed = Event()

    def capture(event):
        observed.append(event)
        if len(observed) == 2:
            completed.set()

    runtime = LiveSignalRuntime(
        SignalRuntimeConfig(
            definitions=(definition(),),
            enabled_definition_ids_by_instrument={"NQU6.CME": ("runtime_context",)},
            evaluation_poll_seconds=0.01,
        ),
        store,
        FixedSessionResolver(),
        handoff,
        clock=lambda: STARTED,
        on_evaluation=capture,
    )
    runtime.start()
    assert handoff.offer(revisions("NQU6.CME", 1))
    degraded_ts = STARTED + timedelta(minutes=2)
    assert handoff.offer(
        (
            CommittedFeatureRevision(
                feature(
                    "NQU6.CME",
                    AnalyticsTimeframe.ONE_HOUR,
                    degraded_ts,
                    revision="5",
                    direction_score=0,
                ),
                degraded_ts,
                5,
            ),
            CommittedFeatureRevision(
                feature(
                    "NQU6.CME",
                    AnalyticsTimeframe.ONE_MINUTE,
                    degraded_ts,
                    revision="6",
                ),
                degraded_ts,
                6,
            ),
        )
    )
    assert completed.wait(1)
    assert runtime.stop(1)

    degraded = observed[-1]
    assert degraded.direction_status == DirectionQualificationStatus.NEUTRAL
    assert degraded.location_status == LocationQualificationStatus.MISSING_EVIDENCE
    assert degraded.episode_event == LocationEpisodeEventType.EVIDENCE_GAP
    assert degraded.signal_status == SignalStatus.ARMED
    assert store.lifecycle_writes == 1
    assert runtime.snapshot.open_signal_count == 1


def test_runtime_invalidates_armed_episode_on_fully_qualified_opposite_direction() -> None:
    store = MemorySignalStore()
    handoff = BoundedFeatureCommitHandoff(16)
    observed = []
    completed = Event()

    def capture(event):
        observed.append(event)
        if len(observed) == 2:
            completed.set()

    runtime = LiveSignalRuntime(
        SignalRuntimeConfig(
            definitions=(definition(),),
            enabled_definition_ids_by_instrument={"NQU6.CME": ("runtime_context",)},
            evaluation_poll_seconds=0.01,
        ),
        store,
        FixedSessionResolver(),
        handoff,
        clock=lambda: STARTED,
        on_evaluation=capture,
    )
    runtime.start()
    assert handoff.offer(revisions("NQU6.CME", 1))
    flipped_ts = STARTED + timedelta(minutes=2)
    assert handoff.offer(
        (
            CommittedFeatureRevision(
                feature(
                    "NQU6.CME",
                    AnalyticsTimeframe.ONE_HOUR,
                    flipped_ts,
                    revision="5",
                    direction_score=-1,
                ),
                flipped_ts,
                5,
            ),
            CommittedFeatureRevision(
                feature(
                    "NQU6.CME",
                    AnalyticsTimeframe.ONE_MINUTE,
                    flipped_ts,
                    revision="6",
                ),
                flipped_ts,
                6,
            ),
        )
    )
    assert completed.wait(1)
    assert runtime.stop(1)

    flipped = observed[-1]
    assert flipped.direction_status == DirectionQualificationStatus.QUALIFIED
    assert flipped.episode_event == LocationEpisodeEventType.EXITED
    assert flipped.signal_status == SignalStatus.INVALIDATED
    assert store.lifecycle_writes == 2
    assert runtime.snapshot.open_signal_count == 0


def test_runtime_applies_identical_signal_path_to_active_and_background() -> None:
    store = MemorySignalStore()
    handoff = BoundedFeatureCommitHandoff(16)
    completed = Event()
    observed = []
    config = SignalRuntimeConfig(
        definitions=(definition(),),
        enabled_definition_ids_by_instrument={
            "NQU6.CME": ("runtime_context",),
            "ESU6.CME": ("runtime_context",),
        },
        evaluation_poll_seconds=0.01,
    )

    def capture(event):
        observed.append(event)
        if len(observed) == 2:
            completed.set()

    runtime = LiveSignalRuntime(
        config,
        store,
        FixedSessionResolver(),
        handoff,
        clock=lambda: STARTED,
        on_evaluation=capture,
    )
    runtime.start()
    assert handoff.offer((*revisions("NQU6.CME", 1), *revisions("ESU6.CME", 5)))
    assert completed.wait(1)
    assert runtime.stop(1)

    assert {event.instrument_id for event in observed} == {"NQU6.CME", "ESU6.CME"}
    assert {event.episode_event for event in observed} == {"entered"}
    assert runtime.snapshot.open_signal_count == 2


def test_one_committed_revision_evaluates_every_enabled_definition() -> None:
    first = definition()
    second = first.model_copy(update={"definition_id": "alternate_context"})
    store = MemorySignalStore()
    handoff = BoundedFeatureCommitHandoff(16)
    completed = Event()
    observed = []

    def capture(event):
        observed.append(event)
        if len(observed) == 2:
            completed.set()

    runtime = LiveSignalRuntime(
        SignalRuntimeConfig(
            definitions=(first, second),
            enabled_definition_ids_by_instrument={
                "NQU6.CME": ("runtime_context", "alternate_context"),
            },
            evaluation_poll_seconds=0.01,
        ),
        store,
        FixedSessionResolver(),
        handoff,
        clock=lambda: STARTED,
        on_evaluation=capture,
    )
    runtime.start()
    assert handoff.offer(revisions("NQU6.CME", 1))
    assert completed.wait(1)
    assert runtime.stop(1)

    assert {event.definition_id for event in observed} == {
        "runtime_context",
        "alternate_context",
    }
    assert runtime.snapshot.open_signal_count == 2


def test_runtime_restores_verified_open_episode_before_consuming_features() -> None:
    store = MemorySignalStore()
    config = SignalRuntimeConfig(
        definitions=(definition(),),
        enabled_definition_ids_by_instrument={"NQU6.CME": ("runtime_context",)},
        evaluation_poll_seconds=0.01,
    )
    first_handoff = BoundedFeatureCommitHandoff(16)
    armed = Event()
    first = LiveSignalRuntime(
        config,
        store,
        FixedSessionResolver(),
        first_handoff,
        clock=lambda: STARTED,
        on_evaluation=lambda event: armed.set(),
    )
    first.start()
    assert first_handoff.offer(revisions("NQU6.CME", 1))
    assert armed.wait(1)
    assert first.stop(1)

    restarted = LiveSignalRuntime(
        config,
        store,
        FixedSessionResolver(),
        BoundedFeatureCommitHandoff(16),
        clock=lambda: STARTED + timedelta(minutes=2),
    )
    restarted.start()
    assert restarted.snapshot.restored_open_signal_count == 1
    assert restarted.snapshot.open_signal_count == 1
    assert restarted.stop(1)


def test_runtime_fails_closed_and_requeues_unprocessed_revision() -> None:
    class FailingSessionResolver:
        def __init__(self) -> None:
            self.entered = Event()

        def session_window(self, instrument_id, timestamp):
            self.entered.set()
            raise RuntimeError("calendar unavailable")

    resolver = FailingSessionResolver()
    handoff = BoundedFeatureCommitHandoff(16)
    runtime = LiveSignalRuntime(
        SignalRuntimeConfig(
            definitions=(definition(),),
            enabled_definition_ids_by_instrument={"NQU6.CME": ("runtime_context",)},
            evaluation_poll_seconds=0.01,
        ),
        MemorySignalStore(),
        resolver,
        handoff,
        clock=lambda: STARTED,
    )
    runtime.start()
    assert handoff.offer(revisions("NQU6.CME", 1))
    assert resolver.entered.wait(1)
    assert runtime.stop(1)

    assert runtime.snapshot.status == LiveSignalRuntimeStatus.FAILED
    assert runtime.snapshot.last_error == "RuntimeError: calendar unavailable"
    assert handoff.snapshot.pending_count == 1


def test_runtime_projects_lifecycle_only_after_durable_write() -> None:
    store = MemorySignalStore()
    handoff = BoundedFeatureCommitHandoff(16)
    completed = Event()
    projections = []

    def capture(projection):
        if isinstance(projection, SignalLifecycleProjection):
            assert store.lifecycle_writes == 1
            completed.set()
        projections.append(projection)
        return True

    runtime = LiveSignalRuntime(
        SignalRuntimeConfig(
            definitions=(definition(),),
            enabled_definition_ids_by_instrument={
                "NQU6.CME": ("runtime_context",),
            },
            evaluation_poll_seconds=0.01,
        ),
        store,
        FixedSessionResolver(),
        handoff,
        clock=lambda: STARTED,
        on_projection=capture,
    )

    runtime.start()
    assert handoff.offer(revisions("NQU6.CME", 1))
    assert completed.wait(1)
    assert runtime.stop(1)

    lifecycle = [item for item in projections if isinstance(item, SignalLifecycleProjection)]
    runtime_events = [item for item in projections if isinstance(item, SignalRuntimeProjection)]
    assert len(lifecycle) == 1
    assert lifecycle[0].kind == SignalLifecycleProjectionKind.TRANSITION
    assert lifecycle[0].signal.status == SignalStatus.ARMED
    assert lifecycle[0].transition_id is not None
    assert [item.kind for item in runtime_events] == [
        SignalRuntimeProjectionKind.STARTED,
        SignalRuntimeProjectionKind.HEARTBEAT,
        SignalRuntimeProjectionKind.STOPPED,
    ]

    lines: list[str] = []
    writer = BoundedSignalProjectionWriter(
        lines.append,
        lambda _instrument_id: "ACTIVE",
        queue_size=4,
        dedupe_size=8,
        poll_seconds=0.01,
    )
    writer.start()
    assert writer.submit(lifecycle[0])
    assert writer.submit(lifecycle[0])
    assert writer.stop(1)
    assert writer.snapshot.rendered_count == 1
    assert writer.snapshot.duplicate_count == 1
    assert lines[0].startswith("SIGNAL_ARMED | role=ACTIVE | NQU6.CME | definition=runtime_context")
    assert "location=support@5m:100-100" in lines[0]


def test_projection_callback_failure_never_fails_signal_runtime() -> None:
    handoff = BoundedFeatureCommitHandoff(16)

    def fail(_projection):
        raise RuntimeError("presentation unavailable")

    runtime = LiveSignalRuntime(
        SignalRuntimeConfig(
            definitions=(definition(),),
            enabled_definition_ids_by_instrument={
                "NQU6.CME": ("runtime_context",),
            },
            evaluation_poll_seconds=0.01,
        ),
        MemorySignalStore(),
        FixedSessionResolver(),
        handoff,
        clock=lambda: STARTED,
        on_projection=fail,
    )

    runtime.start()
    assert handoff.offer(revisions("NQU6.CME", 1))
    deadline = datetime.now(UTC) + timedelta(seconds=1)
    while runtime.snapshot.evaluation_count < 1 and datetime.now(UTC) < deadline:
        Event().wait(0.01)
    assert runtime.stop(1)

    assert runtime.snapshot.status == LiveSignalRuntimeStatus.STOPPED
    assert runtime.snapshot.lifecycle_write_count == 1
    assert runtime.snapshot.projection_callback_error_count >= 3


def test_runtime_labels_verified_open_state_as_restored_not_fresh() -> None:
    store = MemorySignalStore()
    first_handoff = BoundedFeatureCommitHandoff(16)
    armed = Event()
    config = SignalRuntimeConfig(
        definitions=(definition(),),
        enabled_definition_ids_by_instrument={"NQU6.CME": ("runtime_context",)},
        evaluation_poll_seconds=0.01,
    )
    first = LiveSignalRuntime(
        config,
        store,
        FixedSessionResolver(),
        first_handoff,
        clock=lambda: STARTED,
        on_evaluation=lambda _event: armed.set(),
    )
    first.start()
    assert first_handoff.offer(revisions("NQU6.CME", 1))
    assert armed.wait(1)
    assert first.stop(1)

    projections = []
    restarted = LiveSignalRuntime(
        config,
        store,
        FixedSessionResolver(),
        BoundedFeatureCommitHandoff(16),
        clock=lambda: STARTED + timedelta(minutes=2),
        on_projection=lambda projection: projections.append(projection) or True,
    )
    restarted.start()
    assert restarted.stop(1)

    restored = [item for item in projections if isinstance(item, SignalLifecycleProjection)]
    assert len(restored) == 1
    assert restored[0].kind == SignalLifecycleProjectionKind.RESTORED
    assert restored[0].transition_id is None
