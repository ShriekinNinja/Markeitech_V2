from __future__ import annotations

from datetime import UTC, datetime

import pytest
from nautilus_trader.model import InstrumentId

from markeitech.acquisition import (
    HistoricalDependencyCompiler,
    HistoricalDependencyDemandEvent,
    HistoricalResourcePolicy,
)
from markeitech.acquisition.historical_windows import HistoricalWindowResolver
from markeitech.intelligence.session import SessionCalendar, definition_from_config
from markeitech.system.acquisition import (
    HistoricalDemandRetryBook,
    InstrumentDefinitionTracker,
    _analytical_observation_demand,
    _compile_historical_demand,
    _watchlist_observation_demand,
    synchronize_historical_demand_retry_timer,
)
from markeitech.system.messages import (
    INSTRUMENTS_READY,
    INSTRUMENTS_RESOLVING,
    AnalyticalDemandEvent,
    WatchlistDemandEvent,
)


def test_tracker_owns_definition_request_deduplication_and_readiness() -> None:
    tracker = InstrumentDefinitionTracker(["SPY.ARCA", "ESU6.CME"])

    assert tuple(map(str, tracker.take_unrequested())) == ("ESU6.CME", "SPY.ARCA")
    assert tracker.take_unrequested() == ()
    assert tracker.status("DATA-ACQUISITION").state == INSTRUMENTS_RESOLVING

    assert tracker.observe(InstrumentId.from_str("ESU6.CME")) is True
    assert tracker.observe(InstrumentId.from_str("ESU6.CME")) is False
    assert tracker.observe(InstrumentId.from_str("NQU6.CME")) is False
    assert tuple(sorted(map(str, tracker.missing))) == ("SPY.ARCA",)

    assert tracker.observe(InstrumentId.from_str("SPY.ARCA")) is True
    status = tracker.status("DATA-ACQUISITION")
    assert status.state == INSTRUMENTS_READY
    assert status.available_instrument_ids == ("ESU6.CME", "SPY.ARCA")


@pytest.mark.parametrize("instrument_ids", [[], ["ESU6.CME", "ESU6.CME"]])
def test_tracker_rejects_empty_or_duplicate_configuration(
    instrument_ids: list[str],
) -> None:
    with pytest.raises(ValueError):
        InstrumentDefinitionTracker(instrument_ids)


def test_watchlist_contract_maps_to_acquisition_demand() -> None:
    event = WatchlistDemandEvent(
        demand_id="watchlist:1:ESU6.CME/bars/5-SECOND-LAST-EXTERNAL",
        action="REQUEST",
        instrument_id="ESU6.CME",
        capability="watchlist_last",
        feed_kind="bars",
        selector="5-SECOND-LAST-EXTERNAL",
        owner_id="config:system",
        purpose="static watchlist last",
    )

    demand = _watchlist_observation_demand(event)

    assert demand.demand_id == event.demand_id
    assert demand.owner.kind.value == "watchlist"
    assert demand.requirement.stream_key == (
        "ESU6.CME",
        "bars",
        "5-SECOND-LAST-EXTERNAL",
    )


def test_analytical_contract_maps_to_analyzer_owned_acquisition_demand() -> None:
    event = AnalyticalDemandEvent(
        demand_id="metric:quote-quality:ESU6.CME:quotes:default",
        action="REQUEST",
        instrument_id="ESU6.CME",
        capability_id="metric:quote-quality",
        capability_version=1,
        feed_kind="quotes",
        selector="default",
        owner_id="QUOTE-QUALITY-METRICS",
        purpose="calculate bounded quote-quality metrics",
    )

    demand = _analytical_observation_demand(event)

    assert demand.owner.kind.value == "analyzer"
    assert demand.owner.owner_id == "QUOTE-QUALITY-METRICS"
    assert demand.requirement.stream_key == ("ESU6.CME", "quotes", "default")


def test_recent_completed_historical_demand_excludes_forming_bar() -> None:
    event = HistoricalDependencyDemandEvent(
        demand_id="probe:ES",
        consumer_id="probe",
        capability_id="probe",
        capability_version=1,
        instrument_id="ESU6.CME",
        selector="1-MINUTE-LAST-EXTERNAL",
        window="recent_completed",
        minimum_observations=5,
        maximum_observations=10,
        priority=10,
        purpose="acceptance",
        as_of_ns=12 * 60_000_000_000 + 30_000_000_000,
    )
    compiler = HistoricalDependencyCompiler(
        HistoricalResourcePolicy(8, 100, 500),
    )

    request = _compile_historical_demand(event, compiler)

    assert request.start_ns == 2 * 60_000_000_000
    assert request.end_ns == 12 * 60_000_000_000 - 1
    assert request.limit == 10


