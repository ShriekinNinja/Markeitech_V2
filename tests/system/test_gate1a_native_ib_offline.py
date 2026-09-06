from __future__ import annotations

import ast
import base64
import hashlib
import importlib.metadata
import inspect
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest
from nautilus_trader.adapters.interactive_brokers import (
    InteractiveBrokersExecutionClientConfig,
)

ROOT = Path(__file__).parents[2]
PINNED_NAUTILUS_VERSION = "2.0.0rc4"
CONSTRUCTION_TIMEOUT_SECONDS = 15
CONSTRUCTION_SENTINEL = "GATE1A_NATIVE_CONSTRUCTION_OK"

_NATIVE_CONSTRUCTION_SCRIPT = f"""
import json
import sys

from nautilus_trader.adapters.interactive_brokers import (
    InteractiveBrokersExecutionClientConfig,
    InteractiveBrokersExecutionClientFactory,
    InteractiveBrokersInstrumentProviderConfig,
)
from nautilus_trader.common import Environment, LoggerConfig
from nautilus_trader.live import LiveExecutionEngineConfig, LiveNode
from nautilus_trader.model import TraderId

client_id = int(sys.argv[1])
execution_config = InteractiveBrokersExecutionClientConfig(
    host="127.0.0.1",
    port=1,
    client_id=client_id,
    account_id="GATE1A-SYNTHETIC",
    instrument_provider=InteractiveBrokersInstrumentProviderConfig(
        load_ids=set(),
        load_contracts=[],
    ),
)
node = (
    LiveNode.builder(
        "Gate1AOffline",
        TraderId.from_str("GATE1A-001"),
        Environment.SANDBOX,
    )
    .with_logging(LoggerConfig(bypass_logging=True))
    .with_exec_engine_config(LiveExecutionEngineConfig())
    .add_exec_client(
        None,
        InteractiveBrokersExecutionClientFactory(),
        execution_config,
    )
    .build()
)
assert node.is_running is False
print(json.dumps({{"sentinel": "{CONSTRUCTION_SENTINEL}", "client_id": client_id}}))
"""

_FORBIDDEN_LIFECYCLE_CALLS = frozenset(
    {
        "connect",
        "disconnect",
        "generate_fill_reports",
        "generate_mass_status",
        "generate_order_status_report",
        "generate_order_status_reports",
        "generate_position_status_reports",
        "reconcile_execution_mass_status",
        "run",
        "run_async",
        "shutdown",
        "start",
        "stop",
    }
)
_FORBIDDEN_COMPOSITION_SYMBOLS = frozenset(
    {
        "InteractiveBrokersExecutionClientConfig",
        "InteractiveBrokersExecutionClientFactory",
    }
)
_FORBIDDEN_BROKER_COMMAND_SYMBOLS = frozenset(
    {
        "BatchCancelOrders",
        "CancelAllOrders",
        "CancelOrder",
        "ModifyOrder",
        "SubmitOrder",
        "SubmitOrderList",
    }
)


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _assert_construction_only(source: str) -> None:
    tree = ast.parse(source)
    violations = sorted(
        (node.lineno, name)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        if (name := _call_name(node)) in _FORBIDDEN_LIFECYCLE_CALLS
    )
    assert not violations, f"construction fixture invokes lifecycle/report calls: {violations}"


def _run_native_construction(client_id: int, *, timeout: int) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-B", "-c", _NATIVE_CONSTRUCTION_SCRIPT, str(client_id)],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=environment,
        cwd=ROOT,
    )


