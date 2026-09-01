from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any
from uuid import UUID

SIGNED_INT64_MAX = 9_223_372_036_854_775_807
IDENTIFIER_MAX_LENGTH = 128
REFERENCE_MAX_LENGTH = 256
MAX_EVIDENCE_REFERENCES = 256
SERIES_ID_MAX_LENGTH = 64

_TOPIC_TOKEN = re.compile(r"^[A-Za-z0-9_-]+$")
_HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")


def bounded_ascii(value: object, label: str, *, maximum: int = IDENTIFIER_MAX_LENGTH) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    if len(value) > maximum or not value.isascii():
        raise ValueError(f"{label} must be at most {maximum} ASCII characters")
    return value


def topic_token(value: object, label: str = "series_id") -> str:
    normalized = bounded_ascii(value, label, maximum=SERIES_ID_MAX_LENGTH)
    if _TOPIC_TOKEN.fullmatch(normalized) is None:
        raise ValueError(
            f"{label} must contain only ASCII letters, digits, underscores, or hyphens"
        )
    return normalized


def digest(value: object, label: str) -> str:
    normalized = bounded_ascii(value, label, maximum=64)
    if _HEX_DIGEST.fullmatch(normalized) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return normalized


def positive_int64(value: object, label: str) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value <= 0
        or value > SIGNED_INT64_MAX
    ):
        raise ValueError(f"{label} must be a positive signed 64-bit integer")
    return value


def non_negative_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def positive_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def uuid_value(value: object, label: str) -> UUID:
    if not isinstance(value, UUID):
        raise ValueError(f"{label} must be a UUID")
    return value


def decimal_value(value: object, label: str, *, positive: bool = False) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(f"{label} must be a finite Decimal")
    if positive and value <= 0:
        raise ValueError(f"{label} must be positive")
    return value


def decimal_to_wire(value: Decimal, label: str) -> str:
    """Return the one canonical string representation for a finite Decimal."""

    return str(decimal_value(value, label))


def decimal_from_wire(value: object, label: str) -> Decimal:
    """Parse only a canonical Decimal string; numeric JSON values are invalid."""

    if type(value) is not str:
        raise ValueError(f"{label} must be a canonical Decimal string")
    raw = value
    try:
        parsed = Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{label} must be a canonical Decimal string") from exc
    if not parsed.is_finite() or str(parsed) != raw:
        raise ValueError(f"{label} must be a canonical finite Decimal string")
    return parsed


def exact_dict(
    value: object,
    expected_keys: frozenset[str],
    label: str,
) -> dict[str, Any]:
    """Require a plain dictionary with exactly the declared canonical keys."""

    if type(value) is not dict:
        raise ValueError(f"{label} must be a plain dictionary")
    actual_keys = set(value)
    if any(type(key) is not str for key in actual_keys):
        raise ValueError(f"{label} keys must be strings")
    if actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        unknown = sorted(actual_keys - expected_keys)
        raise ValueError(
            f"{label} keys are not exact; missing={missing!r}, unknown={unknown!r}",
        )
    return value


def raw_string(value: object, label: str) -> str:
    if type(value) is not str:
        raise ValueError(f"{label} must be a string")
    return value


def raw_optional_string(value: object, label: str) -> str | None:
    if value is None:
        return None
    return raw_string(value, label)


def raw_int(value: object, label: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{label} must be an integer")
    return value


def raw_optional_int(value: object, label: str) -> int | None:
    if value is None:
        return None
    return raw_int(value, label)


def raw_bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a boolean")
    return value


def raw_list(value: object, label: str) -> list[Any]:
    if type(value) is not list:
        raise ValueError(f"{label} must be a list")
    return value


def raw_string_list(value: object, label: str) -> tuple[str, ...]:
    return tuple(raw_string(item, f"{label} entry") for item in raw_list(value, label))


def uuid_from_wire(value: object, label: str) -> UUID:
    raw = raw_string(value, label)
    try:
        parsed = UUID(raw)
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"{label} must be a canonical UUID string") from exc
    if str(parsed) != raw:
        raise ValueError(f"{label} must be a canonical UUID string")
    return parsed


def enum_value(value: object, kind: type[Enum], label: str) -> Enum:
    if not isinstance(value, kind):
        raise ValueError(f"{label} must be a {kind.__name__}")
    return value


def text_tuple(
    value: object,
    label: str,
    *,
    maximum_items: int,
    maximum_length: int = IDENTIFIER_MAX_LENGTH,
    ascii_only: bool = True,
) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise ValueError(f"{label} must be a tuple")
    if len(value) > maximum_items:
        raise ValueError(f"{label} must contain at most {maximum_items} entries")
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise ValueError(f"{label} entries must be non-empty strings")
        if len(item) > maximum_length or (ascii_only and not item.isascii()):
            qualifier = " ASCII" if ascii_only else ""
            raise ValueError(
                f"{label} entries must be at most {maximum_length}{qualifier} characters",
            )
        normalized.append(item)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{label} entries must be unique")
    return tuple(normalized)


def evidence_references(values: Iterable[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value:
            raise ValueError("evidence references must be non-empty strings")
        if len(value) > REFERENCE_MAX_LENGTH:
            raise ValueError("evidence references must be at most 256 characters")
        if value not in seen:
            seen.add(value)
            normalized.append(value)
    if len(normalized) > MAX_EVIDENCE_REFERENCES:
        raise ValueError("a payload may contain at most 256 evidence references")
    return tuple(normalized)


def canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        _json_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def canonical_digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _json_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_value(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    return value
