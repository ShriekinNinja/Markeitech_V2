from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, time
from pathlib import Path

import pytest

from markeitech.intelligence.session import (
    CalendarProjectionView,
    CanonicalCalendar,
)
from markeitech.system.config import load_system_config
from tests.calendar_fixtures import canonical_calendar


def _ns(value: str) -> int:
    return int(datetime.fromisoformat(value).astimezone(UTC).timestamp() * 1_000_000_000)


def _config():  # noqa: ANN202
    root = Path(__file__).parents[2]
    return load_system_config(root / "config/system.example.toml")


def test_modern_cme_equity_removes_the_obsolete_1515_pause() -> None:
    calendar = canonical_calendar("cme_equity")

    snapshot = calendar.evaluate(_ns("2026-08-24T20:20:00Z"))

    assert snapshot.trade_date == date(2026, 8, 24)
    assert snapshot.phase_memberships == ("GLOBEX",)
    assert snapshot.market_state == "OPEN"
    assert snapshot.is_open is True


def test_cme_correction_is_effective_dated_and_source_identified() -> None:
    calendar = canonical_calendar("cme_equity")
    historical = calendar.projection(date(2021, 6, 25), date(2021, 6, 25))
    modern = calendar.projection(date(2021, 6, 28), date(2021, 6, 28))

    assert [item.market_state for item in historical.exchange_segments] == [
        "OPEN",
        "BREAK",
        "OPEN",
    ]
    assert historical.correction_outcomes[0].status == "NOT_APPLICABLE"
    assert [item.market_state for item in modern.exchange_segments] == ["OPEN"]
    assert modern.correction_outcomes[0].status == "APPLIED"
    assert modern.correction_outcomes[0].source_id == "cme-equity-index-hours-2021-06-21"


def test_cme_correction_fails_closed_when_provider_break_changes() -> None:
    base = canonical_calendar("cme_equity")
    conflicting = replace(
        base.definition.corrections[0],
        expected_start=time(15, 14),
    )
    calendar = CanonicalCalendar(
        replace(
            base.definition,
            definition_digest="c" * 64,
            schedule_version="test-conflict-v1",
            corrections=(conflicting,),
        ),
    )

    with pytest.raises(ValueError, match="calendar correction conflicts"):
        calendar.projection(date(2026, 8, 24), date(2026, 8, 24))


def test_cme_projection_keeps_exchange_state_separate_from_product_phase() -> None:
    projection = canonical_calendar("cme_equity").projection(
        date(2026, 8, 24),
        date(2026, 8, 24),
    )

    exchange_segments = [
        (item.market_state, item.start_ns, item.end_ns)
        for item in projection.exchange_segments
    ]
    assert exchange_segments == [
        ("OPEN", _ns("2026-08-23T22:00:00Z"), _ns("2026-08-24T21:00:00Z")),
    ]
    assert [(item.phase, item.start_ns, item.end_ns) for item in projection.phase_windows] == [
        ("ASIA", _ns("2026-08-23T22:00:00Z"), _ns("2026-08-24T05:00:00Z")),
        ("GLOBEX", _ns("2026-08-23T22:00:00Z"), _ns("2026-08-24T21:00:00Z")),
        ("LONDON", _ns("2026-08-24T07:00:00Z"), _ns("2026-08-24T10:30:00Z")),
        ("NEW_YORK", _ns("2026-08-24T13:30:00Z"), _ns("2026-08-24T20:00:00Z")),
    ]


def test_product_phases_can_overlap_without_collapsing_exchange_state() -> None:
    calendar = canonical_calendar("cme_equity")

    snapshot = calendar.evaluate(_ns("2026-08-24T14:00:00Z"))

    assert snapshot.market_state == "OPEN"
    assert snapshot.phase_memberships == ("GLOBEX", "NEW_YORK")


