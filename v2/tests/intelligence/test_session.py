from __future__ import annotations

from datetime import UTC, datetime

from markeitech.intelligence.session import SessionCalendar, definition_from_config


def _calendar() -> SessionCalendar:
    return SessionCalendar(
        definition_from_config(
            {
                "calendar_id": "cboe_spxw",
                "provider_calendar": "CBOE_Index_Options",
                "timezone": "America/New_York",
                "schedule_version": "test-1",
                "phases": [
                    {"name": "GTH", "start": "20:15", "end": "09:25", "start_day_offset": -1},
                    {"name": "RTH", "start": "09:30", "end": "16:15", "start_day_offset": 0},
                    {"name": "CURB", "start": "16:15", "end": "17:00", "start_day_offset": 0},
                ],
                "overrides": [
                    {
                        "trade_date": "2026-01-19",
                        "phase": "GTH",
                        "start": "20:15",
                        "end": "11:30",
                        "start_day_offset": -1,
                    },
                ],
            },
        ),
    )


def _ns(value: str) -> int:
    return int(datetime.fromisoformat(value).astimezone(UTC).timestamp() * 1_000_000_000)


def test_spxw_gth_uses_next_exchange_trade_date() -> None:
    snapshot = _calendar().evaluate(_ns("2026-08-16T21:00:00-04:00"))

    assert snapshot.phase == "GTH"
    assert snapshot.trade_date.isoformat() == "2026-08-17"
    assert snapshot.is_open is True


def test_spxw_rth_respects_dst() -> None:
    snapshot = _calendar().evaluate(_ns("2026-03-09T09:30:00-04:00"))

    assert snapshot.phase == "RTH"
    assert snapshot.trade_date.isoformat() == "2026-03-09"


def test_configured_gth_holiday_override_can_open_without_rth() -> None:
    snapshot = _calendar().evaluate(_ns("2026-01-19T10:00:00-05:00"))

    assert snapshot.phase == "GTH"
    assert snapshot.trade_date.isoformat() == "2026-01-19"
    assert snapshot.phase_close_ns == _ns("2026-01-19T11:30:00-05:00")


def test_spxw_early_close_does_not_invent_a_curb_session() -> None:
    snapshot = _calendar().evaluate(_ns("2026-11-27T14:00:00-05:00"))

    assert snapshot.phase == "CLOSED"
