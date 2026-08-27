from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum, StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

from markeitech.intelligence.completed_bars import CompletedBarInput
from markeitech.intelligence.entities import EntityRevision
from markeitech.intelligence.metrics import MetricValue
from markeitech.intelligence.quote_metrics import QUOTE_METRIC_IDS
from markeitech.intelligence.rolling_measurements import (
    ROLLING_METRIC_SUFFIXES,
    rolling_metric_id,
)
from markeitech.intelligence.session_measurements import COMPLETED_BAR_METRIC_IDS
from markeitech.intelligence.session_references import SESSION_REFERENCE_METRIC_IDS
from markeitech.intelligence.session_windows import OPENING_RANGE_FIELDS, POWER_HOUR_FIELDS

if TYPE_CHECKING:
    from markeitech.system.config import SystemConfig


class ReviewItemKind(StrEnum):
    METRIC = "metric"
    ENTITY_APPLICATION = "entity_application"
    PURE_COMPONENT = "pure_component"
    DEFERRED_COMPONENT = "deferred_component"


class ActivationState(StrEnum):
    ENABLED = "ENABLED"
    PURE_ONLY = "PURE_ONLY"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    DEFERRED = "DEFERRED"


class ProjectionStatus(StrEnum):
    PENDING_REVIEW = "PENDING_REVIEW"
    OBSERVED = "OBSERVED"
    NOT_OBSERVED_BY_CAPTURE_CUTOFF = "NOT_OBSERVED_BY_CAPTURE_CUTOFF"
    UNSUPPORTED_FOR_ES = "UNSUPPORTED_FOR_ES"
    PURE_ONLY_NO_RUNTIME_PRODUCER = "PURE_ONLY_NO_RUNTIME_PRODUCER"
    DEFERRED_BY_ACCEPTED_PLAN = "DEFERRED_BY_ACCEPTED_PLAN"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    BLOCKED_BY_KNOWN_DEFECT = "BLOCKED_BY_KNOWN_DEFECT"


@dataclass(frozen=True, slots=True)
class ReviewKey:
    item_kind: ReviewItemKind
    implementation_id: str
    definition_or_metric_id: str
    definition_or_metric_version: int
    parameter_identity: str
    application_id: str
    instrument_id: str
    analytical_profile_id: str
    analytical_profile_version: int
    session_phase_or_window: str
    analytical_horizon: str
    source_bar_specification: str
    producer_id: str

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if isinstance(value, str) and not value:
                raise ValueError(f"review key {field.name} must not be empty")
        if self.definition_or_metric_version <= 0 or self.analytical_profile_version <= 0:
            raise ValueError("review key versions must be positive")

    @property
    def canonical_json(self) -> str:
        return canonical_json(to_json_value(self))

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class ReviewInventoryItem:
    key: ReviewKey
    activation_state: ActivationState
    representation: str
    expected_canonical_type: str
    canonical_subject_id: str
    disposition: str


@dataclass(frozen=True, slots=True)
class ReviewInventory:
    schema_version: int
    checkout_identity: str
    configuration_identity: str
    items: tuple[ReviewInventoryItem, ...]

    def __post_init__(self) -> None:
        identity_incomplete = (
            self.schema_version <= 0
            or not self.checkout_identity
            or not self.configuration_identity
        )
        if identity_incomplete:
            raise ValueError("review inventory identity is incomplete")
        digests = tuple(item.key.digest for item in self.items)
        if len(digests) != len(set(digests)):
            raise ValueError("review inventory contains duplicate review identities")
        if tuple(sorted(digests)) != digests:
            raise ValueError("review inventory must be ordered by identity digest")

    @property
    def digest(self) -> str:
        return hashlib.sha256(canonical_json(to_json_value(self)).encode()).hexdigest()


