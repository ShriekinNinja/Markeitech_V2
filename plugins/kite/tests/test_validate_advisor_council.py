from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
VALIDATOR_PATH = (
    REPOSITORY_ROOT / "plugins" / "kite" / "scripts" / "validate_advisor_council.py"
)
SPEC = importlib.util.spec_from_file_location("validate_advisor_council", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"unable to load {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class AdvisorCouncilValidatorTests(unittest.TestCase):
    def copy_validation_tree(self, destination: Path) -> None:
        for relative in (Path(".codex"), Path(".agents"), Path("plugins/kite")):
            shutil.copytree(REPOSITORY_ROOT / relative, destination / relative)
        shutil.copyfile(REPOSITORY_ROOT / "AGENTS.md", destination / "AGENTS.md")

    def test_repository_council_is_valid(self) -> None:
        self.assertEqual(VALIDATOR.validate_repo(REPOSITORY_ROOT), [])

    def test_cycle_detection_returns_the_cycle(self) -> None:
        graph = {"first": ["second"], "second": ["third"], "third": ["first"]}
        self.assertEqual(
            VALIDATOR.find_cycle(graph),
            ["first", "second", "third", "first"],
        )

    def test_acyclic_dependencies_pass(self) -> None:
        graph = {"first": [], "second": ["first"], "third": ["second"]}
        self.assertIsNone(VALIDATOR.find_cycle(graph))

    def test_duplicate_detection_is_order_independent(self) -> None:
        self.assertEqual(VALIDATOR.duplicates(["a", "b", "a", "c", "b"]), {"a", "b"})

    def test_router_cannot_enable_implicit_invocation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_validation_tree(root)
            interface = (
                root
                / "plugins/kite/skills/markeitech-advisor-router/agents/openai.yaml"
            )
            interface.write_text(
                interface.read_text(encoding="utf-8").replace(
                    "allow_implicit_invocation: false",
                    "allow_implicit_invocation: true",
                ),
                encoding="utf-8",
            )
            self.assertTrue(
                any(
                    "router skill must set allow_implicit_invocation false" in error
                    for error in VALIDATOR.validate_repo(root)
                )
            )

    def test_activation_policy_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_validation_tree(root)
            policy = (
                root
                / "plugins/kite/skills/markeitech-advisor-router/references/council-policy.toml"
            )
            policy.write_text(
                policy.read_text(encoding="utf-8").replace(
                    'fresh_session = "normal_codex"',
                    'fresh_session = "kite"',
                ),
                encoding="utf-8",
            )
            self.assertIn(
                "policy defaults.fresh_session must be 'normal_codex'",
                VALIDATOR.validate_repo(root),
            )

    def test_inactive_activation_case_cannot_route(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_validation_tree(root)
            cases = (
                root
                / "plugins/kite/skills/markeitech-advisor-router/references/routing-cases.toml"
            )
            cases.write_text(
                cases.read_text(encoding="utf-8").replace(
                    'class = "ordinary_substantive_default"\n'
                    'prompt = "Review this substantive Markeitech architecture proposal without '
                    'invoking Kite."\n'
                    'activation_source = "none"\n'
                    'kite_active = false\n'
                    'router_expected = false',
                    'class = "ordinary_substantive_default"\n'
                    'prompt = "Review this substantive Markeitech architecture proposal without '
                    'invoking Kite."\n'
                    'activation_source = "none"\n'
                    'kite_active = false\n'
                    'router_expected = true',
                ),
                encoding="utf-8",
            )
            self.assertTrue(
                any(
                    "inactive Kite cannot route or invoke advisors" in error
                    for error in VALIDATOR.validate_repo(root)
                )
            )

    def test_explicit_specialist_cannot_promote_kite_or_router(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_validation_tree(root)
            cases = (
                root
                / "plugins/kite/skills/markeitech-advisor-router/references/routing-cases.toml"
            )
            cases.write_text(
                cases.read_text(encoding="utf-8").replace(
                    'class = "explicit_specialist"\n'
                    'prompt = "Use $kite:markeitech-security-tool-boundary-expert to review this '
                    'tool boundary."\n'
                    'activation_source = "explicit_specialist"\n'
                    'kite_active = false\n'
                    'router_expected = false',
                    'class = "explicit_specialist"\n'
                    'prompt = "Use $kite:markeitech-security-tool-boundary-expert to review this '
                    'tool boundary."\n'
                    'activation_source = "explicit_specialist"\n'
                    'kite_active = false\n'
                    'router_expected = true',
                ),
                encoding="utf-8",
            )
            errors = VALIDATOR.validate_repo(root)
            self.assertTrue(
                any(
                    "inactive Kite cannot route or invoke advisors" in error
                    or "activation class explicit_specialist requires" in error
                    for error in errors
                )
            )

    def test_plugin_default_prompts_must_explicitly_invoke_router(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_validation_tree(root)
            manifest = root / "plugins/kite/.codex-plugin/plugin.json"
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace(
                    "Use $kite:markeitech-advisor-router to activate Kite and review this "
                    "Markeitech batch defect-first.",
                    "Review this Markeitech batch defect-first.",
                ),
                encoding="utf-8",
            )
            self.assertIn(
                "every plugin defaultPrompt must explicitly invoke the Kite router",
                VALIDATOR.validate_repo(root),
            )

    def test_agents_md_cannot_restore_automatic_kite_invocation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_validation_tree(root)
            agents = root / "AGENTS.md"
            agents.write_text(
                agents.read_text(encoding="utf-8")
                + "\nAutomatically invoke the bundled "
                + "`$kite:markeitech-advisor-router` before work.\n",
                encoding="utf-8",
            )
            self.assertIn(
                "AGENTS.md must not automatically invoke Kite from ordinary prompts",
                VALIDATOR.validate_repo(root),
            )

    def test_specialist_cannot_enable_implicit_invocation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_validation_tree(root)
            interface = (
                root
                / "plugins/kite/skills/markeitech-security-tool-boundary-expert/agents/openai.yaml"
            )
            interface.write_text(
                interface.read_text(encoding="utf-8").replace(
                    "allow_implicit_invocation: false",
                    "allow_implicit_invocation: true",
                ),
                encoding="utf-8",
            )
            self.assertTrue(
                any(
                    "specialist skill must set allow_implicit_invocation false" in error
                    for error in VALIDATOR.validate_repo(root)
                )
            )

    def test_extra_enabled_mcp_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_validation_tree(root)
            agent = (
                root
                / ".codex/agents/markeitech-security-tool-boundary-advisor.toml"
            )
            agent.write_text(
                agent.read_text(encoding="utf-8")
                + "\n[mcp_servers.unapproved]\nenabled = true\n",
                encoding="utf-8",
            )
            self.assertTrue(
                any(
                    "MCP override IDs must exactly match" in error
                    for error in VALIDATOR.validate_repo(root)
                )
            )

    def test_missing_mcp_denial_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_validation_tree(root)
            agent = root / ".codex/agents/markeitech-nautilus-advisor.toml"
            agent.write_text(
                agent.read_text(encoding="utf-8").replace(
                    '\n[mcp_servers.pycharm]\n'
                    'url = "http://127.0.0.1:64462/stream"\n'
                    'enabled = false\n',
                    "\n",
                ),
                encoding="utf-8",
            )
            self.assertTrue(
                any(
                    "MCP override IDs must exactly match" in error
                    for error in VALIDATOR.validate_repo(root)
                )
            )

    def test_disabled_mcp_without_transport_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_validation_tree(root)
            agent = root / ".codex/agents/markeitech-nautilus-advisor.toml"
            agent.write_text(
                agent.read_text(encoding="utf-8").replace(
                    'url = "http://127.0.0.1:64462/stream"\n'
                    'enabled = false\n',
                    'enabled = false\n',
                ),
                encoding="utf-8",
            )
            self.assertTrue(
                any(
                    "must preserve the exact project transport" in error
                    for error in VALIDATOR.validate_repo(root)
                )
            )

    def test_duplicate_custom_role_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_validation_tree(root)
            source = root / ".codex/agents/markeitech-nautilus-advisor.toml"
            duplicate = root / ".codex/agents/markeitech-copy-advisor.toml"
            shutil.copyfile(source, duplicate)
            errors = VALIDATOR.validate_repo(root)
            self.assertTrue(any("expected 20 custom-agent files" in error for error in errors))
            self.assertTrue(any("duplicate custom-agent role name" in error for error in errors))

    def test_generated_plugin_artifact_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_validation_tree(root)
            cache = root / "plugins/kite/scripts/__pycache__"
            cache.mkdir()
            (cache / "validator.pyc").write_bytes(b"not real bytecode")
            self.assertTrue(
                any(
                    "plugin contains generated/cache artifact" in error
                    for error in VALIDATOR.validate_repo(root)
                )
            )

    def test_plugin_policy_version_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_validation_tree(root)
            manifest = root / "plugins/kite/.codex-plugin/plugin.json"
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace(
                    "0.1.0+codex.20260826132235",
                    "0.1.0+codex.invalid",
                ),
                encoding="utf-8",
            )
            self.assertIn(
                "plugin version differs from council policy",
                VALIDATOR.validate_repo(root),
            )

    def test_network_default_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_validation_tree(root)
            policy = (
                root
                / "plugins/kite/skills/markeitech-advisor-router/references/council-policy.toml"
            )
            policy.write_text(
                policy.read_text(encoding="utf-8").replace(
                    'network = "deny"',
                    'network = "approved_public_read_only"',
                    1,
                ),
                encoding="utf-8",
            )
            self.assertIn(
                "policy defaults.network must be 'deny'",
                VALIDATOR.validate_repo(root),
            )

    def test_multi_case_without_edges_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_validation_tree(root)
            cases = (
                root
                / "plugins/kite/skills/markeitech-advisor-router/references/routing-cases.toml"
            )
            cases.write_text(
                cases.read_text(encoding="utf-8").replace(
                    'edges = [["markeitech_architecture_boundaries_advisor", '
                    '"markeitech_event_driven_architecture_advisor"]]\n',
                    "",
                    1,
                ),
                encoding="utf-8",
            )
            self.assertTrue(
                any(
                    "MULTI must declare explicit edges" in error
                    for error in VALIDATOR.validate_repo(root)
                )
            )


if __name__ == "__main__":
    unittest.main()
