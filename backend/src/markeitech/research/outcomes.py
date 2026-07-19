from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from statistics import median
from typing import Protocol

from pydantic import Field, field_validator, model_validator

from markeitech.domain.base import VersionedDomainModel, require_utc
from markeitech.domain.market_data import OneMinuteBar
from markeitech.persistence import RecoveryPlanningError
from markeitech.signals import (
    SignalDirection,
    SignalEvidenceReference,
    SignalEvidenceType,
    SignalLocationMatch,
    SignalSnapshot,
    SignalStatus,
    SignalTransitionEvent,
)

DEFAULT_HORIZONS_MINUTES = (1, 3, 5, 15, 30)
_MINUTE = timedelta(minutes=1)
_ROLE_SOURCE = "audit_configuration_not_point_in_time"


class AuditSessionCalendar(Protocol):
    def expected_minute_opens(
        self,
        instrument_id: str,
        start_ts: datetime,
        end_ts: datetime,
    ) -> tuple[datetime, ...]: ...

    def session_window(
        self,
        instrument_id: str,
        timestamp: datetime,
    ) -> tuple[datetime, datetime]: ...


class AuditEventKind(StrEnum):
    ARMED = "armed"
    TRIGGERED = "triggered"


class HorizonOutcomeStatus(StrEnum):
    COMPLETE = "complete"
    UNAVAILABLE = "unavailable"


class SignalOutcomeHorizon(VersionedDomainModel):
    horizon_minutes: int = Field(gt=0)
    status: HorizonOutcomeStatus
    expected_end_ts: datetime
    observed_bar_count: int = Field(ge=0)
    close_price: Decimal | None = Field(default=None, gt=0)
    directional_return_points: Decimal | None = None
    directional_return_bps: Decimal | None = None
    directional_return_atr: Decimal | None = None
    maximum_favorable_excursion_points: Decimal | None = Field(default=None, ge=0)
    maximum_adverse_excursion_points: Decimal | None = Field(default=None, ge=0)
    maximum_favorable_excursion_atr: Decimal | None = Field(default=None, ge=0)
    maximum_adverse_excursion_atr: Decimal | None = Field(default=None, ge=0)
    favorable_extreme_ts: datetime | None = None
    adverse_extreme_ts: datetime | None = None
    reason_codes: tuple[str, ...] = ()

    @field_validator("expected_end_ts", "favorable_extreme_ts", "adverse_extreme_ts")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @model_validator(mode="after")
    def _status_must_match_metrics(self) -> SignalOutcomeHorizon:
        metrics = (
            self.close_price,
            self.directional_return_points,
            self.directional_return_bps,
            self.maximum_favorable_excursion_points,
            self.maximum_adverse_excursion_points,
            self.favorable_extreme_ts,
            self.adverse_extreme_ts,
        )
        if self.status == HorizonOutcomeStatus.COMPLETE:
            if any(value is None for value in metrics):
                raise ValueError("complete horizon requires price and excursion metrics")
            if self.reason_codes:
                raise ValueError("complete horizon cannot carry unavailable reasons")
        elif any(value is not None for value in metrics):
            raise ValueError("unavailable horizon cannot carry outcome metrics")
        elif not self.reason_codes:
            raise ValueError("unavailable horizon requires a reason")
        return self


