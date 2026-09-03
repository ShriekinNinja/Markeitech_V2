from __future__ import annotations

import ast
import html
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from markeitech_api_docs.metadata import parse_metadata_docstring
from markeitech_api_docs.models import ApiDocsError, AttributeRegistry, SourceSnapshot
from markeitech_api_docs.registry import sha256_bytes, sha256_file
from markeitech_api_docs.source import source_snapshot_signature

SCHEMA_ID = "markeitech-architecture-class-components"
SCHEMA_VERSION = 1
ARCHITECTURE_PREFIX = "architecture.component."
REQUIRED_FIELDS = frozenset(
    {
        "architecture.component.id",
        "architecture.component.label",
        "architecture.component.kind",
        "architecture.component.boundary",
    }
)
OPTIONAL_FIELDS = frozenset({"architecture.component.responsibilities"})
APPROVED_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS


@dataclass(frozen=True)
class ComponentDocsProjection:
    payload: dict[str, Any]
    markdown: str


def _module_path(source: Path, source_root: Path) -> str:
    relative = source.relative_to(source_root)
    parts = list(relative.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(["markeitech", *parts])


def _docstring_node(node: ast.ClassDef) -> ast.Constant | None:
    if not node.body:
        return None
    first = node.body[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return first.value
    return None


def _typed_fields(occurrences: tuple[Any, ...], object_path: str) -> dict[str, Any]:
    architecture = [
        occurrence
        for occurrence in occurrences
        if occurrence.key is not None and occurrence.key.startswith(ARCHITECTURE_PREFIX)
    ]
    if not architecture:
        return {}
    if any(occurrence.status != "typed_exposed" for occurrence in architecture):
        raise ApiDocsError(
            f"ARCHITECTURE_METADATA_INVALID: invalid declaration on {object_path}"
        )
    values = {occurrence.key: occurrence.typed_value for occurrence in architecture}
    if set(values) - APPROVED_FIELDS:
        raise ApiDocsError(
            f"ARCHITECTURE_METADATA_INVALID: unapproved field on {object_path}"
        )
    missing = REQUIRED_FIELDS - set(values)
    if missing:
        raise ApiDocsError(
            f"ARCHITECTURE_METADATA_INCOMPLETE: required field missing on {object_path}"
        )
    return values


def _markdown_text(value: str) -> str:
    escaped = html.escape(value, quote=False)
    for token in ("\\", "|", "*", "_", "[", "]", "#"):
        escaped = escaped.replace(token, f"\\{token}")
    return escaped


def _code(value: str) -> str:
    if "`" in value or "\n" in value:
        raise ApiDocsError("ARCHITECTURE_METADATA_INVALID: unsafe code identity")
    return f"`{value}`"


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Architecture Components",
        "",
        "> Generated from validated architecture declarations in V2 class docstrings. ",
        "> This page is not a Python call graph and does not prove runtime calls, delivery, ",
        "> acceptance, ownership, or completeness of the whole system architecture.",
        "",
        "These implementation-backed components are documented separately from the supported ",
        "public API denominator. Incoming/outgoing relationships, contracts, non-Python ",
        "components, status, and evidence remain deferred to a separately reviewed source schema.",
        "",
        "| Component | Python class | Kind | Boundary | Responsibilities |",
        "|---|---|---|---|---|",
    ]
    for component in payload["components"]:
        responsibilities = component["responsibilities"]
        rendered_responsibilities = (
            "<br>".join(_markdown_text(value) for value in responsibilities)
            if responsibilities
            else "Not yet declared"
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    f"{_code(component['id'])}<br>{_markdown_text(component['label'])}",
                    _code(component["object_path"]),
                    _code(component["kind"]),
                    _code(component["boundary"]),
                    rendered_responsibilities,
                ]
            )
            + " |"
        )

    lines.extend(["", "## Class Reference", ""])
    for component in payload["components"]:
        lines.extend(
            [
                f"### {_code(component['id'])} — {_markdown_text(component['label'])}",
                "",
                f"::: {component['object_path']}",
                "",
            ]
        )
    return "\n".join(lines)


def build_component_docs_projection(
    *,
    repository_root: Path,
    source_root: Path,
    registry: AttributeRegistry,
    snapshot: SourceSnapshot,
) -> ComponentDocsProjection:
    components: list[dict[str, Any]] = []
    seen_ids: dict[str, str] = {}

    for source in sorted(source_root.rglob("*.py")):
        relative_source = source.relative_to(repository_root).as_posix()
        try:
            tree = ast.parse(source.read_text(encoding="utf-8"), filename=relative_source)
        except SyntaxError as exc:
            raise ApiDocsError("SOURCE_PARSE_FAILED: V2 source is invalid") from exc
        module = _module_path(source, source_root)
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            doc_node = _docstring_node(node)
            if doc_node is None:
                continue
            raw_docstring = ast.get_docstring(node, clean=True)
            if raw_docstring is None:
                continue
            if ARCHITECTURE_PREFIX not in raw_docstring:
                continue
            object_path = f"{module}.{node.name}"
            parsed = parse_metadata_docstring(
                raw_docstring,
                registry=registry,
                object_path=object_path,
                source=relative_source,
                base_line=doc_node.lineno,
            )
            if any(
                occurrence.status not in {"typed_exposed", "typed_hidden"}
                for occurrence in parsed.occurrences
            ):
                raise ApiDocsError(
                    f"ARCHITECTURE_METADATA_INVALID: rejected declaration on {object_path}"
                )
            fields = _typed_fields(parsed.occurrences, object_path)
            if not fields:
                continue
            component_id = str(fields["architecture.component.id"])
            if component_id in seen_ids:
                raise ApiDocsError(
                    "ARCHITECTURE_ID_CONFLICT: component identity declared more than once"
                )
            seen_ids[component_id] = object_path
            responsibilities = fields.get("architecture.component.responsibilities", [])
            if not isinstance(responsibilities, list):
                raise ApiDocsError(
                    f"ARCHITECTURE_METADATA_INVALID: responsibilities on {object_path}"
                )
            normalized = {
                "id": component_id,
                "label": str(fields["architecture.component.label"]),
                "kind": str(fields["architecture.component.kind"]),
                "boundary": str(fields["architecture.component.boundary"]),
                "responsibilities": [str(value) for value in responsibilities],
                "object_path": object_path,
                "implementation_ref": f"{relative_source}:{node.name}",
                "source": relative_source,
                "definition_line": node.lineno,
                "source_sha256": sha256_file(source),
            }
            normalized["record_sha256"] = sha256_bytes(
                json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
            )
            components.append(normalized)

    components.sort(key=lambda item: item["id"])
    with_responsibilities = sum(bool(item["responsibilities"]) for item in components)
    payload: dict[str, Any] = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "authority": "source_documentation_component_declarations",
        "evidence_class": "author_declared_source_architecture",
        "analysis_mode": "static_ast",
        "not_runtime_configuration": True,
        "limitations": [
            "This index covers implementation-backed class components only.",
            "A source declaration does not prove runtime calls, delivery, or acceptance.",
            "Relationships, contracts, non-Python components, status, and diagram generation "
            "are not implemented in this schema.",
        ],
        "source_snapshot_sha256": source_snapshot_signature(snapshot),
        "registry": {
            "id": registry.registry_id,
            "version": registry.registry_version,
            "sha256": registry.source_sha256,
        },
        "counts": {
            "components": len(components),
            "with_responsibilities": with_responsibilities,
            "without_responsibilities": len(components) - with_responsibilities,
        },
        "components": components,
    }
    return ComponentDocsProjection(payload=payload, markdown=_render_markdown(payload))
