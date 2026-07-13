from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from markeitech.persistence import (
    DataFidelity,
    ExplicitSessionCalendar,
    PersistenceConfig,
    PersistenceEventKind,
    RecoveryLifecycleTracker,
    RecoveryMethod,
    RecoveryPlanner,
    RecoveryPlanningError,
    RecoveryPlanStatus,
    RecoveryStatus,
    SessionWindow,
    SQLiteMetadataStore,
)

NOW = datetime(2026, 7, 13, 12, tzinfo=UTC)
START = datetime(2026, 7, 13, 9, tzinfo=UTC)
END = datetime(2026, 7, 13, 9, 10, tzinfo=UTC)


def persistence_config(tmp_path: Path, **updates: object) -> PersistenceConfig:
    return PersistenceConfig(
        catalog_path=tmp_path / "catalog",
        metadata_path=tmp_path / "metadata.sqlite3",
        journal_path=tmp_path / "journal",
        **updates,
    )


def session_calendar() -> ExplicitSessionCalendar:
    return ExplicitSessionCalendar(
        {
            "NQU6.CME": (
                SessionWindow(open_ts=START, close_ts=START + timedelta(minutes=5)),
                SessionWindow(
                    open_ts=START + timedelta(minutes=6),
                    close_ts=END,
                ),
            ),
            "ESU6.CME": (),
        }
    )


def planner(tmp_path: Path, **updates: object) -> RecoveryPlanner:
    return RecoveryPlanner(persistence_config(tmp_path, **updates), session_calendar())


def minute(offset: int) -> datetime:
    return START + timedelta(minutes=offset)


def test_bar_plan_excludes_maintenance_and_merges_only_contiguous_gaps(
    tmp_path: Path,
) -> None:
    observed = [minute(offset) for offset in (0, 1, 4, 6, 8, 9)]

    plan = planner(tmp_path).plan_bars(
        instrument_id="NQU6.CME",
        source="ib",
        start_ts=START,
        end_ts=END,
        observed_open_timestamps=observed,
        now=NOW,
    )

    assert plan.status == RecoveryPlanStatus.REQUIRED
    assert plan.expected_intervals == 9
    assert plan.observed_intervals == 6
    assert plan.missing_intervals == 3
    assert [(item.start_ts, item.end_ts, item.missing_intervals) for item in plan.intervals] == [
        (minute(2), minute(4), 2),
        (minute(7), minute(8), 1),
    ]
    assert [(request.start_ts, request.end_ts) for request in plan.requests] == [
        (minute(2), minute(4)),
        (minute(7), minute(8)),
    ]
    assert all(not request.best_effort for request in plan.requests)


def test_complete_bars_and_expected_closure_need_no_recovery(tmp_path: Path) -> None:
    complete = planner(tmp_path).plan_bars(
        instrument_id="NQU6.CME",
        source="ib",
        start_ts=START,
        end_ts=END,
        observed_open_timestamps=[minute(offset) for offset in (0, 1, 2, 3, 4, 6, 7, 8, 9)],
        now=NOW,
    )
    holiday = planner(tmp_path).plan_bars(
        instrument_id="ESU6.CME",
        source="ib",
        start_ts=START,
        end_ts=END,
        observed_open_timestamps=(),
        now=NOW,
    )

    assert complete.status == RecoveryPlanStatus.NOT_REQUIRED
    assert complete.missing_intervals == 0
    assert complete.intervals == ()
    assert holiday.status == RecoveryPlanStatus.NOT_REQUIRED
    assert holiday.reason_codes == (RecoveryMethod.EXPECTED_SESSION_CLOSURE.value,)
    assert holiday.intervals[0].method == RecoveryMethod.EXPECTED_SESSION_CLOSURE


def test_requests_split_at_configured_size_and_fail_at_plan_limit(tmp_path: Path) -> None:
    split = planner(
        tmp_path,
        recovery_max_intervals_per_request=2,
        recovery_max_requests_per_plan=5,
    ).plan_bars(
        instrument_id="NQU6.CME",
        source="ib",
        start_ts=START,
        end_ts=START + timedelta(minutes=5),
        observed_open_timestamps=(),
        now=NOW,
    )

    assert [request.expected_intervals for request in split.requests] == [2, 2, 1]

    with pytest.raises(RecoveryPlanningError, match="request limit"):
        planner(
            tmp_path,
            recovery_max_intervals_per_request=1,
            recovery_max_requests_per_plan=2,
        ).plan_bars(
            instrument_id="NQU6.CME",
            source="ib",
            start_ts=START,
            end_ts=START + timedelta(minutes=5),
            observed_open_timestamps=(),
            now=NOW,
        )


def test_bar_plan_rejects_non_minute_observations(tmp_path: Path) -> None:
    with pytest.raises(RecoveryPlanningError, match="not minute-aligned"):
        planner(tmp_path).plan_bars(
            instrument_id="NQU6.CME",
            source="ib",
            start_ts=START,
            end_ts=END,
            observed_open_timestamps=(START + timedelta(seconds=1),),
            now=NOW,
        )


