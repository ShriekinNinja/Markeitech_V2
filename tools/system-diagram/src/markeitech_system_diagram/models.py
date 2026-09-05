from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from .diagnostics import ManifestError

_STABLE_ID = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
_OWNER_SENTINELS = frozenset({"none_current", "not_applicable", "unknown"})


def validate_stable_id(value: str, location: str) -> str:
    if not _STABLE_ID.fullmatch(value):
        raise ManifestError(
            "MANIFEST_INVALID_ID",
            location,
            "expected a lowercase stable ID containing only letters, numbers, '.', '_' or '-'",
        )
    return value


def is_owner_sentinel(value: str) -> bool:
    return value in _OWNER_SENTINELS


class ReviewStatus(StrEnum):
    DRAFT = "draft"
    PROPOSED = "proposed"
    APPROVED = "approved"
    SUPERSEDED = "superseded"


class EvidenceClass(StrEnum):
    TRACKED_AUTHORITY = "tracked_authority"
    SOURCE = "source"
    CONFIGURATION = "configuration"
    TEST = "test"
    INSTALLED_CONTRACT = "installed_contract"
    PROVIDER_DOCUMENTATION = "provider_documentation"
    MEASURED_BOUNDED = "measured_bounded"
    HISTORICAL = "historical"


class BoundaryKind(StrEnum):
    PROCESS = "process"
    NAUTILUS_ENGINE = "nautilus_engine"
    ACTOR_RUNTIME = "actor_runtime"
    WORKER = "worker"
    QUEUE = "queue"
    PROVIDER = "provider"
    PERSISTENCE = "persistence"
    FILESYSTEM = "filesystem"
    OPERATOR = "operator"
    PROJECTION = "projection"
    FUTURE_GOVERNED = "future_governed"


class ComponentKind(StrEnum):
    FRAMEWORK = "framework"
    ENGINE = "engine"
    MARKEITECH_ACTOR = "markeitech_actor"
    WORKER = "worker"
    QUEUE = "queue"
    PROVIDER = "provider"
    DATA_STORE = "data_store"
    PROJECTION = "projection"
    OPERATOR = "operator"
    FUTURE_COMPONENT = "future_component"
    DIAGNOSTIC = "diagnostic"


