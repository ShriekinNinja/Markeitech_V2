from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from markeitech.analytics import (
    AnalyticsInputFidelity,
    FairValueGapDirection,
    MarketContextFeatureSnapshot,
)
from markeitech.domain.base import require_utc
from markeitech.domain.market_data import OneMinuteBar
from markeitech.signals.config import (
    LocationSourcePolicyConfig,
    SignalDefinitionConfig,
)
from markeitech.signals.contracts import (
    LocationQualification,
    LocationQualificationStatus,
    LocationSourceKind,
    SignalDirection,
    SignalEvidenceFidelity,
    SignalLocationMatch,
    SignalLocationZone,
    SignalLocationZoneKind,
)
from markeitech.signals.direction import CommittedMarketContextBundle


@dataclass(frozen=True)
class LocationZoneDerivation:
    zones: tuple[SignalLocationZone, ...]
    available_source_kinds: frozenset[LocationSourceKind]
    is_degraded: bool
    reason_codes: tuple[str, ...]


def derive_location_zones(
    bundle: CommittedMarketContextBundle,
    definition: SignalDefinitionConfig,
    direction: SignalDirection,
    *,
    session_start: datetime,
) -> LocationZoneDerivation:
    session_start = require_utc(session_start)
    if session_start > bundle.evaluation_as_of:
        raise ValueError("location session start cannot follow evaluation time")
    policy = definition.location_policy
    if policy is None:
        return LocationZoneDerivation(
            zones=(),
            available_source_kinds=frozenset(),
            is_degraded=True,
            reason_codes=("location_policy_unavailable",),
        )

    zones: list[SignalLocationZone] = []
    available: set[LocationSourceKind] = set()
    reasons: list[str] = []
    degraded = False
    for source_policy in policy.sources:
        source_available = False
        for timeframe in source_policy.timeframes:
            feature = bundle.feature(timeframe)
            if feature is None:
                degraded = True
                reasons.append(
                    f"missing_{timeframe.value}_{source_policy.source_kind.value}_feature"
                )
                continue
            derived, usable = _zones_from_feature(
                feature,
                source_policy.source_kind,
                direction,
                session_start,
            )
            if any(zone.observed_ts > feature.snapshot.as_of for zone in derived):
                raise ValueError("location zone evidence cannot follow source feature")
            source_available |= usable
            zones.extend(derived)
        if source_available:
            available.add(source_policy.source_kind)
        else:
            degraded = True
            reasons.append(f"unavailable_{source_policy.source_kind.value}_source")

    unique_zones: dict[str, SignalLocationZone] = {}
    for zone in zones:
        existing = unique_zones.get(zone.zone_id)
        if existing is not None and existing != zone:
            raise ValueError("one location bundle produced conflicting semantic zones")
        unique_zones[zone.zone_id] = zone
    ordered = tuple(
        sorted(
            unique_zones.values(),
            key=lambda zone: (
                zone.source_kind.value,
                zone.timeframe.duration,
                zone.lower_price,
                zone.upper_price,
                zone.zone_id,
            ),
        )
    )
    return LocationZoneDerivation(
        zones=ordered,
        available_source_kinds=frozenset(available),
        is_degraded=degraded,
        reason_codes=tuple(reasons) or ("location_sources_available",),
    )


