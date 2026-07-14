from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from markeitech.analytics import AnalyticsTimeframe
from markeitech.signals import (
    LocationPolicyConfig,
    LocationQualification,
    LocationQualificationStatus,
    LocationSourceKind,
    LocationSourcePolicyConfig,
    SignalDirection,
    SignalEvidenceFidelity,
    SignalLocationMatch,
    SignalLocationZone,
    SignalLocationZoneKind,
    intraday_context_definition,
)
from pydantic import ValidationError

NOW = datetime(2026, 7, 14, 13, 30, tzinfo=UTC)


def zone(**updates: object) -> SignalLocationZone:
    values: dict[str, object] = {
        "instrument_id": "NQU6.CME",
        "direction": SignalDirection.LONG,
        "source_kind": LocationSourceKind.STRUCTURAL_LEVEL,
        "zone_kind": SignalLocationZoneKind.SUPPORT,
        "timeframe": AnalyticsTimeframe.FIFTEEN_MINUTES,
        "zone_anchor": "swing_support:2026-07-14T12:45:00+00:00:29580.00",
        "source_feature_id": "a" * 64,
        "observed_ts": NOW,
        "lower_price": Decimal("29577.00"),
        "upper_price": Decimal("29583.00"),
        "fidelity": SignalEvidenceFidelity.INFERRED,
        "reason_codes": ("near_15m_structural_support",),
    }
    values.update(updates)
    return SignalLocationZone(**values)


def match(**updates: object) -> SignalLocationMatch:
    values: dict[str, object] = {
        "zone": zone(),
        "evaluation_feature_id": "b" * 64,
        "observed_ts": NOW + timedelta(minutes=1),
        "observed_price": Decimal("29584.00"),
        "distance": Decimal("1.00"),
        "tolerance": Decimal("4.00"),
        "fidelity": SignalEvidenceFidelity.INFERRED,
        "reason_codes": ("price_within_atr_tolerance",),
    }
    values.update(updates)
    return SignalLocationMatch(**values)


def test_zone_identity_uses_semantic_anchor_not_developing_bounds_or_feature_revision() -> None:
    original = zone()
    revised = zone(
        source_feature_id="c" * 64,
        observed_ts=NOW + timedelta(minutes=1),
        lower_price=Decimal("29578.00"),
        upper_price=Decimal("29584.00"),
        reason_codes=("recalculated_developing_zone",),
    )
    different_origin = zone(
        zone_anchor="swing_support:2026-07-14T13:00:00+00:00:29580.00"
    )

    assert original.zone_id == revised.zone_id
    assert original.model_dump() != revised.model_dump()
    assert original.zone_id != different_origin.zone_id


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"lower_price": Decimal("29584"), "upper_price": Decimal("29583")}, "lower price"),
        ({"source_kind": LocationSourceKind.FAIR_VALUE_GAP}, "must match source"),
        ({"zone_kind": SignalLocationZoneKind.RESISTANCE}, "align with signal direction"),
        ({"zone_anchor": " untrimmed"}, "anchor must be trimmed"),
        ({"fidelity": SignalEvidenceFidelity.UNAVAILABLE}, "requires available evidence"),
    ],
)
def test_zone_rejects_inconsistent_semantics(
    updates: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        zone(**updates)


def test_vwap_zone_can_align_with_either_direction_but_identity_remains_directional() -> None:
    long = zone(
        source_kind=LocationSourceKind.SESSION_VWAP,
        zone_kind=SignalLocationZoneKind.SESSION_VWAP,
        zone_anchor="session:2026-07-14:session_vwap",
    )
    short = zone(
        direction=SignalDirection.SHORT,
        source_kind=LocationSourceKind.SESSION_VWAP,
        zone_kind=SignalLocationZoneKind.SESSION_VWAP,
        zone_anchor="session:2026-07-14:session_vwap",
    )

    assert long.zone_id != short.zone_id


def test_location_match_retains_zone_and_exact_evaluation_evidence() -> None:
    observed = match()

    assert observed.zone.zone_id == zone().zone_id
    assert observed.evaluation_feature_id == "b" * 64

    with pytest.raises(ValidationError, match="cannot exceed tolerance"):
        match(distance=Decimal("5"), tolerance=Decimal("4"))
    with pytest.raises(ValidationError, match="cannot precede zone evidence"):
        match(observed_ts=NOW - timedelta(minutes=1))
    with pytest.raises(ValidationError, match="requires available evidence"):
        match(fidelity=SignalEvidenceFidelity.UNAVAILABLE)


def test_location_qualification_status_is_consistent_with_matches() -> None:
    qualified = LocationQualification(
        status=LocationQualificationStatus.QUALIFIED,
        matches=(match(),),
        reason_codes=("minimum_location_sources_met",),
    )

    assert qualified.matches[0].zone.zone_id == zone().zone_id
    with pytest.raises(ValidationError, match="requires at least one match"):
        LocationQualification(
            status=LocationQualificationStatus.QUALIFIED,
            reason_codes=("invalid_test_result",),
        )
    with pytest.raises(ValidationError, match="cannot contain matches"):
        LocationQualification(
            status=LocationQualificationStatus.NOT_AT_LOCATION,
            matches=(match(),),
            reason_codes=("invalid_test_result",),
        )
    with pytest.raises(ValidationError, match="cannot repeat a semantic zone"):
        LocationQualification(
            status=LocationQualificationStatus.INSUFFICIENT_CONFLUENCE,
            matches=(match(), match(evaluation_feature_id="c" * 64)),
            reason_codes=("invalid_test_result",),
        )


def test_location_policy_requires_distinct_sources_and_unique_timeframes() -> None:
    structural = LocationSourcePolicyConfig(
        source_kind=LocationSourceKind.STRUCTURAL_LEVEL,
        timeframes=(AnalyticsTimeframe.FIFTEEN_MINUTES,),
    )

    with pytest.raises(ValidationError, match="timeframes must be unique"):
        LocationSourcePolicyConfig(
            source_kind=LocationSourceKind.FAIR_VALUE_GAP,
            timeframes=(AnalyticsTimeframe.FIVE_MINUTES, AnalyticsTimeframe.FIVE_MINUTES),
        )
    with pytest.raises(ValidationError, match="source kinds must be unique"):
        LocationPolicyConfig(sources=(structural, structural))
    with pytest.raises(ValidationError, match="cannot exceed configured sources"):
        LocationPolicyConfig(sources=(structural,), minimum_distinct_sources=2)


def test_intraday_definition_declares_reviewable_location_policy() -> None:
    definition = intraday_context_definition()
    assert definition.location_policy is not None

    policies = {
        item.source_kind: item for item in definition.location_policy.sources
    }
    assert set(policies) == set(LocationSourceKind)
    assert policies[LocationSourceKind.STRUCTURAL_LEVEL].timeframes == (
        AnalyticsTimeframe.FIFTEEN_MINUTES,
        AnalyticsTimeframe.FIVE_MINUTES,
    )
    assert policies[LocationSourceKind.FAIR_VALUE_GAP].proximity_atr_fraction == 0
    assert definition.location_policy.minimum_distinct_sources == 1
    assert definition.configuration_hash != definition.model_copy(
        update={
            "location_policy": definition.location_policy.model_copy(
                update={"minimum_distinct_sources": 2}
            )
        }
    ).configuration_hash
