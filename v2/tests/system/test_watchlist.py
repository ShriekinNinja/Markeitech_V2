from __future__ import annotations

import pytest

from markeitech.system.watchlist import ConsumerState, ObservationState, WatchlistState

INSTRUMENTS = (
    "ESU6.CME",
    "NQU6.CME",
    "SPY.ARCA",
    "QQQ.NASDAQ",
    "XLK.ARCA",
    "XLF.ARCA",
    "IWM.ARCA",
    "SOXL.ARCA",
)


def test_requires_nonempty_unique_instruments_without_proof_size_constraint() -> None:
    with pytest.raises(ValueError, match="at least one"):
        WatchlistState(())
    with pytest.raises(ValueError, match="unique"):
        WatchlistState((INSTRUMENTS[0], INSTRUMENTS[0]))

    assert len(WatchlistState((INSTRUMENTS[0],)).snapshot().instruments) == 1


def test_separates_consumer_registration_from_market_observation() -> None:
    state = WatchlistState(INSTRUMENTS)

    initial = state.snapshot()
    assert initial.consumer_state == ConsumerState.DETACHED
    assert initial.observation_state == ObservationState.UNOBSERVED
    assert initial.operational is False

    assert state.register_consumers() is True
    assert state.register_consumers() is False
    registered = state.snapshot()
    assert registered.consumer_state == ConsumerState.REGISTERED
    assert registered.observation_state == ObservationState.UNOBSERVED
    assert registered.operational is True


def test_becomes_observed_only_after_quote_and_bar_for_every_instrument() -> None:
    state = WatchlistState(INSTRUMENTS)

    for index, instrument_id in enumerate(INSTRUMENTS, start=1):
        assert state.observe_quote(instrument_id, "100.00", "100.25", index) is False
    assert state.observed_count == 0
    assert state.snapshot().observation_state == ObservationState.PARTIAL

    for index, instrument_id in enumerate(INSTRUMENTS, start=1):
        assert state.observe_bar(instrument_id, "100.25", index) is True
        assert state.observed_count == index

    snapshot = state.snapshot()
    assert state.is_observed is True
    assert snapshot.observation_state == ObservationState.OBSERVED
    assert all(
        item.observation_state == ObservationState.OBSERVED
        for item in snapshot.instruments
    )


def test_snapshot_is_immutable_and_ordered() -> None:
    state = WatchlistState(("SPY.ARCA", "ESU6.CME"))
    state.register_consumers()
    state.observe_quote("SPY.ARCA", "100.00", "100.25", 10)

    snapshot = state.snapshot()

    assert snapshot.schema_version == 1
    assert snapshot.sequence == 2
    assert [item.instrument_id for item in snapshot.instruments] == ["ESU6.CME", "SPY.ARCA"]
    with pytest.raises(AttributeError):
        snapshot.sequence = 3  # type: ignore[misc]


def test_out_of_order_observation_is_counted_without_replacing_latest_state() -> None:
    state = WatchlistState(("ESU6.CME",))
    state.observe_quote("ESU6.CME", "100.00", "100.25", 20)
    state.observe_quote("ESU6.CME", "99.00", "99.25", 10)
    state.observe_bar("ESU6.CME", "100.25", 20)
    state.observe_bar("ESU6.CME", "99.25", 10)

    instrument = state.snapshot().instruments[0]

    assert instrument.best_bid == "100.00"
    assert instrument.best_ask == "100.25"
    assert instrument.last == "100.25"
    assert instrument.quote_ts_event_ns == 20
    assert instrument.bar_ts_event_ns == 20
    assert instrument.quote_observations == 2
    assert instrument.bar_observations == 2
    assert instrument.out_of_order_observations == 2


def test_rejects_invalid_timestamps_and_observations_outside_watchlist() -> None:
    state = WatchlistState(INSTRUMENTS)

    with pytest.raises(ValueError, match="unexpected watchlist instrument"):
        state.observe_bar("VIX.CBOE", "20.00", 1)
    with pytest.raises(ValueError, match="non-negative integer"):
        state.observe_quote(INSTRUMENTS[0], "100.00", "100.25", -1)
    assert state.snapshot().instruments[0].quote_observations == 0


def test_detach_changes_operational_state_without_erasing_observations() -> None:
    state = WatchlistState(("ESU6.CME",))
    state.register_consumers()
    state.observe_quote("ESU6.CME", "100.00", "100.25", 1)
    state.observe_bar("ESU6.CME", "100.25", 1)

    assert state.detach_consumers() is True
    assert state.detach_consumers() is False

    snapshot = state.snapshot()
    assert snapshot.operational is False
    assert snapshot.observation_state == ObservationState.OBSERVED
