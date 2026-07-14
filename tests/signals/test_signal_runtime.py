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
    LiveSignalRuntime,
    LiveSignalRuntimeStatus,
    LocationPolicyConfig,
    LocationSourceKind,
    LocationSourcePolicyConfig,
    SignalDefinitionConfig,
    SignalRuntimeConfig,
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
            direction_score=1,
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
            if all(
                value is None or getattr(signal, key) == value
                for key, value in filters.items()
            )
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
