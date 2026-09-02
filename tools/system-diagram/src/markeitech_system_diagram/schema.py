from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import PurePosixPath

from .diagnostics import ManifestError
from .models import (
    ArchitectureManifest,
    EnablementState,
    ImplementationState,
    OutputFormat,
    TemporalStatus,
    ViewKind,
    is_owner_sentinel,
    validate_stable_id,
)

_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_EVIDENCE_ROOTS = frozenset(
    {
        "AGENTS.md",
        "CONTRIBUTING.md",
        "markeitech.md",
        "config",
        "docs",
        "src",
        "tools",
    }
)
_FORBIDDEN_PATH_PARTS = frozenset({".env", ".git", ".idea", ".venv", "__pycache__"})


def validate_repository_path(value: str, location: str) -> str:
    if "\\" in value or "://" in value:
        raise ManifestError(
            "MANIFEST_UNSAFE_REPOSITORY_PATH",
            location,
            "expected a normalized repository-relative path",
        )
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ManifestError(
            "MANIFEST_UNSAFE_REPOSITORY_PATH",
            location,
            "expected a normalized repository-relative path",
        )
    if any(part in _FORBIDDEN_PATH_PARTS for part in path.parts):
        raise ManifestError(
            "MANIFEST_FORBIDDEN_REPOSITORY_PATH",
            location,
            "path enters a forbidden repository or local-state boundary",
        )
    first = path.parts[0]
    if first not in _ALLOWED_EVIDENCE_ROOTS:
        raise ManifestError(
            "MANIFEST_UNAPPROVED_REPOSITORY_ROOT",
            location,
            "path is outside the approved architecture-evidence roots",
        )
    return value


def _validate_unique_strings(values: tuple[str, ...], location: str) -> None:
    seen: set[str] = set()
    for index, value in enumerate(values):
        if value in seen:
            raise ManifestError(
                "MANIFEST_DUPLICATE_VALUE",
                f"{location}[{index}]",
                "duplicate value is not allowed",
            )
        seen.add(value)


def _require_reference(value: str, allowed: set[str], location: str) -> None:
    if value not in allowed:
        raise ManifestError(
            "MANIFEST_DANGLING_REFERENCE",
            location,
            "referenced stable ID does not exist",
        )


def _require_references(values: Iterable[str], allowed: set[str], location: str) -> None:
    for index, value in enumerate(values):
        _require_reference(value, allowed, f"{location}[{index}]")


def _require_evidence(values: tuple[str, ...], evidence_ids: set[str], location: str) -> None:
    _validate_unique_strings(values, location)
    _require_references(values, evidence_ids, location)


def _validate_owner(value: str, allowed: set[str], location: str) -> None:
    if not is_owner_sentinel(value):
        _require_reference(value, allowed, location)


def _validate_global_ids(manifest: ArchitectureManifest) -> set[str]:
    records = (
        *manifest.evidence,
        *manifest.profiles,
        *manifest.boundaries,
        *manifest.components,
        *manifest.capabilities,
        *manifest.contracts,
        *manifest.delivery_claims,
        *manifest.edges,
        *manifest.styles,
        *manifest.views,
        *manifest.tombstones,
        *manifest.authority_conflicts,
        *manifest.drift_exceptions,
    )
    seen: set[str] = set()
    validate_stable_id(manifest.header.id, "manifest.id")
    for record in records:
        validate_stable_id(record.id, f"{record.__class__.__name__}.{record.id}.id")
        if record.id in seen:
            raise ManifestError(
                "MANIFEST_DUPLICATE_ID",
                record.id,
                "stable IDs must be globally unique across all record families",
            )
        seen.add(record.id)
    return seen


def _validate_boundary_tree(manifest: ArchitectureManifest, boundary_ids: set[str]) -> None:
    parent_by_id = {boundary.id: boundary.parent for boundary in manifest.boundaries}
    for boundary in manifest.boundaries:
        if boundary.parent is not None:
            _require_reference(
                boundary.parent,
                boundary_ids,
                f"boundaries.{boundary.id}.parent",
            )
        visited: set[str] = set()
        current: str | None = boundary.id
        while current is not None:
            if current in visited:
                raise ManifestError(
                    "MANIFEST_BOUNDARY_CYCLE",
                    f"boundaries.{boundary.id}.parent",
                    "boundary hierarchy contains a cycle",
                )
            visited.add(current)
            current = parent_by_id.get(current)


