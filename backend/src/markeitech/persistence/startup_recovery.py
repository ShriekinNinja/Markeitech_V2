from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol

from pydantic import Field

from markeitech.domain.base import VersionedDomainModel, require_utc
from markeitech.domain.instruments import InstrumentRegistryConfig, SecurityType
from markeitech.domain.market_data import OneMinuteBar
from markeitech.persistence.config import PersistenceConfig
from markeitech.persistence.contracts import RecoveryRecord, RecoveryStatus
from markeitech.persistence.ports import RecoveryMetadataStore
from markeitech.persistence.recovery import (
    HistoricalRecoveryRequest,
    RecoveryLifecycleTracker,
    RecoveryPlan,
    RecoveryPlanner,
    RecoveryPlanningError,
    SessionCalendar,
)


class StartupRecoveryStatus(StrEnum):
    IDLE = "idle"
    RECOVERING = "recovering"
    COMPLETE = "complete"
    DEGRADED = "degraded"
    FAILED = "failed"


class StartupRecoveryCatalog(Protocol):
    def query_one_minute_bars(self, instrument_id: str) -> tuple[OneMinuteBar, ...]: ...


class InstrumentStartupRecoverySnapshot(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    status: RecoveryStatus
    requested_start_ts: datetime
    requested_end_ts: datetime
    missing_before: int = Field(ge=0)
    missing_after: int = Field(ge=0)
    request_count: int = Field(ge=0)
    confirmed_provider_empty_count: int = Field(default=0, ge=0)
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)


class StartupRecoverySnapshot(VersionedDomainModel):
    status: StartupRecoveryStatus = StartupRecoveryStatus.IDLE
    instruments: tuple[InstrumentStartupRecoverySnapshot, ...] = Field(default_factory=tuple)
    total_request_count: int = Field(default=0, ge=0)


@dataclass
class _RecoveryContext:
    initial_plan: RecoveryPlan
    record: RecoveryRecord
    terminal: bool = False


