from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from markeitech_system_diagram import load_manifest
from markeitech_system_diagram.render import generate_all
from markeitech_system_diagram.source_census import validate_source_census
from markeitech_system_diagram.view_model import select_view

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).parent / "fixtures" / "minimal-valid.toml"
CANONICAL = REPOSITORY_ROOT / "docs" / "architecture" / "system-dataflow.toml"
GENERATED = REPOSITORY_ROOT / "docs" / "architecture" / "generated" / "system-dataflow"


def _tree_digest(directory: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in directory.iterdir() if item.is_file()):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


class GenerationTests(unittest.TestCase):
    def test_canonical_manifest_passes_source_and_configuration_census(self) -> None:
        manifest = load_manifest(CANONICAL, repository_root=REPOSITORY_ROOT)
        report = validate_source_census(manifest, repository_root=REPOSITORY_ROOT)

        self.assertEqual(len(report.actor_registrations), 17)
        self.assertEqual(report.checked_profiles, ("profile.v3-es-minimal",))
        self.assertGreaterEqual(len(report.contract_constants), 20)

    def test_view_selection_uses_only_explicit_edges(self) -> None:
        manifest = load_manifest(CANONICAL, repository_root=REPOSITORY_ROOT)
        selected = select_view(manifest, "view.complete-inventory")

        self.assertEqual(len(selected.components), 33)
        self.assertEqual(len(selected.tombstones), 2)
        self.assertEqual(selected.edges, ())

    def test_fixture_generation_is_repeatable_and_complete(self) -> None:
        manifest = load_manifest(FIXTURE, repository_root=REPOSITORY_ROOT)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "generated"
            first = generate_all(manifest, manifest_path=FIXTURE, output_directory=output)
            first_digest = _tree_digest(output)
            second = generate_all(manifest, manifest_path=FIXTURE, output_directory=output)

            self.assertEqual(first.artifact_count, 6)
            self.assertEqual(second.artifact_count, 6)
            self.assertEqual(first_digest, _tree_digest(output))
            self.assertEqual(
                sorted(path.name for path in output.iterdir()),
                [
                    "SHA256SUMS",
                    "artifact-index.json",
                    "current-v3.dot",
                    "current-v3.md",
                    "current-v3.png",
                    "current-v3.svg",
                ],
            )

    def test_generated_canonical_views_preserve_selected_identities(self) -> None:
        manifest = load_manifest(CANONICAL, repository_root=REPOSITORY_ROOT)
        index = json.loads((GENERATED / "artifact-index.json").read_text(encoding="utf-8"))
        self.assertEqual(len(index["views"]), len(manifest.views))

        for view in manifest.views:
            selected = select_view(manifest, view.id)
            stem = view.id.removeprefix("view.")
            dot = (GENERATED / f"{stem}.dot").read_text(encoding="utf-8")
            svg_root = ElementTree.parse(GENERATED / f"{stem}.svg").getroot()
            svg_ids = {
                element.attrib["id"]
                for element in svg_root.iter()
                if "id" in element.attrib
            }
            markdown = (GENERATED / f"{stem}.md").read_text(encoding="utf-8")
            for component in selected.components:
                self.assertIn(f'id="{component.id}"', dot)
                self.assertIn(component.id, svg_ids)
                self.assertIn(f"`{component.id}`", markdown)
            for capability in selected.capabilities:
                self.assertIn(f"`{capability.id}`", markdown)
            for tombstone in selected.tombstones:
                self.assertIn(f'id="{tombstone.id}"', dot)
                self.assertIn(tombstone.id, svg_ids)
                self.assertIn(f"`{tombstone.id}`", markdown)
            for edge in selected.edges:
                self.assertIn(f'id="{edge.id}"', dot)
                self.assertIn(edge.id, svg_ids)
                self.assertIn(f"`{edge.id}`", markdown)

    def test_generated_hash_manifest_matches_every_listed_artifact(self) -> None:
        for line in (GENERATED / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
            expected, filename = line.split("  ", 1)
            observed = hashlib.sha256((GENERATED / filename).read_bytes()).hexdigest()
            self.assertEqual(observed, expected)


if __name__ == "__main__":
    unittest.main()
