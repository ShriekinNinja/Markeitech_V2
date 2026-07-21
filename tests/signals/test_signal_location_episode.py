from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from markeitech.analytics import AnalyticsTimeframe
from markeitech.signals import (
    LocationEpisodeEventType,
    LocationEpisodeObservation,
    LocationEpisodeTracker,
    LocationInteractionState,
    LocationPolicyConfig,
    LocationQualification,
    LocationQualificationStatus,
    LocationSourceKind,
    LocationSourcePolicyConfig,
    SignalDirection,
    SignalEvidenceFidelity,
    SignalLocationEpisode,
    SignalLocationMatch,
    SignalLocationZone,
    SignalLocationZoneKind,
    build_location_interaction_event,
    intraday_context_definition,
)
from pydantic import ValidationError

NOW = datetime(2026, 7, 14, 13, 30, tzinfo=UTC)
REGIME = "direction_regime:2026-07-14T12:00:00+00:00"


def location_match(
    anchor: str,
    *,
    observed_ts: datetime = NOW,
    direction: SignalDirection = SignalDirection.LONG,
) -> SignalLocationMatch:
    zone_kind = (
        SignalLocationZoneKind.SUPPORT
        if direction == SignalDirection.LONG
        else SignalLocationZoneKind.RESISTANCE
    )
    return SignalLocationMatch(
        zone=SignalLocationZone(
            instrument_id="NQU6.CME",
            direction=direction,
            source_kind=LocationSourceKind.STRUCTURAL_LEVEL,
            zone_kind=zone_kind,
            timeframe=AnalyticsTimeframe.FIFTEEN_MINUTES,
            zone_anchor=anchor,
            source_feature_id="a" * 64,
            observed_ts=observed_ts,
            lower_price=Decimal("100"),
            upper_price=Decimal("100"),
            fidelity=SignalEvidenceFidelity.REPORTED,
            reason_codes=("structural_test_zone",),
        ),
        evaluation_feature_id="b" * 64,
        observed_ts=observed_ts,
        observed_price=Decimal("100"),
        distance=Decimal("0"),
        tolerance=Decimal("1"),
        fidelity=SignalEvidenceFidelity.REPORTED,
        reason_codes=("matched_test_zone",),
    )


def observation(
    ts: datetime,
    status: LocationQualificationStatus,
    *,
    anchors: tuple[str, ...] = (),
    direction: SignalDirection = SignalDirection.LONG,
    regime_anchor: str = REGIME,
    observed_price: Decimal | None = Decimal("100"),
) -> LocationEpisodeObservation:
    matches = tuple(
        location_match(anchor, observed_ts=ts, direction=direction) for anchor in anchors
    )
    return LocationEpisodeObservation(
        definition_id="intraday_context",
        instrument_id="NQU6.CME",
        direction=direction,
        direction_regime_anchor=regime_anchor,
        evaluation_ts=ts,
        observed_price=observed_price,
        qualification=LocationQualification(
            status=status,
            matches=matches,
            reason_codes=(f"test_{status.value}",),
        ),
    )


def test_enters_once_and_stays_active_while_any_entry_zone_overlaps() -> None:
    tracker = LocationEpisodeTracker(intraday_context_definition())
    entered = tracker.evaluate(
        observation(
            NOW,
            LocationQualificationStatus.QUALIFIED,
            anchors=("zone-a", "zone-b"),
        )
    )
    active = tracker.evaluate(
        observation(
            NOW + timedelta(minutes=1),
            LocationQualificationStatus.QUALIFIED,
            anchors=("zone-b", "zone-c"),
        )
    )
    unchanged = tracker.evaluate(
        observation(
            NOW + timedelta(minutes=2),
            LocationQualificationStatus.QUALIFIED,
            anchors=("zone-a", "zone-b"),
        )
    )

    assert entered.event_type == LocationEpisodeEventType.ENTERED
    assert entered.is_state_change
    assert entered.episode is not None
    assert active.event_type == LocationEpisodeEventType.ACTIVE
    assert active.is_state_change
    assert active.episode == entered.episode
    assert active.ended_episode_id is None
    assert unchanged.event_type == LocationEpisodeEventType.ACTIVE
    assert not unchanged.is_state_change


def test_disjoint_qualified_location_replaces_active_episode_immediately() -> None:
    tracker = LocationEpisodeTracker(intraday_context_definition())
    entered = tracker.evaluate(
        observation(
            NOW,
            LocationQualificationStatus.QUALIFIED,
            anchors=("zone-a",),
        )
    )
    replaced = tracker.evaluate(
        observation(
            NOW + timedelta(minutes=1),
            LocationQualificationStatus.QUALIFIED,
            anchors=("zone-b",),
        )
    )

    assert entered.episode is not None
    assert replaced.event_type == LocationEpisodeEventType.REPLACED
    assert replaced.ended_episode_id == entered.episode.episode_id
    assert replaced.episode is not None
    assert replaced.episode.episode_id != entered.episode.episode_id


