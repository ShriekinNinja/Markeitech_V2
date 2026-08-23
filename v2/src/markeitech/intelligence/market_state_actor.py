from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

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
from markeitech.intelligence.market_state_entities import (
    MARKET_STATE_GROUPS,
    MarketStateApplication,
    MarketStateDefinition,
    MarketStatePolicyBinding,
    MarketStateProjectionOwner,
    payload_type_for_market_state,
)
from markeitech.intelligence.market_states import (
    StateCategoryBand,
    StateClassificationPolicy,
)
from markeitech.intelligence.metrics import (
    METRIC_VALUE_TYPE_NAME,
    MetricFidelity,
    MetricHealth,
    MetricValue,
)
from markeitech.system.messages import (
    PERSISTENCE_READY_REQUEST_SIGNAL,
    PERSISTENCE_READY_SIGNAL,
    PersistenceReadyEvent,
    PersistenceReadyRequest,
)

_RECONCILIATION_TIMER = "market-state-reconciliation"


class MarketStateEntityActorConfig(DataActorConfig):
    def __new__(
        cls,
        instrument_profiles: dict[str, dict[str, object]],
        definitions: list[dict[str, object]],
        maximum_entities_global: int,
        maximum_entities_per_instrument: int,
        maximum_entities_per_type: int,
        maximum_metric_values: int,
        reconciliation_interval_ms: int,
        minimum_snapshot_interval_ms: int,
        maximum_publications_per_cycle: int,
        schema_version: int,
        actor_id: str | ActorId = "MARKET-STATE-ENTITIES",
    ) -> MarketStateEntityActorConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        obj = super().__new__(cls, actor_id=resolved)
        obj.instrument_profiles = dict(instrument_profiles)
        obj.definitions = tuple(dict(item) for item in definitions)
        obj.maximum_entities_global = maximum_entities_global
        obj.maximum_entities_per_instrument = maximum_entities_per_instrument
        obj.maximum_entities_per_type = maximum_entities_per_type
        obj.maximum_metric_values = maximum_metric_values
        obj.reconciliation_interval_ms = reconciliation_interval_ms
        obj.minimum_snapshot_interval_ms = minimum_snapshot_interval_ms
        obj.maximum_publications_per_cycle = maximum_publications_per_cycle
        obj.schema_version = schema_version
        return obj


