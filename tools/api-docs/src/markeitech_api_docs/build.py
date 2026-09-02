from __future__ import annotations

import importlib.metadata
import json
import os
import re
import shutil
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from mkdocs.commands.build import build as mkdocs_build
from mkdocs.config import load_config

from markeitech_api_docs import __version__
from markeitech_api_docs.component_docs import build_component_docs_projection
from markeitech_api_docs.models import ApiDocsError, ApiIndex, SourceSnapshot
from markeitech_api_docs.registry import (
    load_attribute_registry,
    load_public_surface_registry,
    sha256_bytes,
    sha256_file,
)
from markeitech_api_docs.security import constrained_generation_environment, validate_interpreter
from markeitech_api_docs.source import (
    build_api_index,
    capture_source_snapshot,
    documentation_input_paths,
)

MAX_OUTPUT_FILES = 5000
MAX_OUTPUT_BYTES = 64 * 1024 * 1024
TEXT_SUFFIXES = {".css", ".html", ".js", ".json", ".txt", ".xml"}
DIRECT_VERSIONS = {
    "griffe": "2.2.0",
    "mkdocs": "1.6.1",
    "mkdocstrings-python": "2.0.5",
}
SECRET_PATTERNS = (
    re.compile(r"https://(?:canary\.)?discord(?:app)?\.com/api/webhooks/", re.IGNORECASE),
    re.compile(r"\b(?:sk|pk)-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
REMOTE_ASSET_PATTERN = re.compile(
    r"<(?:script|link|img|source|iframe|object|audio|video)\b[^>]*"
    r"(?:src|srcset|href|data)=[\"'](?:https?:)?//",
    re.IGNORECASE,
)
UNSAFE_CSS_PATTERN = re.compile(
    r"@import\b|@font-face\b|url\s*\(|expression\s*\(|"
    r"(?:^|[;{])\s*(?:behavior|-moz-binding)\s*:",
    re.IGNORECASE | re.MULTILINE,
)
HIDING_CSS_PATTERN = re.compile(
    r"(?:display\s*:\s*none|visibility\s*:\s*hidden|opacity\s*:\s*0(?:\D|$)|"
    r"clip-path\s*:|position\s*:\s*(?:absolute|fixed)\s*;[^}]*left\s*:\s*-)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class FixedPaths:
    tool_root: Path
    repository_root: Path
    source_root: Path
    config: Path
    public_surface_registry: Path
    attribute_registry: Path
    output: Path
    build_root: Path

    @classmethod
    def discover(cls) -> FixedPaths:
        tool_root = Path(__file__).resolve().parents[2]
        repository_root = tool_root.parents[1]
        return cls(
            tool_root=tool_root,
            repository_root=repository_root,
            source_root=repository_root / "src" / "markeitech",
            config=tool_root / "mkdocs.yml",
            public_surface_registry=tool_root / "schema" / "public-surface.toml",
            attribute_registry=tool_root / "schema" / "attribute-registry.toml",
            output=repository_root / "docs" / "api",
            build_root=tool_root / ".build",
        )


def _is_within(path: Path, root: Path) -> bool:
    return path.resolve().is_relative_to(root.resolve())


def _validate_output_path(paths: FixedPaths) -> None:
    documentation_root = paths.repository_root / "docs"
    expected_output = documentation_root / "api"
    if paths.output != expected_output:
        raise ApiDocsError("PATH_INVALID: output is not the fixed repository API site")
    if (
        not documentation_root.is_dir()
        or documentation_root.is_symlink()
        or not _is_within(documentation_root, paths.repository_root)
    ):
        raise ApiDocsError("PATH_INVALID: repository documentation root is unsafe")
    if paths.output.is_symlink():
        raise ApiDocsError("OUTPUT_PATH_DENIED: output cannot be a symlink")
    if paths.output.exists() and not paths.output.is_dir():
        raise ApiDocsError("OUTPUT_PATH_DENIED: output must be a directory")
    if not _is_within(paths.output, paths.repository_root):
        raise ApiDocsError("OUTPUT_PATH_DENIED: output is outside the repository")


def _validate_fixed_paths(paths: FixedPaths) -> None:
    if paths.tool_root.name != "api-docs" or paths.tool_root.parent.name != "tools":
        raise ApiDocsError("PATH_INVALID: tool root identity is unexpected")
    if not _is_within(paths.tool_root, paths.repository_root):
        raise ApiDocsError("PATH_INVALID: tool root is outside the repository")
    _validate_output_path(paths)
    if paths.source_root.resolve() != (paths.repository_root / "src/markeitech").resolve():
        raise ApiDocsError("PATH_INVALID: source root is not the fixed V2 package")
    required = (
        paths.source_root,
        paths.config,
        paths.public_surface_registry,
        paths.attribute_registry,
        paths.tool_root / "docs" / "stylesheets" / "markeitech.css",
        paths.tool_root / "pyproject.toml",
        paths.tool_root / "uv.lock",
    )
    for path in required:
        if not path.exists() or path.is_symlink():
            raise ApiDocsError("PATH_INVALID: required input is missing or symlinked")


def _validate_stylesheet(path: Path) -> None:
    value = path.read_text(encoding="utf-8")
    if UNSAFE_CSS_PATTERN.search(value):
        raise ApiDocsError("CONFIG_INVALID: stylesheet contains an unsafe asset reference")
    if HIDING_CSS_PATTERN.search(value):
        raise ApiDocsError("CONFIG_INVALID: stylesheet contains a content-hiding rule")


def _normalized_distribution_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _validate_installed_versions(lock_path: Path) -> dict[str, str]:
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    locked_distributions = {
        _normalized_distribution_name(str(package["name"])): str(package["version"])
        for package in lock.get("package", [])
        if isinstance(package, dict)
        and isinstance(package.get("source"), dict)
        and "registry" in package["source"]
    }
    installed_distributions = {
        _normalized_distribution_name(distribution.metadata["Name"]): distribution.version
        for distribution in importlib.metadata.distributions()
    }
    if installed_distributions != locked_distributions:
        raise ApiDocsError(
            "DEPENDENCY_DRIFT: installed documentation closure differs from uv.lock"
        )

    versions: dict[str, str] = {}
    for distribution, expected in DIRECT_VERSIONS.items():
        try:
            actual = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError as exc:
            raise ApiDocsError(
                "DEPENDENCY_MISSING: locked documentation dependency absent"
            ) from exc
        if actual != expected:
            raise ApiDocsError("DEPENDENCY_DRIFT: direct documentation dependency changed")
        versions[distribution] = actual
    versions["mkdocstrings"] = importlib.metadata.version("mkdocstrings")
    python_version = sys.version_info
    versions["python"] = (
        f"{python_version.major}.{python_version.minor}.{python_version.micro}"
    )
    return dict(sorted(versions.items()))


def _validate_mkdocs_policy(path: Path) -> None:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("strict") is not True:
        raise ApiDocsError("CONFIG_INVALID: MkDocs strict mode is required")
    allowed_top_level = {
        "site_name",
        "site_description",
        "docs_dir",
        "strict",
        "theme",
        "nav",
        "plugins",
        "markdown_extensions",
        "extra_css",
    }
    if set(raw) != allowed_top_level or raw.get("docs_dir") != "docs":
        raise ApiDocsError("CONFIG_INVALID: MkDocs top-level policy changed")
    theme = raw.get("theme")
    if theme != {"name": "readthedocs", "highlightjs": False}:
        raise ApiDocsError("CONFIG_INVALID: only the built-in ReadTheDocs theme is approved")
    if raw.get("extra_css") != ["stylesheets/markeitech.css"]:
        raise ApiDocsError("CONFIG_INVALID: custom stylesheet allowlist changed")
    markdown_extensions = raw.get("markdown_extensions")
    if markdown_extensions != [
        "fenced_code",
        "tables",
        {"toc": {"permalink": True, "toc_depth": 2}},
    ]:
        raise ApiDocsError("CONFIG_INVALID: Markdown extension allowlist changed")
    expected_nav = [
        {"Overview": "index.md"},
        {"Architecture components": "architecture-components.md"},
        {
            "API": [
                {"System": "api/system.md"},
                {"Acquisition": "api/acquisition.md"},
                {"Intelligence": "api/intelligence.md"},
                {"CLI": "api/cli.md"},
            ]
        },
    ]
    if raw.get("nav") != expected_nav:
        raise ApiDocsError("CONFIG_INVALID: navigation allowlist changed")
    plugins = raw.get("plugins")
    if not isinstance(plugins, list) or len(plugins) != 2 or plugins[0] != "search":
        raise ApiDocsError("CONFIG_INVALID: plugin allowlist changed")
    if not isinstance(plugins[1], dict) or set(plugins[1]) != {"mkdocstrings"}:
        raise ApiDocsError("CONFIG_INVALID: mkdocstrings plugin declaration changed")
    mkdocstrings = plugins[1]["mkdocstrings"]
    if set(mkdocstrings) != {"handlers"}:
        raise ApiDocsError("CONFIG_INVALID: mkdocstrings policy changed")
    handlers = mkdocstrings["handlers"]
    if not isinstance(handlers, dict) or set(handlers) != {"python"}:
        raise ApiDocsError("CONFIG_INVALID: handler allowlist changed")
    handler = handlers["python"]
    if not isinstance(handler, dict) or set(handler) != {
        "paths",
        "inventories",
        "load_external_modules",
        "options",
    }:
        raise ApiDocsError("CONFIG_INVALID: Python handler policy changed")
    if handler.get("paths") != ["../../src"]:
        raise ApiDocsError("CONFIG_INVALID: Python source path changed")
    options = handler["options"]
    allowed_options = {
        "allow_inspection",
        "force_inspection",
        "show_source",
        "show_root_heading",
        "show_root_full_path",
        "show_object_full_path",
        "show_signature_annotations",
        "separate_signature",
        "members_order",
        "docstring_style",
        "docstring_section_style",
        "extensions",
    }
    if not isinstance(options, dict) or set(options) != allowed_options:
        raise ApiDocsError("CONFIG_INVALID: mkdocstrings option allowlist changed")
    required_options = {
        "allow_inspection": False,
        "force_inspection": False,
        "show_source": False,
    }
    for key, expected in required_options.items():
        if options.get(key) is not expected:
            raise ApiDocsError(f"CONFIG_INVALID: safe mkdocstrings option {key} changed")
    if handler.get("inventories") != []:
        raise ApiDocsError("CONFIG_INVALID: remote inventories are forbidden")
    if handler.get("load_external_modules") is not False:
        raise ApiDocsError("CONFIG_INVALID: external module loading is forbidden")
    extensions = options.get("extensions")
    if extensions != [
        "markeitech_api_docs.griffe_extension:MarkeitechMetadataExtension"
    ]:
        raise ApiDocsError("CONFIG_INVALID: extension allowlist changed")


def _canonical_json(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode()


def _verify_snapshot_unchanged(
    snapshot: SourceSnapshot,
    repository_root: Path,
    tool_root: Path | None = None,
) -> None:
    if tool_root is not None:
        captured_paths = {item.path for item in snapshot.files}
        current_paths = {
            path.relative_to(repository_root.resolve()).as_posix()
            for path in documentation_input_paths(repository_root, tool_root)
        }
        if current_paths != captured_paths:
            raise ApiDocsError("SOURCE_CHANGED: documentation input population changed")
    for item in snapshot.files:
        path = repository_root / item.path
        if not path.is_file() or path.is_symlink():
            raise ApiDocsError("SOURCE_CHANGED: input disappeared or became a symlink")
        if path.stat().st_size != item.size_bytes or sha256_file(path) != item.sha256:
            raise ApiDocsError("SOURCE_CHANGED: input changed during generation")


def _collect_files(root: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    total = 0
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ApiDocsError("OUTPUT_INVALID: symlinked artifacts are forbidden")
        if not path.is_file():
            continue
        files.append(path)
        total += path.stat().st_size
    if len(files) > MAX_OUTPUT_FILES or total > MAX_OUTPUT_BYTES:
        raise ApiDocsError("OUTPUT_LIMIT_EXCEEDED: generated artifact set is too large")
    return tuple(files)


def _scan_output(root: Path, protected_literals: tuple[str, ...], repository_root: Path) -> None:
    protected = tuple(value for value in protected_literals if value)
    forbidden_fixed = ("Markeitech Metadata:", str(repository_root.resolve()))
    for path in _collect_files(root):
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            value = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ApiDocsError("OUTPUT_INVALID: text artifact is not UTF-8") from exc
        if any(token in value for token in forbidden_fixed):
            raise ApiDocsError("OUTPUT_LEAK_DETECTED: protected documentation content escaped")
        if any(token in value for token in protected):
            raise ApiDocsError("OUTPUT_LEAK_DETECTED: custom metadata value escaped")
        if any(pattern.search(value) for pattern in SECRET_PATTERNS):
            raise ApiDocsError("OUTPUT_LEAK_DETECTED: secret-like content detected")
        if REMOTE_ASSET_PATTERN.search(value):
            raise ApiDocsError("OUTPUT_INVALID: remote auto-fetching asset detected")
        if (
            path.relative_to(root).as_posix() == "stylesheets/markeitech.css"
            and UNSAFE_CSS_PATTERN.search(value)
        ):
            raise ApiDocsError("OUTPUT_INVALID: unsafe stylesheet asset reference detected")


def _hash_entries(root: Path, *, exclude: set[str] | None = None) -> list[dict[str, object]]:
    excluded = exclude or set()
    entries: list[dict[str, object]] = []
    for path in _collect_files(root):
        relative = path.relative_to(root).as_posix()
        if relative in excluded:
            continue
        entries.append(
            {
                "path": relative,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return entries


def _write_artifact_manifests(
    root: Path,
    *,
    paths: FixedPaths,
    snapshot: SourceSnapshot,
    versions: dict[str, str],
) -> None:
    base_entries = _hash_entries(root, exclude={"artifact-index.json", "SHA256SUMS"})
    artifact_index: dict[str, Any] = {
        "schema_id": "markeitech-api-docs-artifact-index",
        "schema_version": 1,
        "authority": "generated_projection_only",
        "not_runtime_configuration": True,
        "source_commit": snapshot.commit,
        "source_state": snapshot.state,
        "tool_version": __version__,
        "tool_versions": versions,
        "lock_sha256": sha256_file(paths.tool_root / "uv.lock"),
        "config_sha256": sha256_file(paths.config),
        "artifacts": base_entries,
    }
    (root / "artifact-index.json").write_bytes(_canonical_json(artifact_index))
    all_entries = _hash_entries(root, exclude={"SHA256SUMS"})
    sums = "".join(f"{entry['sha256']}  {entry['path']}\n" for entry in all_entries)
    (root / "SHA256SUMS").write_text(sums, encoding="utf-8")


def _safe_remove(path: Path, paths: FixedPaths) -> None:
    if not path.exists():
        return
    resolved = path.resolve()
    allowed = {paths.output.resolve(), (paths.build_root / "previous").resolve()}
    if resolved not in allowed and not resolved.is_relative_to(paths.build_root.resolve()):
        raise ApiDocsError("OUTPUT_PATH_DENIED: refusing to remove an unsafe path")
    if path.is_symlink():
        raise ApiDocsError("OUTPUT_PATH_DENIED: refusing to remove a symlink")
    shutil.rmtree(path)


def _publish_complete_set(staged: Path, paths: FixedPaths) -> None:
    previous = paths.build_root / "previous"
    _safe_remove(previous, paths)
    moved_previous = False
    if paths.output.exists():
        if paths.output.is_symlink():
            raise ApiDocsError("OUTPUT_PATH_DENIED: output cannot be a symlink")
        os.replace(paths.output, previous)
        moved_previous = True
    try:
        os.replace(staged, paths.output)
    except OSError as exc:
        if moved_previous and previous.exists() and not paths.output.exists():
            os.replace(previous, paths.output)
        raise ApiDocsError("OUTPUT_PUBLICATION_FAILED: previous complete set was retained") from exc
    _safe_remove(previous, paths)


def _prepare_docs_tree(
    stage_parent: Path,
    paths: FixedPaths,
    generated_markdown: dict[str, str],
) -> Path:
    source = paths.tool_root / "docs"
    for item in source.rglob("*"):
        if item.is_symlink():
            raise ApiDocsError("PATH_INVALID: documentation source cannot contain symlinks")
    destination = stage_parent / "docs"
    shutil.copytree(source, destination)
    for relative, value in generated_markdown.items():
        relative_path = Path(relative)
        if (
            relative_path.is_absolute()
            or ".." in relative_path.parts
            or relative_path.suffix != ".md"
        ):
            raise ApiDocsError("OUTPUT_PATH_DENIED: generated Markdown path is unsafe")
        target = destination / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value, encoding="utf-8")
    return destination


def prepare_index(paths: FixedPaths) -> tuple[ApiIndex, SourceSnapshot, dict[str, str]]:
    _validate_fixed_paths(paths)
    _validate_stylesheet(paths.tool_root / "docs" / "stylesheets" / "markeitech.css")
    validate_interpreter(paths.tool_root)
    versions = _validate_installed_versions(paths.tool_root / "uv.lock")
    _validate_mkdocs_policy(paths.config)
    public_surface = load_public_surface_registry(paths.public_surface_registry)
    attributes = load_attribute_registry(paths.attribute_registry)
    snapshot = capture_source_snapshot(paths.repository_root, paths.tool_root)
    with constrained_generation_environment():
        index = build_api_index(
            repository_root=paths.repository_root,
            tool_root=paths.tool_root,
            snapshot=snapshot,
            surface=public_surface,
            attributes=attributes,
        )
        components = build_component_docs_projection(
            repository_root=paths.repository_root,
            source_root=paths.source_root,
            registry=attributes,
            snapshot=snapshot,
        )
        index = ApiIndex(
            payload={**index.payload, "architecture_components": components.payload},
            protected_literals=index.protected_literals,
            generated_markdown={"architecture-components.md": components.markdown},
        )
    _verify_snapshot_unchanged(snapshot, paths.repository_root, paths.tool_root)
    return index, snapshot, versions


def validate() -> dict[str, object]:
    paths = FixedPaths.discover()
    index, snapshot, versions = prepare_index(paths)
    surface = index.payload["public_surface"]
    return {
        "source_commit": snapshot.commit,
        "source_state": snapshot.state,
        "selected": surface["selected"],
        "documented": surface["documented"],
        "missing_docstring": surface["missing_docstring"],
        "metadata_occurrences": index.payload["metadata"]["occurrence_count"],
        "architecture_components": index.payload["architecture_components"]["counts"][
            "components"
        ],
        "architecture_responsibilities": index.payload["architecture_components"]["counts"][
            "with_responsibilities"
        ],
        "versions": versions,
    }


def generate() -> dict[str, object]:
    paths = FixedPaths.discover()
    index, snapshot, versions = prepare_index(paths)
    paths.build_root.mkdir(parents=True, exist_ok=True)
    if paths.build_root.is_symlink():
        raise ApiDocsError("OUTPUT_PATH_DENIED: build root cannot be a symlink")
    stage_parent = Path(tempfile.mkdtemp(prefix="stage-", dir=paths.build_root))
    staged_output = stage_parent / "complete"

    try:
        staged_output.mkdir()
        staged_docs = _prepare_docs_tree(stage_parent, paths, index.generated_markdown)
        with constrained_generation_environment():
            config = load_config(
                config_file=str(paths.config),
                docs_dir=str(staged_docs),
                site_dir=str(staged_output),
            )
            effective_output = Path(config.site_dir).resolve()
            effective_docs = Path(config.docs_dir).resolve()
            if (
                config.strict is not True
                or effective_output != staged_output.resolve()
                or effective_docs != staged_docs.resolve()
            ):
                raise ApiDocsError("CONFIG_INVALID: effective MkDocs safety settings changed")
            mkdocs_build(config, dirty=False)
        _verify_snapshot_unchanged(snapshot, paths.repository_root, paths.tool_root)
        (staged_output / "metadata-index.json").write_bytes(_canonical_json(index.payload))
        (staged_output / "architecture-components-index.json").write_bytes(
            _canonical_json(index.payload["architecture_components"])
        )
        _scan_output(staged_output, index.protected_literals, paths.repository_root)
        _write_artifact_manifests(
            staged_output,
            paths=paths,
            snapshot=snapshot,
            versions=versions,
        )
        _scan_output(staged_output, index.protected_literals, paths.repository_root)
        _publish_complete_set(staged_output, paths)
    except Exception:
        _safe_remove(stage_parent, paths)
        raise
    _safe_remove(stage_parent, paths)

    return {
        "output": paths.output.as_posix(),
        "source_commit": snapshot.commit,
        "source_state": snapshot.state,
        "selected": index.payload["public_surface"]["selected"],
        "documented": index.payload["public_surface"]["documented"],
        "missing_docstring": index.payload["public_surface"]["missing_docstring"],
        "metadata_occurrences": index.payload["metadata"]["occurrence_count"],
        "architecture_components": index.payload["architecture_components"]["counts"][
            "components"
        ],
        "architecture_responsibilities": index.payload["architecture_components"]["counts"][
            "with_responsibilities"
        ],
        "artifact_count": len(_collect_files(paths.output)),
        "artifact_set_sha256": sha256_bytes((paths.output / "SHA256SUMS").read_bytes()),
    }