class ForwardPriceResponse(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    direction: SignalDirection
    event_ts: datetime
    reference_price: Decimal | None = Field(default=None, gt=0)
    reference_ts: datetime | None = None
    reference_source: str = "ib:latest_completed_one_minute_close_at_or_before_event"
    atr_at_event: Decimal | None = Field(default=None, gt=0)
    horizons: tuple[SignalOutcomeHorizon, ...] = Field(min_length=1)
    reason_codes: tuple[str, ...] = ()

    @field_validator("event_ts", "reference_ts")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @model_validator(mode="after")
    def _reference_fields_must_coexist(self) -> ForwardPriceResponse:
        if (self.reference_price is None) != (self.reference_ts is None):
            raise ValueError("forward response reference price and timestamp must coexist")
        if self.reference_ts is not None and self.reference_ts > self.event_ts:
            raise ValueError("forward response reference cannot use future data")
        if (
            self.reference_price is None
            and "event_reference_bar_unavailable" not in self.reason_codes
        ):
            raise ValueError("missing forward response reference requires a reason")
        return self


class AuditedLocation(VersionedDomainModel):
    zone_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_kind: str = Field(min_length=1)
    zone_kind: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    lower_price: Decimal = Field(gt=0)
    upper_price: Decimal = Field(gt=0)
    observed_price: Decimal = Field(gt=0)
    observed_ts: datetime
    fidelity: str = Field(min_length=1)

    @field_validator("observed_ts")
    @classmethod
    def _timestamp_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)


class SignalOutcomeRecord(VersionedDomainModel):
    signal_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    transition_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_kind: AuditEventKind
    event_ts: datetime
    instrument_id: str = Field(min_length=1)
    instrument_role: str = Field(pattern=r"^(active|background|unknown)$")
    instrument_role_source: str = Field(min_length=1)
    definition_id: str = Field(min_length=1)
    algorithm_version: str = Field(min_length=1)
    configuration_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    direction: SignalDirection
    event_reference_price: Decimal | None = Field(default=None, gt=0)
    event_reference_ts: datetime | None = None
    event_reference_source: str = "ib:latest_completed_one_minute_close_at_or_before_event"
    atr_at_arm: Decimal | None = Field(default=None, gt=0)
    created_ts: datetime
    armed_ts: datetime
    triggered_ts: datetime | None = None
    terminal_status: SignalStatus | None = None
    terminal_ts: datetime | None = None
    replacement_signal_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    candidate_to_arm_seconds: Decimal = Field(ge=0)
    arm_to_trigger_seconds: Decimal | None = Field(default=None, ge=0)
    event_to_terminal_seconds: Decimal | None = Field(default=None, ge=0)
    event_reason_codes: tuple[str, ...] = Field(min_length=1)
    terminal_reason_codes: tuple[str, ...] = ()
    feature_ids: tuple[str, ...] = ()
    locations: tuple[AuditedLocation, ...] = Field(min_length=1)
    evidence: tuple[SignalEvidenceReference, ...] = Field(min_length=1)
    horizons: tuple[SignalOutcomeHorizon, ...] = Field(min_length=1)
    reason_codes: tuple[str, ...] = ()

    @field_validator(
        "event_ts",
        "event_reference_ts",
        "created_ts",
        "armed_ts",
        "triggered_ts",
        "terminal_ts",
    )
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @model_validator(mode="after")
    def _timeline_must_be_consistent(self) -> SignalOutcomeRecord:
        if self.created_ts > self.armed_ts or self.armed_ts > self.event_ts:
            raise ValueError("audit lifecycle timestamps are out of order")
        if self.event_kind == AuditEventKind.ARMED and self.event_ts != self.armed_ts:
            raise ValueError("Armed audit event must occur at armed timestamp")
        if self.event_kind == AuditEventKind.TRIGGERED:
            if self.triggered_ts is None or self.event_ts != self.triggered_ts:
                raise ValueError("Triggered audit event requires trigger timestamp")
        if (self.event_reference_price is None) != (self.event_reference_ts is None):
            raise ValueError("event reference price and timestamp must coexist")
        if self.event_reference_ts is not None and self.event_reference_ts > self.event_ts:
            raise ValueError("event reference cannot use future data")
        if self.terminal_status is None:
            if self.terminal_ts is not None or self.terminal_reason_codes:
                raise ValueError("nonterminal audit record cannot carry terminal detail")
        elif self.terminal_status not in {SignalStatus.INVALIDATED, SignalStatus.EXPIRED}:
            raise ValueError("audit terminal status must end the signal lifecycle")
        elif self.terminal_ts is None or self.terminal_ts < self.event_ts:
            raise ValueError("audit terminal timestamp cannot precede event")
        return self


