"""Bounded operator history requests, detached from web and native runtime mechanics."""

from dataclasses import dataclass, replace
from uuid import UUID

from markeitech.acquisition import HistoricalDependencyDemandEvent
from markeitech.acquisition.historical import HistoricalRequest
from markeitech.acquisition.minute_candles import MinuteCandle, _MinuteCandleBook

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
    if event.capability_id != "dashboard.history-page":
        return request
    token = event.consumer_id.removeprefix(HISTORY_CONSUMER_PREFIX)
    if not event.consumer_id.startswith(HISTORY_CONSUMER_PREFIX) or str(UUID(token)) != token:
        raise ValueError("invalid history page execution identity")
    return replace(request, request_id=f"{request.request_id}:page:{token}")


@dataclass(frozen=True, slots=True)
class DashboardHistoryRequest:
    """Request a half-open UTC minute window; timestamps are whole Unix seconds."""

    request_id: str
    instrument_id: str
    start: int
    end: int

    def __post_init__(self) -> None:
        if str(UUID(self.request_id)) != self.request_id:
            raise ValueError("invalid history request identity")
        if not isinstance(self.instrument_id, str) or not 1 <= len(self.instrument_id) <= 128:
            raise ValueError("invalid history instrument")
        if any(type(v) is not int or v <= 0 or v % 60 for v in (self.start, self.end)):
            raise ValueError("history bounds must be positive UTC minute boundaries")
        if not 60 <= self.end - self.start <= 120 * 60:
            raise ValueError("history page must span 1..120 minutes")

    @property
    def consumer_id(self) -> str:
        """Return unique request correlation retained by the native historical executor."""
        return HISTORY_CONSUMER_PREFIX + self.request_id

    def demand(self) -> HistoricalDependencyDemandEvent:
        """Use the native recent-completed resolver anchored at the chosen past end."""
        return HistoricalDependencyDemandEvent(
            demand_id=self.consumer_id,
            consumer_id=self.consumer_id,
            capability_id="dashboard.history-page",
            capability_version=1,
            instrument_id=self.instrument_id,
            selector="5-SECOND-LAST-EXTERNAL",
            window="recent_completed",
            minimum_observations=1,
            maximum_observations=(self.end - self.start) // 5,
            priority=40,
            purpose="operator chart history page",
            as_of_ns=self.end * 1_000_000_000,
        )


@dataclass(frozen=True, slots=True)
class DashboardHistoryPage:
    """Acquisition-produced minute page; missing provider intervals remain absent."""

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


def project_history_page(batch, consumer_id: str, received_ns: int) -> DashboardHistoryPage:  # noqa: ANN001
    """Aggregate one validated native batch inside acquisition, without retaining raw bars."""
    request = batch.request
    start, end = request.start_ns // 1_000_000_000, (request.end_ns + 1) // 1_000_000_000
    page = DashboardHistoryRequest(
        consumer_id.removeprefix(HISTORY_CONSUMER_PREFIX), request.instrument_id, start, end
    )
    book = _MinuteCandleBook({page.instrument_id}, max(2, (end - start) // 60 + 1))
    for bar in batch.observations:
        if request.start_ns < bar.ts_event <= request.end_ns + 1:
            book.observe(bar, historical=True)
    update = book.snapshot(page.instrument_id, received_ns)
    candles = tuple(
        replace(c, status="INCOMPLETE") if c.status == "FORMING" else c
        for c in update.candles
        if start <= c.time < end
    )
    return DashboardHistoryPage(
        page.request_id,
        page.instrument_id,
        start,
        end,
        candles,
        update.conflicts,
        update.rejected_inputs,
        update.ts_event,
        received_ns,
    )
