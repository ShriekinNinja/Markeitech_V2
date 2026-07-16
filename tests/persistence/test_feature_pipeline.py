from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from threading import Event

import pytest
from markeitech.analytics import (
    AnalyticsInputFidelity,
    AnalyticsTimeframe,
    FeatureInputLineage,
    MarketContextFeatureSnapshot,
    MarketContextSnapshot,
    TrendState,
    VwapPosition,
)
from markeitech.persistence import (
    BoundedFeatureWriter,
    CommittedFeatureRevision,
    FeaturePersistenceCoordinator,
    FeaturePersistenceResult,
    FeatureSubmissionStatus,
    FeatureWriterStatus,
    ParquetFeatureStore,
    PersistenceConfig,
    SQLiteMetadataStore,
)
from markeitech.signals import (
    BoundedFeatureCommitHandoff,
    CommittedFeatureState,
    FeatureHandoffStatus,
    SignalDefinitionConfig,
)

AS_OF = datetime(2026, 7, 14, 10, 1, tzinfo=UTC)


def feature(
    instrument_id: str = "NQU6.CME",
    *,
    as_of: datetime = AS_OF,
    timeframe: AnalyticsTimeframe = AnalyticsTimeframe.ONE_MINUTE,
    configuration_hash: str = "a" * 64,
) -> MarketContextFeatureSnapshot:
    snapshot = MarketContextSnapshot(
        instrument_id=instrument_id,
        timeframe=timeframe,
        as_of=as_of,
        source="classified_ticks",
        input_fidelity=AnalyticsInputFidelity.INFERRED,
        bar_count=251,
        close=Decimal("29605.25"),
        session_open=Decimal("29420"),
        session_high=Decimal("29649.75"),
        session_low=Decimal("29320"),
        session_range_position=Decimal("0.865"),
        vwap_position=VwapPosition.ABOVE,
        trend=TrendState.BULLISH,
        trend_reason_codes=("ema20_above_ema50",),
    )
    return MarketContextFeatureSnapshot(
        configuration_hash=configuration_hash,
        input_lineage=(
            FeatureInputLineage(
                instrument_id=instrument_id,
                timeframe=timeframe,
                source="classified_ticks",
                input_fidelity=AnalyticsInputFidelity.INFERRED,
                start_ts=as_of - timedelta(minutes=250),
                end_ts=as_of,
                event_count=251,
                identity_hash="1" * 64,
            ),
        ),
        snapshot=snapshot,
    )


def config(tmp_path: Path) -> PersistenceConfig:
    return PersistenceConfig(
        catalog_path=tmp_path / "catalog",
        metadata_path=tmp_path / "metadata.sqlite3",
        journal_path=tmp_path / "journal",
    )


def test_catalog_first_commit_recovers_idempotently_after_metadata_failure(
    tmp_path: Path,
) -> None:
    settings = config(tmp_path)
    catalog = ParquetFeatureStore(settings)
    metadata = SQLiteMetadataStore(settings)
    value = feature()

    class FailFirstMetadataCommit:
        def __init__(self) -> None:
            self.failed = False

        def committed_feature_revisions(
            self,
            features: tuple[MarketContextFeatureSnapshot, ...],
        ) -> tuple[CommittedFeatureRevision, ...]:
            return metadata.committed_feature_revisions(features)

        def commit_feature_snapshots(
            self,
            features: tuple[MarketContextFeatureSnapshot, ...],
            *,
            committed_ts: datetime,
        ) -> tuple[CommittedFeatureRevision, ...]:
            if not self.failed:
                self.failed = True
                raise RuntimeError("simulated process loss before metadata commit")
            return metadata.commit_feature_snapshots(features, committed_ts=committed_ts)

    failing = FeaturePersistenceCoordinator(catalog, FailFirstMetadataCommit())
    with pytest.raises(RuntimeError, match="simulated process loss"):
        failing.persist((value,))

    assert catalog.query_history("NQU6.CME") == (value,)
    assert metadata.committed_feature_ids((value,)) == frozenset()
    metadata.close()

    with SQLiteMetadataStore(settings) as restarted_metadata:
        recovered = FeaturePersistenceCoordinator(catalog, restarted_metadata).persist((value,))
        assert recovered.committed_count == 1
        assert recovered.duplicate_count == 0
        assert tuple(item.feature for item in recovered.revisions) == (value,)
        assert restarted_metadata.committed_feature_ids((value,)) == frozenset(
            {value.feature_id}
        )
        assert catalog.query_history("NQU6.CME") == (value,)