def review_inventory_from_json(value: Mapping[str, Any]) -> ReviewInventory:
    items = []
    for raw_item in value["items"]:
        raw_key = raw_item["key"]
        key = ReviewKey(
            item_kind=ReviewItemKind(raw_key["item_kind"]),
            implementation_id=raw_key["implementation_id"],
            definition_or_metric_id=raw_key["definition_or_metric_id"],
            definition_or_metric_version=raw_key["definition_or_metric_version"],
            parameter_identity=raw_key["parameter_identity"],
            application_id=raw_key["application_id"],
            instrument_id=raw_key["instrument_id"],
            analytical_profile_id=raw_key["analytical_profile_id"],
            analytical_profile_version=raw_key["analytical_profile_version"],
            session_phase_or_window=raw_key["session_phase_or_window"],
            analytical_horizon=raw_key["analytical_horizon"],
            source_bar_specification=raw_key["source_bar_specification"],
            producer_id=raw_key["producer_id"],
        )
        items.append(ReviewInventoryItem(
            key=key,
            activation_state=ActivationState(raw_item["activation_state"]),
            representation=raw_item["representation"],
            expected_canonical_type=raw_item["expected_canonical_type"],
            canonical_subject_id=raw_item["canonical_subject_id"],
            disposition=raw_item["disposition"],
        ))
    return ReviewInventory(
        schema_version=value["schema_version"],
        checkout_identity=value["checkout_identity"],
        configuration_identity=value["configuration_identity"],
        items=tuple(items),
    )


_PURE_COMPONENTS = (
    ("signed-displacement-v1", "signed_displacement"),
    ("signed-simple-return-v1", "signed_simple_return"),
    ("signed-path-efficiency-v1", "signed_path_efficiency"),
    ("sma-seeded-ema-v1", "sma_seeded_ema_value_slope_separation"),
    ("compression-expansion-projector-v1", "compression_expansion_projector"),
    ("directional-projector-v1", "directional_projector"),
    ("reference-state-projector-v1", "reference_state_projector"),
    ("trend-rotation-projector-v1", "trend_rotation_projector"),
    ("uniform-bar-volume-allocation-v1", "inferred_bar_volume_allocation"),
)

_DEFERRED_COMPONENTS = (
    ("bar-volume-distribution-entities", "inferred_poc_value_area_hvn_lvn"),
    ("semantic-interaction-events", "semantic_interaction_events"),
    ("options-intelligence", "options_intelligence"),
    ("cross-instrument-state", "cross_instrument_state"),
    ("opportunity-lifecycle", "opportunity_lifecycle"),
    ("sir-loke", "sir_loke"),
    ("ml-evaluation", "ml_evaluation"),
    ("execution", "execution"),
)


