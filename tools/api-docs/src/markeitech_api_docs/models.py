from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal


class ApiDocsError(RuntimeError):
    """A sanitized, operator-actionable API documentation failure."""


@dataclass(frozen=True)
class AttributeField:
    name: str
    value_type: Literal["scalar", "list"]
    cardinality: Literal["one", "many"]
    exposure: Literal["public", "status_only"]
    maximum_items: int
    value_pattern: str | None = None


@dataclass(frozen=True)
class AttributeRegistry:
    schema_version: int
    registry_id: str
    registry_version: int
    section_name: str
    maximum_section_bytes: int
    maximum_occurrences_per_object: int
    maximum_key_bytes: int
    maximum_value_bytes: int
    fields: dict[str, AttributeField]
    source_path: Path = field(repr=False)
    source_sha256: str


@dataclass(frozen=True)
class PublicPackagePolicy:
    module: str
    source: str
    expected_export_count: int
    expected_exports_sha256: str


@dataclass(frozen=True)
class ExplicitPublicObject:
    exposed: str
    canonical: str
    source: str
    kind: str
    reason: str


@dataclass(frozen=True)
class PublicSurfaceRegistry:
    schema_version: int
    registry_id: str
    registry_version: int
    selection_policy: str
    packages: tuple[PublicPackagePolicy, ...]
    explicit: tuple[ExplicitPublicObject, ...]
    source_path: Path = field(repr=False)
    source_sha256: str


@dataclass(frozen=True)
class MetadataOccurrence:
    occurrence_id: str
    object_path: str
    source: str
    start_line: int
    end_line: int
    ordinal: int
    status: Literal[
        "typed_exposed",
        "typed_hidden",
        "unknown_schema",
        "invalid_syntax",
        "conflict",
    ]
    key: str | None
    key_sha256: str | None
    raw_byte_length: int
    registry_id: str
    registry_version: int
    diagnostic_code: str | None
    typed_value: str | list[str] | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PublicApiEntry:
    exposed: str
    canonical: str
    kind: str
    source: str
    definition_line: int | None
    alias: bool
    has_docstring: bool
    metadata_occurrence_ids: tuple[str, ...]
    inclusion_reason: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["metadata_occurrence_ids"] = list(self.metadata_occurrence_ids)
        return value


@dataclass(frozen=True)
class SourceFileIdentity:
    path: str
    sha256: str
    size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SourceSnapshot:
    commit: str
    state: Literal["clean", "dirty"]
    dirty_path_count: int
    dirty_state_sha256: str | None
    files: tuple[SourceFileIdentity, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "commit": self.commit,
            "state": self.state,
            "dirty_path_count": self.dirty_path_count,
            "dirty_state_sha256": self.dirty_state_sha256,
            "files": [item.to_dict() for item in self.files],
        }


@dataclass(frozen=True)
class MetadataParseResult:
    sanitized_docstring: str
    occurrences: tuple[MetadataOccurrence, ...]
    protected_literals: tuple[str, ...] = field(repr=False)


@dataclass(frozen=True)
class ApiIndex:
    payload: dict[str, Any]
    protected_literals: tuple[str, ...] = field(repr=False)
    generated_markdown: dict[str, str] = field(default_factory=dict, repr=False)
