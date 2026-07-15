from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

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
    NotificationOutboxRecord,
    PersistenceConfig,
    SignalPersistenceOutcome,
    SQLiteMetadataStore,
)
from markeitech.signals import (
    CommittedMarketContextBundle,
    DirectionQualificationStatus,
    DirectionRegimeTracker,
    LocationEpisodeDecision,
    LocationEpisodeEventType,
    LocationEpisodeObservation,
    LocationEpisodeTracker,
    LocationQualification,
    LocationQualificationStatus,
    LocationSourceKind,
    SignalDirection,
    SignalEvidenceStage,
    SignalLocationEpisode,
    SignalLocationMatch,
    SignalLocationZone,
    SignalLocationZoneKind,
    SignalStatus,
    build_armed_location_signal,
    intraday_context_definition,
    invalidate_ended_location_signal,
    qualify_direction,
    restore_location_episode,
)

NOW = datetime(2026, 7, 14, 13, 30, tzinfo=UTC)
INSTRUMENT_ID = "NQU6.CME"


def config(path: Path) -> PersistenceConfig:
    return PersistenceConfig(
        catalog_path=path.parent / "catalog",
        metadata_path=path,
        journal_path=path.parent / "journal",
    )


def feature(timeframe: AnalyticsTimeframe, score: int) -> MarketContextFeatureSnapshot:
    return MarketContextFeatureSnapshot(
        configuration_hash="a" * 64,
        input_lineage=(
            FeatureInputLineage(
                instrument_id=INSTRUMENT_ID,
                timeframe=timeframe,
                source="ib",
                input_fidelity=AnalyticsInputFidelity.REPORTED,
                start_ts=NOW - timeframe.duration,
                end_ts=NOW,
                event_count=1,
                identity_hash=f"{list(AnalyticsTimeframe).index(timeframe) + 1:x}" * 64,
            ),
        ),
        snapshot=MarketContextSnapshot(
            instrument_id=INSTRUMENT_ID,
            timeframe=timeframe,
            as_of=NOW,
            source="ib",
            input_fidelity=AnalyticsInputFidelity.REPORTED,
            bar_count=251,
            close=Decimal("100"),
            atr_14=Decimal("10"),
            session_open=Decimal("98"),
            session_high=Decimal("105"),
            session_low=Decimal("95"),
            session_vwap=Decimal("99"),
            session_range_position=Decimal("0.5"),
            vwap_position=VwapPosition.ABOVE,
            trend=TrendState.BULLISH,
            trend_reason_codes=("bullish_test_context",),
            direction_score=score,
            direction_location_reason_codes=("bullish_direction_score",),
        ),
    )


def direction_bundle() -> CommittedMarketContextBundle:
    return CommittedMarketContextBundle(
        instrument_id=INSTRUMENT_ID,
        evaluation_as_of=NOW,
        features=tuple(
            feature(timeframe, 1)
            for timeframe in (
                AnalyticsTimeframe.ONE_MINUTE,
                AnalyticsTimeframe.FIVE_MINUTES,
                AnalyticsTimeframe.FIFTEEN_MINUTES,
                AnalyticsTimeframe.ONE_HOUR,
                AnalyticsTimeframe.DAILY,
            )
        ),
    )


