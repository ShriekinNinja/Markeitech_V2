from __future__ import annotations

import pytest
from nautilus_trader.model import InstrumentId

from markeitech.system.acquisition import InstrumentDefinitionTracker, _observation_demand
from markeitech.system.messages import (
    INSTRUMENTS_READY,
    INSTRUMENTS_RESOLVING,
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

    demand = _observation_demand(event)

    assert demand.demand_id == event.demand_id
    assert demand.owner.kind.value == "watchlist"
    assert demand.requirement.stream_key == (
        "ESU6.CME",
        "bars",
        "5-SECOND-LAST-EXTERNAL",
    )
