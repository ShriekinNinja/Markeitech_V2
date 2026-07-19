from __future__ import annotations

import csv
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path

from pydantic import Field, field_validator, model_validator

from markeitech.analytics import AnalyticsTimeframe, MarketContextFeatureSnapshot
from markeitech.domain.base import VersionedDomainModel, require_utc
from markeitech.domain.market_data import OneMinuteBar
from markeitech.research.outcomes import (
    AuditSessionCalendar,
    ForwardPriceResponse,
    SignalAuditHistory,
    measure_forward_price_response,
)
from markeitech.signals import SignalDirection, SignalTransitionEvent

REFERENCE_CSV_COLUMNS = (
    "annotation_id",
    "annotation_version",
    "instrument_alias",
    "instrument_id",
    "chart_timeframe",
    "observed_ts_utc",
    "candidate_ts_utc",
    "armed_ts_utc",
    "triggered_ts_utc",
    "direction",
    "setup_family",
    "expected_lifecycle",
    "decision_zone_lower",
    "decision_zone_upper",
    "semantic_level_type",
    "level_timeframe",
    "trigger_timeframe",
    "qualification_reason",
    "price_confirmation",
    "volume_confirmation",
    "profile_confirmation",
    "order_flow_confirmation",
    "invalidation_condition",
    "target_1",
    "target_2",
    "screenshot_path",
    "screenshot_sha256",
    "notes",
    "annotated_by",
    "annotated_at_utc",
)
_LEGACY_REFERENCE_CSV_COLUMNS = tuple(
    column
    for column in REFERENCE_CSV_COLUMNS
    if column not in {"chart_timeframe", "trigger_timeframe"}
)
_INFERRED_CSV_COLUMNS = frozenset(
    {
        "annotation_id",
        "annotation_version",
        "instrument_alias",
        "instrument_id",
        "chart_timeframe",
        "observed_ts_utc",
        "candidate_ts_utc",
        "direction",
        "setup_family",
        "screenshot_path",
        "screenshot_sha256",
    }
)
_SCREENSHOT_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}Z)_"
    r"(?P<instrument>[A-Za-z0-9.-]+)_(?P<timeframe>1m|5m)_"
    r"(?P<direction>long|short)_"
    r"(?P<setup>[a-z0-9][a-z0-9-]*)\.(?P<extension>png|jpg|jpeg)$",
    re.IGNORECASE,
)


class ExpectedLifecycle(StrEnum):
    IGNORE = "ignore"
    WARN = "warn"
    CANDIDATE = "candidate"
    ARMED = "armed"
    TRIGGERED = "triggered"


class AnnotationCompletionStatus(StrEnum):
    DRAFT = "draft"
    COMPLETE = "complete"


class EvidenceJoinStatus(StrEnum):
    MATCHED = "matched"
    STALE = "stale"
    AMBIGUOUS = "ambiguous"
    UNAVAILABLE = "unavailable"


class SignalCandidateJoinStatus(StrEnum):
    MATCHED = "matched"
    UNMATCHED = "unmatched"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"


