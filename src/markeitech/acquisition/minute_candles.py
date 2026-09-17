"""Acquisition-owned minute projections from immutable close-stamped five-second inputs."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation

MINUTE_CANDLES_TYPE_NAME = "markeitech.acquisition.minute_candles.v1"
_SECOND = 1_000_000_000
_MINUTE = 60 * _SECOND
_SOURCE_INTERVAL = 5 * _SECOND
# Protocol-supported clock-aligned intraday intervals; session intervals are separate.
INTRADAY_TIMEFRAMES = {"1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600}
_FIELDS = ("open", "high", "low", "close", "volume")


@dataclass(frozen=True, slots=True)
class MinuteCandle:
    """UTC intraday candle with exact decimals and explicit source provenance.

    ``time`` labels the opening second; ``ts_event_ns`` is the closing boundary.
    For derived_5s, COMPLETE means every expected five-second constituent was observed.
    For provider_history, COMPLETE means one completed native bar was received; input
    counts refer to that native selector and do not claim five-second coverage. INCOMPLETE
    means the source has reached/passed the close with missing constituents. FORMING
    means the latest source has not reached the close. History can repair incomplete
    projections; native observations are never rewritten.
    """

    time: int
    ts_event_ns: str
    ts_init_ns: str
    open: str
    high: str
    low: str
    close: str
    volume: str
    status: str
    input_count: int
    historical_inputs: int
    live_inputs: int
    selector: str = "5-SECOND-LAST-EXTERNAL"
    provenance: str = "derived_5s"


@dataclass(frozen=True, slots=True)
class MinuteCandleUpdate:
    """Detached acquisition projection; UTC nanoseconds retain native source identity.

    Candles are transient derived evidence, not provider-aggregated bars. Conflict counts
    expose differing observations at an identical source timestamp; live wins over
    historical overlap, and conflicting same-origin duplicates retain the first value.
    """

    instrument_id: str
    candles: tuple[MinuteCandle, ...]
    conflicts: int
    rejected_inputs: int
    ts_event: int
    ts_init: int
    source: str = "DATA-ACQUISITION"
    provider: str = "IB"
    selector: str = "5-SECOND-LAST-EXTERNAL"
    schema_version: int = 1
    timeframe: str = "1m"


@dataclass(frozen=True, slots=True)
class _Input:
    values: tuple[Decimal, ...]
    historical: bool
    ts_init: int


class _MinuteCandleBook:
    """Bound event-time buckets; never close a candle using the wall clock."""

    def __init__(self, instruments: set[str], capacity: int) -> None:
        if not 2 <= capacity <= 5000:
            raise ValueError("minute candle capacity must be 2..5000")
        self.capacity = capacity
        self._buckets: dict[str, dict[int, dict[int, _Input]]] = {i: {} for i in instruments}
        self._latest = dict.fromkeys(instruments, 0)
        self._conflicts = dict.fromkeys(instruments, 0)
        self._rejected = dict.fromkeys(instruments, 0)

    def observe(self, bar, *, historical: bool = False) -> bool:  # noqa: ANN001
        instrument = str(bar.bar_type.instrument_id)
        if instrument not in self._buckets:
            return False
        if str(bar.bar_type) != f"{instrument}-5-SECOND-LAST-EXTERNAL":
            return False
        timestamp = bar.ts_event
        try:
            values = tuple(Decimal(str(getattr(bar, key))) for key in _FIELDS)
            valid = all(v.is_finite() for v in values)
            valid = valid and values[2] <= min(values[0], values[3])
            valid = valid and values[1] >= max(values[0], values[3]) and values[4] >= 0
        except (InvalidOperation, ValueError):
            valid = False
        if not valid or timestamp <= 0 or timestamp % _SOURCE_INTERVAL:
            self._rejected[instrument] += 1
            return True
        # IB source timestamps denote the close: :00 belongs to the previous minute.
        end = ((timestamp - 1) // _MINUTE + 1) * _MINUTE
        buckets = self._buckets[instrument]
        if len(buckets) >= self.capacity and end < min(buckets):
            return False  # Older than retained history: cannot evict newer observations.
        bucket = buckets.setdefault(end, {})
        incoming = _Input(values, historical, bar.ts_init)
        existing = bucket.get(timestamp)
        if existing is not None:
            different = existing.values != values
            if different:
                self._conflicts[instrument] += 1
            if not existing.historical or historical:
                return different
            # Prefer live lineage, even when values agree; never sum an overlap twice.
        bucket[timestamp] = incoming
        self._latest[instrument] = max(self._latest[instrument], timestamp)
        while len(buckets) > self.capacity:
            del buckets[min(buckets)]
        return True

    def _snapshots(self, instrument: str, received_ns: int) -> tuple[MinuteCandleUpdate, ...]:
        minute = self.snapshot(instrument, received_ns)
        return (
            minute,
            *(
                replace(
                    minute,
                    timeframe=frame,
                    candles=tuple(_rollup(list(minute.candles), seconds, minute.ts_event)),
                )
                for frame, seconds in INTRADAY_TIMEFRAMES.items()
                if frame != "1m"
            ),
        )

    def snapshot(
        self, instrument: str, received_ns: int, timeframe: str = "1m"
    ) -> MinuteCandleUpdate:
        if timeframe not in INTRADAY_TIMEFRAMES:
            raise ValueError("unsupported intraday timeframe")
        candles = []
        for end, inputs in sorted(self._buckets[instrument].items()):
            ordered = [value for _, value in sorted(inputs.items())]
            count = len(ordered)
            status = (
                "COMPLETE"
                if count == 12
                else "INCOMPLETE"
                if self._latest[instrument] >= end
                else "FORMING"
            )
            candles.append(
                MinuteCandle(
                    time=(end - _MINUTE) // _SECOND,
                    ts_event_ns=str(end),
                    ts_init_ns=str(max(v.ts_init for v in ordered)),
                    open=str(ordered[0].values[0]),
                    high=str(max(v.values[1] for v in ordered)),
                    low=str(min(v.values[2] for v in ordered)),
                    close=str(ordered[-1].values[3]),
                    volume=str(sum(v.values[4] for v in ordered)),
                    status=status,
                    input_count=count,
                    historical_inputs=sum(v.historical for v in ordered),
                    live_inputs=sum(not v.historical for v in ordered),
                )
            )
        if timeframe != "1m":
            candles = _rollup(candles, INTRADAY_TIMEFRAMES[timeframe], self._latest[instrument])
        return MinuteCandleUpdate(
            instrument,
            tuple(candles),
            self._conflicts[instrument],
            self._rejected[instrument],
            self._latest[instrument],
            received_ns,
            timeframe=timeframe,
        )


def _rollup(candles: list[MinuteCandle], seconds: int, latest_ns: int) -> list[MinuteCandle]:
    """Compose disjoint minute constituents without filling missing source intervals."""
    groups: dict[int, list[MinuteCandle]] = {}
    for candle in candles:
        start = candle.time // seconds * seconds
        groups.setdefault(start, []).append(candle)
    result = []
    for start, group in sorted(groups.items()):
        count = sum(c.input_count for c in group)
        end_ns = (start + seconds) * _SECOND
        result.append(
            replace(
                group[0],
                time=start,
                ts_event_ns=str(end_ns),
                ts_init_ns=str(max(int(c.ts_init_ns) for c in group)),
                high=str(max(Decimal(c.high) for c in group)),
                low=str(min(Decimal(c.low) for c in group)),
                close=group[-1].close,
                volume=str(sum(Decimal(c.volume) for c in group)),
                status="COMPLETE"
                if count == seconds // 5
                else ("INCOMPLETE" if latest_ns >= end_ns else "FORMING"),
                input_count=count,
                historical_inputs=sum(c.historical_inputs for c in group),
                live_inputs=sum(c.live_inputs for c in group),
            )
        )
    return result
