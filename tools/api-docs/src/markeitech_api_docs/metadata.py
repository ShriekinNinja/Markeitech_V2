from __future__ import annotations

import hashlib
import re
from dataclasses import replace

from markeitech_api_docs.models import (
    AttributeField,
    AttributeRegistry,
    MetadataOccurrence,
    MetadataParseResult,
)

_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)+$")


def _sha256(domain: str, value: str) -> str:
    payload = f"markeitech-api-docs:{domain}:v1\0{value}".encode()
    return hashlib.sha256(payload).hexdigest()


def _indent(value: str) -> int:
    return len(value) - len(value.lstrip(" "))


def _safe_protected_literal(value: str) -> str | None:
    stripped = value.strip()
    if len(stripped) < 4:
        return None
    return stripped


def _occurrence_id(object_path: str, source: str, start_line: int, ordinal: int) -> str:
    return _sha256("occurrence", f"{object_path}\0{source}\0{start_line}\0{ordinal}")


def _invalid_occurrence(
    *,
    registry: AttributeRegistry,
    object_path: str,
    source: str,
    start_line: int,
    end_line: int,
    ordinal: int,
    raw_byte_length: int,
    diagnostic_code: str,
) -> MetadataOccurrence:
    return MetadataOccurrence(
        occurrence_id=_occurrence_id(object_path, source, start_line, ordinal),
        object_path=object_path,
        source=source,
        start_line=start_line,
        end_line=end_line,
        ordinal=ordinal,
        status="invalid_syntax",
        key=None,
        key_sha256=None,
        raw_byte_length=raw_byte_length,
        registry_id=registry.registry_id,
        registry_version=registry.registry_version,
        diagnostic_code=diagnostic_code,
        typed_value=None,
    )


def _validate_field(
    field: AttributeField,
    values: list[str],
    registry: AttributeRegistry,
) -> str | None:
    if field.value_type == "scalar" and len(values) != 1:
        return "METADATA_TYPE_MISMATCH"
    if field.value_type == "list" and (not values or len(values) > field.maximum_items):
        return "METADATA_CARDINALITY_INVALID"
    if any(len(value.encode()) > registry.maximum_value_bytes for value in values):
        return "METADATA_VALUE_TOO_LARGE"
    if field.value_pattern is not None:
        pattern = re.compile(field.value_pattern)
        if any(pattern.fullmatch(value) is None for value in values):
            return "METADATA_VALUE_INVALID"
    return None


