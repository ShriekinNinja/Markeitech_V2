from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from markeitech import cli


@pytest.mark.parametrize(
    "arguments",
    [
        ["--help"],
        ["system", "--help"],
        ["system", "build", "--help"],
        ["system", "run", "--help"],
        ["docs", "--help"],
        ["diagrams", "--help"],
        ["verify", "--help"],
        ["environment", "--help"],
        ["environment", "check", "--help"],
    ],
)
def test_help_is_available_at_every_command_level(
    arguments: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(arguments)

    assert exc.value.code == 0
    assert "usage:" in capsys.readouterr().out


@pytest.mark.parametrize(
    "arguments",
    [
        ["unknown"],
        ["system", "unknown"],
        ["docs", "unknown"],
        ["diagrams", "unknown"],
        ["verify", "unknown"],
        ["environment", "unknown"],
    ],
)
def test_unknown_area_or_operation_is_rejected(arguments: list[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(arguments)

    assert exc.value.code == 2


def test_python_module_and_installed_entry_point_have_help_parity() -> None:
    entry_point = Path(sys.executable).parent / "markeitech"
    assert entry_point.is_file()

    module_result = subprocess.run(
        [sys.executable, "-m", "markeitech", "--help"],
        cwd=cli.PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    entry_result = subprocess.run(
        [str(entry_point), "--help"],
        cwd=cli.PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert module_result.returncode == entry_result.returncode == 0
    assert module_result.stdout == entry_result.stdout
    assert module_result.stderr == entry_result.stderr == ""


def test_legacy_system_entry_point_remains_available() -> None:
    legacy_entry_point = Path(sys.executable).parent / "markeitech-system"
    assert legacy_entry_point.is_file()

    result = subprocess.run(
        [str(legacy_entry_point), "--help"],
        cwd=cli.PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Build or run the Markeitech v2 system." in result.stdout


def test_system_build_delegates_without_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    system_main = Mock(return_value=0)
    monkeypatch.setattr("markeitech.system.cli.main", system_main)

    result = cli.main(
        [
            "system",
            "build",
            "--config",
            "config/system.example.toml",
            "--env-file",
            "missing.env",
        ]
    )

    assert result == 0
    system_main.assert_called_once_with(
        ["config/system.example.toml", "--env-file", "missing.env"]
    )
    assert "--connect" not in system_main.call_args.args[0]


@pytest.mark.parametrize(
    "arguments",
    [
        ["system", "run"],
        ["system", "run", "--connect", "wrong"],
    ],
)
def test_system_run_requires_exact_connection_confirmation(arguments: list[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(arguments)

    assert exc.value.code == 2


def test_system_run_forwards_owned_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    system_main = Mock(return_value=7)
    monkeypatch.setattr("markeitech.system.cli.main", system_main)

    result = cli.main(
        [
            "system",
            "run",
            "--config",
            "custom.toml",
            "--env-file",
            "custom.env",
            "--connect",
            "I_UNDERSTAND_THIS_CONNECTS_TO_IB",
            "--keep-awake",
        ]
    )

    assert result == 7
    system_main.assert_called_once_with(
        [
            "custom.toml",
            "--env-file",
            "custom.env",
            "--connect",
            "I_UNDERSTAND_THIS_CONNECTS_TO_IB",
            "--keep-awake",
        ]
    )


@pytest.mark.parametrize("operation", ["validate", "check", "generate"])
def test_docs_commands_map_to_the_first_party_wrapper(
    operation: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    isolated = Mock(return_value=5)
    monkeypatch.setattr(cli, "_run_isolated", isolated)

    result = cli.main(["docs", operation])

    assert result == 5
    isolated.assert_called_once_with(
        cli._DOCS,
        ["-m", "markeitech_api_docs", operation],
    )


def test_docs_test_maps_to_the_isolated_test_suite(monkeypatch: pytest.MonkeyPatch) -> None:
    isolated = Mock(return_value=0)
    monkeypatch.setattr(cli, "_run_isolated", isolated)

    result = cli.main(["docs", "test"])

    assert result == 0
    isolated.assert_called_once_with(
        cli._DOCS,
        ["-m", "markeitech_api_docs", "test"],
    )


@pytest.mark.parametrize(
    ("operation", "expected"),
    [
        (
            "validate",
            [
                "-m",
                "markeitech_system_diagram",
                "validate",
                "--manifest",
                "docs/architecture/system-dataflow.toml",
            ],
        ),
        (
            "check",
            [
                "-m",
                "markeitech_system_diagram",
                "validate",
                "--manifest",
                "docs/architecture/system-dataflow.toml",
                "--check-drift",
            ],
        ),
        (
            "generate",
            [
                "-m",
                "markeitech_system_diagram",
                "generate",
                "--manifest",
                "docs/architecture/system-dataflow.toml",
                "--output",
                "docs/architecture/generated/system-dataflow",
                "--check-drift",
            ],
        ),
        (
            "test",
            ["-m", "markeitech_system_diagram", "test"],
        ),
    ],
)
def test_diagram_commands_preserve_canonical_paths_and_drift_behavior(
    operation: str,
    expected: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    isolated = Mock(return_value=0)
    monkeypatch.setattr(cli, "_run_isolated", isolated)

    result = cli.main(["diagrams", operation])

    assert result == 0
    isolated.assert_called_once_with(cli._DIAGRAMS, expected)


def test_isolated_environment_is_deterministic_and_does_not_name_runtime_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTHONHOME", "/unsafe")
    monkeypatch.setenv("PYTHONHASHSEED", "random")

    environment = cli._tool_environment(cli._DOCS)

    assert "PYTHONHOME" not in environment
    assert environment["PYTHONUNBUFFERED"] == "1"
    assert environment["PYTHONDONTWRITEBYTECODE"] == "1"
    assert environment["PYTHONHASHSEED"] == "0"
    assert environment["PYTHONPATH"] == "tools/api-docs/src"
    assert environment["TZ"] == "UTC"
    assert ".env" not in environment.values()


def test_offline_routing_does_not_enter_the_runtime_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    system_main = Mock(side_effect=AssertionError("offline command entered runtime owner"))
    monkeypatch.setattr("markeitech.system.cli.main", system_main)
    monkeypatch.setattr(cli, "_run_isolated", Mock(return_value=0))
    monkeypatch.setattr(cli, "_run_process", Mock(return_value=0))

    assert cli.main(["docs", "validate"]) == 0
    assert cli.main(["diagrams", "check"]) == 0
    assert cli.main(["verify", "lint"]) == 0
    system_main.assert_not_called()


def test_missing_isolated_environment_reports_remediation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tool = cli._IsolatedTool(
        name="test tool",
        project=str(tmp_path / "missing-tool"),
        module="missing_tool",
        import_probe="import missing_tool",
    )

    result = cli._run_isolated(tool, ["-m", "missing_tool"])

    assert result == 1
    error = capsys.readouterr().err
    assert "environment is missing or invalid" in error
    assert f"uv sync --project {tmp_path / 'missing-tool'} --locked" in error


def test_invalid_isolated_environment_reports_remediation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tool_root = tmp_path / "invalid-tool"
    interpreter = tool_root / ".venv/bin/python"
    interpreter.parent.mkdir(parents=True)
    interpreter.symlink_to(sys.executable)
    tool = cli._IsolatedTool(
        name="test tool",
        project=str(tool_root),
        module="invalid_tool",
        import_probe="import invalid_tool",
    )
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        Mock(return_value=SimpleNamespace(returncode=1)),
    )

    result = cli._run_isolated(tool, ["-m", "invalid_tool"])

    assert result == 1
    assert f"uv sync --project {tool_root} --locked" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("operation", "expected"),
    [
        (
            "lint",
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "src",
                "tests",
                "scripts/sir-kite-pr.py",
            ],
        ),
        (
            "test",
            [sys.executable, "-m", "pytest", "-q", "tests", "-m", "not postgres"],
        ),
        (
            "postgres",
            [sys.executable, "-m", "pytest", "-q", "tests", "-m", "postgres"],
        ),
    ],
)
def test_verify_commands_map_to_the_current_interpreter(
    operation: str,
    expected: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_process = Mock(return_value=0)
    monkeypatch.setattr(cli, "_run_process", run_process)

    assert cli.main(["verify", operation]) == 0

    run_process.assert_called_once_with(expected)


def test_verify_all_orders_lint_before_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        cli,
        "_run_process",
        lambda command: calls.append(list(command)) or 0,
    )

    assert cli.main(["verify", "all"]) == 0
    assert calls == [cli._verify_arguments("lint"), cli._verify_arguments("test")]


def test_verify_all_stops_at_the_first_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    run_process = Mock(return_value=9)
    monkeypatch.setattr(cli, "_run_process", run_process)

    assert cli.main(["verify", "all"]) == 9

    run_process.assert_called_once_with(cli._verify_arguments("lint"))


def test_environment_check_preserves_explicit_ib_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    run_process = Mock(return_value=0)
    monkeypatch.setattr(cli, "_run_process", run_process)

    assert cli.main(["environment", "check"]) == 0
    run_process.assert_called_once_with([str(cli.PROJECT_ROOT / "scripts/check-env")])

    run_process.reset_mock()
    assert cli.main(["environment", "check", "--with-ib"]) == 0
    run_process.assert_called_once_with(
        [str(cli.PROJECT_ROOT / "scripts/check-env"), "--with-ib"]
    )


def test_child_exit_code_is_propagated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        Mock(return_value=SimpleNamespace(returncode=23)),
    )

    assert cli._run_process(["fixed", "command"]) == 23


def test_child_signal_is_returned_as_a_shell_interrupt_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        Mock(return_value=SimpleNamespace(returncode=-2)),
    )

    assert cli._run_process(["fixed", "command"]) == 130


def test_child_interruption_is_propagated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli.subprocess, "run", Mock(side_effect=KeyboardInterrupt))

    with pytest.raises(KeyboardInterrupt):
        cli._run_process(["fixed", "command"])


def test_isolated_command_uses_fixed_root_and_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tool_root = tmp_path / "valid-tool"
    interpreter = tool_root / ".venv/bin/python"
    interpreter.parent.mkdir(parents=True)
    interpreter.symlink_to(sys.executable)
    tool = cli._IsolatedTool(
        name="test tool",
        project=str(tool_root),
        module="test_tool",
        import_probe="import test_tool",
    )
    probe = Mock(return_value=SimpleNamespace(returncode=0))
    child = Mock(return_value=4)
    monkeypatch.setattr(cli.subprocess, "run", probe)
    monkeypatch.setattr(cli, "_run_process", child)

    result = cli._run_isolated(tool, ["-m", "test_tool", "validate"])

    assert result == 4
    probe.assert_called_once()
    assert probe.call_args.kwargs["cwd"] == cli.PROJECT_ROOT
    assert probe.call_args.kwargs["env"]["PYTHONPATH"] == f"{tool_root}/src"
    child.assert_called_once_with(
        [str(interpreter), "-m", "test_tool", "validate"],
        environment=probe.call_args.kwargs["env"],
    )