@dataclass(frozen=True)
class SignalAuditHistory:
    current: SignalSnapshot
    transitions: tuple[SignalTransitionEvent, ...]


def measure_forward_price_response(
    instrument_id: str,
    direction: SignalDirection,
    event_ts: datetime,
    bars: Sequence[OneMinuteBar],
    *,
    calendar: AuditSessionCalendar,
    atr: Decimal | None = None,
    horizons_minutes: Sequence[int] = DEFAULT_HORIZONS_MINUTES,
) -> ForwardPriceResponse:
    event_ts = require_utc(event_ts)
    horizons = tuple(sorted(horizons_minutes))
    if not horizons or any(value <= 0 for value in horizons):
        raise ValueError("forward response horizons must be positive")
    if len(horizons) != len(set(horizons)):
        raise ValueError("forward response horizons must be unique")
    bar_index = _reported_bar_index(bars)
    session = _session_window(calendar, instrument_id, event_ts)
    reference = _event_reference(bar_index, event_ts, session)
    reference_price = None if reference is None else reference.close
    reference_ts = None if reference is None else reference.close_ts
    reasons = () if reference is not None else ("event_reference_bar_unavailable",)
    return ForwardPriceResponse(
        instrument_id=instrument_id,
        direction=direction,
        event_ts=event_ts,
        reference_price=reference_price,
        reference_ts=reference_ts,
        atr_at_event=atr,
        horizons=tuple(
            _horizon_outcome(
                instrument_id,
                direction,
                event_ts,
                reference_price,
                atr,
                bar_index,
                calendar,
                session,
                horizon,
            )
            for horizon in horizons
        ),
        reason_codes=reasons,
    )