def _expect_native_construction_success(
    client_id: int,
    *,
    timeout: int = CONSTRUCTION_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[str]:
    try:
        result = _run_native_construction(client_id, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise AssertionError(
            f"native client {client_id} construction exceeded {timeout} seconds",
        ) from exc
    assert result.returncode == 0, (
        f"native client {client_id} construction failed with {result.returncode}: "
        f"{result.stderr}"
    )
    assert CONSTRUCTION_SENTINEL in result.stdout
    return result


def _repository_dependency_versions() -> tuple[str, str]:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = pyproject["project"]["dependencies"]
    requirement = next(
        item for item in dependencies if item.partition("==")[0] == "nautilus_trader"
    )
    match = re.fullmatch(r"nautilus_trader==([^\s]+)", requirement)
    assert match is not None, "nautilus_trader must remain an exact root dependency pin"

    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    locked_package = next(
        package for package in lock["package"] if package["name"] == "nautilus-trader"
    )
    return match.group(1), locked_package["version"]


def _assert_dependency_identity(
    project_version: str,
    lock_version: str,
    installed_version: str,
) -> None:
    assert project_version == lock_version == installed_version == PINNED_NAUTILUS_VERSION, (
        "Gate 1A evidence is version-bound: "
        f"project={project_version}, lock={lock_version}, installed={installed_version}, "
        f"expected={PINNED_NAUTILUS_VERSION}"
    )


def _validate_relevant_record_entries(distribution: Any) -> tuple[str, ...]:
    files = distribution.files
    assert files is not None, "installed Nautilus distribution has no RECORD file inventory"

    relevant = [
        entry
        for entry in files
        if str(entry).startswith("nautilus_trader/adapters/interactive_brokers/")
        and str(entry).endswith(("/__init__.py", "/__init__.pyi"))
    ]
    relevant.extend(
        entry
        for entry in files
        if str(entry).startswith("nautilus_trader/_libnautilus")
        and str(entry).endswith((".so", ".pyd"))
    )
    assert len(relevant) == 3, (
        "expected RECORD evidence for the IB Python module, stub, and native extension"
    )

    verified: list[str] = []
    for entry in relevant:
        assert entry.hash is not None, f"missing RECORD hash for {entry}"
        assert entry.size is not None, f"missing RECORD size for {entry}"
        path = Path(entry.locate())
        assert path.is_file(), f"installed artifact is missing: {entry}"
        payload = path.read_bytes()
        digest = hashlib.new(entry.hash.mode, payload).digest()
        encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        assert encoded == entry.hash.value, f"RECORD hash mismatch for {entry}"
        assert len(payload) == entry.size, f"RECORD size mismatch for {entry}"
        verified.append(str(entry))
    return tuple(sorted(verified))


def _composition_violations(source: str) -> tuple[tuple[int, str], ...]:
    tree = ast.parse(source)
    violations: set[tuple[int, str]] = set()
    forbidden_imports = _FORBIDDEN_COMPOSITION_SYMBOLS | _FORBIDDEN_BROKER_COMMAND_SYMBOLS

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for imported in node.names:
                if imported.name in forbidden_imports:
                    violations.add((node.lineno, imported.name))
        elif isinstance(node, ast.Attribute) and node.attr in forbidden_imports:
            violations.add((node.lineno, node.attr))
        elif isinstance(node, ast.Call):
            name = _call_name(node)
            if name == "add_exec_client" or name in forbidden_imports:
                violations.add((node.lineno, name))

    return tuple(sorted(violations))


def _assert_data_only_composition(sources: dict[Path, str]) -> None:
    violations = {
        str(path.relative_to(ROOT)): _composition_violations(source)
        for path, source in sources.items()
        if _composition_violations(source)
    }
    assert not violations, f"production execution/order wiring detected: {violations}"


def test_gate1a_dependency_identity_matches_lock() -> None:
    project_version, lock_version = _repository_dependency_versions()
    distribution = importlib.metadata.distribution("nautilus_trader")

    _assert_dependency_identity(project_version, lock_version, distribution.version)
    verified = _validate_relevant_record_entries(distribution)
    assert "nautilus_trader/adapters/interactive_brokers/__init__.py" in verified
    assert "nautilus_trader/adapters/interactive_brokers/__init__.pyi" in verified
    assert len(verified) == 3
    assert any(
        entry.startswith("nautilus_trader/_libnautilus")
        and entry.endswith((".so", ".pyd"))
        for entry in verified
    )


def test_gate1a_dependency_identity_rejects_drift() -> None:
    with pytest.raises(AssertionError, match="version-bound"):
        _assert_dependency_identity(PINNED_NAUTILUS_VERSION, "2.0.0rc5", "2.0.0rc5")


def test_gate1a_dependency_identity_requires_integrity_metadata() -> None:
    class DistributionWithoutRecord:
        files = None

    with pytest.raises(AssertionError, match="no RECORD"):
        _validate_relevant_record_entries(DistributionWithoutRecord())


def test_gate1a_execution_config_contract() -> None:
    config = InteractiveBrokersExecutionClientConfig()

    assert config.client_id == 1
    assert config.account_id is None
    assert config.fetch_all_open_orders is False
    assert config.track_option_exercise_from_position_update is False

    parameters = inspect.signature(InteractiveBrokersExecutionClientConfig).parameters
    assert {
        "master_client_id",
        "master_id",
        "observation_only",
        "read_only",
        "read_only_api",
    }.isdisjoint(parameters)


def test_gate1a_native_client_one_constructs() -> None:
    _expect_native_construction_success(1)


def test_gate1a_native_client_zero_rejected() -> None:
    result = _run_native_construction(0, timeout=CONSTRUCTION_TIMEOUT_SECONDS)

    assert result.returncode != 0
    assert "must not be a multiple of 1000" in result.stderr
    assert "order ID partitioning uses client_id % 1000" in result.stderr
    assert CONSTRUCTION_SENTINEL not in result.stdout


def test_gate1a_native_construction_reports_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def timeout(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd="gate1a", timeout=1)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(AssertionError, match="exceeded 1 seconds"):
        _expect_native_construction_success(1, timeout=1)


def test_gate1a_native_construction_reports_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess("gate1a", 7, "", "synthetic failure")

    monkeypatch.setattr(subprocess, "run", fail)
    with pytest.raises(AssertionError, match="failed with 7: synthetic failure"):
        _expect_native_construction_success(1)


def test_gate1a_characterization_code_does_not_invoke_lifecycle() -> None:
    _assert_construction_only(_NATIVE_CONSTRUCTION_SCRIPT)
    _assert_construction_only(
        "config = InteractiveBrokersExecutionClientConfig(client_id=1)",
    )


@pytest.mark.parametrize(
    "forbidden_call",
    [
        "node.start()",
        "node.run()",
        "node.run_async()",
        "client.connect()",
        "client.generate_mass_status()",
        "manager.reconcile_execution_mass_status()",
        "client.disconnect()",
    ],
)
def test_gate1a_characterization_guard_rejects_lifecycle_calls(
    forbidden_call: str,
) -> None:
    with pytest.raises(AssertionError, match="lifecycle/report calls"):
        _assert_construction_only(forbidden_call)


def test_gate1a_current_composition_remains_data_only() -> None:
    sources = {
        path: path.read_text(encoding="utf-8")
        for path in (ROOT / "src").rglob("*.py")
    }
    _assert_data_only_composition(sources)


@pytest.mark.parametrize(
    "source",
    [
        "from nautilus_trader.adapters.interactive_brokers import "
        "InteractiveBrokersExecutionClientFactory as Factory",
        "import nautilus_trader.adapters.interactive_brokers as ib\n"
        "factory = ib.InteractiveBrokersExecutionClientFactory()",
        "builder.add_exec_client(None, factory, config)",
        "from nautilus_trader.execution.messages import SubmitOrder as BrokerCommand",
        "command = SubmitOrder()",
    ],
)
def test_gate1a_composition_guard_rejects_execution_wiring(source: str) -> None:
    assert _composition_violations(source)


def test_gate1a_composition_guard_ignores_unrelated_words_and_methods() -> None:
    source = """
execution_note = "descriptive evidence only"
cache.reconcile()
resource.close()
"""
    assert _composition_violations(source) == ()
