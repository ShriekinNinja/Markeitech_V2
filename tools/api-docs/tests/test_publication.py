from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from markeitech_api_docs.build import (
    FixedPaths,
    _publish_complete_set,
    _verify_snapshot_unchanged,
)
from markeitech_api_docs.models import ApiDocsError, SourceFileIdentity, SourceSnapshot
from markeitech_api_docs.registry import sha256_file


class PublicationSafetyTest(unittest.TestCase):
    def test_failed_promotion_restores_previous_complete_set(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "site"
            build_root = root / ".build"
            staged = build_root / "stage" / "complete"
            output.mkdir()
            staged.mkdir(parents=True)
            (output / "identity.txt").write_text("previous", encoding="utf-8")
            (staged / "identity.txt").write_text("candidate", encoding="utf-8")
            paths = FixedPaths(
                tool_root=root,
                repository_root=root,
                source_root=root / "source",
                config=root / "mkdocs.yml",
                public_surface_registry=root / "public.toml",
                attribute_registry=root / "attributes.toml",
                output=output,
                build_root=build_root,
            )
            real_replace = os.replace
            replacement_count = 0

            def fail_candidate_promotion(source: Path, destination: Path) -> None:
                nonlocal replacement_count
                replacement_count += 1
                if replacement_count == 2:
                    raise OSError("simulated promotion failure")
                real_replace(source, destination)

            with patch(
                "markeitech_api_docs.build.os.replace",
                side_effect=fail_candidate_promotion,
            ):
                with self.assertRaisesRegex(ApiDocsError, "OUTPUT_PUBLICATION_FAILED"):
                    _publish_complete_set(staged, paths)

            self.assertEqual(
                (output / "identity.txt").read_text(encoding="utf-8"),
                "previous",
            )
            self.assertFalse((build_root / "previous").exists())

    def test_source_mutation_invalidates_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "v2" / "src" / "markeitech" / "fixture.py"
            source.parent.mkdir(parents=True)
            source.write_text("VALUE = 1\n", encoding="utf-8")
            snapshot = SourceSnapshot(
                commit="0" * 40,
                state="clean",
                dirty_path_count=0,
                dirty_state_sha256=None,
                files=(
                    SourceFileIdentity(
                        path="v2/src/markeitech/fixture.py",
                        sha256=sha256_file(source),
                        size_bytes=source.stat().st_size,
                    ),
                ),
            )
            source.write_text("VALUE = 2\n", encoding="utf-8")

            with self.assertRaisesRegex(ApiDocsError, "SOURCE_CHANGED"):
                _verify_snapshot_unchanged(snapshot, root)


if __name__ == "__main__":
    unittest.main()
