from __future__ import annotations

import pytest

from markeitech.system.watchlist import WatchlistState

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


def test_requires_eight_unique_instruments() -> None:
    with pytest.raises(ValueError, match="at least eight"):
        WatchlistState(INSTRUMENTS[:7])
    with pytest.raises(ValueError, match="unique"):
        WatchlistState((*INSTRUMENTS[:7], INSTRUMENTS[0]))


def test_becomes_ready_only_after_quote_and_bar_for_every_instrument() -> None:
    state = WatchlistState(INSTRUMENTS)

    for instrument_id in INSTRUMENTS:
        assert state.observe_quote(instrument_id, "100.00", "100.25") is False
    assert state.ready_count == 0

    for index, instrument_id in enumerate(INSTRUMENTS, start=1):
        assert state.observe_bar(instrument_id, "100.25") is True
        assert state.ready_count == index

    assert state.is_ready is True
    assert all(item.ready for _, item in state.snapshot())


def test_rejects_observations_outside_watchlist() -> None:
    state = WatchlistState(INSTRUMENTS)

    with pytest.raises(ValueError, match="unexpected watchlist instrument"):
        state.observe_bar("VIX.CBOE", "20.00")
