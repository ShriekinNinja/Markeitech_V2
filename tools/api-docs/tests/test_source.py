from __future__ import annotations

import json
import unittest

from markeitech_api_docs.build import FixedPaths, prepare_index
from markeitech_api_docs.registry import load_public_surface_registry
from markeitech_api_docs.source import exports_digest, literal_all


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
        self.assertEqual(surface["expected"], 260)
        self.assertEqual(surface["selected"], 260)
        self.assertEqual(surface["parse_failed"], 0)
        self.assertEqual(surface["unresolved_alias"], 0)
        self.assertNotIn("LegacyMetricValue", json.dumps(index.payload, sort_keys=True))
        self.assertEqual(len(snapshot.commit), 40)
        self.assertTrue(all(value in "0123456789abcdef" for value in snapshot.commit))
        self.assertEqual(versions["griffe"], "2.2.0")


if __name__ == "__main__":
    unittest.main()
