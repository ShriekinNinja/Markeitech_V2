from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

from markeitech.intelligence import (
    AnalyticalWindowBook,
    AnalyticalWindowPolicy,
    CompletedBarInput,
    CompletedBarSource,
    MetricFidelity,
    MetricHealth,
    MetricRegistry,
    analytical_window_metric_definitions,
    calculate_analytical_window_metrics,
    resolve_analytical_window,
    resolve_historical_analytical_window,
)
from markeitech.intelligence.session import SessionSnapshot, SessionWindow

MINUTE_NS = 60 * 1_000_000_000


def test_catalog_preserves_window_specific_dependency_and_parameter_envelopes() -> None:
    policy = _policy(purpose="opening_range", window_id="or_fast", duration_minutes=5)
    registry = MetricRegistry(analytical_window_metric_definitions((policy,)))

    high = registry.get(f"{policy.metric_prefix}.high", 1)

    assert high.historical_inputs[0].selector == "1-MINUTE-LAST-EXTERNAL"
    assert high.historical_inputs[0].window.value == "opening_range"
    assert dict(high.historical_inputs[0].window_parameters) == {
        "phase_source": "analytical_profile:cme_equity_primary:OPEN",
        "anchor_boundary": "start",
        "offset_seconds": 0,
        "duration_seconds": 300,
    }
    duration = next(item for item in high.parameters if item.parameter_id == "duration_seconds")
    assert duration.dynamic is True
    assert duration.minimum == 60
    assert duration.maximum == 1_800


def test_calendar_relative_windows_follow_actual_session_close() -> None:
    session = SessionWindow(
        trade_date=date(2026, 11, 27),
        phase="OPEN",
        start_ns=0,
        end_ns=210 * MINUTE_NS,
    )
    opening = resolve_analytical_window(
        _policy(purpose="opening_range", window_id="or_fast", duration_minutes=5),
        session,
        session_id="cme_equity:2026-11-27:OPEN",
    )
    power = resolve_analytical_window(
        _policy(
            purpose="power_hour",
            window_id="power_hour",
            duration_minutes=60,
            anchor_boundary="end",
            offset_seconds=-3_600,
            selector="15-MINUTE-LAST-EXTERNAL",
            maximum_observations=4,
        ),
        session,
        session_id="cme_equity:2026-11-27:OPEN",
    )

    assert (opening.start_ns, opening.end_ns) == (0, 5 * MINUTE_NS)
    assert (power.start_ns, power.end_ns) == (150 * MINUTE_NS, 210 * MINUTE_NS)


def test_historical_window_uses_request_session_identity() -> None:
    policy = _policy(
        purpose="power_hour",
        window_id="power_hour",
        duration_minutes=60,
        anchor_boundary="end",
        offset_seconds=-3_600,
        selector="15-MINUTE-LAST-EXTERNAL",
        maximum_observations=4,
    )
    session = SessionWindow(date(2026, 8, 20), "OPEN", 0, 1_380 * MINUTE_NS)

    class Calendar:
        def evaluate(self, _timestamp_ns: int) -> SessionSnapshot:
            return SessionSnapshot(
                calendar_id="cme_equity",
                schedule_version="test",
                timezone="UTC",
                trade_date=session.trade_date,
                phase=session.phase,
                phase_open_ns=session.start_ns,
                phase_close_ns=session.end_ns,
                next_transition_ns=session.end_ns,
            )

        def windows(self, _start: date, _end: date) -> tuple[SessionWindow, ...]:
            return (session,)

    trade_date, spec = resolve_historical_analytical_window(
        policy,
        Calendar(),  # type: ignore[arg-type]
        calendar_id="cme_equity",
        request_start_ns=1_320 * MINUTE_NS,
    )

    assert trade_date == date(2026, 8, 20)
    assert spec.session_id == "cme_equity:2026-08-20:OPEN"
    assert spec.start_ns == 1_320 * MINUTE_NS
    assert spec.end_ns == 1_380 * MINUTE_NS


