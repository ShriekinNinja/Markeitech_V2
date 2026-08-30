from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime

import pytest

from tests.calendar_fixtures import canonical_calendar, projection_view


def _ns(value: str) -> int:
    return int(datetime.fromisoformat(value).astimezone(UTC).timestamp() * 1_000_000_000)


def test_spxw_gth_uses_next_exchange_trade_date() -> None:
    snapshot = projection_view("cboe_spxw").evaluate(_ns("2026-08-16T21:00:00-04:00"))

    assert snapshot.phase == "GTH"
    assert snapshot.trade_date == date(2026, 8, 17)


def test_spxw_rth_respects_dst() -> None:
    snapshot = projection_view("cboe_spxw").evaluate(_ns("2026-03-09T09:30:00-04:00"))

    assert snapshot.phase == "RTH"
    assert snapshot.trade_date == date(2026, 3, 9)


def test_spxw_early_close_omits_curb_phase() -> None:
    snapshot = projection_view("cboe_spxw").evaluate(_ns("2026-11-27T14:00:00-05:00"))

    assert snapshot.market_state == "CLOSED"
    assert "CURB" not in snapshot.phase_memberships


def test_public_windows_query_returns_exact_immutable_utc_bounds() -> None:
    rth = next(
        item
        for item in projection_view("cboe_spxw").windows(
            date(2026, 3, 9),
            date(2026, 3, 9),
        )
        if item.phase == "RTH"
    )

    assert rth.start_ns == _ns("2026-03-09T09:30:00-04:00")
    assert rth.end_ns == _ns("2026-03-09T16:15:00-04:00")
    with pytest.raises(FrozenInstanceError):
        rth.phase = "changed"  # type: ignore[misc]


def test_overlapping_product_phases_are_preserved_as_memberships() -> None:
    calendar = canonical_calendar("cboe_spxw")
    projection = calendar.projection(date(2026, 3, 9), date(2026, 3, 9))

    assert {item.phase for item in projection.phase_windows} == {"GTH", "RTH", "CURB"}
