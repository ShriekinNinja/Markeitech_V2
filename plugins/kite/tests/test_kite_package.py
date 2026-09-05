"""Package maintenance tests use disposable local directories, never the host cache."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import tomllib
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts/kite-package.py"
SPEC = importlib.util.spec_from_file_location("kite_package", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
PACKAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKAGE)


class PackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / ".codex-plugin/plugin.json"
        self.policy = self.root / "skills/markeitech-advisor-router/references/council-policy.toml"
        self.manifest.parent.mkdir(parents=True)
        self.policy.parent.mkdir(parents=True)
        self.manifest.write_text(
            json.dumps({"name": "kite", "version": "0.1.0+codex.20260801000000"})
        )
        self.policy.write_text('plugin_version = "0.1.0+codex.20260801000000"\n')

    def test_bump_preserves_base_and_updates_both_owners(self) -> None:
        version = PACKAGE.bump(self.root, "20260905210000")
        self.assertEqual(version, "0.1.0+codex.20260905210000")
        self.assertEqual(json.loads(self.manifest.read_text())["version"], version)
        self.assertEqual(tomllib.loads(self.policy.read_text())["plugin_version"], version)
        before = PACKAGE.inventory(self.root)
        with self.assertRaisesRegex(ValueError, "VERSION_UNCHANGED"):
            PACKAGE.bump(self.root, "20260905210000")
        self.assertEqual(before, PACKAGE.inventory(self.root))

    def test_mismatch_or_bad_stamp_does_not_mutate(self) -> None:
        before = PACKAGE.inventory(self.root)
        with self.assertRaises(ValueError):
            PACKAGE.bump(self.root, "20261301000000")
        self.assertEqual(before, PACKAGE.inventory(self.root))
        self.policy.write_text('plugin_version = "other"\n')
        before = PACKAGE.inventory(self.root)
        with self.assertRaisesRegex(ValueError, "SOURCE_VERSION_MISMATCH"):
            PACKAGE.bump(self.root, "20260905210000")
        self.assertEqual(before, PACKAGE.inventory(self.root))

    def test_identity_includes_extra_content_and_rejects_symlinks(self) -> None:
        before = PACKAGE.identity(self.root)
        extra = self.root / "unexpected.txt"
        extra.write_text("extra")
        self.assertNotEqual(before["sha256"], PACKAGE.identity(self.root)["sha256"])
        extra.unlink()
        self.assertEqual(before, PACKAGE.identity(self.root))
        extra.symlink_to(self.manifest)
        with self.assertRaisesRegex(ValueError, "PACKAGE_SYMLINK"):
            PACKAGE.identity(self.root)


if __name__ == "__main__":
    unittest.main()
