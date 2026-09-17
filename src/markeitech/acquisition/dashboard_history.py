"""Bounded operator history requests, detached from web and native runtime mechanics."""

from dataclasses import dataclass, replace
from decimal import Decimal
from uuid import UUID

from markeitech.acquisition import HistoricalDependencyDemandEvent
from markeitech.acquisition.historical import HistoricalRequest
from markeitech.acquisition.minute_candles import (
    INTRADAY_TIMEFRAMES,
    MinuteCandle,
)

HISTORY_PAGE_TYPE_NAME = "markeitech.acquisition.dashboard_history.v1"
HISTORY_CONSUMER_PREFIX = "DASHBOARD-HISTORY:"


def scope_history_page_execution(
    request: HistoricalRequest, event: HistoricalDependencyDemandEvent
) -> HistoricalRequest:
    """Give an operator re-fetch its own execution ID while retaining retry identity.

    The generic compiler identifies logical provider windows. Its executor forbids
    re-enqueueing terminal IDs. A new explicit operator intent can fetch that window
    again; redelivery of the same intent still resolves to the same execution ID.
    Native bounds, selector, parameters and constituent lineage remain unchanged.
    """
    if event.capability_id not in {
        "dashboard.history-page",
        *(f"dashboard.history-page.{frame}" for frame in INTRADAY_TIMEFRAMES),
    }:
        return request
    token = event.consumer_id.removeprefix(HISTORY_CONSUMER_PREFIX)
    if not event.consumer_id.startswith(HISTORY_CONSUMER_PREFIX) or str(UUID(token)) != token:
        raise ValueError("invalid history page execution identity")
    return replace(request, request_id=f"{request.request_id}:page:{token}")


@dataclass(frozen=True, slots=True)
class DashboardHistoryRequest:
    """Request a half-open UTC timeframe-aligned window in whole Unix seconds."""

    request_id: str
    instrument_id: str
    start: int
    end: int
    timeframe: str = "1m"

    def __post_init__(self) -> None:
        if self.timeframe not in INTRADAY_TIMEFRAMES:
            raise ValueError("unsupported history timeframe")
        if str(UUID(self.request_id)) != self.request_id:
            raise ValueError("invalid history request identity")
        if not isinstance(self.instrument_id, str) or not 1 <= len(self.instrument_id) <= 128:
            raise ValueError("invalid history instrument")
        interval = INTRADAY_TIMEFRAMES[self.timeframe]
        if any(type(v) is not int or v <= 0 or v % interval for v in (self.start, self.end)):
            raise ValueError("history bounds must be positive UTC timeframe boundaries")
        if not 1 <= (self.end - self.start) // interval <= 1000:
            raise ValueError("history page must span 1..1000 selected candles")

    @property
    def selector(self) -> str:
        """Return the native provider selector for completed selected candles."""
        unit = (
            "1-HOUR"
            if self.timeframe == "1h"
            else f"{INTRADAY_TIMEFRAMES[self.timeframe] // 60}-MINUTE"
        )
        return f"{unit}-LAST-EXTERNAL"

    @property
    def consumer_id(self) -> str:
        """Return unique request correlation retained by the native historical executor."""
        return HISTORY_CONSUMER_PREFIX + self.request_id

    def demand(self) -> HistoricalDependencyDemandEvent:
        """Use the native recent-completed resolver anchored at the chosen past end."""
        return HistoricalDependencyDemandEvent(
            demand_id=self.consumer_id,
            consumer_id=self.consumer_id,
            capability_id=(
                "dashboard.history-page"
                if self.timeframe == "1m"
                else f"dashboard.history-page.{self.timeframe}"
            ),
            capability_version=1,
            instrument_id=self.instrument_id,
            selector=self.selector,
            window="recent_completed",
            minimum_observations=1,
            maximum_observations=(self.end - self.start) // INTRADAY_TIMEFRAMES[self.timeframe],
            priority=40,
            purpose="operator chart history page",
            as_of_ns=self.end * 1_000_000_000,
        )


@dataclass(frozen=True, slots=True)
class DashboardHistoryPage:
    """Acquisition-produced intraday page; missing provider intervals remain absent."""

    request_id: str
    instrument_id: str
    start: int
    end: int
    candles: tuple[MinuteCandle, ...]
    conflicts: int
    rejected_inputs: int
    ts_event: int
    ts_init: int
    source: str = "DATA-ACQUISITION"
    schema_version: int = 1
    timeframe: str = "1m"
    status: str = "COMPLETED"
    detail: str | None = None


def project_history_page(batch, consumer_id: str, received_ns: int) -> DashboardHistoryPage:  # noqa: ANN001
    """Project completed native bars inside acquisition, retaining provider OHLCV and lineage."""
    request = batch.request
    start, end = request.start_ns // 1_000_000_000, (request.end_ns + 1) // 1_000_000_000
    capability = next(
        ref.capability_id for ref in request.dependencies if ref.consumer_id == consumer_id
    )
    timeframe = capability.removeprefix("dashboard.history-page.")
    if capability == "dashboard.history-page":
        timeframe = "1m"
    page = DashboardHistoryRequest(
        consumer_id.removeprefix(HISTORY_CONSUMER_PREFIX),
        request.instrument_id,
        start,
        end,
        timeframe,
    )
    if request.selector != page.selector:
        raise ValueError("history selector does not match timeframe")
    interval = INTRADAY_TIMEFRAMES[timeframe]
    candles = []
    for bar in batch.observations:
        if not request.start_ns < bar.ts_event <= request.end_ns + 1:
            continue
        if str(bar.bar_type) != f"{page.instrument_id}-{page.selector}":
            raise ValueError("history bar identity mismatch")
        if bar.ts_event % (interval * 1_000_000_000):
            raise ValueError("provider history is not aligned with the live timeframe")
        values = [
            Decimal(str(getattr(bar, field)))
            for field in ("open", "high", "low", "close", "volume")
        ]
        if (
            not all(v.is_finite() for v in values)
            or values[4] < 0
            or values[2] > min(values[0], values[3])
            or values[1] < max(values[0], values[3])
        ):
            raise ValueError("invalid historical OHLCV")
        candles.append(
            MinuteCandle(
                time=bar.ts_event // 1_000_000_000 - interval,
                ts_event_ns=str(bar.ts_event),
                ts_init_ns=str(bar.ts_init),
                open=str(bar.open),
                high=str(bar.high),
                low=str(bar.low),
                close=str(bar.close),
                volume=str(bar.volume),
                status="COMPLETE",
                input_count=1,
                historical_inputs=1,
                live_inputs=0,
                selector=page.selector,
                provenance="provider_history",
            )
        )
    return DashboardHistoryPage(
        page.request_id,
        page.instrument_id,
        start,
        end,
        tuple(candles),
        0,
        0,
        max((int(c.ts_event_ns) for c in candles), default=0),
        received_ns,
        timeframe=timeframe,
    )
