from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_FILE = PROJECT_ROOT / "config/system.local.toml"
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"


@dataclass(frozen=True)
class _IsolatedTool:
    name: str
    project: str
    module: str
    import_probe: str

    @property
    def interpreter(self) -> Path:
        return PROJECT_ROOT / self.project / ".venv/bin/python"

    @property
    def source_path(self) -> str:
        return f"{self.project}/src"

    @property
    def remediation(self) -> str:
        return f"uv sync --project {self.project} --locked"


_DOCS = _IsolatedTool(
    name="API documentation",
    project="tools/api-docs",
    module="markeitech_api_docs",
    import_probe="from markeitech_api_docs.cli import main",
)
_DIAGRAMS = _IsolatedTool(
    name="system diagram",
    project="tools/system-diagram",
    module="markeitech_system_diagram",
    import_probe="from markeitech_system_diagram.cli import main",
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
        default=DEFAULT_CONFIG_FILE,
        help="Path to the local system TOML (default: config/system.local.toml).",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_FILE,
        help="Path to the runtime environment file (default: .env).",
    )


def _connection_confirmation(value: str) -> str:
    from markeitech.system.cli import IB_CONFIRMATION

    if value != IB_CONFIRMATION:
        raise argparse.ArgumentTypeError(f"must exactly equal {IB_CONFIRMATION}")
    return value


def _system_arguments(args: argparse.Namespace) -> list[str]:
    return [str(args.config), "--env-file", str(args.env_file)]


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
    environment = os.environ.copy()
    environment.pop("PYTHONHOME", None)
    environment.update(
        {
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONPATH": tool.source_path,
            "TZ": "UTC",
        }
    )
    return environment


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
    try:
        probe = subprocess.run(
            [str(interpreter), "-c", tool.import_probe],
            cwd=PROJECT_ROOT,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        _isolated_environment_error(tool)
        return 1
    if probe.returncode != 0:
        _isolated_environment_error(tool)
        return 1
    return _run_process([str(interpreter), *arguments], environment=environment)


def _docs_command(args: argparse.Namespace) -> int:
    return _run_isolated(_DOCS, ["-m", _DOCS.module, args.operation])


def _diagram_command(args: argparse.Namespace) -> int:
    arguments = [
        "-m",
        _DIAGRAMS.module,
        "validate" if args.operation == "check" else args.operation,
        "--manifest",
        "docs/architecture/system-dataflow.toml",
    ]
    if args.operation == "test":
        arguments = ["-m", _DIAGRAMS.module, "test"]
    elif args.operation == "generate":
        arguments.extend(
            ["--output", "docs/architecture/generated/system-dataflow", "--check-drift"]
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
) -> int:
    result = subprocess.run(
        list(command),
        cwd=PROJECT_ROOT,
        env=environment,
        check=False,
    )
    if result.returncode < 0:
        return 128 - result.returncode
    return result.returncode


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