def qualify_location(
    bundle: CommittedMarketContextBundle,
    definition: SignalDefinitionConfig,
    direction: SignalDirection,
    *,
    session_start: datetime,
    evaluation_bar: OneMinuteBar | None = None,
) -> LocationQualification:
    policy = definition.location_policy
    if policy is None:
        return LocationQualification(
            status=LocationQualificationStatus.MISSING_EVIDENCE,
            is_degraded=True,
            reason_codes=("location_policy_unavailable",),
        )
    evaluation = bundle.feature(definition.evaluation_timeframe)
    if evaluation is None or evaluation.snapshot.as_of != bundle.evaluation_as_of:
        return LocationQualification(
            status=LocationQualificationStatus.MISSING_EVIDENCE,
            is_degraded=True,
            reason_codes=(
                f"missing_current_{definition.evaluation_timeframe.value}_location_clock",
            ),
        )
    if evaluation_bar is not None:
        if evaluation_bar.instrument_id != bundle.instrument_id:
            raise ValueError("location evaluation bar instrument must match bundle")
        if evaluation_bar.close_ts != bundle.evaluation_as_of:
            raise ValueError("location evaluation bar must close at evaluation time")
        if evaluation_bar.close != evaluation.snapshot.close:
            raise ValueError("location evaluation bar close must match analytical snapshot")
        if not evaluation_bar.is_complete or evaluation_bar.is_revision:
            raise ValueError("location evaluation requires a complete canonical bar")

    derivation = derive_location_zones(
        bundle,
        definition,
        direction,
        session_start=session_start,
    )
    policy_by_source = {item.source_kind: item for item in policy.sources}
    features_by_id = {item.feature_id: item for item in bundle.features}
    matches: list[SignalLocationMatch] = []
    reasons = list(derivation.reason_codes)
    degraded = derivation.is_degraded
    for zone in derivation.zones:
        source_feature = features_by_id[zone.source_feature_id]
        source_policy = policy_by_source[zone.source_kind]
        distance = (
            _distance_from_range_to_zone(evaluation_bar.low, evaluation_bar.high, zone)
            if evaluation_bar is not None
            else _distance_to_zone(evaluation.snapshot.close, zone)
        )
        tolerance = _tolerance(source_feature, source_policy)
        if tolerance is None:
            if distance > 0:
                degraded = True
                reasons.append(f"missing_{zone.timeframe.value}_{zone.source_kind.value}_atr")
                continue
            tolerance = Decimal("0")
        if distance > tolerance:
            continue
        matches.append(
            SignalLocationMatch(
                zone=zone,
                evaluation_feature_id=evaluation.feature_id,
                observed_ts=bundle.evaluation_as_of,
                observed_price=(
                    _range_match_price(evaluation_bar.low, evaluation_bar.high, zone)
                    if evaluation_bar is not None
                    else evaluation.snapshot.close
                ),
                distance=distance,
                tolerance=tolerance,
                fidelity=_combined_fidelity(
                    zone.fidelity,
                    _signal_fidelity(evaluation.snapshot.input_fidelity),
                ),
                reason_codes=(f"matched_{zone.timeframe.value}_{zone.zone_kind.value}",),
            )
        )

    matched_sources = {item.zone.source_kind for item in matches}
    if len(matched_sources) >= policy.minimum_distinct_sources:
        status = LocationQualificationStatus.QUALIFIED
        reasons.append("minimum_location_sources_met")
    elif matches:
        status = LocationQualificationStatus.INSUFFICIENT_CONFLUENCE
        reasons.append("minimum_location_sources_not_met")
    elif not derivation.available_source_kinds:
        status = LocationQualificationStatus.MISSING_EVIDENCE
        reasons.append("no_location_sources_available")
    else:
        status = LocationQualificationStatus.NOT_AT_LOCATION
        reasons.append("price_not_at_configured_location")

    return LocationQualification(
        status=status,
        matches=tuple(matches),
        is_degraded=degraded,
        reason_codes=tuple(dict.fromkeys(reasons)),
    )