def _validate_header(manifest: ArchitectureManifest, profile_ids: set[str]) -> None:
    header = manifest.header
    if not header.not_runtime_configuration:
        raise ManifestError(
            "MANIFEST_RUNTIME_AUTHORITY_FORBIDDEN",
            "manifest.not_runtime_configuration",
            "the architecture manifest cannot be runtime configuration",
        )
    if header.authority != "architecture_representation_only":
        raise ManifestError(
            "MANIFEST_AUTHORITY",
            "manifest.authority",
            "authority must be architecture_representation_only",
        )
    if not _COMMIT.fullmatch(header.checkout_commit):
        raise ManifestError(
            "MANIFEST_COMMIT",
            "manifest.checkout_commit",
            "expected a full lowercase 40-character Git commit",
        )
    _require_reference(header.default_profile, profile_ids, "manifest.default_profile")
    _validate_unique_strings(header.limitations, "manifest.limitations")


def validate_manifest(manifest: ArchitectureManifest) -> None:
    """Validate schema-version-1 semantic and reference invariants."""

    all_ids = _validate_global_ids(manifest)
    evidence_ids = {record.id for record in manifest.evidence}
    profile_ids = {record.id for record in manifest.profiles}
    boundary_ids = {record.id for record in manifest.boundaries}
    component_ids = {record.id for record in manifest.components}
    capability_ids = {record.id for record in manifest.capabilities}
    contract_ids = {record.id for record in manifest.contracts}
    delivery_ids = {record.id for record in manifest.delivery_claims}
    edge_ids = {record.id for record in manifest.edges}
    style_ids = {record.id for record in manifest.styles}
    endpoint_ids = component_ids | boundary_ids
    owner_ids = endpoint_ids

    if not manifest.profiles:
        raise ManifestError("MANIFEST_EMPTY", "profiles", "at least one named profile is required")
    if not manifest.boundaries:
        raise ManifestError("MANIFEST_EMPTY", "boundaries", "at least one boundary is required")
    if not manifest.views:
        raise ManifestError("MANIFEST_EMPTY", "views", "at least one view is required")

    _validate_header(manifest, profile_ids)
    _validate_boundary_tree(manifest, boundary_ids)

    for evidence in manifest.evidence:
        validate_repository_path(evidence.source_path, f"evidence.{evidence.id}.source_path")
        _validate_unique_strings(evidence.proves, f"evidence.{evidence.id}.proves")
        _validate_unique_strings(evidence.limitations, f"evidence.{evidence.id}.limitations")

    for profile in manifest.profiles:
        validate_repository_path(profile.config_path, f"profiles.{profile.id}.config_path")
        if not profile.config_path.startswith("config/") or profile.config_path.endswith(
            ".local.toml"
        ):
            raise ManifestError(
                "MANIFEST_PROFILE_PATH",
                f"profiles.{profile.id}.config_path",
                "profile must be a tracked non-local TOML under config",
            )
        if profile.content_sha256 is not None and not _SHA256.fullmatch(profile.content_sha256):
            raise ManifestError(
                "MANIFEST_SHA256",
                f"profiles.{profile.id}.content_sha256",
                "expected a lowercase SHA-256 digest",
            )
        _require_evidence(profile.evidence, evidence_ids, f"profiles.{profile.id}.evidence")

    for boundary in manifest.boundaries:
        _require_evidence(boundary.evidence, evidence_ids, f"boundaries.{boundary.id}.evidence")

    for component in manifest.components:
        _require_reference(component.boundary, boundary_ids, f"components.{component.id}.boundary")
        if component.implementation_ref is not None:
            source_path = component.implementation_ref.split(":", 1)[0]
            validate_repository_path(source_path, f"components.{component.id}.implementation_ref")
        for owner_field in (
            "semantic_owner",
            "mutation_owner",
            "transport_owner",
            "persistence_owner",
            "recovery_owner",
            "projection_owner",
            "policy_owner",
        ):
            _validate_owner(
                getattr(component, owner_field),
                owner_ids,
                f"components.{component.id}.{owner_field}",
            )
        _require_reference(component.style, style_ids, f"components.{component.id}.style")
        profile_state_ids = tuple(state.profile for state in component.profile_states)
        _validate_unique_strings(profile_state_ids, f"components.{component.id}.profile_states")
        _require_references(
            profile_state_ids,
            profile_ids,
            f"components.{component.id}.profile_states",
        )
        _require_evidence(component.evidence, evidence_ids, f"components.{component.id}.evidence")

    composed_components = [
        component for component in manifest.components if component.composition_key is not None
    ]
    composition_orders = tuple(component.composition_order for component in composed_components)
    if any(
        component.actor_id is None or component.composition_order is None
        for component in composed_components
    ):
        raise ManifestError(
            "MANIFEST_COMPOSITION_IDENTITY",
            "components",
            "every actor registration requires actor_id and composition_order",
        )
    if any(
        component.composition_order is not None
        for component in manifest.components
        if component.composition_key is None
    ):
        raise ManifestError(
            "MANIFEST_COMPOSITION_IDENTITY",
            "components",
            "non-registered components cannot declare composition_order",
        )
    if set(composition_orders) != set(range(1, len(composed_components) + 1)):
        raise ManifestError(
            "MANIFEST_COMPOSITION_ORDER",
            "components",
            "actor composition order must be unique and contiguous from one",
        )

    for capability in manifest.capabilities:
        _require_reference(
            capability.component, component_ids, f"capabilities.{capability.id}.component"
        )
        _require_reference(capability.profile, profile_ids, f"capabilities.{capability.id}.profile")
        _require_evidence(
            capability.evidence,
            evidence_ids,
            f"capabilities.{capability.id}.evidence",
        )

    for contract in manifest.contracts:
        _validate_owner(
            contract.canonical_owner,
            component_ids,
            f"contracts.{contract.id}.canonical_owner",
        )
        _require_references(contract.producers, endpoint_ids, f"contracts.{contract.id}.producers")
        _require_references(contract.consumers, endpoint_ids, f"contracts.{contract.id}.consumers")
        _require_references(
            contract.parent_contracts,
            contract_ids,
            f"contracts.{contract.id}.parent_contracts",
        )
        contract_sequence_fields = (
            "producers",
            "consumers",
            "parent_contracts",
            "identity_fields",
            "join_key",
        )
        for field_name in contract_sequence_fields:
            _validate_unique_strings(
                getattr(contract, field_name), f"contracts.{contract.id}.{field_name}"
            )
        _require_evidence(contract.evidence, evidence_ids, f"contracts.{contract.id}.evidence")

    for claim in manifest.delivery_claims:
        _require_evidence(claim.evidence, evidence_ids, f"delivery_claims.{claim.id}.evidence")

    for edge in manifest.edges:
        _require_reference(edge.source, endpoint_ids, f"edges.{edge.id}.source")
        _require_reference(edge.target, endpoint_ids, f"edges.{edge.id}.target")
        _require_reference(edge.contract, contract_ids, f"edges.{edge.id}.contract")
        _require_reference(edge.delivery_claim, delivery_ids, f"edges.{edge.id}.delivery_claim")
        _require_reference(edge.style, style_ids, f"edges.{edge.id}.style")
        _require_evidence(edge.evidence, evidence_ids, f"edges.{edge.id}.evidence")

    component_by_id = {component.id: component for component in manifest.components}
    for view in manifest.views:
        if view.profile is not None:
            _require_reference(view.profile, profile_ids, f"views.{view.id}.profile")
        _require_reference(view.theme, style_ids, f"views.{view.id}.theme")
        _validate_unique_strings(view.explicit_components, f"views.{view.id}.explicit_components")
        _require_references(
            view.explicit_components,
            component_ids,
            f"views.{view.id}.explicit_components",
        )
        tombstone_ids = {item.id for item in manifest.tombstones}
        _validate_unique_strings(
            view.explicit_tombstones, f"views.{view.id}.explicit_tombstones"
        )
        _require_references(
            view.explicit_tombstones,
            tombstone_ids,
            f"views.{view.id}.explicit_tombstones",
        )
        _validate_unique_strings(view.explicit_edges, f"views.{view.id}.explicit_edges")
        _require_references(view.explicit_edges, edge_ids, f"views.{view.id}.explicit_edges")
        selected_components = set(view.explicit_components)
        for edge_id in view.explicit_edges:
            edge = next(item for item in manifest.edges if item.id == edge_id)
            if edge.source not in selected_components or edge.target not in selected_components:
                raise ManifestError(
                    "MANIFEST_VIEW_EDGE_ENDPOINT",
                    f"views.{view.id}.explicit_edges",
                    "a selected edge has an endpoint outside the selected component set",
                )
        if view.accessibility_companion_required and OutputFormat.MARKDOWN not in view.formats:
            raise ManifestError(
                "MANIFEST_ACCESSIBILITY_COMPANION",
                f"views.{view.id}.formats",
                "Markdown is required when the accessibility companion is required",
            )
        if not view.no_execution_banner:
            raise ManifestError(
                "MANIFEST_EXECUTION_BOUNDARY",
                f"views.{view.id}.no_execution_banner",
                "every view must state that no current order submission or execution exists",
            )
        _validate_unique_strings(
            tuple(item.value for item in view.formats), f"views.{view.id}.formats"
        )
        if view.pack_mode not in {"graph", "array"}:
            raise ManifestError(
                "MANIFEST_VIEW_PACK_MODE",
                f"views.{view.id}.pack_mode",
                "expected graph or array",
            )
        if view.pack_mode == "array" and view.grid_columns is None:
            raise ManifestError(
                "MANIFEST_VIEW_GRID",
                f"views.{view.id}.grid_columns",
                "array packing requires an explicit grid column count",
            )
        if view.kind is ViewKind.CURRENT_RUNTIME:
            if view.explicit_tombstones:
                raise ManifestError(
                    "MANIFEST_CURRENT_VIEW_TOMBSTONE",
                    f"views.{view.id}.explicit_tombstones",
                    "current-runtime views cannot select historical tombstones",
                )
            forbidden_temporal = set(view.include_temporal_status) - {TemporalStatus.CURRENT}
            forbidden_implementation = set(view.include_implementation_state) & {
                ImplementationState.REMOVED,
                ImplementationState.REJECTED,
                ImplementationState.FUTURE,
            }
            if forbidden_temporal or forbidden_implementation:
                raise ManifestError(
                    "MANIFEST_CURRENT_VIEW_FILTER",
                    f"views.{view.id}",
                    "current-runtime views cannot select historical, future, removed, "
                    "or rejected records",
                )
            for component_id in view.explicit_components:
                component = component_by_id[component_id]
                disallowed_state = component.implementation_state in {
                    ImplementationState.REMOVED,
                    ImplementationState.REJECTED,
                    ImplementationState.FUTURE,
                }
                if component.temporal_status is not TemporalStatus.CURRENT or disallowed_state:
                    raise ManifestError(
                        "MANIFEST_CURRENT_VIEW_STATUS",
                        f"views.{view.id}.explicit_components",
                        "a current view explicitly includes a removed, rejected, "
                        "or future component",
                    )
                if view.profile is not None:
                    states = {
                        state.profile: state.enablement for state in component.profile_states
                    }
                    if states.get(view.profile) is EnablementState.DISABLED:
                        raise ManifestError(
                            "MANIFEST_CURRENT_VIEW_DISABLED",
                            f"views.{view.id}.explicit_components",
                            "a current profile view explicitly includes a disabled component",
                        )
        _require_evidence(view.evidence, evidence_ids, f"views.{view.id}.evidence")

    active_ids = component_ids | capability_ids | boundary_ids | contract_ids | edge_ids
    for tombstone in manifest.tombstones:
        _require_reference(
            tombstone.former_boundary,
            boundary_ids,
            f"tombstones.{tombstone.id}.former_boundary",
        )
        if tombstone.disposition not in {
            ImplementationState.REMOVED,
            ImplementationState.REJECTED,
        }:
            raise ManifestError(
                "MANIFEST_TOMBSTONE_STATUS",
                f"tombstones.{tombstone.id}.disposition",
                "tombstones must be removed or rejected",
            )
        if not _COMMIT.fullmatch(tombstone.removed_at_commit):
            raise ManifestError(
                "MANIFEST_COMMIT",
                f"tombstones.{tombstone.id}.removed_at_commit",
                "expected a full lowercase 40-character Git commit",
            )
        if tombstone.replacement is not None:
            _require_reference(
                tombstone.replacement,
                active_ids,
                f"tombstones.{tombstone.id}.replacement",
            )
        _require_evidence(tombstone.evidence, evidence_ids, f"tombstones.{tombstone.id}.evidence")

    for conflict in manifest.authority_conflicts:
        _require_references(
            conflict.affected_ids,
            all_ids,
            f"authority_conflicts.{conflict.id}.affected_ids",
        )
        _require_evidence(
            conflict.evidence,
            evidence_ids,
            f"authority_conflicts.{conflict.id}.evidence",
        )

    for exception in manifest.drift_exceptions:
        if not exception.affected_paths and not exception.affected_ids:
            raise ManifestError(
                "MANIFEST_EXCEPTION_SCOPE",
                f"drift_exceptions.{exception.id}",
                "a drift exception must identify an affected path or stable ID",
            )
        for index, path in enumerate(exception.affected_paths):
            validate_repository_path(
                path,
                f"drift_exceptions.{exception.id}.affected_paths[{index}]",
            )
        _require_references(
            exception.affected_ids,
            all_ids,
            f"drift_exceptions.{exception.id}.affected_ids",
        )
        _require_evidence(
            exception.evidence,
            evidence_ids,
            f"drift_exceptions.{exception.id}.evidence",
        )
        if not exception.approval_reference.lower().startswith("markeitect"):
            raise ManifestError(
                "MANIFEST_EXCEPTION_APPROVAL",
                f"drift_exceptions.{exception.id}.approval_reference",
                "drift exceptions require an explicit Markeitect approval reference",
            )
