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
        description="Validate or generate the fixed offline Markeitech V2 API documentation set.",
    )
    parser.add_argument("command", choices=("validate", "generate"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = validate() if args.command == "validate" else generate()
    except ApiDocsError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        print("API_DOCS_FAILED: unexpected sanitized failure", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0
