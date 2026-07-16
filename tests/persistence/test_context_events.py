from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
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
from markeitech.context_events import (
    ContextDetectionStatus,
    ContextEventKind,
    MarketContextTransitionDetector,
)
from markeitech.persistence import PersistenceConfig, SQLiteMetadataStore

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


def committed_revisions(store: SQLiteMetadataStore):
    values = (
        feature(0, trend=TrendState.BULLISH, location=ProfileLocation.BELOW_VALUE),
        feature(1, trend=TrendState.BEARISH, location=ProfileLocation.LOWER_VALUE),
        feature(2, trend=TrendState.RANGE, location=ProfileLocation.ABOVE_VALUE),
    )
    return store.commit_feature_snapshots(values, committed_ts=START + timedelta(minutes=3))


def test_context_events_and_checkpoint_commit_atomically_and_idempotently(
    tmp_path: Path,
) -> None:
    with SQLiteMetadataStore(settings(tmp_path)) as store:
        first, second, _ = committed_revisions(store)
        detector = MarketContextTransitionDetector()
        seeded = detector.apply(first)
        transitioned = detector.apply(second)

        seed_result = store.commit_context_detection(seeded)
        first_result = store.commit_context_detection(transitioned)
        retry_result = store.commit_context_detection(transitioned)

        assert seed_result.checkpoint_advanced
        assert seed_result.committed_event_count == 0
        assert first_result.committed_event_count == 2
        assert first_result.committed_event_ids == tuple(
            event.event_id for event in transitioned.events
        )
        assert first_result.duplicate_event_count == 0
        assert not retry_result.checkpoint_advanced
        assert retry_result.committed_event_count == 0
        assert retry_result.duplicate_event_count == 2
        assert retry_result.committed_event_ids == ()
        assert store.load_context_checkpoints() == (transitioned.checkpoint,)
        assert store.load_context_events() == transitioned.events
        assert store.load_context_events(kind=ContextEventKind.TREND_CHANGED) == (
            transitioned.events[0],
        )


def test_restart_seed_resumes_after_durable_checkpoint_without_replay(tmp_path: Path) -> None:
    config = settings(tmp_path)
    with SQLiteMetadataStore(config) as store:
        first, second, third = committed_revisions(store)
        detector = MarketContextTransitionDetector()
        store.commit_context_detection(detector.apply(first))
        store.commit_context_detection(detector.apply(second))

    with SQLiteMetadataStore(config) as restarted:
        detector = MarketContextTransitionDetector()
        detector.seed(restarted.load_context_checkpoints())
        duplicate = detector.apply(second)
        next_result = detector.apply(third)

        assert duplicate.status == ContextDetectionStatus.DUPLICATE
        assert next_result.status == ContextDetectionStatus.APPLIED
        assert [event.kind for event in next_result.events] == [
            ContextEventKind.TREND_CHANGED,
            ContextEventKind.VALUE_AREA_REGION_CHANGED,
        ]
        committed = restarted.commit_context_detection(next_result)
        assert committed.committed_event_count == 2
        assert len(restarted.load_context_events()) == 4


def test_unchanged_state_advances_checkpoint_without_emitting_event(tmp_path: Path) -> None:
    with SQLiteMetadataStore(settings(tmp_path)) as store:
        first, second, _ = committed_revisions(store)
        unchanged = store.commit_feature_snapshots(
            (
                feature(
                    3,
                    trend=TrendState.BEARISH,
                    location=ProfileLocation.UPPER_VALUE,
                ),
            ),
            committed_ts=START + timedelta(minutes=4),
        )[0]
        detector = MarketContextTransitionDetector()
        store.commit_context_detection(detector.apply(first))
        transitioned = detector.apply(second)
        store.commit_context_detection(transitioned)

        result = detector.apply(unchanged)
        committed = store.commit_context_detection(result)

        assert result.events == ()
        assert committed.checkpoint_advanced
        assert committed.committed_event_count == 0
        assert store.load_context_checkpoints() == (result.checkpoint,)
        assert store.load_context_events() == transitioned.events


def test_checkpoint_regression_rolls_back_new_events(tmp_path: Path) -> None:
    with SQLiteMetadataStore(settings(tmp_path)) as store:
        first, second, _ = committed_revisions(store)
        detector = MarketContextTransitionDetector()
        seeded = detector.apply(first)
        transitioned = detector.apply(second)
        store.commit_context_detection(seeded)
        store.commit_context_detection(transitioned)
        invalid = replace(transitioned, events=(), checkpoint=seeded.checkpoint)

        with pytest.raises(ValueError, match="commit order cannot regress"):
            store.commit_context_detection(invalid)

        assert store.load_context_events() == transitioned.events
        assert store.load_context_checkpoints() == (transitioned.checkpoint,)


def test_event_must_continue_the_durable_checkpoint_chain(tmp_path: Path) -> None:
    with SQLiteMetadataStore(settings(tmp_path)) as store:
        first, second, third = committed_revisions(store)
        detector = MarketContextTransitionDetector()
        seeded = detector.apply(first)
        second_result = detector.apply(second)
        store.commit_context_detection(seeded)

        invalid_event = second_result.events[0].model_copy(
            update={
                "previous_feature_id": third.feature.feature_id,
                "previous_commit_sequence": third.commit_sequence,
            }
        )
        invalid = replace(second_result, events=(invalid_event, *second_result.events[1:]))
        with pytest.raises(ValueError, match="does not continue stored checkpoint"):
            store.commit_context_detection(invalid)

        assert store.load_context_events() == ()
        assert store.load_context_checkpoints() == (seeded.checkpoint,)