def _zones_from_feature(
    feature: MarketContextFeatureSnapshot,
    source_kind: LocationSourceKind,
    direction: SignalDirection,
    session_start: datetime,
) -> tuple[tuple[SignalLocationZone, ...], bool]:
    snapshot = feature.snapshot
    fidelity = _signal_fidelity(snapshot.input_fidelity)
    if source_kind == LocationSourceKind.STRUCTURAL_LEVEL:
        level = (
            snapshot.nearest_support
            if direction == SignalDirection.LONG
            else snapshot.nearest_resistance
        )
        if level is None:
            return (), True
        kind = (
            SignalLocationZoneKind.SUPPORT
            if direction == SignalDirection.LONG
            else SignalLocationZoneKind.RESISTANCE
        )
        return (
            SignalLocationZone(
                instrument_id=snapshot.instrument_id,
                direction=direction,
                source_kind=source_kind,
                zone_kind=kind,
                timeframe=snapshot.timeframe,
                zone_anchor=(
                    f"structural:{level.kind.value}:{level.observed_ts.isoformat()}:"
                    f"{_decimal_text(level.price)}"
                ),
                source_feature_id=feature.feature_id,
                observed_ts=level.observed_ts,
                lower_price=level.price,
                upper_price=level.price,
                fidelity=fidelity,
                reason_codes=(f"{snapshot.timeframe.value}_{level.kind.value}",),
            ),
        ), True

    if source_kind == LocationSourceKind.FAIR_VALUE_GAP:
        expected = (
            FairValueGapDirection.BULLISH
            if direction == SignalDirection.LONG
            else FairValueGapDirection.BEARISH
        )
        kind = (
            SignalLocationZoneKind.BULLISH_FVG
            if direction == SignalDirection.LONG
            else SignalLocationZoneKind.BEARISH_FVG
        )
        return tuple(
            SignalLocationZone(
                instrument_id=snapshot.instrument_id,
                direction=direction,
                source_kind=source_kind,
                zone_kind=kind,
                timeframe=snapshot.timeframe,
                zone_anchor=(
                    f"fvg:{gap.direction.value}:{gap.detected_ts.isoformat()}:"
                    f"{_decimal_text(gap.lower)}:{_decimal_text(gap.upper)}"
                ),
                source_feature_id=feature.feature_id,
                observed_ts=gap.detected_ts,
                lower_price=gap.lower,
                upper_price=gap.upper,
                fidelity=fidelity,
                reason_codes=(f"active_{snapshot.timeframe.value}_{gap.direction.value}_fvg",),
            )
            for gap in snapshot.fair_value_gaps
            if gap.direction == expected
            and gap.timeframe == snapshot.timeframe
            and not gap.is_filled
        ), True

    if source_kind == LocationSourceKind.VALUE_AREA_EDGE:
        profile = snapshot.volume_profile
        if profile is None:
            return (), False
        price = (
            profile.value_area_low if direction == SignalDirection.LONG else profile.value_area_high
        )
        kind = (
            SignalLocationZoneKind.VALUE_AREA_LOW
            if direction == SignalDirection.LONG
            else SignalLocationZoneKind.VALUE_AREA_HIGH
        )
        return (
            SignalLocationZone(
                instrument_id=snapshot.instrument_id,
                direction=direction,
                source_kind=source_kind,
                zone_kind=kind,
                timeframe=snapshot.timeframe,
                zone_anchor=f"session:{session_start.isoformat()}:{kind.value}",
                source_feature_id=feature.feature_id,
                observed_ts=snapshot.as_of,
                lower_price=price,
                upper_price=price,
                fidelity=_signal_fidelity(profile.input_fidelity),
                reason_codes=(f"developing_session_{kind.value}",),
            ),
        ), True

    if snapshot.session_vwap is None:
        return (), False
    return (
        SignalLocationZone(
            instrument_id=snapshot.instrument_id,
            direction=direction,
            source_kind=source_kind,
            zone_kind=SignalLocationZoneKind.SESSION_VWAP,
            timeframe=snapshot.timeframe,
            zone_anchor=f"session:{session_start.isoformat()}:session_vwap",
            source_feature_id=feature.feature_id,
            observed_ts=snapshot.as_of,
            lower_price=snapshot.session_vwap,
            upper_price=snapshot.session_vwap,
            fidelity=fidelity,
            reason_codes=("developing_session_vwap",),
        ),
    ), True


def _distance_to_zone(price: Decimal, zone: SignalLocationZone) -> Decimal:
    if price < zone.lower_price:
        return zone.lower_price - price
    if price > zone.upper_price:
        return price - zone.upper_price
    return Decimal("0")


def _distance_from_range_to_zone(
    low: Decimal,
    high: Decimal,
    zone: SignalLocationZone,
) -> Decimal:
    if high < zone.lower_price:
        return zone.lower_price - high
    if low > zone.upper_price:
        return low - zone.upper_price
    return Decimal("0")


def _range_match_price(
    low: Decimal,
    high: Decimal,
    zone: SignalLocationZone,
) -> Decimal:
    if high < zone.lower_price:
        return high
    if low > zone.upper_price:
        return low
    return max(low, min(high, zone.lower_price))


def _tolerance(
    feature: MarketContextFeatureSnapshot,
    policy: LocationSourcePolicyConfig,
) -> Decimal | None:
    if policy.proximity_atr_fraction == 0:
        return Decimal("0")
    atr = feature.snapshot.atr_14
    if atr is None or atr <= 0:
        return None
    return atr * policy.proximity_atr_fraction


def _signal_fidelity(value: AnalyticsInputFidelity) -> SignalEvidenceFidelity:
    return {
        AnalyticsInputFidelity.REPORTED: SignalEvidenceFidelity.REPORTED,
        AnalyticsInputFidelity.INFERRED: SignalEvidenceFidelity.INFERRED,
        AnalyticsInputFidelity.MIXED: SignalEvidenceFidelity.PARTIAL,
    }[value]


def _combined_fidelity(
    zone: SignalEvidenceFidelity,
    evaluation: SignalEvidenceFidelity,
) -> SignalEvidenceFidelity:
    if zone == evaluation:
        return zone
    if SignalEvidenceFidelity.PARTIAL in {zone, evaluation}:
        return SignalEvidenceFidelity.PARTIAL
    return SignalEvidenceFidelity.PARTIAL


def _decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")