def build_review_inventory(
    config: SystemConfig,
    *,
    checkout_identity: str,
    configuration_identity: str,
) -> ReviewInventory:
    review = config.live_evidence_review
    instrument_id = review.instrument_id
    profile_id = review.analytical_profile_id
    profile_version = review.analytical_profile_version
    items: list[ReviewInventoryItem] = []

    def add_metric(
        metric_id: str,
        *,
        producer: str,
        selector: str,
        horizon: str,
        application: str,
        parameter: str,
        enabled: bool,
        representation: str = "text",
        window: str = "not_applicable",
    ) -> None:
        items.append(
            ReviewInventoryItem(
                key=ReviewKey(
                    item_kind=ReviewItemKind.METRIC,
                    implementation_id=f"markeitech.metric.{metric_id}.v1",
                    definition_or_metric_id=metric_id,
                    definition_or_metric_version=1,
                    parameter_identity=parameter,
                    application_id=application,
                    instrument_id=instrument_id,
                    analytical_profile_id=profile_id,
                    analytical_profile_version=profile_version,
                    session_phase_or_window=window,
                    analytical_horizon=horizon,
                    source_bar_specification=selector,
                    producer_id=producer,
                ),
                activation_state=(ActivationState.ENABLED if enabled else ActivationState.DEFERRED),
                representation=representation,
                expected_canonical_type="MetricValue",
                canonical_subject_id=metric_id,
                disposition=("runtime producer composed" if enabled else "producer disabled"),
            ),
        )

    quote = config.metrics.quote_quality
    for metric_id in QUOTE_METRIC_IDS:
        add_metric(
            metric_id,
            producer="QUOTE-QUALITY-METRICS",
            selector="quotes/default",
            horizon="latest_quote",
            application="es-top-of-book",
            parameter=f"parameter-version:{quote.parameter_version}",
            enabled=quote.enabled,
        )

    session = config.metrics.session_measurements
    completed = session.completed_bars
    for metric_id in COMPLETED_BAR_METRIC_IDS:
        add_metric(
            metric_id,
            producer="SESSION-METRICS",
            selector=completed.live_selector,
            horizon=f"{completed.calculation_interval_seconds}s",
            application="completed-bar-foundation",
            parameter=f"parameter-version:{session.parameter_version}",
            enabled=session.enabled,
            representation="geometry" if metric_id in {
                "completed_bar.open", "completed_bar.high", "completed_bar.low",
                "completed_bar.close", "completed_bar.volume",
            } else "text",
        )

    for metric_id in SESSION_REFERENCE_METRIC_IDS:
        add_metric(
            metric_id,
            producer="SESSION-METRICS",
            selector=session.session_references.historical_selector,
            horizon="session",
            application="session-references",
            parameter=f"parameter-version:{session.parameter_version}",
            enabled=session.enabled and session.session_references.enabled,
            window="primary-or-previous-session",
        )

    profile = next(item for item in session.profiles if item.profile_id == profile_id)
    for window in profile.windows:
        fields_for_window = (
            OPENING_RANGE_FIELDS if window.purpose == "opening_range" else POWER_HOUR_FIELDS
        )
        for field_name in fields_for_window:
            add_metric(
                f"{window.purpose}.{profile_id}.{window.window_id}.{field_name}",
                producer="SESSION-METRICS",
                selector=window.historical_selector,
                horizon=window.purpose,
                application=window.window_id,
                parameter=f"parameter-version:{session.parameter_version}",
                enabled=session.enabled and session.session_windows.enabled,
                representation="geometry" if field_name in {"high", "low"} else "text",
                window=window.window_id,
            )

    rolling = session.rolling_measurements
    for family in rolling.families:
        for candidate in family.candidates:
            for suffix in ROLLING_METRIC_SUFFIXES:
                add_metric(
                    rolling_metric_id(family.family_id, candidate.candidate_id, suffix),
                    producer="SESSION-METRICS",
                    selector=family.input_selector,
                    horizon=family.family_id,
                    application=candidate.candidate_id,
                    parameter=f"parameter-version:{session.parameter_version}",
                    enabled=session.enabled and rolling.enabled and candidate.active,
                )

    entity_config = config.metrics.entity_analysis
    for definition in entity_config.definitions:
        for application in definition.applications:
            applies = instrument_id in application.instrument_ids or (
                not application.instrument_ids and profile_id in application.analytical_profile_ids
            )
            items.append(
                ReviewInventoryItem(
                    key=ReviewKey(
                        item_kind=ReviewItemKind.ENTITY_APPLICATION,
                        implementation_id=definition.implementation_id,
                        definition_or_metric_id=definition.definition_id,
                        definition_or_metric_version=definition.entity_version,
                        parameter_identity=application.parameter_set_id,
                        application_id=application.application_id,
                        instrument_id=instrument_id,
                        analytical_profile_id=profile_id,
                        analytical_profile_version=profile_version,
                        session_phase_or_window=(
                            ",".join(application.session_phases) or "not_applicable"
                        ),
                        analytical_horizon=application.horizon,
                        source_bar_specification=application.source_selector,
                        producer_id=_entity_producer(definition.group),
                    ),
                    activation_state=(
                        ActivationState.ENABLED
                        if entity_config.enabled and definition.enabled and applies
                        else ActivationState.DEFERRED
                    ),
                    representation=(
                        "geometry"
                        if definition.group in {
                            "objective_session_reference_level", "swing_fvg_zone"
                        }
                        else "text"
                    ),
                    expected_canonical_type="EntityRevision",
                    canonical_subject_id=definition.entity_type,
                    disposition=(
                        "runtime producer composed"
                        if entity_config.enabled and definition.enabled and applies
                        else "not enabled or not applicable to ES"
                    ),
                ),
            )

    for implementation_id, component_id in _PURE_COMPONENTS:
        items.append(_non_runtime_item(
            kind=ReviewItemKind.PURE_COMPONENT,
            activation=ActivationState.PURE_ONLY,
            implementation_id=implementation_id,
            component_id=component_id,
            instrument_id=instrument_id,
            profile_id=profile_id,
            profile_version=profile_version,
            disposition="PURE_ONLY_NO_RUNTIME_PRODUCER",
        ))
    for implementation_id, component_id in _DEFERRED_COMPONENTS:
        items.append(_non_runtime_item(
            kind=ReviewItemKind.DEFERRED_COMPONENT,
            activation=ActivationState.DEFERRED,
            implementation_id=implementation_id,
            component_id=component_id,
            instrument_id=instrument_id,
            profile_id=profile_id,
            profile_version=profile_version,
            disposition="DEFERRED_BY_ACCEPTED_PLAN",
        ))

    return ReviewInventory(
        schema_version=1,
        checkout_identity=checkout_identity,
        configuration_identity=configuration_identity,
        items=tuple(sorted(items, key=lambda item: item.key.digest)),
    )


