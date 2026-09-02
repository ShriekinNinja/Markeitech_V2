from __future__ import annotations

import ast
import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .diagnostics import ManifestError
from .models import ArchitectureManifest, CompositionPolicy, EnablementState


@dataclass(frozen=True, slots=True)
class ActorRegistrationFact:
    key: str
    actor_id: str
    composition_order: int


@dataclass(frozen=True, slots=True)
class ContractConstantFact:
    name: str
    value: str
    source_path: str


@dataclass(frozen=True, slots=True)
class CensusPolicy:
    node_path: str = "src/markeitech/system/node.py"
    composition_path: str = "src/markeitech/system/composition.py"
    contract_paths: tuple[str, ...] = (
        "src/markeitech/system/messages.py",
        "src/markeitech/system/resource_contracts.py",
        "src/markeitech/acquisition/historical_messages.py",
        "src/markeitech/intelligence/messages.py",
        "src/markeitech/intelligence/metrics.py",
        "src/markeitech/intelligence/completed_bars.py",
        "src/markeitech/intelligence/entities.py",
    )


@dataclass(frozen=True, slots=True)
class CensusReport:
    actor_registrations: tuple[ActorRegistrationFact, ...]
    contract_constants: tuple[ContractConstantFact, ...]
    checked_profiles: tuple[str, ...]
    checked_implementation_refs: tuple[str, ...]


def _repository_file(repository_root: Path, relative_path: str) -> Path:
    root = repository_root.resolve()
    path = root / relative_path
    if path.is_symlink():
        raise ManifestError(
            "DRIFT_UNSAFE_SOURCE_PATH",
            relative_path,
            "source evidence cannot be a symlink",
        )
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, ValueError) as exc:
        raise ManifestError(
            "DRIFT_SOURCE_ABSENT",
            relative_path,
            "repository-controlled source evidence is absent",
        ) from exc
    if not resolved.is_file():
        raise ManifestError(
            "DRIFT_SOURCE_TYPE",
            relative_path,
            "repository-controlled source evidence must be a regular file",
        )
    return resolved


def _parse_python(repository_root: Path, relative_path: str) -> ast.Module:
    path = _repository_file(repository_root, relative_path)
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=relative_path)
    except SyntaxError as exc:
        raise ManifestError(
            "DRIFT_SOURCE_SYNTAX",
            relative_path,
            "Python source cannot be parsed by the offline census",
        ) from exc


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _string_expression(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        pieces: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                pieces.append(value.value)
            else:
                pieces.append("*")
        return "".join(pieces)
    return None


def extract_actor_registrations(
    repository_root: Path,
    relative_path: str = "src/markeitech/system/composition.py",
) -> tuple[ActorRegistrationFact, ...]:
    tree = _parse_python(repository_root, relative_path)
    facts: list[ActorRegistrationFact] = []
    calls = sorted(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and _call_name(node) == "ActorRegistration"
        ),
        key=lambda node: (node.lineno, node.col_offset),
    )
    for composition_order, node in enumerate(calls, start=1):
        keywords = {keyword.arg: keyword.value for keyword in node.keywords if keyword.arg}
        key_node = keywords.get("key")
        actor_node = keywords.get("actor_id")
        if key_node is None or actor_node is None:
            raise ManifestError(
                "DRIFT_UNSUPPORTED_ACTOR_REGISTRATION",
                f"{relative_path}:{node.lineno}",
                "ActorRegistration must use explicit key and actor_id keywords",
            )
        key = _string_expression(key_node)
        actor_id = _string_expression(actor_node)
        if key is None:
            raise ManifestError(
                "DRIFT_UNSUPPORTED_ACTOR_REGISTRATION",
                f"{relative_path}:{node.lineno}",
                "actor registration key uses an unsupported source shape",
            )
        if actor_id is None:
            if key == "historical_dependency_probe:*":
                actor_id = "HISTORICAL-DEPENDENCY-PROBE-*"
            else:
                raise ManifestError(
                    "DRIFT_UNSUPPORTED_ACTOR_REGISTRATION",
                    f"{relative_path}:{node.lineno}",
                    "actor ID uses an unsupported source shape",
                )
        facts.append(
            ActorRegistrationFact(
                key=key,
                actor_id=actor_id,
                composition_order=composition_order,
            )
        )
    if not facts:
        raise ManifestError(
            "DRIFT_ACTOR_CENSUS_EMPTY",
            relative_path,
            "no ActorRegistration calls were found",
        )
    if len({fact.key for fact in facts}) != len(facts):
        raise ManifestError(
            "DRIFT_DUPLICATE_ACTOR_KEY",
            relative_path,
            "actor registration keys are not unique",
        )
    return tuple(facts)


