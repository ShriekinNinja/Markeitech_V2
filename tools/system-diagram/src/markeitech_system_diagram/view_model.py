from __future__ import annotations

from dataclasses import dataclass

from .diagnostics import ManifestError
from .models import ArchitectureManifest, Boundary, Capability, Component, Edge, Tombstone, View


@dataclass(frozen=True, slots=True)
class SelectedView:
    definition: View
    boundaries: tuple[Boundary, ...]
    components: tuple[Component, ...]
    capabilities: tuple[Capability, ...]
    tombstones: tuple[Tombstone, ...]
    edges: tuple[Edge, ...]


def _boundary_depth(boundary_id: str, boundaries: dict[str, Boundary]) -> int:
    depth = 1
    current = boundaries[boundary_id]
    visited = {boundary_id}
    while current.parent is not None:
        if current.parent in visited:
            raise ManifestError("VIEW_BOUNDARY_CYCLE", boundary_id, "boundary cycle detected")
        visited.add(current.parent)
        depth += 1
        current = boundaries[current.parent]
    return depth


def select_view(manifest: ArchitectureManifest, view_id: str) -> SelectedView:
    views = {view.id: view for view in manifest.views}
    if view_id not in views:
        raise ManifestError("VIEW_UNKNOWN", view_id, "view is not declared by the manifest")
    view = views[view_id]
    components_by_id = {component.id: component for component in manifest.components}
    edges_by_id = {edge.id: edge for edge in manifest.edges}
    tombstones_by_id = {tombstone.id: tombstone for tombstone in manifest.tombstones}
    boundaries_by_id = {boundary.id: boundary for boundary in manifest.boundaries}

    component_ids = view.explicit_components or tuple(components_by_id)
    components = tuple(components_by_id[item] for item in sorted(component_ids))
    selected_component_ids = {component.id for component in components}
    capabilities = tuple(
        capability
        for capability in manifest.capabilities
        if capability.component in selected_component_ids
    )
    edge_ids = view.explicit_edges
    edges = tuple(edges_by_id[item] for item in sorted(edge_ids))
    tombstones = tuple(
        tombstones_by_id[item] for item in sorted(view.explicit_tombstones)
    )

    required_boundary_ids = {component.boundary for component in components} | {
        tombstone.former_boundary for tombstone in tombstones
    }
    for boundary_id in tuple(required_boundary_ids):
        current = boundaries_by_id[boundary_id]
        while current.parent is not None:
            required_boundary_ids.add(current.parent)
            current = boundaries_by_id[current.parent]
    boundaries = tuple(
        boundaries_by_id[item]
        for item in sorted(
            required_boundary_ids,
            key=lambda item: (_boundary_depth(item, boundaries_by_id), item),
        )
    )

    node_count = len(components) + len(tombstones)
    if view.max_nodes is not None and node_count > view.max_nodes:
        raise ManifestError(
            "VIEW_NODE_BUDGET",
            view.id,
            f"selected {node_count} nodes; approved maximum is {view.max_nodes}",
        )
    if view.max_edges is not None and len(edges) > view.max_edges:
        raise ManifestError(
            "VIEW_EDGE_BUDGET",
            view.id,
            f"selected {len(edges)} edges; approved maximum is {view.max_edges}",
        )
    if view.max_cluster_depth is not None:
        actual_depth = max(
            (_boundary_depth(component.boundary, boundaries_by_id) for component in components),
            default=0,
        )
        if actual_depth > view.max_cluster_depth:
            raise ManifestError(
                "VIEW_CLUSTER_BUDGET",
                view.id,
                f"selected cluster depth {actual_depth}; approved maximum is "
                f"{view.max_cluster_depth}",
            )
    return SelectedView(
        definition=view,
        boundaries=boundaries,
        components=components,
        capabilities=capabilities,
        tombstones=tombstones,
        edges=edges,
    )