def episode(bundle: CommittedMarketContextBundle) -> SignalLocationEpisode:
    evaluation = bundle.feature(AnalyticsTimeframe.ONE_MINUTE)
    source = bundle.feature(AnalyticsTimeframe.FIVE_MINUTES)
    assert evaluation is not None
    assert source is not None
    location_match = SignalLocationMatch(
        zone=SignalLocationZone(
            instrument_id=INSTRUMENT_ID,
            direction=SignalDirection.LONG,
            source_kind=LocationSourceKind.STRUCTURAL_LEVEL,
            zone_kind=SignalLocationZoneKind.SUPPORT,
            timeframe=AnalyticsTimeframe.FIVE_MINUTES,
            zone_anchor="test-support",
            source_feature_id=source.feature_id,
            observed_ts=NOW,
            lower_price=Decimal("100"),
            upper_price=Decimal("100"),
            fidelity="reported",
            reason_codes=("test_support",),
        ),
        evaluation_feature_id=evaluation.feature_id,
        observed_ts=NOW,
        observed_price=Decimal("100"),
        distance=Decimal("0"),
        tolerance=Decimal("1"),
        fidelity="reported",
        reason_codes=("test_location_match",),
    )
    return SignalLocationEpisode(
        definition_id="intraday_context",
        instrument_id=INSTRUMENT_ID,
        direction=SignalDirection.LONG,
        direction_regime_anchor="direction_regime:2026-07-14T12:00:00+00:00",
        entry_ts=NOW,
        entry_matches=(location_match,),
    )


def armed_setup():
    definition = intraday_context_definition()
    bundle = direction_bundle()
    direction = qualify_direction(bundle, definition)
    assert direction.status == DirectionQualificationStatus.QUALIFIED
    return build_armed_location_signal(definition, episode(bundle), direction)


def later_armed_setup():
    definition = intraday_context_definition()
    bundle = direction_bundle()
    direction = qualify_direction(bundle, definition)
    original = episode(bundle)
    entry_ts = NOW + timedelta(minutes=1)
    later_match = original.entry_matches[0].model_copy(update={"observed_ts": entry_ts})
    later_episode = SignalLocationEpisode(
        definition_id=original.definition_id,
        instrument_id=original.instrument_id,
        direction=original.direction,
        direction_regime_anchor=original.direction_regime_anchor,
        entry_ts=entry_ts,
        entry_matches=(later_match,),
    )
    return build_armed_location_signal(definition, later_episode, direction)


def test_builds_candidate_then_armed_state_from_one_location_episode() -> None:
    setup = armed_setup()
    candidate = setup.candidate
    armed = setup.armed_transition.current

    assert candidate.status == SignalStatus.CANDIDATE
    assert candidate.location_episode_id is not None
    assert candidate.location_matches == ()
    assert armed.status == SignalStatus.ARMED
    assert armed.signal_id == candidate.signal_id
    assert armed.location_episode_id == candidate.location_episode_id
    assert len(armed.location_matches) == 1
    assert {item.stage for item in armed.evidence} == {
        SignalEvidenceStage.DIRECTION,
        SignalEvidenceStage.LOCATION,
    }
    location_ids = {
        item.evidence_id for item in armed.evidence if item.stage == SignalEvidenceStage.LOCATION
    }
    match = armed.location_matches[0]
    assert location_ids == {
        match.zone.source_feature_id,
        match.evaluation_feature_id,
    }
    assert restore_location_episode(armed).episode_id == armed.location_episode_id


def test_distinct_location_episodes_create_distinct_signal_identity() -> None:
    definition = intraday_context_definition()
    bundle = direction_bundle()
    direction = qualify_direction(bundle, definition)
    original = episode(bundle)
    later = original.model_copy(update={"entry_ts": NOW + timedelta(minutes=1)})
    later_match = original.entry_matches[0].model_copy(
        update={"observed_ts": NOW + timedelta(minutes=1)}
    )
    later = later.model_copy(update={"entry_matches": (later_match,)})

    first = build_armed_location_signal(definition, original, direction)
    second = build_armed_location_signal(definition, later, direction)

    assert first.candidate.signal_id != second.candidate.signal_id


def test_arming_rejects_unqualified_or_opposing_direction() -> None:
    definition = intraday_context_definition()
    bundle = direction_bundle()
    qualified = qualify_direction(bundle, definition)
    missing = qualified.__class__(
        status=DirectionQualificationStatus.MISSING_EVIDENCE,
        direction=None,
        is_degraded=True,
        reason_codes=("test_missing",),
        evidence_features=(),
    )

    with pytest.raises(ValueError, match="requires qualified Direction"):
        build_armed_location_signal(definition, episode(bundle), missing)
    opposing = episode(bundle).model_copy(update={"direction": SignalDirection.SHORT})
    with pytest.raises(ValueError, match="align with qualified Direction"):
        build_armed_location_signal(definition, opposing, qualified)


