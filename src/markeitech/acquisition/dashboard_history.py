"""Bounded operator history requests, detached from web and native runtime mechanics."""

from dataclasses import dataclass, replace
from decimal import Decimal
from uuid import UUID

from markeitech.acquisition import HistoricalDependencyDemandEvent
from markeitech.acquisition.historical import HistoricalRequest
from markeitech.acquisition.minute_candles import (
    CHART_TIMEFRAMES,
    MinuteCandle,
)

HISTORY_PAGE_TYPE_NAME = "markeitech.acquisition.dashboard_history.v1"
HISTORY_CONSUMER_PREFIX = "DASHBOARD-HISTORY:"


def _chart_selector(timeframe: str) -> str:
    seconds = CHART_TIMEFRAMES[timeframe]
    unit = (
        "1-DAY"
        if timeframe == "1d"
        else f"{seconds // 3600}-HOUR"
        if seconds >= 3600
        else f"{seconds // 60}-MINUTE"
    )
    return f"{unit}-LAST-EXTERNAL"


def _provider_candle(bar, timeframe: str, *, historical: bool) -> MinuteCandle:
    values = [
        Decimal(str(getattr(bar, field))) for field in ("open", "high", "low", "close", "volume")
    ]
    if (
        not all(v.is_finite() for v in values)
        or values[4] < 0
        or values[2] > min(values[0], values[3])
        or values[1] < max(values[0], values[3])
    ):
        raise ValueError("invalid provider OHLCV")
    return MinuteCandle(
        time=(bar.ts_event + (1 if timeframe == "1d" else 0)) // 1_000_000_000
        - CHART_TIMEFRAMES[timeframe],
        ts_event_ns=str(bar.ts_event),
        ts_init_ns=str(bar.ts_init),
        **{field: str(getattr(bar, field)) for field in ("open", "high", "low", "close", "volume")},
        status="COMPLETE" if historical else "UPDATING",
        input_count=1,
        historical_inputs=int(historical),
        live_inputs=int(not historical),
        selector=_chart_selector(timeframe),
        provenance="provider_history" if historical else "provider_subscription",
    )


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
        *(f"dashboard.history-page.{frame}" for frame in CHART_TIMEFRAMES),
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
        if self.timeframe not in CHART_TIMEFRAMES:
            raise ValueError("unsupported history timeframe")
        if str(UUID(self.request_id)) != self.request_id:
            raise ValueError("invalid history request identity")
        if not isinstance(self.instrument_id, str) or not 1 <= len(self.instrument_id) <= 128:
            raise ValueError("invalid history instrument")
        interval = CHART_TIMEFRAMES[self.timeframe]
        if any(type(v) is not int or v <= 0 or v % interval for v in (self.start, self.end)):
            raise ValueError("history bounds must be positive UTC timeframe boundaries")
        if not 1 <= (self.end - self.start) // interval <= 1000:
            raise ValueError("history page must span 1..1000 selected candles")

    @property
    def selector(self) -> str:
        """Return the native provider selector for completed selected candles."""
        return _chart_selector(self.timeframe)

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
            maximum_observations=(self.end - self.start) // CHART_TIMEFRAMES[self.timeframe],
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
    candles = []
    for bar in batch.observations:
        if str(bar.bar_type) != f"{page.instrument_id}-{page.selector}":
            raise ValueError("history bar identity mismatch")
        candle = _provider_candle(bar, timeframe, historical=True)
        # Provider/session opens can be off the UTC grid and have a shortened final
        # interval. rc5's nominal close must not discard such a returned candle.
        if start <= candle.time < end:
            candles.append(candle)
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
