"""Static import canary.

Markeitech Metadata:
    example.unknown: DO_NOT_RENDER_IMPORT_CANARY_SENTINEL
"""

raise RuntimeError("THIS MODULE MUST NEVER EXECUTE")


def safe_function(value: int) -> int:
    """Return the supplied fixture value."""

    return value
