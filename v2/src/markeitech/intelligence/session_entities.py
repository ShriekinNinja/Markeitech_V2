from __future__ import annotations

import re
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType

from markeitech.intelligence._legacy_metric_value import LegacyMetricValue as MetricValue
from markeitech.intelligence.entities import (
    EntityAdmissionStatus,
    EntityDefinition,
    EntityEvidenceKind,
    EntityEvidenceReference,
    EntityIdentity,
    EntityIdentityDimension,
    EntityLifecycle,
    EntityPayload,
    EntityRegistry,
    EntityRevision,
    EntitySnapshot,
    EntityStateBook,
    EntityStateBookLimits,
)
from markeitech.intelligence.metrics import MetricFidelity, MetricHealth

SESSION_ENTITY_GROUP = "objective_session_reference_level"
"""Catalog group for objective session, gap, and reference-level entities."""
_TRADE_DATE_PATTERN = re.compile(r"(?:^|:)(\d{4}-\d{2}-\d{2})(?::|$)")


@dataclass(frozen=True, slots=True)
class AnalyticalSessionPayload(EntityPayload):
    """Carry objective active-session geometry, coverage, and supported volume."""

    session_id: str
    start_ns: int
    end_ns: int
    phase: str
    open: Decimal
    high: Decimal
    low: Decimal
    latest_close: Decimal
    range: Decimal
    location: Decimal | None
    volume: Decimal | None
    bar_vwap_estimate: Decimal | None
    coverage_ratio: Decimal
    complete: bool


@dataclass(frozen=True, slots=True)
class PreviousSessionReferencePayload(EntityPayload):
    """Carry finalized previous-session OHLC, return, coverage, and volume context."""

    session_id: str
    start_ns: int
    end_ns: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    range: Decimal
    simple_return: Decimal | None
    volume: Decimal | None
    bar_vwap_estimate: Decimal | None
    coverage_ratio: Decimal
    complete: bool


@dataclass(frozen=True, slots=True)
class OpeningRangePayload(EntityPayload):
    """Carry one calendar-relative opening-range window and completion state."""

    session_id: str
    window_id: str
    start_ns: int
    end_ns: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    range: Decimal
    volume: Decimal | None
    coverage_ratio: Decimal
    complete: bool


@dataclass(frozen=True, slots=True)
class GapPayload(EntityPayload):
    """Carry one objective price gap in points and optional ratio units."""

    session_id: str
    gap_kind: str
    points: Decimal
    ratio: Decimal | None


@dataclass(frozen=True, slots=True)
class ObjectiveLevelPayload(EntityPayload):
    """Carry an evidence-derived price interval without support or resistance meaning."""

    price: Decimal
    lower: Decimal
    upper: Decimal
    source_kind: str
    horizon: str
    role: str
    developing: bool


_PAYLOAD_TYPES: Mapping[str, type[EntityPayload]] = MappingProxyType(
    {
        "analytical_session": AnalyticalSessionPayload,
        "previous_session_reference": PreviousSessionReferencePayload,
        "opening_range": OpeningRangePayload,
        "gap": GapPayload,
    },
)


@dataclass(frozen=True, slots=True)
class SessionEntityApplication:
    """Scope one session entity to profiles, instruments, phases, and horizon."""

    application_id: str
    analytical_profile_ids: tuple[str, ...]
    instrument_ids: tuple[str, ...]
    session_phases: tuple[str, ...]
    horizon: str


@dataclass(frozen=True, slots=True)
class SessionEntityDefinition:
    """Bind a generic entity definition to metric roles and session applications."""

    definition_id: str
    definition: EntityDefinition
    metric_roles: Mapping[tuple[str, int], str]
    parameter_version: int
    applications: tuple[SessionEntityApplication, ...]

    def matching_applications(
        self,
        instrument_id: str,
        profile_id: str,
        session_phase: str,
    ) -> tuple[SessionEntityApplication, ...]:
        return tuple(
            application
            for application in self.applications
            if profile_id in application.analytical_profile_ids
            and (not application.instrument_ids or instrument_id in application.instrument_ids)
            and session_phase in application.session_phases
        )


@dataclass(frozen=True, slots=True)
class SessionEntityOwnerCounts:
    """Snapshot bounded session-entity admission and publication counters."""

    metrics_accepted: int
    metrics_duplicate: int
    metrics_stale: int
    metrics_conflict: int
    revisions_published: int
    revisions_duplicate: int
    revisions_rejected: int
    publications_deferred: int


