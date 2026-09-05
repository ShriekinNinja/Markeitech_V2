from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_TERMINATION_GRACE_SECONDS = 2.0
_IMPORT_ORIGIN_PROBE = """
import importlib
import pathlib
import sys

module = importlib.import_module(sys.argv[1])
actual = pathlib.Path(module.__file__).resolve()
expected = pathlib.Path(sys.argv[2]).resolve()
raise SystemExit(0 if actual == expected else 1)
"""


@dataclass(frozen=True)
class _IsolatedTool:
    name: str
    project: str
    module: str

    @property
    def interpreter(self) -> Path:
        return PROJECT_ROOT / self.project / ".venv/bin/python"

    @property
    def source_path(self) -> Path:
        return (PROJECT_ROOT / self.project / "src").resolve()

    @property
    def cli_path(self) -> Path:
        return self.source_path / self.module / "cli.py"

    @property
    def remediation(self) -> str:
        return f"uv sync --project {self.project} --locked"


_DOCS = _IsolatedTool(
    name="API documentation",
    project="tools/api-docs",
    module="markeitech_api_docs",
)
_DIAGRAMS = _IsolatedTool(
    name="system diagram",
    project="tools/system-diagram",
    module="markeitech_system_diagram",
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="markeitech",
        description="Run the closed Markeitech runtime and repository command surface.",
    )
    areas = parser.add_subparsers(dest="area", required=True)

    system = areas.add_parser("system", help="Build or run the Markeitech system.")
    system_operations = system.add_subparsers(dest="operation", required=True)
    build = system_operations.add_parser(
        "build",
        help="Build the configured system without connecting to a provider.",
    )
    _add_system_paths(build)
    build.set_defaults(handler=_system_build)

    run = system_operations.add_parser(
        "run",
        help="Run the connected system after exact Interactive Brokers confirmation.",
    )
    _add_system_paths(run)
    run.add_argument(
        "--connect",
        required=True,
        metavar="CONFIRMATION",
        type=_connection_confirmation,
        help="Must exactly confirm I_UNDERSTAND_THIS_CONNECTS_TO_IB.",
    )
    run.add_argument(
        "--keep-awake",
        action="store_true",
        help="Keep macOS awake for the lifetime of the connected runtime.",
    )
    run.set_defaults(handler=_system_run)

    docs = areas.add_parser("docs", help="Operate the isolated static API documentation tool.")
    docs_operations = docs.add_subparsers(dest="operation", required=True)
    for operation in ("validate", "check", "generate", "test"):
        command = docs_operations.add_parser(operation, help=f"Run API docs {operation}.")
        command.set_defaults(handler=_docs_command)

    diagrams = areas.add_parser(
        "diagrams",
        help="Operate the isolated system/data-flow diagram tool.",
    )
    diagram_operations = diagrams.add_subparsers(dest="operation", required=True)
    for operation in ("validate", "check", "generate", "test"):
        command = diagram_operations.add_parser(operation, help=f"Run diagram {operation}.")
        command.set_defaults(handler=_diagram_command)

    verify = areas.add_parser("verify", help="Run repository verification commands.")
    verify_operations = verify.add_subparsers(dest="operation", required=True)
    for operation, help_text in (
        ("lint", "Run the authoritative Ruff scope."),
        ("test", "Run the offline non-PostgreSQL test suite."),
        ("all", "Run lint, then offline tests, stopping at the first failure."),
        ("postgres", "Run only tests requiring an explicitly configured PostgreSQL service."),
    ):
        command = verify_operations.add_parser(operation, help=help_text)
        command.set_defaults(handler=_verify_command)

    environment = areas.add_parser("environment", help="Check the supported local environment.")
    environment_operations = environment.add_subparsers(dest="operation", required=True)
    check = environment_operations.add_parser(
        "check",
        help="Run the setup doctor without starting services or the runtime.",
    )
    check.add_argument(
        "--with-ib",
        action="store_true",
        help="Also check whether the configured IB endpoint is listening.",
    )
    check.set_defaults(handler=_environment_check)
    return parser


def _add_system_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        type=Path,
        default=argparse.SUPPRESS,
        help="Override the runtime owner's default system TOML path.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=argparse.SUPPRESS,
        help="Override the runtime owner's default environment-file path.",
    )


def _connection_confirmation(value: str) -> str:
    from markeitech.system.cli import IB_CONFIRMATION

    if value != IB_CONFIRMATION:
        raise argparse.ArgumentTypeError(f"must exactly equal {IB_CONFIRMATION}")
    return value


def _system_arguments(args: argparse.Namespace) -> list[str]:
    arguments: list[str] = []
    if hasattr(args, "config"):
        arguments.append(str(args.config))
    if hasattr(args, "env_file"):
        arguments.extend(["--env-file", str(args.env_file)])
    return arguments


def _system_build(args: argparse.Namespace) -> int:
    from markeitech.system.cli import main as system_main

    return system_main(_system_arguments(args))


def _system_run(args: argparse.Namespace) -> int:
    from markeitech.system.cli import main as system_main

    arguments = [*_system_arguments(args), "--connect", args.connect]
    if args.keep_awake:
        arguments.append("--keep-awake")
    return system_main(arguments)


def _tool_environment(tool: _IsolatedTool) -> dict[str, str]:
    return {
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": str(tool.source_path),
        "PYTHONSAFEPATH": "1",
        "PYTHONUNBUFFERED": "1",
        "PYTHONUTF8": "1",
        "TZ": "UTC",
    }


