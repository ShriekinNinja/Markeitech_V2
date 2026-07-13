from __future__ import annotations

from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from threading import Lock
from typing import Any

import pandas_market_calendars as market_calendars
from pandas import isna

from markeitech.domain.base import require_utc
from markeitech.domain.instruments import InstrumentRegistryConfig, SessionProfile
from markeitech.persistence.recovery import RecoveryPlanningError, SessionWindow

_MINUTE = timedelta(minutes=1)
_SCHEDULE_PADDING = timedelta(days=2)


@dataclass(frozen=True)
class InstrumentCalendarPolicy:
    instrument_id: str
    calendar_id: str
    session_profile: SessionProfile


class PandasMarketSessionCalendar:
    """Product-calendar adapter with explicit instrument ownership and bounded caching."""

    def __init__(
        self,
        policies: Sequence[InstrumentCalendarPolicy],
        *,
        maximum_query_days: int = 370,
        maximum_cached_schedules: int = 128,
    ) -> None:
        if maximum_query_days < 1:
            raise ValueError("maximum calendar query days must be positive")
        if maximum_cached_schedules < 1:
            raise ValueError("maximum cached schedules must be positive")
        self._maximum_query_days = maximum_query_days
        self._maximum_cached_schedules = maximum_cached_schedules
        self._schedule_cache: OrderedDict[
            tuple[str, SessionProfile, date, date], tuple[SessionWindow, ...]
        ] = OrderedDict()
        self._session_cache: OrderedDict[
            tuple[str, SessionProfile, date, date], tuple[SessionWindow, ...]
        ] = OrderedDict()
        self._cache_lock = Lock()
        self._policies: dict[str, InstrumentCalendarPolicy] = {}
        for policy in policies:
            if policy.instrument_id in self._policies:
                raise ValueError(f"duplicate calendar policy for {policy.instrument_id!r}")
            self._validate_policy(policy)
            self._policies[policy.instrument_id] = policy

    @classmethod
    def from_registry(
        cls,
        registry: InstrumentRegistryConfig,
        *,
        include_disabled: bool = False,
        maximum_query_days: int = 370,
        maximum_cached_schedules: int = 128,
    ) -> PandasMarketSessionCalendar:
        return cls(
            tuple(
                InstrumentCalendarPolicy(
                    instrument_id=runtime.contract.instrument_id,
                    calendar_id=runtime.contract.calendar_id,
                    session_profile=runtime.contract.session_profile,
                )
                for runtime in registry.instruments
                if runtime.enabled or include_disabled
            ),
            maximum_query_days=maximum_query_days,
            maximum_cached_schedules=maximum_cached_schedules,
        )

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
        if end_ts - start_ts > timedelta(days=self._maximum_query_days):
            raise RecoveryPlanningError("calendar query exceeds configured day limit")
        policy = self._policy(instrument_id)

        if policy.session_profile == SessionProfile.CONTINUOUS:
            return _minute_range(start_ts, end_ts)

        windows = self._schedule_windows(
            policy.calendar_id,
            policy.session_profile,
            (start_ts - _SCHEDULE_PADDING).date(),
            (end_ts + _SCHEDULE_PADDING).date(),
        )
        expected: list[datetime] = []
        for window in windows:
            cursor = _ceil_minute(max(window.open_ts, start_ts))
            limit = min(window.close_ts, end_ts)
            while cursor < limit:
                expected.append(cursor)
                cursor += _MINUTE
        return tuple(expected)

    def retention_cutoff(
        self,
        instrument_id: str,
        completed_sessions: int,
        as_of: datetime,
    ) -> datetime:
        as_of = require_utc(as_of)
        if completed_sessions < 1:
            raise ValueError("completed session count must be positive")
        policy = self._policy(instrument_id)
        if policy.session_profile == SessionProfile.CONTINUOUS:
            cutoff_date = as_of.date() - timedelta(days=completed_sessions)
            return datetime.combine(cutoff_date, time.min, UTC)

        calendar = _load_calendar(policy.calendar_id)
        start_name, end_name = _market_time_range(calendar, policy.session_profile)
        schedule = calendar.schedule(
            start_date=(as_of - timedelta(days=self._maximum_query_days)).date(),
            end_date=as_of.date(),
            tz="UTC",
            start=start_name,
            end=end_name,
            interruptions=True,
        )
        completed = [
            (_utc_datetime(row[start_name]), _utc_datetime(row[end_name]))
            for _, row in schedule.iterrows()
            if _utc_datetime(row[end_name]) <= as_of
        ]
        if len(completed) < completed_sessions:
            raise RecoveryPlanningError(
                f"calendar cannot resolve {completed_sessions} completed sessions "
                f"for instrument {instrument_id!r} within its query limit"
            )
        return completed[-completed_sessions][0]

    def has_policy(self, instrument_id: str) -> bool:
        return instrument_id in self._policies

    def session_window(
        self,
        instrument_id: str,
        timestamp: datetime,
    ) -> tuple[datetime, datetime]:
        timestamp = require_utc(timestamp)
        policy = self._policy(instrument_id)
        if policy.session_profile == SessionProfile.CONTINUOUS:
            open_ts = datetime.combine(timestamp.date(), time.min, UTC)
            return open_ts, open_ts + timedelta(days=1)
        windows = self._session_bounds(
            policy.calendar_id,
            policy.session_profile,
            (timestamp - _SCHEDULE_PADDING).date(),
            (timestamp + _SCHEDULE_PADDING).date(),
        )
        for window in windows:
            if window.open_ts <= timestamp < window.close_ts:
                return window.open_ts, window.close_ts
        raise RecoveryPlanningError(
            f"timestamp {timestamp.isoformat()} is outside a configured session "
            f"for instrument {instrument_id!r}"
        )

    def _schedule_windows(
        self,
        calendar_id: str,
        session_profile: SessionProfile,
        start_date: date,
        end_date: date,
    ) -> tuple[SessionWindow, ...]:
        key = (calendar_id, session_profile, start_date, end_date)
        with self._cache_lock:
            cached = self._schedule_cache.get(key)
            if cached is not None:
                self._schedule_cache.move_to_end(key)
                return cached
        calendar = _load_calendar(calendar_id)
        start_name, end_name = _market_time_range(calendar, session_profile)
        schedule = calendar.schedule(
            start_date=start_date,
            end_date=end_date,
            tz="UTC",
            start=start_name,
            end=end_name,
            interruptions=True,
        )
        windows: list[SessionWindow] = []
        for _, row in schedule.iterrows():
            open_ts = _utc_datetime(row[start_name])
            close_ts = _utc_datetime(row[end_name])
            exclusions = _exclusions(row, schedule.columns)
            windows.extend(_subtract_exclusions(open_ts, close_ts, exclusions))
        result = tuple(sorted(windows, key=lambda item: item.open_ts))
        with self._cache_lock:
            self._schedule_cache[key] = result
            self._schedule_cache.move_to_end(key)
            while len(self._schedule_cache) > self._maximum_cached_schedules:
                self._schedule_cache.popitem(last=False)
        return result

    def _session_bounds(
        self,
        calendar_id: str,
        session_profile: SessionProfile,
        start_date: date,
        end_date: date,
    ) -> tuple[SessionWindow, ...]:
        key = (calendar_id, session_profile, start_date, end_date)
        with self._cache_lock:
            cached = self._session_cache.get(key)
            if cached is not None:
                self._session_cache.move_to_end(key)
                return cached
        calendar = _load_calendar(calendar_id)
        start_name, end_name = _market_time_range(calendar, session_profile)
        schedule = calendar.schedule(
            start_date=start_date,
            end_date=end_date,
            tz="UTC",
            start=start_name,
            end=end_name,
            interruptions=True,
        )
        result = tuple(
            SessionWindow(
                open_ts=_utc_datetime(row[start_name]),
                close_ts=_utc_datetime(row[end_name]),
            )
            for _, row in schedule.iterrows()
        )
        with self._cache_lock:
            self._session_cache[key] = result
            self._session_cache.move_to_end(key)
            while len(self._session_cache) > self._maximum_cached_schedules:
                self._session_cache.popitem(last=False)
        return result

    def _policy(self, instrument_id: str) -> InstrumentCalendarPolicy:
        try:
            return self._policies[instrument_id]
        except KeyError as exc:
            raise RecoveryPlanningError(
                f"session calendar is not configured for instrument {instrument_id!r}"
            ) from exc

    @staticmethod
    def _validate_policy(policy: InstrumentCalendarPolicy) -> None:
        is_continuous = policy.session_profile == SessionProfile.CONTINUOUS
        if (policy.calendar_id == "24/7") != is_continuous:
            raise ValueError("24/7 calendar and continuous session profile must be used together")
        if not is_continuous:
            _load_calendar(policy.calendar_id)


