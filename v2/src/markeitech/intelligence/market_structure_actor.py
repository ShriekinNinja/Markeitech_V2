from __future__ import annotations

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId, CustomData, DataType

from markeitech.intelligence.completed_bars import (
    COMPLETED_BAR_INPUT_TYPE_NAME,
    CompletedBarInput,
)
from markeitech.intelligence.entities import (
    ENTITY_REVISION_TYPE_NAME,
    ENTITY_SNAPSHOT_REQUEST_TYPE_NAME,
    ENTITY_SNAPSHOT_TYPE_NAME,
    EntityRevision,
    EntitySnapshot,
    EntitySnapshotRequest,
    EntitySnapshotResponse,
    EntityStateBookLimits,
)
from markeitech.intelligence.fvg_entities import (
    FVG_ENTITY_TYPE,
    FvgEntityProjectionOwner,
)
from markeitech.intelligence.market_structure_entities import (
    CONFIRMED_SWING_ENTITY_TYPE,
    ConfirmedSwingProjectionOwner,
)
from markeitech.intelligence.market_structure_relationships import (
    MarketStructureRelationshipOwner,
)
from markeitech.intelligence.market_structure_runtime import (
    resolve_market_structure_definitions,
)
from markeitech.intelligence.zone_entities import DerivedZoneProjectionOwner
from markeitech.system.messages import (
    PERSISTENCE_READY_REQUEST_SIGNAL,
    PERSISTENCE_READY_SIGNAL,
    PersistenceReadyEvent,
    PersistenceReadyRequest,
)


class MarketStructureEntityActorConfig(DataActorConfig):
    def __new__(
        cls,
        instrument_profiles: dict[str, dict[str, object]],
        definitions: list[dict[str, object]],
        maximum_entities_global: int,
        maximum_entities_per_instrument: int,
        maximum_entities_per_type: int,
        minimum_snapshot_interval_ms: int,
        maximum_publications_per_cycle: int,
        schema_version: int,
        actor_id: str | ActorId = "MARKET-STRUCTURE-ENTITIES",
    ) -> MarketStructureEntityActorConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        obj = super().__new__(cls, actor_id=resolved)
        obj.instrument_profiles = dict(instrument_profiles)
        obj.definitions = tuple(dict(item) for item in definitions)
        obj.maximum_entities_global = maximum_entities_global
        obj.maximum_entities_per_instrument = maximum_entities_per_instrument
        obj.maximum_entities_per_type = maximum_entities_per_type
        obj.minimum_snapshot_interval_ms = minimum_snapshot_interval_ms
        obj.maximum_publications_per_cycle = maximum_publications_per_cycle
        obj.schema_version = schema_version
        return obj


