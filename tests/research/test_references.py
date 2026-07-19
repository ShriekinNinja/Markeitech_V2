from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from markeitech.analytics import (
    AnalyticsInputFidelity,
    AnalyticsTimeframe,
    FeatureInputLineage,
    MarketContextFeatureSnapshot,
    MarketContextSnapshot,
    TrendState,
    VwapPosition,
)
from markeitech.domain.market_data import OneMinuteBar
from markeitech.research import (
    EvidenceJoinStatus,
    ExpectedLifecycle,
    ReferenceAnnotation,
    SignalAuditHistory,
    SignalCandidateJoinStatus,
    enrich_reference_annotations,
    render_reference_report,
    sync_reference_csv,
    write_reference_artifacts,
)
from markeitech.signals import (
    LocationSourceKind,
    SignalDirection,
    SignalEvidenceFidelity,
    SignalEvidenceReference,
    SignalEvidenceStage,
    SignalEvidenceType,
    SignalFamily,
    SignalLocationMatch,
    SignalLocationZone,
    SignalLocationZoneKind,
    SignalSnapshot,
    SignalStatus,
    signal_setup_key,
    transition_signal,
)

NOW = datetime(2026, 7, 16, 22, 50, tzinfo=UTC)
INSTRUMENT = "NQU6.CME"
SCREENSHOT = "2026-07-16T22-50Z_NQ_1m_short_resistance-poc-val-rejection.png"


class FixedCalendar:
    def session_window(
        self,
        instrument_id: str,
        timestamp: datetime,
    ) -> tuple[datetime, datetime]:
        assert instrument_id == INSTRUMENT
        return NOW - timedelta(hours=1), NOW + timedelta(hours=2)

    def expected_minute_opens(
        self,
        instrument_id: str,
        start_ts: datetime,
        end_ts: datetime,
    ) -> tuple[datetime, ...]:
        assert instrument_id == INSTRUMENT
        cursor = start_ts.replace(second=0, microsecond=0)
        if cursor < start_ts:
            cursor += timedelta(minutes=1)
        values = []
        while cursor < end_ts:
            values.append(cursor)
            cursor += timedelta(minutes=1)
        return tuple(values)


def test_sync_infers_draft_fields_and_rejects_changed_screenshot(tmp_path: Path) -> None:
    workspace = tmp_path / "reference-set"
    screenshots = workspace / "screenshots"
    screenshots.mkdir(parents=True)
    image = screenshots / SCREENSHOT
    image.write_bytes(b"reference-image-v1")

    annotation = sync_reference_csv(workspace, instrument_aliases={"NQ": INSTRUMENT})[0]

    assert annotation.instrument_id == INSTRUMENT
    assert annotation.chart_timeframe == AnalyticsTimeframe.ONE_MINUTE
    assert annotation.observed_ts == NOW
    assert annotation.candidate_ts == NOW
    assert annotation.direction == SignalDirection.SHORT
    assert annotation.setup_family == "resistance_poc_val_rejection"
    assert annotation.screenshot_path == f"screenshots/{SCREENSHOT}"
    assert annotation.missing_human_fields == (
        "expected_lifecycle",
        "qualification_reason",
        "invalidation_condition",
        "target_1",
        "annotated_by",
    )

    csv_path = workspace / "markeitect-reference-set.csv"
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    rows[0]["qualification_reason"] = "Failed reclaim of resistance and value"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    preserved = sync_reference_csv(workspace, instrument_aliases={"NQ": INSTRUMENT})[0]
    assert preserved.qualification_reason == "Failed reclaim of resistance and value"

    image.write_bytes(b"reference-image-v2")
    with pytest.raises(ValueError, match="changed in place"):
        sync_reference_csv(workspace, instrument_aliases={"NQ": INSTRUMENT})


