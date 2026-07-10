from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from markeitech.domain.base import (
    VersionedDomainModel,
    require_utc,
    unix_ns_from_utc_datetime,
)
from markeitech.domain.market_data import (
    CanonicalQuoteTick,
    CanonicalTradeTick,
    OneMinuteBar,
)
from markeitech.domain.state import (
    GapSeverity,
    GapState,
    ReadinessStatus,
    SourceHealth,
    SourceStatus,
)


class MarketDataStreamKind(StrEnum):
    TRADE_TICK = "trade_tick"
    QUOTE_TICK = "quote_tick"
    BAR_1M = "bar_1m"


class MarketDataStreamStatus(StrEnum):
    WAITING = "waiting"
    HEALTHY = "healthy"
    STALE = "stale"
    PAUSED = "paused"


class MarketDataStreamHealth(VersionedDomainModel):
    kind: MarketDataStreamKind
    status: MarketDataStreamStatus
    last_event_ts: datetime | None = None
    last_received_ts: datetime | None = None
    stale_after_seconds: int = Field(ge=1)
    reason: str | None = None

    @field_validator("last_event_ts", "last_received_ts")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @model_validator(mode="after")
    def _reason_must_match_status(self) -> MarketDataStreamHealth:
        if (
            self.status
            in {
                MarketDataStreamStatus.WAITING,
                MarketDataStreamStatus.STALE,
            }
            and self.reason is None
        ):
            raise ValueError("waiting or stale stream health requires a reason")
        if (
            self.status
            in {
                MarketDataStreamStatus.HEALTHY,
                MarketDataStreamStatus.PAUSED,
            }
            and self.reason is not None
        ):
            raise ValueError("healthy or paused stream health cannot carry a reason")
        return self


class InstrumentMarketDataHealth(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    is_active: bool
    readiness: ReadinessStatus
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)
    streams: tuple[MarketDataStreamHealth, ...]
    gap: GapState
    updated_ts: datetime

    @field_validator("updated_ts")
    @classmethod
    def _updated_ts_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _reasons_must_match_readiness(self) -> InstrumentMarketDataHealth:
        if self.readiness == ReadinessStatus.READY and self.reason_codes:
            raise ValueError("ready instrument health cannot carry reason codes")
        if self.readiness != ReadinessStatus.READY and not self.reason_codes:
            raise ValueError("non-ready instrument health requires reason codes")
        return self


class MarketDataHealthSnapshot(VersionedDomainModel):
    source: SourceHealth
    instruments: tuple[InstrumentMarketDataHealth, ...]


@dataclass(frozen=True)
class MarketDataHealthPolicy:
    tick_stale_after: timedelta = timedelta(seconds=30)
    bar_stale_after: timedelta = timedelta(seconds=90)

    def __post_init__(self) -> None:
        if self.tick_stale_after < timedelta(seconds=1):
            raise ValueError("tick stale threshold must be at least one second")
        if self.bar_stale_after < timedelta(seconds=1):
            raise ValueError("bar stale threshold must be at least one second")


type SessionOpenResolver = Callable[[str, datetime], bool]
type MarketDataHealthSink = Callable[[MarketDataHealthSnapshot], None]