class ReferenceAnnotation(VersionedDomainModel):
    annotation_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    annotation_version: int = Field(default=1, ge=1)
    instrument_alias: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    chart_timeframe: AnalyticsTimeframe
    observed_ts: datetime
    candidate_ts: datetime | None = None
    armed_ts: datetime | None = None
    triggered_ts: datetime | None = None
    direction: SignalDirection
    setup_family: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    expected_lifecycle: ExpectedLifecycle | None = None
    decision_zone_lower: Decimal | None = Field(default=None, gt=0)
    decision_zone_upper: Decimal | None = Field(default=None, gt=0)
    semantic_level_type: str | None = Field(default=None, min_length=1)
    level_timeframe: str | None = Field(default=None, min_length=1)
    trigger_timeframe: str | None = Field(default=None, min_length=1)
    qualification_reason: str | None = Field(default=None, min_length=1)
    price_confirmation: str | None = Field(default=None, min_length=1)
    volume_confirmation: str | None = Field(default=None, min_length=1)
    profile_confirmation: str | None = Field(default=None, min_length=1)
    order_flow_confirmation: str | None = Field(default=None, min_length=1)
    invalidation_condition: str | None = Field(default=None, min_length=1)
    target_1: str | None = Field(default=None, min_length=1)
    target_2: str | None = Field(default=None, min_length=1)
    screenshot_path: str = Field(min_length=1)
    screenshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    notes: str | None = Field(default=None, min_length=1)
    annotated_by: str | None = Field(default=None, min_length=1)
    annotated_at: datetime | None = None

    @field_validator(
        "observed_ts",
        "candidate_ts",
        "armed_ts",
        "triggered_ts",
        "annotated_at",
    )
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @field_validator("screenshot_path")
    @classmethod
    def _screenshot_path_must_be_safe(cls, value: str) -> str:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise ValueError("annotation screenshot path must be safe and relative")
        if path.parts[0] != "screenshots":
            raise ValueError("annotation screenshot must live under screenshots/")
        return path.as_posix()

    @model_validator(mode="after")
    def _annotation_must_be_consistent(self) -> ReferenceAnnotation:
        if self.chart_timeframe not in {
            AnalyticsTimeframe.ONE_MINUTE,
            AnalyticsTimeframe.FIVE_MINUTES,
        }:
            raise ValueError("reference chart timeframe must be 1m or 5m")
        if (
            self.decision_zone_lower is not None
            and self.decision_zone_upper is not None
            and self.decision_zone_lower > self.decision_zone_upper
        ):
            raise ValueError("annotation zone lower price cannot exceed upper price")
        timeline = tuple(
            value
            for value in (self.candidate_ts, self.armed_ts, self.triggered_ts)
            if value is not None
        )
        if tuple(sorted(timeline)) != timeline:
            raise ValueError("annotation lifecycle timestamps cannot move backward")
        if self.annotated_at is not None and self.annotated_by is None:
            raise ValueError("annotation timestamp requires an author")
        return self

    @property
    def missing_human_fields(self) -> tuple[str, ...]:
        required = {
            "expected_lifecycle": self.expected_lifecycle,
            "qualification_reason": self.qualification_reason,
            "invalidation_condition": self.invalidation_condition,
            "target_1": self.target_1,
            "annotated_by": self.annotated_by,
        }
        return tuple(name for name, value in required.items() if value is None)

    @property
    def completion_status(self) -> AnnotationCompletionStatus:
        return (
            AnnotationCompletionStatus.COMPLETE
            if not self.missing_human_fields
            else AnnotationCompletionStatus.DRAFT
        )


class ContextEvidenceJoin(VersionedDomainModel):
    timeframe: AnalyticsTimeframe
    status: EvidenceJoinStatus
    feature_ids: tuple[str, ...] = ()
    as_of: datetime | None = None
    staleness_seconds: Decimal | None = Field(default=None, ge=0)
    features: tuple[MarketContextFeatureSnapshot, ...] = ()
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator("as_of")
    @classmethod
    def _timestamp_must_be_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @model_validator(mode="after")
    def _status_must_match_features(self) -> ContextEvidenceJoin:
        if self.status == EvidenceJoinStatus.UNAVAILABLE and self.features:
            raise ValueError("unavailable context join cannot carry features")
        if self.status != EvidenceJoinStatus.UNAVAILABLE and not self.features:
            raise ValueError("available context join requires features")
        if self.feature_ids != tuple(item.feature_id for item in self.features):
            raise ValueError("context join feature identities must match payloads")
        return self


class NearbySignalTransition(VersionedDomainModel):
    signal_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    transition_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    occurred_ts: datetime
    direction: SignalDirection
    from_status: str = Field(min_length=1)
    to_status: str = Field(min_length=1)
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator("occurred_ts")
    @classmethod
    def _timestamp_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)


