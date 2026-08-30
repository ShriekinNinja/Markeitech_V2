from __future__ import annotations

from datetime import UTC, datetime

import pytest

from markeitech.acquisition.demand import HistoricalWindow
from markeitech.acquisition.historical_windows import (
    HistoricalWindowParameters,
    HistoricalWindowResolutionError,
    HistoricalWindowResolver,
    HistoricalWindowUnavailable,
)
from markeitech.intelligence.session import CalendarProjectionView
from tests.calendar_fixtures import projection_view

MINUTE_NS = 60 * 1_000_000_000


def _calendar() -> CalendarProjectionView:
    return projection_view("cboe_spxw")


def _ns(value: str) -> int:
    return int(datetime.fromisoformat(value).astimezone(UTC).timestamp() * 1_000_000_000)


def _resolve(
    window: HistoricalWindow,
    as_of: str,
    policy: HistoricalWindowParameters,
    *,
    interval_minutes: int = 1,
):
    return HistoricalWindowResolver().resolve(
        window,
        calendar=_calendar(),
        selector_interval_ns=interval_minutes * MINUTE_NS,
        as_of_ns=_ns(as_of),
        parameters={window: policy},
    )


def test_previous_rth_crosses_weekend_and_respects_dst() -> None:
    bounds = _resolve(
        HistoricalWindow.PREVIOUS_RTH,
        "2026-03-09T10:00:00-04:00",
        HistoricalWindowParameters(phase="RTH"),
    )

    assert bounds.start_ns == _ns("2026-03-06T09:30:00-05:00")
    assert bounds.end_ns == _ns("2026-03-06T16:15:00-05:00") - 1


def test_previous_rth_skips_exchange_holiday() -> None:
    bounds = _resolve(
        HistoricalWindow.PREVIOUS_RTH,
        "2026-01-20T10:00:00-05:00",
        HistoricalWindowParameters(phase="RTH"),
    )

    assert bounds.start_ns == _ns("2026-01-16T09:30:00-05:00")
    assert bounds.end_ns == _ns("2026-01-16T16:15:00-05:00") - 1


def test_previous_gth_overnight_uses_configured_phase() -> None:
    bounds = _resolve(
        HistoricalWindow.PREVIOUS_GTH_OVERNIGHT,
        "2026-08-17T10:00:00-04:00",
        HistoricalWindowParameters(phase="GTH"),
    )

    assert bounds.start_ns == _ns("2026-08-16T20:15:00-04:00")
    assert bounds.end_ns == _ns("2026-08-17T09:25:00-04:00") - 1


def test_recent_completed_requires_and_uses_configured_duration() -> None:
    bounds = _resolve(
        HistoricalWindow.RECENT_COMPLETED,
        "2026-08-17T10:43:27-04:00",
        HistoricalWindowParameters(duration_minutes=20),
        interval_minutes=5,
    )

    assert bounds.start_ns == _ns("2026-08-17T10:20:00-04:00")
    assert bounds.end_ns == _ns("2026-08-17T10:40:00-04:00") - 1


def test_current_rth_clips_to_last_completed_five_minute_interval() -> None:
    bounds = _resolve(
        HistoricalWindow.CURRENT_RTH,
        "2026-08-17T10:43:27-04:00",
        HistoricalWindowParameters(phase="RTH"),
        interval_minutes=5,
    )

    assert bounds.start_ns == _ns("2026-08-17T09:30:00-04:00")
    assert bounds.end_ns == _ns("2026-08-17T10:40:00-04:00") - 1


@pytest.mark.parametrize(
    "window",
    [
        HistoricalWindow.CURRENT_OVERNIGHT,
        HistoricalWindow.CURRENT_GTH,
        HistoricalWindow.SESSION_TO_DATE,
    ],
)
def test_current_gth_windows_resolve_same_trade_date_and_clip(
    window: HistoricalWindow,
) -> None:
    bounds = _resolve(
        window,
        "2026-08-16T21:03:00-04:00",
        HistoricalWindowParameters(phase="GTH"),
        interval_minutes=5,
    )

    assert bounds.start_ns == _ns("2026-08-16T20:15:00-04:00")
    assert bounds.end_ns == _ns("2026-08-16T21:00:00-04:00") - 1


