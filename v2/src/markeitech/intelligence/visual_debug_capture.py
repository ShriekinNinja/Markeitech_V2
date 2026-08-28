from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any

from markeitech.acquisition.historical_messages import HistoricalReadinessEvent
from markeitech.intelligence.completed_bars import CompletedBarInput, CompletedBarSource
from markeitech.intelligence.metrics import MetricValue
from markeitech.intelligence.session_measurements import COMPLETED_BAR_METRIC_IDS

VISUAL_DEBUG_SNAPSHOT_REQUEST_TYPE_NAME = "markeitech.visual_debug.snapshot.request"
VISUAL_DEBUG_SNAPSHOT_RESPONSE_TYPE_NAME = "markeitech.visual_debug.snapshot.response"
CAPTURE_COMPLETENESS = "SUBJECT_COMPLETE_BOUNDED_RECEIVE_CUT_NOT_TRANSACTIONALLY_FINAL"
ARTIFACT_KIND = "source-faithful-frozen-completed-bar-review"


def _required_text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty")
    return value.strip()


def _positive(value: int, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


@dataclass(frozen=True, slots=True)
class CompletedBarFoundationSnapshotRequest:
    request_id: str
    requester: str
    requested_ts_ns: int
    instrument_id: str
    bar_specification: str
    parameter_version: int
    maximum_intervals: int

    def __post_init__(self) -> None:
        for name in ("request_id", "requester", "instrument_id", "bar_specification"):
            object.__setattr__(self, name, _required_text(getattr(self, name), name))
        _positive(self.requested_ts_ns, "requested_ts_ns")
        _positive(self.parameter_version, "parameter_version")
        _positive(self.maximum_intervals, "maximum_intervals")

    @property
    def ts_event(self) -> int:
        return self.requested_ts_ns

    @property
    def ts_init(self) -> int:
        return self.requested_ts_ns


@dataclass(frozen=True, slots=True)
class CompletedBarFoundationSnapshot:
    generated_ts_ns: int
    producer_id: str
    bars: tuple[CompletedBarInput, ...]
    metrics: tuple[MetricValue, ...]
    historical_readiness: HistoricalReadinessEvent | None = None

    def __post_init__(self) -> None:
        _positive(self.generated_ts_ns, "generated_ts_ns")
        object.__setattr__(self, "producer_id", _required_text(self.producer_id, "producer_id"))
        if any(not isinstance(item, CompletedBarInput) for item in self.bars):
            raise ValueError("bars must contain CompletedBarInput values")
        if any(not isinstance(item, MetricValue) for item in self.metrics):
            raise ValueError("metrics must contain MetricValue values")
        if self.historical_readiness is not None and not isinstance(
            self.historical_readiness,
            HistoricalReadinessEvent,
        ):
            raise ValueError("historical_readiness must be a HistoricalReadinessEvent")

    @property
    def ts_event(self) -> int:
        return self.generated_ts_ns

    @property
    def ts_init(self) -> int:
        return self.generated_ts_ns


@dataclass(frozen=True, slots=True)
class CompletedBarFoundationSnapshotResponse:
    request_id: str
    requester: str
    snapshot: CompletedBarFoundationSnapshot

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _required_text(self.request_id, "request_id"))
        object.__setattr__(self, "requester", _required_text(self.requester, "requester"))
        if not isinstance(self.snapshot, CompletedBarFoundationSnapshot):
            raise ValueError("snapshot must be a CompletedBarFoundationSnapshot")

    @property
    def ts_event(self) -> int:
        return self.snapshot.ts_event

    @property
    def ts_init(self) -> int:
        return self.snapshot.ts_init


def build_completed_bar_foundation_snapshot(
    request: CompletedBarFoundationSnapshotRequest,
    *,
    generated_ts_ns: int,
    producer_id: str,
    bars: tuple[CompletedBarInput, ...],
    metric_cohorts: dict[tuple[str, int], tuple[MetricValue, ...]],
    historical_readiness: HistoricalReadinessEvent | None = None,
) -> CompletedBarFoundationSnapshot:
    selected_bars = tuple(
        bar
        for bar in bars
        if bar.instrument_id == request.instrument_id
        and bar.bar_specification == request.bar_specification
    )[-request.maximum_intervals :]
    selected_metrics = tuple(
        metric
        for bar in selected_bars
        for metric in metric_cohorts.get((bar.instrument_id, bar.interval_end_ns), ())
        if metric.parameter_version == request.parameter_version
    )
    return CompletedBarFoundationSnapshot(
        generated_ts_ns=generated_ts_ns,
        producer_id=producer_id,
        bars=selected_bars,
        metrics=selected_metrics,
        historical_readiness=historical_readiness,
    )