class SessionEntityProjectionOwner:
    """Order-independent, bounded owner for Stage 9D.3 metric projections."""

    def __init__(
        self,
        *,
        definitions: tuple[SessionEntityDefinition, ...],
        instrument_profiles: Mapping[str, tuple[str, int]],
        limits: EntityStateBookLimits,
        maximum_metric_values: int,
        maximum_publications_per_cycle: int,
        source: str,
        schema_version: int,
    ) -> None:
        if not definitions:
            raise ValueError("session entity owner requires definitions")
        if maximum_metric_values <= 0 or maximum_publications_per_cycle <= 0:
            raise ValueError("session entity owner bounds must be positive")
        self._definitions = definitions
        self._profiles = MappingProxyType(dict(instrument_profiles))
        metric_keys = {
            dependency.key for spec in definitions for dependency in spec.definition.metric_inputs
        }
        registry = EntityRegistry(
            tuple(spec.definition for spec in definitions),
            metric_keys=metric_keys,
        )
        self._book = EntityStateBook(registry, limits)
        self._maximum_metric_values = maximum_metric_values
        self._maximum_publications = maximum_publications_per_cycle
        self._source = source.strip()
        self._schema_version = schema_version
        if not self._source or schema_version <= 0:
            raise ValueError("session entity source and schema version are required")
        self._metrics: dict[tuple[str, str | None, str, int, int], MetricValue] = {}
        self._pending_publications: deque[EntityRevision] = deque()
        self._metrics_accepted = 0
        self._metrics_duplicate = 0
        self._metrics_stale = 0
        self._metrics_conflict = 0
        self._revisions_published = 0
        self._revisions_duplicate = 0
        self._revisions_rejected = 0
        self._publications_deferred = 0

    def ingest(self, value: MetricValue, *, now_ns: int) -> tuple[EntityRevision, ...]:
        if not isinstance(value, MetricValue):
            raise ValueError("session entity input must be MetricValue")
        if value.instrument_id not in self._profiles:
            return self._drain_publications()
        if value.session_id is None:
            return self._drain_publications()
        trade_date = _trade_date(value.session_id)
        session_phase = _session_phase(value.session_id, trade_date)
        relevant = tuple(
            (spec, application)
            for spec in self._definitions
            if value.key in spec.metric_roles and value.parameter_version == spec.parameter_version
            for application in spec.matching_applications(
                value.instrument_id,
                self._profiles[value.instrument_id][0],
                session_phase,
            )
        )
        if not relevant:
            return self._drain_publications()
        key = (
            value.instrument_id,
            value.session_id,
            value.metric_id,
            value.metric_version,
            value.parameter_version,
        )
        current = self._metrics.get(key)
        if current is not None:
            if value.revision < current.revision or value.published_ts_ns < current.published_ts_ns:
                self._metrics_stale += 1
                return self._drain_publications()
            if value.revision == current.revision:
                if value == current:
                    self._metrics_duplicate += 1
                else:
                    self._metrics_conflict += 1
                return self._drain_publications()
        self._metrics[key] = value
        self._metrics_accepted += 1
        self._trim_metrics()

        projected: list[EntityRevision] = []
        for spec, application in relevant:
            if len(self._pending_publications) + len(projected) >= self._maximum_metric_values:
                self._revisions_rejected += 1
                continue
            candidate = self._project(spec, application, value, now_ns=now_ns)
            if candidate is None:
                continue
            admission = self._book.admit(candidate)
            if admission.status in {EntityAdmissionStatus.ADDED, EntityAdmissionStatus.UPDATED}:
                projected.append(candidate)
            elif admission.status is EntityAdmissionStatus.DUPLICATE:
                self._revisions_duplicate += 1
            else:
                self._revisions_rejected += 1
        self._pending_publications.extend(projected)
        return self._drain_publications()

    def snapshot(
        self,
        generated_ts_ns: int,
        *,
        instrument_id: str | None = None,
        entity_type: str | None = None,
        analytical_profile_id: str | None = None,
        analytical_profile_version: int | None = None,
        lifecycles: tuple[EntityLifecycle, ...] | None = None,
    ) -> EntitySnapshot:
        return self._book.snapshot(
            generated_ts_ns,
            instrument_id=instrument_id,
            entity_type=entity_type,
            analytical_profile_id=analytical_profile_id,
            analytical_profile_version=analytical_profile_version,
            lifecycles=lifecycles,
        )

    @property
    def counts(self) -> SessionEntityOwnerCounts:
        return SessionEntityOwnerCounts(
            self._metrics_accepted,
            self._metrics_duplicate,
            self._metrics_stale,
            self._metrics_conflict,
            self._revisions_published,
            self._revisions_duplicate,
            self._revisions_rejected,
            self._publications_deferred,
        )

    @property
    def retained_metric_values(self) -> int:
        return len(self._metrics)

    @property
    def pending_publications(self) -> int:
        return len(self._pending_publications)

    def _project(
        self,
        spec: SessionEntityDefinition,
        application: SessionEntityApplication,
        trigger: MetricValue,
        *,
        now_ns: int,
    ) -> EntityRevision | None:
        if trigger.session_id is None:
            return None
        profile_id, profile_version = self._profiles[trigger.instrument_id]
        values = self._subject_values(spec, trigger)
        context = _identity_context(spec, application, trigger, values)
        try:
            identity = EntityIdentity(
                entity_type=spec.definition.entity_type,
                entity_version=spec.definition.version,
                instrument_id=trigger.instrument_id,
                analytical_profile_id=profile_id,
                analytical_profile_version=profile_version,
                dimensions=tuple(
                    EntityIdentityDimension(name, context[name])
                    for name in spec.definition.identity_dimensions
                ),
            )
        except KeyError as exc:
            raise ValueError(
                f"unsupported identity dimension for {spec.definition_id}: {exc.args[0]}",
            ) from exc

        usable, missing = _usable_evidence(spec, values)
        payload = _payload(spec, trigger, usable, context) if not missing else None
        current = self._book.get(identity.entity_id)
        revision_number = 1 if current is None else current.revision + 1
        health = _entity_health(usable, missing)
        fidelity = _entity_fidelity(usable, missing)
        lifecycle = _entity_lifecycle(spec, payload, health, usable)
        evidence = tuple(_evidence_reference(item) for item in usable.values())
        observed_ns = max(
            (item.observed_ts_ns for item in usable.values()),
            default=trigger.observed_ts_ns,
        )
        calculated_ns = max(
            now_ns,
            observed_ns,
            *(item.calculated_ts_ns for item in usable.values()),
        )
        latest_input_publication_ns = max(
            (item.published_ts_ns for item in usable.values()),
            default=calculated_ns,
        )
        published_ns = max(calculated_ns, latest_input_publication_ns)
        effective_ns = max(
            (item.effective_ts_ns for item in usable.values()),
            default=trigger.effective_ts_ns,
        )
        return EntityRevision(
            identity=identity,
            revision=revision_number,
            parameter_version=spec.parameter_version,
            payload=payload,
            lifecycle=lifecycle,
            effective_ts_ns=effective_ns,
            observed_ts_ns=observed_ns,
            calculated_ts_ns=calculated_ns,
            published_ts_ns=published_ns,
            health=health,
            fidelity=fidelity,
            evidence_refs=evidence,
            missing_reasons=tuple(missing),
            conflict_reasons=(),
            source=self._source,
            schema_version=self._schema_version,
            previous_revision=None if current is None else current.revision,
        )

    def _subject_values(
        self,
        spec: SessionEntityDefinition,
        trigger: MetricValue,
    ) -> dict[str, MetricValue]:
        result: dict[str, MetricValue] = {}
        for dependency in spec.definition.metric_inputs:
            candidate = self._metrics.get(
                (
                    trigger.instrument_id,
                    trigger.session_id,
                    dependency.metric_id,
                    dependency.metric_version,
                    trigger.parameter_version,
                ),
            )
            if candidate is not None:
                result[spec.metric_roles[dependency.key]] = candidate
        return result

    def _trim_metrics(self) -> None:
        while len(self._metrics) > self._maximum_metric_values:
            oldest = min(
                self._metrics,
                key=lambda key: (
                    self._metrics[key].published_ts_ns,
                    self._metrics[key].effective_ts_ns,
                    key,
                ),
            )
            del self._metrics[oldest]

    def _drain_publications(self) -> tuple[EntityRevision, ...]:
        published: list[EntityRevision] = []
        while self._pending_publications and len(published) < self._maximum_publications:
            published.append(self._pending_publications.popleft())
        self._revisions_published += len(published)
        if self._pending_publications:
            self._publications_deferred += len(self._pending_publications)
        return tuple(published)


