from __future__ import annotations

import ast
import json
import os
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

import griffe

from markeitech_api_docs.griffe_extension import MarkeitechMetadataExtension
from markeitech_api_docs.models import (
    ApiDocsError,
    ApiIndex,
    AttributeRegistry,
    PublicApiEntry,
    PublicSurfaceRegistry,
    SourceFileIdentity,
    SourceSnapshot,
)
from markeitech_api_docs.registry import sha256_bytes, sha256_file

INDEX_SCHEMA_ID = "markeitech-api-metadata-index"
INDEX_SCHEMA_VERSION = 1
MAX_SOURCE_FILES = 1000
MAX_SOURCE_BYTES = 100 * 1024 * 1024


def load_static_package(
    source_root: Path,
    registry: AttributeRegistry,
) -> tuple[griffe.Module, MarkeitechMetadataExtension]:
    extension = MarkeitechMetadataExtension(registry)
    extensions = griffe.load_extensions(extension)
    package = griffe.load(
        "markeitech",
        search_paths=[source_root],
        extensions=extensions,
        docstring_parser="google",
        allow_inspection=False,
        force_inspection=False,
        resolve_aliases=True,
        resolve_external=False,
        try_relative_path=False,
    )
    if not isinstance(package, griffe.Module) or package.analysis != "static":
        raise ApiDocsError("STATIC_LOAD_FAILED: markeitech did not resolve as a static module")
    return package, extension


def literal_all(path: Path) -> tuple[str, ...]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        raise ApiDocsError("SOURCE_PARSE_FAILED: package initializer is invalid") from exc

    declarations: list[tuple[str, ...]] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        declares_all = any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        )
        if not declares_all:
            continue
        if not isinstance(node.value, (ast.List, ast.Tuple)):
            raise ApiDocsError("PUBLIC_SURFACE_INVALID: __all__ must be a literal list or tuple")
        names: list[str] = []
        for item in node.value.elts:
            if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
                raise ApiDocsError("PUBLIC_SURFACE_INVALID: __all__ entries must be literal text")
            names.append(item.value)
        declarations.append(tuple(names))

    if len(declarations) != 1:
        raise ApiDocsError("PUBLIC_SURFACE_INVALID: exactly one literal __all__ is required")
    names = declarations[0]
    if len(names) != len(set(names)):
        raise ApiDocsError("PUBLIC_SURFACE_INVALID: duplicate __all__ export")
    return names


def exports_digest(names: tuple[str, ...]) -> str:
    return sha256_bytes(("\n".join(names) + "\n").encode())


def _repository_relative(path: Path, repository_root: Path) -> str:
    resolved = path.resolve()
    root = repository_root.resolve()
    if not resolved.is_relative_to(root):
        raise ApiDocsError("SOURCE_SCOPE_DENIED: object source is outside the repository")
    return resolved.relative_to(root).as_posix()


def _object_source_path(obj: griffe.Object, repository_root: Path) -> str:
    filepath = obj.filepath
    if isinstance(filepath, list):
        if len(filepath) != 1:
            raise ApiDocsError("SOURCE_IDENTITY_INVALID: namespace packages are unsupported")
        filepath = filepath[0]
    return _repository_relative(Path(filepath), repository_root)


def _target(obj: griffe.Object | griffe.Alias) -> griffe.Object:
    if isinstance(obj, griffe.Alias):
        target = obj.final_target
        if not isinstance(target, griffe.Object):
            raise ApiDocsError("PUBLIC_ALIAS_UNRESOLVED: alias target is not a static object")
        return target
    return obj


def _lookup(package: griffe.Module, path: str) -> griffe.Object | griffe.Alias:
    prefix = "markeitech."
    if not path.startswith(prefix):
        raise ApiDocsError("PUBLIC_SURFACE_INVALID: object must be under markeitech")
    try:
        value = package[path.removeprefix(prefix)]
    except (KeyError, ValueError) as exc:
        raise ApiDocsError("PUBLIC_OBJECT_MISSING: selected object was not found") from exc
    if not isinstance(value, (griffe.Object, griffe.Alias)):
        raise ApiDocsError("PUBLIC_OBJECT_INVALID: selected value is not documentable")
    return value


