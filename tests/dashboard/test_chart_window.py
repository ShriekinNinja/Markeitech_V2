"""Run browser presentation regressions offline without npm or provider connections."""

import shutil
import subprocess
from pathlib import Path

import pytest


def test_chart_window_regressions():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for the standalone browser JavaScript checks")
    result = subprocess.run(
        [node, "--test", str(Path(__file__).with_name("chart_window.test.cjs"))],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