def test_opening_range_freezes_bounds_and_tracks_post_range_distance() -> None:
    policy = _policy(purpose="opening_range", window_id="or_fast", duration_minutes=5)
    spec = resolve_analytical_window(
        policy,
        SessionWindow(date(2026, 8, 21), "OPEN", 0, 390 * MINUTE_NS),
        session_id="cme_equity:2026-08-21:OPEN",
    )
    book = AnalyticalWindowBook(
        instrument_id="ESU6.CME",
        policy=policy,
        maximum_observations_per_session=100,
    )
    opening = tuple(
        _bar(
            minute,
            open_=str(100 + minute),
            high=str(101 + minute),
            low=str(99 + minute),
            close=str(100.5 + minute),
        )
        for minute in range(5)
    )
    book.ingest_historical(spec, opening, cutoff_ns=5 * MINUTE_NS)
    book.ingest_live(
        spec,
        _bar(
            6,
            open_="108",
            high="111",
            low="107",
            close="110",
            source=CompletedBarSource.LIVE_AGGREGATE,
        ),
    )

    summary = book.summary(as_of_ns=7 * MINUTE_NS)

    assert summary is not None
    assert summary.complete is True
    assert summary.high == Decimal("105")
    assert summary.low == Decimal("99")
    assert summary.latest_close == Decimal("110")
    registry = MetricRegistry(analytical_window_metric_definitions((policy,)))
    values = calculate_analytical_window_metrics(
        "ESU6.CME",
        policy,
        summary,
        registry=registry,
        parameter_version=1,
        calculated_ts_ns=8 * MINUTE_NS,
        published_ts_ns=8 * MINUTE_NS,
        source="SESSION-METRICS",
        revision=1,
    )
    by_id = {value.metric_id: value for value in values}
    assert by_id[f"{policy.metric_prefix}.open"].value == Decimal("100")
    assert by_id[f"{policy.metric_prefix}.close"].value == Decimal("104.5")
    assert by_id[f"{policy.metric_prefix}.volume"].value == Decimal("50")
    assert by_id[f"{policy.metric_prefix}.distance_above_high_points"].value == Decimal("5")
    assert by_id[f"{policy.metric_prefix}.distance_below_low_points"].value == Decimal("0")


def test_opening_range_price_evidence_does_not_depend_on_volume() -> None:
    policy = _policy(purpose="opening_range", window_id="or_fast", duration_minutes=5)
    spec = resolve_analytical_window(
        policy,
        SessionWindow(date(2026, 8, 21), "OPEN", 0, 390 * MINUTE_NS),
        session_id="cme_equity:2026-08-21:OPEN",
    )
    book = AnalyticalWindowBook(
        instrument_id="ESU6.CME",
        policy=policy,
        maximum_observations_per_session=20,
    )
    bars = tuple(
        _bar(
            minute,
            open_="100",
            high="101",
            low="99",
            close="100",
            volume=None,
        )
        for minute in range(5)
    )
    book.ingest_historical(spec, bars, cutoff_ns=5 * MINUTE_NS)

    summary = book.summary(as_of_ns=6 * MINUTE_NS)

    assert summary is not None
    assert summary.health is MetricHealth.READY
    assert summary.fidelity is MetricFidelity.DERIVED
    assert summary.missing_reasons == ()
    assert summary.volume is None
    assert summary.volume_missing_reasons == ("volume_unsupported",)

    registry = MetricRegistry(analytical_window_metric_definitions((policy,)))
    values = calculate_analytical_window_metrics(
        "ESU6.CME",
        policy,
        summary,
        registry=registry,
        parameter_version=1,
        calculated_ts_ns=7 * MINUTE_NS,
        published_ts_ns=7 * MINUTE_NS,
        source="SESSION-METRICS",
        revision=1,
    )
    by_id = {value.metric_id: value for value in values}
    assert by_id[f"{policy.metric_prefix}.high"].health is MetricHealth.READY
    assert by_id[f"{policy.metric_prefix}.volume"].value is None
    assert by_id[f"{policy.metric_prefix}.volume"].health is MetricHealth.UNSUPPORTED
    assert by_id[f"{policy.metric_prefix}.volume"].missing_reasons == (
        "volume_unsupported",
    )