def test_history_older_than_provider_lookback_stays_explicitly_unavailable(
    tmp_path: Path,
) -> None:
    old_start = datetime(2026, 6, 1, 9, tzinfo=UTC)
    old_end = old_start + timedelta(minutes=3)
    calendar = ExplicitSessionCalendar(
        {"NQU6.CME": (SessionWindow(open_ts=old_start, close_ts=old_end),)}
    )
    recovery_planner = RecoveryPlanner(
        persistence_config(tmp_path, recovery_max_lookback_days=5),
        calendar,
    )

    plan = recovery_planner.plan_bars(
        instrument_id="NQU6.CME",
        source="ib",
        start_ts=old_start,
        end_ts=old_end,
        observed_open_timestamps=(),
        now=NOW,
    )

    assert plan.status == RecoveryPlanStatus.DEGRADED
    assert plan.missing_intervals == 3
    assert plan.requests == ()
    assert plan.intervals[0].method == RecoveryMethod.UNAVAILABLE_BAR_HISTORY
    assert plan.intervals[0].fidelity == DataFidelity.UNAVAILABLE


@pytest.mark.parametrize(
    "journal_available,historical_available,method,fidelity,request_count",
    [
        (True, False, RecoveryMethod.EXACT_WAL_REPLAY, DataFidelity.REPORTED, 0),
        (
            False,
            True,
            RecoveryMethod.BEST_EFFORT_TICK_BACKFILL,
            DataFidelity.PARTIAL,
            1,
        ),
        (
            False,
            False,
            RecoveryMethod.UNRECOVERABLE_TICK_GAP,
            DataFidelity.UNAVAILABLE,
            0,
        ),
    ],
)
def test_tick_recovery_never_overstates_unjournaled_completeness(
    tmp_path: Path,
    journal_available: bool,
    historical_available: bool,
    method: RecoveryMethod,
    fidelity: DataFidelity,
    request_count: int,
) -> None:
    plan = planner(tmp_path).plan_tick_gap(
        instrument_id="NQU6.CME",
        event_kind=PersistenceEventKind.QUOTE_TICK,
        source="ib",
        start_ts=minute(2),
        end_ts=minute(3),
        now=NOW,
        journal_available=journal_available,
        historical_backfill_available=historical_available,
    )

    assert plan.intervals[0].method == method
    assert plan.intervals[0].fidelity == fidelity
    assert len(plan.requests) == request_count
    if plan.requests:
        assert plan.requests[0].best_effort is True
        assert plan.status == RecoveryPlanStatus.DEGRADED


def test_recovery_lifecycle_persists_complete_and_degraded_outcomes(tmp_path: Path) -> None:
    config = persistence_config(tmp_path)
    store = SQLiteMetadataStore(config)
    tracker = RecoveryLifecycleTracker(store)
    plan = RecoveryPlanner(config, session_calendar()).plan_bars(
        instrument_id="NQU6.CME",
        source="ib",
        start_ts=START,
        end_ts=END,
        observed_open_timestamps=[minute(offset) for offset in (0, 1, 4, 6, 8, 9)],
        now=NOW,
    )

    pending = tracker.begin(plan, NOW)
    recovering = tracker.mark_recovering(pending, NOW + timedelta(seconds=1))
    complete = tracker.finish(
        recovering,
        remaining_intervals=0,
        now=NOW + timedelta(seconds=2),
    )

    assert complete.status == RecoveryStatus.COMPLETE
    assert store.load_recovery(plan.recovery_id) == complete
    assert tracker.begin(plan, NOW + timedelta(seconds=3)) == complete
    regressed = pending.model_copy(update={"updated_ts": NOW + timedelta(seconds=3)})
    with pytest.raises(ValueError, match="cannot move from complete to pending"):
        store.save_recovery(regressed)
    store.close()


def test_recovery_lifecycle_requires_reasons_for_remaining_damage(tmp_path: Path) -> None:
    config = persistence_config(tmp_path)
    store = SQLiteMetadataStore(config)
    tracker = RecoveryLifecycleTracker(store)
    plan = RecoveryPlanner(config, session_calendar()).plan_tick_gap(
        instrument_id="NQU6.CME",
        event_kind=PersistenceEventKind.TRADE_TICK,
        source="ib",
        start_ts=minute(2),
        end_ts=minute(3),
        now=NOW,
        journal_available=False,
        historical_backfill_available=False,
    )
    recovering = tracker.mark_recovering(tracker.begin(plan, NOW), NOW + timedelta(seconds=1))

    with pytest.raises(ValueError, match="requires reason codes"):
        tracker.finish(
            recovering,
            remaining_intervals=1,
            now=NOW + timedelta(seconds=2),
        )

    degraded = tracker.finish(
        recovering,
        remaining_intervals=1,
        now=NOW + timedelta(seconds=2),
        reason_codes=("unrecoverable_tick_gap",),
    )
    assert degraded.status == RecoveryStatus.DEGRADED
    assert degraded.missing_intervals == 1
    store.close()


def test_calendar_rejects_overlapping_windows() -> None:
    with pytest.raises(ValueError, match="overlap"):
        ExplicitSessionCalendar(
            {
                "NQU6.CME": (
                    SessionWindow(open_ts=START, close_ts=minute(5)),
                    SessionWindow(open_ts=minute(4), close_ts=END),
                )
            }
        )


def test_calendar_does_not_mistake_missing_configuration_for_a_holiday(
    tmp_path: Path,
) -> None:
    with pytest.raises(RecoveryPlanningError, match="not configured"):
        planner(tmp_path).plan_bars(
            instrument_id="YM.USEQUITY",
            source="ib",
            start_ts=START,
            end_ts=END,
            observed_open_timestamps=(),
            now=NOW,
        )
