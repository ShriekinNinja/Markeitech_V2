from __future__ import annotations

from markeitech.acquisition import (
    HistoricalDependencyDemandEvent,
    HistoricalExecutionEventMessage,
    HistoricalReadinessEvent,
)


def test_historical_signal_contracts_round_trip_without_market_data() -> None:
    demand = HistoricalDependencyDemandEvent(
        demand_id="probe:ES",
        consumer_id="HISTORICAL-PROBE",
        capability_id="historical.acceptance_probe",
        capability_version=1,
        instrument_id="ESU6.CME",
        selector="1-MINUTE-LAST-EXTERNAL",
        window="recent_completed",
        minimum_observations=5,
        maximum_observations=10,
        priority=10,
        purpose="acceptance",
        as_of_ns=100,
        parameters={"dynamic": False},
    )
    execution = HistoricalExecutionEventMessage(
        event_id="request:SUBMITTED:1",
        request_id="request",
        state="SUBMITTED",
        attempt=1,
        instrument_id="ESU6.CME",
        selector="1-MINUTE-LAST-EXTERNAL",
        window="recent_completed",
        start_ns=10,
        end_ns=20,
        limit=10,
        consumer_ids=("HISTORICAL-PROBE",),
        occurred_at_ns=30,
        source="DATA-ACQUISITION",
        detail="provider request submitted",
    )
    readiness = HistoricalReadinessEvent(
        event_id="request:HISTORICAL-PROBE:READY",
        request_id="request",
        consumer_id="HISTORICAL-PROBE",
        capability_id="historical.acceptance_probe",
        capability_version=1,
        state="READY",
        instrument_id="ESU6.CME",
        selector="1-MINUTE-LAST-EXTERNAL",
        window="recent_completed",
        minimum_observations=5,
        observed_count=10,
        completed_at_ns=40,
        source="DATA-ACQUISITION",
        reason="minimum observations satisfied",
    )

    assert HistoricalDependencyDemandEvent.from_signal_value(demand.to_signal_value()) == demand
    assert (
        HistoricalExecutionEventMessage.from_signal_value(execution.to_signal_value()) == execution
    )
    assert HistoricalReadinessEvent.from_signal_value(readiness.to_signal_value()) == readiness
    assert "observations" not in execution.to_signal_value()
    assert "bars" not in readiness.to_signal_value()
