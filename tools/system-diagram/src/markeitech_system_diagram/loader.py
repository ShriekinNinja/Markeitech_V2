from __future__ import annotations

import stat
import tomllib
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, TypeVar

from .diagnostics import ManifestError
from .models import (
    AcceptanceState,
    ArchitectureManifest,
    AuthorityConflict,
    Boundary,
    BoundaryKind,
    Capability,
    Component,
    ComponentKind,
    CompositionPolicy,
    Contract,
    DeliveryClaim,
    DeliveryGuarantee,
    DiagramDirection,
    DriftException,
    Edge,
    EdgeCategory,
    EnablementState,
    EvidenceCertainty,
    EvidenceClass,
    EvidenceRecord,
    ImplementationState,
    LayoutEngine,
    ManifestHeader,
    OutputFormat,
    Profile,
    ProfileState,
    ReviewStatus,
    RoutingStyle,
    Style,
    SyncSemantics,
    TemporalStatus,
    Tombstone,
    TransportKind,
    View,
    ViewKind,
)
from .schema import validate_manifest

_MAX_MANIFEST_BYTES = 2 * 1024 * 1024
_EnumT = TypeVar("_EnumT")


class _Reader:
    def __init__(self, value: Mapping[str, Any], location: str) -> None:
        self._remaining = dict(value)
        self.location = location

    def take(self, key: str, *, default: Any = ...) -> Any:
        if key in self._remaining:
            return self._remaining.pop(key)
        if default is not ...:
            return default
        raise ManifestError(
            "MANIFEST_MISSING_FIELD",
            f"{self.location}.{key}",
            "required field is missing",
        )

    def finish(self) -> None:
        if self._remaining:
            unknown = sorted(self._remaining)[0]
            raise ManifestError(
                "MANIFEST_UNKNOWN_FIELD",
                f"{self.location}.{unknown}",
                "field is not defined by schema version 1",
            )