class MarketStructureEntityActor(DataActor):
    """Coordinates reviewed market-structure owners without deriving new semantics."""

    def __init__(self, config: MarketStructureEntityActorConfig) -> None:
        super().__init__(config)
        profiles = {
            instrument_id: (str(raw["profile_id"]), int(raw["profile_version"]))
            for instrument_id, raw in config.instrument_profiles.items()
        }
        resolved = resolve_market_structure_definitions(
            config.definitions,
            eligible_instrument_ids=tuple(sorted(profiles)),
        )
        limits = EntityStateBookLimits(
            config.maximum_entities_global,
            config.maximum_entities_per_instrument,
            config.maximum_entities_per_type,
        )
        owner_args = {
            "limits": limits,
            "maximum_publications_per_cycle": config.maximum_publications_per_cycle,
            "source": str(self.actor_id),
            "schema_version": config.schema_version,
        }
        self._swings = (
            ConfirmedSwingProjectionOwner(
                definitions=resolved.confirmed_swings,
                **owner_args,
            )
            if resolved.confirmed_swings
            else None
        )
        self._relationships = (
            MarketStructureRelationshipOwner(
                definitions=resolved.relationships,
                **owner_args,
            )
            if resolved.relationships
            else None
        )
        self._fvgs = (
            FvgEntityProjectionOwner(definitions=resolved.fvgs, **owner_args)
            if resolved.fvgs
            else None
        )
        self._zones = (
            DerivedZoneProjectionOwner(definitions=resolved.zones, **owner_args)
            if resolved.zones
            else None
        )
        self._definition_count = resolved.definition_count
        self._completed_bar_type = DataType(COMPLETED_BAR_INPUT_TYPE_NAME)
        self._revision_type = DataType(ENTITY_REVISION_TYPE_NAME)
        self._snapshot_request_type = DataType(ENTITY_SNAPSHOT_REQUEST_TYPE_NAME)
        self._snapshot_type = DataType(ENTITY_SNAPSHOT_TYPE_NAME)
        self._minimum_snapshot_interval_ns = config.minimum_snapshot_interval_ms * 1_000_000
        self._last_snapshot_ns: dict[str, int] = {}
        self._persistence_ready = False
        self._bars_received = 0
        self._external_revisions = 0
        self._revisions_published = 0
        self._swing_failures = 0
        self._relationship_failures = 0
        self._fvg_failures = 0
        self._zone_failures = 0
        self._snapshot_requests = 0
        self._snapshot_suppressed = 0
        self._snapshot_failures = 0

    def on_start(self) -> None:
        self.subscribe_signal(PERSISTENCE_READY_SIGNAL)
        self.subscribe_data(self._completed_bar_type)
        self.subscribe_data(self._revision_type)
        self.subscribe_data(self._snapshot_request_type)
        self.publish_signal(
            PERSISTENCE_READY_REQUEST_SIGNAL,
            PersistenceReadyRequest(requester=str(self.actor_id)).to_signal_value(),
        )
        self.log.info(
            "MARKET_STRUCTURE_ENTITIES_STARTED"
            f" | definitions={self._definition_count}"
            f" | swings={str(self._swings is not None).lower()}"
            f" | relationships={str(self._relationships is not None).lower()}"
            f" | fvgs={str(self._fvgs is not None).lower()}"
            f" | zones={str(self._zones is not None).lower()}",
        )

    def on_signal(self, signal: Signal) -> None:
        if signal.name != PERSISTENCE_READY_SIGNAL:
            return
        try:
            PersistenceReadyEvent.from_signal_value(signal.value)
        except ValueError as exc:
            self.log.error(
                f"MARKET_STRUCTURE_PERSISTENCE_READY_REJECTED | error={type(exc).__name__}",
            )
            return
        self._persistence_ready = True

    def on_data(self, data) -> None:  # noqa: ANN001
        payload = data.data if isinstance(data, CustomData) else data
        if isinstance(payload, CompletedBarInput):
            self._on_completed_bar(payload)
        elif isinstance(payload, EntityRevision):
            self._on_external_revision(payload)
        elif isinstance(payload, EntitySnapshotRequest):
            self._on_snapshot_request(payload)

    def on_stop(self) -> None:
        self.unsubscribe_signal(PERSISTENCE_READY_SIGNAL)
        self.unsubscribe_data(self._completed_bar_type)
        self.unsubscribe_data(self._revision_type)
        self.unsubscribe_data(self._snapshot_request_type)
        retained = self._retained_counts()
        pending = self._pending_publications()
        self.log.info(
            "MARKET_STRUCTURE_ENTITIES_STOPPED"
            f" | persistence_ready={str(self._persistence_ready).lower()}"
            f" | bars={self._bars_received}"
            f" | external_revisions={self._external_revisions}"
            f" | revisions={self._revisions_published}"
            f" | swing_failures={self._swing_failures}"
            f" | relationship_failures={self._relationship_failures}"
            f" | fvg_failures={self._fvg_failures}"
            f" | zone_failures={self._zone_failures}"
            f" | retained_swings={retained['swings']}"
            f" | retained_relationships={retained['relationships']}"
            f" | retained_fvgs={retained['fvgs']}"
            f" | retained_zones={retained['zones']}"
            f" | pending_publications={pending}"
            f" | snapshots={self._snapshot_requests}"
            f" | snapshot_suppressed={self._snapshot_suppressed}"
            f" | snapshot_failures={self._snapshot_failures}",
        )

    def _on_completed_bar(self, bar: CompletedBarInput) -> None:
        self._bars_received += 1
        now_ns = self.clock.timestamp_ns()
        if self._relationships is not None:
            try:
                self._publish(self._relationships.ingest_bar(bar, now_ns=now_ns))
            except (ValueError, TypeError, ArithmeticError, RuntimeError) as exc:
                self._relationship_failures += 1
                self._log_projection_failure("relationship_bar", bar.instrument_id, exc)
        if self._swings is not None:
            try:
                self._publish_with_fanout(self._swings.ingest(bar, now_ns=now_ns), now_ns)
            except (ValueError, TypeError, ArithmeticError, RuntimeError) as exc:
                self._swing_failures += 1
                self._log_projection_failure("confirmed_swing", bar.instrument_id, exc)
        if self._fvgs is not None:
            try:
                self._publish_with_fanout(self._fvgs.ingest_bar(bar, now_ns=now_ns), now_ns)
            except (ValueError, TypeError, ArithmeticError, RuntimeError) as exc:
                self._fvg_failures += 1
                self._log_projection_failure("fair_value_gap", bar.instrument_id, exc)

    def _on_external_revision(self, revision: EntityRevision) -> None:
        if revision.source == str(self.actor_id):
            return
        self._external_revisions += 1
        now_ns = self.clock.timestamp_ns()
        derived: list[EntityRevision] = []
        if (
            self._relationships is not None
            and revision.identity.entity_type == CONFIRMED_SWING_ENTITY_TYPE
        ):
            try:
                derived.extend(self._relationships.ingest_swing(revision, now_ns=now_ns))
            except (ValueError, TypeError, ArithmeticError, RuntimeError) as exc:
                self._relationship_failures += 1
                self._log_projection_failure(
                    "relationship_swing",
                    revision.identity.instrument_id,
                    exc,
                )
        if self._zones is not None:
            try:
                derived.extend(self._zones.ingest(revision, now_ns=now_ns))
            except (ValueError, TypeError, ArithmeticError, RuntimeError) as exc:
                self._zone_failures += 1
                self._log_projection_failure("derived_zone", revision.identity.instrument_id, exc)
        self._publish(tuple(derived))

    def _publish_with_fanout(
        self,
        revisions: tuple[EntityRevision, ...],
        now_ns: int,
    ) -> None:
        pending = list(revisions)
        published: list[EntityRevision] = []
        while pending:
            revision = pending.pop(0)
            published.append(revision)
            if (
                self._relationships is not None
                and revision.identity.entity_type == CONFIRMED_SWING_ENTITY_TYPE
            ):
                try:
                    pending.extend(self._relationships.ingest_swing(revision, now_ns=now_ns))
                except (ValueError, TypeError, ArithmeticError, RuntimeError) as exc:
                    self._relationship_failures += 1
                    self._log_projection_failure(
                        "relationship_swing",
                        revision.identity.instrument_id,
                        exc,
                    )
            if self._zones is not None and revision.identity.entity_type in {
                CONFIRMED_SWING_ENTITY_TYPE,
                FVG_ENTITY_TYPE,
            }:
                try:
                    pending.extend(self._zones.ingest(revision, now_ns=now_ns))
                except (ValueError, TypeError, ArithmeticError, RuntimeError) as exc:
                    self._zone_failures += 1
                    self._log_projection_failure(
                        "derived_zone",
                        revision.identity.instrument_id,
                        exc,
                    )
        self._publish(tuple(published))

    def _publish(self, revisions: tuple[EntityRevision, ...]) -> None:
        for revision in revisions:
            self.publish_data(self._revision_type, CustomData(self._revision_type, revision))
            self._revisions_published += 1
            self.log.info(
                "MARKET_STRUCTURE_REVISION"
                f" | instrument_id={revision.identity.instrument_id}"
                f" | entity_type={revision.identity.entity_type}"
                f" | lifecycle={revision.lifecycle}"
                f" | revision={revision.revision}"
                f" | entity_id={revision.entity_id}",
            )

    def _on_snapshot_request(self, request: EntitySnapshotRequest) -> None:
        now_ns = self.clock.timestamp_ns()
        previous = self._last_snapshot_ns.get(request.requester)
        if previous is not None and now_ns - previous < self._minimum_snapshot_interval_ns:
            self._snapshot_suppressed += 1
            return
        try:
            revisions = self._snapshot_revisions(now_ns, request)
            response = EntitySnapshotResponse(
                request.request_id,
                request.requester,
                EntitySnapshot(now_ns, revisions),
            )
        except ValueError as exc:
            self._snapshot_failures += 1
            self.log.error(f"MARKET_STRUCTURE_SNAPSHOT_FAILED | error={type(exc).__name__}")
            return
        self.publish_data(self._snapshot_type, CustomData(self._snapshot_type, response))
        self._last_snapshot_ns[request.requester] = now_ns
        self._snapshot_requests += 1

    def _snapshot_revisions(
        self,
        now_ns: int,
        request: EntitySnapshotRequest,
    ) -> tuple[EntityRevision, ...]:
        snapshots = []
        if self._swings is not None:
            snapshots.append(self._swings.snapshot(now_ns, instrument_id=request.instrument_id))
        if self._relationships is not None:
            entity_type = request.entity_type
            if entity_type in {None, "swing_leg", "pivot_structure_state"}:
                snapshots.append(
                    self._relationships.snapshot(
                        now_ns,
                        instrument_id=request.instrument_id,
                        entity_type=entity_type,
                    ),
                )
        if self._fvgs is not None:
            snapshots.append(self._fvgs.snapshot(now_ns, instrument_id=request.instrument_id))
        if self._zones is not None:
            snapshots.append(self._zones.snapshot(now_ns, instrument_id=request.instrument_id))
        revisions = {
            revision.entity_id: revision
            for snapshot in snapshots
            for revision in snapshot.revisions
            if _matches_request(revision, request)
        }
        return tuple(revisions[key] for key in sorted(revisions))

    def _retained_counts(self) -> dict[str, int]:
        return {
            "swings": 0 if self._swings is None else self._swings.retained_entities,
            "relationships": (
                0 if self._relationships is None else self._relationships.retained_entities
            ),
            "fvgs": 0 if self._fvgs is None else self._fvgs.retained_entities,
            "zones": 0 if self._zones is None else self._zones.retained_entities,
        }

    def _pending_publications(self) -> int:
        owners = (self._swings, self._relationships, self._fvgs, self._zones)
        return sum(
            int(getattr(owner, "pending_publications", 0)) for owner in owners if owner is not None
        )

    def _log_projection_failure(self, family: str, instrument_id: str, exc: Exception) -> None:
        self.log.error(
            "MARKET_STRUCTURE_PROJECTION_FAILED"
            f" | family={family} | instrument_id={instrument_id}"
            f" | error={type(exc).__name__} | reason={exc}",
        )


def _matches_request(revision: EntityRevision, request: EntitySnapshotRequest) -> bool:
    if request.entity_type is not None and revision.identity.entity_type != request.entity_type:
        return False
    if (
        request.analytical_profile_id is not None
        and revision.identity.analytical_profile_id != request.analytical_profile_id
    ):
        return False
    if (
        request.analytical_profile_version is not None
        and revision.identity.analytical_profile_version != request.analytical_profile_version
    ):
        return False
    return request.lifecycles is None or revision.lifecycle in request.lifecycles