def _non_runtime_item(
    *,
    kind: ReviewItemKind,
    activation: ActivationState,
    implementation_id: str,
    component_id: str,
    instrument_id: str,
    profile_id: str,
    profile_version: int,
    disposition: str,
) -> ReviewInventoryItem:
    return ReviewInventoryItem(
        key=ReviewKey(
            item_kind=kind,
            implementation_id=implementation_id,
            definition_or_metric_id=component_id,
            definition_or_metric_version=1,
            parameter_identity="not_runtime_bound",
            application_id="es-review-disposition",
            instrument_id=instrument_id,
            analytical_profile_id=profile_id,
            analytical_profile_version=profile_version,
            session_phase_or_window="not_applicable",
            analytical_horizon="not_runtime_bound",
            source_bar_specification="not_runtime_bound",
            producer_id="none",
        ),
        activation_state=activation,
        representation="text",
        expected_canonical_type="none",
        canonical_subject_id=component_id,
        disposition=disposition,
    )


def _entity_producer(group: str) -> str:
    return {
        "objective_session_reference_level": "SESSION-REFERENCE-ENTITIES",
        "volatility_compression_expansion": "MARKET-STATE-ENTITIES",
        "direction_trend_rotation_reference": "MARKET-STATE-ENTITIES",
        "swing_fvg_zone": "MARKET-STRUCTURE-ENTITIES",
    }.get(group, "ENTITY-PRODUCER-UNKNOWN")


class ProjectionCollector:
    def __init__(
        self,
        *,
        instrument_id: str,
        bar_specifications: tuple[str, ...],
        maximum_bars_per_series: int,
        maximum_metric_subjects: int,
        maximum_entity_subjects: int,
    ) -> None:
        self.instrument_id = instrument_id
        self.bar_specifications = frozenset(bar_specifications)
        self.maximum_bars_per_series = maximum_bars_per_series
        self.maximum_metric_subjects = maximum_metric_subjects
        self.maximum_entity_subjects = maximum_entity_subjects
        self.bars: dict[str, OrderedDict[int, CompletedBarInput]] = {}
        self.metrics: OrderedDict[tuple[Any, ...], MetricValue] = OrderedDict()
        self.entities: OrderedDict[str, EntityRevision] = OrderedDict()
        self.counters = {name: 0 for name in (
            "accepted", "duplicates", "stale", "conflicts", "evicted", "ignored",
            "after_freeze_ignored",
        )}
        self.frozen = False

    def accept(self, value: CompletedBarInput | MetricValue | EntityRevision) -> bool:
        if self.frozen:
            self.counters["after_freeze_ignored"] += 1
            return False
        if isinstance(value, CompletedBarInput):
            return self._accept_bar(value)
        if isinstance(value, MetricValue):
            return self._accept_metric(value)
        if isinstance(value, EntityRevision):
            return self._accept_entity(value)
        raise TypeError("unsupported projection value")

    def _accept_bar(self, value: CompletedBarInput) -> bool:
        if (
            value.instrument_id != self.instrument_id
            or value.bar_specification not in self.bar_specifications
        ):
            self.counters["ignored"] += 1
            return False
        series = self.bars.setdefault(value.bar_specification, OrderedDict())
        existing = series.get(value.interval_end_ns)
        if existing is not None:
            return self._resolve_revision(existing, value, series, value.interval_end_ns)
        series[value.interval_end_ns] = value
        while len(series) > self.maximum_bars_per_series:
            series.popitem(last=False)
            self.counters["evicted"] += 1
        self.counters["accepted"] += 1
        return True

    def _accept_metric(self, value: MetricValue) -> bool:
        if value.instrument_id != self.instrument_id:
            self.counters["ignored"] += 1
            return False
        key = (
            value.instrument_id, value.metric_id, value.metric_version,
            value.parameter_version, value.session_id,
        )
        existing = self.metrics.get(key)
        if existing is not None:
            return self._resolve_revision(existing, value, self.metrics, key)
        self.metrics[key] = value
        while len(self.metrics) > self.maximum_metric_subjects:
            self.metrics.popitem(last=False)
            self.counters["evicted"] += 1
        self.counters["accepted"] += 1
        return True

    def _accept_entity(self, value: EntityRevision) -> bool:
        if value.identity.instrument_id != self.instrument_id:
            self.counters["ignored"] += 1
            return False
        existing = self.entities.get(value.entity_id)
        if existing is not None:
            return self._resolve_revision(existing, value, self.entities, value.entity_id)
        self.entities[value.entity_id] = value
        while len(self.entities) > self.maximum_entity_subjects:
            self.entities.popitem(last=False)
            self.counters["evicted"] += 1
        self.counters["accepted"] += 1
        return True

    def _resolve_revision(self, existing: Any, value: Any, target: Any, key: Any) -> bool:
        if value.revision < existing.revision:
            self.counters["stale"] += 1
            return False
        if value.revision == existing.revision:
            same_value = to_json_value(value) == to_json_value(existing)
            counter = "duplicates" if same_value else "conflicts"
            self.counters[counter] += 1
            return False
        target[key] = value
        self.counters["accepted"] += 1
        return True

    def freeze(self) -> None:
        if self.frozen:
            raise RuntimeError("projection collector already frozen")
        self.frozen = True

    @property
    def has_conflicts(self) -> bool:
        return self.counters["conflicts"] > 0


