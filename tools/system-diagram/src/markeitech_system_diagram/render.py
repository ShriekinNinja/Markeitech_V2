from __future__ import annotations

import hashlib
import html
import importlib.metadata
import json
import os
import platform
import shutil
import struct
import subprocess
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from diagrams import Diagram, Edge as DiagramEdge, Node, setdiagram
from diagrams.c4 import C4Node, Container, Database, Person, Relationship, System, SystemBoundary

from . import __version__
from .diagnostics import ManifestError
from .models import (
    ArchitectureManifest,
    Boundary,
    Component,
    DiagramDirection,
    Edge,
    EnablementState,
    ImplementationState,
    OutputFormat,
    RoutingStyle,
    Tombstone,
)
from .view_model import SelectedView, select_view

_GRAPHVIZ_CANDIDATES = (
    Path("/opt/homebrew/bin/dot"),
    Path("/usr/local/bin/dot"),
    Path("/usr/bin/dot"),
)
_REQUIRED_DIAGRAMS_VERSION = "0.25.1"
_REQUIRED_PYTHON_GRAPHVIZ_VERSION = "0.20.3"
_REQUIRED_GRAPHVIZ_VERSION = "15.1.1"
_DARK_THEME = {
    "canvas": "#0B1118",
    "canvas_text": "#F2F6FA",
    "cluster_fill": "#111A24",
    "cluster_border": "#566B7D",
    "cluster_text": "#D6E2EA",
    "current_fill": "#172332",
    "current_border": "#6FA8CC",
    "current_text": "#F4F7FA",
    "actor_fill": "#102B28",
    "actor_border": "#43D9AE",
    "actor_text": "#ECFFF8",
    "external_fill": "#2B2017",
    "external_border": "#F0A45D",
    "external_text": "#FFF4E8",
    "future_fill": "#261C35",
    "future_border": "#C49AFA",
    "disabled_fill": "#2B2416",
    "disabled_border": "#E2B75C",
    "disabled_text": "#FFF3D6",
    "store_fill": "#142921",
    "store_border": "#69C7A5",
    "store_text": "#E9FFF7",
    "worker_fill": "#17243A",
    "worker_border": "#78A9F5",
    "worker_text": "#EEF5FF",
    "projection_fill": "#29261D",
    "projection_border": "#D4C484",
    "projection_text": "#FFF9DF",
    "historical_fill": "#24272B",
    "historical_border": "#A9B0B7",
    "historical_text": "#E8EAED",
    "data_edge": "#8DC5E3",
    "data_edge_text": "#B9DDF0",
    "persistence_edge": "#6FD0AC",
    "persistence_edge_text": "#A5E3CD",
    "projection_edge": "#D7C77B",
    "projection_edge_text": "#E8DFAF",
    "failure_edge": "#FF8A80",
    "failure_edge_text": "#FFC1BB",
    "muted_text": "#C7D2DD",
    "badge_enabled": "#164C3E",
    "badge_disabled": "#5B4316",
    "badge_external": "#5A3419",
    "badge_future": "#452B60",
    "badge_historical": "#3D444B",
}
_DIRECTION = {
    DiagramDirection.LEFT_TO_RIGHT: "LR",
    DiagramDirection.TOP_TO_BOTTOM: "TB",
    DiagramDirection.RIGHT_TO_LEFT: "RL",
    DiagramDirection.BOTTOM_TO_TOP: "BT",
}
_ROUTING = {
    RoutingStyle.SPLINE: "spline",
    RoutingStyle.POLYLINE: "polyline",
    RoutingStyle.ORTHO: "ortho",
}
_EDGE_PREFIX = {
    "command": "CMD",
    "query": "REQ",
    "response": "RESP",
    "event": "EVENT",
    "publication": "PUB",
    "subscription_command": "SUB",
    "native_observation": "DATA",
    "callback": "CALLBACK",
    "readiness": "READY",
    "release": "RELEASE",
    "control": "CONTROL",
    "persistence": "PERSIST",
    "notification": "NOTIFY",
    "projection": "PROJECT",
    "timer": "TIMER",
    "queue_admission": "QUEUE",
    "worker_result": "RESULT",
    "failure": "FAILURE",
}


@dataclass(frozen=True, slots=True)
class ToolchainIdentity:
    python: str
    diagrams: str
    python_graphviz: str
    graphviz: str
    dot_path: str