def _usable_evidence(
    spec: SessionEntityDefinition,
    values: Mapping[str, MetricValue],
) -> tuple[dict[str, MetricValue], list[str]]:
    usable: dict[str, MetricValue] = {}
    missing: list[str] = []
    for dependency in spec.definition.metric_inputs:
        role = spec.metric_roles[dependency.key]
        value = values.get(role)
        valid = (
            value is not None
            and value.value is not None
            and value.health in dependency.permitted_health
            and value.fidelity in dependency.permitted_fidelities
        )
        if valid:
            usable[role] = value
        elif dependency.required:
            missing.append(f"required_metric_unavailable:{role}")
    return usable, missing


def _payload(
    spec: SessionEntityDefinition,
    trigger: MetricValue,
    values: Mapping[str, MetricValue],
    context: Mapping[str, str],
) -> EntityPayload:
    entity_type = spec.definition.entity_type
    if entity_type == "analytical_session":
        return AnalyticalSessionPayload(
            trigger.session_id or "",
            _integer(values, "start_ns"),
            _integer(values, "end_ns"),
            context["session_phase"],
            _decimal(values, "open"),
            _decimal(values, "high"),
            _decimal(values, "low"),
            _decimal(values, "latest_close"),
            _decimal(values, "range"),
            _optional_decimal(values, "location"),
            _optional_decimal(values, "volume"),
            _optional_decimal(values, "bar_vwap_estimate"),
            _decimal(values, "coverage_ratio"),
            _boolean(values, "complete"),
        )
    if entity_type == "previous_session_reference":
        return PreviousSessionReferencePayload(
            trigger.session_id or "",
            _integer(values, "start_ns"),
            _integer(values, "end_ns"),
            _decimal(values, "open"),
            _decimal(values, "high"),
            _decimal(values, "low"),
            _decimal(values, "close"),
            _decimal(values, "range"),
            _optional_decimal(values, "simple_return"),
            _optional_decimal(values, "volume"),
            _optional_decimal(values, "bar_vwap_estimate"),
            _decimal(values, "coverage_ratio"),
            _boolean(values, "complete"),
        )
    if entity_type == "opening_range":
        return OpeningRangePayload(
            trigger.session_id or "",
            context["window_id"],
            _integer(values, "start_ns"),
            _integer(values, "end_ns"),
            _decimal(values, "open"),
            _decimal(values, "high"),
            _decimal(values, "low"),
            _decimal(values, "close"),
            _decimal(values, "range"),
            _optional_decimal(values, "volume"),
            _decimal(values, "coverage_ratio"),
            _boolean(values, "complete"),
        )
    if entity_type == "gap":
        return GapPayload(
            trigger.session_id or "",
            context["gap_kind"],
            _decimal(values, "points"),
            _optional_decimal(values, "ratio"),
        )
    if entity_type.startswith("objective_level."):
        price = _decimal(values, "price")
        complete = _optional_boolean(values, "source_complete")
        return ObjectiveLevelPayload(
            price,
            price,
            price,
            context["source_metric"],
            context["horizon"],
            "OBJECTIVE_REFERENCE",
            not bool(complete),
        )
    raise ValueError(f"unsupported Stage 9D.3 entity type: {entity_type}")


