from __future__ import annotations

import json
import unittest

from markeitech_api_docs.build import FixedPaths, generate


class GenerationTest(unittest.TestCase):
    def test_generation_is_repeatable_and_sanitized(self) -> None:
        first = generate()
        second = generate()
        self.assertEqual(first["artifact_set_sha256"], second["artifact_set_sha256"])
        self.assertEqual(first["selected"], 258)

        output = FixedPaths.discover().output
        index = json.loads((output / "metadata-index.json").read_text(encoding="utf-8"))
        self.assertEqual(index["authority"], "non_authoritative_discovery_only")
        self.assertTrue(index["not_runtime_configuration"])
        self.assertEqual(index["public_surface"]["selected"], 258)
        self.assertEqual(index["metadata"]["occurrence_count"], 0)

        for path in output.rglob("*"):
            if path.is_file() and path.suffix in {".html", ".json", ".txt", ".xml"}:
                value = path.read_text(encoding="utf-8")
                self.assertNotIn("Markeitech Metadata:", value)
                self.assertNotIn(str(FixedPaths.discover().repository_root), value)


if __name__ == "__main__":
    unittest.main()
