from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from statistics import median

from pydantic import Field, field_validator, model_validator

from markeitech.domain.base import VersionedDomainModel, require_utc
from markeitech.domain.market_data import OneMinuteBar
from markeitech.signals.config import AggressionPolicyConfig
from markeitech.signals.contracts import (
    SignalDirection,
    SignalEvidenceFidelity,
    SignalEvidenceReference,
    SignalEvidenceStage,
    SignalEvidenceType,
    SignalSnapshot,
    SignalStatus,
)


class AggressionEvaluationStatus(StrEnum):
    COLLECTING = "collecting"
    OBSERVING = "observing"
    QUALIFIED = "qualified"
    EXPIRED = "expired"


class AggressionWindowSnapshot(VersionedDomainModel):
    signal_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    instrument_id: str = Field(min_length=1)
    direction: SignalDirection
    start_ts: datetime
    end_ts: datetime
    source: str = Field(min_length=1)
    fidelity: SignalEvidenceFidelity
    bar_identity_hashes: tuple[str, ...] = Field(min_length=1)
    total_volume: Decimal = Field(gt=0)
    classified_volume_ratio: Decimal = Field(ge=0, le=1)
    directional_delta_ratio: Decimal = Field(ge=-1, le=1)
    follow_through_atr_fraction: Decimal
    adverse_atr_fraction: Decimal = Field(ge=0)
    pace_ratio: Decimal | None = Field(default=None, ge=0)
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator("start_ts", "end_ts")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _window_must_be_consistent(self) -> AggressionWindowSnapshot:
        if self.end_ts <= self.start_ts:
            raise ValueError("aggression window end must follow start")
        if len(self.bar_identity_hashes) != len(set(self.bar_identity_hashes)):
            raise ValueError("aggression window bars must be unique")
        if self.fidelity == SignalEvidenceFidelity.UNAVAILABLE:
            raise ValueError("materialized aggression window cannot be unavailable")
        return self

    @property
    def window_id(self) -> str:
        return _canonical_hash(self.model_dump(mode="json"))


class AggressionEvaluation(VersionedDomainModel):
    status: AggressionEvaluationStatus
    evaluated_ts: datetime
    elapsed_observation_bars: int = Field(ge=0)
    window: AggressionWindowSnapshot | None = None
    evidence: tuple[SignalEvidenceReference, ...] = ()
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator("evaluated_ts")
    @classmethod
    def _timestamp_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _result_must_match_status(self) -> AggressionEvaluation:
        if self.status == AggressionEvaluationStatus.QUALIFIED:
            if self.window is None:
                raise ValueError("qualified aggression requires a materialized window")
            stages = {item.stage for item in self.evidence}
            if stages != {
                SignalEvidenceStage.AGGRESSION,
                SignalEvidenceStage.FOLLOW_THROUGH,
            }:
                raise ValueError("qualified aggression requires aggression and follow-through")
        elif self.status == AggressionEvaluationStatus.EXPIRED:
            stages = {item.stage for item in self.evidence}
            if stages != {
                SignalEvidenceStage.AGGRESSION,
                SignalEvidenceStage.FOLLOW_THROUGH,
            }:
                raise ValueError("expired aggression requires terminal observation evidence")
        elif self.evidence:
            raise ValueError("nonqualified aggression cannot append lifecycle evidence")
        return self


def evaluate_aggression_window(
    signal: SignalSnapshot,
    policy: AggressionPolicyConfig,
    bars: Sequence[OneMinuteBar],
    *,
    evaluated_ts: datetime,
    elapsed_observation_bars: int,
    atr_at_arm: Decimal,
    pace_baseline_bars: Sequence[OneMinuteBar] = (),
) -> AggressionEvaluation:
    evaluated_ts = require_utc(evaluated_ts)
    if signal.status != SignalStatus.ARMED:
        raise ValueError("aggression evaluation requires an Armed signal")
    if evaluated_ts < signal.updated_ts:
        raise ValueError("aggression evaluation cannot precede arming")
    if elapsed_observation_bars < 0:
        raise ValueError("elapsed aggression observations cannot be negative")
    if atr_at_arm <= 0:
        raise ValueError("aggression evaluation requires positive ATR at arm")

    eligible = _eligible_bars(signal, bars, evaluated_ts)
    contiguous = _latest_contiguous_bars(eligible)
    if len(contiguous) < policy.window_bars:
        return _nonqualified_result(
            signal,
            policy,
            evaluated_ts,
            elapsed_observation_bars,
            "classified_tick_window_incomplete",
        )

    selected = contiguous[-policy.window_bars :]
    window = _build_window(
        signal,
        selected,
        atr_at_arm=atr_at_arm,
        pace_baseline_bars=pace_baseline_bars,
        policy=policy,
    )
    failures = _qualification_failures(window, policy)
    if failures:
        expired = elapsed_observation_bars >= policy.expiry_observation_bars
        return AggressionEvaluation(
            status=(
                AggressionEvaluationStatus.EXPIRED
                if expired
                else AggressionEvaluationStatus.OBSERVING
            ),
            evaluated_ts=evaluated_ts,
            elapsed_observation_bars=elapsed_observation_bars,
            window=window,
            evidence=_terminal_evidence(window, failures) if expired else (),
            reason_codes=failures,
        )

    return AggressionEvaluation(
        status=AggressionEvaluationStatus.QUALIFIED,
        evaluated_ts=evaluated_ts,
        elapsed_observation_bars=elapsed_observation_bars,
        window=window,
        evidence=_qualified_evidence(window),
        reason_codes=("aggression_and_follow_through_confirmed",),
    )


