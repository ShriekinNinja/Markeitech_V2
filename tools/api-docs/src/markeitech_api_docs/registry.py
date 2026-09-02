from __future__ import annotations

import hashlib
import re
import tomllib
from pathlib import Path

from markeitech_api_docs.models import (
    ApiDocsError,
    AttributeField,
    AttributeRegistry,
    ExplicitPublicObject,
    PublicPackagePolicy,
    PublicSurfaceRegistry,
)

_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)+$")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ApiDocsError(f"REGISTRY_INVALID: {label} must be a table")
    return value


def _sequence(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise ApiDocsError(f"REGISTRY_INVALID: {label} must be an array of tables")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ApiDocsError(f"REGISTRY_INVALID: {label} must be non-empty text")
    return value


def _positive_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ApiDocsError(f"REGISTRY_INVALID: {label} must be a positive integer")
    return value


def _safe_relative_path(value: object, label: str) -> str:
    text = _text(value, label)
    path = Path(text)
    if path.is_absolute() or ".." in path.parts:
        raise ApiDocsError(f"REGISTRY_INVALID: {label} must be repository-relative")
    return path.as_posix()


def load_attribute_registry(path: Path) -> AttributeRegistry:
    raw_bytes = path.read_bytes()
    raw = tomllib.loads(raw_bytes.decode("utf-8"))
    schema_version = _positive_int(raw.get("schema_version"), "schema_version")
    if schema_version != 1:
        raise ApiDocsError("REGISTRY_UNSUPPORTED: attribute registry schema must be 1")

    fields: dict[str, AttributeField] = {}
    for index, raw_field in enumerate(_sequence(raw.get("fields", []), "fields")):
        field = _mapping(raw_field, f"fields[{index}]")
        name = _text(field.get("name"), f"fields[{index}].name")
        if not _KEY_PATTERN.fullmatch(name):
            raise ApiDocsError(f"REGISTRY_INVALID: fields[{index}].name has invalid syntax")
        if name in fields:
            raise ApiDocsError(f"REGISTRY_INVALID: duplicate attribute field {name}")
        value_type = _text(field.get("value_type"), f"fields[{index}].value_type")
        cardinality = _text(field.get("cardinality"), f"fields[{index}].cardinality")
        exposure = _text(field.get("exposure"), f"fields[{index}].exposure")
        if value_type not in {"scalar", "list"}:
            raise ApiDocsError(f"REGISTRY_INVALID: {name} has unsupported value_type")
        if cardinality not in {"one", "many"}:
            raise ApiDocsError(f"REGISTRY_INVALID: {name} has unsupported cardinality")
        if exposure not in {"public", "status_only"}:
            raise ApiDocsError(f"REGISTRY_INVALID: {name} has unsupported exposure")
        pattern = field.get("value_pattern")
        if pattern is not None:
            pattern = _text(pattern, f"fields[{index}].value_pattern")
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ApiDocsError(
                    f"REGISTRY_INVALID: {name} has an invalid value_pattern"
                ) from exc
        fields[name] = AttributeField(
            name=name,
            value_type=value_type,  # type: ignore[arg-type]
            cardinality=cardinality,  # type: ignore[arg-type]
            exposure=exposure,  # type: ignore[arg-type]
            maximum_items=_positive_int(
                field.get("maximum_items", 1), f"fields[{index}].maximum_items"
            ),
            value_pattern=pattern,
        )

    return AttributeRegistry(
        schema_version=schema_version,
        registry_id=_text(raw.get("registry_id"), "registry_id"),
        registry_version=_positive_int(raw.get("registry_version"), "registry_version"),
        section_name=_text(raw.get("section_name"), "section_name"),
        maximum_section_bytes=_positive_int(
            raw.get("maximum_section_bytes"), "maximum_section_bytes"
        ),
        maximum_occurrences_per_object=_positive_int(
            raw.get("maximum_occurrences_per_object"), "maximum_occurrences_per_object"
        ),
        maximum_key_bytes=_positive_int(raw.get("maximum_key_bytes"), "maximum_key_bytes"),
        maximum_value_bytes=_positive_int(
            raw.get("maximum_value_bytes"), "maximum_value_bytes"
        ),
        fields=fields,
        source_path=path,
        source_sha256=sha256_bytes(raw_bytes),
    )


def load_public_surface_registry(path: Path) -> PublicSurfaceRegistry:
    raw_bytes = path.read_bytes()
    raw = tomllib.loads(raw_bytes.decode("utf-8"))
    schema_version = _positive_int(raw.get("schema_version"), "schema_version")
    if schema_version != 1:
        raise ApiDocsError("REGISTRY_UNSUPPORTED: public-surface schema must be 1")

    packages: list[PublicPackagePolicy] = []
    seen_modules: set[str] = set()
    for index, raw_package in enumerate(_sequence(raw.get("packages"), "packages")):
        package = _mapping(raw_package, f"packages[{index}]")
        module = _text(package.get("module"), f"packages[{index}].module")
        if module in seen_modules:
            raise ApiDocsError(f"REGISTRY_INVALID: duplicate package policy {module}")
        seen_modules.add(module)
        digest = _text(
            package.get("expected_exports_sha256"),
            f"packages[{index}].expected_exports_sha256",
        )
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ApiDocsError(f"REGISTRY_INVALID: {module} export hash is not SHA-256")
        packages.append(
            PublicPackagePolicy(
                module=module,
                source=_safe_relative_path(
                    package.get("source"), f"packages[{index}].source"
                ),
                expected_export_count=_positive_int(
                    package.get("expected_export_count"),
                    f"packages[{index}].expected_export_count",
                ),
                expected_exports_sha256=digest,
            )
        )

    explicit: list[ExplicitPublicObject] = []
    seen_exposed: set[str] = set()
    for index, raw_item in enumerate(_sequence(raw.get("explicit", []), "explicit")):
        item = _mapping(raw_item, f"explicit[{index}]")
        exposed = _text(item.get("exposed"), f"explicit[{index}].exposed")
        if exposed in seen_exposed:
            raise ApiDocsError(f"REGISTRY_INVALID: duplicate explicit object {exposed}")
        seen_exposed.add(exposed)
        explicit.append(
            ExplicitPublicObject(
                exposed=exposed,
                canonical=_text(item.get("canonical"), f"explicit[{index}].canonical"),
                source=_safe_relative_path(item.get("source"), f"explicit[{index}].source"),
                kind=_text(item.get("kind"), f"explicit[{index}].kind"),
                reason=_text(item.get("reason"), f"explicit[{index}].reason"),
            )
        )

    return PublicSurfaceRegistry(
        schema_version=schema_version,
        registry_id=_text(raw.get("registry_id"), "registry_id"),
        registry_version=_positive_int(raw.get("registry_version"), "registry_version"),
        selection_policy=_text(raw.get("selection_policy"), "selection_policy"),
        packages=tuple(packages),
        explicit=tuple(explicit),
        source_path=path,
        source_sha256=sha256_bytes(raw_bytes),
    )