def test_power_hour_reports_only_ohlcv_derived_evidence() -> None:
    policy = _policy(
        purpose="power_hour",
        window_id="power_hour",
        duration_minutes=60,
        anchor_boundary="end",
        offset_seconds=-3_600,
        selector="15-MINUTE-LAST-EXTERNAL",
        maximum_observations=4,
    )
    session_id = "cme_equity:2026-08-21:OPEN"
    spec = resolve_analytical_window(
        policy,
        SessionWindow(date(2026, 8, 21), "OPEN", 0, 390 * MINUTE_NS),
        session_id=session_id,
    )
    book = AnalyticalWindowBook(
        instrument_id="ESU6.CME",
        policy=policy,
        maximum_observations_per_session=20,
    )
    bars = (
        _bar(330, duration=15, open_="100", high="103", low="99", close="102"),
        _bar(345, duration=15, open_="102", high="104", low="101", close="103"),
        _bar(360, duration=15, open_="103", high="104", low="100", close="101"),
        _bar(375, duration=15, open_="101", high="106", low="100", close="105"),
    )
    book.ingest_historical(spec, bars, cutoff_ns=390 * MINUTE_NS)

    summary = book.summary(as_of_ns=391 * MINUTE_NS)

    assert summary is not None
    assert summary.complete is True
    assert summary.open == Decimal("100")
    assert summary.close == Decimal("105")
    assert summary.range == Decimal("7")
    assert summary.directional_efficiency == Decimal(3) / Decimal(7)
    assert summary.coverage_ratio == Decimal("1")


def test_pre_window_live_bar_preserves_previous_power_hour_summary() -> None:
    policy = _policy(
        purpose="power_hour",
        window_id="power_hour",
        duration_minutes=60,
        anchor_boundary="end",
        offset_seconds=-3_600,
        selector="15-MINUTE-LAST-EXTERNAL",
        maximum_observations=4,
    )
    previous_session_id = "cme_equity:2026-08-20:OPEN"
    current_session_id = "cme_equity:2026-08-21:OPEN"
    previous_spec = resolve_analytical_window(
        policy,
        SessionWindow(date(2026, 8, 20), "OPEN", 0, 390 * MINUTE_NS),
        session_id=previous_session_id,
    )
    current_spec = resolve_analytical_window(
        policy,
        SessionWindow(
            date(2026, 8, 21),
            "OPEN",
            1_440 * MINUTE_NS,
            1_830 * MINUTE_NS,
        ),
        session_id=current_session_id,
    )
    book = AnalyticalWindowBook(
        instrument_id="ESU6.CME",
        policy=policy,
        maximum_observations_per_session=20,
    )
    previous_bars = tuple(
        replace(
            _bar(
                330 + index * 15,
                duration=15,
                open_=str(100 + index),
                high=str(102 + index),
                low=str(99 + index),
                close=str(101 + index),
            ),
            trade_date=date(2026, 8, 20),
            session_id=previous_session_id,
        )
        for index in range(4)
    )
    book.ingest_historical(previous_spec, previous_bars, cutoff_ns=390 * MINUTE_NS)
    pre_window_bar = replace(
        _bar(
            1_500,
            duration=1,
            open_="110",
            high="111",
            low="109",
            close="110",
            source=CompletedBarSource.LIVE_AGGREGATE,
        ),
        session_id=current_session_id,
    )

    book.ingest_live(current_spec, pre_window_bar)
    summary = book.summary(as_of_ns=1_501 * MINUTE_NS)

    assert summary is not None
    assert summary.session_id == previous_session_id