def _eligible_bars(
    signal: SignalSnapshot,
    bars: Sequence[OneMinuteBar],
    evaluated_ts: datetime,
) -> tuple[OneMinuteBar, ...]:
    eligible = [
        bar
        for bar in bars
        if bar.instrument_id == signal.instrument_id
        and bar.source == "classified_ticks"
        and bar.is_complete
        and not bar.is_revision
        and bar.open_ts >= signal.updated_ts
        and bar.close_ts <= evaluated_ts
    ]
    eligible.sort(key=lambda bar: (bar.open_ts, bar.close_ts, bar.dedupe_key))
    if len({bar.open_ts for bar in eligible}) != len(eligible):
        raise ValueError("aggression bars cannot conflict at one observation time")
    return tuple(eligible)


def _latest_contiguous_bars(bars: Sequence[OneMinuteBar]) -> tuple[OneMinuteBar, ...]:
    if not bars:
        return ()
    start = len(bars) - 1
    while start > 0 and bars[start - 1].close_ts == bars[start].open_ts:
        start -= 1
    return tuple(bars[start:])


def _build_window(
    signal: SignalSnapshot,
    bars: Sequence[OneMinuteBar],
    *,
    atr_at_arm: Decimal,
    pace_baseline_bars: Sequence[OneMinuteBar],
    policy: AggressionPolicyConfig,
) -> AggressionWindowSnapshot:
    total_volume = sum((bar.volume for bar in bars), Decimal("0"))
    if total_volume <= 0:
        raise ValueError("aggression window requires positive traded volume")
    classified_volume = sum(
        (bar.buy_volume + bar.sell_volume for bar in bars),
        Decimal("0"),
    )
    signed_delta = sum((bar.delta for bar in bars), Decimal("0"))
    direction_multiplier = (
        Decimal("1") if signal.direction == SignalDirection.LONG else Decimal("-1")
    )
    directional_delta = signed_delta * direction_multiplier
    anchor_price = _arm_price(signal)
    final_price = bars[-1].close
    directional_progress = (final_price - anchor_price) * direction_multiplier
    adverse_price = (
        max(Decimal("0"), anchor_price - min(bar.low for bar in bars))
        if signal.direction == SignalDirection.LONG
        else max(Decimal("0"), max(bar.high for bar in bars) - anchor_price)
    )
    pace_ratio = _pace_ratio(bars, pace_baseline_bars, policy)
    classified_ratio = classified_volume / total_volume
    fidelity = (
        SignalEvidenceFidelity.INFERRED
        if classified_ratio == Decimal("1")
        else SignalEvidenceFidelity.PARTIAL
    )
    return AggressionWindowSnapshot(
        signal_id=signal.signal_id,
        instrument_id=signal.instrument_id,
        direction=signal.direction,
        start_ts=bars[0].open_ts,
        end_ts=bars[-1].close_ts,
        source="classified_ticks",
        fidelity=fidelity,
        bar_identity_hashes=tuple(_canonical_hash(bar.dedupe_key) for bar in bars),
        total_volume=total_volume,
        classified_volume_ratio=classified_ratio,
        directional_delta_ratio=(
            directional_delta / classified_volume if classified_volume > 0 else Decimal("0")
        ),
        follow_through_atr_fraction=directional_progress / atr_at_arm,
        adverse_atr_fraction=adverse_price / atr_at_arm,
        pace_ratio=pace_ratio,
        reason_codes=(
            "quote_test_classified_trade_window",
            "price_follow_through_measured",
            *(() if pace_ratio is not None else ("pace_baseline_unavailable",)),
            "quote_response_unavailable",
        ),
    )


def _arm_price(signal: SignalSnapshot) -> Decimal:
    latest = max(signal.location_matches, key=lambda item: item.observed_ts)
    return latest.observed_price


def _pace_ratio(
    bars: Sequence[OneMinuteBar],
    baseline: Sequence[OneMinuteBar],
    policy: AggressionPolicyConfig,
) -> Decimal | None:
    usable = [
        bar.volume
        for bar in baseline
        if bar.instrument_id == bars[0].instrument_id
        and bar.is_complete
        and not bar.is_revision
        and bar.close_ts <= bars[0].open_ts
        and bar.volume > 0
    ]
    if len(usable) < policy.minimum_pace_baseline_bars:
        return None
    baseline_volume = Decimal(median(usable[-policy.minimum_pace_baseline_bars :]))
    if baseline_volume <= 0:
        return None
    observed = sum((bar.volume for bar in bars), Decimal("0")) / Decimal(len(bars))
    return observed / baseline_volume