@dataclass(frozen=True, slots=True)
class CaptureCounters:
    bar_publications: int
    metric_publications: int
    exact_duplicates: int
    stale_revisions: int
    higher_revisions: int
    excluded_after_cut: int


@dataclass(frozen=True, slots=True)
class FrozenVisualDebugCapture:
    schema_version: int
    artifact_kind: str
    capture_completeness: str
    capture_id: str
    run_id: str
    configuration_identity: str
    capture_policy_version: int
    historical_bar_count: int
    live_bar_count: int
    frozen_at_ns: int
    cutoff_interval_end_ns: int
    historical_readiness: HistoricalReadinessEvent
    bars: tuple[CompletedBarInput, ...]
    metrics: tuple[MetricValue, ...]
    counters: CaptureCounters
    upstream_bar_conflict_evidence: str
    constituent_records_captured: bool
    payload_sha256: str


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, Enum)):
        return value.isoformat() if isinstance(value, date) else value.value
    if is_dataclass(value):
        return {field.name: _canonical(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda x: str(x[0]))
        }
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


class VisualDebugCaptureCollector:
    """Bounded, single-series receive-cut collector. It never calculates market values."""

    def __init__(
        self,
        *,
        instrument_id: str,
        bar_specification: str,
        parameter_version: int,
        historical_bar_count: int = 5,
        live_bar_count: int = 5,
        interval_seconds: int = 60,
    ) -> None:
        self.instrument_id = _required_text(instrument_id, "instrument_id")
        self.bar_specification = _required_text(bar_specification, "bar_specification")
        self.parameter_version = _positive(parameter_version, "parameter_version")
        self.historical_bar_count = _positive(historical_bar_count, "historical_bar_count")
        self.live_bar_count = _positive(live_bar_count, "live_bar_count")
        self.interval_ns = _positive(interval_seconds, "interval_seconds") * 1_000_000_000
        self.maximum_intervals = self.historical_bar_count + self.live_bar_count
        self._bars: dict[int, CompletedBarInput] = {}
        self._metrics: dict[tuple[str, int], dict[int, MetricValue]] = {}
        self._frozen = False
        self._conflict: str | None = None
        self._bar_publications = 0
        self._metric_publications = 0
        self._duplicates = 0
        self._stale = 0
        self._higher = 0
        self._excluded = 0

    @property
    def conflict(self) -> str | None:
        return self._conflict

    def accept_snapshot(self, snapshot: CompletedBarFoundationSnapshot) -> None:
        for bar in snapshot.bars:
            self.accept_bar(bar)
        for metric in snapshot.metrics:
            self.accept_metric(metric)

    def accept_bar(self, bar: CompletedBarInput) -> bool:
        if self._frozen:
            self._excluded += 1
            return False
        if (
            bar.instrument_id != self.instrument_id
            or bar.bar_specification != self.bar_specification
            or not bar.complete
        ):
            return False
        self._bar_publications += 1
        existing = self._bars.get(bar.interval_end_ns)
        if existing is not None:
            if existing == bar:
                self._duplicates += 1
                return False
            self._conflict = "PROJECTION_BAR_CONFLICT"
            return False
        if bar.revision != 1:
            self._conflict = "PRODUCER_BAR_REVISION_VIOLATION"
            return False
        self._bars[bar.interval_end_ns] = bar
        return True

    def accept_metric(self, metric: MetricValue) -> bool:
        if self._frozen:
            self._excluded += 1
            return False
        if (
            metric.instrument_id != self.instrument_id
            or metric.metric_id not in COMPLETED_BAR_METRIC_IDS
            or metric.metric_version != 1
            or metric.parameter_version != self.parameter_version
        ):
            return False
        self._metric_publications += 1
        subject = (metric.metric_id, metric.effective_ts_ns)
        revisions = self._metrics.setdefault(subject, {})
        existing = revisions.get(metric.revision)
        if existing is not None:
            if existing == metric:
                self._duplicates += 1
                return False
            self._conflict = "PROJECTION_METRIC_CONFLICT"
            return False
        if revisions:
            maximum = max(revisions)
            if metric.revision < maximum:
                self._stale += 1
                return False
            elif metric.revision > maximum:
                self._higher += 1
                self._metrics[subject] = {metric.revision: metric}
                return True
        revisions[metric.revision] = metric
        return True

    def selected_records(
        self,
    ) -> tuple[tuple[CompletedBarInput, ...], tuple[MetricValue, ...]] | None:
        if self._conflict is not None:
            return None
        ordered = tuple(self._bars[key] for key in sorted(self._bars))
        for start in range(max(0, len(ordered) - self.maximum_intervals + 1)):
            candidate = ordered[start : start + self.maximum_intervals]
            if len(candidate) != self.maximum_intervals or not self._valid_bar_window(candidate):
                continue
            selected: list[MetricValue] = []
            for bar in candidate:
                cohorts: dict[int, list[MetricValue]] = {}
                highest_seen = 0
                for metric_id in COMPLETED_BAR_METRIC_IDS:
                    revisions = self._metrics.get((metric_id, bar.interval_end_ns), {})
                    if revisions:
                        highest_seen = max(highest_seen, max(revisions))
                    for revision, value in revisions.items():
                        cohorts.setdefault(revision, []).append(value)
                cohort = cohorts.get(highest_seen, [])
                if len(cohort) != len(COMPLETED_BAR_METRIC_IDS):
                    return None
                if not self._valid_metric_cohort(bar, tuple(cohort)):
                    self._conflict = "METRIC_COHORT_INVALID"
                    return None
                selected.extend(sorted(cohort, key=lambda item: item.metric_id))
            return candidate, tuple(selected)
        return None

    def freeze(
        self,
        *,
        run_id: str,
        configuration_identity: str,
        capture_policy_version: int,
        frozen_at_ns: int,
        historical_readiness: HistoricalReadinessEvent,
    ) -> FrozenVisualDebugCapture:
        if self._frozen:
            raise ValueError("capture has already frozen")
        selected = self.selected_records()
        if selected is None:
            raise ValueError(self._conflict or "capture is not subject-complete")
        bars, metrics = selected
        if (
            not isinstance(historical_readiness, HistoricalReadinessEvent)
            or historical_readiness.state != "READY"
            or historical_readiness.observed_count != self.historical_bar_count
        ):
            raise ValueError("historical readiness does not match capture policy")
        expected_ref = f"historical:{historical_readiness.request_id}"
        if any(expected_ref not in bar.evidence_refs for bar in bars[: self.historical_bar_count]):
            raise ValueError("historical bars do not cite the readiness request")
        core = {
            "run_id": _required_text(run_id, "run_id"),
            "configuration_identity": _required_text(
                configuration_identity, "configuration_identity"
            ),
            "capture_policy_version": _positive(capture_policy_version, "capture_policy_version"),
            "historical_bar_count": self.historical_bar_count,
            "live_bar_count": self.live_bar_count,
            "frozen_at_ns": _positive(frozen_at_ns, "frozen_at_ns"),
            "bars": bars,
            "metrics": metrics,
            "historical_readiness": historical_readiness,
        }
        payload_digest = canonical_sha256(core)
        capture_id = hashlib.sha256(
            f"{core['run_id']}:{core['configuration_identity']}:{payload_digest}".encode(),
        ).hexdigest()
        self._frozen = True
        return FrozenVisualDebugCapture(
            schema_version=1,
            artifact_kind=ARTIFACT_KIND,
            capture_completeness=CAPTURE_COMPLETENESS,
            capture_id=capture_id,
            run_id=core["run_id"],
            configuration_identity=core["configuration_identity"],
            capture_policy_version=core["capture_policy_version"],
            historical_bar_count=core["historical_bar_count"],
            live_bar_count=core["live_bar_count"],
            frozen_at_ns=core["frozen_at_ns"],
            cutoff_interval_end_ns=bars[-1].interval_end_ns,
            historical_readiness=historical_readiness,
            bars=bars,
            metrics=metrics,
            counters=CaptureCounters(
                self._bar_publications,
                self._metric_publications,
                self._duplicates,
                self._stale,
                self._higher,
                self._excluded,
            ),
            upstream_bar_conflict_evidence="NOT_SUPPLIED",
            constituent_records_captured=False,
            payload_sha256=payload_digest,
        )

    def _valid_bar_window(self, bars: tuple[CompletedBarInput, ...]) -> bool:
        expected_sources = (CompletedBarSource.HISTORICAL_PROVIDER,) * self.historical_bar_count + (
            CompletedBarSource.LIVE_AGGREGATE,
        ) * self.live_bar_count
        first = bars[0]
        identity = (
            first.calendar_id,
            first.analytical_profile_id,
            first.analytical_profile_version,
            first.trade_date,
            first.session_id,
            first.window_id,
        )
        for index, bar in enumerate(bars):
            if bar.source is not expected_sources[index] or bar.interval_ns != self.interval_ns:
                return False
            if bar.interval_start_ns % self.interval_ns != 0:
                return False
            if index and bars[index - 1].interval_end_ns != bar.interval_start_ns:
                return False
            if (
                bar.calendar_id,
                bar.analytical_profile_id,
                bar.analytical_profile_version,
                bar.trade_date,
                bar.session_id,
                bar.window_id,
            ) != identity:
                return False
        return True

    @staticmethod
    def _valid_metric_cohort(bar: CompletedBarInput, values: tuple[MetricValue, ...]) -> bool:
        ids = {value.metric_id for value in values}
        if ids != set(COMPLETED_BAR_METRIC_IDS):
            return False
        shared = {
            (
                value.instrument_id,
                value.session_id,
                value.effective_ts_ns,
                value.metric_version,
                value.parameter_version,
                value.revision,
                value.calculated_ts_ns,
                value.published_ts_ns,
                value.source,
            )
            for value in values
        }
        if len(shared) != 1:
            return False
        value = values[0]
        if (
            value.instrument_id != bar.instrument_id
            or value.session_id != bar.session_id
            or value.effective_ts_ns != bar.interval_end_ns
            or value.observed_ts_ns != bar.observed_ts_ns
            or value.received_ts_ns != bar.received_ts_ns
        ):
            return False
        exact = {
            "completed_bar.open": bar.open,
            "completed_bar.high": bar.high,
            "completed_bar.low": bar.low,
            "completed_bar.close": bar.close,
            "completed_bar.volume": bar.volume,
        }
        by_id = {item.metric_id: item for item in values}
        units = {
            "completed_bar.open": "price",
            "completed_bar.high": "price",
            "completed_bar.low": "price",
            "completed_bar.close": "price",
            "completed_bar.volume": "volume",
            "completed_bar.simple_return": "ratio",
            "completed_bar.true_range": "price",
        }
        if any(
            item.observed_ts_ns != bar.observed_ts_ns
            or item.received_ts_ns != bar.received_ts_ns
            or item.evidence_refs != bar.evidence_refs
            or item.unit != units[item.metric_id]
            for item in values
        ):
            return False
        if any(
            by_id[metric_id].health is not bar.health
            or by_id[metric_id].fidelity is not bar.fidelity
            for metric_id in (
                "completed_bar.open",
                "completed_bar.high",
                "completed_bar.low",
                "completed_bar.close",
            )
        ):
            return False
        return all(by_id[metric_id].value == expected for metric_id, expected in exact.items())