def build_projection_payload(
    *,
    run_id: str,
    frozen_at_ns: int,
    trigger_bar: CompletedBarInput,
    readiness: Mapping[str, Any],
    inventory: ReviewInventory,
    collector: ProjectionCollector,
    capture_policy: Mapping[str, Any],
    capture_timing: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not collector.frozen:
        raise ValueError("projection collector must be frozen")
    identity = {
        "run_id": run_id,
        "configuration_identity": inventory.configuration_identity,
        "inventory_digest": inventory.digest,
        "instrument_id": collector.instrument_id,
        "trigger_bar": to_json_value(trigger_bar),
        "capture_policy_version": capture_policy["capture_policy_version"],
    }
    capture_id = hashlib.sha256(canonical_json(identity).encode()).hexdigest()
    metric_records = tuple(to_json_value(item) for item in collector.metrics.values())
    entity_records = tuple(to_json_value(item) for item in collector.entities.values())
    bar_records = tuple(
        to_json_value(item)
        for selector in sorted(collector.bars)
        for item in collector.bars[selector].values()
    )
    ledger = []
    for item in inventory.items:
        key = item.key
        observed = _review_item_observed(
            item,
            tuple(collector.metrics.values()),
            tuple(collector.entities.values()),
        )
        if item.activation_state is ActivationState.PURE_ONLY:
            status = ProjectionStatus.PURE_ONLY_NO_RUNTIME_PRODUCER
        elif item.activation_state is ActivationState.NOT_IMPLEMENTED:
            status = ProjectionStatus.NOT_IMPLEMENTED
        elif item.activation_state is ActivationState.DEFERRED:
            status = ProjectionStatus.DEFERRED_BY_ACCEPTED_PLAN
        elif observed:
            status = ProjectionStatus.OBSERVED
        else:
            status = ProjectionStatus.NOT_OBSERVED_BY_CAPTURE_CUTOFF
        ledger.append({
            "review_key": to_json_value(key),
            "identity_digest": key.digest,
            "activation_state": item.activation_state.value,
            "representation": item.representation,
            "expected_canonical_type": item.expected_canonical_type,
            "canonical_subject_id": item.canonical_subject_id,
            "disposition": item.disposition,
            "capture_status": status.value,
            "human_review_outcome": ProjectionStatus.PENDING_REVIEW.value,
            "reviewer_note": "",
            "focused_artifact": f"focused/{key.item_kind.value}/{key.digest}.png",
        })
    return {
        "schema_version": 1,
        "artifact_kind": "source-faithful-projection-receive-cut",
        "capture_id": capture_id,
        "run_id": run_id,
        "frozen_at_ns": frozen_at_ns,
        "capture_completeness": "BOUNDED_RECEIVE_CUT_NOT_TRANSACTIONALLY_COMPLETE",
        "identity": identity,
        "capture_policy": to_json_value(capture_policy),
        "capture_timing": to_json_value(capture_timing or {}),
        "readiness": to_json_value(readiness),
        "inventory": to_json_value(inventory),
        "collector_counters": to_json_value(collector.counters),
        "canonical_records": {
            "completed_bars": bar_records,
            "metric_values": metric_records,
            "entity_revisions": entity_records,
        },
        "review_ledger": tuple(ledger),
    }


def _review_item_observed(
    item: ReviewInventoryItem,
    metrics: tuple[MetricValue, ...],
    entities: tuple[EntityRevision, ...],
) -> bool:
    key = item.key
    if key.item_kind is ReviewItemKind.METRIC:
        parameter_version = int(key.parameter_identity.rsplit(":", 1)[-1])
        return any(
            value.metric_id == key.definition_or_metric_id
            and value.metric_version == key.definition_or_metric_version
            and value.parameter_version == parameter_version
            and value.instrument_id == key.instrument_id
            for value in metrics
        )
    if key.item_kind is not ReviewItemKind.ENTITY_APPLICATION:
        return False
    for value in entities:
        identity = value.identity
        if (
            identity.entity_type != item.canonical_subject_id
            or identity.entity_version != key.definition_or_metric_version
            or identity.instrument_id != key.instrument_id
            or identity.analytical_profile_id != key.analytical_profile_id
            or identity.analytical_profile_version != key.analytical_profile_version
        ):
            continue
        dimensions = {dimension.name: dimension.value for dimension in identity.dimensions}
        constraints = {
            "definition_id": key.definition_or_metric_id,
            "horizon": key.analytical_horizon,
            "bar_specification": key.source_bar_specification,
            "parameter_set_id": key.parameter_identity,
        }
        if all(
            name not in dimensions or dimensions[name] == expected
            for name, expected in constraints.items()
        ):
            return True
    return False


def publish_projection_payload(payload: Mapping[str, Any], output_directory: Path) -> Path:
    run_id = str(payload["run_id"])
    capture_id = str(payload["capture_id"])
    run_directory = output_directory / ".pending" / run_id
    final_directory = run_directory / capture_id
    if final_directory.exists():
        raise FileExistsError(f"capture already exists: {capture_id}")
    staging = run_directory / f".{capture_id}.capture-staging"
    if staging.exists():
        raise FileExistsError(f"capture staging already exists: {capture_id}")
    staging.mkdir(parents=True)
    try:
        snapshot_path = staging / "projection-snapshot.json"
        ledger_path = staging / "review-ledger.json"
        snapshot = dict(payload)
        ledger = snapshot.pop("review_ledger")
        snapshot_path.write_text(canonical_json(snapshot) + "\n", encoding="utf-8")
        ledger_path.write_text(canonical_json({
            "schema_version": 1,
            "capture_id": capture_id,
            "items": ledger,
        }) + "\n", encoding="utf-8")
        staging.rename(final_directory)
    except Exception:
        for path in sorted(staging.rglob("*"), reverse=True) if staging.exists() else ():
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        if staging.exists():
            staging.rmdir()
        raise
    return final_directory


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def to_json_value(value: Any) -> Any:
    if value is None or isinstance(value, str | int | bool):
        return value
    if isinstance(value, float):
        if not value == value or value in {float("inf"), float("-inf")}:
            raise ValueError("non-finite float is not serializable")
        return value
    if isinstance(value, Decimal):
        return {"decimal": str(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, EntityRevision):
        result = {field.name: to_json_value(getattr(value, field.name)) for field in fields(value)}
        result["identity"]["entity_id"] = value.entity_id
        return result
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: to_json_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {
            str(key): to_json_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, tuple | list):
        return [to_json_value(item) for item in value]
    if isinstance(value, set | frozenset):
        return sorted((to_json_value(item) for item in value), key=canonical_json)
    raise TypeError(f"unsupported projection value: {type(value).__name__}")
