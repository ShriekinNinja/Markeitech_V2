from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
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


def test_system_defaults_remain_owned_by_the_runtime_cli(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    system_main = Mock(return_value=0)
    monkeypatch.setattr("markeitech.system.cli.main", system_main)

    assert cli.main(["system", "build"]) == 0

    system_main.assert_called_once_with([])


def test_system_run_forwards_no_default_path_values(monkeypatch: pytest.MonkeyPatch) -> None:
    system_main = Mock(return_value=0)
    monkeypatch.setattr("markeitech.system.cli.main", system_main)

    assert (
        cli.main(
            ["system", "run", "--connect", "I_UNDERSTAND_THIS_CONNECTS_TO_IB"]
        )
        == 0
    )

    system_main.assert_called_once_with(
        ["--connect", "I_UNDERSTAND_THIS_CONNECTS_TO_IB"]
    )


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
    monkeypatch.setenv("PYTHONINSPECT", "1")
    monkeypatch.setenv("MARKEITECH_DISCORD_SYSTEM_HEALTH_WEBHOOK", "secret-sentinel")

    environment = cli._tool_environment(cli._DOCS)

    assert "PYTHONHOME" not in environment
    assert "PYTHONINSPECT" not in environment
    assert "MARKEITECH_DISCORD_SYSTEM_HEALTH_WEBHOOK" not in environment
    assert environment["LANG"] == "C"
    assert environment["LC_ALL"] == "C"
    assert environment["PYTHONUNBUFFERED"] == "1"
    assert environment["PYTHONDONTWRITEBYTECODE"] == "1"
    assert environment["PYTHONHASHSEED"] == "0"
    assert environment["PYTHONNOUSERSITE"] == "1"
    assert environment["PYTHONSAFEPATH"] == "1"
    assert environment["PYTHONPATH"] == str(cli._DOCS.source_path)
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
    )
    run_process = Mock(return_value=1)
    monkeypatch.setattr(cli, "_run_process", run_process)

    result = cli._run_isolated(tool, ["-m", "invalid_tool"])

    assert result == 1
    run_process.assert_called_once()
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


def test_child_exit_code_is_propagated() -> None:
    assert cli._run_process([sys.executable, "-c", "raise SystemExit(23)"]) == 23


def test_child_signal_is_returned_as_a_shell_interrupt_code() -> None:
    command = [
        sys.executable,
        "-c",
        "import os, signal; os.kill(os.getpid(), signal.SIGTERM)",
    ]

    assert cli._run_process(command) == 143


def test_child_interruption_is_propagated(monkeypatch: pytest.MonkeyPatch) -> None:
    process = Mock(pid=91234)
    process.wait.side_effect = [KeyboardInterrupt, 0]
    monkeypatch.setattr(cli.subprocess, "Popen", Mock(return_value=process))
    signal_group = Mock()
    monkeypatch.setattr(cli, "_signal_process_group", signal_group)

    with pytest.raises(KeyboardInterrupt):
        cli._run_process(["fixed", "command"])

    signal_group.assert_called_once_with(process.pid, signal.SIGKILL)


def test_launch_oserror_is_sanitized(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli.subprocess,
        "Popen",
        Mock(side_effect=OSError("/private/secret/tool: permission denied")),
    )

    assert cli._run_process(["/private/secret/tool"]) == 1

    error = capsys.readouterr().err
    assert error == "ERROR: unable to start the requested process.\n"
    assert "/private" not in error


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
    )
    run_process = Mock(side_effect=[0, 4])
    monkeypatch.setattr(cli, "_run_process", run_process)

    result = cli._run_isolated(tool, ["-m", "test_tool", "validate"])

    assert result == 4
    probe_call, child_call = run_process.call_args_list
    assert probe_call.args[0][:3] == [str(interpreter), "-P", "-c"]
    assert probe_call.args[0][-2:] == ["test_tool.cli", str(tool.cli_path)]
    assert probe_call.kwargs["environment"]["PYTHONPATH"] == str(tool.source_path)
    assert probe_call.kwargs["report_launch_error"] is False
    assert child_call == (
        ([str(interpreter), "-P", "-m", "test_tool", "validate"],),
        {"environment": probe_call.kwargs["environment"]},
    )


def _write_isolated_test_tool(root: Path, module: str = "test_tool") -> cli._IsolatedTool:
    tool_root = root / "tool"
    interpreter = tool_root / ".venv/bin/python"
    interpreter.parent.mkdir(parents=True)
    interpreter.symlink_to(sys.executable)
    package = tool_root / "src" / module
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "cli.py").write_text("def main(): return 0\n", encoding="utf-8")
    (package / "__main__.py").write_text(
        "import json, os, pathlib, sys\n"
        "pathlib.Path(sys.argv[1]).write_text(json.dumps(dict(os.environ)))\n",
        encoding="utf-8",
    )
    return cli._IsolatedTool(name="test tool", project="tool", module=module)


