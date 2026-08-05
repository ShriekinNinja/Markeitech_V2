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


def test_clean_connected_run_is_closed_only_after_node_returns(monkeypatch) -> None:
    store = Mock()
    node = Mock()
    sequence: list[str] = []
    store.start_run.side_effect = lambda *_args: sequence.append("start")
    node.run.side_effect = lambda: sequence.append("run")
    store.close_run.side_effect = lambda *_args: sequence.append("close")
    monkeypatch.setattr(
        "markeitech.system.cli.OperationalStore.from_environment",
        lambda *_args: store,
    )
    monkeypatch.setattr("markeitech.system.cli.build_system_node", lambda *_args: node)

    result = main(
        [
            str(V2_ROOT / "config/system.toml"),
            "--connect",
            "I_UNDERSTAND_THIS_CONNECTS_TO_IB",
        ],
    )

    assert result == 0
    assert sequence == ["start", "run", "close"]
    store.initialize.assert_called_once_with()
    assert store.close_run.call_args.args[1:] == (
        "STOPPED",
        "Nautilus LiveNode returned cleanly",
    )


def test_unclean_connected_run_remains_open(monkeypatch) -> None:
    store = Mock()
    node = Mock()
    node.run.side_effect = RuntimeError("node failed")
    monkeypatch.setattr(
        "markeitech.system.cli.OperationalStore.from_environment",
        lambda *_args: store,
    )
    monkeypatch.setattr("markeitech.system.cli.build_system_node", lambda *_args: node)

    try:
        main(
            [
                str(V2_ROOT / "config/system.toml"),
                "--connect",
                "I_UNDERSTAND_THIS_CONNECTS_TO_IB",
            ],
        )
    except RuntimeError as exc:
        assert str(exc) == "node failed"
    else:
        raise AssertionError("expected node failure")

    store.close_run.assert_not_called()
