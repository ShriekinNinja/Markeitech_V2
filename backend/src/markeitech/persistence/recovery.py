from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import Field, field_validator, model_validator

from markeitech.domain.base import VersionedDomainModel, require_utc
from markeitech.persistence.config import PersistenceConfig
from markeitech.persistence.contracts import (
    DataFidelity,
    PersistenceEventKind,
    RecoveryRecord,
    RecoveryStatus,
)
from markeitech.persistence.ports import RecoveryMetadataStore

_MINUTE = timedelta(minutes=1)


class RecoveryPlanningError(ValueError):
    pass


class RecoveryMethod(StrEnum):
    EXACT_WAL_REPLAY = "exact_wal_replay"
    HISTORICAL_BAR_BACKFILL = "historical_bar_backfill"
    BEST_EFFORT_TICK_BACKFILL = "best_effort_tick_backfill"
    UNRECOVERABLE_TICK_GAP = "unrecoverable_tick_gap"
    UNAVAILABLE_BAR_HISTORY = "unavailable_bar_history"
    EXPECTED_SESSION_CLOSURE = "expected_session_closure"


class RecoveryPlanStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    REQUIRED = "required"
    DEGRADED = "degraded"


class SessionWindow(VersionedDomainModel):
    open_ts: datetime
    close_ts: datetime

    @field_validator("open_ts", "close_ts")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _window_must_be_positive(self) -> SessionWindow:
        if self.close_ts <= self.open_ts:
            raise ValueError("session window close must be after open")
        if self.open_ts.second or self.open_ts.microsecond:
            raise ValueError("session window open must align to a minute")
        if self.close_ts.second or self.close_ts.microsecond:
            raise ValueError("session window close must align to a minute")
        return self


class SessionCalendar(Protocol):
    def expected_minute_opens(
        self,
        instrument_id: str,
        start_ts: datetime,
        end_ts: datetime,
    ) -> tuple[datetime, ...]: ...


class ExplicitSessionCalendar:
    """Deterministic schedule boundary for tests and provider calendar adapters."""

    def __init__(self, windows: dict[str, Sequence[SessionWindow]]) -> None:
        self._windows = {
            instrument_id: tuple(sorted(instrument_windows, key=lambda item: item.open_ts))
            for instrument_id, instrument_windows in windows.items()
        }
        for instrument_id, instrument_windows in self._windows.items():
            previous_close: datetime | None = None
            for window in instrument_windows:
                if previous_close is not None and window.open_ts < previous_close:
                    raise ValueError(f"session windows overlap for instrument {instrument_id!r}")
                previous_close = window.close_ts

    def expected_minute_opens(
        self,
        instrument_id: str,
        start_ts: datetime,
        end_ts: datetime,
    ) -> tuple[datetime, ...]:
        start_ts = require_utc(start_ts)
        end_ts = require_utc(end_ts)
        if end_ts <= start_ts:
            raise ValueError("calendar query end must be after start")
        if instrument_id not in self._windows:
            raise RecoveryPlanningError(
                f"session calendar is not configured for instrument {instrument_id!r}"
            )
        expected: list[datetime] = []
        for window in self._windows[instrument_id]:
            cursor = max(window.open_ts, start_ts)
            cursor = _ceil_minute(cursor)
            limit = min(window.close_ts, end_ts)
            while cursor < limit:
                expected.append(cursor)
                cursor += _MINUTE
        return tuple(expected)


class RecoveryInterval(VersionedDomainModel):
    start_ts: datetime
    end_ts: datetime
    method: RecoveryMethod
    fidelity: DataFidelity
    missing_intervals: int = Field(ge=0)
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator("start_ts", "end_ts")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _interval_must_be_consistent(self) -> RecoveryInterval:
        if self.end_ts <= self.start_ts:
            raise ValueError("recovery interval end must be after start")
        if self.method == RecoveryMethod.EXPECTED_SESSION_CLOSURE:
            if self.missing_intervals != 0:
                raise ValueError("expected closure cannot contain missing intervals")
        elif self.missing_intervals == 0:
            raise ValueError("recovery interval must contain missing intervals")
        return self


class HistoricalRecoveryRequest(VersionedDomainModel):
    request_id: str = Field(min_length=64, max_length=64)
    instrument_id: str = Field(min_length=1)
    event_kind: PersistenceEventKind
    source: str = Field(min_length=1)
    start_ts: datetime
    end_ts: datetime
    expected_intervals: int = Field(ge=1)
    best_effort: bool = False

    @field_validator("start_ts", "end_ts")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _request_must_be_consistent(self) -> HistoricalRecoveryRequest:
        if self.end_ts <= self.start_ts:
            raise ValueError("recovery request end must be after start")
        if self.event_kind == PersistenceEventKind.ONE_MINUTE_BAR and self.best_effort:
            raise ValueError("bar recovery requests cannot be best effort")
        if self.event_kind != PersistenceEventKind.ONE_MINUTE_BAR and not self.best_effort:
            raise ValueError("tick recovery requests must be labeled best effort")
        return self