class ImplementationState(StrEnum):
    IMPLEMENTED = "implemented"
    REMOVED = "removed"
    REJECTED = "rejected"
    FUTURE = "future"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class CompositionPolicy(StrEnum):
    ALWAYS = "always"
    CONDITIONAL = "conditional"
    NOT_COMPOSED = "not_composed"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class EnablementState(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class AcceptanceState(StrEnum):
    ACCEPTED = "accepted"
    BOUNDED_EVIDENCE = "bounded_evidence"
    UNACCEPTED = "unaccepted"
    REJECTED = "rejected"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class TemporalStatus(StrEnum):
    CURRENT = "current"
    HISTORICAL = "historical"
    FUTURE = "future"
    UNKNOWN = "unknown"


class EvidenceCertainty(StrEnum):
    VERIFIED_SOURCE = "verified_source"
    MEASURED_BOUNDED = "measured_bounded"
    INFERENCE = "inference"
    HYPOTHESIS = "hypothesis"
    RECOMMENDATION = "recommendation"
    UNKNOWN = "unknown"


class TransportKind(StrEnum):
    METHOD_CALL = "method_call"
    NAUTILUS_SIGNAL = "nautilus_signal"
    NAUTILUS_CUSTOM_DATA = "nautilus_custom_data"
    NAUTILUS_NATIVE_DATA = "nautilus_native_data"
    NAUTILUS_CALLBACK = "nautilus_callback"
    THREAD_QUEUE = "thread_queue"
    TIMER = "timer"
    POSTGRES_WRITE = "postgres_write"
    EXTERNAL_HTTP = "external_http"
    FILESYSTEM = "filesystem"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class EdgeCategory(StrEnum):
    COMMAND = "command"
    QUERY = "query"
    RESPONSE = "response"
    EVENT = "event"
    PUBLICATION = "publication"
    SUBSCRIPTION_COMMAND = "subscription_command"
    NATIVE_OBSERVATION = "native_observation"
    CALLBACK = "callback"
    READINESS = "readiness"
    RELEASE = "release"
    CONTROL = "control"
    PERSISTENCE = "persistence"
    NOTIFICATION = "notification"
    PROJECTION = "projection"
    TIMER = "timer"
    QUEUE_ADMISSION = "queue_admission"
    WORKER_RESULT = "worker_result"
    FAILURE = "failure"


class SyncSemantics(StrEnum):
    VERIFIED_SYNC = "verified_sync"
    VERIFIED_ASYNC = "verified_async"
    MIXED = "mixed"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class DeliveryGuarantee(StrEnum):
    UNKNOWN = "unknown"
    AT_MOST_ONCE_ATTEMPT = "at_most_once_attempt"
    AT_LEAST_ONCE_ATTEMPT = "at_least_once_attempt"
    LOCAL_IDEMPOTENT_ADMISSION = "local_idempotent_admission"
    NOT_APPLICABLE = "not_applicable"


class DiagramDirection(StrEnum):
    LEFT_TO_RIGHT = "left_to_right"
    TOP_TO_BOTTOM = "top_to_bottom"
    RIGHT_TO_LEFT = "right_to_left"
    BOTTOM_TO_TOP = "bottom_to_top"


class LayoutEngine(StrEnum):
    DOT = "dot"


class RoutingStyle(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    SPLINE = "spline"
    POLYLINE = "polyline"
    ORTHO = "ortho"


class OutputFormat(StrEnum):
    SVG = "svg"
    PNG = "png"
    DOT = "dot"
    MARKDOWN = "md"


class ViewKind(StrEnum):
    CURRENT_RUNTIME = "current_runtime"
    COMPLETE_INVENTORY = "complete_inventory"
    PROVIDER_TO_CANONICAL_DATA = "provider_to_canonical_data"
    METRICS_ENTITIES_INTELLIGENCE = "metrics_entities_intelligence"
    PERSISTENCE_AUDIT_PROJECTIONS = "persistence_audit_projections"


@dataclass(frozen=True, slots=True)
class ManifestHeader:
    schema_version: int
    id: str
    title: str
    description: str
    scope: str
    authority: str
    not_runtime_configuration: bool
    checkout_commit: str
    owner: str
    review_status: ReviewStatus
    architecture_effective_at: str
    generator_contract_version: int
    default_profile: str
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    id: str
    evidence_class: EvidenceClass
    source_path: str
    source_symbol: str | None
    observed_at: str
    proves: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Profile:
    id: str
    config_path: str
    config_schema_version: int
    content_sha256: str | None
    status: str
    limitations: tuple[str, ...]
    evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Boundary:
    id: str
    label: str
    kind: BoundaryKind
    parent: str | None
    temporal_status: TemporalStatus
    evidence: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProfileState:
    profile: str
    enablement: EnablementState


@dataclass(frozen=True, slots=True)
class Component:
    id: str
    label: str
    kind: ComponentKind
    logical_area: str
    boundary: str
    implementation_ref: str | None
    composition_key: str | None
    composition_order: int | None
    actor_id: str | None
    responsibilities: tuple[str, ...]
    semantic_owner: str
    mutation_owner: str
    transport_owner: str
    persistence_owner: str
    recovery_owner: str
    projection_owner: str
    policy_owner: str
    implementation_state: ImplementationState
    composition_policy: CompositionPolicy
    temporal_status: TemporalStatus
    acceptance_state: AcceptanceState
    evidence_certainty: EvidenceCertainty
    configuration_path: str | None
    failure_isolation: str
    cardinality: str
    style: str
    profile_states: tuple[ProfileState, ...]
    evidence: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Capability:
    id: str
    component: str
    label: str
    implementation_state: ImplementationState
    composition_policy: CompositionPolicy
    configuration_path: str | None
    profile: str
    enablement: EnablementState
    evidence: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Contract:
    id: str
    label: str
    transport_kind: TransportKind
    type_name: str
    python_symbol: str | None
    schema_version_kind: str
    canonical_owner: str
    producers: tuple[str, ...]
    consumers: tuple[str, ...]
    parent_contracts: tuple[str, ...]
    identity_fields: tuple[str, ...]
    join_key: tuple[str, ...]
    expected_cardinality: str
    event_clock: str
    availability_clock: str
    clock_unit: str
    source_classes: tuple[str, ...]
    reconciliation_policy: str
    retention: str
    evidence: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DeliveryClaim:
    id: str
    scope: str
    transport: TransportKind
    guarantee: DeliveryGuarantee
    replay: str
    acknowledgement_milestone: str
    ordering_scope: str
    cross_producer_ordering: str
    duplicate_possible: bool
    evidence: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Edge:
    id: str
    source: str
    target: str
    category: EdgeCategory
    contract: str
    transport: TransportKind
    correlation: str
    sync_semantics: SyncSemantics
    delivery_claim: str
    enablement_condition: str | None
    authority_direction: str
    required: bool
    style: str
    evidence: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Style:
    id: str
    semantic_role: str
    label: str


@dataclass(frozen=True, slots=True)
class View:
    id: str
    label: str
    kind: ViewKind
    purpose: str
    profile: str | None
    include_temporal_status: tuple[TemporalStatus, ...]
    include_implementation_state: tuple[ImplementationState, ...]
    include_profile_enablement: tuple[EnablementState, ...]
    explicit_components: tuple[str, ...]
    explicit_tombstones: tuple[str, ...]
    explicit_edges: tuple[str, ...]
    direction: DiagramDirection
    layout_engine: LayoutEngine
    routing: RoutingStyle
    pack_mode: str
    grid_columns: int | None
    node_separation: float | None
    rank_separation: float | None
    formats: tuple[OutputFormat, ...]
    theme: str
    accessibility_companion_required: bool
    no_execution_banner: bool
    max_nodes: int | None
    max_edges: int | None
    max_cluster_depth: int | None
    target_width_px: int | None
    target_height_px: int | None
    minimum_text_size_pt: int | None
    evidence: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Tombstone:
    id: str
    label: str
    former_kind: str
    former_boundary: str
    disposition: ImplementationState
    removed_at_commit: str
    replacement: str | None
    evidence: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AuthorityConflict:
    id: str
    label: str
    affected_ids: tuple[str, ...]
    evidence: tuple[str, ...]
    required_decision: str
    status: str
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DriftException:
    id: str
    rule: str
    affected_paths: tuple[str, ...]
    affected_ids: tuple[str, ...]
    reason: str
    owner: str
    approval_reference: str
    expires_at: str | None
    removal_condition: str
    evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ArchitectureManifest:
    header: ManifestHeader
    evidence: tuple[EvidenceRecord, ...]
    profiles: tuple[Profile, ...]
    boundaries: tuple[Boundary, ...]
    components: tuple[Component, ...]
    capabilities: tuple[Capability, ...]
    contracts: tuple[Contract, ...]
    delivery_claims: tuple[DeliveryClaim, ...]
    edges: tuple[Edge, ...]
    styles: tuple[Style, ...]
    views: tuple[View, ...]
    tombstones: tuple[Tombstone, ...]
    authority_conflicts: tuple[AuthorityConflict, ...]
    drift_exceptions: tuple[DriftException, ...]