def extract_contract_constants(
    repository_root: Path,
    relative_paths: tuple[str, ...],
) -> tuple[ContractConstantFact, ...]:
    facts: list[ContractConstantFact] = []
    for relative_path in relative_paths:
        tree = _parse_python(repository_root, relative_path)
        for node in tree.body:
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            if not (target.id.endswith("_SIGNAL") or target.id.endswith("_TYPE_NAME")):
                continue
            value = _string_expression(node.value)
            if value is None:
                raise ManifestError(
                    "DRIFT_UNSUPPORTED_CONTRACT_CONSTANT",
                    f"{relative_path}:{node.lineno}",
                    "contract identity must remain a literal string",
                )
            facts.append(
                ContractConstantFact(
                    name=target.id,
                    value=value,
                    source_path=relative_path,
                )
            )
    facts.sort(key=lambda item: (item.value, item.name, item.source_path))
    values = [fact.value for fact in facts]
    if len(set(values)) != len(values):
        raise ManifestError(
            "DRIFT_DUPLICATE_CONTRACT_IDENTITY",
            "contract_constants",
            "two source constants define the same transport identity",
        )
    return tuple(facts)


def _read_toml(repository_root: Path, relative_path: str) -> dict[str, Any]:
    path = _repository_file(repository_root, relative_path)
    try:
        with path.open("rb") as file:
            return tomllib.load(file)
    except tomllib.TOMLDecodeError as exc:
        raise ManifestError(
            "DRIFT_PROFILE_TOML",
            relative_path,
            "tracked profile is invalid TOML",
        ) from exc


def _dotted_value(raw: dict[str, Any], dotted_path: str, location: str) -> Any:
    value: Any = raw
    for part in dotted_path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise ManifestError(
                "DRIFT_PROFILE_KEY_ABSENT",
                location,
                "configuration condition is absent from the tracked profile",
            )
        value = value[part]
    return value


def _validate_node_shape(repository_root: Path, relative_path: str) -> None:
    tree = _parse_python(repository_root, relative_path)
    calls = {
        name
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        for name in [_call_name(node)]
        if name is not None
    }
    required_calls = {
        "InteractiveBrokersDataClientConfig",
        "add_actor_from_config",
        "add_data_client",
        "build",
        "builder",
    }
    missing = required_calls - calls
    if missing:
        raise ManifestError(
            "DRIFT_NODE_SHAPE",
            relative_path,
            "LiveNode construction no longer matches the supported offline census shape",
        )


def _validate_implementation_ref(repository_root: Path, implementation_ref: str) -> None:
    try:
        relative_path, symbol = implementation_ref.split(":", 1)
    except ValueError as exc:
        raise ManifestError(
            "DRIFT_IMPLEMENTATION_REF",
            implementation_ref,
            "implementation reference must be path:symbol",
        ) from exc
    tree = _parse_python(repository_root, relative_path)
    declared = {
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
    }
    if symbol not in declared:
        raise ManifestError(
            "DRIFT_IMPLEMENTATION_SYMBOL",
            implementation_ref,
            "implementation symbol is absent from the referenced source file",
        )


