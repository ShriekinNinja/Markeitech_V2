from __future__ import annotations

from pathlib import Path
from typing import Any

import griffe

from markeitech_api_docs.metadata import parse_metadata_docstring
from markeitech_api_docs.models import ApiDocsError, AttributeRegistry
from markeitech_api_docs.registry import load_attribute_registry


def tool_root() -> Path:
    return Path(__file__).resolve().parents[2]


def repository_root() -> Path:
    return tool_root().parents[1]


class MarkeitechMetadataExtension(griffe.Extension):
    """Strip custom metadata before rendering and retain sanitized static evidence only."""

    def __init__(self, registry: AttributeRegistry | None = None) -> None:
        super().__init__()
        self.registry = registry or load_attribute_registry(
            tool_root() / "schema" / "attribute-registry.toml"
        )
        self.occurrences_by_object: dict[str, tuple[dict[str, object], ...]] = {}
        self.protected_literals: list[str] = []

    def on_object(
        self,
        *,
        obj: griffe.Object,
        loader: griffe.GriffeLoader,
        **kwargs: Any,
    ) -> None:
        del loader, kwargs
        self._process(obj)

    def on_package(
        self,
        *,
        pkg: griffe.Module,
        loader: griffe.GriffeLoader,
        **kwargs: Any,
    ) -> None:
        del loader, kwargs
        self._process(pkg)

    def _process(self, obj: griffe.Object) -> None:
        if obj.docstring is None:
            return
        if obj.analysis != "static":
            raise ApiDocsError("DYNAMIC_ANALYSIS_DENIED: every documented object must be static")

        source = self._source_path(obj)
        result = parse_metadata_docstring(
            obj.docstring.value,
            registry=self.registry,
            object_path=obj.path,
            source=source,
            base_line=obj.docstring.lineno or obj.lineno or 1,
        )
        obj.docstring.value = result.sanitized_docstring
        namespace = obj.extra.setdefault("markeitech", {})
        namespace["metadata"] = [item.to_dict() for item in result.occurrences]
        namespace["authority"] = "non_authoritative_discovery_only"
        self.occurrences_by_object[obj.path] = tuple(
            item.to_dict() for item in result.occurrences
        )
        self.protected_literals.extend(result.protected_literals)

    @staticmethod
    def _source_path(obj: griffe.Object) -> str:
        filepath = obj.filepath
        if isinstance(filepath, list):
            if len(filepath) != 1:
                raise ApiDocsError("SOURCE_IDENTITY_INVALID: namespace packages are unsupported")
            filepath = filepath[0]
        resolved = Path(filepath).resolve()
        root = repository_root().resolve()
        if not resolved.is_relative_to(root):
            raise ApiDocsError("SOURCE_SCOPE_DENIED: documented object is outside the repository")
        return resolved.relative_to(root).as_posix()