def test_cme_and_cbot_have_distinct_identity_but_equal_current_hours() -> None:
    cme = canonical_calendar("cme_equity").projection(date(2026, 8, 24), date(2026, 8, 24))
    cbot = canonical_calendar("cbot_equity").projection(date(2026, 8, 24), date(2026, 8, 24))

    assert [(item.market_state, item.start_ns, item.end_ns) for item in cme.exchange_segments] == [
        (item.market_state, item.start_ns, item.end_ns) for item in cbot.exchange_segments
    ]
    assert cme.definition_digest != cbot.definition_digest


def test_watchlist_owns_concrete_instrument_calendar_bindings() -> None:
    config = _config()
    mappings = {
        item.instrument_id: item.calendar_id for item in config.watchlist.members
    }

    assert mappings["ESU6.CME"] == "cme_equity"
    assert mappings["NQU6.CME"] == "cme_equity"
    assert mappings["YMU6.CBOT"] == "cbot_equity"
    assert mappings["CLV6.NYMEX"] == "cme_energy"
    correction = canonical_calendar("cme_equity").definition.corrections[0]
    assert correction.product_roots == ("ES", "NQ", "YM")


def test_cl_uses_product_specific_provider_calendar_and_globex_phase() -> None:
    calendar = canonical_calendar("cme_energy")
    projection = calendar.projection(date(2026, 8, 24), date(2026, 8, 24))

    assert calendar.definition.provider_calendar == "CMEGlobex_CL"
    assert [item.market_state for item in projection.exchange_segments] == ["OPEN"]
    assert {item.phase for item in projection.phase_windows} == {
        "ASIA",
        "GLOBEX",
        "LONDON",
        "NEW_YORK",
    }


def test_cme_dst_and_weekend_are_derived_from_mcal() -> None:
    calendar = canonical_calendar("cme_equity")
    before_dst = next(
        item
        for item in calendar.projection(date(2026, 3, 6), date(2026, 3, 6)).phase_windows
        if item.phase == "GLOBEX"
    )
    after_dst = next(
        item
        for item in calendar.projection(date(2026, 3, 9), date(2026, 3, 9)).phase_windows
        if item.phase == "GLOBEX"
    )
    weekend = calendar.evaluate(_ns("2026-08-23T20:00:00Z"))

    assert before_dst.start_ns == _ns("2026-03-05T23:00:00Z")
    assert after_dst.start_ns == _ns("2026-03-08T22:00:00Z")
    assert weekend.market_state == "CLOSED"
    assert weekend.trade_date == date(2026, 8, 24)
    assert weekend.next_transition_ns == _ns("2026-08-23T22:00:00Z")


def test_cboe_phase_timezone_and_mcal_early_close_are_both_respected() -> None:
    calendar = canonical_calendar("cboe_spxw")
    rth = calendar.evaluate(_ns("2026-03-09T13:30:00Z"))
    holiday = calendar.evaluate(_ns("2026-01-19T15:00:00Z"))
    early_close = calendar.evaluate(_ns("2026-11-27T19:00:00Z"))

    assert calendar.definition.exchange_timezone == "America/Chicago"
    assert rth.phase_memberships == ("RTH",)
    assert rth.segment_open_ns == _ns("2026-03-09T13:30:00Z")
    assert holiday.market_state == "CLOSED"
    assert early_close.market_state == "CLOSED"
    assert "CURB" not in early_close.phase_memberships


def test_projection_view_fails_closed_outside_coverage() -> None:
    projection = canonical_calendar("cme_equity").projection(
        date(2026, 8, 24),
        date(2026, 8, 24),
    )
    view = CalendarProjectionView(projection)

    with pytest.raises(ValueError, match="outside calendar projection coverage"):
        view.evaluate(_ns("2025-01-01T00:00:00Z"))


def test_canonical_calendar_and_projection_are_immutable() -> None:
    calendar = canonical_calendar("cme_equity")
    projection = calendar.projection(date(2026, 8, 24), date(2026, 8, 24))

    with pytest.raises(FrozenInstanceError):
        calendar.definition = calendar.definition  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        projection.phase_windows[0].phase = "CHANGED"  # type: ignore[misc]
