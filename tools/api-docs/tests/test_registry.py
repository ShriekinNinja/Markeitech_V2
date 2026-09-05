from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from markeitech_api_docs.models import ApiDocsError
from markeitech_api_docs.registry import (
    load_attribute_registry,
    load_public_surface_registry,
)


class RegistryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tool_root = Path(__file__).resolve().parents[1]

    def test_production_registries_are_versioned_and_closed(self) -> None:
        attributes = load_attribute_registry(
            self.tool_root / "schema" / "attribute-registry.toml"
        )
        surface = load_public_surface_registry(
            self.tool_root / "schema" / "public-surface.toml"
        )
        self.assertEqual(attributes.schema_version, 1)
        self.assertEqual(attributes.registry_version, 2)
        self.assertEqual(
            set(attributes.fields),
            {
                "architecture.component.id",
                "architecture.component.label",
                "architecture.component.kind",
                "architecture.component.boundary",
                "architecture.component.responsibilities",
            },
        )
        expected = {
            "architecture.component.id": (
                "scalar",
                "one",
                "public",
                1,
                r"(?:actor|component)\.[a-z0-9]+(?:-[a-z0-9]+)*",
            ),
            "architecture.component.label": (
                "scalar",
                "one",
                "public",
                1,
                r".{1,96}",
            ),
            "architecture.component.kind": (
                "scalar",
                "one",
                "public",
                1,
                r"(?:markeitech_actor|engine)",
            ),
            "architecture.component.boundary": (
                "scalar",
                "one",
                "public",
                1,
                r"(?:boundary\.system|boundary\.acquisition|boundary\.intelligence)",
            ),
            "architecture.component.responsibilities": (
                "list",
                "one",
                "public",
                8,
                r".{1,512}",
            ),
        }
        actual = {
            name: (
                field.value_type,
                field.cardinality,
                field.exposure,
                field.maximum_items,
                field.value_pattern,
            )
            for name, field in attributes.fields.items()
        }
        self.assertEqual(actual, expected)
        self.assertEqual(surface.schema_version, 1)
        self.assertEqual(surface.registry_version, 5)
        self.assertEqual(sum(item.expected_export_count for item in surface.packages), 260)

    def test_unsafe_registry_source_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "surface.toml"
            path.write_text(
                """schema_version = 1
registry_id = "test"
registry_version = 1
selection_policy = "test"
[[packages]]
module = "markeitech.test"
source = "../escape.py"
expected_export_count = 1
expected_exports_sha256 = "0000000000000000000000000000000000000000000000000000000000000000"
""",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ApiDocsError, "repository-relative"):
                load_public_surface_registry(path)


if __name__ == "__main__":
    unittest.main()
