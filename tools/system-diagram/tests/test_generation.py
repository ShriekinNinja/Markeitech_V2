from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree

from markeitech_system_diagram import load_manifest
from markeitech_system_diagram.render import (
    _DARK_THEME,
    _component_card_label,
    _graph_header,
    generate_all,
)
from markeitech_system_diagram.source_census import validate_source_census
from markeitech_system_diagram.view_model import select_view

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).parent / "fixtures" / "minimal-valid.toml"
CANONICAL = REPOSITORY_ROOT / "tools" / "system-diagram" / "docs" / "system-dataflow.toml"
GENERATED = REPOSITORY_ROOT / "tools" / "system-diagram" / "docs" / "generated"


def _tree_digest(directory: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in directory.iterdir() if item.is_file()):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _relative_luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: str, second: str) -> float:
    light, dark = sorted(
        (_relative_luminance(first), _relative_luminance(second)), reverse=True
    )
    return (light + 0.05) / (dark + 0.05)


class GenerationTests(unittest.TestCase):
    def test_dark_theme_meets_text_and_graphical_contrast_contract(self) -> None:
        text_pairs = (
            ("canvas_text", "canvas"),
            ("cluster_text", "cluster_fill"),
            ("current_text", "current_fill"),
            ("actor_text", "actor_fill"),
            ("external_text", "external_fill"),
            ("current_text", "future_fill"),
            ("disabled_text", "disabled_fill"),
            ("store_text", "store_fill"),
            ("worker_text", "worker_fill"),
            ("projection_text", "projection_fill"),
            ("historical_text", "historical_fill"),
            ("data_edge_text", "canvas"),
            ("persistence_edge_text", "canvas"),
            ("projection_edge_text", "canvas"),
            ("failure_edge_text", "canvas"),
            ("actor_text", "badge_enabled"),
            ("current_text", "badge_enabled"),
            ("disabled_text", "badge_disabled"),
            ("external_text", "badge_external"),
            ("current_text", "badge_future"),
            ("historical_text", "badge_historical"),
        )
        graphical_pairs = (
            ("cluster_border", "cluster_fill"),
            ("current_border", "current_fill"),
            ("actor_border", "actor_fill"),
            ("external_border", "external_fill"),
            ("future_border", "future_fill"),
            ("disabled_border", "disabled_fill"),
            ("store_border", "store_fill"),
            ("worker_border", "worker_fill"),
            ("projection_border", "projection_fill"),
            ("historical_border", "historical_fill"),
            ("data_edge", "canvas"),
            ("persistence_edge", "canvas"),
            ("projection_edge", "canvas"),
            ("failure_edge", "canvas"),
        )
        for foreground, background in text_pairs:
            self.assertGreaterEqual(
                _contrast(_DARK_THEME[foreground], _DARK_THEME[background]),
                4.5,
                foreground,
            )
        for foreground, background in graphical_pairs:
            self.assertGreaterEqual(
                _contrast(_DARK_THEME[foreground], _DARK_THEME[background]),
                3.0,
                foreground,
            )

    def test_html_card_and_header_escape_manifest_text(self) -> None:
        manifest = load_manifest(CANONICAL, repository_root=REPOSITORY_ROOT)
        selected = select_view(manifest, "view.current-runtime")
        component = replace(
            selected.components[0],
            id='actor.escape-test[one]&"two"',
            label='<Actor & "quoted">',
        )
        card = _component_card_label(component, selected.definition.profile)
        self.assertIn("&lt;Actor &amp; &quot;quoted&quot;&gt;", card)
        self.assertIn("actor.escape-test[one]&amp;&quot;two&quot;", card)
        self.assertNotIn('<Actor & "quoted">', card)

        escaped_view = replace(selected.definition, label='<View & "quoted">')
        header = _graph_header(manifest, replace(selected, definition=escaped_view))
        self.assertIn("&lt;View &amp; &quot;quoted&quot;&gt;", header)
        self.assertNotIn('<View & "quoted">', header)

    def test_canonical_manifest_passes_source_and_configuration_census(self) -> None:
        manifest = load_manifest(CANONICAL, repository_root=REPOSITORY_ROOT)
        report = validate_source_census(manifest, repository_root=REPOSITORY_ROOT)

        self.assertEqual(len(report.actor_registrations), 19)
        self.assertEqual(report.checked_profiles, ("profile.v3-es-minimal",))
        self.assertGreaterEqual(len(report.contract_constants), 20)

    def test_view_selection_uses_only_explicit_edges(self) -> None:
        manifest = load_manifest(CANONICAL, repository_root=REPOSITORY_ROOT)
        selected = select_view(manifest, "view.complete-inventory")

        self.assertEqual(len(selected.components), 35)
        self.assertEqual(len(selected.tombstones), 5)
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

    def test_generated_canonical_views_use_opaque_dark_theme(self) -> None:
        manifest = load_manifest(CANONICAL, repository_root=REPOSITORY_ROOT)
        theme = next(style for style in manifest.styles if style.id == "style.theme")
        self.assertEqual(theme.label, "Markeitech polished dark theme v2")

        retired_light_colors = {
            "#FFFFFF",
            "#EEF3F6",
            "#F6F0FF",
            "#F2F2F2",
            "#FFF8E8",
            "#E9F5F1",
            "#EAF2FF",
            "#F7F4EC",
            "#F7FAFC",
        }
        for view in manifest.views:
            stem = view.id.removeprefix("view.")
            dot = (GENERATED / f"{stem}.dot").read_text(encoding="utf-8")
            svg = (GENERATED / f"{stem}.svg").read_text(encoding="utf-8")
            self.assertIn(f'bgcolor="{_DARK_THEME["canvas"]}"', dot)
            self.assertIn(f'fontcolor="{_DARK_THEME["canvas_text"]}"', dot)
            self.assertIn('id="boundary.process"', dot)
            self.assertIn("IMPLEMENTATION:", dot)
            self.assertIn("CHECKOUT EVIDENCE:", dot)
            self.assertNotIn("[...]", dot)
            self.assertNotIn("image=", dot)
            self.assertIn(f'fill="{_DARK_THEME["canvas"].lower()}"', svg)
            for color in retired_light_colors:
                self.assertNotIn(color, dot)

    def test_generated_hash_manifest_matches_every_listed_artifact(self) -> None:
        for line in (GENERATED / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
            expected, filename = line.split("  ", 1)
            observed = hashlib.sha256((GENERATED / filename).read_bytes()).hexdigest()
            self.assertEqual(observed, expected)


if __name__ == "__main__":
    unittest.main()