class AnnotatedPriceResponse(VersionedDomainModel):
    anchor: str = Field(pattern=r"^(observed|candidate|armed|triggered)$")
    response: ForwardPriceResponse


class ReferenceEnrichmentRecord(VersionedDomainModel):
    annotation: ReferenceAnnotation
    completion_status: AnnotationCompletionStatus
    missing_human_fields: tuple[str, ...]
    context: tuple[ContextEvidenceJoin, ...]
    signal_join_status: SignalCandidateJoinStatus
    signal_candidate_ids: tuple[str, ...]
    nearby_signal_transitions: tuple[NearbySignalTransition, ...]
    price_responses: tuple[AnnotatedPriceResponse, ...]
    first_divergence: str = Field(min_length=1)
    reason_codes: tuple[str, ...] = Field(min_length=1)


def sync_reference_csv(
    workspace: Path,
    *,
    instrument_aliases: Mapping[str, str],
) -> tuple[ReferenceAnnotation, ...]:
    workspace = workspace.resolve()
    screenshots = workspace / "screenshots"
    csv_path = workspace / "markeitect-reference-set.csv"
    screenshots.mkdir(parents=True, exist_ok=True)
    existing = _read_raw_rows(csv_path)
    by_path: dict[str, dict[str, str]] = {}
    by_hash: dict[str, list[dict[str, str]]] = {}
    for row in existing:
        screenshot_path = row.get("screenshot_path", "").strip()
        if not screenshot_path:
            raise ValueError("reference CSV row requires a screenshot path")
        if screenshot_path in by_path:
            raise ValueError(f"duplicate reference screenshot row {screenshot_path!r}")
        by_path[screenshot_path] = row
        screenshot_hash = row.get("screenshot_sha256", "").strip()
        if screenshot_hash:
            by_hash.setdefault(screenshot_hash, []).append(row)
    discovered: list[dict[str, str]] = []
    discovered_paths: set[str] = set()
    migrated_paths: set[str] = set()
    for path in sorted(
        value
        for value in screenshots.iterdir()
        if value.is_file() and value.suffix.lower() in {".png", ".jpg", ".jpeg"}
    ):
        relative = path.relative_to(workspace).as_posix()
        discovered_paths.add(relative)
        inferred = _infer_screenshot(path, relative, instrument_aliases)
        current = by_path.get(relative, {})
        if not current:
            hash_matches = by_hash.get(inferred["screenshot_sha256"], [])
            if len(hash_matches) > 1:
                raise ValueError(
                    f"reference screenshot rename is ambiguous for content hash: {relative}"
                )
            if hash_matches:
                current = hash_matches[0]
                migrated_paths.add(current["screenshot_path"])
        if current and current.get("screenshot_sha256") not in {
            "",
            inferred["screenshot_sha256"],
        }:
            raise ValueError(
                f"reference screenshot changed in place; create a new version: {relative}"
            )
        discovered.append(
            {
                column: (
                    inferred.get(column, "")
                    if column in _INFERRED_CSV_COLUMNS
                    else current.get(column, "").strip()
                )
                for column in REFERENCE_CSV_COLUMNS
            }
        )
    missing = sorted(set(by_path) - discovered_paths - migrated_paths)
    if missing:
        raise ValueError("reference CSV declares missing screenshots: " + ", ".join(missing))
    _write_raw_rows(csv_path, discovered)
    return tuple(_annotation_from_row(row) for row in discovered)


