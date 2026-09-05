"""Run the unified Markeitech CLI through ``python -m markeitech``.

This module delegates directly to the same public ``main`` function as the installed
``markeitech`` entry point so both invocation forms share parsing, safety checks, and exit codes.
"""

from __future__ import annotations

from markeitech.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