class MarketDataHealthMonitor:
    def __init__(
        self,
        *,
        instrument_ids: set[str],
        active_instrument_id: Callable[[], str],
        now: Callable[[], datetime],
        is_session_open: SessionOpenResolver,
        policy: MarketDataHealthPolicy | None = None,
        on_change: MarketDataHealthSink | None = None,
        source_name: str = "ib",
    ) -> None:
        if not instrument_ids:
            raise ValueError("market-data health monitor requires configured instruments")
        self._instrument_ids = frozenset(instrument_ids)
        self._active_instrument_id = active_instrument_id
        self._now = now
        self._is_session_open = is_session_open
        self._policy = policy or MarketDataHealthPolicy()
        self._on_change = on_change
        self._source_name = source_name
        self._last_event: dict[tuple[str, MarketDataStreamKind], datetime] = {}
        self._last_received: dict[tuple[str, MarketDataStreamKind], datetime] = {}
        self._last_bar_open_ns: dict[str, int] = {}
        self._missing_bar_opens: dict[str, set[int]] = {
            instrument_id: set() for instrument_id in instrument_ids
        }
        self._gap_opened_ts: dict[str, datetime] = {}
        self._current: MarketDataHealthSnapshot | None = None
        self._last_signature: tuple[object, ...] | None = None

    @property
    def current(self) -> MarketDataHealthSnapshot:
        return self.evaluate()

    def observe(self, event: object) -> MarketDataHealthSnapshot:
        stream_kind = _stream_kind(event)
        if stream_kind is None:
            return self.evaluate()
        instrument_id = event.instrument_id
        self._require_instrument(instrument_id)
        received_ts = require_utc(self._now())
        key = (instrument_id, stream_kind)
        previous_event_ts = self._last_event.get(key)
        if previous_event_ts is None or event.event_ts >= previous_event_ts:
            self._last_event[key] = event.event_ts
            self._last_received[key] = received_ts
        if stream_kind == MarketDataStreamKind.BAR_1M:
            self._observe_bar(event, received_ts)
        return self.evaluate(received_ts)

    def evaluate(self, now: datetime | None = None) -> MarketDataHealthSnapshot:
        checked_at = require_utc(now or self._now())
        instruments = tuple(
            self._instrument_health(instrument_id, checked_at)
            for instrument_id in sorted(self._instrument_ids)
        )
        snapshot = MarketDataHealthSnapshot(
            source=self._source_health(instruments, checked_at),
            instruments=instruments,
        )
        signature = _health_signature(snapshot)
        self._current = snapshot
        if signature != self._last_signature:
            self._last_signature = signature
            if self._on_change is not None:
                self._on_change(snapshot)
        return snapshot

    def _instrument_health(
        self,
        instrument_id: str,
        checked_at: datetime,
    ) -> InstrumentMarketDataHealth:
        is_active = instrument_id == self._active_instrument_id()
        session_open = self._is_session_open(instrument_id, checked_at)
        required = (
            (
                MarketDataStreamKind.TRADE_TICK,
                MarketDataStreamKind.QUOTE_TICK,
                MarketDataStreamKind.BAR_1M,
            )
            if is_active
            else (MarketDataStreamKind.BAR_1M,)
        )
        streams = tuple(
            self._stream_health(instrument_id, kind, checked_at, session_open) for kind in required
        )
        gap = self._gap_state(instrument_id, checked_at)
        reasons = tuple(stream.reason for stream in streams if stream.reason is not None)
        if gap.severity != GapSeverity.NONE:
            reasons = (*reasons, *gap.reason_codes)
        readiness = ReadinessStatus.READY if not reasons else ReadinessStatus.DEGRADED
        if any(stream.status == MarketDataStreamStatus.WAITING for stream in streams):
            readiness = ReadinessStatus.NOT_READY
        return InstrumentMarketDataHealth(
            instrument_id=instrument_id,
            is_active=is_active,
            readiness=readiness,
            reason_codes=tuple(dict.fromkeys(reasons)),
            streams=streams,
            gap=gap,
            updated_ts=checked_at,
        )

    def _stream_health(
        self,
        instrument_id: str,
        kind: MarketDataStreamKind,
        checked_at: datetime,
        session_open: bool,
    ) -> MarketDataStreamHealth:
        threshold = self._threshold(kind)
        key = (instrument_id, kind)
        last_event = self._last_event.get(key)
        last_received = self._last_received.get(key)
        if not session_open:
            status = MarketDataStreamStatus.PAUSED
            reason = None
        elif last_received is None:
            status = MarketDataStreamStatus.WAITING
            reason = f"waiting_for_{kind.value}"
        elif checked_at - last_received > threshold:
            status = MarketDataStreamStatus.STALE
            reason = f"stale_{kind.value}"
        else:
            status = MarketDataStreamStatus.HEALTHY
            reason = None
        return MarketDataStreamHealth(
            kind=kind,
            status=status,
            last_event_ts=last_event,
            last_received_ts=last_received,
            stale_after_seconds=int(threshold.total_seconds()),
            reason=reason,
        )

    def _source_health(
        self,
        instruments: tuple[InstrumentMarketDataHealth, ...],
        checked_at: datetime,
    ) -> SourceHealth:
        last_events = [event_ts for event_ts in self._last_event.values()]
        last_event_ts = max(last_events) if last_events else None
        reasons = tuple(
            dict.fromkeys(
                reason for instrument in instruments for reason in instrument.reason_codes
            )
        )
        if last_event_ts is None:
            status = SourceStatus.CONNECTING
        elif reasons:
            status = SourceStatus.DEGRADED
        else:
            status = SourceStatus.HEALTHY
        lag_ms = None
        if last_event_ts is not None:
            lag_ms = max(0, int((checked_at - last_event_ts).total_seconds() * 1000))
        return SourceHealth(
            source=self._source_name,
            status=status,
            last_event_ts=last_event_ts,
            lag_ms=lag_ms,
            reason_codes=reasons,
            updated_ts=checked_at,
        )

    def _observe_bar(self, bar: OneMinuteBar, received_ts: datetime) -> None:
        open_ns = _bar_open_ns(bar)
        instrument_id = bar.instrument_id
        missing = self._missing_bar_opens[instrument_id]
        missing.discard(open_ns)
        previous = self._last_bar_open_ns.get(instrument_id)
        if previous is not None and open_ns > previous + 60_000_000_000:
            missing.update(range(previous + 60_000_000_000, open_ns, 60_000_000_000))
            self._gap_opened_ts.setdefault(instrument_id, received_ts)
        self._last_bar_open_ns[instrument_id] = max(previous or open_ns, open_ns)
        if not missing:
            self._gap_opened_ts.pop(instrument_id, None)

    def _gap_state(self, instrument_id: str, checked_at: datetime) -> GapState:
        missing = len(self._missing_bar_opens[instrument_id])
        if missing == 0:
            return GapState(
                instrument_id=instrument_id,
                severity=GapSeverity.NONE,
                updated_ts=checked_at,
            )
        if missing == 1:
            severity = GapSeverity.WARNING
        elif missing < 5:
            severity = GapSeverity.DEGRADED
        else:
            severity = GapSeverity.CRITICAL
        return GapState(
            instrument_id=instrument_id,
            severity=severity,
            open_ts=self._gap_opened_ts[instrument_id],
            missing_intervals=missing,
            reason_codes=("missing_1m_bars",),
            updated_ts=checked_at,
        )

    def _threshold(self, kind: MarketDataStreamKind) -> timedelta:
        if kind == MarketDataStreamKind.BAR_1M:
            return self._policy.bar_stale_after
        return self._policy.tick_stale_after

    def _require_instrument(self, instrument_id: str) -> None:
        if instrument_id not in self._instrument_ids:
            raise ValueError(f"health event references unconfigured instrument {instrument_id!r}")


def _stream_kind(event: object) -> MarketDataStreamKind | None:
    if isinstance(event, CanonicalTradeTick):
        return MarketDataStreamKind.TRADE_TICK
    if isinstance(event, CanonicalQuoteTick):
        return MarketDataStreamKind.QUOTE_TICK
    if isinstance(event, OneMinuteBar) and event.is_complete and event.source == "ib":
        return MarketDataStreamKind.BAR_1M
    return None


def _bar_open_ns(bar: OneMinuteBar) -> int:
    if bar.event_ts_ns is not None:
        return bar.event_ts_ns - 60_000_000_000
    return unix_ns_from_utc_datetime(bar.open_ts)


def _health_signature(snapshot: MarketDataHealthSnapshot) -> tuple[object, ...]:
    return (
        snapshot.source.status,
        snapshot.source.reason_codes,
        *(
            (
                instrument.instrument_id,
                instrument.is_active,
                instrument.readiness,
                instrument.reason_codes,
                instrument.gap.severity,
                instrument.gap.missing_intervals,
                tuple((stream.kind, stream.status) for stream in instrument.streams),
            )
            for instrument in snapshot.instruments
        ),
    )