class RecoveryPlan(VersionedDomainModel):
    recovery_id: UUID
    instrument_id: str = Field(min_length=1)
    event_kind: PersistenceEventKind
    source: str = Field(min_length=1)
    status: RecoveryPlanStatus
    requested_start_ts: datetime
    requested_end_ts: datetime
    expected_intervals: int = Field(ge=0)
    observed_intervals: int = Field(ge=0)
    missing_intervals: int = Field(ge=0)
    intervals: tuple[RecoveryInterval, ...] = Field(default_factory=tuple)
    requests: tuple[HistoricalRecoveryRequest, ...] = Field(default_factory=tuple)
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)
    created_ts: datetime

    @field_validator("requested_start_ts", "requested_end_ts", "created_ts")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _plan_must_be_consistent(self) -> RecoveryPlan:
        if self.requested_end_ts <= self.requested_start_ts:
            raise ValueError("recovery plan end must be after start")
        if self.observed_intervals > self.expected_intervals:
            raise ValueError("observed intervals cannot exceed expected intervals")
        if self.missing_intervals != self.expected_intervals - self.observed_intervals:
            if self.event_kind == PersistenceEventKind.ONE_MINUTE_BAR:
                raise ValueError("bar missing count must equal expected minus observed")
        if self.status == RecoveryPlanStatus.NOT_REQUIRED and self.missing_intervals:
            raise ValueError("not-required recovery cannot contain missing intervals")
        if self.status != RecoveryPlanStatus.NOT_REQUIRED and not self.reason_codes:
            raise ValueError("required or degraded recovery requires reason codes")
        return self


