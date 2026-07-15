from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from threading import Lock

from markeitech.domain.base import require_utc
from markeitech.domain.market_data import OneMinuteBar

_AGGRESSION_SOURCES = frozenset({"classified_ticks", "ib"})


@dataclass(frozen=True)
class AggressionObservationStoreSnapshot:
    stream_count: int
    retained_bar_count: int
    accepted_bar_count: int
    duplicate_bar_count: int
    evicted_bar_count: int
    conflicting_retry_count: int


class BoundedAggressionObservationStore:
    """Retains a bounded committed-bar tail for live confirmation windows."""

    def __init__(self, max_bars_per_stream: int) -> None:
        if max_bars_per_stream < 1:
            raise ValueError("aggression observation history must be positive")
        self._max_bars_per_stream = max_bars_per_stream
        self._streams: dict[tuple[str, str], dict[datetime, OneMinuteBar]] = {}
        self._accepted_bar_count = 0
        self._duplicate_bar_count = 0
        self._evicted_bar_count = 0
        self._conflicting_retry_count = 0
        self._lock = Lock()

    @property
    def snapshot(self) -> AggressionObservationStoreSnapshot:
        with self._lock:
            return AggressionObservationStoreSnapshot(
                stream_count=len(self._streams),
                retained_bar_count=sum(len(values) for values in self._streams.values()),
                accepted_bar_count=self._accepted_bar_count,
                duplicate_bar_count=self._duplicate_bar_count,
                evicted_bar_count=self._evicted_bar_count,
                conflicting_retry_count=self._conflicting_retry_count,
            )

    def offer_committed(self, events: Sequence[object]) -> bool:
        bars = tuple(
            event
            for event in events
            if isinstance(event, OneMinuteBar)
            and event.source in _AGGRESSION_SOURCES
            and event.is_complete
            and not event.is_revision
        )
        with self._lock:
            for bar in bars:
                key = (bar.instrument_id, bar.source)
                stream = self._streams.setdefault(key, {})
                existing = stream.get(bar.open_ts)
                if existing is not None:
                    if not _same_market_observation(existing, bar):
                        self._conflicting_retry_count += 1
                    else:
                        self._duplicate_bar_count += 1
                    continue
                stream[bar.open_ts] = bar
                self._accepted_bar_count += 1
                while len(stream) > self._max_bars_per_stream:
                    oldest = min(stream)
                    del stream[oldest]
                    self._evicted_bar_count += 1
        return True

    def bars(
        self,
        instrument_id: str,
        source: str,
        *,
        through_ts: datetime | None = None,
    ) -> tuple[OneMinuteBar, ...]:
        if source not in _AGGRESSION_SOURCES:
            raise ValueError(f"unsupported aggression observation source {source!r}")
        if through_ts is not None:
            through_ts = require_utc(through_ts)
        with self._lock:
            values = tuple(
                bar
                for _, bar in sorted(self._streams.get((instrument_id, source), {}).items())
                if through_ts is None or bar.close_ts <= through_ts
            )
        return values


def _same_market_observation(left: OneMinuteBar, right: OneMinuteBar) -> bool:
    transport_fields = {"ts_init", "ts_init_ns"}
    return left.model_dump(exclude=transport_fields) == right.model_dump(exclude=transport_fields)
