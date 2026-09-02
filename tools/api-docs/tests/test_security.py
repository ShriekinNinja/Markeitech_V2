from __future__ import annotations

import importlib
import socket
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from markeitech_api_docs.build import (
    FixedPaths,
    _scan_output,
    _validate_installed_versions,
    _validate_mkdocs_policy,
    _validate_output_path,
    _validate_stylesheet,
)
from markeitech_api_docs.models import ApiDocsError
from markeitech_api_docs.registry import load_attribute_registry
from markeitech_api_docs.security import constrained_generation_environment
from markeitech_api_docs.source import load_static_package


class SecurityBoundaryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tool_root = Path(__file__).resolve().parents[1]
        self.registry = load_attribute_registry(
            self.tool_root / "schema" / "attribute-registry.toml"
        )

    def test_import_canary_is_loaded_without_execution(self) -> None:
        fixture_root = self.tool_root / "tests" / "fixtures" / "import-canary"
        with constrained_generation_environment():
            package, extension = load_static_package(fixture_root, self.registry)
            self.assertEqual(package.path, "markeitech")
            self.assertNotIn("markeitech", sys.modules)
            self.assertIn(
                "DO_NOT_RENDER_IMPORT_CANARY_SENTINEL",
                extension.protected_literals,
            )

    def test_target_import_is_denied(self) -> None:
        with constrained_generation_environment():
            with self.assertRaisesRegex(ApiDocsError, "TARGET_IMPORT_DENIED"):
                importlib.import_module("markeitech")

    def test_network_and_subprocess_are_denied(self) -> None:
        with constrained_generation_environment():
            with self.assertRaisesRegex(ApiDocsError, "NETWORK_DENIED"):
                socket.socket()
            with self.assertRaisesRegex(ApiDocsError, "SUBPROCESS_DENIED"):
                subprocess.run(["true"], check=False)

    def test_unapproved_mkdocs_hook_is_denied(self) -> None:
        source = (self.tool_root / "mkdocs.yml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "mkdocs.yml"
            config.write_text(f"{source}\nhooks:\n  - arbitrary.py\n", encoding="utf-8")
            with self.assertRaisesRegex(ApiDocsError, "top-level policy"):
                _validate_mkdocs_policy(config)

    def test_remote_or_hiding_stylesheet_rules_are_denied(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            stylesheet = Path(temporary) / "markeitech.css"
            for unsafe in (
                "@import 'https://example.invalid/theme.css';\n",
                ".item { background: url(//example.invalid/image.png); }\n",
                "@font-face { font-family: remote; src: url(font.woff2); }\n",
            ):
                with self.subTest(unsafe=unsafe):
                    stylesheet.write_text(unsafe, encoding="utf-8")
                    with self.assertRaisesRegex(ApiDocsError, "unsafe asset"):
                        _validate_stylesheet(stylesheet)
            stylesheet.write_text(".warning { display: none; }\n")
            with self.assertRaisesRegex(ApiDocsError, "content-hiding"):
                _validate_stylesheet(stylesheet)

    def test_generated_remote_auto_fetching_assets_are_denied(self) -> None:
        fragments = (
            '<img src="https://example.invalid/image.png">',
            '<source srcset="//example.invalid/image.png">',
            '<iframe src="http://example.invalid/embed"></iframe>',
            '<object data="https://example.invalid/object"></object>',
        )
        for fragment in fragments:
            with self.subTest(fragment=fragment), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / "index.html").write_text(fragment, encoding="utf-8")
                with self.assertRaisesRegex(ApiDocsError, "remote auto-fetching"):
                    _scan_output(root, (), root / "repository")

    def test_output_is_fixed_to_repository_docs_api(self) -> None:
        paths = FixedPaths.discover()
        self.assertEqual(paths.output, paths.repository_root / "docs" / "api")
        _validate_output_path(paths)

        with tempfile.TemporaryDirectory() as temporary:
            repository_root = Path(temporary)
            (repository_root / "docs").mkdir()
            redirected = replace(
                paths,
                repository_root=repository_root,
                output=repository_root / "site",
            )
            with self.assertRaisesRegex(ApiDocsError, "fixed repository API site"):
                _validate_output_path(redirected)

    def test_output_symlinks_are_denied(self) -> None:
        paths = FixedPaths.discover()
        with (
            tempfile.TemporaryDirectory() as temporary,
            tempfile.TemporaryDirectory() as external,
        ):
            repository_root = Path(temporary)
            documentation_root = repository_root / "docs"
            documentation_root.symlink_to(Path(external), target_is_directory=True)
            unsafe_parent = replace(
                paths,
                repository_root=repository_root,
                output=documentation_root / "api",
            )
            with self.assertRaisesRegex(ApiDocsError, "documentation root is unsafe"):
                _validate_output_path(unsafe_parent)

        with tempfile.TemporaryDirectory() as temporary:
            repository_root = Path(temporary)
            documentation_root = repository_root / "docs"
            documentation_root.mkdir()
            target = repository_root / "elsewhere"
            target.mkdir()
            (documentation_root / "api").symlink_to(target, target_is_directory=True)
            unsafe_output = replace(
                paths,
                repository_root=repository_root,
                output=documentation_root / "api",
            )
            with self.assertRaisesRegex(ApiDocsError, "output cannot be a symlink"):
                _validate_output_path(unsafe_output)

    def test_tracked_stylesheet_freezes_dark_full_width_overflow_contract(self) -> None:
        stylesheet = self.tool_root / "docs" / "stylesheets" / "markeitech.css"
        _validate_stylesheet(stylesheet)
        value = stylesheet.read_text(encoding="utf-8")
        for required in (
            "color-scheme: dark",
            "max-width: none",
            "overflow-x: auto",
            "overflow-wrap: anywhere",
            "word-break: break-word",
            "min-width: max(100%, 60rem)",
        ):
            with self.subTest(required=required):
                self.assertIn(required, value)
        self.assertNotIn("overflow: hidden", value)

    def test_installed_dependency_drift_is_denied(self) -> None:
        with patch(
            "markeitech_api_docs.build.importlib.metadata.distributions",
            return_value=(),
        ):
            with self.assertRaisesRegex(ApiDocsError, "installed documentation closure"):
                _validate_installed_versions(self.tool_root / "uv.lock")


if __name__ == "__main__":
    unittest.main()