def test_candidate_and_armed_transition_commit_atomically_and_restore(
    tmp_path: Path,
) -> None:
    setup = armed_setup()
    path = tmp_path / "metadata.sqlite3"
    with SQLiteMetadataStore(config(path)) as store:
        assert (
            store.save_signal_candidate_and_transition(
                setup.candidate,
                setup.armed_transition,
            )
            == SignalPersistenceOutcome.TRANSITIONED
        )
        assert (
            store.save_signal_candidate_and_transition(
                setup.candidate,
                setup.armed_transition,
            )
            == SignalPersistenceOutcome.DUPLICATE
        )

    with SQLiteMetadataStore(config(path)) as restarted:
        restored = restarted.load_signal(setup.candidate.signal_id)
        assert restored == setup.armed_transition.current
        assert restarted.load_signal_transitions(setup.candidate.signal_id) == (
            setup.armed_transition,
        )
        assert restored is not None
        assert restore_location_episode(restored).episode_id == restored.location_episode_id


def test_atomic_operation_rejects_transition_from_another_candidate(
    tmp_path: Path,
) -> None:
    setup = armed_setup()
    conflicting = setup.candidate.model_copy(update={"setup_key": "f" * 64})

    with SQLiteMetadataStore(config(tmp_path / "metadata.sqlite3")) as store:
        with pytest.raises(ValueError, match="does not match candidate"):
            store.save_signal_candidate_and_transition(
                conflicting,
                setup.armed_transition,
            )
        assert store.load_signal(conflicting.signal_id) is None


def test_outbox_conflict_rolls_back_candidate_and_armed_transition(tmp_path: Path) -> None:
    setup = armed_setup()
    outbox_id = UUID("bf8a854b-20b6-49c6-859e-9a851046f456")
    values = {
        "outbox_id": outbox_id,
        "topic": "signals.lifecycle",
        "destination_key": "discord.signals.lifecycle",
        "aggregate_key": setup.candidate.signal_id,
        "event_type": "signal.transition",
        "event_schema_version": setup.armed_transition.schema_version,
        "dedupe_key": f"signal-transition:{setup.armed_transition.transition_id}",
        "available_ts": NOW,
        "created_ts": NOW,
        "updated_ts": NOW,
    }
    existing = NotificationOutboxRecord(payload={"version": "existing"}, **values)
    conflicting = NotificationOutboxRecord(payload={"version": "conflicting"}, **values)

    with SQLiteMetadataStore(config(tmp_path / "metadata.sqlite3")) as store:
        store.enqueue(existing)
        with pytest.raises(ValueError, match="conflicts with existing outbox"):
            store.save_signal_candidate_and_transition(
                setup.candidate,
                setup.armed_transition,
                notification=conflicting,
            )
        assert store.load_signal(setup.candidate.signal_id) is None


def test_restore_rejects_corrupt_episode_identity() -> None:
    armed = armed_setup().armed_transition.current
    corrupt = armed.model_copy(update={"location_episode_id": "f" * 64})

    with pytest.raises(ValueError, match="identity is inconsistent"):
        restore_location_episode(corrupt)


def test_episode_replacement_invalidates_old_and_arms_new_atomically(tmp_path: Path) -> None:
    original = armed_setup()
    replacement = later_armed_setup()
    decision = LocationEpisodeDecision(
        event_type=LocationEpisodeEventType.REPLACED,
        episode=restore_location_episode(replacement.armed_transition.current),
        ended_episode_id=original.candidate.location_episode_id,
        outside_confirmation_count=0,
    )
    ended = invalidate_ended_location_signal(
        original.armed_transition.current,
        decision,
        occurred_ts=replacement.candidate.created_ts,
    )

    with SQLiteMetadataStore(config(tmp_path / "metadata.sqlite3")) as store:
        store.save_signal_candidate_and_transition(
            original.candidate,
            original.armed_transition,
        )
        assert (
            store.replace_signal_with_armed_candidate(
                ended,
                replacement.candidate,
                replacement.armed_transition,
            )
            == SignalPersistenceOutcome.TRANSITIONED
        )
        assert (
            store.replace_signal_with_armed_candidate(
                ended,
                replacement.candidate,
                replacement.armed_transition,
            )
            == SignalPersistenceOutcome.DUPLICATE
        )
        assert store.load_signal(original.candidate.signal_id) == ended.current
        assert (
            store.load_signal(replacement.candidate.signal_id)
            == replacement.armed_transition.current
        )