def parse_metadata_docstring(
    value: str,
    *,
    registry: AttributeRegistry,
    object_path: str,
    source: str,
    base_line: int,
) -> MetadataParseResult:
    """Remove custom metadata blocks and return only sanitized structured evidence."""

    lines = value.splitlines()
    header = f"{registry.section_name}:"
    occurrences: list[MetadataOccurrence] = []
    protected_literals: list[str] = []
    retained: list[str] = []
    index = 0
    ordinal = 0

    while index < len(lines):
        line = lines[index]
        if line != header:
            retained.append(line)
            index += 1
            continue

        block_start = index
        index += 1
        while index < len(lines):
            candidate = lines[index]
            if candidate and _indent(candidate) == 0:
                break
            index += 1
        block_end = index
        block_lines = lines[block_start:block_end]
        block_bytes = "\n".join(block_lines).encode()

        if len(block_bytes) > registry.maximum_section_bytes:
            ordinal += 1
            occurrences.append(
                _invalid_occurrence(
                    registry=registry,
                    object_path=object_path,
                    source=source,
                    start_line=base_line + block_start,
                    end_line=base_line + max(block_start, block_end - 1),
                    ordinal=ordinal,
                    raw_byte_length=len(block_bytes),
                    diagnostic_code="METADATA_SECTION_TOO_LARGE",
                )
            )
            protected_literals.extend(
                item
                for raw in block_lines[1:]
                if (item := _safe_protected_literal(raw)) is not None
            )
            continue

        cursor = block_start + 1
        while cursor < block_end:
            raw_line = lines[cursor]
            if not raw_line.strip():
                cursor += 1
                continue

            ordinal += 1
            occurrence_start = cursor
            entry_match = re.fullmatch(
                r" {4}([a-z][a-z0-9]*(?:[._-][a-z0-9]+)+):(?: (.*))?",
                raw_line,
            )
            if entry_match is None:
                occurrences.append(
                    _invalid_occurrence(
                        registry=registry,
                        object_path=object_path,
                        source=source,
                        start_line=base_line + cursor,
                        end_line=base_line + cursor,
                        ordinal=ordinal,
                        raw_byte_length=len(raw_line.encode()),
                        diagnostic_code="METADATA_ENTRY_INVALID",
                    )
                )
                protected = _safe_protected_literal(raw_line)
                if protected is not None:
                    protected_literals.append(protected)
                cursor += 1
                continue

            key = entry_match.group(1)
            inline_value = entry_match.group(2)
            values: list[str] = []
            raw_parts = [raw_line]
            cursor += 1

            if inline_value is not None and inline_value != "":
                values.append(inline_value)
            else:
                while cursor < block_end:
                    list_match = re.fullmatch(r" {8}- (.+)", lines[cursor])
                    if list_match is None:
                        break
                    item = list_match.group(1)
                    raw_parts.append(lines[cursor])
                    cursor += 1
                    while cursor < block_end:
                        continuation = re.fullmatch(r" {10}(\S.*)", lines[cursor])
                        if continuation is None:
                            break
                        item = f"{item} {continuation.group(1)}"
                        raw_parts.append(lines[cursor])
                        cursor += 1
                    values.append(item)

            raw_text = "\n".join(raw_parts)
            raw_length = len(raw_text.encode())
            field = registry.fields.get(key)
            start_line = base_line + occurrence_start
            end_line = base_line + cursor - 1

            if len(key.encode()) > registry.maximum_key_bytes or not _KEY_PATTERN.fullmatch(key):
                occurrences.append(
                    _invalid_occurrence(
                        registry=registry,
                        object_path=object_path,
                        source=source,
                        start_line=start_line,
                        end_line=end_line,
                        ordinal=ordinal,
                        raw_byte_length=raw_length,
                        diagnostic_code="METADATA_KEY_INVALID",
                    )
                )
                protected_literals.extend(filter(None, map(_safe_protected_literal, values)))
                continue

            if field is None:
                occurrences.append(
                    MetadataOccurrence(
                        occurrence_id=_occurrence_id(object_path, source, start_line, ordinal),
                        object_path=object_path,
                        source=source,
                        start_line=start_line,
                        end_line=end_line,
                        ordinal=ordinal,
                        status="unknown_schema",
                        key=None,
                        key_sha256=_sha256("unknown-key", key),
                        raw_byte_length=raw_length,
                        registry_id=registry.registry_id,
                        registry_version=registry.registry_version,
                        diagnostic_code="METADATA_SCHEMA_UNKNOWN",
                        typed_value=None,
                    )
                )
                protected_literals.extend(filter(None, map(_safe_protected_literal, values)))
                continue

            diagnostic = _validate_field(field, values, registry)
            if diagnostic is not None:
                occurrences.append(
                    MetadataOccurrence(
                        occurrence_id=_occurrence_id(object_path, source, start_line, ordinal),
                        object_path=object_path,
                        source=source,
                        start_line=start_line,
                        end_line=end_line,
                        ordinal=ordinal,
                        status="invalid_syntax",
                        key=key,
                        key_sha256=None,
                        raw_byte_length=raw_length,
                        registry_id=registry.registry_id,
                        registry_version=registry.registry_version,
                        diagnostic_code=diagnostic,
                        typed_value=None,
                    )
                )
                protected_literals.extend(filter(None, map(_safe_protected_literal, values)))
                continue

            typed_value: str | list[str]
            typed_value = values[0] if field.value_type == "scalar" else values
            exposed = field.exposure == "public"
            occurrences.append(
                MetadataOccurrence(
                    occurrence_id=_occurrence_id(object_path, source, start_line, ordinal),
                    object_path=object_path,
                    source=source,
                    start_line=start_line,
                    end_line=end_line,
                    ordinal=ordinal,
                    status="typed_exposed" if exposed else "typed_hidden",
                    key=key,
                    key_sha256=None,
                    raw_byte_length=raw_length,
                    registry_id=registry.registry_id,
                    registry_version=registry.registry_version,
                    diagnostic_code=None,
                    typed_value=typed_value if exposed else None,
                )
            )
            if not exposed:
                protected_literals.extend(filter(None, map(_safe_protected_literal, values)))

        if len(occurrences) > registry.maximum_occurrences_per_object:
            occurrences = [
                _invalid_occurrence(
                    registry=registry,
                    object_path=object_path,
                    source=source,
                    start_line=base_line + block_start,
                    end_line=base_line + max(block_start, block_end - 1),
                    ordinal=1,
                    raw_byte_length=len(block_bytes),
                    diagnostic_code="METADATA_OCCURRENCE_LIMIT_EXCEEDED",
                )
            ]

    positions_by_key: dict[str, list[int]] = {}
    for position, occurrence in enumerate(occurrences):
        if occurrence.key is not None:
            positions_by_key.setdefault(occurrence.key, []).append(position)
    for key, positions in positions_by_key.items():
        field = registry.fields.get(key)
        if field is not None and field.cardinality == "one" and len(positions) > 1:
            for position in positions:
                occurrences[position] = replace(
                    occurrences[position],
                    status="conflict",
                    diagnostic_code="METADATA_DUPLICATE_CONFLICT",
                    typed_value=None,
                )

    while retained and not retained[-1].strip():
        retained.pop()
    sanitized = "\n".join(retained)
    return MetadataParseResult(
        sanitized_docstring=sanitized,
        occurrences=tuple(occurrences),
        protected_literals=tuple(dict.fromkeys(protected_literals)),
    )
