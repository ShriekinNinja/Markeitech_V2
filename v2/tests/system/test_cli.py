from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import Mock

from markeitech.system.cli import V2_ROOT, _start_caffeinate, main


def test_default_env_file_is_owned_by_v2() -> None:
    assert V2_ROOT.name == "v2"
    assert V2_ROOT / ".env" != V2_ROOT.parent / ".env"


def test_loads_explicit_env_file_without_overriding_process_environment(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = V2_ROOT / "config/system.toml"
    env_path = tmp_path / ".env"
    env_path.write_text("MARKEITECH_TEST_FILE_VALUE=loaded\nMARKEITECH_TEST_PRIORITY=file\n")
    monkeypatch.setenv("MARKEITECH_TEST_PRIORITY", "process")
    monkeypatch.delenv("MARKEITECH_TEST_FILE_VALUE", raising=False)

    result = main([str(config_path), "--env-file", str(env_path)])

    assert result == 0
    assert os.environ["MARKEITECH_TEST_FILE_VALUE"] == "loaded"
    assert os.environ["MARKEITECH_TEST_PRIORITY"] == "process"


def test_caffeinate_tracks_the_system_process(monkeypatch) -> None:
    popen = Mock()
    monkeypatch.setattr("markeitech.system.cli.subprocess.Popen", popen)
    monkeypatch.setattr("markeitech.system.cli.os.getpid", lambda: 1234)

    _start_caffeinate()

    popen.assert_called_once_with(["/usr/bin/caffeinate", "-dimsu", "-w", "1234"])
