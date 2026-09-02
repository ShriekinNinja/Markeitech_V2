from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from markeitech_system_diagram import ManifestError
from markeitech_system_diagram.source_census import (
    extract_actor_registrations,
    extract_contract_constants,
)


class SourceCensusTests(unittest.TestCase):
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