def _isolated_environment_error(tool: _IsolatedTool) -> None:
    print(
        f"ERROR: {tool.name} environment is missing or invalid.\nRun: {tool.remediation}",
        file=sys.stderr,
    )


def _run_isolated(tool: _IsolatedTool, arguments: Sequence[str]) -> int:
    interpreter = tool.interpreter
    if not interpreter.is_file() or not os.access(interpreter, os.X_OK):
        _isolated_environment_error(tool)
        return 1
    environment = _tool_environment(tool)
    probe_result = _run_process(
        [
            str(interpreter),
            "-P",
            "-c",
            _IMPORT_ORIGIN_PROBE,
            f"{tool.module}.cli",
            str(tool.cli_path),
        ],
        environment=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        report_launch_error=False,
    )
    if probe_result != 0:
        _isolated_environment_error(tool)
        return 1
    return _run_process([str(interpreter), "-P", *arguments], environment=environment)


def _docs_command(args: argparse.Namespace) -> int:
    return _run_isolated(_DOCS, ["-m", _DOCS.module, args.operation])


def _diagram_command(args: argparse.Namespace) -> int:
    arguments = [
        "-m",
        _DIAGRAMS.module,
        "validate" if args.operation == "check" else args.operation,
        "--manifest",
        "tools/system-diagram/docs/system-dataflow.toml",
    ]
    if args.operation == "test":
        arguments = ["-m", _DIAGRAMS.module, "test"]
    elif args.operation == "generate":
        arguments.extend(
            ["--output", "tools/system-diagram/docs/generated", "--check-drift"]
        )
    elif args.operation == "check":
        arguments.append("--check-drift")
    return _run_isolated(_DIAGRAMS, arguments)


def _verify_arguments(operation: str) -> list[str]:
    if operation == "lint":
        return [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "src",
            "tests",
            "scripts/sir-kite-pr.py",
        ]
    marker = "postgres" if operation == "postgres" else "not postgres"
    return [sys.executable, "-m", "pytest", "-q", "tests", "-m", marker]


def _verify_command(args: argparse.Namespace) -> int:
    operations = ("lint", "test") if args.operation == "all" else (args.operation,)
    for operation in operations:
        result = _run_process(_verify_arguments(operation))
        if result != 0:
            return result
    return 0


def _environment_check(args: argparse.Namespace) -> int:
    command = [str(PROJECT_ROOT / "scripts/check-env")]
    if args.with_ib:
        command.append("--with-ib")
    return _run_process(command)


def _run_process(
    command: Sequence[str],
    *,
    environment: dict[str, str] | None = None,
    stdout: int | None = None,
    stderr: int | None = None,
    report_launch_error: bool = True,
) -> int:
    try:
        process = subprocess.Popen(
            list(command),
            cwd=PROJECT_ROOT,
            env=environment,
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
        )
    except OSError:
        if report_launch_error:
            print("ERROR: unable to start the requested process.", file=sys.stderr)
        return 1

    cancellation_signal: int | None = None
    cancellation_deadline: float | None = None
    previous_handlers: dict[int, signal.Handlers] = {}

    def forward_signal(signum: int, _frame: object) -> None:
        nonlocal cancellation_deadline, cancellation_signal
        if cancellation_signal is None:
            cancellation_signal = signum
            cancellation_deadline = time.monotonic() + _TERMINATION_GRACE_SECONDS
            _signal_process_group(process.pid, signum)
        else:
            _signal_process_group(process.pid, signal.SIGKILL)

    if threading.current_thread() is threading.main_thread():
        for handled_signal in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            previous_handlers[handled_signal] = signal.getsignal(handled_signal)
            signal.signal(handled_signal, forward_signal)

    try:
        while True:
            try:
                returncode = process.wait(timeout=0.1)
                break
            except subprocess.TimeoutExpired:
                if (
                    cancellation_deadline is not None
                    and time.monotonic() >= cancellation_deadline
                ):
                    _signal_process_group(process.pid, signal.SIGKILL)
    except BaseException:
        _signal_process_group(process.pid, signal.SIGKILL)
        process.wait()
        raise
    finally:
        for handled_signal, previous_handler in previous_handlers.items():
            signal.signal(handled_signal, previous_handler)

    if cancellation_signal is not None:
        _signal_process_group(process.pid, signal.SIGKILL)
        return 128 + cancellation_signal
    if returncode < 0:
        return 128 - returncode
    return returncode


def _signal_process_group(process_group_id: int, signum: int) -> None:
    try:
        os.killpg(process_group_id, signum)
    except OSError:
        pass


def main(argv: Sequence[str] | None = None) -> int:
    """Route one explicit Markeitech runtime or repository operation.

    The command hierarchy owns parsing and fixed child-process mappings only. Runtime behavior
    remains owned by `markeitech.system.cli`; API documentation and diagrams remain in their
    isolated locked tool projects. No command provisions dependencies, starts Docker, supplies the
    Interactive Brokers confirmation, or broadens connected or persistence authority.

    Args:
        argv: Optional command-line arguments. ``None`` reads process arguments.

    Returns:
        The selected in-process owner or fixed child process exit code.

    Raises:
        SystemExit: If command-line parsing or exact connection confirmation fails.
        KeyboardInterrupt: If the operator interrupts command execution.
    """

    args = _parser().parse_args(argv)
    handler: Callable[[argparse.Namespace], int] = args.handler
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