def test_unsupported_volume_does_not_hide_price_measurements() -> None:
    policy = _policy(
        purpose="power_hour",
        window_id="power_hour",
        duration_minutes=60,
        anchor_boundary="end",
        offset_seconds=-3_600,
        selector="15-MINUTE-LAST-EXTERNAL",
        maximum_observations=4,
    )
    spec = resolve_analytical_window(
        policy,
        SessionWindow(date(2026, 8, 21), "OPEN", 0, 390 * MINUTE_NS),
        session_id="cme_equity:2026-08-21:OPEN",
    )
    book = AnalyticalWindowBook(
        instrument_id="ESU6.CME",
        policy=policy,
        maximum_observations_per_session=20,
    )
    bars = tuple(
        _bar(
            330 + index * 15,
            duration=15,
            open_=str(100 + index),
            high=str(102 + index),
            low=str(99 + index),
            close=str(101 + index),
            volume=None,
        )
        for index in range(4)
    )
    book.ingest_historical(spec, bars, cutoff_ns=390 * MINUTE_NS)
    summary = book.summary(as_of_ns=391 * MINUTE_NS)
    assert summary is not None
    registry = MetricRegistry(analytical_window_metric_definitions((policy,)))

    values = calculate_analytical_window_metrics(
        "ESU6.CME",
        policy,
        summary,
        registry=registry,
        parameter_version=1,
        calculated_ts_ns=392 * MINUTE_NS,
        published_ts_ns=392 * MINUTE_NS,
        source="SESSION-METRICS",
        revision=1,
    )
    by_id = {value.metric_id: value for value in values}

    assert by_id[f"{policy.metric_prefix}.high"].value == Decimal("105")
    assert by_id[f"{policy.metric_prefix}.volume"].value is None
    assert by_id[f"{policy.metric_prefix}.volume"].health is MetricHealth.UNSUPPORTED


def _policy(
    *,
    purpose: str,
    window_id: str,
    duration_minutes: int,
    anchor_boundary: str = "start",
    offset_seconds: int = 0,
    selector: str = "1-MINUTE-LAST-EXTERNAL",
    maximum_observations: int = 60,
) -> AnalyticalWindowPolicy:
    return AnalyticalWindowPolicy(
        profile_id="cme_equity_primary",
        profile_version=1,
        window_id=window_id,
        purpose=purpose,
        anchor_phase="OPEN",
        anchor_boundary=anchor_boundary,
        offset_seconds=offset_seconds,
        duration_seconds=duration_minutes * 60,
        minimum_duration_seconds=60 if purpose == "opening_range" else 1_800,
        maximum_duration_seconds=1_800 if purpose == "opening_range" else 7_200,
        duration_step_seconds=60 if purpose == "opening_range" else 300,
        duration_dynamic=True,
        live_selector="5-SECOND-LAST-EXTERNAL",
        historical_selector=selector,
        minimum_historical_observations=1,
        maximum_historical_observations=maximum_observations,
        price_basis="typical",
        price_basis_dynamic=True,
        minimum_coverage_ratio=0.8,
        minimum_coverage_ratio_floor=0.5,
        minimum_coverage_ratio_ceiling=1.0,
        minimum_coverage_ratio_step=0.05,
        minimum_coverage_ratio_dynamic=True,
        parameter_source="operator-reviewed-config",
        priority=40,
        maximum_retained_sessions=4,
        maximum_output_age_ms=120_000,
    )


def _bar(
    start_minute: int,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
    duration: int = 1,
    volume: str | None = "10",
    source: CompletedBarSource = CompletedBarSource.HISTORICAL_PROVIDER,
) -> CompletedBarInput:
    start_ns = start_minute * MINUTE_NS
    end_ns = start_ns + duration * MINUTE_NS
    return CompletedBarInput(
        instrument_id="ESU6.CME",
        bar_specification=f"{duration}-MINUTE-LAST-EXTERNAL",
        calendar_id="cme_equity",
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        trade_date=date(2026, 8, 21),
        session_id="cme_equity:2026-08-21:OPEN",
        window_id="primary",
        interval_start_ns=start_ns,
        interval_end_ns=end_ns,
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal(volume) if volume is not None else None,
        source=source,
        observed_ts_ns=end_ns,
        received_ts_ns=end_ns + 1,
        normalized_ts_ns=end_ns + 1,
        health=MetricHealth.READY,
        fidelity=MetricFidelity.REPORTED,
        evidence_refs=(f"bar:{start_minute}:{duration}",),
        complete=True,
        missing_reasons=() if volume is not None else ("volume_unsupported",),
    )
