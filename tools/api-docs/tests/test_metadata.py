from __future__ import annotations

import json
import unittest
from pathlib import Path

from markeitech_api_docs.metadata import parse_metadata_docstring
from markeitech_api_docs.models import AttributeField, AttributeRegistry


def registry(*fields: AttributeField) -> AttributeRegistry:
    return AttributeRegistry(
        schema_version=1,
        registry_id="test-registry",
        registry_version=7,
        section_name="Markeitech Metadata",
        maximum_section_bytes=4096,
        maximum_occurrences_per_object=16,
        maximum_key_bytes=64,
        maximum_value_bytes=128,
        fields={field.name: field for field in fields},
        source_path=Path("attribute-registry.toml"),
        source_sha256="0" * 64,
    )


class MetadataParserTest(unittest.TestCase):
    def test_exposed_hidden_unknown_and_invalid_values_are_separated(self) -> None:
        value = """Summary.

Markeitech Metadata:
    docs.exposed: visible-value
    docs.hidden:
        - PRIVATE_HIDDEN_SENTINEL
    future.unknown: PRIVATE_UNKNOWN_SENTINEL
    invalid prose

Returns:
    Nothing.
"""
        result = parse_metadata_docstring(
            value,
            registry=registry(
                AttributeField("docs.exposed", "scalar", "one", "public", 1),
                AttributeField("docs.hidden", "list", "one", "status_only", 3),
            ),
            object_path="markeitech.fixture.func",
            source="v2/src/markeitech/fixture.py",
            base_line=10,
        )

        self.assertNotIn("Markeitech Metadata:", result.sanitized_docstring)
        self.assertIn("Returns:", result.sanitized_docstring)
        statuses = [item.status for item in result.occurrences]
        self.assertEqual(
            statuses,
            ["typed_exposed", "typed_hidden", "unknown_schema", "invalid_syntax"],
        )
        self.assertEqual(result.occurrences[0].typed_value, "visible-value")
        self.assertIsNone(result.occurrences[1].typed_value)
        self.assertIsNone(result.occurrences[2].key)
        serialized = json.dumps([item.to_dict() for item in result.occurrences])
        self.assertNotIn("PRIVATE_HIDDEN_SENTINEL", serialized)
        self.assertNotIn("PRIVATE_UNKNOWN_SENTINEL", serialized)
        self.assertIn("PRIVATE_HIDDEN_SENTINEL", result.protected_literals)
        self.assertIn("PRIVATE_UNKNOWN_SENTINEL", result.protected_literals)

    def test_single_cardinality_duplicates_become_conflicts(self) -> None:
        result = parse_metadata_docstring(
            """Summary.

Markeitech Metadata:
    docs.key: first-value
    docs.key: second-value
""",
            registry=registry(
                AttributeField("docs.key", "scalar", "one", "public", 1)
            ),
            object_path="markeitech.fixture.func",
            source="v2/src/markeitech/fixture.py",
            base_line=1,
        )
        self.assertEqual([item.status for item in result.occurrences], ["conflict", "conflict"])
        self.assertTrue(all(item.typed_value is None for item in result.occurrences))

    def test_multiline_scalar_is_not_silently_absorbed(self) -> None:
        result = parse_metadata_docstring(
            """Summary.

Markeitech Metadata:
    docs.key:
        continuation without list marker
""",
            registry=registry(
                AttributeField("docs.key", "scalar", "one", "public", 1)
            ),
            object_path="markeitech.fixture.func",
            source="v2/src/markeitech/fixture.py",
            base_line=1,
        )
        self.assertEqual(result.occurrences[0].status, "invalid_syntax")
        self.assertTrue(
            any(item.diagnostic_code == "METADATA_ENTRY_INVALID" for item in result.occurrences)
        )

    def test_wrapped_list_item_is_normalized_without_changing_meaning(self) -> None:
        result = parse_metadata_docstring(
            """Summary.

Markeitech Metadata:
    docs.items:
        - one long declaration which is wrapped
          onto a second source line.
""",
            registry=registry(
                AttributeField("docs.items", "list", "one", "public", 3)
            ),
            object_path="markeitech.fixture.Component",
            source="v2/src/markeitech/fixture.py",
            base_line=1,
        )
        self.assertEqual(
            result.occurrences[0].typed_value,
            ["one long declaration which is wrapped onto a second source line."],
        )


if __name__ == "__main__":
    unittest.main()
