from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from markeitech_api_docs.component_docs import build_component_docs_projection
from markeitech_api_docs.models import ApiDocsError, SourceSnapshot
from markeitech_api_docs.registry import load_attribute_registry


def _component_docstring(
    *,
    component_id: str = "actor.fixture",
    extra: str = "",
    omit_boundary: bool = False,
) -> str:
    boundary = "" if omit_boundary else "        architecture.component.boundary: boundary.system\n"
    return f'''class FixtureActor:
    """Fixture component.

    Markeitech Metadata:
        architecture.component.id: {component_id}
        architecture.component.label: Fixture
        architecture.component.kind: markeitech_actor
{boundary}{extra}    """
'''


class ComponentDocsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tool_root = Path(__file__).resolve().parents[1]
        self.registry = load_attribute_registry(
            self.tool_root / "schema" / "attribute-registry.toml"
        )
        self.snapshot = SourceSnapshot(
            commit="0" * 40,
            state="clean",
            dirty_path_count=0,
            dirty_state_sha256=None,
            files=(),
        )

    def _projection(self, sources: dict[str, str]):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        repository_root = Path(temporary.name)
        source_root = repository_root / "src" / "markeitech"
        source_root.mkdir(parents=True)
        for name, value in sources.items():
            (source_root / name).write_text(value, encoding="utf-8")
        return build_component_docs_projection(
            repository_root=repository_root,
            source_root=source_root,
            registry=self.registry,
            snapshot=self.snapshot,
        )

    def test_private_top_level_component_is_selected_with_derived_identity(self) -> None:
        projection = self._projection({"private_actor.py": _component_docstring()})
        self.assertEqual(projection.payload["counts"]["components"], 1)
        component = projection.payload["components"][0]
        self.assertEqual(component["object_path"], "markeitech.private_actor.FixtureActor")
        self.assertEqual(
            component["implementation_ref"],
            "src/markeitech/private_actor.py:FixtureActor",
        )

    def test_duplicate_component_identity_fails_closed(self) -> None:
        source = _component_docstring()
        with self.assertRaisesRegex(ApiDocsError, "ARCHITECTURE_ID_CONFLICT"):
            self._projection({"one.py": source, "two.py": source})

    def test_missing_required_field_fails_closed(self) -> None:
        with self.assertRaisesRegex(ApiDocsError, "ARCHITECTURE_METADATA_INCOMPLETE"):
            self._projection(
                {"missing.py": _component_docstring(omit_boundary=True)}
            )

    def test_unapproved_architecture_field_fails_closed(self) -> None:
        source = _component_docstring(
            extra="        architecture.component.status: current\n"
        )
        with self.assertRaisesRegex(ApiDocsError, "ARCHITECTURE_METADATA_INVALID"):
            self._projection({"unknown.py": source})

    def test_malformed_architecture_value_fails_closed(self) -> None:
        source = _component_docstring().replace(
            "architecture.component.kind: markeitech_actor",
            "architecture.component.kind: arbitrary_worker",
        )
        with self.assertRaisesRegex(ApiDocsError, "ARCHITECTURE_METADATA_INVALID"):
            self._projection({"malformed.py": source})

    def test_nested_class_is_not_an_architecture_component(self) -> None:
        nested = "\n".join(
            f"    {line}" for line in _component_docstring().splitlines()
        )
        projection = self._projection({"nested.py": f"class Container:\n{nested}"})
        self.assertEqual(projection.payload["counts"]["components"], 0)


if __name__ == "__main__":
    unittest.main()