class StartupRecoveryService:
    """Plans, tracks, and verifies startup bar recovery for all enabled instruments."""

    def __init__(
        self,
        config: PersistenceConfig,
        registry: InstrumentRegistryConfig,
        catalog: StartupRecoveryCatalog,
        metadata: RecoveryMetadataStore,
        calendar: SessionCalendar,
        flush_pending: Callable[[], bool],
    ) -> None:
        self._config = config
        self._catalog = catalog
        self._planner = RecoveryPlanner(config, calendar)
        self._tracker = RecoveryLifecycleTracker(metadata)
        self._metadata = metadata
        self._flush_pending = flush_pending
        self._runtimes = tuple(
            sorted(
                (
                    runtime
                    for runtime in registry.instruments
                    if runtime.enabled and runtime.contract.security_type != SecurityType.CRYPTO
                ),
                key=lambda runtime: runtime.contract.instrument_id,
            )
        )
        self._returned: dict[str, set[datetime]] = defaultdict(set)
        self._rejected: dict[str, set[datetime]] = defaultdict(set)
        self._confirmed_counts: dict[str, int] = defaultdict(int)
        self._unresolved_reasons: dict[str, tuple[str, ...]] = {}
        self._contexts: dict[str, _RecoveryContext] = {}
        self._snapshot = StartupRecoverySnapshot()
        self._prepared = False
        self._finished = False

    @property
    def snapshot(self) -> StartupRecoverySnapshot:
        return self._snapshot

    def observe_bar(self, bar: OneMinuteBar, *, accepted: bool) -> None:
        configured = {runtime.contract.instrument_id for runtime in self._runtimes}
        if bar.instrument_id not in configured or bar.source != "ib" or not bar.is_complete:
            return
        self._returned[bar.instrument_id].add(bar.open_ts)
        if not accepted:
            self._rejected[bar.instrument_id].add(bar.open_ts)

    def prepare(self, now: datetime) -> tuple[HistoricalRecoveryRequest, ...]:
        if self._prepared:
            raise RuntimeError("startup recovery can only be prepared once")
        self._prepared = True
        now = require_utc(now)
        end_ts = now.replace(second=0, microsecond=0)
        requests_by_instrument: dict[str, deque[HistoricalRecoveryRequest]] = {}
        try:
            if not self._flush_pending():
                raise RuntimeError("persistence flush failed before startup recovery planning")
            for runtime in self._runtimes:
                instrument_id = runtime.contract.instrument_id
                warmup = runtime.warmup
                if warmup is None:
                    raise RuntimeError(f"enabled instrument {instrument_id!r} has no warmup policy")
                calendar_days = min(
                    max(warmup.lookback_sessions * 2, warmup.lookback_sessions + 4),
                    self._config.recovery_max_lookback_days,
                )
                start_ts = end_ts - timedelta(days=calendar_days)
                observed = self._catalog_observed(instrument_id, start_ts, end_ts)
                confirmed = self._confirmed_empty_opens(instrument_id, start_ts, end_ts)
                observed.update(confirmed)
                self._confirmed_counts[instrument_id] = len(confirmed)
                plan = self._planner.plan_bars(
                    instrument_id=instrument_id,
                    source="ib",
                    start_ts=start_ts,
                    end_ts=end_ts,
                    observed_open_timestamps=tuple(observed),
                    now=now,
                )
                record = self._tracker.begin(plan, now)
                terminal = record.status in {
                    RecoveryStatus.COMPLETE,
                    RecoveryStatus.DEGRADED,
                    RecoveryStatus.FAILED,
                }
                if not terminal and record.status == RecoveryStatus.PENDING:
                    record = self._tracker.mark_recovering(record, now)
                context = _RecoveryContext(plan, record, terminal)
                self._contexts[instrument_id] = context
                if terminal:
                    continue
                if plan.requests:
                    requests_by_instrument[instrument_id] = deque(plan.requests)
                else:
                    self._finish_context(context, plan, now)

            requests = _round_robin(requests_by_instrument)
            if len(requests) > self._config.recovery_max_total_requests:
                raise RecoveryPlanningError("startup recovery exceeds total request limit")
            self._snapshot = StartupRecoverySnapshot(
                status=(
                    StartupRecoveryStatus.RECOVERING
                    if requests
                    else self._overall_terminal_status()
                ),
                instruments=self._instrument_snapshots(),
                total_request_count=len(requests),
            )
            return requests
        except Exception:
            self._snapshot = StartupRecoverySnapshot(status=StartupRecoveryStatus.FAILED)
            raise

    def finish(self, now: datetime) -> StartupRecoverySnapshot:
        if not self._prepared:
            raise RuntimeError("startup recovery must be prepared before finish")
        if self._finished:
            return self._snapshot
        self._finished = True
        now = require_utc(now)
        try:
            if not self._flush_pending():
                raise RuntimeError("persistence flush failed before startup recovery verification")
            for instrument_id, context in self._contexts.items():
                if context.terminal:
                    continue
                initial = context.initial_plan
                observed = self._catalog_observed(
                    instrument_id,
                    initial.requested_start_ts,
                    initial.requested_end_ts,
                )
                confirmed = self._confirmed_empty_opens(
                    instrument_id,
                    initial.requested_start_ts,
                    initial.requested_end_ts,
                )
                observed.update(confirmed)
                for request in initial.requests:
                    cursor = request.start_ts
                    while cursor < request.end_ts:
                        if cursor not in observed and cursor not in self._returned[instrument_id]:
                            self._metadata.record_provider_empty_interval(
                                instrument_id=instrument_id,
                                source="ib",
                                open_ts=cursor,
                                observed_ts=now,
                            )
                        cursor += timedelta(minutes=1)
                confirmed = self._confirmed_empty_opens(
                    instrument_id,
                    initial.requested_start_ts,
                    initial.requested_end_ts,
                )
                observed.update(confirmed)
                self._confirmed_counts[instrument_id] = len(confirmed)
                requested_opens = {
                    timestamp
                    for request in initial.requests
                    for timestamp in _minute_opens(request.start_ts, request.end_ts)
                }
                unresolved = requested_opens - observed
                reasons: list[str] = []
                if unresolved & self._rejected[instrument_id]:
                    reasons.append("recovery_persistence_rejected")
                elif unresolved & self._returned[instrument_id]:
                    reasons.append("recovery_bar_not_durable")
                if unresolved - self._returned[instrument_id]:
                    reasons.append("provider_returned_no_bar")
                self._unresolved_reasons[instrument_id] = tuple(reasons)
                verified = self._planner.plan_bars(
                    instrument_id=instrument_id,
                    source="ib",
                    start_ts=initial.requested_start_ts,
                    end_ts=initial.requested_end_ts,
                    observed_open_timestamps=tuple(observed),
                    now=now,
                )
                self._finish_context(context, verified, now)
            self._snapshot = StartupRecoverySnapshot(
                status=self._overall_terminal_status(),
                instruments=self._instrument_snapshots(),
                total_request_count=self._snapshot.total_request_count,
            )
            return self._snapshot
        except Exception:
            self._snapshot = self._snapshot.model_copy(
                update={"status": StartupRecoveryStatus.FAILED}
            )
            raise

    def _catalog_observed(
        self,
        instrument_id: str,
        start_ts: datetime,
        end_ts: datetime,
    ) -> set[datetime]:
        return {
            bar.open_ts
            for bar in self._catalog.query_one_minute_bars(instrument_id)
            if bar.source == "ib" and start_ts <= bar.open_ts < end_ts
        }

    def _confirmed_empty_opens(
        self,
        instrument_id: str,
        start_ts: datetime,
        end_ts: datetime,
    ) -> set[datetime]:
        return set(
            self._metadata.load_confirmed_provider_empty_opens(
                instrument_id=instrument_id,
                source="ib",
                start_ts=start_ts,
                end_ts=end_ts,
                minimum_attempts=self._config.recovery_provider_empty_confirmation_attempts,
            )
        )

    def _finish_context(
        self,
        context: _RecoveryContext,
        verified: RecoveryPlan,
        now: datetime,
    ) -> None:
        reasons: list[str] = []
        if verified.missing_intervals:
            reasons.extend(verified.reason_codes)
            reasons.extend(self._unresolved_reasons.get(verified.instrument_id, ()))
        context.record = self._tracker.finish(
            context.record,
            remaining_intervals=verified.missing_intervals,
            now=now,
            reason_codes=tuple(dict.fromkeys(reasons)),
        )
        context.terminal = True

    def _overall_terminal_status(self) -> StartupRecoveryStatus:
        if any(
            context.record.status in {RecoveryStatus.DEGRADED, RecoveryStatus.FAILED}
            for context in self._contexts.values()
        ):
            return StartupRecoveryStatus.DEGRADED
        return StartupRecoveryStatus.COMPLETE

    def _instrument_snapshots(self) -> tuple[InstrumentStartupRecoverySnapshot, ...]:
        return tuple(
            InstrumentStartupRecoverySnapshot(
                instrument_id=instrument_id,
                status=context.record.status,
                requested_start_ts=context.initial_plan.requested_start_ts,
                requested_end_ts=context.initial_plan.requested_end_ts,
                missing_before=context.initial_plan.missing_intervals,
                missing_after=context.record.missing_intervals,
                request_count=len(context.initial_plan.requests),
                confirmed_provider_empty_count=self._confirmed_counts[instrument_id],
                reason_codes=context.record.reason_codes,
            )
            for instrument_id, context in sorted(self._contexts.items())
        )


def _round_robin(
    by_instrument: dict[str, deque[HistoricalRecoveryRequest]],
) -> tuple[HistoricalRecoveryRequest, ...]:
    ordered: list[HistoricalRecoveryRequest] = []
    active = deque(sorted(by_instrument))
    while active:
        instrument_id = active.popleft()
        requests = by_instrument[instrument_id]
        ordered.append(requests.popleft())
        if requests:
            active.append(instrument_id)
    return tuple(ordered)


def _minute_opens(start_ts: datetime, end_ts: datetime) -> tuple[datetime, ...]:
    opens: list[datetime] = []
    cursor = start_ts
    while cursor < end_ts:
        opens.append(cursor)
        cursor += timedelta(minutes=1)
    return tuple(opens)