class RecoveryPlanner:
    def __init__(self, config: PersistenceConfig, calendar: SessionCalendar) -> None:
        self._config = config
        self._calendar = calendar

    def plan_bars(
        self,
        *,
        instrument_id: str,
        source: str,
        start_ts: datetime,
        end_ts: datetime,
        observed_open_timestamps: Sequence[datetime],
        now: datetime,
    ) -> RecoveryPlan:
        start_ts, end_ts, now = _validated_range(start_ts, end_ts, now)
        effective_start = max(
            start_ts,
            now - timedelta(days=self._config.recovery_max_lookback_days),
        )
        all_expected = self._expected(instrument_id, start_ts, end_ts)
        recoverable_expected = (
            self._expected(instrument_id, effective_start, end_ts)
            if effective_start < end_ts
            else ()
        )
        observed: set[datetime] = set()
        for timestamp in observed_open_timestamps:
            timestamp = require_utc(timestamp)
            if timestamp.second or timestamp.microsecond:
                raise RecoveryPlanningError("observed bar open is not minute-aligned")
            if start_ts <= timestamp < end_ts:
                observed.add(timestamp)
        observed_expected = set(all_expected) & observed
        missing = tuple(timestamp for timestamp in all_expected if timestamp not in observed)
        recoverable_missing = tuple(
            timestamp for timestamp in recoverable_expected if timestamp not in observed
        )
        unavailable_missing = tuple(
            timestamp for timestamp in missing if timestamp < effective_start
        )

        intervals = [
            *_intervals_from_opens(
                unavailable_missing,
                method=RecoveryMethod.UNAVAILABLE_BAR_HISTORY,
                fidelity=DataFidelity.UNAVAILABLE,
                reason="bar_gap_beyond_provider_lookback",
            ),
            *_intervals_from_opens(
                recoverable_missing,
                method=RecoveryMethod.HISTORICAL_BAR_BACKFILL,
                fidelity=DataFidelity.REPORTED,
                reason="missing_1m_bars",
            ),
        ]
        requests = self._bar_requests(instrument_id, source, recoverable_missing)
        reasons: tuple[str, ...]
        if not all_expected:
            reasons = (RecoveryMethod.EXPECTED_SESSION_CLOSURE.value,)
            intervals = [
                RecoveryInterval(
                    start_ts=start_ts,
                    end_ts=end_ts,
                    method=RecoveryMethod.EXPECTED_SESSION_CLOSURE,
                    fidelity=DataFidelity.UNAVAILABLE,
                    missing_intervals=0,
                    reason_codes=reasons,
                )
            ]
            status = RecoveryPlanStatus.NOT_REQUIRED
        elif unavailable_missing:
            reasons = tuple(
                dict.fromkeys(reason for interval in intervals for reason in interval.reason_codes)
            )
            status = RecoveryPlanStatus.DEGRADED
        elif missing:
            reasons = ("missing_1m_bars",)
            status = RecoveryPlanStatus.REQUIRED
        else:
            reasons = ()
            status = RecoveryPlanStatus.NOT_REQUIRED
        return RecoveryPlan(
            recovery_id=_recovery_id(
                instrument_id,
                PersistenceEventKind.ONE_MINUTE_BAR,
                source,
                start_ts,
                end_ts,
            ),
            instrument_id=instrument_id,
            event_kind=PersistenceEventKind.ONE_MINUTE_BAR,
            source=source,
            status=status,
            requested_start_ts=start_ts,
            requested_end_ts=end_ts,
            expected_intervals=len(all_expected),
            observed_intervals=len(observed_expected),
            missing_intervals=len(missing),
            intervals=tuple(intervals),
            requests=requests,
            reason_codes=reasons,
            created_ts=now,
        )

    def plan_tick_gap(
        self,
        *,
        instrument_id: str,
        event_kind: PersistenceEventKind,
        source: str,
        start_ts: datetime,
        end_ts: datetime,
        now: datetime,
        journal_available: bool,
        historical_backfill_available: bool,
    ) -> RecoveryPlan:
        if event_kind not in {
            PersistenceEventKind.TRADE_TICK,
            PersistenceEventKind.QUOTE_TICK,
        }:
            raise ValueError("tick recovery requires a trade or quote event kind")
        start_ts, end_ts, now = _validated_range(start_ts, end_ts, now)
        if journal_available:
            method = RecoveryMethod.EXACT_WAL_REPLAY
            fidelity = DataFidelity.REPORTED
            status = RecoveryPlanStatus.REQUIRED
            reason = "journaled_tick_gap"
            requests: tuple[HistoricalRecoveryRequest, ...] = ()
        elif historical_backfill_available:
            method = RecoveryMethod.BEST_EFFORT_TICK_BACKFILL
            fidelity = DataFidelity.PARTIAL
            status = RecoveryPlanStatus.DEGRADED
            reason = "tick_gap_best_effort_only"
            requests = (
                _request(
                    instrument_id,
                    event_kind,
                    source,
                    start_ts,
                    end_ts,
                    expected_intervals=1,
                    best_effort=True,
                ),
            )
        else:
            method = RecoveryMethod.UNRECOVERABLE_TICK_GAP
            fidelity = DataFidelity.UNAVAILABLE
            status = RecoveryPlanStatus.DEGRADED
            reason = "unrecoverable_tick_gap"
            requests = ()
        interval = RecoveryInterval(
            start_ts=start_ts,
            end_ts=end_ts,
            method=method,
            fidelity=fidelity,
            missing_intervals=1,
            reason_codes=(reason,),
        )
        return RecoveryPlan(
            recovery_id=_recovery_id(
                instrument_id,
                event_kind,
                source,
                start_ts,
                end_ts,
            ),
            instrument_id=instrument_id,
            event_kind=event_kind,
            source=source,
            status=status,
            requested_start_ts=start_ts,
            requested_end_ts=end_ts,
            expected_intervals=1,
            observed_intervals=0,
            missing_intervals=1,
            intervals=(interval,),
            requests=requests,
            reason_codes=(reason,),
            created_ts=now,
        )

    def _expected(
        self,
        instrument_id: str,
        start_ts: datetime,
        end_ts: datetime,
    ) -> tuple[datetime, ...]:
        expected = self._calendar.expected_minute_opens(instrument_id, start_ts, end_ts)
        normalized = tuple(sorted(set(expected)))
        for timestamp in normalized:
            require_utc(timestamp)
            if not start_ts <= timestamp < end_ts:
                raise RecoveryPlanningError("calendar returned an out-of-range minute")
            if timestamp.second or timestamp.microsecond:
                raise RecoveryPlanningError("calendar returned a non-minute timestamp")
        return normalized

    def _bar_requests(
        self,
        instrument_id: str,
        source: str,
        missing: tuple[datetime, ...],
    ) -> tuple[HistoricalRecoveryRequest, ...]:
        requests: list[HistoricalRecoveryRequest] = []
        for contiguous in _contiguous_runs(missing):
            maximum = self._config.recovery_max_intervals_per_request
            for offset in range(0, len(contiguous), maximum):
                chunk = contiguous[offset : offset + maximum]
                requests.append(
                    _request(
                        instrument_id,
                        PersistenceEventKind.ONE_MINUTE_BAR,
                        source,
                        chunk[0],
                        chunk[-1] + _MINUTE,
                        expected_intervals=len(chunk),
                        best_effort=False,
                    )
                )
        if len(requests) > self._config.recovery_max_requests_per_plan:
            raise RecoveryPlanningError("recovery plan exceeds configured request limit")
        return tuple(requests)