def _identity_context(
    spec: SessionEntityDefinition,
    application: SessionEntityApplication,
    trigger: MetricValue,
    values: Mapping[str, MetricValue],
) -> dict[str, str]:
    session_id = trigger.session_id or ""
    trade_date = _trade_date(session_id)
    phase = _session_phase(session_id, trade_date)
    source = values.get("price", trigger)
    return {
        "definition_id": spec.definition_id,
        "gap_kind": "indicative" if ".indicative." in trigger.metric_id else "opening",
        "horizon": application.horizon,
        "session_id": session_id,
        "session_phase": phase,
        "source_metric": source.metric_id,
        "source_subject": source.session_id or session_id,
        "trade_date": trade_date,
        "window_id": session_id.rsplit(":", 1)[-1],
    }


def _entity_lifecycle(
    spec: SessionEntityDefinition,
    payload: EntityPayload | None,
    health: MetricHealth,
    values: Mapping[str, MetricValue],
) -> EntityLifecycle:
    if payload is None:
        return EntityLifecycle.WARMING
    if health in {MetricHealth.DEGRADED, MetricHealth.STALE}:
        return (
            EntityLifecycle.DEGRADED if health is MetricHealth.DEGRADED else EntityLifecycle.STALE
        )
    if spec.definition.entity_type == "analytical_session":
        return EntityLifecycle.COMPLETE if _boolean(values, "complete") else EntityLifecycle.ACTIVE
    if spec.definition.entity_type in {"previous_session_reference", "opening_range"}:
        return EntityLifecycle.COMPLETE if _boolean(values, "complete") else EntityLifecycle.ACTIVE
    if spec.definition.entity_type == "gap":
        return EntityLifecycle.COMPLETE
    if spec.definition.entity_type.startswith("objective_level."):
        complete = _optional_boolean(values, "source_complete")
        return EntityLifecycle.COMPLETE if complete else EntityLifecycle.ACTIVE
    return EntityLifecycle.ACTIVE