def audit_signal_outcomes(
    histories: Sequence[SignalAuditHistory],
    bars_by_instrument: Mapping[str, Sequence[OneMinuteBar]],
    *,
    calendar: AuditSessionCalendar,
    role_by_instrument: Mapping[str, str],
    available_feature_ids: frozenset[str] | None,
    start_ts: datetime,
    end_ts: datetime,
    horizons_minutes: Sequence[int] = DEFAULT_HORIZONS_MINUTES,
) -> tuple[SignalOutcomeRecord, ...]:
    start_ts = require_utc(start_ts)
    end_ts = require_utc(end_ts)
    if end_ts <= start_ts:
        raise ValueError("audit end must follow start")
    horizons = tuple(sorted(horizons_minutes))
    if not horizons or any(value <= 0 for value in horizons):
        raise ValueError("audit horizons must be positive")
    if len(horizons) != len(set(horizons)):
        raise ValueError("audit horizons must be unique")

    reported = {
        instrument_id: _reported_bar_index(values)
        for instrument_id, values in bars_by_instrument.items()
    }
    armed_events = tuple(
        event
        for history in histories
        for event in history.transitions
        if event.to_status == SignalStatus.ARMED
    )
    replacement_index = _replacement_index(histories, armed_events)
    records: list[SignalOutcomeRecord] = []
    for history in histories:
        _validate_history(history)
        transitions = tuple(sorted(history.transitions, key=lambda item: item.occurred_ts))
        armed = next(
            (event for event in transitions if event.to_status == SignalStatus.ARMED),
            None,
        )
        if armed is None:
            continue
        triggered = next(
            (event for event in transitions if event.to_status == SignalStatus.TRIGGERED),
            None,
        )
        terminal = next(
            (
                event
                for event in transitions
                if event.to_status in {SignalStatus.INVALIDATED, SignalStatus.EXPIRED}
            ),
            None,
        )
        for event, kind in ((armed, AuditEventKind.ARMED), (triggered, AuditEventKind.TRIGGERED)):
            if event is None or not start_ts <= event.occurred_ts < end_ts:
                continue
            feature_ids = event.current.feature_ids
            _verify_feature_evidence(event, feature_ids, available_feature_ids)
            bar_index = reported.get(event.current.instrument_id, {})
            session = _session_window(calendar, event.current.instrument_id, event.occurred_ts)
            reference = _event_reference(bar_index, event.occurred_ts, session)
            reference_price = None if reference is None else reference.close
            reference_ts = None if reference is None else reference.close_ts
            atr = (
                None
                if armed.current.confirmation_context is None
                else armed.current.confirmation_context.atr_at_arm
            )
            reasons = () if reference is not None else ("event_reference_bar_unavailable",)
            records.append(
                SignalOutcomeRecord(
                    signal_id=event.signal_id,
                    transition_id=event.transition_id,
                    event_kind=kind,
                    event_ts=event.occurred_ts,
                    instrument_id=event.current.instrument_id,
                    instrument_role=role_by_instrument.get(event.current.instrument_id, "unknown"),
                    instrument_role_source=_ROLE_SOURCE,
                    definition_id=event.current.definition_id,
                    algorithm_version=event.current.algorithm_version,
                    configuration_hash=event.current.configuration_hash,
                    direction=event.current.direction,
                    event_reference_price=reference_price,
                    event_reference_ts=reference_ts,
                    atr_at_arm=atr,
                    created_ts=event.current.created_ts,
                    armed_ts=armed.occurred_ts,
                    triggered_ts=None if triggered is None else triggered.occurred_ts,
                    terminal_status=None if terminal is None else terminal.to_status,
                    terminal_ts=None if terminal is None else terminal.occurred_ts,
                    replacement_signal_id=(
                        None if terminal is None else replacement_index.get(terminal.transition_id)
                    ),
                    candidate_to_arm_seconds=_seconds(armed.occurred_ts - event.current.created_ts),
                    arm_to_trigger_seconds=(
                        None
                        if triggered is None
                        else _seconds(triggered.occurred_ts - armed.occurred_ts)
                    ),
                    event_to_terminal_seconds=(
                        None
                        if terminal is None
                        else _seconds(terminal.occurred_ts - event.occurred_ts)
                    ),
                    event_reason_codes=event.reason_codes,
                    terminal_reason_codes=() if terminal is None else terminal.reason_codes,
                    feature_ids=feature_ids,
                    locations=tuple(
                        _audited_location(item) for item in event.current.location_matches
                    ),
                    evidence=event.current.evidence,
                    horizons=tuple(
                        _horizon_outcome(
                            event.current.instrument_id,
                            event.current.direction,
                            event.occurred_ts,
                            reference_price,
                            atr,
                            bar_index,
                            calendar,
                            session,
                            horizon,
                        )
                        for horizon in horizons
                    ),
                    reason_codes=reasons,
                )
            )
    return tuple(sorted(records, key=lambda item: (item.event_ts, item.transition_id)))


