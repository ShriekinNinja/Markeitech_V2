from __future__ import annotations

from collections.abc import Mapping

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId, CustomData, DataType

from markeitech.intelligence.entities import (
    ENTITY_REVISION_TYPE_NAME,
    ENTITY_SNAPSHOT_REQUEST_TYPE_NAME,
    ENTITY_SNAPSHOT_TYPE_NAME,
    EntityDefinition,
    EntityDurability,
    EntityMetricDependency,
    EntitySnapshotRequest,
    EntitySnapshotResponse,
    EntityStateBookLimits,
)
from markeitech.intelligence.metrics import (
    METRIC_VALUE_TYPE_NAME,
    MetricFidelity,
    MetricHealth,
    MetricValue,
)
from markeitech.intelligence.session_entities import (
    SESSION_ENTITY_GROUP,
    SessionEntityApplication,
    SessionEntityDefinition,
    SessionEntityProjectionOwner,
    payload_type_for_entity,
)
from markeitech.system.messages import (
    PERSISTENCE_READY_REQUEST_SIGNAL,
    PERSISTENCE_READY_SIGNAL,
    PersistenceReadyEvent,
    PersistenceReadyRequest,
)


class SessionReferenceEntityActorConfig(DataActorConfig):
    def __new__(
        cls,
        instrument_profiles: dict[str, dict[str, object]],
        definitions: list[dict[str, object]],
        maximum_entities_global: int,
        maximum_entities_per_instrument: int,
        maximum_entities_per_type: int,
        maximum_metric_values: int,
        minimum_snapshot_interval_ms: int,
        maximum_publications_per_cycle: int,
        schema_version: int,
        actor_id: str | ActorId = "SESSION-REFERENCE-ENTITIES",
    ) -> SessionReferenceEntityActorConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        obj = super().__new__(cls, actor_id=resolved)
        obj.instrument_profiles = dict(instrument_profiles)
        obj.definitions = tuple(dict(item) for item in definitions)
        obj.maximum_entities_global = maximum_entities_global
        obj.maximum_entities_per_instrument = maximum_entities_per_instrument
        obj.maximum_entities_per_type = maximum_entities_per_type
        obj.maximum_metric_values = maximum_metric_values
        obj.minimum_snapshot_interval_ms = minimum_snapshot_interval_ms
        obj.maximum_publications_per_cycle = maximum_publications_per_cycle
        obj.schema_version = schema_version
        return obj


class SessionReferenceEntityActor(DataActor):
    """Publishes objective Group 1 entities from typed metric evidence only."""

    def __init__(self, config: SessionReferenceEntityActorConfig) -> None:
        super().__init__(config)
        definitions = tuple(_definition_from_config(item) for item in config.definitions)
        profiles = {
            instrument_id: (str(raw["profile_id"]), int(raw["profile_version"]))
            for instrument_id, raw in config.instrument_profiles.items()
        }
        self._owner = SessionEntityProjectionOwner(
            definitions=definitions,
            instrument_profiles=profiles,
            limits=EntityStateBookLimits(
                config.maximum_entities_global,
                config.maximum_entities_per_instrument,
                config.maximum_entities_per_type,
            ),
            maximum_metric_values=config.maximum_metric_values,
            maximum_publications_per_cycle=config.maximum_publications_per_cycle,
            source=str(self.actor_id),
            schema_version=config.schema_version,
        )
        self._metric_type = DataType(METRIC_VALUE_TYPE_NAME)
        self._revision_type = DataType(ENTITY_REVISION_TYPE_NAME)
        self._snapshot_request_type = DataType(ENTITY_SNAPSHOT_REQUEST_TYPE_NAME)
        self._snapshot_type = DataType(ENTITY_SNAPSHOT_TYPE_NAME)
        self._minimum_snapshot_interval_ns = config.minimum_snapshot_interval_ms * 1_000_000
        self._last_snapshot_ns: dict[str, int] = {}
        self._persistence_ready = False
        self._snapshot_requests = 0
        self._snapshot_suppressed = 0
        self._snapshot_failures = 0

    def on_start(self) -> None:
        self.subscribe_signal(PERSISTENCE_READY_SIGNAL)
        self.subscribe_data(self._metric_type)
        self.subscribe_data(self._snapshot_request_type)
        self.publish_signal(
            PERSISTENCE_READY_REQUEST_SIGNAL,
            PersistenceReadyRequest(requester=str(self.actor_id)).to_signal_value(),
        )

    def on_signal(self, signal: Signal) -> None:
        if signal.name != PERSISTENCE_READY_SIGNAL:
            return
        try:
            PersistenceReadyEvent.from_signal_value(signal.value)
        except ValueError as exc:
            self.log.error(
                f"SESSION_ENTITY_PERSISTENCE_READY_REJECTED | error={type(exc).__name__}",
            )
            return
        self._persistence_ready = True

    def on_data(self, data) -> None:  # noqa: ANN001
        payload = data.data if isinstance(data, CustomData) else data
        if isinstance(payload, MetricValue):
            self._on_metric(payload)
        elif isinstance(payload, EntitySnapshotRequest):
            self._on_snapshot_request(payload)

    def on_stop(self) -> None:
        self.unsubscribe_signal(PERSISTENCE_READY_SIGNAL)
        self.unsubscribe_data(self._metric_type)
        self.unsubscribe_data(self._snapshot_request_type)
        counts = self._owner.counts
        self.log.info(
            "SESSION_ENTITIES_STOPPED"
            f" | persistence_ready={str(self._persistence_ready).lower()}"
            f" | metrics={counts.metrics_accepted}"
            f" | metric_duplicates={counts.metrics_duplicate}"
            f" | metric_stale={counts.metrics_stale}"
            f" | metric_conflicts={counts.metrics_conflict}"
            f" | revisions={counts.revisions_published}"
            f" | revision_duplicates={counts.revisions_duplicate}"
            f" | revision_rejected={counts.revisions_rejected}"
            f" | retained_metrics={self._owner.retained_metric_values}"
            f" | pending_publications={self._owner.pending_publications}"
            f" | snapshots={self._snapshot_requests}"
            f" | snapshot_suppressed={self._snapshot_suppressed}"
            f" | snapshot_failures={self._snapshot_failures}",
        )

    def _on_metric(self, value: MetricValue) -> None:
        now_ns = self.clock.timestamp_ns()
        try:
            revisions = self._owner.ingest(value, now_ns=now_ns)
        except (ValueError, ArithmeticError) as exc:
            self.log.error(
                "SESSION_ENTITY_PROJECTION_FAILED"
                f" | instrument_id={value.instrument_id}"
                f" | metric_id={value.metric_id} | error={type(exc).__name__}",
            )
            return
        for revision in revisions:
            self.publish_data(
                self._revision_type,
                CustomData(self._revision_type, revision),
            )

    def _on_snapshot_request(self, request: EntitySnapshotRequest) -> None:
        now_ns = self.clock.timestamp_ns()
        previous = self._last_snapshot_ns.get(request.requester)
        if previous is not None and now_ns - previous < self._minimum_snapshot_interval_ns:
            self._snapshot_suppressed += 1
            return
        try:
            snapshot = self._owner.snapshot(
                now_ns,
                instrument_id=request.instrument_id,
                entity_type=request.entity_type,
                analytical_profile_id=request.analytical_profile_id,
                analytical_profile_version=request.analytical_profile_version,
                lifecycles=request.lifecycles,
            )
            response = EntitySnapshotResponse(request.request_id, request.requester, snapshot)
        except ValueError as exc:
            self._snapshot_failures += 1
            self.log.error(f"SESSION_ENTITY_SNAPSHOT_FAILED | error={type(exc).__name__}")
            return
        self.publish_data(self._snapshot_type, CustomData(self._snapshot_type, response))
        self._last_snapshot_ns[request.requester] = now_ns
        self._snapshot_requests += 1