@dataclass(frozen=True, slots=True)
class GenerationResult:
    output_directory: Path
    artifact_count: int
    manifest_sha256: str
    toolchain: ToolchainIdentity


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _generator_sha256() -> str:
    digest = hashlib.sha256()
    source_root = Path(__file__).resolve().parent
    for path in sorted(source_root.glob("*.py")):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _resolve_dot() -> Path:
    for candidate in _GRAPHVIZ_CANDIDATES:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            resolved = candidate.resolve()
            approved_roots = (
                Path("/opt/homebrew/Cellar/graphviz"),
                Path("/usr/local/Cellar/graphviz"),
            )
            if candidate == Path("/usr/bin/dot") or any(
                resolved.is_relative_to(root) for root in approved_roots
            ):
                return resolved
    raise ManifestError(
        "GRAPHVIZ_MISSING",
        "graphviz.dot",
        "no approved Graphviz executable was found; install the pinned project prerequisite",
    )


def _toolchain(dot_path: Path) -> ToolchainIdentity:
    completed = subprocess.run(
        [str(dot_path), "-V"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        env={"PATH": str(dot_path.parent) + ":/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
    )
    output = (completed.stderr or completed.stdout).strip()
    if completed.returncode != 0 or "graphviz version" not in output:
        raise ManifestError("GRAPHVIZ_IDENTITY", "graphviz.dot", "Graphviz identity check failed")
    version = output.split("graphviz version", 1)[1].strip().split(" ", 1)[0]
    diagrams_version = importlib.metadata.version("diagrams")
    python_graphviz_version = importlib.metadata.version("graphviz")
    observed = (diagrams_version, python_graphviz_version, version)
    required = (
        _REQUIRED_DIAGRAMS_VERSION,
        _REQUIRED_PYTHON_GRAPHVIZ_VERSION,
        _REQUIRED_GRAPHVIZ_VERSION,
    )
    if observed != required:
        raise ManifestError(
            "TOOLCHAIN_VERSION",
            "toolchain",
            "installed Diagrams/Python-Graphviz/Graphviz versions do not match the locked contract",
        )
    return ToolchainIdentity(
        python=platform.python_version(),
        diagrams=diagrams_version,
        python_graphviz=python_graphviz_version,
        graphviz=version,
        dot_path=str(dot_path),
    )


def _profile_state(component: Component, profile_id: str | None) -> str:
    if profile_id is None:
        return EnablementState.NOT_APPLICABLE.value
    states = {state.profile: state.enablement.value for state in component.profile_states}
    return states.get(profile_id, EnablementState.NOT_APPLICABLE.value)


def _node_appearance(component: Component, profile_id: str | None) -> dict[str, str]:
    state = _profile_state(component, profile_id)
    attrs = {
        "shape": "box",
        "style": "rounded,filled",
        "fillcolor": _DARK_THEME["current_fill"],
        "color": _DARK_THEME["current_border"],
        "fontcolor": _DARK_THEME["current_text"],
        "penwidth": "1.5",
    }
    if component.kind.value == "markeitech_actor":
        attrs.update(
            fillcolor=_DARK_THEME["actor_fill"],
            color=_DARK_THEME["actor_border"],
            fontcolor=_DARK_THEME["actor_text"],
        )
    elif component.kind.value == "provider":
        attrs.update(shape="box3d")
    elif component.kind.value == "data_store":
        attrs.update(
            shape="cylinder",
            fillcolor=_DARK_THEME["store_fill"],
            color=_DARK_THEME["store_border"],
            fontcolor=_DARK_THEME["store_text"],
        )
    elif component.kind.value in {"queue", "worker"}:
        attrs.update(
            shape="component",
            fillcolor=_DARK_THEME["worker_fill"],
            color=_DARK_THEME["worker_border"],
            fontcolor=_DARK_THEME["worker_text"],
        )
    elif component.kind.value == "projection":
        attrs.update(
            shape="note",
            fillcolor=_DARK_THEME["projection_fill"],
            color=_DARK_THEME["projection_border"],
            fontcolor=_DARK_THEME["projection_text"],
        )
    elif component.kind.value == "operator":
        attrs.update(
            shape="tab",
            fillcolor=_DARK_THEME["projection_fill"],
            color=_DARK_THEME["projection_border"],
            fontcolor=_DARK_THEME["projection_text"],
        )

    if component.implementation_state is ImplementationState.EXTERNAL:
        attrs.update(
            fillcolor=_DARK_THEME["external_fill"],
            color=_DARK_THEME["external_border"],
            fontcolor=_DARK_THEME["external_text"],
        )
    elif component.implementation_state is ImplementationState.FUTURE:
        attrs.update(
            shape="hexagon",
            style="dashed,filled",
            fillcolor=_DARK_THEME["future_fill"],
            color=_DARK_THEME["future_border"],
        )
    elif component.implementation_state in {
        ImplementationState.REMOVED,
        ImplementationState.REJECTED,
    }:
        attrs.update(
            style="dashed,filled",
            fillcolor=_DARK_THEME["historical_fill"],
            color=_DARK_THEME["historical_border"],
            fontcolor=_DARK_THEME["historical_text"],
        )
    elif state == EnablementState.DISABLED.value:
        attrs.update(
            style="dashed,filled",
            fillcolor=_DARK_THEME["disabled_fill"],
            color=_DARK_THEME["disabled_border"],
            fontcolor=_DARK_THEME["disabled_text"],
        )
    return attrs


def _component_badge(component: Component, profile_id: str | None) -> tuple[str, str]:
    state = _profile_state(component, profile_id)
    if component.implementation_state is ImplementationState.EXTERNAL:
        return "EXTERNAL", _DARK_THEME["badge_external"]
    if component.implementation_state is ImplementationState.FUTURE:
        return "FUTURE", _DARK_THEME["badge_future"]
    if component.implementation_state in {
        ImplementationState.REMOVED,
        ImplementationState.REJECTED,
    }:
        return "HISTORICAL", _DARK_THEME["badge_historical"]
    if state == EnablementState.DISABLED.value:
        return "DISABLED", _DARK_THEME["badge_disabled"]
    if state == EnablementState.ENABLED.value:
        return "ENABLED", _DARK_THEME["badge_enabled"]
    return "NOT APPLICABLE", _DARK_THEME["badge_historical"]


def _badge_html(text: str, fill: str, border: str, fontcolor: str) -> str:
    return (
        f'<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="3" '
        f'COLOR="{border}" BGCOLOR="{fill}"><TR><TD><FONT COLOR="{fontcolor}" '
        f'POINT-SIZE="9"><B>{html.escape(text)}</B></FONT></TD></TR></TABLE>'
    )


def _component_card_label(component: Component, profile_id: str | None) -> str:
    appearance = _node_appearance(component, profile_id)
    badge, badge_fill = _component_badge(component, profile_id)
    order = (
        f"ORDER {component.composition_order}"
        if component.composition_order is not None
        else "ORDER NOT APPLICABLE"
    )
    profile = _profile_state(component, profile_id).upper()
    badge_html = _badge_html(
        badge,
        badge_fill,
        appearance["color"],
        appearance["fontcolor"],
    )
    return (
        '<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="3">'
        f'<TR><TD ALIGN="LEFT"><FONT COLOR="{appearance["fontcolor"]}" '
        f'POINT-SIZE="12"><B>{html.escape(component.label)}</B></FONT></TD>'
        f'<TD ALIGN="RIGHT">{badge_html}</TD></TR><HR/>'
        f'<TR><TD COLSPAN="2" ALIGN="LEFT"><FONT COLOR="{_DARK_THEME["muted_text"]}" '
        f'POINT-SIZE="9">{html.escape(component.id)}</FONT></TD></TR>'
        f'<TR><TD COLSPAN="2" ALIGN="LEFT"><FONT COLOR="{appearance["fontcolor"]}" '
        f'POINT-SIZE="9">IMPLEMENTATION: '
        f'{html.escape(component.implementation_state.value.upper())} &#183; COMPOSITION: '
        f'{html.escape(component.composition_policy.value.upper())}</FONT></TD></TR>'
        f'<TR><TD COLSPAN="2" ALIGN="LEFT"><FONT COLOR="{appearance["fontcolor"]}" '
        f'POINT-SIZE="9">PROFILE: {html.escape(profile)} &#183; {order}</FONT></TD></TR>'
        "</TABLE>>"
    )


def _tombstone_card_label(tombstone: Tombstone) -> str:
    badge_html = _badge_html(
        "HISTORICAL",
        _DARK_THEME["badge_historical"],
        _DARK_THEME["historical_border"],
        _DARK_THEME["historical_text"],
    )
    return (
        '<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="3">'
        f'<TR><TD ALIGN="LEFT"><FONT COLOR="{_DARK_THEME["historical_text"]}" '
        f'POINT-SIZE="12"><B>{html.escape(tombstone.label)}</B></FONT></TD>'
        f'<TD ALIGN="RIGHT">{badge_html}</TD></TR><HR/>'
        f'<TR><TD COLSPAN="2" ALIGN="LEFT"><FONT COLOR="{_DARK_THEME["muted_text"]}" '
        f'POINT-SIZE="9">{html.escape(tombstone.id)}</FONT></TD></TR>'
        f'<TR><TD COLSPAN="2" ALIGN="LEFT"><FONT '
        f'COLOR="{_DARK_THEME["historical_text"]}" POINT-SIZE="9">DISPOSITION: '
        f'{html.escape(tombstone.disposition.value.upper())} &#183; FORMER KIND: '
        f'{html.escape(tombstone.former_kind.upper())}</FONT></TD></TR>'
        "</TABLE>>"
    )


def _component_node(component: Component, profile_id: str | None) -> Node:
    attrs = {
        **_node_appearance(component, profile_id),
        "fixedsize": "false",
        "group": component.boundary,
        "height": "0.82",
        "id": component.id,
        "label": _component_card_label(component, profile_id),
        "labelloc": "c",
        "margin": "0.12,0.09",
        "nodeid": component.id,
        "tooltip": component.id,
        "width": "2.7",
    }
    if component.kind.value == "data_store":
        return Database(component.label, **attrs)
    if component.kind.value == "operator":
        return Person(component.label, external=True, **attrs)
    if component.kind.value in {"provider", "projection"}:
        return System(component.label, external=True, **attrs)
    return Container(component.label, **attrs)


def _tombstone_node(tombstone: Tombstone) -> Node:
    return C4Node(
        tombstone.label,
        nodeid=tombstone.id,
        id=tombstone.id,
        label=_tombstone_card_label(tombstone),
        shape="box",
        style="dashed,filled",
        fillcolor=_DARK_THEME["historical_fill"],
        color=_DARK_THEME["historical_border"],
        fontcolor=_DARK_THEME["historical_text"],
        fixedsize="false",
        group=tombstone.former_boundary,
        height="0.82",
        labelloc="c",
        margin="0.12,0.09",
        penwidth="1.5",
        tooltip=tombstone.id,
        width="2.7",
    )


def _edge_appearance(edge: Edge) -> dict[str, str]:
    attrs = {
        "color": _DARK_THEME["data_edge"],
        "fontcolor": _DARK_THEME["data_edge_text"],
        "penwidth": "1.7",
    }
    if edge.category.value in {"failure", "release"}:
        attrs.update(
            color=_DARK_THEME["failure_edge"],
            fontcolor=_DARK_THEME["failure_edge_text"],
            style="dashed",
        )
    elif edge.category.value in {"persistence", "queue_admission", "worker_result"}:
        attrs.update(
            color=_DARK_THEME["persistence_edge"],
            fontcolor=_DARK_THEME["persistence_edge_text"],
        )
    elif edge.category.value in {"projection", "notification"}:
        attrs.update(
            color=_DARK_THEME["projection_edge"],
            fontcolor=_DARK_THEME["projection_edge_text"],
            style="dotted",
        )
    elif not edge.required or edge.enablement_condition is not None:
        attrs.update(style="dashed")
    return attrs


def _edge_label(edge: Edge, manifest: ArchitectureManifest) -> tuple[str, str]:
    contract = next(item for item in manifest.contracts if item.id == edge.contract)
    requirement = "R" if edge.required else "O"
    return f"{requirement} · {_EDGE_PREFIX[edge.category.value]}", contract.label


def _diagram_edge(edge: Edge, manifest: ArchitectureManifest) -> DiagramEdge:
    attrs = _edge_appearance(edge)
    identity, contract_label = _edge_label(edge, manifest)
    attrs.update(
        arrowhead="vee",
        id=edge.id,
        style=attrs.get("style", "solid"),
        tooltip=edge.id,
    )
    return Relationship(
        label=f"{identity} — {contract_label}",
        forward=True,
        **attrs,
    )


def _graph_header(manifest: ArchitectureManifest, selected: SelectedView) -> str:
    view = selected.definition
    statuses: dict[str, tuple[str, str, str]] = {}
    for component in selected.components:
        badge, fill = _component_badge(component, view.profile)
        appearance = _node_appearance(component, view.profile)
        statuses[badge] = (fill, appearance["color"], appearance["fontcolor"])
    if selected.tombstones:
        statuses["HISTORICAL"] = (
            _DARK_THEME["badge_historical"],
            _DARK_THEME["historical_border"],
            _DARK_THEME["historical_text"],
        )
    status_order = ("ENABLED", "DISABLED", "EXTERNAL", "FUTURE", "HISTORICAL")
    status_cells = "".join(
        f'<TD>{_badge_html(label, *statuses[label])}</TD>'
        for label in status_order
        if label in statuses
    )

    edge_groups: list[tuple[str, str]] = []
    categories = {edge.category.value for edge in selected.edges}
    if categories - {
        "failure",
        "release",
        "persistence",
        "queue_admission",
        "worker_result",
        "projection",
        "notification",
    }:
        edge_groups.append(("DATA · SOLID/DASHED", _DARK_THEME["data_edge_text"]))
    if categories & {"persistence", "queue_admission", "worker_result"}:
        edge_groups.append(("PERSIST · SOLID", _DARK_THEME["persistence_edge_text"]))
    if categories & {"projection", "notification"}:
        edge_groups.append(("PROJECT · DOTTED", _DARK_THEME["projection_edge_text"]))
    if categories & {"failure", "release"}:
        edge_groups.append(("FAILURE/RELEASE · DASHED", _DARK_THEME["failure_edge_text"]))
    edge_cells = "".join(
        f'<TD><FONT COLOR="{color}" POINT-SIZE="9"><B>{label}</B></FONT></TD>'
        for label, color in edge_groups
    )
    legend = ""
    if status_cells or edge_cells:
        legend = (
            '<TR><TD ALIGN="LEFT"><TABLE BORDER="0" CELLBORDER="0" CELLSPACING="8" '
            f'CELLPADDING="0"><TR>{status_cells}{edge_cells}'
            f'<TD><FONT COLOR="{_DARK_THEME["muted_text"]}" POINT-SIZE="9">'
            "R = REQUIRED &#183; O = OPTIONAL</FONT></TD></TR></TABLE></TD></TR>"
        )
    profile = html.escape(view.profile or "not applicable")
    return (
        '<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="2">'
        f'<TR><TD ALIGN="LEFT"><FONT COLOR="{_DARK_THEME["canvas_text"]}" '
        f'POINT-SIZE="20"><B>{html.escape(view.label)}</B></FONT></TD></TR>'
        f'<TR><TD ALIGN="LEFT"><FONT COLOR="{_DARK_THEME["failure_edge_text"]}" '
        'POINT-SIZE="11"><B>OFFLINE DOCUMENTATION &#8212; NO CURRENT ORDER SUBMISSION '
        "OR EXECUTION</B></FONT></TD></TR>"
        f'<TR><TD ALIGN="LEFT"><FONT COLOR="{_DARK_THEME["muted_text"]}" '
        f'POINT-SIZE="10">PROFILE: {profile} &#183; REVIEW: '
        f'{html.escape(manifest.header.review_status.value.upper())} &#183; MANIFEST SCHEMA: '
        f'{manifest.header.schema_version} &#183; COMPONENTS: {len(selected.components)} &#183; '
        f'CAPABILITIES: {len(selected.capabilities)} &#183; FLOWS: {len(selected.edges)}'
        "</FONT></TD></TR>"
        f'<TR><TD ALIGN="LEFT"><FONT COLOR="{_DARK_THEME["muted_text"]}" '
        f'POINT-SIZE="9">CHECKOUT EVIDENCE: '
        f'{html.escape(manifest.header.checkout_commit)}</FONT></TD></TR>'
        f"{legend}</TABLE>>"
    )


def _boundary_appearance(boundary: Boundary, has_children: bool) -> dict[str, str]:
    border_by_kind = {
        "actor_runtime": _DARK_THEME["actor_border"],
        "future_governed": _DARK_THEME["future_border"],
        "nautilus_engine": _DARK_THEME["current_border"],
        "persistence": _DARK_THEME["persistence_edge"],
        "projection": _DARK_THEME["projection_edge"],
        "provider": _DARK_THEME["external_border"],
        "worker": _DARK_THEME["worker_border"],
    }
    border = border_by_kind.get(boundary.kind.value, _DARK_THEME["cluster_border"])
    fill = "#0E1721" if has_children else _DARK_THEME["cluster_fill"]
    label = (
        f'<<FONT COLOR="{_DARK_THEME["cluster_text"]}" POINT-SIZE="11"><B>'
        f'{html.escape(boundary.label.upper())}</B></FONT><BR ALIGN="LEFT"/>'
        f'<FONT COLOR="{_DARK_THEME["muted_text"]}" POINT-SIZE="8">'
        f'{html.escape(boundary.kind.value.upper())}</FONT>>'
    )
    return {
        "bgcolor": fill,
        "color": border,
        "fontcolor": _DARK_THEME["cluster_text"],
        "fontname": "Helvetica",
        "fontsize": "11",
        "id": boundary.id,
        "label": label,
        "margin": "20" if has_children else "14",
        "pencolor": border,
        "penwidth": "1.4" if has_children else "1.0",
        "style": "rounded",
    }


def _build_dot(manifest: ArchitectureManifest, selected: SelectedView) -> str:
    view = selected.definition
    if view.routing is RoutingStyle.PENDING_APPROVAL:
        raise ManifestError("VIEW_ROUTING_UNAPPROVED", view.id, "view routing is not approved")
    diagram = Diagram(
        view.label,
        filename=view.id,
        direction=_DIRECTION[view.direction],
        outformat="dot",
        show=False,
        curvestyle="ortho" if view.routing is RoutingStyle.ORTHO else "curved",
        graph_attr={
            "bgcolor": _DARK_THEME["canvas"],
            "fontcolor": _DARK_THEME["canvas_text"],
            "fontname": "Helvetica",
            "fontsize": "18",
            "forcelabels": "true",
            "label": _graph_header(manifest, selected),
            "labeljust": "l",
            "labelloc": "t",
            "margin": "0.15",
            "nodesep": "0.45",
            "outputorder": "edgesfirst",
            "overlap": "false",
            "pack": "true",
            "packmode": (
                f"array_u{view.grid_columns}" if view.pack_mode == "array" else "graph"
            ),
            "pad": "0.35",
            "ranksep": "0.85",
            "splines": _ROUTING[view.routing],
        },
        node_attr={
            "fixedsize": "false",
            "fontcolor": _DARK_THEME["current_text"],
            "fontname": "Helvetica",
            "fontsize": str(view.minimum_text_size_pt or 10),
            "height": "0.9",
            "margin": "0.12,0.08",
            "width": "2.2",
        },
        edge_attr={
            "arrowsize": "0.8",
            "color": _DARK_THEME["data_edge"],
            "fontcolor": _DARK_THEME["data_edge_text"],
            "fontname": "Helvetica",
            "fontsize": str(max(8, (view.minimum_text_size_pt or 10) - 1)),
        },
    )
    diagram.dot.graph_attr["splines"] = _ROUTING[view.routing]
    components_by_boundary: dict[str, list[Component]] = defaultdict(list)
    for component in selected.components:
        components_by_boundary[component.boundary].append(component)
    tombstones_by_boundary: dict[str, list[Tombstone]] = defaultdict(list)
    for tombstone in selected.tombstones:
        tombstones_by_boundary[tombstone.former_boundary].append(tombstone)
    boundaries = {boundary.id: boundary for boundary in selected.boundaries}
    children_by_boundary: dict[str, list[str]] = defaultdict(list)
    for boundary in selected.boundaries:
        if boundary.parent in boundaries:
            children_by_boundary[boundary.parent].append(boundary.id)
    root_boundaries = sorted(
        boundary.id
        for boundary in selected.boundaries
        if boundary.parent not in boundaries
    )
    nodes: dict[str, Node] = {}

    def render_boundary(boundary_id: str) -> None:
        boundary = boundaries[boundary_id]
        child_ids = sorted(children_by_boundary[boundary_id])
        with SystemBoundary(
            boundary.label,
            **_boundary_appearance(boundary, bool(child_ids)),
        ):
            for component in sorted(
                components_by_boundary[boundary_id], key=lambda item: item.id
            ):
                nodes[component.id] = _component_node(component, view.profile)
            for tombstone in sorted(
                tombstones_by_boundary[boundary_id], key=lambda item: item.id
            ):
                nodes[tombstone.id] = _tombstone_node(tombstone)
            for child_id in child_ids:
                render_boundary(child_id)

    setdiagram(diagram)
    try:
        for boundary_id in root_boundaries:
            render_boundary(boundary_id)
        if view.pack_mode == "array":
            boundary_ids = sorted(set(components_by_boundary) | set(tombstones_by_boundary))
            for boundary_id in boundary_ids:
                ordered_ids = sorted(
                    [item.id for item in components_by_boundary[boundary_id]]
                    + [item.id for item in tombstones_by_boundary[boundary_id]]
                )
                for first, second in zip(ordered_ids, ordered_ids[1:], strict=False):
                    diagram.dot.edge(
                        first,
                        second,
                        style="invis",
                        weight="100",
                        id=f"layout.{first}.{second}",
                    )
        for edge in selected.edges:
            diagram.connect(
                nodes[edge.source],
                nodes[edge.target],
                _diagram_edge(edge, manifest),
            )
    finally:
        setdiagram(None)
    return diagram.dot.source


def _markdown(manifest: ArchitectureManifest, selected: SelectedView) -> str:
    view = selected.definition
    lines = [
        f"# {view.label}",
        "",
        "> Offline architecture documentation. No current order submission or execution.",
        "",
        view.purpose,
        "",
        f"- View ID: `{view.id}`",
        f"- Profile: `{view.profile or 'not applicable'}`",
        f"- Manifest: `{manifest.header.id}` schema {manifest.header.schema_version}",
        f"- Checkout evidence: `{manifest.header.checkout_commit}`",
        f"- Review status: `{manifest.header.review_status.value}`",
        "",
        "## Components",
        "",
        "| ID | Component | Kind | Implementation | Composition | Order | "
        "Active profile | Semantic owner | Boundary |",
        "|---|---|---|---|---|---:|---|---|---|",
    ]
    for component in selected.components:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{component.id}`",
                    component.label,
                    component.kind.value,
                    component.implementation_state.value,
                    component.composition_policy.value,
                    str(component.composition_order or "not applicable"),
                    _profile_state(component, view.profile),
                    f"`{component.semantic_owner}`",
                    f"`{component.boundary}`",
                )
            )
            + " |"
        )
    if selected.capabilities:
        lines.extend(
            (
                "",
                "## Configuration-gated capabilities",
                "",
                "| ID | Owning component | Capability | Implementation | Composition | "
                "Active profile | Configuration |",
                "|---|---|---|---|---|---|---|",
            )
        )
        for capability in selected.capabilities:
            lines.append(
                "| "
                + " | ".join(
                    (
                        f"`{capability.id}`",
                        f"`{capability.component}`",
                        capability.label,
                        capability.implementation_state.value,
                        capability.composition_policy.value,
                        capability.enablement.value,
                        capability.configuration_path or "not applicable",
                    )
                )
                + " |"
            )
    if selected.tombstones:
        lines.extend(
            (
                "",
                "## Historical removed or rejected identities",
                "",
                "| ID | Former component | Disposition | Former boundary | Removed at commit |",
                "|---|---|---|---|---|",
            )
        )
        for tombstone in selected.tombstones:
            lines.append(
                "| "
                + " | ".join(
                    (
                        f"`{tombstone.id}`",
                        tombstone.label,
                        tombstone.disposition.value,
                        f"`{tombstone.former_boundary}`",
                        f"`{tombstone.removed_at_commit}`",
                    )
                )
                + " |"
            )
    lines.extend(
        (
            "",
            "## Flows",
            "",
            "| ID | Source | Target | Category | Contract | Transport | Required | "
            "Condition | Delivery |",
            "|---|---|---|---|---|---|---|---|---|",
        )
    )
    claims = {claim.id: claim for claim in manifest.delivery_claims}
    for edge in selected.edges:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{edge.id}`",
                    f"`{edge.source}`",
                    f"`{edge.target}`",
                    edge.category.value,
                    f"`{edge.contract}`",
                    edge.transport.value,
                    "yes" if edge.required else "no",
                    edge.enablement_condition or "always",
                    claims[edge.delivery_claim].guarantee.value,
                )
            )
            + " |"
        )
    lines.extend(("", "## Limitations", ""))
    for limitation in (*manifest.header.limitations, *view.limitations):
        lines.append(f"- {limitation}")
    lines.extend(
        (
            "",
            "## Visual grammar",
            "",
            "- Node text carries implementation, composition, and active-profile status; "
            "color is supplementary.",
            "- The graphical DOT/SVG/PNG view uses the manifest-selected opaque dark theme; "
            "Markdown appearance follows the reviewer's viewer settings.",
            "- Graphical cards, relationships, and nested boundaries use Diagrams C4 "
            "primitives with escaped Graphviz-native labels and no external assets.",
            "- Dashed nodes are disabled, historical, rejected, or future, as stated "
            "in their text.",
            "- Edge labels state category, required/optional status, and carried contract.",
            "- External projections consume canonical state; they do not create market truth.",
            "- The diagram is generated from the validated TOML manifest and is never "
            "an authority itself.",
            "",
        )
    )
    return "\n".join(lines)


