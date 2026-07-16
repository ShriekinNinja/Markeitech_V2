from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from markeitech.analytics import (
    AnalyticsInputFidelity,
    AnalyticsTimeframe,
    FeatureInputLineage,
    MarketContextFeatureSnapshot,
    MarketContextSnapshot,
    ProfileLocation,
    TrendState,
    VwapPosition,
)
from markeitech.context_events import ContextEventKind, MarketContextTransitionDetector
from markeitech.persistence import PersistenceConfig, SQLiteMetadataStore
from markeitech.runtime import BoundedEventLoopBridge, ContextEventCommitProcessor
from markeitech.runtime.context_events import context_transition_notice
from markeitech.runtime.events import MarkeitechBusTopic

START = datetime(2026, 7, 16, 10, 0, tzinfo=UTC)


def settings(tmp_path: Path) -> PersistenceConfig:
    return PersistenceConfig(
        catalog_path=tmp_path / "catalog",
        metadata_path=tmp_path / "metadata.sqlite3",
        journal_path=tmp_path / "journal",
    )


def feature(
    minute: int,
    *,
    trend: TrendState,
    location: ProfileLocation,
) -> MarketContextFeatureSnapshot:
    as_of = START + timedelta(minutes=minute)
    return MarketContextFeatureSnapshot(
        configuration_hash="a" * 64,
        input_lineage=(
            FeatureInputLineage(
                instrument_id="NQU6.CME",
                timeframe=AnalyticsTimeframe.ONE_MINUTE,
                source="classified_ticks",
                input_fidelity=AnalyticsInputFidelity.INFERRED,
                start_ts=as_of - timedelta(minutes=249),
                end_ts=as_of,
                event_count=250,
                identity_hash=f"{minute + 1:x}".zfill(64),
            ),
        ),
        snapshot=MarketContextSnapshot(
            instrument_id="NQU6.CME",
            timeframe=AnalyticsTimeframe.ONE_MINUTE,
            as_of=as_of,
            source="classified_ticks",
            input_fidelity=AnalyticsInputFidelity.INFERRED,
            bar_count=250,
            close=Decimal("29600"),
            session_open=Decimal("29500"),
            session_high=Decimal("29650"),
            session_low=Decimal("29450"),
            session_range_position=Decimal("0.75"),
            vwap_position=VwapPosition.ABOVE,
            trend=trend,
            trend_reason_codes=("test_trend",),
            profile_location=location,
            location_reason_codes=("test_location",),
        ),
    )


def revisions(store: SQLiteMetadataStore):
    return store.commit_feature_snapshots(
        (
            feature(0, trend=TrendState.BULLISH, location=ProfileLocation.BELOW_VALUE),
            feature(1, trend=TrendState.BEARISH, location=ProfileLocation.LOWER_VALUE),
            feature(2, trend=TrendState.RANGE, location=ProfileLocation.ABOVE_VALUE),
        ),
        committed_ts=START + timedelta(minutes=3),
    )


def test_first_reconcile_seeds_latest_revision_without_historical_events(tmp_path: Path) -> None:
    with SQLiteMetadataStore(settings(tmp_path)) as store:
        values = revisions(store)
        processor = ContextEventCommitProcessor(store, None)

        processor.reconcile(values)

        assert store.load_context_checkpoints()[0].feature_id == values[-1].feature.feature_id
        assert store.load_context_events() == ()
        assert processor.snapshot.reconciled_revision_count == 1


def test_reconcile_fills_checkpoint_gap_without_projecting_history(tmp_path: Path) -> None:
    bridge = BoundedEventLoopBridge(8)
    with SQLiteMetadataStore(settings(tmp_path)) as store:
        values = revisions(store)
        detector = MarketContextTransitionDetector()
        store.commit_context_detection(detector.apply(values[0]))
        processor = ContextEventCommitProcessor(store, bridge)

        processor.reconcile(values)

        assert len(store.load_context_events()) == 4
        assert bridge.snapshot.pending_count == 0
        assert processor.snapshot.reconciled_revision_count == 2


def test_live_offer_publishes_only_newly_committed_transitions(tmp_path: Path) -> None:
    bridge = BoundedEventLoopBridge(8)
    with SQLiteMetadataStore(settings(tmp_path)) as store:
        first, second, _ = revisions(store)
        processor = ContextEventCommitProcessor(store, bridge)
        processor.reconcile((first,))

        assert processor.offer((second,))
        assert processor.offer((second,))

        assert len(store.load_context_events()) == 2
        assert bridge.snapshot.pending_count == 2
        assert processor.snapshot.committed_event_count == 2


def test_projection_rejection_does_not_undo_durable_transition(tmp_path: Path) -> None:
    bridge = BoundedEventLoopBridge(1)
    with SQLiteMetadataStore(settings(tmp_path)) as store:
        first, second, _ = revisions(store)
        processor = ContextEventCommitProcessor(store, bridge)
        processor.reconcile((first,))

        assert processor.offer((second,))

        assert len(store.load_context_events()) == 2
        assert processor.snapshot.projection_rejected_count == 2


def test_context_transition_maps_to_operator_notice(tmp_path: Path) -> None:
    with SQLiteMetadataStore(settings(tmp_path)) as store:
        first, second, _ = revisions(store)
        detector = MarketContextTransitionDetector()
        detector.apply(first)
        transition = detector.apply(second).events[0]

    notice = context_transition_notice(transition)

    assert notice.topic == MarkeitechBusTopic.CONTEXT_EVENT
    assert notice.transition_kind == ContextEventKind.TREND_CHANGED.value
    assert notice.previous_value == "bullish"
    assert notice.current_value == "bearish"
    assert notice.commit_sequence == second.commit_sequence
