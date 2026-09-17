"""Exercise discoverability and retirement failures using isolated package copies."""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "plugins/kite/scripts/validate_skill_library.py"
SPEC = importlib.util.spec_from_file_location("kite_library", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
LIBRARY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LIBRARY)


class LibraryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "plugins/kite", self.root / "plugins/kite")
        self.skill = self.root / "plugins/kite/skills/markeitech-advisor-router"

    def test_library_has_resolvable_skill_entrypoints(self) -> None:
        self.assertEqual(LIBRARY.validate(self.root), [])

    def test_broken_reference_is_reported(self) -> None:
        (self.skill / "references/skill-index.md").unlink()
        self.assertTrue(any("Broken local link" in e for e in LIBRARY.validate(self.root)))

    def test_old_project_role_cannot_silently_survive_migration(self) -> None:
        path = self.root / ".codex/agents/markeitech-nautilus-advisor.toml"
        path.parent.mkdir(parents=True)
        path.write_text('name = "markeitech_nautilus_advisor"\n')
        self.assertTrue(any("still discoverable" in e for e in LIBRARY.validate(self.root)))

    def test_unrelated_project_agents_are_preserved(self) -> None:
        path = self.root / ".codex/agents/unrelated.toml"
        path.parent.mkdir(parents=True)
        path.write_text('name = "unrelated"\n')
        self.assertEqual(LIBRARY.validate(self.root), [])
        self.assertTrue(path.is_file())

    def test_implicit_activation_is_rejected(self) -> None:
        path = self.skill / "agents/openai.yaml"
        path.write_text(path.read_text().replace(
            "allow_implicit_invocation: false", "allow_implicit_invocation: true"
        ))
        self.assertTrue(any("Explicit-only" in e for e in LIBRARY.validate(self.root)))


if __name__ == "__main__":
    unittest.main()