def test_coordinator_persists_active_and_background_features_independently(
    tmp_path: Path,
) -> None:
    settings = config(tmp_path)
    catalog = ParquetFeatureStore(settings)
    with SQLiteMetadataStore(settings) as metadata:
        coordinator = FeaturePersistenceCoordinator(catalog, metadata)
        nq = feature()
        es = feature("ESU6.CME")

        first = coordinator.persist((nq, es))
        retry = coordinator.persist((nq, es))

        assert (first.committed_count, first.duplicate_count) == (2, 0)
        assert (retry.committed_count, retry.duplicate_count) == (0, 2)
        assert first.revisions == retry.revisions
        assert [item.commit_sequence for item in first.revisions] == [1, 2]
        assert catalog.query_history("NQU6.CME") == (nq,)
        assert catalog.query_history("ESU6.CME") == (es,)


def test_coordinator_collapses_duplicates_within_one_submission(tmp_path: Path) -> None:
    settings = config(tmp_path)
    catalog = ParquetFeatureStore(settings)
    value = feature()
    with SQLiteMetadataStore(settings) as metadata:
        result = FeaturePersistenceCoordinator(catalog, metadata).persist((value, value))

        assert (result.committed_count, result.duplicate_count) == (1, 1)
        assert tuple(item.feature for item in result.revisions) == (value,)
        assert metadata.committed_feature_ids((value,)) == frozenset({value.feature_id})
        assert catalog.query_history("NQU6.CME") == (value,)


def test_same_timestamp_corrections_keep_restart_stable_commit_order(tmp_path: Path) -> None:
    settings = config(tmp_path)
    first = feature(configuration_hash="a" * 64)
    corrected = feature(configuration_hash="b" * 64)
    with SQLiteMetadataStore(settings) as metadata:
        result = FeaturePersistenceCoordinator(
            ParquetFeatureStore(settings), metadata
        ).persist((first, corrected))
        expected = result.revisions

    with SQLiteMetadataStore(settings) as restarted:
        restored = restarted.committed_feature_revisions((first, corrected))

    assert [item.commit_sequence for item in expected] == [1, 2]
    assert restored == expected


class RecordingCoordinator:
    def __init__(self) -> None:
        self.values: list[MarketContextFeatureSnapshot] = []

    def persist(
        self,
        features: tuple[MarketContextFeatureSnapshot, ...],
    ) -> FeaturePersistenceResult:
        self.values.extend(features)
        return FeaturePersistenceResult(len(features), 0)


def test_bounded_writer_flushes_batches_and_stops_cleanly() -> None:
    coordinator = RecordingCoordinator()
    writer = BoundedFeatureWriter(
        coordinator,  # type: ignore[arg-type]
        queue_size=4,
        batch_size=2,
        poll_seconds=0.01,
    )
    values = (feature(), feature(as_of=AS_OF + timedelta(minutes=1)))

    writer.start()
    assert [writer.submit(value) for value in values] == [
        FeatureSubmissionStatus.ACCEPTED,
        FeatureSubmissionStatus.ACCEPTED,
    ]
    assert writer.flush(1)
    assert writer.stop(1)

    assert coordinator.values == list(values)
    assert writer.snapshot.status == FeatureWriterStatus.STOPPED
    assert writer.snapshot.accepted_count == 2
    assert writer.snapshot.committed_count == 2
    assert writer.snapshot.pending_count == 0


def test_feature_commit_sink_can_only_be_bound_once_before_start() -> None:
    writer = BoundedFeatureWriter(
        RecordingCoordinator(),  # type: ignore[arg-type]
        queue_size=1,
        batch_size=1,
        poll_seconds=0.01,
    )
    writer.set_commit_sink(lambda _revisions: True)

    with pytest.raises(RuntimeError, match="already configured"):
        writer.set_commit_sink(lambda _revisions: True)

    writer.start()
    with pytest.raises(RuntimeError, match="before start"):
        writer.set_commit_sink(lambda _revisions: True)
    assert writer.stop(1)


def test_bounded_writer_fails_closed_and_retains_failed_batch() -> None:
    class FailingCoordinator:
        def persist(
            self,
            features: tuple[MarketContextFeatureSnapshot, ...],
        ) -> FeaturePersistenceResult:
            raise RuntimeError("catalog unavailable")

    writer = BoundedFeatureWriter(
        FailingCoordinator(),  # type: ignore[arg-type]
        queue_size=2,
        batch_size=1,
        poll_seconds=0.01,
    )
    value = feature()
    writer.start()
    assert writer.submit(value) == FeatureSubmissionStatus.ACCEPTED
    assert not writer.flush(1)

    snapshot = writer.snapshot
    assert snapshot.status == FeatureWriterStatus.FAILED
    assert snapshot.pending_count == 1
    assert snapshot.committed_count == 0
    assert snapshot.last_error == "RuntimeError: catalog unavailable"
    assert tuple(writer._queue) == (value,)  # noqa: SLF001
    assert writer.submit(value) == FeatureSubmissionStatus.WRITER_FAILED
    assert writer.stop(1)


