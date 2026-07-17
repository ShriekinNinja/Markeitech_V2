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
from markeitech.domain import OneMinuteBar
from markeitech.notifications import build_signal_transition_notification
from markeitech.persistence import CommittedFeatureRevision
from markeitech.signals import (
    AggressionPolicyConfig,
    BoundedAggressionObservationStore,
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
    SignalConfirmationMethod,
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


def aggression_definition() -> SignalDefinitionConfig:
    return definition().model_copy(
        update={
            "aggression_policy": AggressionPolicyConfig(
                window_bars=3,
                expiry_observation_bars=5,
                minimum_pace_baseline_bars=3,
                bar_proxy_minimum_pace_ratio=Decimal("1.0"),
            )
        }
    )


def observation_bar(
    minute: int,
    *,
    source: str,
    open_price: str,
    high: str,
    low: str,
    close: str,
) -> OneMinuteBar:
    open_ts = STARTED + timedelta(minutes=minute)
    close_ts = open_ts + timedelta(minutes=1)
    classified = source == "classified_ticks"
    return OneMinuteBar(
        instrument_id="NQU6.CME",
        event_ts=close_ts,
        ts_init=close_ts,
        open_ts=open_ts,
        close_ts=close_ts,
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("100"),
        buy_volume=Decimal("70") if classified else Decimal("0"),
        sell_volume=Decimal("30") if classified else Decimal("0"),
        unknown_volume=Decimal("0") if classified else Decimal("100"),
        source=source,
    )


def feature(
    instrument_id: str,
    timeframe: AnalyticsTimeframe,
    as_of: datetime,
    *,
    revision: str,
    direction_score: int = 1,
    close: Decimal = Decimal("100"),
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
            close=close,
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
        self.notifications = []

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
        self.notifications.append(kwargs.get("notification"))

    def replace_signal_with_armed_candidate(self, ended_event, candidate, armed_event, **kwargs):
        self.signals[ended_event.signal_id] = ended_event.current
        self.signals[candidate.signal_id] = armed_event.current
        self.lifecycle_writes += 1
        self.notifications.extend(
            (kwargs.get("ended_notification"), kwargs.get("armed_notification"))
        )

    def apply_signal_transition(self, event, **kwargs):
        self.signals[event.signal_id] = event.current
        self.lifecycle_writes += 1
        self.notifications.append(kwargs.get("notification"))


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


def _expired_runtime_for_location_exit(store, handoff, observations):
    events = []
    expired = Event()
    terminal_episode = Event()

    def capture(event):
        events.append(event)
        if event.signal_status == SignalStatus.EXPIRED:
            expired.set()
        if event.episode_event == LocationEpisodeEventType.EXITED:
            terminal_episode.set()

    runtime = LiveSignalRuntime(
        SignalRuntimeConfig(
            definitions=(aggression_definition(),),
            enabled_definition_ids_by_instrument={"NQU6.CME": ("runtime_context",)},
            evaluation_poll_seconds=0.01,
        ),
        store,
        FixedSessionResolver(),
        handoff,
        observation_store=observations,
        role_resolver=lambda _instrument_id: "ACTIVE",
        clock=lambda: STARTED,
        on_evaluation=capture,
    )
    runtime.start()
    assert handoff.offer(revisions("NQU6.CME", 1))
    deadline = datetime.now(UTC) + timedelta(seconds=1)
    while runtime.snapshot.open_signal_count != 1 and datetime.now(UTC) < deadline:
        Event().wait(0.01)

    bars = tuple(
        observation_bar(
            minute,
            source="ib",
            open_price="100",
            high="100.25",
            low="99.75",
            close="100",
        )
        for minute in range(1, 6)
    )
    assert observations.offer_committed(bars)
    expired_ts = STARTED + timedelta(minutes=6)
    assert handoff.offer(
        (
            CommittedFeatureRevision(
                feature("NQU6.CME", AnalyticsTimeframe.ONE_MINUTE, expired_ts, revision="8"),
                expired_ts,
                8,
            ),
        )
    )
    assert expired.wait(1)
    assert runtime.snapshot.status == LiveSignalRuntimeStatus.RUNNING
    return runtime, events, terminal_episode


def _offer_runtime_feature(
    handoff,
    as_of: datetime,
    sequence: int,
    *,
    close: Decimal = Decimal("100"),
    direction_score: int = 1,
    revision: str = "x",
) -> None:
    assert handoff.offer(
        (
            CommittedFeatureRevision(
                feature(
                    "NQU6.CME",
                    AnalyticsTimeframe.ONE_MINUTE,
                    as_of,
                    revision=revision,
                    close=close,
                    direction_score=direction_score,
                ),
                as_of,
                sequence,
            ),
        )
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
        notification_factory=lambda event: build_signal_transition_notification(
            event,
            role="ACTIVE",
        ),
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
    assert len(store.notifications) == 1
    notification = store.notifications[0]
    assert notification.destination_key == "signal-lifecycle"
    assert notification.aggregate_key in store.signals
    assert notification.payload["content"].startswith("**SHADOW DLA ARMED | NQU6.CME LONG**")
    assert notification.payload["allowed_mentions"] == {"parse": []}


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


def test_runtime_preserves_armed_episode_after_favorable_location_departure() -> None:
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
    departure_ts = STARTED + timedelta(minutes=2)
    assert handoff.offer(
        (
            CommittedFeatureRevision(
                feature(
                    "NQU6.CME",
                    AnalyticsTimeframe.ONE_MINUTE,
                    departure_ts,
                    revision="5",
                    close=Decimal("102"),
                ),
                departure_ts,
                5,
            ),
        )
    )
    assert completed.wait(1)
    assert runtime.stop(1)

    favorable = observed[-1]
    assert favorable.location_status == LocationQualificationStatus.NOT_AT_LOCATION
    assert favorable.episode_event == LocationEpisodeEventType.FAVORABLE_DEPARTURE
    assert favorable.signal_status == SignalStatus.ARMED
    assert store.lifecycle_writes == 1
    assert runtime.snapshot.open_signal_count == 1


def test_runtime_invalidates_only_after_confirmed_adverse_location_breach() -> None:
    store = MemorySignalStore()
    handoff = BoundedFeatureCommitHandoff(16)
    observed = []
    completed = Event()

    def capture(event):
        observed.append(event)
        if len(observed) == 3:
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
    first_breach_ts = STARTED + timedelta(minutes=2)
    second_breach_ts = STARTED + timedelta(minutes=3)
    assert handoff.offer(
        tuple(
            CommittedFeatureRevision(
                feature(
                    "NQU6.CME",
                    AnalyticsTimeframe.ONE_MINUTE,
                    timestamp,
                    revision=revision,
                    close=Decimal("98"),
                ),
                timestamp,
                sequence,
            )
            for timestamp, revision, sequence in (
                (first_breach_ts, "5", 5),
                (second_breach_ts, "6", 6),
            )
        )
    )
    assert completed.wait(1)
    assert runtime.stop(1)

    pending, invalidated = observed[-2:]
    assert pending.episode_event == LocationEpisodeEventType.EXIT_PENDING
    assert pending.signal_status == SignalStatus.ARMED
    assert invalidated.episode_event == LocationEpisodeEventType.EXITED
    assert invalidated.signal_status == SignalStatus.INVALIDATED
    assert store.lifecycle_writes == 2
    assert runtime.snapshot.open_signal_count == 0
    assert next(iter(store.signals.values())).reason_codes[-1] == (
        "location_adverse_breach_confirmed"
    )


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
    projections = []
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
        on_projection=lambda projection: projections.append(projection) or True,
    )
    runtime.start()
    assert handoff.offer(revisions("NQU6.CME", 1))
    assert resolver.entered.wait(1)
    assert runtime.stop(1)

    snapshot = runtime.snapshot
    assert snapshot.status == LiveSignalRuntimeStatus.FAILED
    assert snapshot.last_error == "RuntimeError: calendar unavailable"
    assert snapshot.failure_phase == "feature_revision"
    assert snapshot.failure_input_identity is not None
    assert "commit_sequence=4" in snapshot.failure_input_identity
    assert snapshot.last_successful_commit_sequence == 3
    assert snapshot.last_traceback is not None
    assert "calendar unavailable" in snapshot.last_traceback
    assert snapshot.handoff_capacity == 16
    assert snapshot.handoff_pending_count == 1
    assert snapshot.handoff_high_watermark == 4
    assert snapshot.handoff_rejected_count == 0
    assert snapshot.handoff_is_closed
    assert handoff.snapshot.pending_count == 1
    assert not handoff.offer(
        (
            CommittedFeatureRevision(
                feature(
                    "NQU6.CME",
                    AnalyticsTimeframe.ONE_MINUTE,
                    STARTED + timedelta(minutes=2),
                    revision="5",
                ),
                STARTED,
                5,
            ),
        )
    )
    assert handoff.snapshot.rejected_count == 1
    failed = [
        projection
        for projection in projections
        if isinstance(projection, SignalRuntimeProjection)
        and projection.kind == SignalRuntimeProjectionKind.FAILED
    ]
    assert len(failed) == 1
    assert failed[0].last_error == "RuntimeError: calendar unavailable"
    assert failed[0].failure_phase == "feature_revision"
    assert failed[0].handoff_pending_count == 1
    assert failed[0].handoff_high_watermark == 4
    assert failed[0].handoff_is_closed


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


def test_runtime_triggers_active_signal_when_feature_arrives_before_committed_bars() -> None:
    store = MemorySignalStore()
    observations = BoundedAggressionObservationStore(32)
    handoff = BoundedFeatureCommitHandoff(32)
    terminal = Event()
    role = {"value": "ACTIVE"}
    runtime = LiveSignalRuntime(
        SignalRuntimeConfig(
            definitions=(aggression_definition(),),
            enabled_definition_ids_by_instrument={"NQU6.CME": ("runtime_context",)},
            evaluation_poll_seconds=0.01,
        ),
        store,
        FixedSessionResolver(),
        handoff,
        observation_store=observations,
        role_resolver=lambda _instrument_id: role["value"],
        clock=lambda: STARTED,
        on_evaluation=lambda event: (
            terminal.set() if event.signal_status == SignalStatus.TRIGGERED else None
        ),
    )
    runtime.start()
    assert handoff.offer(revisions("NQU6.CME", 1))
    deadline = datetime.now(UTC) + timedelta(seconds=1)
    while runtime.snapshot.open_signal_count != 1 and datetime.now(UTC) < deadline:
        Event().wait(0.01)

    role["value"] = "BACKGROUND"
    prices = (
        ("100", "101", "99.5", "100.75"),
        ("100.75", "101.75", "100.5", "101.5"),
        ("101.5", "102.25", "101.25", "102"),
    )
    for index, values in enumerate(prices, start=1):
        as_of = STARTED + timedelta(minutes=index + 1)
        assert handoff.offer(
            (
                CommittedFeatureRevision(
                    feature(
                        "NQU6.CME",
                        AnalyticsTimeframe.ONE_MINUTE,
                        as_of,
                        revision=str(index + 4),
                        close=Decimal(values[3]),
                    ),
                    as_of,
                    index + 4,
                ),
            )
        )
        Event().wait(0.02)
        assert observations.offer_committed(
            (
                observation_bar(
                    index,
                    source="classified_ticks",
                    open_price=values[0],
                    high=values[1],
                    low=values[2],
                    close=values[3],
                ),
                observation_bar(
                    index,
                    source="ib",
                    open_price=values[0],
                    high=values[1],
                    low=values[2],
                    close=values[3],
                ),
            )
        )

    assert terminal.wait(1)
    assert runtime.stop(1)
    signal = next(iter(store.signals.values()))
    assert signal.status == SignalStatus.TRIGGERED
    assert signal.confirmation_context is not None
    assert signal.confirmation_context.method == SignalConfirmationMethod.TICK_AGGRESSION
    assert runtime.snapshot.triggered_signal_count == 1
    assert runtime.snapshot.observation_accepted_bar_count == 6


def test_runtime_expires_once_and_suppresses_same_location_episode() -> None:
    store = MemorySignalStore()
    observations = BoundedAggressionObservationStore(32)
    handoff = BoundedFeatureCommitHandoff(32)
    expired = Event()
    runtime = LiveSignalRuntime(
        SignalRuntimeConfig(
            definitions=(aggression_definition(),),
            enabled_definition_ids_by_instrument={"NQU6.CME": ("runtime_context",)},
            evaluation_poll_seconds=0.01,
        ),
        store,
        FixedSessionResolver(),
        handoff,
        observation_store=observations,
        role_resolver=lambda _instrument_id: "ACTIVE",
        clock=lambda: STARTED,
        on_evaluation=lambda event: (
            expired.set() if event.signal_status == SignalStatus.EXPIRED else None
        ),
    )
    runtime.start()
    assert handoff.offer(revisions("NQU6.CME", 1))
    deadline = datetime.now(UTC) + timedelta(seconds=1)
    while runtime.snapshot.open_signal_count != 1 and datetime.now(UTC) < deadline:
        Event().wait(0.01)
    bars = tuple(
        observation_bar(
            minute,
            source="ib",
            open_price="100",
            high="100.25",
            low="99.75",
            close="100",
        )
        for minute in range(1, 6)
    )
    assert observations.offer_committed(bars)
    latest = STARTED + timedelta(minutes=6)
    assert handoff.offer(
        (
            CommittedFeatureRevision(
                feature(
                    "NQU6.CME",
                    AnalyticsTimeframe.ONE_MINUTE,
                    latest,
                    revision="8",
                ),
                latest,
                8,
            ),
        )
    )
    assert expired.wait(1)
    next_ts = latest + timedelta(minutes=1)
    assert handoff.offer(
        (
            CommittedFeatureRevision(
                feature(
                    "NQU6.CME",
                    AnalyticsTimeframe.ONE_MINUTE,
                    next_ts,
                    revision="9",
                ),
                next_ts,
                9,
            ),
        )
    )
    Event().wait(0.05)
    assert runtime.stop(1)
    assert tuple(signal.status for signal in store.signals.values()) == (SignalStatus.EXPIRED,)
    assert store.lifecycle_writes == 2
    assert runtime.snapshot.expired_signal_count == 1
    assert runtime.snapshot.open_signal_count == 0

    restart_watermark = STARTED + timedelta(minutes=7)
    restarted_evaluation = Event()
    restarted_handoff = BoundedFeatureCommitHandoff(32)
    restarted = LiveSignalRuntime(
        SignalRuntimeConfig(
            definitions=(aggression_definition(),),
            enabled_definition_ids_by_instrument={"NQU6.CME": ("runtime_context",)},
            evaluation_poll_seconds=0.01,
        ),
        store,
        FixedSessionResolver(),
        restarted_handoff,
        observation_store=BoundedAggressionObservationStore(32),
        role_resolver=lambda _instrument_id: "ACTIVE",
        clock=lambda: restart_watermark,
        on_evaluation=lambda _event: restarted_evaluation.set(),
    )
    restarted.start()
    original_warmup = tuple(item.feature for item in revisions("NQU6.CME", 30)[:3])
    warmup = (
        *original_warmup,
        feature(
            "NQU6.CME",
            AnalyticsTimeframe.ONE_MINUTE,
            restart_watermark + timedelta(minutes=1),
            revision="d",
        ),
    )
    assert restarted_handoff.offer(
        tuple(
            CommittedFeatureRevision(value, restart_watermark, 20 + index)
            for index, value in enumerate(warmup)
        )
    )
    assert restarted_evaluation.wait(1)
    assert restarted.stop(1)
    assert restarted.snapshot.restored_open_signal_count == 0
    assert restarted.snapshot.open_signal_count == 0
    assert store.lifecycle_writes == 2


def test_runtime_closes_suppressed_episode_after_confirmed_adverse_exit() -> None:
    store = MemorySignalStore()
    handoff = BoundedFeatureCommitHandoff(32)
    observations = BoundedAggressionObservationStore(32)
    runtime, events, exited = _expired_runtime_for_location_exit(store, handoff, observations)

    try:
        first_breach_ts = STARTED + timedelta(minutes=7)
        second_breach_ts = STARTED + timedelta(minutes=8)
        _offer_runtime_feature(
            handoff,
            first_breach_ts,
            9,
            close=Decimal("98"),
            revision="9",
        )
        _offer_runtime_feature(
            handoff,
            second_breach_ts,
            10,
            close=Decimal("98"),
            revision="a",
        )

        assert exited.wait(1)
        assert runtime.snapshot.status == LiveSignalRuntimeStatus.RUNNING
        pending, closed = events[-2:]
        assert pending.episode_event == LocationEpisodeEventType.EXIT_PENDING
        assert closed.episode_event == LocationEpisodeEventType.EXITED
        assert closed.signal_status is None
        assert closed.signal_id is None
        assert runtime.snapshot.last_error is None
        assert runtime.snapshot.open_signal_count == 0
        assert store.lifecycle_writes == 2
        assert tuple(signal.status for signal in store.signals.values()) == (
            SignalStatus.EXPIRED,
        )
    finally:
        assert runtime.stop(1)


def test_runtime_closes_suppressed_episode_after_direction_regime_exit() -> None:
    store = MemorySignalStore()
    handoff = BoundedFeatureCommitHandoff(32)
    observations = BoundedAggressionObservationStore(32)
    runtime, events, exited = _expired_runtime_for_location_exit(store, handoff, observations)

    try:
        direction_flip_ts = STARTED + timedelta(minutes=7)
        assert handoff.offer(
            (
                CommittedFeatureRevision(
                    feature(
                        "NQU6.CME",
                        AnalyticsTimeframe.ONE_HOUR,
                        direction_flip_ts,
                        revision="9",
                        direction_score=-1,
                    ),
                    direction_flip_ts,
                    9,
                ),
                CommittedFeatureRevision(
                    feature(
                        "NQU6.CME",
                        AnalyticsTimeframe.ONE_MINUTE,
                        direction_flip_ts,
                        revision="a",
                        direction_score=-1,
                    ),
                    direction_flip_ts,
                    10,
                ),
            )
        )

        assert exited.wait(1)
        assert runtime.snapshot.status == LiveSignalRuntimeStatus.RUNNING
        closed = events[-1]
        assert closed.episode_event == LocationEpisodeEventType.EXITED
        assert closed.direction_status == DirectionQualificationStatus.QUALIFIED
        assert closed.signal_status is None
        assert runtime.snapshot.last_error is None
        assert runtime.snapshot.open_signal_count == 0
        assert store.lifecycle_writes == 2
        assert tuple(signal.status for signal in store.signals.values()) == (
            SignalStatus.EXPIRED,
        )
    finally:
        assert runtime.stop(1)


def test_runtime_closes_restored_suppressed_episode_after_exit() -> None:
    store = MemorySignalStore()
    first_handoff = BoundedFeatureCommitHandoff(32)
    first_observations = BoundedAggressionObservationStore(32)
    first, _events, _exited = _expired_runtime_for_location_exit(
        store,
        first_handoff,
        first_observations,
    )
    assert first.stop(1)

    restart_watermark = STARTED + timedelta(minutes=7)
    handoff = BoundedFeatureCommitHandoff(32)
    observations = BoundedAggressionObservationStore(32)
    events = []
    ready = Event()
    exited = Event()

    def capture(event):
        events.append(event)
        if event.episode_event == LocationEpisodeEventType.ACTIVE:
            ready.set()
        if event.episode_event == LocationEpisodeEventType.EXITED:
            exited.set()

    restarted = LiveSignalRuntime(
        SignalRuntimeConfig(
            definitions=(aggression_definition(),),
            enabled_definition_ids_by_instrument={"NQU6.CME": ("runtime_context",)},
            evaluation_poll_seconds=0.01,
        ),
        store,
        FixedSessionResolver(),
        handoff,
        observation_store=observations,
        role_resolver=lambda _instrument_id: "ACTIVE",
        clock=lambda: restart_watermark,
        on_evaluation=capture,
    )
    restarted.start()
    try:
        original_warmup = tuple(item.feature for item in revisions("NQU6.CME", 30)[:3])
        warmup = tuple(
            CommittedFeatureRevision(value, restart_watermark, 20 + index)
            for index, value in enumerate(original_warmup)
        )
        live_ts = restart_watermark + timedelta(minutes=1)
        assert handoff.offer(
            (
                *warmup,
                CommittedFeatureRevision(
                    feature(
                        "NQU6.CME",
                        AnalyticsTimeframe.ONE_MINUTE,
                        live_ts,
                        revision="d",
                    ),
                    live_ts,
                    23,
                ),
            )
        )
        assert ready.wait(1)

        first_breach_ts = restart_watermark + timedelta(minutes=2)
        second_breach_ts = restart_watermark + timedelta(minutes=3)
        _offer_runtime_feature(
            handoff,
            first_breach_ts,
            24,
            close=Decimal("98"),
            revision="e",
        )
        _offer_runtime_feature(
            handoff,
            second_breach_ts,
            25,
            close=Decimal("98"),
            revision="f",
        )

        assert exited.wait(1)
        assert restarted.snapshot.status == LiveSignalRuntimeStatus.RUNNING
        closed = events[-1]
        assert closed.episode_event == LocationEpisodeEventType.EXITED
        assert closed.signal_status is None
        assert restarted.snapshot.last_error is None
        assert restarted.snapshot.restored_open_signal_count == 0
        assert restarted.snapshot.open_signal_count == 0
        assert store.lifecycle_writes == 2
        assert tuple(signal.status for signal in store.signals.values()) == (
            SignalStatus.EXPIRED,
        )
    finally:
        assert restarted.stop(1)


def test_runtime_triggers_background_signal_from_reported_bar_proxy() -> None:
    store = MemorySignalStore()
    observations = BoundedAggressionObservationStore(32)
    baseline = tuple(
        observation_bar(
            minute,
            source="ib",
            open_price="99",
            high="99.25",
            low="98.75",
            close="99",
        )
        for minute in range(-2, 1)
    )
    assert observations.offer_committed(baseline)
    handoff = BoundedFeatureCommitHandoff(32)
    terminal = Event()
    runtime = LiveSignalRuntime(
        SignalRuntimeConfig(
            definitions=(aggression_definition(),),
            enabled_definition_ids_by_instrument={"NQU6.CME": ("runtime_context",)},
            evaluation_poll_seconds=0.01,
        ),
        store,
        FixedSessionResolver(),
        handoff,
        observation_store=observations,
        role_resolver=lambda _instrument_id: "BACKGROUND",
        clock=lambda: STARTED,
        on_evaluation=lambda event: (
            terminal.set() if event.signal_status == SignalStatus.TRIGGERED else None
        ),
    )
    runtime.start()
    assert handoff.offer(revisions("NQU6.CME", 1))
    deadline = datetime.now(UTC) + timedelta(seconds=1)
    while runtime.snapshot.open_signal_count != 1 and datetime.now(UTC) < deadline:
        Event().wait(0.01)
    prices = (
        ("100", "101", "99.5", "100.75"),
        ("100.75", "101.75", "100.5", "101.5"),
        ("101.5", "102.25", "101.25", "102"),
    )
    for index, values in enumerate(prices, start=1):
        bar = observation_bar(
            index,
            source="ib",
            open_price=values[0],
            high=values[1],
            low=values[2],
            close=values[3],
        )
        assert observations.offer_committed((bar,))
        as_of = bar.close_ts
        assert handoff.offer(
            (
                CommittedFeatureRevision(
                    feature(
                        "NQU6.CME",
                        AnalyticsTimeframe.ONE_MINUTE,
                        as_of,
                        revision=str(index + 4),
                        close=Decimal(values[3]),
                    ),
                    as_of,
                    index + 4,
                ),
            )
        )
    assert terminal.wait(1)
    assert runtime.stop(1)
    signal = next(iter(store.signals.values()))
    assert signal.status == SignalStatus.TRIGGERED
    assert signal.confirmation_context is not None
    assert signal.confirmation_context.method == SignalConfirmationMethod.BAR_IMPULSE_PROXY
    assert runtime.snapshot.triggered_signal_count == 1