def build_public_entries(
    *,
    package: griffe.Module,
    surface: PublicSurfaceRegistry,
    repository_root: Path,
) -> tuple[PublicApiEntry, ...]:
    entries: list[PublicApiEntry] = []
    seen_exposed: set[str] = set()

    for policy in surface.packages:
        source_path = repository_root / policy.source
        names = literal_all(source_path)
        if len(names) != policy.expected_export_count:
            raise ApiDocsError("PUBLIC_SURFACE_DRIFT: export count changed")
        if exports_digest(names) != policy.expected_exports_sha256:
            raise ApiDocsError("PUBLIC_SURFACE_DRIFT: ordered exports changed")
        module = _lookup(package, policy.module)
        module = _target(module)
        if not isinstance(module, griffe.Module):
            raise ApiDocsError("PUBLIC_SURFACE_INVALID: package policy target is not a module")

        for name in names:
            exposed = f"{policy.module}.{name}"
            if exposed in seen_exposed:
                raise ApiDocsError("PUBLIC_SURFACE_INVALID: duplicate exposed identity")
            seen_exposed.add(exposed)
            try:
                surface_object = module.members[name]
            except KeyError as exc:
                raise ApiDocsError("PUBLIC_OBJECT_MISSING: export has no static object") from exc
            target = _target(surface_object)
            source = _object_source_path(target, repository_root)
            if not source.startswith("v2/src/markeitech/"):
                raise ApiDocsError("PUBLIC_ALIAS_EXTERNAL: export resolves outside V2 source")
            metadata = target.extra.get("markeitech", {}).get("metadata", [])
            occurrence_ids = tuple(
                str(item["occurrence_id"]) for item in metadata if isinstance(item, dict)
            )
            entries.append(
                PublicApiEntry(
                    exposed=exposed,
                    canonical=target.path,
                    kind=target.kind.value,
                    source=source,
                    definition_line=target.lineno,
                    alias=isinstance(surface_object, griffe.Alias),
                    has_docstring=bool(target.docstring and target.docstring.value.strip()),
                    metadata_occurrence_ids=occurrence_ids,
                    inclusion_reason=f"literal export from {policy.module}.__all__",
                )
            )

    for item in surface.explicit:
        if item.exposed in seen_exposed:
            raise ApiDocsError("PUBLIC_SURFACE_INVALID: duplicate explicit exposed identity")
        seen_exposed.add(item.exposed)
        surface_object = _lookup(package, item.canonical)
        target = _target(surface_object)
        source = _object_source_path(target, repository_root)
        if source != item.source:
            raise ApiDocsError("PUBLIC_SURFACE_DRIFT: explicit object source changed")
        if target.kind.value != item.kind:
            raise ApiDocsError("PUBLIC_SURFACE_DRIFT: explicit object kind changed")
        metadata = target.extra.get("markeitech", {}).get("metadata", [])
        occurrence_ids = tuple(
            str(value["occurrence_id"]) for value in metadata if isinstance(value, dict)
        )
        entries.append(
            PublicApiEntry(
                exposed=item.exposed,
                canonical=target.path,
                kind=target.kind.value,
                source=source,
                definition_line=target.lineno,
                alias=isinstance(surface_object, griffe.Alias),
                has_docstring=bool(target.docstring and target.docstring.value.strip()),
                metadata_occurrence_ids=occurrence_ids,
                inclusion_reason=item.reason,
            )
        )

    return tuple(sorted(entries, key=lambda value: value.exposed))


def documentation_input_paths(repository_root: Path, tool_root: Path) -> tuple[Path, ...]:
    paths = list((repository_root / "v2" / "src" / "markeitech").rglob("*.py"))
    paths.extend((tool_root / "src").rglob("*.py"))
    paths.extend((tool_root / "docs").rglob("*.md"))
    paths.extend((tool_root / "docs").rglob("*.css"))
    paths.extend((tool_root / "schema").rglob("*.toml"))
    paths.extend(
        [
            tool_root / "pyproject.toml",
            tool_root / "uv.lock",
            tool_root / "mkdocs.yml",
        ]
    )
    unique = tuple(sorted({path.resolve() for path in paths}))
    if len(unique) > MAX_SOURCE_FILES:
        raise ApiDocsError("SOURCE_LIMIT_EXCEEDED: too many documentation inputs")
    total = sum(path.stat().st_size for path in unique)
    if total > MAX_SOURCE_BYTES:
        raise ApiDocsError("SOURCE_LIMIT_EXCEEDED: documentation inputs are too large")
    return unique