def enrich_reference_annotations(
    annotations: Sequence[ReferenceAnnotation],
    *,
    bars_by_instrument: Mapping[str, Sequence[OneMinuteBar]],
    features_by_instrument: Mapping[str, Sequence[MarketContextFeatureSnapshot]],
    committed_feature_ids: frozenset[str],
    histories: Sequence[SignalAuditHistory],
    calendar: AuditSessionCalendar,
    transition_window_before: timedelta = timedelta(minutes=15),
    transition_window_after: timedelta = timedelta(minutes=45),
) -> tuple[ReferenceEnrichmentRecord, ...]:
    records: list[ReferenceEnrichmentRecord] = []
    for annotation in annotations:
        context = _join_context(
            annotation,
            features_by_instrument.get(annotation.instrument_id, ()),
            committed_feature_ids,
        )
        signal_status, signal_ids, transitions = _join_signal_candidates(
            annotation,
            histories,
            transition_window_before,
            transition_window_after,
        )
        responses = _price_responses(
            annotation,
            bars_by_instrument.get(annotation.instrument_id, ()),
            calendar,
        )
        reasons = list(annotation.missing_human_fields)
        reasons.extend(
            f"context_{item.timeframe.value}_{item.status.value}"
            for item in context
            if item.status != EvidenceJoinStatus.MATCHED
        )
        if signal_status == SignalCandidateJoinStatus.UNMATCHED:
            reasons.append("no_durable_signal_transition_near_annotation")
        elif signal_status != SignalCandidateJoinStatus.MATCHED:
            reasons.append(f"signal_candidate_join_{signal_status.value}")
        if any(
            outcome.status.value == "unavailable"
            for response in responses
            for outcome in response.response.horizons
        ):
            reasons.append("one_or_more_price_horizons_unavailable")
        records.append(
            ReferenceEnrichmentRecord(
                annotation=annotation,
                completion_status=annotation.completion_status,
                missing_human_fields=annotation.missing_human_fields,
                context=context,
                signal_join_status=signal_status,
                signal_candidate_ids=signal_ids,
                nearby_signal_transitions=transitions,
                price_responses=responses,
                first_divergence=_first_divergence(
                    annotation,
                    signal_status,
                    transitions,
                ),
                reason_codes=tuple(dict.fromkeys(reasons)) or ("fully_enriched",),
            )
        )
    return tuple(sorted(records, key=lambda item: item.annotation.observed_ts))