def test_sync_infers_five_minute_chart_and_preserves_row_across_rename(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "reference-set"
    screenshots = workspace / "screenshots"
    screenshots.mkdir(parents=True)
    original = screenshots / SCREENSHOT
    original.write_bytes(b"same-reference-image")
    sync_reference_csv(workspace, instrument_aliases={"NQ": INSTRUMENT})

    csv_path = workspace / "markeitect-reference-set.csv"
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    rows[0]["qualification_reason"] = "Human evidence survives a filename correction"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    renamed = screenshots / "2026-07-16T22-55Z_NQ_5m_short_resistance-rejection.png"
    original.rename(renamed)
    annotation = sync_reference_csv(workspace, instrument_aliases={"NQ": INSTRUMENT})[0]

    assert annotation.chart_timeframe == AnalyticsTimeframe.FIVE_MINUTES
    assert annotation.observed_ts == NOW + timedelta(minutes=5)
    assert annotation.qualification_reason == "Human evidence survives a filename correction"
    assert annotation.screenshot_path == f"screenshots/{renamed.name}"


def test_sync_rejects_unknown_alias_and_malformed_header(tmp_path: Path) -> None:
    workspace = tmp_path / "reference-set"
    screenshots = workspace / "screenshots"
    screenshots.mkdir(parents=True)
    (screenshots / SCREENSHOT).write_bytes(b"image")

    with pytest.raises(ValueError, match="unknown instrument alias"):
        sync_reference_csv(workspace, instrument_aliases={})

    (workspace / "markeitect-reference-set.csv").write_text("wrong,header\n", encoding="utf-8")
    with pytest.raises(ValueError, match="header"):
        sync_reference_csv(workspace, instrument_aliases={"NQ": INSTRUMENT})


def test_enrichment_measures_price_without_inventing_missing_context() -> None:
    annotation = reference_annotation()
    bars = market_bars()

    record = enrich_reference_annotations(
        (annotation,),
        bars_by_instrument={INSTRUMENT: bars},
        features_by_instrument={INSTRUMENT: ()},
        committed_feature_ids=frozenset(),
        histories=(),
        calendar=FixedCalendar(),
    )[0]

    assert record.signal_join_status == SignalCandidateJoinStatus.UNMATCHED
    assert record.first_divergence == "not_observed_before_durable_lifecycle"
    assert all(item.status == EvidenceJoinStatus.UNAVAILABLE for item in record.context)
    assert record.price_responses[0].response.reference_price == Decimal("100")
    five = next(
        item for item in record.price_responses[0].response.horizons if item.horizon_minutes == 5
    )
    assert five.directional_return_points == Decimal("5")


def test_context_join_excludes_future_and_retains_same_time_variants() -> None:
    annotation = reference_annotation()
    past_a = feature(NOW - timedelta(minutes=1), "a")
    past_b = feature(NOW - timedelta(minutes=1), "b")
    future = feature(NOW + timedelta(minutes=1), "c")
    features = (past_a, past_b, future)

    record = enrich_reference_annotations(
        (annotation,),
        bars_by_instrument={INSTRUMENT: market_bars()},
        features_by_instrument={INSTRUMENT: features},
        committed_feature_ids=frozenset(item.feature_id for item in features),
        histories=(),
        calendar=FixedCalendar(),
    )[0]
    one_minute = next(
        item for item in record.context if item.timeframe == AnalyticsTimeframe.ONE_MINUTE
    )

    assert one_minute.status == EvidenceJoinStatus.AMBIGUOUS
    assert set(one_minute.feature_ids) == {past_a.feature_id, past_b.feature_id}
    assert future.feature_id not in one_minute.feature_ids


def test_exact_zone_join_reports_system_stopped_at_armed() -> None:
    annotation = reference_annotation(
        decision_zone_lower=Decimal("100"),
        decision_zone_upper=Decimal("101"),
    )
    history = armed_history()

    record = enrich_reference_annotations(
        (annotation,),
        bars_by_instrument={INSTRUMENT: market_bars()},
        features_by_instrument={INSTRUMENT: ()},
        committed_feature_ids=frozenset(),
        histories=(history,),
        calendar=FixedCalendar(),
    )[0]

    assert record.signal_join_status == SignalCandidateJoinStatus.MATCHED
    assert record.signal_candidate_ids == (history.current.signal_id,)
    assert record.first_divergence == "system_stopped_at_armed"


def test_reference_artifacts_are_byte_stable(tmp_path: Path) -> None:
    records = enrich_reference_annotations(
        (reference_annotation(),),
        bars_by_instrument={INSTRUMENT: market_bars()},
        features_by_instrument={INSTRUMENT: ()},
        committed_feature_ids=frozenset(),
        histories=(),
        calendar=FixedCalendar(),
    )
    report = render_reference_report(records)

    paths = write_reference_artifacts(records, report=report, output_directory=tmp_path)
    before = tuple(path.read_bytes() for path in paths)
    write_reference_artifacts(records, report=report, output_directory=tmp_path)

    assert before == tuple(path.read_bytes() for path in paths)


def reference_annotation(**updates: object) -> ReferenceAnnotation:
    values: dict[str, object] = {
        "annotation_id": "1" * 64,
        "instrument_alias": "NQ",
        "instrument_id": INSTRUMENT,
        "chart_timeframe": AnalyticsTimeframe.ONE_MINUTE,
        "observed_ts": NOW,
        "candidate_ts": NOW,
        "direction": SignalDirection.SHORT,
        "setup_family": "resistance_poc_val_rejection",
        "expected_lifecycle": ExpectedLifecycle.TRIGGERED,
        "qualification_reason": "Failed resistance reclaim",
        "invalidation_condition": "Accept above resistance",
        "target_1": "Prior low",
        "screenshot_path": f"screenshots/{SCREENSHOT}",
        "screenshot_sha256": "2" * 64,
        "annotated_by": "Markeitect",
    }
    values.update(updates)
    return ReferenceAnnotation(**values)


def market_bars() -> tuple[OneMinuteBar, ...]:
    values = [bar(NOW - timedelta(minutes=1), Decimal("100"), Decimal("100"))]
    for offset in range(35):
        close = Decimal("100") - Decimal(offset + 1)
        values.append(bar(NOW + timedelta(minutes=offset), close + 1, close))
    return tuple(values)


def bar(open_ts: datetime, open_price: Decimal, close: Decimal) -> OneMinuteBar:
    high = max(open_price, close) + 1
    low = min(open_price, close) - 1
    return OneMinuteBar(
        instrument_id=INSTRUMENT,
        event_ts=open_ts + timedelta(minutes=1),
        ts_init=open_ts + timedelta(minutes=1),
        open_ts=open_ts,
        close_ts=open_ts + timedelta(minutes=1),
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=Decimal("10"),
        buy_volume=Decimal("0"),
        sell_volume=Decimal("0"),
        unknown_volume=Decimal("10"),
        source="ib",
    )


def feature(as_of: datetime, variant: str) -> MarketContextFeatureSnapshot:
    return MarketContextFeatureSnapshot(
        configuration_hash=variant * 64,
        input_lineage=(
            FeatureInputLineage(
                instrument_id=INSTRUMENT,
                timeframe=AnalyticsTimeframe.ONE_MINUTE,
                source="ib",
                input_fidelity=AnalyticsInputFidelity.REPORTED,
                start_ts=as_of - timedelta(minutes=1),
                end_ts=as_of,
                event_count=1,
                identity_hash=variant * 64,
            ),
        ),
        snapshot=MarketContextSnapshot(
            instrument_id=INSTRUMENT,
            timeframe=AnalyticsTimeframe.ONE_MINUTE,
            as_of=as_of,
            source="ib",
            input_fidelity=AnalyticsInputFidelity.REPORTED,
            bar_count=251,
            close=Decimal("100"),
            session_open=Decimal("100"),
            session_high=Decimal("101"),
            session_low=Decimal("99"),
            session_range_position=Decimal("0.5"),
            vwap_position=VwapPosition.UNAVAILABLE,
            trend=TrendState.RANGE,
            trend_reason_codes=("test",),
        ),
    )


def armed_history() -> SignalAuditHistory:
    direction_evidence = evidence(SignalEvidenceStage.DIRECTION, "d" * 64)
    candidate = SignalSnapshot(
        definition_id="intraday_context",
        algorithm_version="1.0",
        configuration_hash="c" * 64,
        setup_key=signal_setup_key(
            family=SignalFamily.DIRECTION_LOCATION_AGGRESSION,
            definition_id="intraday_context",
            instrument_id=INSTRUMENT,
            direction=SignalDirection.SHORT,
            anchor="reference-test",
        ),
        instrument_id=INSTRUMENT,
        direction=SignalDirection.SHORT,
        created_ts=NOW,
        updated_ts=NOW,
        direction_regime_anchor="direction:test",
        location_episode_id="e" * 64,
        evidence=(direction_evidence,),
        reason_codes=("test_candidate",),
    )
    match = SignalLocationMatch(
        zone=SignalLocationZone(
            instrument_id=INSTRUMENT,
            direction=SignalDirection.SHORT,
            source_kind=LocationSourceKind.STRUCTURAL_LEVEL,
            zone_kind=SignalLocationZoneKind.RESISTANCE,
            timeframe=AnalyticsTimeframe.FIVE_MINUTES,
            zone_anchor="reference-resistance",
            source_feature_id="b" * 64,
            observed_ts=NOW,
            lower_price=Decimal("100"),
            upper_price=Decimal("101"),
            fidelity=SignalEvidenceFidelity.INFERRED,
            reason_codes=("test_resistance",),
        ),
        evaluation_feature_id="b" * 64,
        observed_ts=NOW,
        observed_price=Decimal("100"),
        distance=Decimal("0"),
        tolerance=Decimal("1"),
        fidelity=SignalEvidenceFidelity.INFERRED,
        reason_codes=("test_match",),
    )
    armed = transition_signal(
        candidate,
        SignalStatus.ARMED,
        occurred_ts=NOW + timedelta(minutes=1),
        reason_codes=("test_armed",),
        evidence=(evidence(SignalEvidenceStage.LOCATION, "b" * 64),),
        location_matches=(match,),
    )
    return SignalAuditHistory(current=armed.current, transitions=(armed,))


def evidence(stage: SignalEvidenceStage, evidence_id: str) -> SignalEvidenceReference:
    return SignalEvidenceReference(
        instrument_id=INSTRUMENT,
        stage=stage,
        evidence_type=SignalEvidenceType.MARKET_CONTEXT_FEATURE,
        evidence_id=evidence_id,
        observed_ts=NOW,
        source="market_context",
        fidelity=SignalEvidenceFidelity.INFERRED,
        reason_codes=("test_evidence",),
    )