def _qualification_failures(
    window: AggressionWindowSnapshot,
    policy: AggressionPolicyConfig,
) -> tuple[str, ...]:
    failures = []
    if window.classified_volume_ratio < policy.minimum_classified_volume_ratio:
        failures.append("classified_volume_below_threshold")
    if window.directional_delta_ratio < policy.minimum_directional_delta_ratio:
        failures.append("directional_delta_below_threshold")
    if window.follow_through_atr_fraction < policy.minimum_follow_through_atr_fraction:
        failures.append("follow_through_below_threshold")
    if window.adverse_atr_fraction > policy.maximum_adverse_atr_fraction:
        failures.append("adverse_excursion_above_threshold")
    if policy.minimum_pace_ratio is not None:
        if window.pace_ratio is None:
            failures.append("pace_baseline_unavailable")
        elif window.pace_ratio < policy.minimum_pace_ratio:
            failures.append("pace_below_threshold")
    return tuple(failures)


def _qualified_evidence(
    window: AggressionWindowSnapshot,
) -> tuple[SignalEvidenceReference, SignalEvidenceReference]:
    common = {
        "instrument_id": window.instrument_id,
        "evidence_type": SignalEvidenceType.MARKET_DATA_WINDOW,
        "evidence_id": window.window_id,
        "observed_ts": window.end_ts,
        "source": window.source,
        "fidelity": window.fidelity,
    }
    return (
        SignalEvidenceReference(
            **common,
            stage=SignalEvidenceStage.AGGRESSION,
            reason_codes=(
                "directional_classified_volume_confirmed",
                "quote_response_unavailable",
            ),
        ),
        SignalEvidenceReference(
            **common,
            stage=SignalEvidenceStage.FOLLOW_THROUGH,
            reason_codes=("directional_price_follow_through_confirmed",),
        ),
    )


def _terminal_evidence(
    window: AggressionWindowSnapshot,
    reasons: tuple[str, ...],
) -> tuple[SignalEvidenceReference, SignalEvidenceReference]:
    return tuple(
        SignalEvidenceReference(
            instrument_id=window.instrument_id,
            stage=stage,
            evidence_type=SignalEvidenceType.MARKET_DATA_WINDOW,
            evidence_id=window.window_id,
            observed_ts=window.end_ts,
            source=window.source,
            fidelity=window.fidelity,
            reason_codes=reasons,
        )
        for stage in (
            SignalEvidenceStage.AGGRESSION,
            SignalEvidenceStage.FOLLOW_THROUGH,
        )
    )


def _nonqualified_result(
    signal: SignalSnapshot,
    policy: AggressionPolicyConfig,
    evaluated_ts: datetime,
    elapsed_observation_bars: int,
    reason: str,
) -> AggressionEvaluation:
    expired = elapsed_observation_bars >= policy.expiry_observation_bars
    reasons = (
        reason,
        *(("armed_observation_window_expired",) if expired else ()),
    )
    return AggressionEvaluation(
        status=(
            AggressionEvaluationStatus.EXPIRED if expired else AggressionEvaluationStatus.COLLECTING
        ),
        evaluated_ts=evaluated_ts,
        elapsed_observation_bars=elapsed_observation_bars,
        evidence=(
            _unavailable_terminal_evidence(
                signal,
                evaluated_ts,
                elapsed_observation_bars,
                reasons,
            )
            if expired
            else ()
        ),
        reason_codes=reasons,
    )


def _unavailable_terminal_evidence(
    signal: SignalSnapshot,
    evaluated_ts: datetime,
    elapsed_observation_bars: int,
    reasons: tuple[str, ...],
) -> tuple[SignalEvidenceReference, SignalEvidenceReference]:
    evidence_id = _canonical_hash(
        {
            "signal_id": signal.signal_id,
            "armed_ts": signal.updated_ts.isoformat(),
            "evaluated_ts": evaluated_ts.isoformat(),
            "elapsed_observation_bars": elapsed_observation_bars,
            "source": "classified_ticks",
            "reason_codes": reasons,
        }
    )
    terminal_reasons = (*reasons, "quote_response_unavailable")
    return tuple(
        SignalEvidenceReference(
            instrument_id=signal.instrument_id,
            stage=stage,
            evidence_type=SignalEvidenceType.MARKET_DATA_WINDOW,
            evidence_id=evidence_id,
            observed_ts=evaluated_ts,
            source="classified_ticks",
            fidelity=SignalEvidenceFidelity.UNAVAILABLE,
            reason_codes=terminal_reasons,
        )
        for stage in (
            SignalEvidenceStage.AGGRESSION,
            SignalEvidenceStage.FOLLOW_THROUGH,
        )
    )


def _canonical_hash(value: object) -> str:
    encoded = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()