def test_real_isolated_child_receives_only_the_reviewed_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("PYTHONINSPECT", "1")
    monkeypatch.setenv("PYTHONWARNINGS", "error")
    monkeypatch.setenv("DATABASE_URL", "database-secret")
    monkeypatch.setenv("GITHUB_TOKEN", "github-secret")
    monkeypatch.setenv("MARKEITECH_DISCORD_SYSTEM_HEALTH_WEBHOOK", "discord-secret")
    tool = _write_isolated_test_tool(tmp_path)
    observed_path = tmp_path / "observed-environment.json"

    assert cli._run_isolated(tool, ["-m", tool.module, str(observed_path)]) == 0

    observed = json.loads(observed_path.read_text(encoding="utf-8"))
    expected = cli._tool_environment(tool)
    assert {key: observed[key] for key in expected} == expected
    assert "PYTHONINSPECT" not in observed
    assert "PYTHONWARNINGS" not in observed
    assert "DATABASE_URL" not in observed
    assert "GITHUB_TOKEN" not in observed
    assert "MARKEITECH_DISCORD_SYSTEM_HEALTH_WEBHOOK" not in observed


def test_tool_import_is_bound_to_the_absolute_tool_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    tool = _write_isolated_test_tool(tmp_path)
    shadow = tmp_path / tool.module
    shadow.mkdir()
    (shadow / "__init__.py").write_text("", encoding="utf-8")
    (shadow / "cli.py").write_text(
        "raise RuntimeError('root shadow imported')\n",
        encoding="utf-8",
    )
    observed_path = tmp_path / "origin-environment.json"

    assert cli._run_isolated(tool, ["-m", tool.module, str(observed_path)]) == 0
    assert observed_path.is_file()


@pytest.mark.parametrize(
    ("termination_signal", "send_to_group", "expected_status"),
    [
        (signal.SIGTERM, False, 143),
        (signal.SIGHUP, False, 129),
        (signal.SIGINT, True, 130),
    ],
)
def test_parent_cancellation_terminates_child_group_without_post_cancel_writes(
    tmp_path: Path,
    termination_signal: int,
    send_to_group: bool,
    expected_status: int,
) -> None:
    wrapper_code = (
        "import sys\n"
        "from markeitech import cli\n"
        "cli._TERMINATION_GRACE_SECONDS = 0.1\n"
        "raise SystemExit(cli._run_process([sys.executable, sys.argv[1], sys.argv[2], "
        "sys.argv[3]]))\n"
    )
    child_path = tmp_path / "cancellation_child.py"
    child_path.write_text(
        "import os, pathlib, signal, subprocess, sys, time\n"
        "for value in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):\n"
        "    signal.signal(value, signal.SIG_IGN)\n"
        "descendant = subprocess.Popen([sys.executable, '-c', "
        "'import pathlib, signal, sys, time; '"
        "+ 'signal.signal(signal.SIGINT, signal.SIG_IGN); '"
        "+ 'signal.signal(signal.SIGTERM, signal.SIG_IGN); '"
        "+ 'signal.signal(signal.SIGHUP, signal.SIG_IGN); '"
        "+ 'time.sleep(0.5); pathlib.Path(sys.argv[1]).write_text(\"descendant\")', "
        "sys.argv[2]])\n"
        "print(f'{os.getpid()} {descendant.pid}', flush=True)\n"
        "time.sleep(0.5)\n"
        "pathlib.Path(sys.argv[1]).write_text('child')\n",
        encoding="utf-8",
    )
    child_marker = tmp_path / "child-published"
    descendant_marker = tmp_path / "descendant-published"
    wrapper = subprocess.Popen(
        [
            sys.executable,
            "-c",
            wrapper_code,
            str(child_path),
            str(child_marker),
            str(descendant_marker),
        ],
        cwd=cli.PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    assert wrapper.stdout is not None
    child_ids = wrapper.stdout.readline().strip().split()
    assert len(child_ids) == 2

    child_process_group = int(child_ids[0])
    try:
        if send_to_group:
            os.killpg(wrapper.pid, termination_signal)
        else:
            wrapper.send_signal(termination_signal)
        wrapper.communicate(timeout=5)
        time.sleep(0.6)

        assert wrapper.returncode == expected_status
        assert not child_marker.exists()
        assert not descendant_marker.exists()
    finally:
        try:
            os.killpg(child_process_group, signal.SIGKILL)
        except ProcessLookupError:
            pass
        if wrapper.poll() is None:
            os.killpg(wrapper.pid, signal.SIGKILL)
            wrapper.wait(timeout=5)