def render_reference_report(records: Sequence[ReferenceEnrichmentRecord]) -> str:
    complete = sum(
        item.completion_status == AnnotationCompletionStatus.COMPLETE for item in records
    )
    lines = [
        "# Markeitect Reference Set",
        "",
        f"Annotations: {len(records)} | Complete: {complete} | Draft: {len(records) - complete}",
        "",
        "| Time | Instrument | Chart | Direction | Setup | Human Status | Context "
        "| Signal Join | First Divergence |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in records:
        context_summary = ", ".join(
            f"{join.timeframe.value}:{join.status.value}" for join in item.context
        )
        lines.append(
            f"| {item.annotation.observed_ts.isoformat()} | {item.annotation.instrument_id} "
            f"| {item.annotation.chart_timeframe.value} "
            f"| {item.annotation.direction.value.title()} | {item.annotation.setup_family} "
            f"| {item.completion_status.value.title()} | {context_summary} "
            f"| {item.signal_join_status.value.title()} "
            f"| {item.first_divergence} |"
        )
    lines.extend(
        [
            "",
            "## Draft Work",
            "",
            *(
                [
                    f"- `{item.annotation.screenshot_path}`: "
                    + ", ".join(item.missing_human_fields)
                    for item in records
                    if item.missing_human_fields
                ]
                or ["- None"]
            ),
            "",
            "Persisted context is joined only at or before the annotation timestamp. "
            "Stale, ambiguous, and unavailable evidence remains explicit.",
            "",
        ]
    )
    return "\n".join(lines)


def write_reference_artifacts(
    records: Sequence[ReferenceEnrichmentRecord],
    *,
    report: str,
    output_directory: Path,
) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    dataset_path = output_directory / "enriched-reference-set.jsonl"
    report_path = output_directory / "reference-set-report.md"
    dataset_path.write_text(
        "".join(
            json.dumps(item.model_dump(mode="json"), separators=(",", ":"), sort_keys=True) + "\n"
            for item in records
        ),
        encoding="utf-8",
    )
    report_path.write_text(report, encoding="utf-8")
    return dataset_path, report_path


def _infer_screenshot(
    path: Path,
    relative: str,
    aliases: Mapping[str, str],
) -> dict[str, str]:
    match = _SCREENSHOT_PATTERN.fullmatch(path.name)
    if match is None:
        raise ValueError(
            "reference screenshot must use "
            "YYYY-MM-DDTHH-MMZ_INSTRUMENT_1m|5m_long|short_setup-name.ext: "
            f"{path.name}"
        )
    alias = match.group("instrument").upper()
    instrument_id = aliases.get(alias)
    if instrument_id is None:
        raise ValueError(f"reference screenshot uses unknown instrument alias {alias!r}")
    observed = datetime.strptime(match.group("timestamp"), "%Y-%m-%dT%H-%MZ").replace(tzinfo=UTC)
    identity = ":".join(
        (
            instrument_id,
            observed.isoformat(),
            match.group("timeframe").lower(),
            match.group("direction").lower(),
            match.group("setup").lower(),
        )
    )
    return {
        "annotation_id": hashlib.sha256(f"markeitech-reference:{identity}".encode()).hexdigest(),
        "annotation_version": "1",
        "instrument_alias": alias,
        "instrument_id": instrument_id,
        "chart_timeframe": match.group("timeframe").lower(),
        "observed_ts_utc": observed.isoformat(),
        "candidate_ts_utc": observed.isoformat(),
        "direction": match.group("direction").lower(),
        "setup_family": match.group("setup").lower().replace("-", "_"),
        "screenshot_path": relative,
        "screenshot_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _annotation_from_row(row: Mapping[str, str]) -> ReferenceAnnotation:
    return ReferenceAnnotation(
        annotation_id=row["annotation_id"],
        annotation_version=int(row["annotation_version"]),
        instrument_alias=row["instrument_alias"],
        instrument_id=row["instrument_id"],
        chart_timeframe=AnalyticsTimeframe(row["chart_timeframe"]),
        observed_ts=_optional_datetime(row["observed_ts_utc"]),
        candidate_ts=_optional_datetime(row["candidate_ts_utc"]),
        armed_ts=_optional_datetime(row["armed_ts_utc"]),
        triggered_ts=_optional_datetime(row["triggered_ts_utc"]),
        direction=SignalDirection(row["direction"]),
        setup_family=row["setup_family"],
        expected_lifecycle=_optional_enum(ExpectedLifecycle, row["expected_lifecycle"]),
        decision_zone_lower=_optional_decimal(row["decision_zone_lower"]),
        decision_zone_upper=_optional_decimal(row["decision_zone_upper"]),
        semantic_level_type=_optional_text(row["semantic_level_type"]),
        level_timeframe=_optional_text(row["level_timeframe"]),
        trigger_timeframe=_optional_text(row["trigger_timeframe"]),
        qualification_reason=_optional_text(row["qualification_reason"]),
        price_confirmation=_optional_text(row["price_confirmation"]),
        volume_confirmation=_optional_text(row["volume_confirmation"]),
        profile_confirmation=_optional_text(row["profile_confirmation"]),
        order_flow_confirmation=_optional_text(row["order_flow_confirmation"]),
        invalidation_condition=_optional_text(row["invalidation_condition"]),
        target_1=_optional_text(row["target_1"]),
        target_2=_optional_text(row["target_2"]),
        screenshot_path=row["screenshot_path"],
        screenshot_sha256=row["screenshot_sha256"],
        notes=_optional_text(row["notes"]),
        annotated_by=_optional_text(row["annotated_by"]),
        annotated_at=_optional_datetime(row["annotated_at_utc"]),
    )


def _join_context(
    annotation: ReferenceAnnotation,
    features: Sequence[MarketContextFeatureSnapshot],
    committed_ids: frozenset[str],
) -> tuple[ContextEvidenceJoin, ...]:
    joins: list[ContextEvidenceJoin] = []
    for timeframe in AnalyticsTimeframe:
        eligible = tuple(
            item
            for item in features
            if item.feature_id in committed_ids
            and item.snapshot.timeframe == timeframe
            and item.snapshot.as_of <= annotation.observed_ts
        )
        if not eligible:
            joins.append(
                ContextEvidenceJoin(
                    timeframe=timeframe,
                    status=EvidenceJoinStatus.UNAVAILABLE,
                    reason_codes=("no_committed_feature_at_or_before_annotation",),
                )
            )
            continue
        latest_as_of = max(item.snapshot.as_of for item in eligible)
        latest = tuple(
            sorted(
                (item for item in eligible if item.snapshot.as_of == latest_as_of),
                key=lambda item: item.feature_id,
            )
        )
        age = annotation.observed_ts - latest_as_of
        stale = age > _feature_freshness(timeframe)
        ambiguous = len(latest) > 1
        status = (
            EvidenceJoinStatus.AMBIGUOUS
            if ambiguous
            else EvidenceJoinStatus.STALE
            if stale
            else EvidenceJoinStatus.MATCHED
        )
        reasons = []
        if ambiguous:
            reasons.append("multiple_committed_variants_at_latest_as_of")
        if stale:
            reasons.append("latest_committed_feature_is_stale")
        if not reasons:
            reasons.append("exact_latest_committed_feature_join")
        joins.append(
            ContextEvidenceJoin(
                timeframe=timeframe,
                status=status,
                feature_ids=tuple(item.feature_id for item in latest),
                as_of=latest_as_of,
                staleness_seconds=_timedelta_seconds(age),
                features=latest,
                reason_codes=tuple(reasons),
            )
        )
    return tuple(joins)


def _join_signal_candidates(
    annotation: ReferenceAnnotation,
    histories: Sequence[SignalAuditHistory],
    before: timedelta,
    after: timedelta,
) -> tuple[
    SignalCandidateJoinStatus,
    tuple[str, ...],
    tuple[NearbySignalTransition, ...],
]:
    start = annotation.observed_ts - before
    end = annotation.observed_ts + after
    candidates: dict[str, tuple[SignalTransitionEvent, ...]] = {}
    for history in histories:
        events = tuple(
            event
            for event in history.transitions
            if event.current.instrument_id == annotation.instrument_id
            and event.current.direction == annotation.direction
            and start <= event.occurred_ts <= end
        )
        if not events:
            continue
        if (
            annotation.decision_zone_lower is not None
            and annotation.decision_zone_upper is not None
        ):
            if not any(
                _event_overlaps_zone(
                    event,
                    annotation.decision_zone_lower,
                    annotation.decision_zone_upper,
                )
                for event in events
            ):
                continue
        candidates[history.current.signal_id] = events
    candidate_ids = tuple(sorted(candidates))
    if not candidates:
        status = SignalCandidateJoinStatus.UNMATCHED
    elif annotation.decision_zone_lower is None or annotation.decision_zone_upper is None:
        status = SignalCandidateJoinStatus.UNRESOLVED
    elif len(candidates) == 1:
        status = SignalCandidateJoinStatus.MATCHED
    else:
        status = SignalCandidateJoinStatus.AMBIGUOUS
    events = (event for signal_id in candidate_ids for event in candidates[signal_id])
    transitions = tuple(
        NearbySignalTransition(
            signal_id=event.signal_id,
            transition_id=event.transition_id,
            occurred_ts=event.occurred_ts,
            direction=event.current.direction,
            from_status=event.from_status.value,
            to_status=event.to_status.value,
            reason_codes=event.reason_codes,
        )
        for event in sorted(events, key=lambda item: (item.occurred_ts, item.transition_id))
    )
    return status, candidate_ids, transitions


def _event_overlaps_zone(
    event: SignalTransitionEvent,
    lower: Decimal,
    upper: Decimal,
) -> bool:
    return any(
        match.zone.lower_price <= upper and lower <= match.zone.upper_price
        for match in event.current.location_matches
    )


def _price_responses(
    annotation: ReferenceAnnotation,
    bars: Sequence[OneMinuteBar],
    calendar: AuditSessionCalendar,
) -> tuple[AnnotatedPriceResponse, ...]:
    anchors = (
        ("observed", annotation.observed_ts),
        ("candidate", annotation.candidate_ts),
        ("armed", annotation.armed_ts),
        ("triggered", annotation.triggered_ts),
    )
    seen: set[datetime] = set()
    responses: list[AnnotatedPriceResponse] = []
    for name, timestamp in anchors:
        if timestamp is None or timestamp in seen:
            continue
        seen.add(timestamp)
        responses.append(
            AnnotatedPriceResponse(
                anchor=name,
                response=measure_forward_price_response(
                    annotation.instrument_id,
                    annotation.direction,
                    timestamp,
                    bars,
                    calendar=calendar,
                ),
            )
        )
    return tuple(responses)


def _first_divergence(
    annotation: ReferenceAnnotation,
    join_status: SignalCandidateJoinStatus,
    transitions: Sequence[NearbySignalTransition],
) -> str:
    if annotation.expected_lifecycle is None:
        return "human_expected_lifecycle_pending"
    if join_status == SignalCandidateJoinStatus.UNMATCHED:
        return "not_observed_before_durable_lifecycle"
    if join_status != SignalCandidateJoinStatus.MATCHED:
        return f"signal_candidate_join_{join_status.value}"
    reached = {item.to_status for item in transitions}
    if "triggered" in reached:
        observed = ExpectedLifecycle.TRIGGERED
    elif "armed" in reached:
        observed = ExpectedLifecycle.ARMED
    else:
        observed = None
    if observed is None:
        return "not_observed_before_durable_lifecycle"
    order = {
        ExpectedLifecycle.IGNORE: 0,
        ExpectedLifecycle.WARN: 1,
        ExpectedLifecycle.CANDIDATE: 2,
        ExpectedLifecycle.ARMED: 3,
        ExpectedLifecycle.TRIGGERED: 4,
    }
    if order[observed] < order[annotation.expected_lifecycle]:
        return f"system_stopped_at_{observed.value}"
    if order[observed] > order[annotation.expected_lifecycle]:
        return f"system_advanced_to_{observed.value}"
    return "human_and_system_lifecycle_match"


def _feature_freshness(timeframe: AnalyticsTimeframe) -> timedelta:
    return max(timeframe.duration * 2, timedelta(minutes=2))


def _read_raw_rows(path: Path) -> tuple[dict[str, str], ...]:
    if not path.exists():
        return ()
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            return ()
        fieldnames = tuple(reader.fieldnames)
        if fieldnames not in {REFERENCE_CSV_COLUMNS, _LEGACY_REFERENCE_CSV_COLUMNS}:
            raise ValueError("reference CSV header does not match the current contract")
        return tuple(
            {column: row.get(column, "") or "" for column in REFERENCE_CSV_COLUMNS}
            for row in reader
            if any((value or "").strip() for value in row.values())
        )


def _write_raw_rows(path: Path, rows: Sequence[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=REFERENCE_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _optional_text(value: str) -> str | None:
    stripped = value.strip()
    return stripped or None


def _optional_datetime(value: str) -> datetime | None:
    stripped = value.strip()
    if not stripped:
        return None
    parsed = datetime.fromisoformat(stripped.replace("Z", "+00:00"))
    return require_utc(parsed)


def _optional_decimal(value: str) -> Decimal | None:
    stripped = value.strip()
    return None if not stripped else Decimal(stripped)


def _optional_enum(enum_type: type[ExpectedLifecycle], value: str) -> ExpectedLifecycle | None:
    stripped = value.strip()
    return None if not stripped else enum_type(stripped)


def _timedelta_seconds(value: timedelta) -> Decimal:
    whole_seconds = value.days * 86_400 + value.seconds
    return Decimal(whole_seconds) + Decimal(value.microseconds) / Decimal("1000000")