def _table(value: Any, location: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ManifestError("MANIFEST_TYPE", location, "expected a TOML table")
    return value


def _tables(value: Any, location: str) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ManifestError("MANIFEST_TYPE", location, "expected an array of TOML tables")
    return tuple(value)


def _string(value: Any, location: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ManifestError("MANIFEST_TYPE", location, "expected a non-empty string")
    return value


def _optional_string(value: Any, location: str) -> str | None:
    if value is None:
        return None
    return _string(value, location)


def _integer(value: Any, location: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ManifestError(
            "MANIFEST_TYPE",
            location,
            f"expected an integer greater than or equal to {minimum}",
        )
    return value


def _optional_integer(value: Any, location: str, *, minimum: int = 1) -> int | None:
    if value is None:
        return None
    return _integer(value, location, minimum=minimum)


def _optional_number(
    value: Any,
    location: str,
    *,
    minimum: float,
    maximum: float,
) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ManifestError("MANIFEST_TYPE", location, "expected a number")
    result = float(value)
    if not minimum <= result <= maximum:
        raise ManifestError(
            "MANIFEST_TYPE",
            location,
            f"expected a number between {minimum} and {maximum}",
        )
    return result


def _boolean(value: Any, location: str) -> bool:
    if not isinstance(value, bool):
        raise ManifestError("MANIFEST_TYPE", location, "expected a boolean")
    return value


def _strings(value: Any, location: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ManifestError("MANIFEST_TYPE", location, "expected an array of strings")
    return tuple(_string(item, f"{location}[{index}]") for index, item in enumerate(value))


def _enum(value: Any, enum_type: type[_EnumT], location: str) -> _EnumT:
    raw = _string(value, location)
    try:
        return enum_type(raw)
    except ValueError as exc:
        allowed = ", ".join(member.value for member in enum_type)  # type: ignore[attr-defined]
        raise ManifestError(
            "MANIFEST_ENUM",
            location,
            f"expected one of: {allowed}",
        ) from exc


def _enums(value: Any, enum_type: type[_EnumT], location: str) -> tuple[_EnumT, ...]:
    if not isinstance(value, list):
        raise ManifestError("MANIFEST_TYPE", location, "expected an array of enum values")
    return tuple(
        _enum(item, enum_type, f"{location}[{index}]") for index, item in enumerate(value)
    )


def _records(
    root: _Reader,
    key: str,
    parser: Callable[[Mapping[str, Any], str], _EnumT],
) -> tuple[_EnumT, ...]:
    tables = _tables(root.take(key, default=[]), key)
    return tuple(parser(item, f"{key}[{index}]") for index, item in enumerate(tables))


def _parse_header(value: Mapping[str, Any], location: str) -> ManifestHeader:
    row = _Reader(value, location)
    result = ManifestHeader(
        schema_version=_integer(
            row.take("schema_version"), f"{location}.schema_version", minimum=1
        ),
        id=_string(row.take("id"), f"{location}.id"),
        title=_string(row.take("title"), f"{location}.title"),
        description=_string(row.take("description"), f"{location}.description"),
        scope=_string(row.take("scope"), f"{location}.scope"),
        authority=_string(row.take("authority"), f"{location}.authority"),
        not_runtime_configuration=_boolean(
            row.take("not_runtime_configuration"),
            f"{location}.not_runtime_configuration",
        ),
        checkout_commit=_string(row.take("checkout_commit"), f"{location}.checkout_commit"),
        owner=_string(row.take("owner"), f"{location}.owner"),
        review_status=_enum(
            row.take("review_status"),
            ReviewStatus,
            f"{location}.review_status",
        ),
        architecture_effective_at=_string(
            row.take("architecture_effective_at"),
            f"{location}.architecture_effective_at",
        ),
        generator_contract_version=_integer(
            row.take("generator_contract_version"),
            f"{location}.generator_contract_version",
            minimum=1,
        ),
        default_profile=_string(row.take("default_profile"), f"{location}.default_profile"),
        limitations=_strings(row.take("limitations"), f"{location}.limitations"),
    )
    row.finish()
    return result


def _parse_evidence(value: Mapping[str, Any], location: str) -> EvidenceRecord:
    row = _Reader(value, location)
    result = EvidenceRecord(
        id=_string(row.take("id"), f"{location}.id"),
        evidence_class=_enum(
            row.take("evidence_class"), EvidenceClass, f"{location}.evidence_class"
        ),
        source_path=_string(row.take("source_path"), f"{location}.source_path"),
        source_symbol=_optional_string(
            row.take("source_symbol", default=None), f"{location}.source_symbol"
        ),
        observed_at=_string(row.take("observed_at"), f"{location}.observed_at"),
        proves=_strings(row.take("proves"), f"{location}.proves"),
        limitations=_strings(row.take("limitations"), f"{location}.limitations"),
    )
    row.finish()
    return result


def _parse_profile(value: Mapping[str, Any], location: str) -> Profile:
    row = _Reader(value, location)
    result = Profile(
        id=_string(row.take("id"), f"{location}.id"),
        config_path=_string(row.take("config_path"), f"{location}.config_path"),
        config_schema_version=_integer(
            row.take("config_schema_version"),
            f"{location}.config_schema_version",
            minimum=1,
        ),
        content_sha256=_optional_string(
            row.take("content_sha256", default=None), f"{location}.content_sha256"
        ),
        status=_string(row.take("status"), f"{location}.status"),
        limitations=_strings(row.take("limitations"), f"{location}.limitations"),
        evidence=_strings(row.take("evidence"), f"{location}.evidence"),
    )
    row.finish()
    return result


def _parse_boundary(value: Mapping[str, Any], location: str) -> Boundary:
    row = _Reader(value, location)
    result = Boundary(
        id=_string(row.take("id"), f"{location}.id"),
        label=_string(row.take("label"), f"{location}.label"),
        kind=_enum(row.take("kind"), BoundaryKind, f"{location}.kind"),
        parent=_optional_string(row.take("parent", default=None), f"{location}.parent"),
        temporal_status=_enum(
            row.take("temporal_status"), TemporalStatus, f"{location}.temporal_status"
        ),
        evidence=_strings(row.take("evidence"), f"{location}.evidence"),
        limitations=_strings(row.take("limitations"), f"{location}.limitations"),
    )
    row.finish()
    return result


def _parse_profile_state(value: Mapping[str, Any], location: str) -> ProfileState:
    row = _Reader(value, location)
    result = ProfileState(
        profile=_string(row.take("profile"), f"{location}.profile"),
        enablement=_enum(row.take("enablement"), EnablementState, f"{location}.enablement"),
    )
    row.finish()
    return result


def _parse_component(value: Mapping[str, Any], location: str) -> Component:
    row = _Reader(value, location)
    profile_tables = _tables(row.take("profile_states"), f"{location}.profile_states")
    result = Component(
        id=_string(row.take("id"), f"{location}.id"),
        label=_string(row.take("label"), f"{location}.label"),
        kind=_enum(row.take("kind"), ComponentKind, f"{location}.kind"),
        logical_area=_string(row.take("logical_area"), f"{location}.logical_area"),
        boundary=_string(row.take("boundary"), f"{location}.boundary"),
        implementation_ref=_optional_string(
            row.take("implementation_ref", default=None), f"{location}.implementation_ref"
        ),
        composition_key=_optional_string(
            row.take("composition_key", default=None), f"{location}.composition_key"
        ),
        composition_order=_optional_integer(
            row.take("composition_order", default=None), f"{location}.composition_order"
        ),
        actor_id=_optional_string(row.take("actor_id", default=None), f"{location}.actor_id"),
        responsibilities=_strings(
            row.take("responsibilities"), f"{location}.responsibilities"
        ),
        semantic_owner=_string(row.take("semantic_owner"), f"{location}.semantic_owner"),
        mutation_owner=_string(row.take("mutation_owner"), f"{location}.mutation_owner"),
        transport_owner=_string(row.take("transport_owner"), f"{location}.transport_owner"),
        persistence_owner=_string(
            row.take("persistence_owner"), f"{location}.persistence_owner"
        ),
        recovery_owner=_string(row.take("recovery_owner"), f"{location}.recovery_owner"),
        projection_owner=_string(
            row.take("projection_owner"), f"{location}.projection_owner"
        ),
        policy_owner=_string(row.take("policy_owner"), f"{location}.policy_owner"),
        implementation_state=_enum(
            row.take("implementation_state"),
            ImplementationState,
            f"{location}.implementation_state",
        ),
        composition_policy=_enum(
            row.take("composition_policy"),
            CompositionPolicy,
            f"{location}.composition_policy",
        ),
        temporal_status=_enum(
            row.take("temporal_status"), TemporalStatus, f"{location}.temporal_status"
        ),
        acceptance_state=_enum(
            row.take("acceptance_state"), AcceptanceState, f"{location}.acceptance_state"
        ),
        evidence_certainty=_enum(
            row.take("evidence_certainty"),
            EvidenceCertainty,
            f"{location}.evidence_certainty",
        ),
        configuration_path=_optional_string(
            row.take("configuration_path", default=None), f"{location}.configuration_path"
        ),
        failure_isolation=_string(
            row.take("failure_isolation"), f"{location}.failure_isolation"
        ),
        cardinality=_string(row.take("cardinality"), f"{location}.cardinality"),
        style=_string(row.take("style"), f"{location}.style"),
        profile_states=tuple(
            _parse_profile_state(item, f"{location}.profile_states[{index}]")
            for index, item in enumerate(profile_tables)
        ),
        evidence=_strings(row.take("evidence"), f"{location}.evidence"),
        limitations=_strings(row.take("limitations"), f"{location}.limitations"),
    )
    row.finish()
    return result


def _parse_capability(value: Mapping[str, Any], location: str) -> Capability:
    row = _Reader(value, location)
    result = Capability(
        id=_string(row.take("id"), f"{location}.id"),
        component=_string(row.take("component"), f"{location}.component"),
        label=_string(row.take("label"), f"{location}.label"),
        implementation_state=_enum(
            row.take("implementation_state"),
            ImplementationState,
            f"{location}.implementation_state",
        ),
        composition_policy=_enum(
            row.take("composition_policy"),
            CompositionPolicy,
            f"{location}.composition_policy",
        ),
        configuration_path=_optional_string(
            row.take("configuration_path", default=None), f"{location}.configuration_path"
        ),
        profile=_string(row.take("profile"), f"{location}.profile"),
        enablement=_enum(row.take("enablement"), EnablementState, f"{location}.enablement"),
        evidence=_strings(row.take("evidence"), f"{location}.evidence"),
        limitations=_strings(row.take("limitations"), f"{location}.limitations"),
    )
    row.finish()
    return result


def _parse_contract(value: Mapping[str, Any], location: str) -> Contract:
    row = _Reader(value, location)
    result = Contract(
        id=_string(row.take("id"), f"{location}.id"),
        label=_string(row.take("label"), f"{location}.label"),
        transport_kind=_enum(
            row.take("transport_kind"), TransportKind, f"{location}.transport_kind"
        ),
        type_name=_string(row.take("type_name"), f"{location}.type_name"),
        python_symbol=_optional_string(
            row.take("python_symbol", default=None), f"{location}.python_symbol"
        ),
        schema_version_kind=_string(
            row.take("schema_version_kind"), f"{location}.schema_version_kind"
        ),
        canonical_owner=_string(
            row.take("canonical_owner"), f"{location}.canonical_owner"
        ),
        producers=_strings(row.take("producers"), f"{location}.producers"),
        consumers=_strings(row.take("consumers"), f"{location}.consumers"),
        parent_contracts=_strings(
            row.take("parent_contracts"), f"{location}.parent_contracts"
        ),
        identity_fields=_strings(
            row.take("identity_fields"), f"{location}.identity_fields"
        ),
        join_key=_strings(row.take("join_key"), f"{location}.join_key"),
        expected_cardinality=_string(
            row.take("expected_cardinality"), f"{location}.expected_cardinality"
        ),
        event_clock=_string(row.take("event_clock"), f"{location}.event_clock"),
        availability_clock=_string(
            row.take("availability_clock"), f"{location}.availability_clock"
        ),
        clock_unit=_string(row.take("clock_unit"), f"{location}.clock_unit"),
        source_classes=_strings(row.take("source_classes"), f"{location}.source_classes"),
        reconciliation_policy=_string(
            row.take("reconciliation_policy"), f"{location}.reconciliation_policy"
        ),
        retention=_string(row.take("retention"), f"{location}.retention"),
        evidence=_strings(row.take("evidence"), f"{location}.evidence"),
        limitations=_strings(row.take("limitations"), f"{location}.limitations"),
    )
    row.finish()
    return result


def _parse_delivery_claim(value: Mapping[str, Any], location: str) -> DeliveryClaim:
    row = _Reader(value, location)
    result = DeliveryClaim(
        id=_string(row.take("id"), f"{location}.id"),
        scope=_string(row.take("scope"), f"{location}.scope"),
        transport=_enum(row.take("transport"), TransportKind, f"{location}.transport"),
        guarantee=_enum(
            row.take("guarantee"), DeliveryGuarantee, f"{location}.guarantee"
        ),
        replay=_string(row.take("replay"), f"{location}.replay"),
        acknowledgement_milestone=_string(
            row.take("acknowledgement_milestone"),
            f"{location}.acknowledgement_milestone",
        ),
        ordering_scope=_string(row.take("ordering_scope"), f"{location}.ordering_scope"),
        cross_producer_ordering=_string(
            row.take("cross_producer_ordering"), f"{location}.cross_producer_ordering"
        ),
        duplicate_possible=_boolean(
            row.take("duplicate_possible"), f"{location}.duplicate_possible"
        ),
        evidence=_strings(row.take("evidence"), f"{location}.evidence"),
        limitations=_strings(row.take("limitations"), f"{location}.limitations"),
    )
    row.finish()
    return result


def _parse_edge(value: Mapping[str, Any], location: str) -> Edge:
    row = _Reader(value, location)
    result = Edge(
        id=_string(row.take("id"), f"{location}.id"),
        source=_string(row.take("source"), f"{location}.source"),
        target=_string(row.take("target"), f"{location}.target"),
        category=_enum(row.take("category"), EdgeCategory, f"{location}.category"),
        contract=_string(row.take("contract"), f"{location}.contract"),
        transport=_enum(row.take("transport"), TransportKind, f"{location}.transport"),
        correlation=_string(row.take("correlation"), f"{location}.correlation"),
        sync_semantics=_enum(
            row.take("sync_semantics"), SyncSemantics, f"{location}.sync_semantics"
        ),
        delivery_claim=_string(row.take("delivery_claim"), f"{location}.delivery_claim"),
        enablement_condition=_optional_string(
            row.take("enablement_condition", default=None),
            f"{location}.enablement_condition",
        ),
        authority_direction=_string(
            row.take("authority_direction"), f"{location}.authority_direction"
        ),
        required=_boolean(row.take("required"), f"{location}.required"),
        style=_string(row.take("style"), f"{location}.style"),
        evidence=_strings(row.take("evidence"), f"{location}.evidence"),
        limitations=_strings(row.take("limitations"), f"{location}.limitations"),
    )
    row.finish()
    return result


def _parse_style(value: Mapping[str, Any], location: str) -> Style:
    row = _Reader(value, location)
    result = Style(
        id=_string(row.take("id"), f"{location}.id"),
        semantic_role=_string(row.take("semantic_role"), f"{location}.semantic_role"),
        label=_string(row.take("label"), f"{location}.label"),
    )
    row.finish()
    return result


def _parse_view(value: Mapping[str, Any], location: str) -> View:
    row = _Reader(value, location)
    result = View(
        id=_string(row.take("id"), f"{location}.id"),
        label=_string(row.take("label"), f"{location}.label"),
        kind=_enum(row.take("kind"), ViewKind, f"{location}.kind"),
        purpose=_string(row.take("purpose"), f"{location}.purpose"),
        profile=_optional_string(row.take("profile", default=None), f"{location}.profile"),
        include_temporal_status=_enums(
            row.take("include_temporal_status"),
            TemporalStatus,
            f"{location}.include_temporal_status",
        ),
        include_implementation_state=_enums(
            row.take("include_implementation_state"),
            ImplementationState,
            f"{location}.include_implementation_state",
        ),
        include_profile_enablement=_enums(
            row.take("include_profile_enablement"),
            EnablementState,
            f"{location}.include_profile_enablement",
        ),
        explicit_components=_strings(
            row.take("explicit_components"), f"{location}.explicit_components"
        ),
        explicit_tombstones=_strings(
            row.take("explicit_tombstones"), f"{location}.explicit_tombstones"
        ),
        explicit_edges=_strings(row.take("explicit_edges"), f"{location}.explicit_edges"),
        direction=_enum(row.take("direction"), DiagramDirection, f"{location}.direction"),
        layout_engine=_enum(
            row.take("layout_engine"), LayoutEngine, f"{location}.layout_engine"
        ),
        routing=_enum(row.take("routing"), RoutingStyle, f"{location}.routing"),
        pack_mode=_string(row.take("pack_mode"), f"{location}.pack_mode"),
        grid_columns=_optional_integer(
            row.take("grid_columns", default=None), f"{location}.grid_columns"
        ),
        node_separation=_optional_number(
            row.take("node_separation", default=None),
            f"{location}.node_separation",
            minimum=0.20,
            maximum=3.0,
        ),
        rank_separation=_optional_number(
            row.take("rank_separation", default=None),
            f"{location}.rank_separation",
            minimum=0.25,
            maximum=3.0,
        ),
        formats=_enums(row.take("formats"), OutputFormat, f"{location}.formats"),
        theme=_string(row.take("theme"), f"{location}.theme"),
        accessibility_companion_required=_boolean(
            row.take("accessibility_companion_required"),
            f"{location}.accessibility_companion_required",
        ),
        no_execution_banner=_boolean(
            row.take("no_execution_banner"), f"{location}.no_execution_banner"
        ),
        max_nodes=_optional_integer(
            row.take("max_nodes", default=None), f"{location}.max_nodes"
        ),
        max_edges=_optional_integer(
            row.take("max_edges", default=None), f"{location}.max_edges"
        ),
        max_cluster_depth=_optional_integer(
            row.take("max_cluster_depth", default=None), f"{location}.max_cluster_depth"
        ),
        target_width_px=_optional_integer(
            row.take("target_width_px", default=None), f"{location}.target_width_px"
        ),
        target_height_px=_optional_integer(
            row.take("target_height_px", default=None), f"{location}.target_height_px"
        ),
        minimum_text_size_pt=_optional_integer(
            row.take("minimum_text_size_pt", default=None),
            f"{location}.minimum_text_size_pt",
        ),
        evidence=_strings(row.take("evidence"), f"{location}.evidence"),
        limitations=_strings(row.take("limitations"), f"{location}.limitations"),
    )
    row.finish()
    return result


def _parse_tombstone(value: Mapping[str, Any], location: str) -> Tombstone:
    row = _Reader(value, location)
    result = Tombstone(
        id=_string(row.take("id"), f"{location}.id"),
        label=_string(row.take("label"), f"{location}.label"),
        former_kind=_string(row.take("former_kind"), f"{location}.former_kind"),
        former_boundary=_string(
            row.take("former_boundary"), f"{location}.former_boundary"
        ),
        disposition=_enum(
            row.take("disposition"), ImplementationState, f"{location}.disposition"
        ),
        removed_at_commit=_string(
            row.take("removed_at_commit"), f"{location}.removed_at_commit"
        ),
        replacement=_optional_string(
            row.take("replacement", default=None), f"{location}.replacement"
        ),
        evidence=_strings(row.take("evidence"), f"{location}.evidence"),
        limitations=_strings(row.take("limitations"), f"{location}.limitations"),
    )
    row.finish()
    return result


def _parse_authority_conflict(value: Mapping[str, Any], location: str) -> AuthorityConflict:
    row = _Reader(value, location)
    result = AuthorityConflict(
        id=_string(row.take("id"), f"{location}.id"),
        label=_string(row.take("label"), f"{location}.label"),
        affected_ids=_strings(row.take("affected_ids"), f"{location}.affected_ids"),
        evidence=_strings(row.take("evidence"), f"{location}.evidence"),
        required_decision=_string(
            row.take("required_decision"), f"{location}.required_decision"
        ),
        status=_string(row.take("status"), f"{location}.status"),
        limitations=_strings(row.take("limitations"), f"{location}.limitations"),
    )
    row.finish()
    return result


def _parse_drift_exception(value: Mapping[str, Any], location: str) -> DriftException:
    row = _Reader(value, location)
    result = DriftException(
        id=_string(row.take("id"), f"{location}.id"),
        rule=_string(row.take("rule"), f"{location}.rule"),
        affected_paths=_strings(row.take("affected_paths"), f"{location}.affected_paths"),
        affected_ids=_strings(row.take("affected_ids"), f"{location}.affected_ids"),
        reason=_string(row.take("reason"), f"{location}.reason"),
        owner=_string(row.take("owner"), f"{location}.owner"),
        approval_reference=_string(
            row.take("approval_reference"), f"{location}.approval_reference"
        ),
        expires_at=_optional_string(
            row.take("expires_at", default=None), f"{location}.expires_at"
        ),
        removal_condition=_string(
            row.take("removal_condition"), f"{location}.removal_condition"
        ),
        evidence=_strings(row.take("evidence"), f"{location}.evidence"),
    )
    row.finish()
    return result


def _sorted(records: tuple[_EnumT, ...]) -> tuple[_EnumT, ...]:
    return tuple(sorted(records, key=lambda item: item.id))  # type: ignore[attr-defined]


def _load_raw(path: Path, repository_root: Path) -> Mapping[str, Any]:
    if not repository_root.exists() or not repository_root.is_dir():
        raise ManifestError("MANIFEST_REPOSITORY_ROOT", "repository_root", "directory is absent")
    approved_root = repository_root.absolute()
    resolved_root = repository_root.resolve()
    candidate = path if path.is_absolute() else approved_root / path
    if candidate.is_symlink():
        raise ManifestError("MANIFEST_UNSAFE_PATH", "manifest", "symlinks are not allowed")
    try:
        unresolved = candidate.absolute()
        relative = unresolved.relative_to(approved_root)
        current = approved_root
        for part in relative.parts:
            current /= part
            if current.is_symlink():
                raise ManifestError(
                    "MANIFEST_UNSAFE_PATH",
                    "manifest",
                    "symlinks are not allowed",
                )
        resolved = unresolved.resolve(strict=True)
        resolved.relative_to(resolved_root)
    except ManifestError:
        raise
    except (FileNotFoundError, ValueError) as exc:
        raise ManifestError(
            "MANIFEST_UNSAFE_PATH",
            "manifest",
            "expected an existing file beneath the repository root",
        ) from exc
    mode = resolved.stat().st_mode
    if not stat.S_ISREG(mode):
        raise ManifestError("MANIFEST_UNSAFE_PATH", "manifest", "expected a regular file")
    if resolved.stat().st_size > _MAX_MANIFEST_BYTES:
        raise ManifestError("MANIFEST_TOO_LARGE", "manifest", "file exceeds the 2 MiB limit")
    try:
        with resolved.open("rb") as file:
            raw = tomllib.load(file)
    except tomllib.TOMLDecodeError as exc:
        raise ManifestError("MANIFEST_TOML", "manifest", "invalid TOML") from exc
    return _table(raw, "manifest-root")


def load_manifest(path: Path, *, repository_root: Path) -> ArchitectureManifest:
    """Load and validate one repository-controlled architecture manifest.

    The loader performs no imports from Markeitech or NautilusTrader and has no runtime,
    environment, service, or network integration.
    """

    root = _Reader(_load_raw(path, repository_root), "manifest-root")
    header = _parse_header(_table(root.take("manifest"), "manifest"), "manifest")
    if header.schema_version != 1:
        raise ManifestError(
            "MANIFEST_SCHEMA_VERSION",
            "manifest.schema_version",
            "only schema version 1 is supported",
        )
    manifest = ArchitectureManifest(
        header=header,
        evidence=_sorted(_records(root, "evidence", _parse_evidence)),
        profiles=_sorted(_records(root, "profiles", _parse_profile)),
        boundaries=_sorted(_records(root, "boundaries", _parse_boundary)),
        components=_sorted(_records(root, "components", _parse_component)),
        capabilities=_sorted(_records(root, "capabilities", _parse_capability)),
        contracts=_sorted(_records(root, "contracts", _parse_contract)),
        delivery_claims=_sorted(_records(root, "delivery_claims", _parse_delivery_claim)),
        edges=_sorted(_records(root, "edges", _parse_edge)),
        styles=_sorted(_records(root, "styles", _parse_style)),
        views=_sorted(_records(root, "views", _parse_view)),
        tombstones=_sorted(_records(root, "tombstones", _parse_tombstone)),
        authority_conflicts=_sorted(
            _records(root, "authority_conflicts", _parse_authority_conflict)
        ),
        drift_exceptions=_sorted(_records(root, "drift_exceptions", _parse_drift_exception)),
    )
    root.finish()
    validate_manifest(manifest)
    return manifest