def test_opening_range_uses_configured_duration_and_clips_while_forming() -> None:
    completed = _resolve(
        HistoricalWindow.OPENING_RANGE,
        "2026-08-17T10:12:00-04:00",
        HistoricalWindowParameters(phase="RTH", duration_minutes=30),
        interval_minutes=5,
    )
    forming = _resolve(
        HistoricalWindow.OPENING_RANGE,
        "2026-08-17T09:47:00-04:00",
        HistoricalWindowParameters(phase="RTH", duration_minutes=30),
        interval_minutes=5,
    )

    assert completed.start_ns == _ns("2026-08-17T09:30:00-04:00")
    assert completed.end_ns == _ns("2026-08-17T10:00:00-04:00") - 1
    assert forming.end_ns == _ns("2026-08-17T09:45:00-04:00") - 1


def test_power_hour_fails_until_configured_window_starts() -> None:
    with pytest.raises(HistoricalWindowUnavailable, match="not yet available") as error:
        _resolve(
            HistoricalWindow.POWER_HOUR,
            "2026-08-17T14:59:59-04:00",
            HistoricalWindowParameters(phase="RTH", duration_minutes=60),
            interval_minutes=5,
        )
    assert error.value.retry_at_ns == _ns("2026-08-17T15:20:00-04:00")

    bounds = _resolve(
        HistoricalWindow.POWER_HOUR,
        "2026-08-17T15:22:00-04:00",
        HistoricalWindowParameters(phase="RTH", duration_minutes=60),
        interval_minutes=5,
    )
    assert bounds.start_ns == _ns("2026-08-17T15:15:00-04:00")
    assert bounds.end_ns == _ns("2026-08-17T15:20:00-04:00") - 1


def test_power_hour_can_fall_back_to_latest_started_close_relative_window() -> None:
    bounds = _resolve(
        HistoricalWindow.POWER_HOUR,
        "2026-08-18T10:00:00-04:00",
        HistoricalWindowParameters(
            phase="RTH",
            anchor_boundary="end",
            offset_seconds=-3_600,
            duration_seconds=3_600,
            fallback_to_previous=True,
        ),
        interval_minutes=15,
    )

    assert bounds.start_ns == _ns("2026-08-17T15:15:00-04:00")
    assert bounds.end_ns == _ns("2026-08-17T16:15:00-04:00") - 1


def test_named_phase_slice_uses_only_supplied_offsets() -> None:
    bounds = _resolve(
        HistoricalWindow.NAMED_PHASE_SLICE,
        "2026-08-17T12:07:00-04:00",
        HistoricalWindowParameters(
            phase="RTH",
            start_offset_minutes=90,
            end_offset_minutes=150,
        ),
        interval_minutes=5,
    )

    assert bounds.start_ns == _ns("2026-08-17T11:00:00-04:00")
    assert bounds.end_ns == _ns("2026-08-17T12:00:00-04:00") - 1


@pytest.mark.parametrize(
    "window",
    [
        HistoricalWindow.CURB,
        HistoricalWindow.PREMARKET,
        HistoricalWindow.OVERNIGHT,
    ],
)
def test_generic_named_phase_windows_use_only_configured_phase(
    window: HistoricalWindow,
) -> None:
    bounds = _resolve(
        window,
        "2026-08-16T21:03:00-04:00",
        HistoricalWindowParameters(phase="GTH"),
        interval_minutes=5,
    )

    assert bounds.start_ns == _ns("2026-08-16T20:15:00-04:00")
    assert bounds.end_ns == _ns("2026-08-16T21:00:00-04:00") - 1


def test_previous_sessions_resolves_configured_count_across_weekend() -> None:
    bounds = _resolve(
        HistoricalWindow.PREVIOUS_SESSIONS,
        "2026-08-17T10:00:00-04:00",
        HistoricalWindowParameters(phase="RTH", session_count=2),
    )

    assert bounds.start_ns == _ns("2026-08-13T09:30:00-04:00")
    assert bounds.end_ns == _ns("2026-08-14T16:15:00-04:00") - 1


@pytest.mark.parametrize(
    "window",
    [HistoricalWindow.ANCHORED_INTERVAL, HistoricalWindow.SYNCHRONIZED_INTERVAL],
)
def test_explicit_interval_windows_clip_to_completed_boundary(
    window: HistoricalWindow,
) -> None:
    bounds = _resolve(
        window,
        "2026-08-17T10:43:27-04:00",
        HistoricalWindowParameters(
            start_ns=_ns("2026-08-17T09:30:00-04:00"),
            end_ns=_ns("2026-08-17T11:00:00-04:00"),
        ),
        interval_minutes=5,
    )

    assert bounds.start_ns == _ns("2026-08-17T09:30:00-04:00")
    assert bounds.end_ns == _ns("2026-08-17T10:40:00-04:00") - 1


