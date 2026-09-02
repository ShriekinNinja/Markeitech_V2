from __future__ import annotations

from datetime import date
from decimal import Decimal

from markeitech.acquisition import HistoricalWindow
from markeitech.intelligence import (
    CompletedBarInput,
    CompletedBarSource,
    MetricFidelity,
    MetricHealth,
    MetricRegistry,
)
from markeitech.intelligence.session_references import (
    ACTIVE_SESSION_METRIC_IDS,
    GAP_METRIC_IDS,
    PREVIOUS_SESSION_METRIC_IDS,
    SessionReferenceBook,
    SessionReferenceCatalogPolicy,
    SessionReferenceRole,
    SessionWindowSpec,
    calculate_session_reference_metrics,
    session_reference_metric_definitions,
)

MINUTE_NS = 60 * 1_000_000_000


def _policy() -> SessionReferenceCatalogPolicy:
    return SessionReferenceCatalogPolicy(
        live_selector="5-SECOND-LAST-EXTERNAL",
        historical_selector="15-MINUTE-LAST-EXTERNAL",
        active_window=HistoricalWindow.SESSION_TO_DATE,
        previous_window=HistoricalWindow.PREVIOUS_SESSIONS,
        overnight_window=HistoricalWindow.CURRENT_OVERNIGHT,
        minimum_historical_observations=1,
        maximum_historical_observations=100,
        vwap_price_basis="typical",
        vwap_price_basis_dynamic=True,
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


def test_catalog_declares_purpose_specific_reference_dependencies() -> None:
    registry = MetricRegistry(session_reference_metric_definitions(_policy()))

    active = registry.get("active_session.open", 1)
    previous = registry.get("previous_session.close", 1)
    gap = registry.get("gap.opening.points", 1)

    assert active.live_inputs[0].selector == "5-SECOND-LAST-EXTERNAL"
    assert active.historical_inputs[0].selector == "15-MINUTE-LAST-EXTERNAL"
    assert active.historical_inputs[0].window is HistoricalWindow.SESSION_TO_DATE
    assert previous.historical_inputs[0].window is HistoricalWindow.PREVIOUS_SESSIONS
    assert previous.historical_inputs[0].window_parameters == {
        "phase_source": "analytical_profile.primary_phase",
        "session_count": 1,
    }
    assert tuple(item.metric_id for item in gap.metric_inputs) == (
        "active_session.open",
        "previous_session.close",
    )
    assert registry.get("active_session.start_ns", 1).unit == "unix_ns"
    assert registry.get("active_session.complete", 1).unit == "boolean"


def test_history_live_overlap_is_arrival_order_independent() -> None:
    spec = SessionWindowSpec(
        role=SessionReferenceRole.ACTIVE,
        session_id="cme_equity:2026-08-21:OPEN",
        start_ns=0,
        end_ns=60 * MINUTE_NS,
        complete=False,
    )
    historical = (
        _bar(0, 15, open_="100", high="103", low="99", close="102", volume="150"),
        _bar(15, 15, open_="102", high="105", low="101", close="104", volume="180"),
    )
    overlapping_live = _bar(
        29,
        1,
        open_="104",
        high="110",
        low="103",
        close="109",
        volume="999",
        source=CompletedBarSource.LIVE_AGGREGATE,
    )
    continuing_live = _bar(
        30,
        1,
        open_="104",
        high="106",
        low="103",
        close="105",
        volume="20",
        source=CompletedBarSource.LIVE_AGGREGATE,
    )

    history_first = _book()
    history_first.ingest_historical(spec, historical, cutoff_ns=30 * MINUTE_NS - 1)
    history_first.ingest_live(spec, overlapping_live)
    history_first.ingest_live(spec, continuing_live)

    live_first = _book()
    live_first.ingest_live(spec, overlapping_live)
    live_first.ingest_live(spec, continuing_live)
    live_first.ingest_historical(spec, historical, cutoff_ns=30 * MINUTE_NS - 1)

    assert history_first.summary(SessionReferenceRole.ACTIVE) == live_first.summary(
        SessionReferenceRole.ACTIVE,
    )
    summary = history_first.summary(SessionReferenceRole.ACTIVE)
    assert summary is not None
    assert summary.high == Decimal("106")
    assert summary.volume == Decimal("350")
    assert summary.coverage_ratio == Decimal(1)


def test_live_bar_at_actual_historical_boundary_is_retained() -> None:
    spec = SessionWindowSpec(
        role=SessionReferenceRole.ACTIVE,
        session_id="cme_equity:2026-08-21:OPEN",
        start_ns=0,
        end_ns=60 * MINUTE_NS,
        complete=False,
    )
    book = _book()
    book.ingest_historical(
        spec,
        (
            _bar(0, 15, open_="100", high="102", low="99", close="101", volume="10"),
            _bar(15, 15, open_="101", high="103", low="100", close="102", volume="10"),
        ),
        cutoff_ns=30 * MINUTE_NS,
    )
    book.ingest_live(
        spec,
        _bar(
            30,
            1,
            open_="102",
            high="104",
            low="101",
            close="103",
            volume="5",
            source=CompletedBarSource.LIVE_AGGREGATE,
        ),
    )

    summary = book.summary(SessionReferenceRole.ACTIVE)

    assert summary is not None
    assert summary.close == Decimal("103")
    assert summary.high == Decimal("104")
    assert summary.volume == Decimal("25")


def test_price_and_opening_gap_survive_unsupported_volume() -> None:
    registry = MetricRegistry(session_reference_metric_definitions(_policy()))
    previous_book = _book()
    previous = SessionWindowSpec(
        role=SessionReferenceRole.PREVIOUS,
        session_id="us_equities:2026-08-20:OPEN",
        start_ns=0,
        end_ns=30 * MINUTE_NS,
        complete=True,
    )
    previous_book.ingest_historical(
        previous,
        (
            _bar(
                0,
                15,
                open_="100",
                high="103",
                low="99",
                close="102",
                volume=None,
                session_id=previous.session_id,
            ),
            _bar(
                15,
                15,
                open_="102",
                high="104",
                low="101",
                close="103",
                volume=None,
                session_id=previous.session_id,
            ),
        ),
        cutoff_ns=30 * MINUTE_NS - 1,
    )
    active = SessionWindowSpec(
        role=SessionReferenceRole.ACTIVE,
        session_id="us_equities:2026-08-21:OPEN",
        start_ns=30 * MINUTE_NS,
        end_ns=60 * MINUTE_NS,
        complete=False,
    )
    previous_book.ingest_live(
        active,
        _bar(
            30,
            1,
            open_="105",
            high="106",
            low="104",
            close="105",
            volume=None,
            session_id=active.session_id,
        ),
    )
    snapshot = previous_book.snapshot()

    values = calculate_session_reference_metrics(
        snapshot,
        registry=registry,
        parameter_version=1,
        calculated_ts_ns=61 * MINUTE_NS,
        published_ts_ns=61 * MINUTE_NS,
        source="SESSION-METRICS",
        revision=1,
    )
    by_id = {value.metric_id: value for value in values}

    assert by_id["active_session.open"].value == Decimal("105")
    assert by_id["active_session.start_ns"].value == active.start_ns
    assert by_id["active_session.end_ns"].value == active.end_ns
    assert by_id["active_session.complete"].value is False
    assert by_id["previous_session.close"].value == Decimal("103")
    assert by_id["previous_session.start_ns"].value == previous.start_ns
    assert by_id["previous_session.end_ns"].value == previous.end_ns
    assert by_id["previous_session.complete"].value is True
    assert by_id["gap.opening.points"].value == Decimal("2")
    assert by_id["active_session.volume"].value is None
    assert by_id["active_session.volume"].health is MetricHealth.UNSUPPORTED
    assert by_id["active_session.bar_vwap_estimate"].missing_reasons == ("volume_unsupported",)
    assert by_id["gap.indicative.points"].missing_reasons == ("overnight_not_configured",)


def test_missing_time_degrades_coverage_without_suppressing_values() -> None:
    book = _book()
    spec = SessionWindowSpec(
        role=SessionReferenceRole.PREVIOUS,
        session_id="cme_equity:2026-08-20:OPEN",
        start_ns=0,
        end_ns=30 * MINUTE_NS,
        complete=True,
    )
    book.ingest_historical(
        spec,
        (
            _bar(
                0,
                15,
                open_="100",
                high="101",
                low="99",
                close="100",
                volume="10",
                session_id=spec.session_id,
            ),
        ),
        cutoff_ns=30 * MINUTE_NS - 1,
    )

    summary = book.summary(SessionReferenceRole.PREVIOUS)
    assert summary is not None
    assert summary.coverage_ratio == Decimal("0.5")
    assert summary.health is MetricHealth.DEGRADED
    assert summary.opening_observed is True
    assert summary.closing_observed is False
    assert summary.missing_reasons == (
        "session_close_not_observed",
        "session_coverage_below_threshold",
    )
    values = calculate_session_reference_metrics(
        book.snapshot(),
        registry=MetricRegistry(session_reference_metric_definitions(_policy())),
        parameter_version=1,
        calculated_ts_ns=31 * MINUTE_NS,
        published_ts_ns=31 * MINUTE_NS,
        source="SESSION-METRICS",
        revision=1,
    )
    by_id = {value.metric_id: value for value in values}
    assert by_id["previous_session.high"].value == Decimal("101")
    assert by_id["previous_session.high"].health is MetricHealth.DEGRADED
    assert by_id["previous_session.close"].value is None
    assert by_id["previous_session.close"].missing_reasons == ("session_close_not_observed",)


def test_opening_gap_waits_for_the_actual_active_session_open() -> None:
    registry = MetricRegistry(session_reference_metric_definitions(_policy()))
    book = _book()
    previous = SessionWindowSpec(
        role=SessionReferenceRole.PREVIOUS,
        session_id="cme_equity:2026-08-20:OPEN",
        start_ns=0,
        end_ns=30 * MINUTE_NS,
        complete=True,
    )
    book.ingest_historical(
        previous,
        (
            _bar(
                0,
                15,
                open_="100",
                high="102",
                low="99",
                close="101",
                volume="10",
                session_id=previous.session_id,
            ),
            _bar(
                15,
                15,
                open_="101",
                high="103",
                low="100",
                close="102",
                volume="10",
                session_id=previous.session_id,
            ),
        ),
        cutoff_ns=30 * MINUTE_NS,
    )
    active = SessionWindowSpec(
        role=SessionReferenceRole.ACTIVE,
        session_id="cme_equity:2026-08-21:OPEN",
        start_ns=30 * MINUTE_NS,
        end_ns=60 * MINUTE_NS,
        complete=False,
    )
    book.ingest_live(
        active,
        _bar(
            31,
            1,
            open_="105",
            high="106",
            low="104",
            close="105",
            volume="5",
            source=CompletedBarSource.LIVE_AGGREGATE,
            session_id=active.session_id,
        ),
    )

    values = calculate_session_reference_metrics(
        book.snapshot(),
        registry=registry,
        parameter_version=1,
        calculated_ts_ns=61 * MINUTE_NS,
        published_ts_ns=61 * MINUTE_NS,
        source="SESSION-METRICS",
        revision=1,
    )
    by_id = {value.metric_id: value for value in values}

    assert by_id["active_session.open"].value is None
    assert by_id["active_session.open"].missing_reasons == ("session_open_not_observed",)
    assert by_id["active_session.latest_close"].value == Decimal("105")
    assert by_id["gap.opening.points"].value is None
    assert by_id["gap.opening.points"].missing_reasons == ("active_session_open_not_observed",)


def _book() -> SessionReferenceBook:
    return SessionReferenceBook(
        instrument_id="ESU6.CME",
        price_basis="typical",
        minimum_coverage_ratio=0.8,
        maximum_retained_sessions=4,
        maximum_observations_per_session=100,
    )


def _bar(
    start_minute: int,
    duration_minutes: int,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
    volume: str | None,
    source: CompletedBarSource = CompletedBarSource.HISTORICAL_PROVIDER,
    session_id: str = "cme_equity:2026-08-21:OPEN",
) -> CompletedBarInput:
    start_ns = start_minute * MINUTE_NS
    end_ns = start_ns + duration_minutes * MINUTE_NS
    return CompletedBarInput(
        instrument_id="ESU6.CME",
        bar_specification=f"{duration_minutes}-MINUTE-LAST-EXTERNAL",
        calendar_id="cme_equity",
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        trade_date=date(2026, 8, 21),
        session_id=session_id,
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
        evidence_refs=(f"bar:{start_minute}:{duration_minutes}",),
        complete=True,
        missing_reasons=() if volume is not None else ("volume_unsupported",),
    )


assert set(ACTIVE_SESSION_METRIC_IDS)
assert set(PREVIOUS_SESSION_METRIC_IDS)
assert set(GAP_METRIC_IDS)