def test_exit_requires_configured_consecutive_observed_bars_then_reentry_is_new() -> None:
    tracker = LocationEpisodeTracker(intraday_context_definition())
    entered = tracker.evaluate(
        observation(
            NOW,
            LocationQualificationStatus.QUALIFIED,
            anchors=("zone-a",),
        )
    )
    pending = tracker.evaluate(
        observation(
            NOW + timedelta(minutes=1),
            LocationQualificationStatus.NOT_AT_LOCATION,
            observed_price=Decimal("98"),
        )
    )
    exited = tracker.evaluate(
        observation(
            NOW + timedelta(minutes=2),
            LocationQualificationStatus.INSUFFICIENT_CONFLUENCE,
            anchors=("zone-a",),
            observed_price=Decimal("98"),
        )
    )
    reentered = tracker.evaluate(
        observation(
            NOW + timedelta(minutes=3),
            LocationQualificationStatus.QUALIFIED,
            anchors=("zone-a",),
        )
    )

    assert entered.episode is not None
    assert pending.event_type == LocationEpisodeEventType.EXIT_PENDING
    assert pending.outside_confirmation_count == 1
    assert exited.event_type == LocationEpisodeEventType.EXITED
    assert exited.ended_episode_id == entered.episode.episode_id
    assert exited.outside_confirmation_count == 2
    assert reentered.event_type == LocationEpisodeEventType.ENTERED
    assert reentered.episode is not None
    assert reentered.episode.episode_id != entered.episode.episode_id


def test_missing_evidence_preserves_episode_and_breaks_exit_confirmation_sequence() -> None:
    tracker = LocationEpisodeTracker(intraday_context_definition())
    entered = tracker.evaluate(
        observation(
            NOW,
            LocationQualificationStatus.QUALIFIED,
            anchors=("zone-a",),
        )
    )
    tracker.evaluate(
        observation(
            NOW + timedelta(minutes=1),
            LocationQualificationStatus.NOT_AT_LOCATION,
            observed_price=Decimal("98"),
        )
    )
    gap = tracker.evaluate(
        observation(
            NOW + timedelta(minutes=2),
            LocationQualificationStatus.MISSING_EVIDENCE,
            observed_price=None,
        )
    )
    pending_again = tracker.evaluate(
        observation(
            NOW + timedelta(minutes=3),
            LocationQualificationStatus.NOT_AT_LOCATION,
            observed_price=Decimal("98"),
        )
    )

    assert gap.event_type == LocationEpisodeEventType.EVIDENCE_GAP
    assert gap.episode == entered.episode
    assert pending_again.event_type == LocationEpisodeEventType.EXIT_PENDING
    assert pending_again.outside_confirmation_count == 1


def test_direction_regime_change_ends_or_replaces_episode_without_exit_delay() -> None:
    tracker = LocationEpisodeTracker(intraday_context_definition())
    long = tracker.evaluate(
        observation(
            NOW,
            LocationQualificationStatus.QUALIFIED,
            anchors=("long-zone",),
        )
    )
    short = tracker.evaluate(
        observation(
            NOW + timedelta(minutes=1),
            LocationQualificationStatus.QUALIFIED,
            anchors=("short-zone",),
            direction=SignalDirection.SHORT,
            regime_anchor="direction_regime:2026-07-14T13:31:00+00:00",
        )
    )
    ended = tracker.evaluate(
        observation(
            NOW + timedelta(minutes=2),
            LocationQualificationStatus.NOT_AT_LOCATION,
            direction=SignalDirection.LONG,
            regime_anchor="direction_regime:2026-07-14T13:32:00+00:00",
        )
    )

    assert long.episode is not None
    assert short.event_type == LocationEpisodeEventType.REPLACED
    assert short.ended_episode_id == long.episode.episode_id
    assert ended.event_type == LocationEpisodeEventType.EXITED
    assert short.episode is not None
    assert ended.ended_episode_id == short.episode.episode_id