def test_session_owned_historical_demand_compiles_authoritative_bounds() -> None:
    event = HistoricalDependencyDemandEvent(
        demand_id="probe:ES:rth",
        consumer_id="probe",
        capability_id="probe",
        capability_version=1,
        instrument_id="ESU6.CME",
        selector="5-MINUTE-LAST-EXTERNAL",
        window="current_rth",
        minimum_observations=5,
        maximum_observations=100,
        priority=10,
        purpose="acceptance",
        as_of_ns=int(datetime(2026, 8, 17, 14, 43, 27, tzinfo=UTC).timestamp() * 1_000_000_000),
        window_parameters={"phase": "RTH"},
    )
    calendar = SessionCalendar(
        definition_from_config(
            {
                "calendar_id": "cme_equity",
                "provider_calendar": "CME_Equity",
                "timezone": "America/New_York",
                "schedule_version": "test-1",
                "phases": [
                    {
                        "name": "RTH",
                        "start": "09:30",
                        "end": "16:00",
                        "start_day_offset": 0,
                    },
                ],
                "overrides": [],
            },
        ),
    )
    compiler = HistoricalDependencyCompiler(HistoricalResourcePolicy(8, 500, 1_000))

    request = _compile_historical_demand(
        event,
        compiler,
        resolver=HistoricalWindowResolver(),
        calendar=calendar,
    )

    assert request.window.value == "current_rth"
    assert request.start_ns == int(
        datetime(2026, 8, 17, 13, 30, tzinfo=UTC).timestamp() * 1_000_000_000,
    )
    assert (
        request.end_ns
        == int(
            datetime(2026, 8, 17, 14, 40, tzinfo=UTC).timestamp() * 1_000_000_000,
        )
        - 1
    )


def test_deferred_historical_demands_dedupe_by_demand_id() -> None:
    book = HistoricalDemandRetryBook()
    original = _historical_event("window:ES", as_of_ns=100)
    replacement = _historical_event("window:ES", as_of_ns=200)

    book.retain(original, calendar_id="cme_equity", retry_at_ns=500)
    book.retain(replacement, calendar_id="cme_equity", retry_at_ns=600)

    assert book.demand_ids == ("window:ES",)
    assert book.next_retry_ns == 600
    assert book.release_due(599) == ()
    assert book.release_due(600) == (replacement,)


def test_session_transition_releases_only_matching_calendar_demands() -> None:
    book = HistoricalDemandRetryBook()
    cme = _historical_event("window:ES", as_of_ns=100)
    equities = _historical_event("window:SPY", as_of_ns=100, instrument_id="SPY.ARCA")
    book.retain(cme, calendar_id="cme_equity", retry_at_ns=500)
    book.retain(equities, calendar_id="us_equities", retry_at_ns=500)

    assert book.release_calendar("cme_equity") == (cme,)
    assert book.demand_ids == ("window:SPY",)


def test_clearing_deferred_demands_removes_shutdown_work() -> None:
    book = HistoricalDemandRetryBook()
    book.retain(
        _historical_event("window:ES", as_of_ns=100),
        calendar_id="cme_equity",
        retry_at_ns=500,
    )

    book.clear()

    assert book.demand_ids == ()
    assert book.next_retry_ns is None


def test_historical_retry_timer_is_precise_deduplicated_and_canceled() -> None:
    clock = _RetryClock()

    def callback(_event) -> None:  # noqa: ANN001
        return None

    scheduled = synchronize_historical_demand_retry_timer(
        clock,
        current_retry_at_ns=None,
        next_retry_at_ns=500,
        callback=callback,
    )
    unchanged = synchronize_historical_demand_retry_timer(
        clock,
        current_retry_at_ns=scheduled,
        next_retry_at_ns=500,
        callback=callback,
    )
    replaced = synchronize_historical_demand_retry_timer(
        clock,
        current_retry_at_ns=unchanged,
        next_retry_at_ns=600,
        callback=callback,
    )
    canceled = synchronize_historical_demand_retry_timer(
        clock,
        current_retry_at_ns=replaced,
        next_retry_at_ns=None,
        callback=callback,
    )

    assert clock.scheduled == [500, 600]
    assert clock.cancel_count == 2
    assert canceled is None
    assert clock.timer_names() == []


def _historical_event(
    demand_id: str,
    *,
    as_of_ns: int,
    instrument_id: str = "ESU6.CME",
) -> HistoricalDependencyDemandEvent:
    return HistoricalDependencyDemandEvent(
        demand_id=demand_id,
        consumer_id="SESSION-METRICS",
        capability_id="metric:session-window:opening_range_5m",
        capability_version=1,
        instrument_id=instrument_id,
        selector="5-MINUTE-LAST-EXTERNAL",
        window="opening_range",
        minimum_observations=1,
        maximum_observations=6,
        priority=50,
        purpose="test deferred session window",
        as_of_ns=as_of_ns,
        window_parameters={"phase": "RTH", "duration_minutes": 30},
    )


class _RetryClock:
    def __init__(self) -> None:
        self.scheduled: list[int] = []
        self.cancel_count = 0
        self._active = False

    def timer_names(self) -> list[str]:
        return ["historical-window-demand-retry"] if self._active else []

    def cancel_timer(self, name: str) -> None:
        assert name == "historical-window-demand-retry"
        self.cancel_count += 1
        self._active = False

    def set_time_alert_ns(self, name: str, alert_time_ns: int, callback) -> None:  # noqa: ANN001
        assert name == "historical-window-demand-retry"
        assert callable(callback)
        self.scheduled.append(alert_time_ns)
        self._active = True