def _load_calendar(calendar_id: str) -> Any:
    try:
        return market_calendars.get_calendar(calendar_id)
    except RuntimeError as exc:
        raise ValueError(f"unknown pandas market calendar {calendar_id!r}") from exc


def _market_time_range(calendar: Any, profile: SessionProfile) -> tuple[str, str]:
    available = calendar.regular_market_times
    if profile == SessionProfile.FULL and "pre" in available and "post" in available:
        return "pre", "post"
    return "market_open", "market_close"


def _exclusions(row: Any, columns: Any) -> tuple[tuple[datetime, datetime], ...]:
    pairs = [("break_start", "break_end")]
    pairs.extend(
        (column, column.replace("interruption_start_", "interruption_end_"))
        for column in columns
        if str(column).startswith("interruption_start_")
    )
    exclusions: list[tuple[datetime, datetime]] = []
    for start_name, end_name in pairs:
        if start_name not in row or end_name not in row:
            continue
        start_value = row[start_name]
        end_value = row[end_name]
        if isna(start_value) or isna(end_value):
            continue
        start_ts = _utc_datetime(start_value)
        end_ts = _utc_datetime(end_value)
        if end_ts > start_ts:
            exclusions.append((start_ts, end_ts))
    return tuple(sorted(exclusions))