@pytest.mark.parametrize(
    ("calendar", "window", "policy", "message"),
    [
        (None, HistoricalWindow.CURRENT_RTH, HistoricalWindowParameters(phase="RTH"), "calendar"),
        (_calendar(), HistoricalWindow.CURRENT_RTH, HistoricalWindowParameters(), "phase"),
        (
            _calendar(),
            HistoricalWindow.OPENING_RANGE,
            HistoricalWindowParameters(phase="RTH"),
            "duration_minutes",
        ),
        (
            _calendar(),
            HistoricalWindow.NAMED_PHASE_SLICE,
            HistoricalWindowParameters(phase="RTH", start_offset_minutes=10),
            "requires exactly",
        ),
    ],
)
def test_missing_inputs_fail_deterministically(
    calendar: CalendarProjectionView | None,
    window: HistoricalWindow,
    policy: HistoricalWindowParameters,
    message: str,
) -> None:
    with pytest.raises(HistoricalWindowResolutionError, match=message):
        HistoricalWindowResolver().resolve(
            window,
            calendar=calendar,
            selector_interval_ns=MINUTE_NS,
            as_of_ns=_ns("2026-08-17T10:00:00-04:00"),
            parameters={window: policy},
        )


def test_missing_window_mapping_fails_deterministically() -> None:
    with pytest.raises(HistoricalWindowResolutionError, match="parameters are required"):
        HistoricalWindowResolver().resolve(
            HistoricalWindow.CURRENT_RTH,
            calendar=_calendar(),
            selector_interval_ns=MINUTE_NS,
            as_of_ns=_ns("2026-08-17T10:00:00-04:00"),
            parameters={},
        )


def test_named_slice_with_invalid_bounds_fails_closed() -> None:
    with pytest.raises(HistoricalWindowResolutionError, match="invalid bounds"):
        _resolve(
            HistoricalWindow.NAMED_PHASE_SLICE,
            "2026-08-17T12:00:00-04:00",
            HistoricalWindowParameters(
                phase="RTH",
                start_offset_minutes=120,
                end_offset_minutes=60,
            ),
        )


def test_pre_open_window_defers_until_first_completed_interval() -> None:
    with pytest.raises(HistoricalWindowUnavailable, match="not yet available") as error:
        _resolve(
            HistoricalWindow.CURRENT_RTH,
            "2026-08-17T09:20:00-04:00",
            HistoricalWindowParameters(phase="RTH"),
        )

    assert error.value.retry_at_ns == _ns("2026-08-17T09:31:00-04:00")


def test_closed_market_window_defers_to_next_session_first_completed_interval() -> None:
    with pytest.raises(HistoricalWindowUnavailable) as error:
        _resolve(
            HistoricalWindow.OPENING_RANGE,
            "2026-08-22T09:00:00-04:00",
            HistoricalWindowParameters(phase="RTH", duration_minutes=30),
            interval_minutes=5,
        )

    assert error.value.retry_at_ns == _ns("2026-08-24T09:35:00-04:00")


def test_phase_open_waits_for_first_completed_selector_interval() -> None:
    with pytest.raises(HistoricalWindowUnavailable) as error:
        _resolve(
            HistoricalWindow.OPENING_RANGE,
            "2026-08-17T09:30:30-04:00",
            HistoricalWindowParameters(phase="RTH", duration_minutes=30),
            interval_minutes=5,
        )

    assert error.value.retry_at_ns == _ns("2026-08-17T09:35:00-04:00")

    bounds = _resolve(
        HistoricalWindow.OPENING_RANGE,
        "2026-08-17T09:35:00-04:00",
        HistoricalWindowParameters(phase="RTH", duration_minutes=30),
        interval_minutes=5,
    )
    assert bounds.start_ns == _ns("2026-08-17T09:30:00-04:00")
    assert bounds.end_ns == _ns("2026-08-17T09:35:00-04:00") - 1


def test_invalid_pre_open_window_policy_is_rejected_not_deferred() -> None:
    with pytest.raises(HistoricalWindowResolutionError, match="duration_minutes") as error:
        _resolve(
            HistoricalWindow.OPENING_RANGE,
            "2026-08-17T09:20:00-04:00",
            HistoricalWindowParameters(phase="RTH"),
            interval_minutes=5,
        )

    assert not isinstance(error.value, HistoricalWindowUnavailable)