def _run_dot(dot_path: Path, dot_file: Path, output_file: Path, output_format: str) -> None:
    completed = subprocess.run(
        [str(dot_path), f"-T{output_format}", str(dot_file), "-o", str(output_file)],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
        env={"PATH": str(dot_path.parent) + ":/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
    )
    if completed.returncode != 0:
        raise ManifestError(
            "GRAPHVIZ_RENDER",
            dot_file.name,
            f"Graphviz failed while producing {output_format}",
        )


def _validate_artifact_set(directory: Path, expected: tuple[str, ...]) -> None:
    actual = tuple(sorted(path.name for path in directory.iterdir() if path.is_file()))
    if actual != tuple(sorted(expected)):
        raise ManifestError(
            "OUTPUT_INCOMPLETE",
            str(directory),
            "generated artifact set is incomplete",
        )
    for path in directory.iterdir():
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            raise ManifestError(
                "OUTPUT_INVALID", path.name, "generated artifact is unsafe or empty"
            )
        if path.suffix == ".svg":
            source = path.read_text(encoding="utf-8")
            remote_reference = 'href="http://' in source or 'href="https://' in source
            if "<svg" not in source or "<image" in source or remote_reference:
                raise ManifestError(
                    "OUTPUT_SVG",
                    path.name,
                    "SVG is invalid or references an external resource",
                )
        elif path.suffix == ".png":
            with path.open("rb") as file:
                header = file.read(24)
            if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
                raise ManifestError("OUTPUT_PNG", path.name, "PNG header is invalid")
            width, height = struct.unpack(">II", header[16:24])
            if width == 0 or height == 0:
                raise ManifestError("OUTPUT_PNG", path.name, "PNG dimensions are invalid")


def _png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as file:
        header = file.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ManifestError("OUTPUT_PNG", path.name, "PNG header is invalid")
    return struct.unpack(">II", header[16:24])


def generate_all(
    manifest: ArchitectureManifest,
    *,
    manifest_path: Path,
    output_directory: Path,
) -> GenerationResult:
    dot_path = _resolve_dot()
    toolchain = _toolchain(dot_path)
    output_parent = output_directory.parent
    output_parent.mkdir(parents=True, exist_ok=True)
    if output_directory.is_symlink() or output_parent.is_symlink():
        raise ManifestError(
            "OUTPUT_UNSAFE_PATH",
            str(output_directory),
            "output path cannot be a symlink",
        )
    staging = Path(tempfile.mkdtemp(prefix=".system-dataflow-staging-", dir=output_parent))
    backup = output_parent / ".system-dataflow-previous"
    try:
        if output_directory.exists() and not output_directory.is_dir():
            raise ManifestError(
                "OUTPUT_UNSAFE_PATH",
                str(output_directory),
                "existing output must be a directory",
            )
        if backup.exists() and not output_directory.exists():
            backup.replace(output_directory)
        elif backup.exists():
            shutil.rmtree(backup)
        expected: list[str] = []
        view_index: list[dict[str, object]] = []
        for view in manifest.views:
            selected = select_view(manifest, view.id)
            stem = view.id.removeprefix("view.")
            dot_file = staging / f"{stem}.dot"
            markdown_file = staging / f"{stem}.md"
            dot_file.write_text(_build_dot(manifest, selected), encoding="utf-8")
            markdown_file.write_text(_markdown(manifest, selected), encoding="utf-8")
            _run_dot(dot_path, dot_file, staging / f"{stem}.svg", "svg")
            _run_dot(dot_path, dot_file, staging / f"{stem}.png", "png")
            width, height = _png_dimensions(staging / f"{stem}.png")
            if view.target_width_px is not None and width > view.target_width_px:
                raise ManifestError(
                    "VIEW_WIDTH_BUDGET",
                    view.id,
                    f"rendered width {width}px exceeds approved maximum {view.target_width_px}px",
                )
            if view.target_height_px is not None and height > view.target_height_px:
                raise ManifestError(
                    "VIEW_HEIGHT_BUDGET",
                    view.id,
                    f"rendered height {height}px exceeds approved maximum "
                    f"{view.target_height_px}px",
                )
            expected.extend(f"{stem}.{suffix}" for suffix in ("dot", "md", "png", "svg"))
            view_index.append(
                {
                    "id": view.id,
                    "nodes": len(selected.components) + len(selected.tombstones),
                    "capabilities": len(selected.capabilities),
                    "edges": len(selected.edges),
                    "files": [f"{stem}.{suffix}" for suffix in ("dot", "md", "png", "svg")],
                }
            )
        manifest_sha256 = _sha256(manifest_path)
        index = {
            "authority": (
                "generated documentation only; canonical content is the validated TOML manifest"
            ),
            "manifest": manifest.header.id,
            "manifest_sha256": manifest_sha256,
            "checkout_commit": manifest.header.checkout_commit,
            "generator_contract_version": manifest.header.generator_contract_version,
            "generator_version": __version__,
            "generator_sha256": _generator_sha256(),
            "theme": {
                "id": "style.theme",
                "label": next(
                    style.label for style in manifest.styles if style.id == "style.theme"
                ),
            },
            "toolchain": {
                "python": toolchain.python,
                "diagrams": toolchain.diagrams,
                "python_graphviz": toolchain.python_graphviz,
                "graphviz": toolchain.graphviz,
                "platform": {
                    "system": platform.system(),
                    "release": platform.release(),
                    "machine": platform.machine(),
                },
                "font": "Helvetica resolved by Graphviz/system; byte portability is not claimed",
            },
            "views": view_index,
        }
        index_path = staging / "artifact-index.json"
        index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        expected.append(index_path.name)
        hashes_path = staging / "SHA256SUMS"
        hash_lines = [
            f"{_sha256(staging / name)}  {name}" for name in sorted(expected)
        ]
        hashes_path.write_text("\n".join(hash_lines) + "\n", encoding="utf-8")
        expected.append(hashes_path.name)
        _validate_artifact_set(staging, tuple(expected))

        if output_directory.exists():
            output_directory.replace(backup)
        staging.replace(output_directory)
        if backup.exists():
            shutil.rmtree(backup)
        return GenerationResult(
            output_directory=output_directory,
            artifact_count=len(expected),
            manifest_sha256=manifest_sha256,
            toolchain=toolchain,
        )
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        if backup.exists() and not output_directory.exists():
            backup.replace(output_directory)
        raise