def test_bounded_writer_rejects_when_all_pending_capacity_is_occupied() -> None:
    entered = Event()
    release = Event()

    class BlockingCoordinator:
        def persist(
            self,
            features: tuple[MarketContextFeatureSnapshot, ...],
        ) -> FeaturePersistenceResult:
            entered.set()
            assert release.wait(1)
            return FeaturePersistenceResult(len(features), 0)

    writer = BoundedFeatureWriter(
        BlockingCoordinator(),  # type: ignore[arg-type]
        queue_size=1,
        batch_size=1,
        poll_seconds=0.01,
    )
    writer.start()
    assert writer.submit(feature()) == FeatureSubmissionStatus.ACCEPTED
    assert entered.wait(1)
    assert writer.submit(feature(as_of=AS_OF + timedelta(minutes=1))) == (
        FeatureSubmissionStatus.QUEUE_FULL
    )
    release.set()
    assert writer.flush(1)
    assert writer.stop(1)
    assert writer.snapshot.rejected_count == 1


def test_handoff_admits_batches_atomically_and_reports_saturation() -> None:
    revisions = (
        CommittedFeatureRevision(feature(), AS_OF, 1),
        CommittedFeatureRevision(
            feature("ESU6.CME"), AS_OF + timedelta(microseconds=1), 2
        ),
    )
    handoff = BoundedFeatureCommitHandoff(capacity=1)

    assert handoff.publish(revisions) == FeatureHandoffStatus.QUEUE_FULL
    assert handoff.snapshot.pending_count == 0
    assert handoff.snapshot.rejected_count == 2
    assert handoff.publish(revisions[:1]) == FeatureHandoffStatus.ACCEPTED
    assert handoff.drain(1) == revisions[:1]
    handoff.close()
    assert handoff.publish(revisions[:1]) == FeatureHandoffStatus.CLOSED


def test_writer_fails_closed_when_committed_batch_cannot_be_handed_off() -> None:
    value = feature()
    revision = CommittedFeatureRevision(value, AS_OF, 1)

    class CommittedCoordinator:
        def persist(
            self,
            features: tuple[MarketContextFeatureSnapshot, ...],
        ) -> FeaturePersistenceResult:
            return FeaturePersistenceResult(1, 0, (revision, revision))

    handoff = BoundedFeatureCommitHandoff(capacity=1)
    writer = BoundedFeatureWriter(
        CommittedCoordinator(),  # type: ignore[arg-type]
        queue_size=1,
        batch_size=1,
        poll_seconds=0.01,
        commit_sink=handoff.offer,
    )
    writer.start()
    assert writer.submit(value) == FeatureSubmissionStatus.ACCEPTED
    assert not writer.flush(1)

    snapshot = writer.snapshot
    assert snapshot.status == FeatureWriterStatus.FAILED
    assert snapshot.pending_count == 1
    assert snapshot.committed_count == 1
    assert snapshot.handed_off_count == 0
    assert snapshot.last_error == "RuntimeError: feature commit handoff rejected batch"


def test_committed_state_composes_latest_point_in_time_revision() -> None:
    definition = SignalDefinitionConfig(
        definition_id="test_context",
        evaluation_timeframe=AnalyticsTimeframe.ONE_MINUTE,
        primary_direction_timeframes=(AnalyticsTimeframe.ONE_HOUR,),
    )
    state = CommittedFeatureState()
    hourly = CommittedFeatureRevision(
        feature(timeframe=AnalyticsTimeframe.ONE_HOUR), AS_OF, 1
    )
    initial = CommittedFeatureRevision(feature(), AS_OF, 2)
    corrected = CommittedFeatureRevision(
        feature(configuration_hash="b" * 64), AS_OF + timedelta(microseconds=1), 3
    )

    assert state.apply(hourly)
    assert state.compose(hourly, definition) is None
    assert state.apply(initial)
    first_bundle = state.compose(initial, definition)
    assert state.apply(corrected)
    corrected_bundle = state.compose(corrected, definition)

    assert first_bundle is not None
    assert first_bundle.feature(AnalyticsTimeframe.ONE_MINUTE) == initial.feature
    assert corrected_bundle is not None
    assert corrected_bundle.feature(AnalyticsTimeframe.ONE_MINUTE) == corrected.feature
    assert not state.apply(corrected)
    assert state.compose(corrected, definition) == corrected_bundle