def validate_source_census(
    manifest: ArchitectureManifest,
    *,
    repository_root: Path,
    policy: CensusPolicy = CensusPolicy(),
) -> CensusReport:
    """Compare mechanically supported source/configuration facts with the manifest."""

    _validate_node_shape(repository_root, policy.node_path)
    actor_facts = extract_actor_registrations(repository_root, policy.composition_path)
    source_actor_by_key = {
        fact.key: (fact.actor_id, fact.composition_order) for fact in actor_facts
    }
    manifest_actor_by_key = {
        component.composition_key: (component.actor_id, component.composition_order)
        for component in manifest.components
        if component.composition_key is not None
    }
    if set(source_actor_by_key) != set(manifest_actor_by_key):
        raise ManifestError(
            "DRIFT_ACTOR_ROSTER",
            policy.composition_path,
            "manifest actor roster differs from the supported source census",
        )
    for key, identity in source_actor_by_key.items():
        if manifest_actor_by_key[key] != identity:
            raise ManifestError(
                "DRIFT_ACTOR_ID_OR_ORDER",
                key,
                "manifest actor ID or composition order differs from source",
            )

    contract_facts = extract_contract_constants(repository_root, policy.contract_paths)
    manifest_type_names = {contract.type_name for contract in manifest.contracts}
    missing_contracts = {fact.value for fact in contract_facts} - manifest_type_names
    if missing_contracts:
        raise ManifestError(
            "DRIFT_CONTRACT_ROSTER",
            "contracts",
            "manifest omits a supported literal signal or custom-data identity",
        )

    profiles_by_id = {profile.id: profile for profile in manifest.profiles}
    checked_profiles: list[str] = []
    for profile_id, profile in profiles_by_id.items():
        raw = _read_toml(repository_root, profile.config_path)
        schema_version = raw.get("schema_version")
        if schema_version != profile.config_schema_version:
            raise ManifestError(
                "DRIFT_PROFILE_SCHEMA",
                profile.config_path,
                "manifest profile schema version differs from source",
            )
        digest = hashlib.sha256(
            _repository_file(repository_root, profile.config_path).read_bytes()
        ).hexdigest()
        if profile.content_sha256 is None or profile.content_sha256 != digest:
            raise ManifestError(
                "DRIFT_PROFILE_HASH",
                profile.config_path,
                "manifest profile hash differs from source",
            )
        checked_profiles.append(profile_id)
        for component in manifest.components:
            states = {state.profile: state.enablement for state in component.profile_states}
            if profile_id not in states or component.composition_key is None:
                continue
            if component.composition_policy is CompositionPolicy.ALWAYS:
                expected = EnablementState.ENABLED
            elif component.configuration_path is not None:
                raw_enabled = _dotted_value(
                    raw,
                    component.configuration_path,
                    f"components.{component.id}.configuration_path",
                )
                if not isinstance(raw_enabled, bool):
                    raise ManifestError(
                        "DRIFT_PROFILE_CONDITION_TYPE",
                        f"components.{component.id}.configuration_path",
                        "supported composition condition must resolve to a boolean",
                    )
                expected = EnablementState.ENABLED if raw_enabled else EnablementState.DISABLED
            else:
                raise ManifestError(
                    "DRIFT_UNSUPPORTED_COMPOSITION_CONDITION",
                    component.id,
                    "conditional actor lacks a supported configuration path",
                )
            if states[profile_id] is not expected:
                raise ManifestError(
                    "DRIFT_PROFILE_ENABLEMENT",
                    f"components.{component.id}.profile_states",
                    "manifest profile enablement differs from tracked configuration",
                )

    implementation_refs = sorted(
        component.implementation_ref
        for component in manifest.components
        if component.implementation_ref is not None
    )
    for implementation_ref in implementation_refs:
        _validate_implementation_ref(repository_root, implementation_ref)

    for evidence in manifest.evidence:
        _repository_file(repository_root, evidence.source_path)

    return CensusReport(
        actor_registrations=actor_facts,
        contract_constants=contract_facts,
        checked_profiles=tuple(sorted(checked_profiles)),
        checked_implementation_refs=tuple(implementation_refs),
    )
