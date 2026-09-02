from __future__ import annotations

import contextlib
import os
import socket
import subprocess
import sys
from collections.abc import Iterator
from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Any
from unittest.mock import patch

from markeitech_api_docs.models import ApiDocsError


class MarkeitechImportGuard(MetaPathFinder):
    def find_spec(
        self,
        fullname: str,
        path: object = None,
        target: object = None,
    ) -> ModuleSpec | None:
        del path, target
        if fullname == "markeitech" or fullname.startswith("markeitech."):
            raise ApiDocsError("TARGET_IMPORT_DENIED: Markeitech must be analyzed statically")
        return None


def _deny_network(*args: Any, **kwargs: Any) -> Any:
    del args, kwargs
    raise ApiDocsError("NETWORK_DENIED: API documentation generation is offline")


def _deny_subprocess(*args: Any, **kwargs: Any) -> Any:
    del args, kwargs
    raise ApiDocsError("SUBPROCESS_DENIED: generation cannot launch child processes")


@contextlib.contextmanager
def constrained_generation_environment() -> Iterator[None]:
    existing = [
        name
        for name in sys.modules
        if name == "markeitech" or name.startswith("markeitech.")
    ]
    if existing:
        raise ApiDocsError("TARGET_IMPORT_PRESENT: Markeitech is already imported")

    original_environment = dict(os.environ)
    safe_environment = {
        "PATH": original_environment.get("PATH", ""),
        "LANG": "C",
        "LC_ALL": "C",
        "TZ": "UTC",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "SOURCE_DATE_EPOCH": "0",
    }
    os.environ.clear()
    os.environ.update(safe_environment)

    guard = MarkeitechImportGuard()
    sys.meta_path.insert(0, guard)
    original_socket = socket.socket
    original_create_connection = socket.create_connection
    original_popen = subprocess.Popen
    original_run = subprocess.run
    original_call = subprocess.call
    original_check_call = subprocess.check_call
    original_check_output = subprocess.check_output
    original_os_system = os.system
    socket.socket = _deny_network  # type: ignore[assignment]
    socket.create_connection = _deny_network  # type: ignore[assignment]
    subprocess.Popen = _deny_subprocess  # type: ignore[assignment]
    subprocess.run = _deny_subprocess  # type: ignore[assignment]
    subprocess.call = _deny_subprocess  # type: ignore[assignment]
    subprocess.check_call = _deny_subprocess  # type: ignore[assignment]
    subprocess.check_output = _deny_subprocess  # type: ignore[assignment]
    os.system = _deny_subprocess  # type: ignore[assignment]
    git_metadata_patch = patch(
        "griffe._internal.loader.GitInfo.from_package",
        return_value=None,
    )
    git_metadata_patch.start()

    try:
        yield
        imported = [
            name for name in sys.modules if name == "markeitech" or name.startswith("markeitech.")
        ]
        if imported:
            raise ApiDocsError("TARGET_IMPORT_DETECTED: generation imported Markeitech")
    finally:
        git_metadata_patch.stop()
        socket.socket = original_socket
        socket.create_connection = original_create_connection
        subprocess.Popen = original_popen
        subprocess.run = original_run
        subprocess.call = original_call
        subprocess.check_call = original_check_call
        subprocess.check_output = original_check_output
        os.system = original_os_system
        if guard in sys.meta_path:
            sys.meta_path.remove(guard)
        os.environ.clear()
        os.environ.update(original_environment)


def validate_interpreter(tool_root: Path) -> None:
    expected = (tool_root / ".venv").resolve()
    if Path(sys.prefix).resolve() != expected:
        raise ApiDocsError("ENVIRONMENT_INVALID: use the locked tools/api-docs interpreter")
    if sys.version_info[:2] != (3, 13):
        raise ApiDocsError("ENVIRONMENT_INVALID: Python 3.13 is required")
    forbidden = (tool_root.parents[1] / "src").resolve()
    for entry in sys.path:
        if not entry:
            continue
        try:
            resolved = Path(entry).resolve()
        except OSError:
            continue
        if resolved == forbidden or resolved.is_relative_to(forbidden):
            raise ApiDocsError("ENVIRONMENT_INVALID: V2 source must not be on sys.path")
