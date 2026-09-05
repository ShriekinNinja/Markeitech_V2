from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from markeitech_api_docs.build import FixedPaths, prepare_index
from markeitech_api_docs.models import ApiDocsError
from markeitech_api_docs.registry import load_public_surface_registry
from markeitech_api_docs.source import (
    _build_source_input_signature,
    exports_digest,
    literal_all,
)


class StaticSourceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.paths = FixedPaths.discover()

    def test_literal_export_denominator_matches_registry(self) -> None:
        registry = load_public_surface_registry(self.paths.public_surface_registry)
        for policy in registry.packages:
            names = literal_all(self.paths.repository_root / policy.source)
            self.assertEqual(len(names), policy.expected_export_count)
            self.assertEqual(exports_digest(names), policy.expected_exports_sha256)

    def test_current_index_is_complete_for_declared_denominator(self) -> None:
        index, snapshot, versions = prepare_index(self.paths)
        surface = index.payload["public_surface"]
        self.assertEqual(surface["expected"], 261)
        self.assertEqual(surface["selected"], 261)
        self.assertEqual(surface["parse_failed"], 0)
        self.assertEqual(surface["unresolved_alias"], 0)
        self.assertNotIn("LegacyMetricValue", json.dumps(index.payload, sort_keys=True))
        self.assertEqual(len(snapshot.commit), 40)
        self.assertTrue(all(value in "0123456789abcdef" for value in snapshot.commit))
        self.assertEqual(versions["griffe"], "2.2.0")

    def test_input_signature_is_independent_of_checkout_root(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            roots = (Path(first), Path(second))
            signatures = []
            for root in roots:
                source = root / "src" / "markeitech" / "fixture.py"
                config = root / "tools" / "api-docs" / "mkdocs.yml"
                source.parent.mkdir(parents=True)
                config.parent.mkdir(parents=True)
                source.write_text("VALUE = 1\n", encoding="utf-8")
                config.write_text("strict: true\n", encoding="utf-8")
                signatures.append(
                    _build_source_input_signature((source, config), root)
                )

            self.assertEqual(signatures[0], signatures[1])

    def test_input_signature_detects_population_and_content_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first.py"
            second = root / "second.py"
            first.write_text("VALUE = 1\n", encoding="utf-8")
            second.write_text("VALUE = 2\n", encoding="utf-8")
            original = _build_source_input_signature((first,), root)
            with_added_input = _build_source_input_signature((first, second), root)
            first.write_text("VALUE = 3\n", encoding="utf-8")
            with_changed_content = _build_source_input_signature((first,), root)

            self.assertNotEqual(original, with_added_input)
            self.assertNotEqual(original, with_changed_content)

    def test_input_signature_rejects_outside_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as outside:
            root = Path(temporary)
            external = Path(outside) / "fixture.py"
            external.write_text("VALUE = 1\n", encoding="utf-8")

            with self.assertRaisesRegex(ApiDocsError, "PATH_INVALID"):
                _build_source_input_signature((external,), root)


if __name__ == "__main__":
    unittest.main()
