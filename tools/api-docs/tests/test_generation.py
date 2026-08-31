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

        paths = FixedPaths.discover()
        self.assertEqual(paths.output, paths.repository_root / "docs" / "api")
        output = paths.output
        index = json.loads((output / "metadata-index.json").read_text(encoding="utf-8"))
        self.assertEqual(index["authority"], "non_authoritative_discovery_only")
        self.assertTrue(index["not_runtime_configuration"])
        self.assertEqual(index["public_surface"]["selected"], 258)
        self.assertEqual(index["metadata"]["occurrence_count"], 0)
        self.assertEqual(index["architecture_components"]["counts"]["components"], 19)
        self.assertEqual(
            index["architecture_components"]["counts"]["with_responsibilities"],
            6,
        )
        architecture = json.loads(
            (output / "architecture-components-index.json").read_text(encoding="utf-8")
        )
        self.assertEqual(architecture, index["architecture_components"])
        architecture_html = (
            output / "architecture-components" / "index.html"
        ).read_text(
            encoding="utf-8",
        )
        self.assertIn("Architecture Components", architecture_html)
        self.assertIn("actor.session-state", architecture_html)
        self.assertIn("not a Python call graph", architecture_html)
        self.assertIn("stylesheets/markeitech.css", architecture_html)
        self.assertNotIn("architecture.component.id:", architecture_html)
        public_paths = {
            entry["canonical"] for entry in index["public_surface"]["entries"]
        }
        self.assertNotIn(
            "markeitech.intelligence.actors.SessionStateActor",
            public_paths,
        )

        for path in output.rglob("*"):
            if path.is_file() and path.suffix in {".css", ".html", ".json", ".txt", ".xml"}:
                value = path.read_text(encoding="utf-8")
                self.assertNotIn("Markeitech Metadata:", value)
                self.assertNotIn(str(paths.repository_root), value)


if __name__ == "__main__":
    unittest.main()
