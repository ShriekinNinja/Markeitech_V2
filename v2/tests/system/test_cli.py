from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import Mock

from markeitech.system.cli import (
    DEFAULT_CONFIG_FILE,
    DEFAULT_ENV_FILE,
    V2_ROOT,
    _start_caffeinate,
    main,
)
from markeitech.system.discord import (
    OPERATIONAL_EVENTS_WEBHOOK_ENV,
    SYSTEM_HEALTH_WEBHOOK_ENV,
)

POSTGRES_DSN_ENV = "MARKEITECH_POSTGRES_DSN"


def test_default_env_file_is_owned_by_v2() -> None:
    assert V2_ROOT.name == "v2"
    assert DEFAULT_ENV_FILE == V2_ROOT / ".env"
    assert DEFAULT_ENV_FILE != V2_ROOT.parent / ".env"


def test_default_config_file_is_local_and_owned_by_v2() -> None:
    assert DEFAULT_CONFIG_FILE == V2_ROOT / "config/system.local.toml"
    assert DEFAULT_CONFIG_FILE != V2_ROOT / "config/system.example.toml"


def test_loads_explicit_env_file_without_overriding_process_environment(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = V2_ROOT / "config/system.example.toml"
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


def test_clean_connected_run_is_closed_only_after_node_returns(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = Mock()
    node = Mock()
    sequence: list[str] = []
    _set_synthetic_runtime_environment(monkeypatch)
    store.start_run.side_effect = lambda *_args: sequence.append("start")
    store.load_evidence_recency_profiles.return_value = ()
    node.run.side_effect = lambda: sequence.append("run")
    store.close_run.side_effect = lambda *_args: sequence.append("close")
    monkeypatch.setattr(
        "markeitech.system.cli.OperationalStore.from_environment",
        lambda *_args: store,
    )
    monkeypatch.setattr("markeitech.system.cli.build_system_node", lambda *_args: node)

    result = main(
        [
            str(V2_ROOT / "config/system.example.toml"),
            "--env-file",
            str(tmp_path / "missing.env"),
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


def test_unclean_connected_run_remains_open(tmp_path: Path, monkeypatch) -> None:
    store = Mock()
    node = Mock()
    _set_synthetic_runtime_environment(monkeypatch)
    store.load_evidence_recency_profiles.return_value = ()
    node.run.side_effect = RuntimeError("node failed")
    monkeypatch.setattr(
        "markeitech.system.cli.OperationalStore.from_environment",
        lambda *_args: store,
    )
    monkeypatch.setattr("markeitech.system.cli.build_system_node", lambda *_args: node)

    try:
        main(
            [
                str(V2_ROOT / "config/system.example.toml"),
                "--env-file",
                str(tmp_path / "missing.env"),
                "--connect",
                "I_UNDERSTAND_THIS_CONNECTS_TO_IB",
            ],
        )
    except RuntimeError as exc:
        assert str(exc) == "node failed"
    else:
        raise AssertionError("expected node failure")

    store.close_run.assert_not_called()


def _set_synthetic_runtime_environment(monkeypatch) -> None:
    monkeypatch.setenv(
        POSTGRES_DSN_ENV,
        "postgresql://ci-user:ci-password@127.0.0.1:5432/ci-database",
    )
    monkeypatch.setenv(
        SYSTEM_HEALTH_WEBHOOK_ENV,
        "https://discord.invalid/api/webhooks/ci-placeholder",
    )
    monkeypatch.setenv(
        OPERATIONAL_EVENTS_WEBHOOK_ENV,
        "https://discord.invalid/api/webhooks/ci-operational-placeholder",
    )
