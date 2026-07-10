from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol

from pydantic import Field, field_validator, model_validator

from markeitech.domain.base import VersionedDomainModel, require_utc
from markeitech.domain.events import ActiveInstrumentChangedEvent


class ActiveSwitchStatus(StrEnum):
    STABLE = "stable"
    AWAITING_CANDIDATE_TICKS = "awaiting_candidate_ticks"


class ActiveInstrumentSwitchRequest(VersionedDomainModel):
    request_id: str = Field(min_length=1)
    target_instrument_id: str = Field(min_length=1)
    requested_ts: datetime
    reason: str = Field(default="operator_switch", min_length=1)

    @field_validator("requested_ts")
    @classmethod
    def _requested_ts_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)


class ActiveSwitchSnapshot(VersionedDomainModel):
    status: ActiveSwitchStatus
    active_instrument_id: str = Field(min_length=1)
    candidate_instrument_id: str | None = None
    request_id: str | None = None
    reason: str | None = None
    trade_tick_ready: bool = False
    quote_tick_ready: bool = False
    deadline: datetime | None = None
    last_failure: str | None = None

    @field_validator("deadline")
    @classmethod
    def _deadline_must_be_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @model_validator(mode="after")
    def _shape_must_match_status(self) -> ActiveSwitchSnapshot:
        candidate_fields = (
            self.candidate_instrument_id,
            self.request_id,
            self.reason,
            self.deadline,
        )
        if self.status == ActiveSwitchStatus.STABLE:
            if any(value is not None for value in candidate_fields):
                raise ValueError("stable active switch state cannot carry a candidate")
            if self.trade_tick_ready or self.quote_tick_ready:
                raise ValueError("stable active switch state cannot carry candidate readiness")
        elif any(value is None for value in candidate_fields):
            raise ValueError("active switch candidate state requires complete request context")
        return self


class ActiveSwitchTarget(Protocol):
    def subscribe_trade_ticks(self, *, instrument_id: str, data_client_name: str) -> object: ...

    def subscribe_quote_ticks(self, *, instrument_id: str, data_client_name: str) -> object: ...

    def unsubscribe_trade_ticks(self, *, instrument_id: str, data_client_name: str) -> object: ...

    def unsubscribe_quote_ticks(self, *, instrument_id: str, data_client_name: str) -> object: ...


