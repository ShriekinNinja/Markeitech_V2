from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .diagnostics import ManifestError
from .loader import load_manifest
from .render import generate_all
from .source_census import validate_source_census

_MANIFEST = Path("docs/architecture/system-dataflow.toml")
_OUTPUT = Path("docs/architecture/generated/system-dataflow")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and generate offline Markeitech diagrams"
    )
    parser.add_argument("command", choices=("validate", "generate", "test"))
    parser.add_argument("--manifest", type=Path, default=_MANIFEST)
    parser.add_argument("--output", type=Path, default=_OUTPUT)
    parser.add_argument("--check-drift", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "test":
        return _run_tests()
    repository_root = Path.cwd().resolve()
    if args.manifest != _MANIFEST:
        print(
            "CLI_PATH at --manifest: only the canonical repository manifest is accepted",
            file=sys.stderr,
        )
        return 2
    if args.output != _OUTPUT:
        print(
            "CLI_PATH at --output: only the canonical generated directory is accepted",
            file=sys.stderr,
        )
        return 2
    try:
        manifest_path = repository_root / args.manifest
        manifest = load_manifest(manifest_path, repository_root=repository_root)
        if args.check_drift:
            validate_source_census(manifest, repository_root=repository_root)
        if args.command == "generate":
            result = generate_all(
                manifest,
                manifest_path=manifest_path,
                output_directory=repository_root / args.output,
            )
            print(
                f"Generated {result.artifact_count} offline documentation artifacts in "
                f"{args.output}"
            )
        else:
            print("Manifest validation passed" + (" with drift census" if args.check_drift else ""))
    except ManifestError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, subprocess.SubprocessError):
        print("GENERATOR_IO at output: offline generation failed", file=sys.stderr)
        return 2
    return 0


def _run_tests() -> int:
    import unittest

    tests = Path(__file__).resolve().parents[2] / "tests"
    suite = unittest.defaultTestLoader.discover(str(tests))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