class MarketStateEntityActor(DataActor):
    """Publishes configured metric-driven market state without deriving source metrics."""

    def __init__(self, config: MarketStateEntityActorConfig) -> None:
        super().__init__(config)
        definitions = tuple(_definition_from_config(item) for item in config.definitions)
        profiles = {
            instrument_id: (str(raw["profile_id"]), int(raw["profile_version"]))
            for instrument_id, raw in config.instrument_profiles.items()
        }
        self._definition_count = len(definitions)
        self._owner = MarketStateProjectionOwner(
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
        self._reconciliation_interval_ns = config.reconciliation_interval_ms * 1_000_000
        self._minimum_snapshot_interval_ns = config.minimum_snapshot_interval_ms * 1_000_000
        self._last_snapshot_ns: dict[str, int] = {}
        self._persistence_ready = False
        self._reconciliation_cycles = 0
        self._snapshot_requests = 0
        self._snapshot_suppressed = 0
        self._snapshot_failures = 0
        self._projection_failures = 0

    def on_start(self) -> None:
        self.subscribe_signal(PERSISTENCE_READY_SIGNAL)
        self.subscribe_data(self._metric_type)
        self.subscribe_data(self._snapshot_request_type)
        self.clock.set_timer_ns(
            _RECONCILIATION_TIMER,
            self._reconciliation_interval_ns,
            callback=self._reconcile,
        )
        self.publish_signal(
            PERSISTENCE_READY_REQUEST_SIGNAL,
            PersistenceReadyRequest(requester=str(self.actor_id)).to_signal_value(),
        )
        self.log.info(
            "MARKET_STATE_ENTITIES_STARTED"
            f" | definitions={self._definition_count}"
            f" | reconciliation_interval_ms={self._reconciliation_interval_ns // 1_000_000}",
        )

    def on_signal(self, signal: Signal) -> None:
        if signal.name != PERSISTENCE_READY_SIGNAL:
            return
        try:
            PersistenceReadyEvent.from_signal_value(signal.value)
        except ValueError as exc:
            self.log.error(
                f"MARKET_STATE_PERSISTENCE_READY_REJECTED | error={type(exc).__name__}",
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
        if _RECONCILIATION_TIMER in self.clock.timer_names():
            self.clock.cancel_timer(_RECONCILIATION_TIMER)
        self.unsubscribe_signal(PERSISTENCE_READY_SIGNAL)
        self.unsubscribe_data(self._metric_type)
        self.unsubscribe_data(self._snapshot_request_type)
        counts = self._owner.counts
        self.log.info(
            "MARKET_STATE_ENTITIES_STOPPED"
            f" | persistence_ready={str(self._persistence_ready).lower()}"
            f" | metrics={counts.metrics_accepted}"
            f" | metric_duplicates={counts.metrics_duplicate}"
            f" | metric_stale={counts.metrics_stale}"
            f" | metric_conflicts={counts.metrics_conflict}"
            f" | revisions={counts.revisions_published}"
            f" | revision_duplicates={counts.revisions_duplicate}"
            f" | revision_rejected={counts.revisions_rejected}"
            f" | publications_deferred={counts.publications_deferred}"
            f" | staleness_revisions={counts.staleness_reconciliations}"
            f" | retained_metrics={self._owner.retained_metric_values}"
            f" | pending_publications={self._owner.pending_publications}"
            f" | reconciliation_cycles={self._reconciliation_cycles}"
            f" | projection_failures={self._projection_failures}"
            f" | snapshots={self._snapshot_requests}"
            f" | snapshot_suppressed={self._snapshot_suppressed}"
            f" | snapshot_failures={self._snapshot_failures}",
        )

    def _on_metric(self, value: MetricValue) -> None:
        try:
            revisions = self._owner.ingest(value, now_ns=self.clock.timestamp_ns())
        except (ValueError, ArithmeticError) as exc:
            self._projection_failures += 1
            self.log.error(
                "MARKET_STATE_PROJECTION_FAILED"
                f" | instrument_id={value.instrument_id}"
                f" | metric_id={value.metric_id} | error={type(exc).__name__}",
            )
            return
        self._publish(revisions)

    def _reconcile(self, _event) -> None:  # noqa: ANN001
        self._reconciliation_cycles += 1
        try:
            revisions = self._owner.reconcile(now_ns=self.clock.timestamp_ns())
        except (ValueError, ArithmeticError) as exc:
            self._projection_failures += 1
            self.log.error(f"MARKET_STATE_RECONCILIATION_FAILED | error={type(exc).__name__}")
            return
        self._publish(revisions)

    def _publish(self, revisions) -> None:  # noqa: ANN001
        for revision in revisions:
            self.publish_data(self._revision_type, CustomData(self._revision_type, revision))

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
            self.log.error(f"MARKET_STATE_SNAPSHOT_FAILED | error={type(exc).__name__}")
            return
        self.publish_data(self._snapshot_type, CustomData(self._snapshot_type, response))
        self._last_snapshot_ns[request.requester] = now_ns
        self._snapshot_requests += 1


def _definition_from_config(raw: Mapping[str, object]) -> MarketStateDefinition:
    group = str(raw.get("group"))
    if group not in MARKET_STATE_GROUPS:
        raise ValueError("market-state actor accepts Group 2 and Group 3 definitions only")
    state = _mapping(raw.get("market_state"), "market_state")
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
        raise ValueError("metric-driven market-state definitions cannot consume entities")
    entity_type = str(raw["entity_type"])
    definition = EntityDefinition(
        entity_type=entity_type,
        version=int(raw["entity_version"]),
        decision_question=str(raw["decision_question"]),
        implementation_id=str(raw["implementation_id"]),
        payload_type=payload_type_for_market_state(entity_type),
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
    roles = {
        (str(item["metric_id"]), int(item["metric_version"])): str(item["role"])
        for item in raw["metric_inputs"]
    }
    parameter_set_id = str(state["parameter_set_id"])
    selected = next(
        (
            _mapping(item, "parameter_set")
            for item in raw["parameter_sets"]
            if str(item["parameter_set_id"]) == parameter_set_id
        ),
        None,
    )
    if selected is None:
        raise ValueError(f"market-state parameter set is unavailable: {parameter_set_id}")
    configured_values = _mapping(selected["values"], "parameter_set.values")
    parameter_version = int(selected["parameter_version"])
    applications = tuple(
        MarketStateApplication(
            str(item["application_id"]),
            tuple(str(value) for value in item["analytical_profile_ids"]),
            tuple(str(value) for value in item["instrument_ids"]),
            tuple(str(value) for value in item["session_phases"]),
            str(item["horizon"]),
        )
        for item in raw["applications"]
    )
    role_to_metric = {role: key[0] for key, role in roles.items()}
    bindings = tuple(
        _policy_binding(
            _mapping(item, "market_state.policy"),
            role_to_metric=role_to_metric,
            configured_values=configured_values,
            parameter_version=parameter_version,
            parameter_source=str(selected["source"]),
            parameter_effective_from_ns=int(selected["effective_from_ns"]),
        )
        for item in state["policies"]
    )
    return MarketStateDefinition(
        definition_id=str(raw["definition_id"]),
        group=group,
        definition=definition,
        metric_roles=roles,
        parameter_set_id=parameter_set_id,
        parameter_version=parameter_version,
        policy_bindings=bindings,
        applications=applications,
        normalization=_optional_text(state.get("normalization")),
        reference_id=_optional_text(state.get("reference_id")),
        reference_kind=_optional_text(state.get("reference_kind")),
    )


def _policy_binding(
    raw: Mapping[str, object],
    *,
    role_to_metric: Mapping[str, str],
    configured_values: Mapping[str, object],
    parameter_version: int,
    parameter_source: str,
    parameter_effective_from_ns: int,
) -> MarketStatePolicyBinding:
    measure_role = str(raw["measure_role"])
    policy = StateClassificationPolicy(
        definition_id=str(raw["policy_id"]),
        definition_version=int(raw["policy_version"]),
        parameter_version=parameter_version,
        parameter_source=parameter_source,
        parameter_effective_from_ns=parameter_effective_from_ns,
        measure_id=role_to_metric[measure_role],
        unavailable_category=str(raw["unavailable_category"]),
        bands=tuple(
            StateCategoryBand(
                str(item["category"]),
                _optional_parameter_decimal(
                    item.get("lower_bound_parameter_id"),
                    configured_values,
                ),
                _optional_parameter_decimal(
                    item.get("upper_bound_parameter_id"),
                    configured_values,
                ),
            )
            for item in raw["bands"]
        ),
        hysteresis=_parameter_decimal(raw["hysteresis_parameter_id"], configured_values),
        confirmation_observations=_parameter_int(
            raw["confirmation_observations_parameter_id"],
            configured_values,
        ),
        minimum_coverage_ratio=_parameter_decimal(
            raw["minimum_coverage_ratio_parameter_id"],
            configured_values,
        ),
        maximum_evidence_age_ns=(
            _parameter_int(raw["maximum_evidence_age_ms_parameter_id"], configured_values)
            * 1_000_000
        ),
        permitted_health=tuple(MetricHealth(str(value)) for value in raw["permitted_health"]),
        permitted_fidelities=tuple(
            MetricFidelity(str(value)) for value in raw["permitted_fidelities"]
        ),
    )
    return MarketStatePolicyBinding(
        axis=str(raw["axis"]),
        measure_role=measure_role,
        coverage_role=str(raw["coverage_role"]),
        policy=policy,
    )


def _parameter_decimal(parameter_id: object, values: Mapping[str, object]) -> Decimal:
    key = str(parameter_id)
    value = values[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"market-state parameter must be numeric: {key}")
    return Decimal(str(value))


def _optional_parameter_decimal(
    parameter_id: object | None,
    values: Mapping[str, object],
) -> Decimal | None:
    return None if parameter_id is None else _parameter_decimal(parameter_id, values)


def _parameter_int(parameter_id: object, values: Mapping[str, object]) -> int:
    key = str(parameter_id)
    value = values[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"market-state parameter must be an integer: {key}")
    return value


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _optional_text(value: object | None) -> str | None:
    if value is None:
        return None
    resolved = str(value).strip()
    return resolved or None
