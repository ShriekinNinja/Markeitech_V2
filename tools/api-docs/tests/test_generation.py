from __future__ import annotations

import json
import unittest

from markeitech_api_docs.build import FixedPaths, check, generate
from markeitech_api_docs.models import ApiDocsError


class GenerationTest(unittest.TestCase):
    def test_generation_is_repeatable_and_sanitized(self) -> None:
        paths = FixedPaths.discover()
        source = paths.source_root / "intelligence" / "actors.py"
        source_before = source.read_bytes()
        first = generate()
        second = generate()
        self.assertEqual(first["artifact_set_sha256"], second["artifact_set_sha256"])
        self.assertEqual(first["selected"], 261)
        self.assertEqual(source.read_bytes(), source_before)

        self.assertEqual(paths.output, paths.repository_root / "docs" / "api")
        output = paths.output
        index = json.loads((output / "metadata-index.json").read_text(encoding="utf-8"))
        self.assertEqual(index["authority"], "non_authoritative_discovery_only")
        self.assertTrue(index["not_runtime_configuration"])
        self.assertEqual(index["public_surface"]["selected"], 261)
        self.assertEqual(index["metadata"]["occurrence_count"], 0)
        self.assertEqual(index["architecture_components"]["counts"]["components"], 20)
        self.assertEqual(
            index["architecture_components"]["counts"]["with_responsibilities"],
            7,
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
        self.assertIn('class="markeitech-metadata"', architecture_html)
        self.assertIn('class="markeitech-responsibilities"', architecture_html)
        self.assertIn("<h4>Responsibilities</h4>", architecture_html)
        self.assertIn("Markeitech Metadata", architecture_html)
        self.assertIn("architecture.component.responsibilities", architecture_html)
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

    def test_check_is_repeatable_and_detects_drift(self) -> None:
        paths = FixedPaths.discover()
        generate()
        index = check()
        self.assertEqual(index["mode"], "check")
        self.assertIn("artifact_set_sha256", index)
        again = check()
        self.assertEqual(index["artifact_set_sha256"], again["artifact_set_sha256"])

        index_marker = (paths.tool_root / "docs" / "index.md")
        original = index_marker.read_text(encoding="utf-8")
        index_marker.write_text(f"{original}\n", encoding="utf-8")
        try:
            with self.assertRaisesRegex(ApiDocsError, "OUTPUT_DRIFT"):
                check()
        finally:
            index_marker.write_text(original, encoding="utf-8")
        healed = check()
        self.assertEqual(index["artifact_set_sha256"], healed["artifact_set_sha256"])

    def test_check_rejects_tampered_committed_output(self) -> None:
        paths = FixedPaths.discover()
        generate()
        output = paths.output
        index_path = output / "artifact-index.json"
        original = index_path.read_text(encoding="utf-8")
        index_path.write_text("{\"tampered\":true}", encoding="utf-8")
        try:
            with self.assertRaisesRegex(ApiDocsError, "OUTPUT_DRIFT"):
                check()
        finally:
            index_path.write_text(original, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
