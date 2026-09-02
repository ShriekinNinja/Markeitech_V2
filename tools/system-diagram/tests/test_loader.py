from __future__ import annotations

import ast
import os
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from markeitech_system_diagram import ManifestError, load_manifest
from markeitech_system_diagram.models import ImplementationState, OutputFormat

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).parent / "fixtures" / "minimal-valid.toml"
SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src" / "markeitech_system_diagram"
APPROVED_TOOL_IMPORTS = {"diagrams"}


class ManifestLoaderTests(unittest.TestCase):
    def _load_text(self, text: str):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "manifest.toml"
            path.write_text(text, encoding="utf-8")
            return load_manifest(path, repository_root=root)

    def _error_for(self, text: str) -> ManifestError:
        with self.assertRaises(ManifestError) as raised:
            self._load_text(text)
        return raised.exception

    def test_loads_valid_manifest_into_sorted_immutable_models(self) -> None:
        manifest = load_manifest(FIXTURE, repository_root=REPOSITORY_ROOT)

        self.assertEqual(manifest.header.schema_version, 1)
        self.assertTrue(manifest.header.not_runtime_configuration)
        self.assertEqual(manifest.header.default_profile, "profile.v3")
        self.assertEqual(
            tuple(style.id for style in manifest.styles),
            ("style.current", "style.flow", "style.theme"),
        )
        self.assertEqual(
            manifest.components[0].implementation_state,
            ImplementationState.IMPLEMENTED,
        )
        self.assertIn(OutputFormat.MARKDOWN, manifest.views[0].formats)
        self.assertEqual(manifest.views[0].node_separation, 0.4)
        self.assertEqual(manifest.views[0].rank_separation, 0.75)
        with self.assertRaises(FrozenInstanceError):
            manifest.header.title = "mutated"  # type: ignore[misc]

    def test_rejects_out_of_range_rank_separation(self) -> None:
        text = FIXTURE.read_text().replace(
            "rank_separation = 0.75",
            "rank_separation = 0.1",
        )
        error = self._error_for(text)
        self.assertEqual(error.code, "MANIFEST_TYPE")

    def test_loads_repository_relative_manifest_path(self) -> None:
        relative_path = FIXTURE.relative_to(REPOSITORY_ROOT)
        manifest = load_manifest(relative_path, repository_root=REPOSITORY_ROOT)
        self.assertEqual(manifest.header.id, "markeitech-v3-system-dataflow")

    def test_rejects_unknown_root_field(self) -> None:
        error = self._error_for('unknown_root = "forbidden"\n' + FIXTURE.read_text())
        self.assertEqual(error.code, "MANIFEST_UNKNOWN_FIELD")
        self.assertNotIn("forbidden", str(error))

    def test_rejects_unknown_nested_field(self) -> None:
        text = FIXTURE.read_text().replace(
            'limitations = ["No current order submission or execution"]',
            'limitations = ["No current order submission or execution"]\nunknown = true',
            1,
        )
        error = self._error_for(text)
        self.assertEqual(error.code, "MANIFEST_UNKNOWN_FIELD")

    def test_rejects_duplicate_ids_across_record_families(self) -> None:
        text = FIXTURE.read_text().replace(
            'id = "view.current-v3"', 'id = "actor.data-acquisition"'
        )
        error = self._error_for(text)
        self.assertEqual(error.code, "MANIFEST_DUPLICATE_ID")

    def test_rejects_dangling_contract_reference(self) -> None:
        text = FIXTURE.read_text().replace(
            'contract = "contract.native-bar"', 'contract = "contract.absent"'
        )
        error = self._error_for(text)
        self.assertEqual(error.code, "MANIFEST_DANGLING_REFERENCE")

    def test_allows_tombstone_replacement_with_active_edge(self) -> None:
        text = FIXTURE.read_text() + """

[[tombstones]]
id = "tombstone.provider-to-acquisition"
label = "Former provider-to-acquisition edge"
former_kind = "edge"
former_boundary = "boundary.node"
disposition = "removed"
removed_at_commit = "c6fe2ad89ae2da077d08c55998cc9ff639c5f0ce"
replacement = "edge.provider-to-acquisition"
evidence = ["evidence.current-status"]
limitations = ["Fixture tombstone only"]
"""

        manifest = self._load_text(text)

        self.assertEqual(
            manifest.tombstones[0].replacement,
            "edge.provider-to-acquisition",
        )

    def test_rejects_unsafe_evidence_path(self) -> None:
        text = FIXTURE.read_text().replace(
            'source_path = "docs/current-status.md"', 'source_path = "../.env"'
        )
        error = self._error_for(text)
        self.assertEqual(error.code, "MANIFEST_UNSAFE_REPOSITORY_PATH")

    def test_rejects_local_profile_path(self) -> None:
        text = FIXTURE.read_text().replace(
            'config_path = "v2/config/system.v3-es-minimal.toml"',
            'config_path = "v2/config/system.local.toml"',
        )
        error = self._error_for(text)
        self.assertEqual(error.code, "MANIFEST_PROFILE_PATH")

    def test_rejects_exactly_once_delivery_claim(self) -> None:
        text = FIXTURE.read_text().replace('guarantee = "unknown"', 'guarantee = "exactly_once"')
        error = self._error_for(text)
        self.assertEqual(error.code, "MANIFEST_ENUM")

    def test_rejects_current_view_with_future_component(self) -> None:
        text = FIXTURE.read_text().replace(
            'implementation_state = "implemented"',
            'implementation_state = "future"',
            1,
        ).replace('temporal_status = "current"', 'temporal_status = "future"', 3)
        error = self._error_for(text)
        self.assertEqual(error.code, "MANIFEST_CURRENT_VIEW_STATUS")

    def test_rejects_current_view_filter_that_admits_future_records(self) -> None:
        text = FIXTURE.read_text().replace(
            'include_temporal_status = ["current"]',
            'include_temporal_status = ["current", "future"]',
        )
        error = self._error_for(text)
        self.assertEqual(error.code, "MANIFEST_CURRENT_VIEW_FILTER")

    def test_requires_markdown_accessibility_companion(self) -> None:
        text = FIXTURE.read_text().replace(
            'formats = ["svg", "png", "dot", "md"]',
            'formats = ["svg", "png", "dot"]',
        )
        error = self._error_for(text)
        self.assertEqual(error.code, "MANIFEST_ACCESSIBILITY_COMPANION")

    def test_rejects_runtime_authority(self) -> None:
        text = FIXTURE.read_text().replace(
            "not_runtime_configuration = true",
            "not_runtime_configuration = false",
        )
        error = self._error_for(text)
        self.assertEqual(error.code, "MANIFEST_RUNTIME_AUTHORITY_FORBIDDEN")

    def test_requires_no_execution_banner(self) -> None:
        text = FIXTURE.read_text().replace(
            "no_execution_banner = true",
            "no_execution_banner = false",
        )
        error = self._error_for(text)
        self.assertEqual(error.code, "MANIFEST_EXECUTION_BOUNDARY")

    def test_rejects_symlink_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.toml"
            target.write_text(FIXTURE.read_text(), encoding="utf-8")
            link = root / "manifest.toml"
            os.symlink(target, link)
            with self.assertRaises(ManifestError) as raised:
                load_manifest(link, repository_root=root)
        self.assertEqual(raised.exception.code, "MANIFEST_UNSAFE_PATH")

    def test_rejects_manifest_beneath_symlinked_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            actual = root / "actual"
            actual.mkdir()
            target = actual / "manifest.toml"
            target.write_text(FIXTURE.read_text(), encoding="utf-8")
            linked_directory = root / "linked"
            os.symlink(actual, linked_directory)
            with self.assertRaises(ManifestError) as raised:
                load_manifest(linked_directory / "manifest.toml", repository_root=root)
        self.assertEqual(raised.exception.code, "MANIFEST_UNSAFE_PATH")

    def test_package_has_no_runtime_or_network_imports(self) -> None:
        violations: list[str] = []
        for source_path in sorted(SOURCE_ROOT.glob("*.py")):
            tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root = alias.name.split(".", 1)[0]
                        if (
                            root not in sys.stdlib_module_names
                            and root not in APPROVED_TOOL_IMPORTS
                        ):
                            violations.append(f"{source_path.name}:{node.lineno}:{alias.name}")
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    root = node.module.split(".", 1)[0]
                    if root not in sys.stdlib_module_names and root not in APPROVED_TOOL_IMPORTS:
                        violations.append(f"{source_path.name}:{node.lineno}:{node.module}")
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