def _git_output(repository_root: Path, *args: str) -> str:
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "LANG": "C",
        "LC_ALL": "C",
    }
    result = subprocess.run(
        ["git", *args],
        cwd=repository_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise ApiDocsError("GIT_IDENTITY_FAILED: source revision could not be established")
    return result.stdout.strip()


def capture_source_snapshot(repository_root: Path, tool_root: Path) -> SourceSnapshot:
    commit = _git_output(repository_root, "rev-parse", "HEAD")
    if not len(commit) == 40 or any(value not in "0123456789abcdef" for value in commit):
        raise ApiDocsError("GIT_IDENTITY_FAILED: HEAD is not a full commit identity")
    status = _git_output(
        repository_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--",
        "v2/src/markeitech",
        "tools/api-docs",
    )
    status_lines = tuple(line for line in status.splitlines() if line)
    files = tuple(
        SourceFileIdentity(
            path=_repository_relative(path, repository_root),
            sha256=sha256_file(path),
            size_bytes=path.stat().st_size,
        )
        for path in documentation_input_paths(repository_root, tool_root)
    )
    return SourceSnapshot(
        commit=commit,
        state="dirty" if status_lines else "clean",
        dirty_path_count=len(status_lines),
        dirty_state_sha256=sha256_bytes("\n".join(status_lines).encode())
        if status_lines
        else None,
        files=files,
    )


def source_snapshot_signature(snapshot: SourceSnapshot) -> str:
    return sha256_bytes(
        json.dumps(snapshot.to_dict(), sort_keys=True, separators=(",", ":")).encode()
    )


def build_api_index(
    *,
    repository_root: Path,
    tool_root: Path,
    snapshot: SourceSnapshot,
    surface: PublicSurfaceRegistry,
    attributes: AttributeRegistry,
) -> ApiIndex:
    source_root = repository_root / "v2" / "src"
    package, extension = load_static_package(source_root, attributes)
    entries = build_public_entries(
        package=package,
        surface=surface,
        repository_root=repository_root,
    )

    selected_paths = {entry.canonical for entry in entries}
    occurrences_by_id: dict[str, dict[str, Any]] = {}
    for path in selected_paths:
        for item in extension.occurrences_by_object.get(path, ()):
            occurrence_id = str(item["occurrence_id"])
            if occurrence_id in occurrences_by_id and occurrences_by_id[occurrence_id] != item:
                raise ApiDocsError("METADATA_IDENTITY_CONFLICT: occurrence identity collided")
            occurrences_by_id[occurrence_id] = item

    occurrence_counts = Counter(str(item["status"]) for item in occurrences_by_id.values())
    documented = sum(entry.has_docstring for entry in entries)
    payload: dict[str, Any] = {
        "schema_id": INDEX_SCHEMA_ID,
        "schema_version": INDEX_SCHEMA_VERSION,
        "authority": "non_authoritative_discovery_only",
        "not_runtime_configuration": True,
        "limitations": [
            "Static author declarations are not runtime observations.",
            "API visibility is not architecture membership or completeness.",
            "Relationship metadata is not approved in this registry version.",
            "Generated architecture manifests and diagrams are not implemented by this tool.",
        ],
        "source_snapshot": snapshot.to_dict(),
        "source_snapshot_sha256": source_snapshot_signature(snapshot),
        "registries": {
            "public_surface": {
                "id": surface.registry_id,
                "version": surface.registry_version,
                "schema_version": surface.schema_version,
                "sha256": surface.source_sha256,
                "selection_policy": surface.selection_policy,
            },
            "attributes": {
                "id": attributes.registry_id,
                "version": attributes.registry_version,
                "schema_version": attributes.schema_version,
                "sha256": attributes.source_sha256,
                "approved_field_count": len(attributes.fields),
            },
        },
        "public_surface": {
            "expected": len(entries),
            "selected": len(entries),
            "documented": documented,
            "missing_docstring": len(entries) - documented,
            "parse_failed": 0,
            "unresolved_alias": 0,
            "entries": [entry.to_dict() for entry in entries],
        },
        "metadata": {
            "occurrence_count": len(occurrences_by_id),
            "status_counts": dict(sorted(occurrence_counts.items())),
            "occurrences": [
                occurrences_by_id[key] for key in sorted(occurrences_by_id)
            ],
        },
    }
    return ApiIndex(
        payload=payload,
        protected_literals=tuple(dict.fromkeys(extension.protected_literals)),
    )