class ActiveInstrumentSwitchCoordinator:
    def __init__(
        self,
        *,
        active_instrument_id: str,
        enabled_instrument_ids: set[str],
        data_client_name: str,
        target: ActiveSwitchTarget,
        now: Callable[[], datetime],
        runtime_ready: Callable[[], bool],
        on_changed: Callable[[ActiveInstrumentChangedEvent], None],
        readiness_timeout: timedelta = timedelta(seconds=10),
    ) -> None:
        if active_instrument_id not in enabled_instrument_ids:
            raise ValueError("active instrument must be enabled")
        if readiness_timeout <= timedelta(0):
            raise ValueError("readiness timeout must be positive")
        self._enabled_instrument_ids = frozenset(enabled_instrument_ids)
        self._data_client_name = data_client_name
        self._target = target
        self._now = now
        self._runtime_ready = runtime_ready
        self._on_changed = on_changed
        self._readiness_timeout = readiness_timeout
        self._snapshot = ActiveSwitchSnapshot(
            status=ActiveSwitchStatus.STABLE,
            active_instrument_id=active_instrument_id,
        )

    @property
    def snapshot(self) -> ActiveSwitchSnapshot:
        return self._snapshot

    def request_switch(self, request: ActiveInstrumentSwitchRequest) -> ActiveSwitchSnapshot:
        if self._snapshot.status != ActiveSwitchStatus.STABLE:
            raise RuntimeError("an active instrument switch is already in progress")
        if not self._runtime_ready():
            raise RuntimeError("market-data runtime is not ready for active instrument switching")
        if request.target_instrument_id not in self._enabled_instrument_ids:
            raise ValueError("target instrument is not enabled in the runtime registry")
        if request.target_instrument_id == self._snapshot.active_instrument_id:
            raise ValueError("target instrument is already active")

        self._snapshot = ActiveSwitchSnapshot(
            status=ActiveSwitchStatus.AWAITING_CANDIDATE_TICKS,
            active_instrument_id=self._snapshot.active_instrument_id,
            candidate_instrument_id=request.target_instrument_id,
            request_id=request.request_id,
            reason=request.reason,
            deadline=require_utc(self._now()) + self._readiness_timeout,
        )
        try:
            self._subscribe_candidate(request.target_instrument_id)
        except Exception:
            self._rollback_candidate("candidate_subscription_failed")
            raise
        return self._snapshot

    def observe_trade_tick(self, instrument_id: str) -> ActiveInstrumentChangedEvent | None:
        if instrument_id != self._snapshot.candidate_instrument_id:
            return None
        self._snapshot = self._snapshot.model_copy(update={"trade_tick_ready": True})
        return self._promote_if_ready()

    def observe_quote_tick(self, instrument_id: str) -> ActiveInstrumentChangedEvent | None:
        if instrument_id != self._snapshot.candidate_instrument_id:
            return None
        self._snapshot = self._snapshot.model_copy(update={"quote_tick_ready": True})
        return self._promote_if_ready()

    def check_timeout(self, now: datetime | None = None) -> bool:
        checked_at = require_utc(now or self._now())
        if self._snapshot.status != ActiveSwitchStatus.AWAITING_CANDIDATE_TICKS:
            return False
        if self._snapshot.deadline is None or checked_at < self._snapshot.deadline:
            return False
        self._rollback_candidate("candidate_tick_timeout")
        return True

    def _promote_if_ready(self) -> ActiveInstrumentChangedEvent | None:
        if not (self._snapshot.trade_tick_ready and self._snapshot.quote_tick_ready):
            return None

        previous = self._snapshot.active_instrument_id
        candidate = self._require_candidate()
        request_id = self._snapshot.request_id
        reason = self._snapshot.reason
        try:
            self._unsubscribe_ticks(previous)
        except Exception:
            self._repair_previous_active(previous)
            self._rollback_candidate("previous_active_unsubscribe_failed")
            raise

        event_ts = require_utc(self._now())
        event = ActiveInstrumentChangedEvent(
            previous_instrument_id=previous,
            active_instrument_id=candidate,
            event_ts=event_ts,
            ts_init=event_ts,
            reason=f"{reason}:{request_id}",
        )
        self._snapshot = ActiveSwitchSnapshot(
            status=ActiveSwitchStatus.STABLE,
            active_instrument_id=candidate,
        )
        self._on_changed(event)
        return event

    def _subscribe_candidate(self, instrument_id: str) -> None:
        self._target.subscribe_trade_ticks(
            instrument_id=instrument_id,
            data_client_name=self._data_client_name,
        )
        try:
            self._target.subscribe_quote_ticks(
                instrument_id=instrument_id,
                data_client_name=self._data_client_name,
            )
        except Exception:
            self._target.unsubscribe_trade_ticks(
                instrument_id=instrument_id,
                data_client_name=self._data_client_name,
            )
            raise

    def _unsubscribe_ticks(self, instrument_id: str) -> None:
        self._target.unsubscribe_trade_ticks(
            instrument_id=instrument_id,
            data_client_name=self._data_client_name,
        )
        self._target.unsubscribe_quote_ticks(
            instrument_id=instrument_id,
            data_client_name=self._data_client_name,
        )

    def _repair_previous_active(self, instrument_id: str) -> None:
        for subscribe in (
            self._target.subscribe_trade_ticks,
            self._target.subscribe_quote_ticks,
        ):
            try:
                subscribe(
                    instrument_id=instrument_id,
                    data_client_name=self._data_client_name,
                )
            except Exception:
                pass

    def _rollback_candidate(self, failure: str) -> None:
        candidate = self._snapshot.candidate_instrument_id
        if candidate is not None:
            self._best_effort_unsubscribe(candidate)
        active = self._snapshot.active_instrument_id
        self._snapshot = ActiveSwitchSnapshot(
            status=ActiveSwitchStatus.STABLE,
            active_instrument_id=active,
            last_failure=failure,
        )

    def _best_effort_unsubscribe(self, instrument_id: str) -> None:
        for unsubscribe in (
            self._target.unsubscribe_trade_ticks,
            self._target.unsubscribe_quote_ticks,
        ):
            try:
                unsubscribe(
                    instrument_id=instrument_id,
                    data_client_name=self._data_client_name,
                )
            except Exception:
                pass

    def _require_candidate(self) -> str:
        candidate = self._snapshot.candidate_instrument_id
        if candidate is None:
            raise RuntimeError("active switch candidate is missing")
        return candidate