def _subtract_exclusions(
    open_ts: datetime,
    close_ts: datetime,
    exclusions: Sequence[tuple[datetime, datetime]],
) -> tuple[SessionWindow, ...]:
    cursor = open_ts
    windows: list[SessionWindow] = []
    for exclusion_start, exclusion_end in exclusions:
        exclusion_start = max(exclusion_start, open_ts)
        exclusion_end = min(exclusion_end, close_ts)
        if exclusion_end <= cursor:
            continue
        if exclusion_start > cursor:
            windows.append(SessionWindow(open_ts=cursor, close_ts=exclusion_start))
        cursor = max(cursor, exclusion_end)
    if cursor < close_ts:
        windows.append(SessionWindow(open_ts=cursor, close_ts=close_ts))
    return tuple(windows)


def _minute_range(start_ts: datetime, end_ts: datetime) -> tuple[datetime, ...]:
    cursor = _ceil_minute(start_ts)
    expected: list[datetime] = []
    while cursor < end_ts:
        expected.append(cursor)
        cursor += _MINUTE
    return tuple(expected)


def _ceil_minute(value: datetime) -> datetime:
    if value.second == 0 and value.microsecond == 0:
        return value
    return value.replace(second=0, microsecond=0) + _MINUTE


def _utc_datetime(value: Any) -> datetime:
    converted = value.to_pydatetime()
    if converted.tzinfo is None:
        raise ValueError("market calendar returned a naive timestamp")
    return converted.astimezone(UTC)