def test_exact_retry_is_idempotent_and_conflicting_or_backward_time_fails_closed() -> None:
    tracker = LocationEpisodeTracker(intraday_context_definition())
    first_observation = observation(
        NOW,
        LocationQualificationStatus.QUALIFIED,
        anchors=("zone-a",),
    )
    first = tracker.evaluate(first_observation)

    assert tracker.evaluate(first_observation) == first
    with pytest.raises(ValueError, match="conflicting location observation"):
        tracker.evaluate(
            observation(
                NOW,
                LocationQualificationStatus.QUALIFIED,
                anchors=("zone-b",),
            )
        )
    with pytest.raises(ValueError, match="cannot move backward"):
        tracker.evaluate(
            observation(
                NOW - timedelta(minutes=1),
                LocationQualificationStatus.NOT_AT_LOCATION,
            )
        )


def test_episode_identity_is_independent_of_entry_match_order() -> None:
    first = location_match("zone-a")
    second = location_match("zone-b")
    values = {
        "definition_id": "intraday_context",
        "instrument_id": "NQU6.CME",
        "direction": SignalDirection.LONG,
        "direction_regime_anchor": REGIME,
        "entry_ts": NOW,
    }
    ordered = SignalLocationEpisode(entry_matches=(first, second), **values)
    reversed_order = SignalLocationEpisode(entry_matches=(second, first), **values)

    assert ordered.episode_id == reversed_order.episode_id


def test_episode_contract_rejects_cross_instrument_direction_and_timestamp() -> None:
    original = location_match("zone-a")
    values = {
        "definition_id": "intraday_context",
        "instrument_id": "NQU6.CME",
        "direction": SignalDirection.LONG,
        "direction_regime_anchor": REGIME,
        "entry_ts": NOW,
    }
    wrong_instrument = original.model_copy(
        update={"zone": original.zone.model_copy(update={"instrument_id": "ESU6.CME"})}
    )
    wrong_direction = original.model_copy(
        update={"zone": original.zone.model_copy(update={"direction": SignalDirection.SHORT})}
    )
    wrong_time = original.model_copy(update={"observed_ts": NOW + timedelta(minutes=1)})

    with pytest.raises(ValidationError, match="one instrument"):
        SignalLocationEpisode(entry_matches=(wrong_instrument,), **values)
    with pytest.raises(ValidationError, match="align with direction"):
        SignalLocationEpisode(entry_matches=(wrong_direction,), **values)
    with pytest.raises(ValidationError, match="share entry timestamp"):
        SignalLocationEpisode(entry_matches=(wrong_time,), **values)


def test_exit_confirmation_is_definition_configuration() -> None:
    definition = intraday_context_definition()
    assert definition.location_policy is not None
    definition = definition.model_copy(
        update={
            "location_policy": LocationPolicyConfig(
                sources=(
                    LocationSourcePolicyConfig(
                        source_kind=LocationSourceKind.STRUCTURAL_LEVEL,
                        timeframes=(AnalyticsTimeframe.FIFTEEN_MINUTES,),
                    ),
                ),
                exit_confirmation_bars=1,
            )
        }
    )
    tracker = LocationEpisodeTracker(definition)
    entered = tracker.evaluate(
        observation(
            NOW,
            LocationQualificationStatus.QUALIFIED,
            anchors=("zone-a",),
        )
    )
    exited = tracker.evaluate(
        observation(
            NOW + timedelta(minutes=1),
            LocationQualificationStatus.NOT_AT_LOCATION,
            observed_price=Decimal("98"),
        )
    )

    assert entered.episode is not None
    assert exited.event_type == LocationEpisodeEventType.EXITED
    assert exited.ended_episode_id == entered.episode.episode_id


@pytest.mark.parametrize(
    ("direction", "favorable_price"),
    (
        (SignalDirection.LONG, Decimal("102")),
        (SignalDirection.SHORT, Decimal("98")),
    ),
)
def test_favorable_departure_preserves_episode_and_resets_adverse_confirmation(
    direction: SignalDirection,
    favorable_price: Decimal,
) -> None:
    tracker = LocationEpisodeTracker(intraday_context_definition())
    entered = tracker.evaluate(
        observation(
            NOW,
            LocationQualificationStatus.QUALIFIED,
            anchors=("zone-a",),
            direction=direction,
        )
    )
    favorable = tracker.evaluate(
        observation(
            NOW + timedelta(minutes=1),
            LocationQualificationStatus.NOT_AT_LOCATION,
            direction=direction,
            observed_price=favorable_price,
        )
    )

    assert favorable.event_type == LocationEpisodeEventType.FAVORABLE_DEPARTURE
    assert favorable.episode == entered.episode
    assert favorable.ended_episode_id is None
    assert favorable.outside_confirmation_count == 0
    assert favorable.reason_codes == ("location_rejection_pending",)
    assert favorable.interaction_state == LocationInteractionState.DEPARTURE_PENDING