class RecoveryLifecycleTracker:
    def __init__(self, store: RecoveryMetadataStore) -> None:
        self._store = store

    def begin(self, plan: RecoveryPlan, now: datetime) -> RecoveryRecord:
        now = require_utc(now)
        existing = self._store.load_recovery(plan.recovery_id)
        if existing is not None:
            return existing
        record = RecoveryRecord(
            recovery_id=plan.recovery_id,
            instrument_id=plan.instrument_id,
            event_kind=plan.event_kind,
            source=plan.source,
            status=RecoveryStatus.PENDING,
            requested_start_ts=plan.requested_start_ts,
            requested_end_ts=plan.requested_end_ts,
            missing_intervals=plan.missing_intervals,
            reason_codes=plan.reason_codes,
            started_ts=now,
            updated_ts=now,
        )
        self._store.save_recovery(record)
        return record

    def mark_recovering(self, record: RecoveryRecord, now: datetime) -> RecoveryRecord:
        if record.status != RecoveryStatus.PENDING:
            raise ValueError("only pending recovery can start")
        updated = RecoveryRecord.model_validate(
            {
                **record.model_dump(),
                "status": RecoveryStatus.RECOVERING,
                "updated_ts": require_utc(now),
            }
        )
        self._store.save_recovery(updated)
        return updated

    def finish(
        self,
        record: RecoveryRecord,
        *,
        remaining_intervals: int,
        now: datetime,
        reason_codes: tuple[str, ...] = (),
    ) -> RecoveryRecord:
        if record.status != RecoveryStatus.RECOVERING:
            raise ValueError("only recovering lifecycle can finish")
        now = require_utc(now)
        if remaining_intervals == 0:
            status = RecoveryStatus.COMPLETE
            reasons: tuple[str, ...] = ()
        else:
            if not reason_codes:
                raise ValueError("degraded recovery requires reason codes")
            status = RecoveryStatus.DEGRADED
            reasons = reason_codes
        updated = RecoveryRecord.model_validate(
            {
                **record.model_dump(),
                "status": status,
                "missing_intervals": remaining_intervals,
                "reason_codes": reasons,
                "updated_ts": now,
                "completed_ts": now,
            }
        )
        self._store.save_recovery(updated)
        return updated


def _validated_range(
    start_ts: datetime,
    end_ts: datetime,
    now: datetime,
) -> tuple[datetime, datetime, datetime]:
    start_ts = require_utc(start_ts)
    end_ts = require_utc(end_ts)
    now = require_utc(now)
    if end_ts <= start_ts:
        raise ValueError("recovery end must be after start")
    if end_ts > now:
        raise ValueError("recovery range cannot extend into the future")
    return start_ts, end_ts, now


def _ceil_minute(value: datetime) -> datetime:
    if value.second == 0 and value.microsecond == 0:
        return value
    return value.replace(second=0, microsecond=0) + _MINUTE


def _contiguous_runs(timestamps: Sequence[datetime]) -> tuple[tuple[datetime, ...], ...]:
    if not timestamps:
        return ()
    runs: list[list[datetime]] = [[timestamps[0]]]
    for timestamp in timestamps[1:]:
        if timestamp == runs[-1][-1] + _MINUTE:
            runs[-1].append(timestamp)
        else:
            runs.append([timestamp])
    return tuple(tuple(run) for run in runs)


def _intervals_from_opens(
    timestamps: Sequence[datetime],
    *,
    method: RecoveryMethod,
    fidelity: DataFidelity,
    reason: str,
) -> tuple[RecoveryInterval, ...]:
    return tuple(
        RecoveryInterval(
            start_ts=run[0],
            end_ts=run[-1] + _MINUTE,
            method=method,
            fidelity=fidelity,
            missing_intervals=len(run),
            reason_codes=(reason,),
        )
        for run in _contiguous_runs(timestamps)
    )


def _request(
    instrument_id: str,
    event_kind: PersistenceEventKind,
    source: str,
    start_ts: datetime,
    end_ts: datetime,
    *,
    expected_intervals: int,
    best_effort: bool,
) -> HistoricalRecoveryRequest:
    identity = (
        f"{source}|{instrument_id}|{event_kind.value}|"
        f"{start_ts.isoformat()}|{end_ts.isoformat()}|{best_effort}"
    )
    return HistoricalRecoveryRequest(
        request_id=hashlib.sha256(identity.encode()).hexdigest(),
        instrument_id=instrument_id,
        event_kind=event_kind,
        source=source,
        start_ts=start_ts,
        end_ts=end_ts,
        expected_intervals=expected_intervals,
        best_effort=best_effort,
    )


def _recovery_id(
    instrument_id: str,
    event_kind: PersistenceEventKind,
    source: str,
    start_ts: datetime,
    end_ts: datetime,
) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        f"{source}|{instrument_id}|{event_kind.value}|{start_ts.isoformat()}|{end_ts.isoformat()}",
    )
