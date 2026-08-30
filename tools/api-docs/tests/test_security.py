from __future__ import annotations

import importlib
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from markeitech_api_docs.build import _validate_installed_versions, _validate_mkdocs_policy
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

    def test_installed_dependency_drift_is_denied(self) -> None:
        with patch(
            "markeitech_api_docs.build.importlib.metadata.distributions",
            return_value=(),
        ):
            with self.assertRaisesRegex(ApiDocsError, "installed documentation closure"):
                _validate_installed_versions(self.tool_root / "uv.lock")


if __name__ == "__main__":
    unittest.main()
