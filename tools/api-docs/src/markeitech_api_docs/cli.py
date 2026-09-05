from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from markeitech_api_docs.build import generate, validate
from markeitech_api_docs.models import ApiDocsError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="markeitech-api-docs",
        description="Validate, generate, or test the fixed offline Markeitech V2 API docs set.",
    )
    parser.add_argument("command", choices=("validate", "generate", "check", "test"))
    return parser


def _run_tests() -> int:
    import unittest
    from pathlib import Path

    tests = Path(__file__).resolve().parents[2] / "tests"
    suite = unittest.defaultTestLoader.discover(str(tests))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "test":
        return _run_tests()
    try:
        if args.command == "validate":
            result = validate()
        elif args.command == "check":
            from markeitech_api_docs.build import check

            result = check()
        else:
            result = generate()
    except ApiDocsError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        print("API_DOCS_FAILED: unexpected sanitized failure", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0