def _definition_from_config(raw: Mapping[str, object]) -> SessionEntityDefinition:
    if raw.get("group") != SESSION_ENTITY_GROUP:
        raise ValueError("session entity actor accepts Group 1 definitions only")
    metric_inputs = tuple(
        EntityMetricDependency(
            str(item["metric_id"]),
            int(item["metric_version"]),
            bool(item["required"]),
            tuple(MetricHealth(str(value)) for value in item["permitted_health"]),
            tuple(MetricFidelity(str(value)) for value in item["permitted_fidelities"]),
        )
        for item in raw["metric_inputs"]
    )
    if raw.get("entity_inputs"):
        raise ValueError("Stage 9D.3 Group 1 definitions cannot consume entities")
    definition = EntityDefinition(
        entity_type=str(raw["entity_type"]),
        version=int(raw["entity_version"]),
        decision_question=str(raw["decision_question"]),
        implementation_id=str(raw["implementation_id"]),
        payload_type=payload_type_for_entity(str(raw["entity_type"])),
        identity_dimensions=tuple(str(value) for value in raw["identity_dimensions"]),
        metric_inputs=metric_inputs,
        entity_inputs=(),
        permitted_health=tuple(MetricHealth(str(value)) for value in raw["permitted_health"]),
        permitted_fidelities=tuple(
            MetricFidelity(str(value)) for value in raw["permitted_fidelities"]
        ),
        durability=EntityDurability(str(raw["durability"])),
        completion_rule=str(raw["completion_rule"]),
        invalidation_rule=str(raw["invalidation_rule"]),
        expiry_rule=str(raw["expiry_rule"]),
    )
    applications = tuple(
        SessionEntityApplication(
            str(item["application_id"]),
            tuple(str(value) for value in item["analytical_profile_ids"]),
            tuple(str(value) for value in item["instrument_ids"]),
            tuple(str(value) for value in item["session_phases"]),
            str(item["horizon"]),
        )
        for item in raw["applications"]
    )
    roles = {
        (str(item["metric_id"]), int(item["metric_version"])): str(item["role"])
        for item in raw["metric_inputs"]
    }
    parameter_versions = {int(item["parameter_version"]) for item in raw["metric_inputs"]}
    if len(parameter_versions) != 1:
        raise ValueError("Stage 9D.3 metric inputs require one parameter version")
    return SessionEntityDefinition(
        definition_id=str(raw["definition_id"]),
        definition=definition,
        metric_roles=roles,
        parameter_version=parameter_versions.pop(),
        applications=applications,
    )
