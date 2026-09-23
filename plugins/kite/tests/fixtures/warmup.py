"""Synthetic review input for an accepted rolling mean contract.

Contract: period completed observations are required for readiness. Before readiness,
value is unavailable. Once ready, average exactly the latest period observations.
The intended consumer asks for the current mean. The supplied provider prices have
no event or receive timestamps; their freshness and session coverage are unknown.
"""

from collections import deque


class Mean:
    def __init__(self, period: int = 4) -> None:
        if period < 1:
            raise ValueError("period must be positive")
        self.period = period
        self.values: deque[float] = deque(maxlen=period)

    def update(self, value: float) -> None:
        self.values.append(value)

    @property
    def ready(self) -> bool:
        return len(self.values) >= 2

    @property
    def value(self) -> float | None:
        return sum(self.values) / len(self.values) if self.ready else None


SUPPLIED_PRICES = (100.0, 102.0, 104.0)