def render_signal_outcome_report(
    records: Sequence[SignalOutcomeRecord],
    *,
    start_ts: datetime,
    end_ts: datetime,
) -> str:
    start_ts = require_utc(start_ts)
    end_ts = require_utc(end_ts)
    armed = tuple(item for item in records if item.event_kind == AuditEventKind.ARMED)
    triggered = tuple(item for item in records if item.event_kind == AuditEventKind.TRIGGERED)
    terminal_counts = Counter(
        "open" if item.terminal_status is None else item.terminal_status.value for item in armed
    )
    terminal_reasons = Counter(reason for item in armed for reason in item.terminal_reason_codes)
    unavailable_reasons = Counter(
        reason
        for item in records
        for outcome in item.horizons
        if outcome.status == HorizonOutcomeStatus.UNAVAILABLE
        for reason in outcome.reason_codes
    )
    horizons = sorted({value.horizon_minutes for item in records for value in item.horizons})
    lines = [
        "# Signal Outcome Audit",
        "",
        f"Window: `{start_ts.isoformat()}` to `{end_ts.isoformat()}`",
        "",
        "Method: verified SQLite lifecycle histories, exact committed feature identities, "
        "completed reported IB one-minute bars, and configured market-session minutes. "
        "Armed and Triggered observations remain separate.",
        "",
        "## Funnel",
        "",
        f"- Armed observations: {len(armed)}",
        f"- Triggered observations: {len(triggered)}",
        f"- Active Armed: {sum(item.instrument_role == 'active' for item in armed)}",
        f"- Background Armed: {sum(item.instrument_role == 'background' for item in armed)}",
        f"- Terminal states: {_counter_text(terminal_counts)}",
        f"- Replacement churn: "
        f"{sum('location_episode_replaced' in item.terminal_reason_codes for item in armed)}",
        "",
        "## Lifecycle Timing",
        "",
        f"- Median Candidate to Armed: {_median_record_metric(armed, 'candidate_to_arm_seconds')}s",
        f"- Median Armed to Triggered: "
        f"{_median_record_metric(triggered, 'arm_to_trigger_seconds')}s",
        f"- Median event to terminal: "
        f"{_median_record_metric(records, 'event_to_terminal_seconds')}s",
        "",
        "## Forward Outcomes",
        "",
        "| Event | Horizon | Complete | Favorable Close | Median Return ATR "
        "| Median MFE ATR | Median MAE ATR |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for event_kind in AuditEventKind:
        population = tuple(item for item in records if item.event_kind == event_kind)
        for horizon in horizons:
            outcomes = tuple(
                value
                for item in population
                for value in item.horizons
                if value.horizon_minutes == horizon
                and value.status == HorizonOutcomeStatus.COMPLETE
            )
            favorable = sum(
                value.directional_return_points is not None
                and value.directional_return_points > 0
                for value in outcomes
            )
            lines.append(
                f"| {event_kind.value.title()} | {horizon}m | {len(outcomes)}/{len(population)} "
                f"| {_percentage(favorable, len(outcomes))} "
                f"| {_median_metric(outcomes, 'directional_return_atr')} "
                f"| {_median_metric(outcomes, 'maximum_favorable_excursion_atr')} "
                f"| {_median_metric(outcomes, 'maximum_adverse_excursion_atr')} |"
            )
    comparison_horizon = 5 if 5 in horizons else (horizons[0] if horizons else None)
    lines.extend(
        [
            "",
            "## Active And Background Comparison",
            "",
            "| Role | Armed | Complete | Favorable Close | Median Return ATR |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    if comparison_horizon is not None:
        for role in ("active", "background", "unknown"):
            population = tuple(item for item in armed if item.instrument_role == role)
            if not population:
                continue
            outcomes = tuple(
                outcome
                for item in population
                for outcome in item.horizons
                if outcome.horizon_minutes == comparison_horizon
                and outcome.status == HorizonOutcomeStatus.COMPLETE
            )
            favorable = sum(
                outcome.directional_return_points is not None
                and outcome.directional_return_points > 0
                for outcome in outcomes
            )
            lines.append(
                f"| {role.title()} ({comparison_horizon}m) | {len(population)} "
                f"| {len(outcomes)}/{len(population)} "
                f"| {_percentage(favorable, len(outcomes))} "
                f"| {_median_metric(outcomes, 'directional_return_atr')} |"
            )
    lines.extend(
        [
            "",
            "## Terminal Reasons",
            "",
            *(
                [f"- `{reason}`: {count}" for reason, count in terminal_reasons.most_common()]
                or ["- None"]
            ),
            "",
            "## Unavailable Outcomes",
            "",
            *(
                [f"- `{reason}`: {count}" for reason, count in unavailable_reasons.most_common()]
                or ["- None"]
            ),
            "",
            "## Event Detail",
            "",
            "| Time | Role | Instrument | Event | Direction | Location | Terminal | Outcome |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for item in records:
        display = next(
            (value for value in item.horizons if value.horizon_minutes == 5),
            item.horizons[0],
        )
        location = ", ".join(
            f"{value.timeframe} {value.zone_kind} {value.lower_price}-{value.upper_price}"
            for value in item.locations
        )
        terminal = "Open" if item.terminal_status is None else item.terminal_status.value.title()
        outcome = (
            "/".join(display.reason_codes)
            if display.status == HorizonOutcomeStatus.UNAVAILABLE
            else (
                f"{display.horizon_minutes}m "
                f"return={_decimal_text(display.directional_return_atr)} "
                f"MFE/MAE={_decimal_text(display.maximum_favorable_excursion_atr)}/"
                f"{_decimal_text(display.maximum_adverse_excursion_atr)} ATR"
            )
        )
        lines.append(
            f"| {item.event_ts.isoformat()} | {item.instrument_role.title()} "
            f"| {item.instrument_id} | {item.event_kind.value.title()} "
            f"| {item.direction.value.title()} | {location} | {terminal} | {outcome} |"
        )
    lines.extend(
        [
            "",
            "## Integrity Notes",
            "",
            f"- Events missing a valid reported reference bar: "
            f"{sum(item.event_reference_price is None for item in records)}",
            "- Instrument role comes from the supplied audit configuration; it is not claimed "
            "as durable point-in-time evidence.",
            "- Missing, conflicting, cross-session, or broken forward windows are never filled "
            "or inferred.",
            "- Positive returns and excursions are direction-adjusted; no outcome changes the "
            "original lifecycle classification.",
            "",
        ]
    )
    return "\n".join(lines)


def write_signal_outcome_artifacts(
    records: Sequence[SignalOutcomeRecord],
    *,
    report: str,
    output_directory: Path,
) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    dataset_path = output_directory / "signal-outcomes.jsonl"
    report_path = output_directory / "signal-outcomes.md"
    dataset = "".join(
        json.dumps(item.model_dump(mode="json"), separators=(",", ":"), sort_keys=True) + "\n"
        for item in records
    )
    dataset_path.write_text(dataset, encoding="utf-8")
    report_path.write_text(report, encoding="utf-8")
    return dataset_path, report_path


def _reported_bar_index(bars: Sequence[OneMinuteBar]) -> dict[datetime, OneMinuteBar]:
    grouped: dict[datetime, list[OneMinuteBar]] = {}
    for bar in bars:
        if bar.source != "ib" or not bar.is_complete:
            continue
        grouped.setdefault(bar.open_ts, []).append(bar)
    values: dict[datetime, OneMinuteBar] = {}
    for open_ts, revisions in sorted(grouped.items()):
        signatures = {_market_bar_signature(item) for item in revisions}
        if len(signatures) != 1:
            raise ValueError(f"conflicting reported bar revisions at {open_ts.isoformat()}")
        values[open_ts] = max(revisions, key=lambda item: (item.is_revision, item.ts_init))
    return values


def _validate_history(history: SignalAuditHistory) -> None:
    transitions = tuple(sorted(history.transitions, key=lambda item: item.occurred_ts))
    transition_ids = [item.transition_id for item in transitions]
    if len(transition_ids) != len(set(transition_ids)):
        raise ValueError(f"duplicate transition in signal history {history.current.signal_id}")
    if any(item.signal_id != history.current.signal_id for item in transitions):
        raise ValueError(f"mixed signal identities in history {history.current.signal_id}")
    for previous, current in zip(transitions, transitions[1:], strict=False):
        if current.from_status != previous.to_status:
            raise ValueError(f"broken status chain in signal history {history.current.signal_id}")
        if current.previous_content_hash != previous.current.content_hash:
            raise ValueError(f"broken content chain in signal history {history.current.signal_id}")
    if transitions and transitions[-1].current != history.current:
        raise ValueError(
            "current signal does not match transition history "
            f"{history.current.signal_id}"
        )


def _market_bar_signature(bar: OneMinuteBar) -> tuple[object, ...]:
    return (
        bar.instrument_id,
        bar.open_ts,
        bar.close_ts,
        bar.open,
        bar.high,
        bar.low,
        bar.close,
        bar.volume,
        bar.buy_volume,
        bar.sell_volume,
        bar.unknown_volume,
        bar.source,
        bar.is_complete,
    )


def _verify_feature_evidence(
    event: SignalTransitionEvent,
    feature_ids: tuple[str, ...],
    available_feature_ids: frozenset[str] | None,
) -> None:
    evidence_ids = {
        item.evidence_id
        for item in event.current.evidence
        if item.evidence_type == SignalEvidenceType.MARKET_CONTEXT_FEATURE
    }
    location_ids = {
        feature_id
        for match in event.current.location_matches
        for feature_id in (match.zone.source_feature_id, match.evaluation_feature_id)
    }
    required = evidence_ids | location_ids
    if required != set(feature_ids):
        raise ValueError(f"signal {event.signal_id} has inconsistent feature references")
    if available_feature_ids is not None:
        missing = sorted(required - available_feature_ids)
        if missing:
            raise ValueError(
                f"signal {event.signal_id} references unavailable committed features: "
                + ", ".join(missing)
            )


def _replacement_index(
    histories: Sequence[SignalAuditHistory],
    armed_events: Sequence[SignalTransitionEvent],
) -> dict[str, str]:
    armed_by_key: dict[tuple[str, str, datetime], list[str]] = {}
    for event in armed_events:
        key = (event.current.instrument_id, event.current.definition_id, event.occurred_ts)
        armed_by_key.setdefault(key, []).append(event.signal_id)
    replacements: dict[str, str] = {}
    for history in histories:
        for event in history.transitions:
            if "location_episode_replaced" not in event.reason_codes:
                continue
            key = (event.current.instrument_id, event.current.definition_id, event.occurred_ts)
            candidates = sorted(
                signal_id for signal_id in armed_by_key.get(key, ()) if signal_id != event.signal_id
            )
            if len(candidates) > 1:
                raise ValueError(f"ambiguous replacement for signal {event.signal_id}")
            if candidates:
                replacements[event.transition_id] = candidates[0]
    return replacements


def _session_window(
    calendar: AuditSessionCalendar,
    instrument_id: str,
    event_ts: datetime,
) -> tuple[datetime, datetime] | None:
    try:
        return calendar.session_window(instrument_id, event_ts)
    except (RecoveryPlanningError, ValueError):
        return None


def _event_reference(
    bars: Mapping[datetime, OneMinuteBar],
    event_ts: datetime,
    session: tuple[datetime, datetime] | None,
) -> OneMinuteBar | None:
    if session is None:
        return None
    session_open, _ = session
    eligible = tuple(
        bar for bar in bars.values() if session_open <= bar.open_ts and bar.close_ts <= event_ts
    )
    if not eligible:
        return None
    reference = max(eligible, key=lambda item: item.close_ts)
    if event_ts - reference.close_ts > _MINUTE:
        return None
    return reference


def _audited_location(match: SignalLocationMatch) -> AuditedLocation:
    zone = match.zone
    return AuditedLocation(
        zone_id=zone.zone_id,
        source_kind=zone.source_kind.value,
        zone_kind=zone.zone_kind.value,
        timeframe=zone.timeframe.value,
        lower_price=zone.lower_price,
        upper_price=zone.upper_price,
        observed_price=match.observed_price,
        observed_ts=match.observed_ts,
        fidelity=match.fidelity.value,
    )


def _horizon_outcome(
    instrument_id: str,
    direction: SignalDirection,
    event_ts: datetime,
    reference_price: Decimal | None,
    atr: Decimal | None,
    bars: Mapping[datetime, OneMinuteBar],
    calendar: AuditSessionCalendar,
    session: tuple[datetime, datetime] | None,
    horizon_minutes: int,
) -> SignalOutcomeHorizon:
    if session is None:
        return _unavailable_horizon(
            horizon_minutes, event_ts, 0, "event_outside_configured_session"
        )
    _, session_close = session
    expected = calendar.expected_minute_opens(instrument_id, event_ts, session_close)
    if len(expected) < horizon_minutes:
        return _unavailable_horizon(
            horizon_minutes,
            session_close,
            0,
            "session_ended_before_horizon",
        )
    target_opens = expected[:horizon_minutes]
    expected_end = target_opens[-1] + _MINUTE
    selected: list[OneMinuteBar] = []
    for open_ts in target_opens:
        bar = bars.get(open_ts)
        if bar is None:
            return _unavailable_horizon(
                horizon_minutes,
                expected_end,
                len(selected),
                "forward_bar_window_incomplete",
            )
        selected.append(bar)
    if reference_price is None:
        return _unavailable_horizon(
            horizon_minutes,
            expected_end,
            len(selected),
            "event_reference_bar_unavailable",
        )
    multiplier = Decimal("1") if direction == SignalDirection.LONG else Decimal("-1")
    directional_return = (selected[-1].close - reference_price) * multiplier
    if direction == SignalDirection.LONG:
        favorable_bar = max(selected, key=lambda item: item.high)
        adverse_bar = min(selected, key=lambda item: item.low)
        favorable = max(Decimal("0"), favorable_bar.high - reference_price)
        adverse = max(Decimal("0"), reference_price - adverse_bar.low)
    else:
        favorable_bar = min(selected, key=lambda item: item.low)
        adverse_bar = max(selected, key=lambda item: item.high)
        favorable = max(Decimal("0"), reference_price - favorable_bar.low)
        adverse = max(Decimal("0"), adverse_bar.high - reference_price)
    return SignalOutcomeHorizon(
        horizon_minutes=horizon_minutes,
        status=HorizonOutcomeStatus.COMPLETE,
        expected_end_ts=expected_end,
        observed_bar_count=len(selected),
        close_price=selected[-1].close,
        directional_return_points=directional_return,
        directional_return_bps=directional_return / reference_price * Decimal("10000"),
        directional_return_atr=None if atr is None else directional_return / atr,
        maximum_favorable_excursion_points=favorable,
        maximum_adverse_excursion_points=adverse,
        maximum_favorable_excursion_atr=None if atr is None else favorable / atr,
        maximum_adverse_excursion_atr=None if atr is None else adverse / atr,
        favorable_extreme_ts=favorable_bar.close_ts,
        adverse_extreme_ts=adverse_bar.close_ts,
    )


def _unavailable_horizon(
    horizon_minutes: int,
    expected_end_ts: datetime,
    observed_bar_count: int,
    reason: str,
) -> SignalOutcomeHorizon:
    return SignalOutcomeHorizon(
        horizon_minutes=horizon_minutes,
        status=HorizonOutcomeStatus.UNAVAILABLE,
        expected_end_ts=expected_end_ts,
        observed_bar_count=observed_bar_count,
        reason_codes=(reason,),
    )


def _seconds(value: timedelta) -> Decimal:
    whole_seconds = value.days * 86_400 + value.seconds
    return Decimal(whole_seconds) + Decimal(value.microseconds) / Decimal("1000000")


def _counter_text(values: Counter[str]) -> str:
    return ", ".join(f"{key}={count}" for key, count in sorted(values.items())) or "none"


def _percentage(numerator: int, denominator: int) -> str:
    return "n/a" if denominator == 0 else f"{numerator / denominator:.1%}"


def _median_metric(values: Sequence[SignalOutcomeHorizon], field_name: str) -> str:
    available = [getattr(item, field_name) for item in values]
    metrics = [value for value in available if value is not None]
    return _decimal_text(None if not metrics else median(metrics))


def _median_record_metric(
    values: Sequence[SignalOutcomeRecord],
    field_name: str,
) -> str:
    available = [getattr(item, field_name) for item in values]
    metrics = [value for value in available if value is not None]
    return "n/a" if not metrics else str(median(metrics))


def _decimal_text(value: Decimal | None) -> str:
    return "n/a" if value is None else f"{value:+.3f}"
