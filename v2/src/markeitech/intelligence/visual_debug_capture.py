from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any

from nautilus_trader.model import BarType

from markeitech.acquisition.historical_messages import HistoricalReadinessEvent
from markeitech.intelligence.completed_bars import CompletedBarInput, CompletedBarSource
from markeitech.intelligence.metrics import MetricValue
from markeitech.intelligence.session_measurements import COMPLETED_BAR_METRIC_IDS

ARTIFACT_KIND = "passive-completed-bar-debug-projection"
CAPTURE_SCOPE = "BOUNDED_OBSERVER_RECEIVE_CUT_NOT_GLOBALLY_FINAL"
_HISTORICAL_SOURCES = {
    CompletedBarSource.HISTORICAL_PROVIDER,
    CompletedBarSource.HISTORICAL_AGGREGATE,
}
_LIVE_SOURCES = {
    CompletedBarSource.LIVE_NATIVE,
    CompletedBarSource.LIVE_AGGREGATE,
}


def _required_text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty")
    return value.strip()


def _positive(value: int, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _non_negative(value: int, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


@dataclass(frozen=True, slots=True)
class CaptureGap:
    preceding_interval_end_ns: int
    following_interval_start_ns: int
    duration_ns: int
    preceding_source: str
    following_source: str
    reason: str = "UNCLASSIFIED_TEMPORAL_GAP"


@dataclass(frozen=True, slots=True)
class CaptureCounters:
    bar_publications: int
    metric_publications: int
    bar_transport_duplicates: int
    metric_transport_duplicates: int
    stale_metric_revisions: int
    higher_metric_revisions: int
    post_cut_arrivals_accounted: bool


@dataclass(frozen=True, slots=True)
class FrozenVisualDebugCapture:
    schema_version: int
    artifact_kind: str
    capture_scope: str
    selection_state: str
    selection_mode: str
    capture_id: str
    run_id: str
    configuration_identity: str
    capture_policy_version: int
    instrument_id: str
    bar_specification: str
    interval_ns: int
    target_historical_bars: int
    target_live_bars: int
    selected_historical_bars: int
    selected_live_bars: int
    collection_started_ns: int
    frozen_at_ns: int
    cutoff_interval_end_ns: int | None
    historical_readiness: HistoricalReadinessEvent | None
    gaps: tuple[CaptureGap, ...]
    bars: tuple[CompletedBarInput, ...]
    metrics: tuple[MetricValue, ...]
    incomplete_metric_intervals: tuple[int, ...]
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
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


class VisualDebugCaptureCollector:
    """Passive, bounded, single-series observer; it never creates market truth."""

    def __init__(
        self,
        *,
        instrument_id: str,
        analytical_profile_id: str,
        analytical_profile_version: int,
        bar_specification: str,
        parameter_version: int,
        target_historical_bars: int,
        target_live_bars: int,
    ) -> None:
        self.instrument_id = _required_text(instrument_id, "instrument_id")
        self.analytical_profile_id = _required_text(
            analytical_profile_id,
            "analytical_profile_id",
        )
        self.analytical_profile_version = _positive(
            analytical_profile_version,
            "analytical_profile_version",
        )
        self.bar_specification = _required_text(bar_specification, "bar_specification")
        self.parameter_version = _positive(parameter_version, "parameter_version")
        self.target_historical_bars = _non_negative(
            target_historical_bars,
            "target_historical_bars",
        )
        self.target_live_bars = _non_negative(target_live_bars, "target_live_bars")
        if self.target_historical_bars + self.target_live_bars == 0:
            raise ValueError("at least one visual-debug population target must be positive")
        self.interval_ns = int(
            BarType.from_str(f"{self.instrument_id}-{self.bar_specification}")
            .spec.get_interval_ns(),
        )
        self._bars: dict[int, CompletedBarInput] = {}
        self._metrics: dict[tuple[str, int], dict[int, MetricValue]] = {}
        self._frozen = False
        self._conflict: str | None = None
        self._bar_publications = 0
        self._metric_publications = 0
        self._bar_duplicates = 0
        self._metric_duplicates = 0
        self._stale = 0
        self._higher = 0

    @property
    def conflict(self) -> str | None:
        return self._conflict

    @property
    def selection_mode(self) -> str:
        if self.target_historical_bars and self.target_live_bars:
            return "HISTORICAL_PLUS_LIVE"
        if self.target_historical_bars:
            return "HISTORICAL_ONLY"
        return "LIVE_ONLY"

    def accept_bar(self, bar: CompletedBarInput) -> bool:
        if self._frozen:
            return False
        if (
            bar.instrument_id != self.instrument_id
            or bar.bar_specification != self.bar_specification
            or bar.analytical_profile_id != self.analytical_profile_id
            or bar.analytical_profile_version != self.analytical_profile_version
            or not bar.complete
        ):
            return False
        self._bar_publications += 1
        if bar.interval_ns != self.interval_ns or bar.interval_start_ns % self.interval_ns:
            self._conflict = "BAR_INTERVAL_IDENTITY_CONFLICT"
            return False
        existing = self._bars.get(bar.interval_end_ns)
        if existing is not None:
            if existing == bar:
                self._bar_duplicates += 1
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
                self._metric_duplicates += 1
                return False
            self._conflict = "PROJECTION_METRIC_CONFLICT"
            return False
        if revisions:
            maximum = max(revisions)
            if metric.revision < maximum:
                self._stale += 1
                return False
            if metric.revision > maximum:
                self._higher += 1
        revisions[metric.revision] = metric
        return True

    def selected_records(
        self,
    ) -> tuple[tuple[CompletedBarInput, ...], tuple[MetricValue, ...], tuple[int, ...]]:
        historical = (
            sorted(
                (bar for bar in self._bars.values() if bar.source in _HISTORICAL_SOURCES),
                key=lambda bar: bar.interval_end_ns,
            )[-self.target_historical_bars :]
            if self.target_historical_bars
            else []
        )
        live = (
            sorted(
                (bar for bar in self._bars.values() if bar.source in _LIVE_SOURCES),
                key=lambda bar: bar.interval_end_ns,
            )[-self.target_live_bars :]
            if self.target_live_bars
            else []
        )
        bars = tuple(sorted((*historical, *live), key=lambda bar: bar.interval_end_ns))
        metrics: list[MetricValue] = []
        incomplete: list[int] = []
        for bar in bars:
            observed_revisions = {
                revision
                for metric_id in COMPLETED_BAR_METRIC_IDS
                for revision in self._metrics.get((metric_id, bar.interval_end_ns), {})
            }
            if not observed_revisions:
                incomplete.append(bar.interval_end_ns)
                continue
            highest = max(observed_revisions)
            cohort = tuple(
                self._metrics[(metric_id, bar.interval_end_ns)][highest]
                for metric_id in COMPLETED_BAR_METRIC_IDS
                if highest in self._metrics.get((metric_id, bar.interval_end_ns), {})
            )
            if len(cohort) != len(COMPLETED_BAR_METRIC_IDS):
                incomplete.append(bar.interval_end_ns)
            elif not self._valid_metric_cohort(bar, cohort):
                self._conflict = "METRIC_COHORT_INVALID"
                return bars, (), tuple(incomplete)
            metrics.extend(sorted(cohort, key=lambda item: item.metric_id))
        return bars, tuple(metrics), tuple(incomplete)

    def target_population_is_complete(self) -> bool:
        bars, _, incomplete = self.selected_records()
        historical = sum(bar.source in _HISTORICAL_SOURCES for bar in bars)
        live = sum(bar.source in _LIVE_SOURCES for bar in bars)
        return (
            self._conflict is None
            and historical == self.target_historical_bars
            and live == self.target_live_bars
            and not incomplete
        )

    def freeze(
        self,
        *,
        run_id: str,
        configuration_identity: str,
        capture_policy_version: int,
        collection_started_ns: int,
        frozen_at_ns: int,
        historical_readiness: HistoricalReadinessEvent | None,
    ) -> FrozenVisualDebugCapture:
        if self._frozen:
            raise ValueError("capture has already frozen")
        if self._conflict is not None:
            raise ValueError(self._conflict)
        bars, metrics, incomplete = self.selected_records()
        if self._conflict is not None:
            raise ValueError(self._conflict)
        selected_historical = sum(bar.source in _HISTORICAL_SOURCES for bar in bars)
        selected_live = sum(bar.source in _LIVE_SOURCES for bar in bars)
        gaps = tuple(
            CaptureGap(
                preceding_interval_end_ns=previous.interval_end_ns,
                following_interval_start_ns=current.interval_start_ns,
                duration_ns=current.interval_start_ns - previous.interval_end_ns,
                preceding_source=previous.source.value,
                following_source=current.source.value,
            )
            for previous, current in zip(bars, bars[1:], strict=False)
            if current.interval_start_ns > previous.interval_end_ns
        )
        counts_complete = (
            selected_historical == self.target_historical_bars
            and selected_live == self.target_live_bars
        )
        expected_history_ref = (
            f"historical:{historical_readiness.request_id}"
            if historical_readiness is not None
            else None
        )
        historical_lineage_complete = (
            not self.target_historical_bars
            or (
                historical_readiness is not None
                and historical_readiness.state == "READY"
                and all(
                    expected_history_ref in bar.evidence_refs
                    for bar in bars
                    if bar.source in _HISTORICAL_SOURCES
                )
            )
        )
        if not bars:
            state = "NO_COMPATIBLE_RECORDS"
        elif (
            counts_complete
            and not incomplete
            and not historical_lineage_complete
        ):
            state = "PARTIAL_HISTORICAL_LINEAGE"
        elif counts_complete and not incomplete:
            state = "COMPLETE_WITH_GAPS" if gaps else "COMPLETE_CONTIGUOUS"
        elif not counts_complete and incomplete:
            state = "PARTIAL_COUNTS_AND_METRIC_COHORTS"
        elif not counts_complete:
            state = "PARTIAL_COUNTS_WITH_GAPS" if gaps else "PARTIAL_COUNTS"
        else:
            state = "PARTIAL_METRIC_COHORTS"
        core = {
            "run_id": _required_text(run_id, "run_id"),
            "configuration_identity": _required_text(
                configuration_identity,
                "configuration_identity",
            ),
            "capture_policy_version": _positive(capture_policy_version, "capture_policy_version"),
            "instrument_id": self.instrument_id,
            "bar_specification": self.bar_specification,
            "interval_ns": self.interval_ns,
            "selection_mode": self.selection_mode,
            "selection_state": state,
            "target_historical_bars": self.target_historical_bars,
            "target_live_bars": self.target_live_bars,
            "collection_started_ns": _positive(collection_started_ns, "collection_started_ns"),
            "frozen_at_ns": _positive(frozen_at_ns, "frozen_at_ns"),
            "historical_readiness": historical_readiness,
            "gaps": gaps,
            "bars": bars,
            "metrics": metrics,
            "incomplete_metric_intervals": tuple(incomplete),
        }
        payload_digest = canonical_sha256(core)
        capture_id = hashlib.sha256(
            f"{core['run_id']}:{core['configuration_identity']}:{payload_digest}".encode(),
        ).hexdigest()
        self._frozen = True
        return FrozenVisualDebugCapture(
            schema_version=2,
            artifact_kind=ARTIFACT_KIND,
            capture_scope=CAPTURE_SCOPE,
            selection_state=state,
            selection_mode=self.selection_mode,
            capture_id=capture_id,
            run_id=core["run_id"],
            configuration_identity=core["configuration_identity"],
            capture_policy_version=core["capture_policy_version"],
            instrument_id=self.instrument_id,
            bar_specification=self.bar_specification,
            interval_ns=self.interval_ns,
            target_historical_bars=self.target_historical_bars,
            target_live_bars=self.target_live_bars,
            selected_historical_bars=selected_historical,
            selected_live_bars=selected_live,
            collection_started_ns=core["collection_started_ns"],
            frozen_at_ns=core["frozen_at_ns"],
            cutoff_interval_end_ns=bars[-1].interval_end_ns if bars else None,
            historical_readiness=historical_readiness,
            gaps=gaps,
            bars=bars,
            metrics=metrics,
            incomplete_metric_intervals=tuple(incomplete),
            counters=CaptureCounters(
                bar_publications=self._bar_publications,
                metric_publications=self._metric_publications,
                bar_transport_duplicates=self._bar_duplicates,
                metric_transport_duplicates=self._metric_duplicates,
                stale_metric_revisions=self._stale,
                higher_metric_revisions=self._higher,
                post_cut_arrivals_accounted=False,
            ),
            upstream_bar_conflict_evidence="NOT_SUPPLIED",
            constituent_records_captured=False,
            payload_sha256=payload_digest,
        )

    @staticmethod
    def _valid_metric_cohort(bar: CompletedBarInput, values: tuple[MetricValue, ...]) -> bool:
        if {value.metric_id for value in values} != set(COMPLETED_BAR_METRIC_IDS):
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
        return all(by_id[metric_id].value == expected for metric_id, expected in exact.items())


def frozen_capture_manifest(
    capture: FrozenVisualDebugCapture,
    *,
    html_sha256: str,
    plotly_version: str,
    renderer_layout: dict[str, int],
) -> dict[str, Any]:
    return {
        "schema_version": capture.schema_version,
        "artifact_kind": capture.artifact_kind,
        "capture_scope": capture.capture_scope,
        "selection_state": capture.selection_state,
        "selection_mode": capture.selection_mode,
        "capture_id": capture.capture_id,
        "run_id": capture.run_id,
        "configuration_identity": capture.configuration_identity,
        "capture_policy_version": capture.capture_policy_version,
        "series": {
            "instrument_id": capture.instrument_id,
            "bar_specification": capture.bar_specification,
            "interval_ns": capture.interval_ns,
        },
        "collection_started_ns": capture.collection_started_ns,
        "frozen_at_ns": capture.frozen_at_ns,
        "cutoff_interval_end_ns": capture.cutoff_interval_end_ns,
        "historical_readiness": _canonical(capture.historical_readiness),
        "target_population": {
            "historical_bars": capture.target_historical_bars,
            "live_bars": capture.target_live_bars,
        },
        "selected_population": {
            "bars": len(capture.bars),
            "historical_bars": capture.selected_historical_bars,
            "live_bars": capture.selected_live_bars,
            "metric_records": len(capture.metrics),
            "incomplete_metric_intervals": list(capture.incomplete_metric_intervals),
            "source_counts": {
                source.value: sum(bar.source is source for bar in capture.bars)
                for source in CompletedBarSource
            },
            **asdict(capture.counters),
        },
        "gaps": _canonical(capture.gaps),
        "lineage_disclosures": {
            "upstream_bar_conflict_evidence": capture.upstream_bar_conflict_evidence,
            "constituent_records_captured": capture.constituent_records_captured,
            "parameter_effective_time_enforced": False,
            "startup_replay_available": False,
            "post_cut_publications_may_exist": True,
            "capture_changes_upstream_runtime": False,
        },
        "integrity": {
            "canonical_payload_sha256": capture.payload_sha256,
            "html_sha256": _required_text(html_sha256, "html_sha256"),
        },
        "renderer": {
            "plotly_version": _required_text(plotly_version, "plotly_version"),
            "version": 2,
            "layout": dict(renderer_layout),
        },
    }
