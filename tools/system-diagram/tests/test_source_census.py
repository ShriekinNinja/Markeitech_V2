from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from markeitech_system_diagram import ManifestError
from markeitech_system_diagram.source_census import (
    _profile_configuration,
    extract_actor_registrations,
    extract_contract_constants,
)


class SourceCensusTests(unittest.TestCase):
    def test_resolves_relative_policy_and_inline_watchlist_for_profile_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            (root / "config/runtime.example.toml").write_text(
                'schema_version = 30\npolicy_file = "system.policy.toml"\n'
                '[ib]\n[discord]\nenabled = true\n[watchlist]\nenabled = true\n',
            )
            (root / "config/system.policy.toml").write_text(
                "policy_version = 1\n[ib]\n[discord]\nqueue_capacity = 32\n"
                "[watchlist]\nconsumer_retry_interval_ms = 1000\n"
                "[sessions]\n[runtime_resources]\nenabled = true\n",
            )

            raw = _profile_configuration(root, "config/runtime.example.toml")

        self.assertTrue(raw["watchlist"]["enabled"])
        self.assertEqual(raw["watchlist"]["consumer_retry_interval_ms"], 1000)
        self.assertTrue(raw["runtime_resources"]["enabled"])
        self.assertEqual(raw["discord"], {"enabled": True, "queue_capacity": 32})

    def test_extracts_constant_and_bounded_dynamic_actor_registrations(self) -> None:
        source = """
def build():
    ActorRegistration(key="always", actor_id="ALWAYS", config=None)
    ActorRegistration(
        key=f"historical_dependency_probe:{index}",
        actor_id=actor_id,
        config=None,
    )
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "composition.py"
            path.write_text(source, encoding="utf-8")
            facts = extract_actor_registrations(root, "composition.py")
        self.assertEqual(
            tuple((fact.key, fact.actor_id) for fact in facts),
            (
                ("always", "ALWAYS"),
                ("historical_dependency_probe:*", "HISTORICAL-DEPENDENCY-PROBE-*"),
            ),
        )

    def test_fails_closed_for_unrecognized_dynamic_actor_key(self) -> None:
        source = """
def build():
    ActorRegistration(key=make_key(), actor_id="ACTOR", config=None)
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "composition.py"
            path.write_text(source, encoding="utf-8")
            with self.assertRaises(ManifestError) as raised:
                extract_actor_registrations(root, "composition.py")
        self.assertEqual(raised.exception.code, "DRIFT_UNSUPPORTED_ACTOR_REGISTRATION")

    def test_extracts_literal_signal_and_type_name_constants(self) -> None:
        source = """
READY_SIGNAL = "markeitech.ready"
VALUE_TYPE_NAME = "markeitech.value"
UNRELATED = "ignored"
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "contracts.py"
            path.write_text(source, encoding="utf-8")
            facts = extract_contract_constants(root, ("contracts.py",))
        self.assertEqual(
            tuple((fact.name, fact.value) for fact in facts),
            (
                ("READY_SIGNAL", "markeitech.ready"),
                ("VALUE_TYPE_NAME", "markeitech.value"),
            ),
        )

    def test_fails_closed_for_computed_contract_identity(self) -> None:
        source = 'READY_SIGNAL = "markeitech." + "ready"\n'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "contracts.py"
            path.write_text(source, encoding="utf-8")
            with self.assertRaises(ManifestError) as raised:
                extract_contract_constants(root, ("contracts.py",))
        self.assertEqual(raised.exception.code, "DRIFT_UNSUPPORTED_CONTRACT_CONSTANT")


if __name__ == "__main__":
    unittest.main()