def test_replacement_conflict_rolls_back_old_signal_invalidation(tmp_path: Path) -> None:
    original = armed_setup()
    replacement = later_armed_setup()
    conflicting_candidate = replacement.candidate.model_copy(
        update={"reason_codes": ("conflicting_initial_content",)}
    )
    decision = LocationEpisodeDecision(
        event_type=LocationEpisodeEventType.REPLACED,
        episode=restore_location_episode(replacement.armed_transition.current),
        ended_episode_id=original.candidate.location_episode_id,
        outside_confirmation_count=0,
    )
    ended = invalidate_ended_location_signal(
        original.armed_transition.current,
        decision,
        occurred_ts=replacement.candidate.created_ts,
    )

    with SQLiteMetadataStore(config(tmp_path / "metadata.sqlite3")) as store:
        store.save_signal_candidate_and_transition(
            original.candidate,
            original.armed_transition,
        )
        store.save_signal_candidate(conflicting_candidate)
        with pytest.raises(ValueError, match="different initial content"):
            store.replace_signal_with_armed_candidate(
                ended,
                replacement.candidate,
                replacement.armed_transition,
            )
        assert store.load_signal(original.candidate.signal_id) == original.armed_transition.current


def test_verified_open_signal_seeds_direction_and_location_trackers() -> None:
    definition = intraday_context_definition()
    bundle = direction_bundle()
    armed = armed_setup().armed_transition.current
    restored_episode = restore_location_episode(armed)
    location_tracker = LocationEpisodeTracker(definition)
    location_tracker.seed_active_episodes((restored_episode,))
    next_ts = NOW + timedelta(minutes=1)
    next_match = restored_episode.entry_matches[0].model_copy(update={"observed_ts": next_ts})
    active = location_tracker.evaluate(
        LocationEpisodeObservation(
            definition_id=definition.definition_id,
            instrument_id=INSTRUMENT_ID,
            direction=SignalDirection.LONG,
            direction_regime_anchor=restored_episode.direction_regime_anchor,
            evaluation_ts=next_ts,
            observed_price=next_match.observed_price,
            qualification=LocationQualification(
                status=LocationQualificationStatus.QUALIFIED,
                matches=(next_match,),
                reason_codes=("restart_same_location",),
            ),
        )
    )
    direction_tracker = DirectionRegimeTracker(definition)
    direction_tracker.seed_open_signals((armed,))
    direction = direction_tracker.evaluate(bundle)

    assert active.event_type == LocationEpisodeEventType.ACTIVE
    assert active.episode == restored_episode
    assert direction.candidate is None
    assert direction.regime_anchor == restored_episode.direction_regime_anchor


def test_tracker_seeding_rejects_duplicate_or_invalid_restored_state() -> None:
    definition = intraday_context_definition()
    armed = armed_setup().armed_transition.current
    restored_episode = restore_location_episode(armed)

    with pytest.raises(ValueError, match="multiple active location episodes"):
        LocationEpisodeTracker(definition).seed_active_episodes(
            (restored_episode, restored_episode)
        )
    corrupt_anchor = armed.model_copy(update={"direction_regime_anchor": "invalid"})
    with pytest.raises(ValueError, match="invalid direction regime anchor"):
        DirectionRegimeTracker(definition).seed_open_signals((corrupt_anchor,))