def _entity_health(values: Mapping[str, MetricValue], missing: list[str]) -> MetricHealth:
    if missing:
        return MetricHealth.WARMING
    return _worst_health(tuple(item.health for item in values.values()))


def _entity_fidelity(values: Mapping[str, MetricValue], missing: list[str]) -> MetricFidelity:
    if missing:
        return MetricFidelity.PARTIAL
    return _worst_fidelity(tuple(item.fidelity for item in values.values()))


def _evidence_reference(value: MetricValue) -> EntityEvidenceReference:
    return EntityEvidenceReference(
        kind=EntityEvidenceKind.METRIC,
        definition_id=value.metric_id,
        reference_id=(
            f"metric:{value.metric_id}:{value.instrument_id}:"
            f"{value.session_id or 'none'}:{value.parameter_version}"
        ),
        version=value.metric_version,
        revision=value.revision,
        effective_ts_ns=value.effective_ts_ns,
        health=value.health,
        fidelity=value.fidelity,
    )


def _trade_date(session_id: str) -> str:
    match = _TRADE_DATE_PATTERN.search(session_id)
    if match is None:
        raise ValueError(f"session identity does not contain a trade date: {session_id}")
    return match.group(1)


def _session_phase(session_id: str, trade_date: str) -> str:
    suffix = session_id.split(f":{trade_date}:", 1)
    if len(suffix) != 2 or not suffix[1]:
        raise ValueError(f"session identity does not contain a phase: {session_id}")
    return suffix[1].split(":", 1)[0]


def _decimal(values: Mapping[str, MetricValue], role: str) -> Decimal:
    value = values[role].value
    if isinstance(value, bool) or not isinstance(value, Decimal | int | float):
        raise ValueError(f"{role} must be numeric")
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _optional_decimal(values: Mapping[str, MetricValue], role: str) -> Decimal | None:
    return _decimal(values, role) if role in values else None


def _integer(values: Mapping[str, MetricValue], role: str) -> int:
    value = values[role].value
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{role} must be an integer")
    return value


def _boolean(values: Mapping[str, MetricValue], role: str) -> bool:
    value = values[role].value
    if not isinstance(value, bool):
        raise ValueError(f"{role} must be a boolean")
    return value


def _optional_boolean(values: Mapping[str, MetricValue], role: str) -> bool | None:
    return _boolean(values, role) if role in values else None


def _worst_health(values: tuple[MetricHealth, ...]) -> MetricHealth:
    order = {
        MetricHealth.READY: 0,
        MetricHealth.WARMING: 1,
        MetricHealth.DEGRADED: 2,
        MetricHealth.STALE: 3,
        MetricHealth.UNAVAILABLE: 4,
        MetricHealth.UNSUPPORTED: 5,
        MetricHealth.FAILED: 6,
    }
    return max(values, key=order.__getitem__) if values else MetricHealth.WARMING


def _worst_fidelity(values: tuple[MetricFidelity, ...]) -> MetricFidelity:
    order = {
        MetricFidelity.REPORTED: 0,
        MetricFidelity.DERIVED: 1,
        MetricFidelity.INFERRED: 2,
        MetricFidelity.PARTIAL: 3,
        MetricFidelity.UNAVAILABLE: 4,
    }
    return max(values, key=order.__getitem__) if values else MetricFidelity.PARTIAL


def payload_type_for_entity(entity_type: str) -> type[EntityPayload]:
    """Return the payload contract for a supported objective session entity.

    Raises:
        ValueError: If the entity type is unsupported by session projection.
    """

    if entity_type.startswith("objective_level."):
        return ObjectiveLevelPayload
    try:
        return _PAYLOAD_TYPES[entity_type]
    except KeyError as exc:
        raise ValueError(f"unsupported Stage 9D.3 entity type: {entity_type}") from exc