@pytest.mark.parametrize(
    ("direction", "favorable_price"),
    (
        (SignalDirection.LONG, Decimal("102")),
        (SignalDirection.SHORT, Decimal("98")),
    ),
)
def test_rejection_requires_consecutive_favorable_closes(
    direction: SignalDirection,
    favorable_price: Decimal,
) -> None:
    tracker = LocationEpisodeTracker(intraday_context_definition())
    entered = tracker.evaluate(
        observation(
            NOW,
            LocationQualificationStatus.QUALIFIED,
            anchors=("zone-a",),
            direction=direction,
        )
    )
    pending = tracker.evaluate(
        observation(
            NOW + timedelta(minutes=1),
            LocationQualificationStatus.NOT_AT_LOCATION,
            direction=direction,
            observed_price=favorable_price,
        )
    )
    rejected = tracker.evaluate(
        observation(
            NOW + timedelta(minutes=2),
            LocationQualificationStatus.NOT_AT_LOCATION,
            direction=direction,
            observed_price=favorable_price,
        )
    )

    assert entered.interaction_state == LocationInteractionState.TOUCHED
    assert pending.event_type == LocationEpisodeEventType.FAVORABLE_DEPARTURE
    assert rejected.event_type == LocationEpisodeEventType.REJECTED
    assert rejected.interaction_state == LocationInteractionState.REJECTED
    assert rejected.reason_codes == ("location_rejection_confirmed",)


def test_restart_restores_pending_rejection_confirmation_progress() -> None:
    definition = intraday_context_definition()
    tracker = LocationEpisodeTracker(definition)
    entered_observation = observation(
        NOW,
        LocationQualificationStatus.QUALIFIED,
        anchors=("zone-a",),
    )
    entered = tracker.evaluate(entered_observation)
    pending_observation = observation(
        NOW + timedelta(minutes=1),
        LocationQualificationStatus.NOT_AT_LOCATION,
        observed_price=Decimal("102"),
    )
    pending = tracker.evaluate(pending_observation)
    assert entered.episode is not None
    pending_event = build_location_interaction_event(
        definition,
        entered.episode,
        pending_observation,
        pending,
    )

    restarted = LocationEpisodeTracker(definition)
    restarted.seed_active_episodes((entered.episode,), (pending_event,))
    rejected = restarted.evaluate(
        observation(
            NOW + timedelta(minutes=2),
            LocationQualificationStatus.NOT_AT_LOCATION,
            observed_price=Decimal("102"),
        )
    )

    assert pending_event.favorable_confirmation_count == 1
    assert rejected.event_type == LocationEpisodeEventType.REJECTED
    assert rejected.reason_codes == ("location_rejection_confirmed",)


def test_unresolved_departure_preserves_episode_without_advancing_breach_count() -> None:
    tracker = LocationEpisodeTracker(intraday_context_definition())
    entered = tracker.evaluate(
        observation(
            NOW,
            LocationQualificationStatus.QUALIFIED,
            anchors=("zone-a",),
        )
    )
    unresolved = tracker.evaluate(
        observation(
            NOW + timedelta(minutes=1),
            LocationQualificationStatus.NOT_AT_LOCATION,
            observed_price=Decimal("100.5"),
        )
    )

    assert unresolved.event_type == LocationEpisodeEventType.DEPARTURE_UNRESOLVED
    assert unresolved.episode == entered.episode
    assert unresolved.outside_confirmation_count == 0


def test_adverse_breach_requires_confirmation_and_exposes_terminal_reason() -> None:
    tracker = LocationEpisodeTracker(intraday_context_definition())
    entered = tracker.evaluate(
        observation(
            NOW,
            LocationQualificationStatus.QUALIFIED,
            anchors=("zone-a",),
        )
    )
    pending = tracker.evaluate(
        observation(
            NOW + timedelta(minutes=1),
            LocationQualificationStatus.NOT_AT_LOCATION,
            observed_price=Decimal("98"),
        )
    )
    exited = tracker.evaluate(
        observation(
            NOW + timedelta(minutes=2),
            LocationQualificationStatus.NOT_AT_LOCATION,
            observed_price=Decimal("98"),
        )
    )

    assert pending.event_type == LocationEpisodeEventType.EXIT_PENDING
    assert pending.reason_codes == ("location_acceptance_pending",)
    assert pending.interaction_state == LocationInteractionState.ACCEPTANCE_PENDING
    assert exited.event_type == LocationEpisodeEventType.EXITED
    assert exited.ended_episode_id == entered.episode.episode_id
    assert exited.reason_codes == ("location_acceptance_confirmed",)
    assert exited.interaction_state == LocationInteractionState.ACCEPTED_THROUGH