def frozen_capture_manifest(
    capture: FrozenVisualDebugCapture, *, html_sha256: str, plotly_version: str
) -> dict[str, Any]:
    return {
        "schema_version": capture.schema_version,
        "artifact_kind": capture.artifact_kind,
        "capture_completeness": capture.capture_completeness,
        "capture_id": capture.capture_id,
        "run_id": capture.run_id,
        "configuration_identity": capture.configuration_identity,
        "capture_policy_version": capture.capture_policy_version,
        "frozen_at_ns": capture.frozen_at_ns,
        "cutoff_interval_end_ns": capture.cutoff_interval_end_ns,
        "historical_readiness": _canonical(capture.historical_readiness),
        "expected_population": {
            "bars": capture.historical_bar_count + capture.live_bar_count,
            "historical_bars": capture.historical_bar_count,
            "live_bars": capture.live_bar_count,
            "metric_records": (
                (capture.historical_bar_count + capture.live_bar_count)
                * len(COMPLETED_BAR_METRIC_IDS)
            ),
            "metric_ids": list(COMPLETED_BAR_METRIC_IDS),
        },
        "observed_population": {
            "bars": len(capture.bars),
            "selected_metric_records": len(capture.metrics),
            **asdict(capture.counters),
        },
        "lineage_disclosures": {
            "upstream_bar_conflict_evidence": capture.upstream_bar_conflict_evidence,
            "constituent_records_captured": capture.constituent_records_captured,
            "parameter_effective_time_enforced": False,
        },
        "integrity": {
            "canonical_payload_sha256": capture.payload_sha256,
            "html_sha256": _required_text(html_sha256, "html_sha256"),
        },
        "renderer": {
            "plotly_version": _required_text(plotly_version, "plotly_version"),
            "version": 1,
        },
    }
