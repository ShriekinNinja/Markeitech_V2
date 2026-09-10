"""Acquisition-owned minute projections from immutable close-stamped five-second inputs."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

MINUTE_CANDLES_TYPE_NAME = "markeitech.acquisition.minute_candles.v1"
_SECOND = 1_000_000_000
_MINUTE = 60 * _SECOND
_SOURCE_INTERVAL = 5 * _SECOND
_FIELDS = ("open", "high", "low", "close", "volume")


@dataclass(frozen=True, slots=True)
class MinuteCandle:
    """Derived UTC minute with exact decimal strings and observed constituent coverage.

    ``time`` labels the opening second; ``ts_event_ns`` is the closing boundary.
    COMPLETE means all twelve unique five-second constituents were observed. INCOMPLETE
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


@dataclass(frozen=True, slots=True)
class MinuteCandleUpdate:
    """Detached acquisition projection; UTC nanoseconds retain native source identity.

    Candles are transient derived evidence, not provider minute bars. Conflict counts
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

    def snapshot(self, instrument: str, received_ns: int) -> MinuteCandleUpdate:
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
        return MinuteCandleUpdate(
            instrument,
            tuple(candles),
            self._conflicts[instrument],
            self._rejected[instrument],
            self._latest[instrument],
            received_ns,
        )
