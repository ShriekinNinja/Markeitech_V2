from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from markeitech.domain import SessionProfile
from markeitech.market_data import load_market_data_runtime_config
from markeitech.persistence import (
    InstrumentCalendarPolicy,
    PandasMarketSessionCalendar,
    RecoveryPlanningError,
)


def policy(
    instrument_id: str,
    calendar_id: str,
    profile: SessionProfile,
) -> InstrumentCalendarPolicy:
    return InstrumentCalendarPolicy(instrument_id, calendar_id, profile)


def calendar() -> PandasMarketSessionCalendar:
    return PandasMarketSessionCalendar(
        (
            policy("NQU6.CME", "CME_Equity", SessionProfile.FULL),
            policy("SPY.ARCA", "NYSE", SessionProfile.REGULAR),
            policy("QQQ.ARCA", "NYSE", SessionProfile.FULL),
            policy("BTC/USD.PAXOS", "24/7", SessionProfile.CONTINUOUS),
        )
    )


def test_cme_equity_session_excludes_intraday_halt() -> None:
    start = datetime(2026, 7, 1, 22, tzinfo=UTC)
    end = datetime(2026, 7, 2, 21, tzinfo=UTC)

    expected = calendar().expected_minute_opens("NQU6.CME", start, end)

    assert len(expected) == 1_365
    assert datetime(2026, 7, 2, 20, 14, tzinfo=UTC) in expected
    assert datetime(2026, 7, 2, 20, 15, tzinfo=UTC) not in expected
    assert datetime(2026, 7, 2, 20, 29, tzinfo=UTC) not in expected
    assert datetime(2026, 7, 2, 20, 30, tzinfo=UTC) in expected


def test_cme_equity_holiday_early_close_is_not_a_gap() -> None:
    start = datetime(2026, 7, 2, 22, tzinfo=UTC)
    end = datetime(2026, 7, 3, 21, tzinfo=UTC)

    expected = calendar().expected_minute_opens("NQU6.CME", start, end)

    assert len(expected) == 1_140
    assert expected[-1] == datetime(2026, 7, 3, 16, 59, tzinfo=UTC)


def test_nyse_regular_profile_respects_holiday_and_dst() -> None:
    session_calendar = calendar()
    holiday = session_calendar.expected_minute_opens(
        "SPY.ARCA",
        datetime(2026, 7, 3, tzinfo=UTC),
        datetime(2026, 7, 4, tzinfo=UTC),
    )
    dst_transition = session_calendar.expected_minute_opens(
        "SPY.ARCA",
        datetime(2026, 3, 6, tzinfo=UTC),
        datetime(2026, 3, 10, tzinfo=UTC),
    )

    assert holiday == ()
    assert len(dst_transition) == 780
    assert datetime(2026, 3, 6, 14, 30, tzinfo=UTC) in dst_transition
    assert datetime(2026, 3, 9, 13, 30, tzinfo=UTC) in dst_transition


def test_nyse_full_profile_includes_premarket_and_postmarket() -> None:
    start = datetime(2026, 7, 2, tzinfo=UTC)
    end = start + timedelta(days=1)

    regular = calendar().expected_minute_opens("SPY.ARCA", start, end)
    full = calendar().expected_minute_opens("QQQ.ARCA", start, end)

    assert len(regular) == 390
    assert len(full) == 960
    assert full[0] == datetime(2026, 7, 2, 8, tzinfo=UTC)
    assert full[-1] == datetime(2026, 7, 2, 23, 59, tzinfo=UTC)


def test_continuous_calendar_includes_weekends_and_partial_minutes() -> None:
    start = datetime(2026, 7, 11, 12, 0, 30, tzinfo=UTC)
    end = datetime(2026, 7, 11, 12, 5, tzinfo=UTC)

    expected = calendar().expected_minute_opens("BTC/USD.PAXOS", start, end)

    assert expected == tuple(
        datetime(2026, 7, 11, 12, minute, tzinfo=UTC) for minute in range(1, 5)
    )


def test_retention_cutoff_counts_only_completed_product_sessions() -> None:
    as_of = datetime(2026, 7, 13, 10, tzinfo=UTC)

    futures_cutoff = calendar().retention_cutoff("NQU6.CME", 5, as_of)
    continuous_cutoff = calendar().retention_cutoff("BTC/USD.PAXOS", 5, as_of)

    assert futures_cutoff == datetime(2026, 7, 5, 22, tzinfo=UTC)
    assert continuous_cutoff == datetime(2026, 7, 8, tzinfo=UTC)


def test_registry_builds_explicit_instrument_calendar_policies() -> None:
    config = load_market_data_runtime_config(Path("config/market-data.example.toml"))
    session_calendar = PandasMarketSessionCalendar.from_registry(config.instrument_registry)

    expected = session_calendar.expected_minute_opens(
        "NQU6.CME",
        datetime(2026, 7, 2, 20, 14, tzinfo=UTC),
        datetime(2026, 7, 2, 20, 31, tzinfo=UTC),
    )

    assert expected == (
        datetime(2026, 7, 2, 20, 14, tzinfo=UTC),
        datetime(2026, 7, 2, 20, 30, tzinfo=UTC),
    )


def test_calendar_configuration_and_queries_fail_closed() -> None:
    with pytest.raises(ValueError, match="unknown pandas market calendar"):
        PandasMarketSessionCalendar((policy("NQU6.CME", "NOT_A_CALENDAR", SessionProfile.FULL),))
    with pytest.raises(ValueError, match="used together"):
        PandasMarketSessionCalendar((policy("BTC/USD.PAXOS", "NYSE", SessionProfile.CONTINUOUS),))

    session_calendar = calendar()
    with pytest.raises(RecoveryPlanningError, match="not configured"):
        session_calendar.expected_minute_opens(
            "UNKNOWN",
            datetime(2026, 7, 1, tzinfo=UTC),
            datetime(2026, 7, 2, tzinfo=UTC),
        )
    with pytest.raises(RecoveryPlanningError, match="day limit"):
        session_calendar.expected_minute_opens(
            "NQU6.CME",
            datetime(2025, 1, 1, tzinfo=UTC),
            datetime(2026, 7, 1, tzinfo=UTC),
        )
