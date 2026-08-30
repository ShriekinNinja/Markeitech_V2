from __future__ import annotations

from datetime import date
from pathlib import Path

from markeitech.intelligence.session import (
    CalendarProjectionView,
    CanonicalCalendar,
    canonical_definition_from_config,
)
from markeitech.system.composition import _canonical_calendar_payload
from markeitech.system.config import load_system_config


def canonical_calendar(calendar_id: str) -> CanonicalCalendar:
    root = Path(__file__).parents[1]
    config = load_system_config(root / "config/system.example.toml")
    definition = next(
        item
        for item in config.sessions.available_calendars
        if item.calendar_id == calendar_id
    )
    return CanonicalCalendar(
        canonical_definition_from_config(_canonical_calendar_payload(definition)),
    )


def projection_view(
    calendar_id: str,
    start: date = date(2025, 1, 1),
    end: date = date(2027, 12, 31),
) -> CalendarProjectionView:
    return CalendarProjectionView(canonical_calendar(calendar_id).projection(start, end))
