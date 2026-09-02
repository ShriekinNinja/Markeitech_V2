#!/usr/bin/env python3
"""Validate the repository-owned Kite advisor council without third-party packages."""

from __future__ import annotations

import argparse
import json
import re
import stat
import sys
import tomllib
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

ALLOWED_MODELS = {"gpt-5.6-sol"}
ALLOWED_REASONING = {"medium", "high", "xhigh"}
ROUTE_MODES = {"NO_COUNCIL", "SINGLE", "MULTI", "BLOCKED"}
ACTIVATION_SOURCES = {
    "none": False,
    "casual_mention": False,
    "explicit_router": True,
    "explicit_plugin": True,
    "direct_kite_task_followup": True,
    "unrelated_request": False,
    "explicit_specialist": False,
}
ACTIVATION_CLASS_EXPECTATIONS = {
    "fresh_session_default": ("none", False, False, False),
    "ordinary_substantive_default": ("none", False, False, False),
    "casual_mention": ("casual_mention", False, False, False),
    "explicit_router": ("explicit_router", True, True, True),
    "explicit_plugin": ("explicit_plugin", True, True, True),
    "direct_followup": ("direct_kite_task_followup", True, True, True),
    "unrelated_reset": ("unrelated_request", False, False, False),
    "explicit_trivial": ("explicit_router", True, True, False),
    "explicit_specialist": ("explicit_specialist", False, False, False),
}
DEPRECATED_IDENTIFIERS = {
    "markeitech_market_evidence_validation_advisor",
    "markeitech-market-evidence-validation-expert",
}
REQUIRED_POLICY_FIELDS = {
    "role",
    "skill",
    "domain",
    "model",
    "reasoning",
    "tier",
    "owns",
    "excludes",
    "inputs",
    "output",
    "default_after",
    "handoffs",
    "fresh_primary_sources",
    "network",
}


def repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def extract_skill_name(skill_path: Path) -> str | None:
    text = skill_path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(?P<header>.*?)\n---\s*\n", text, re.DOTALL)
    if match is None:
        return None
    name = re.search(r"(?m)^name:\s*[\"']?([^\"'\n]+)[\"']?\s*$", match.group("header"))
    return name.group(1).strip() if name else None


def extract_implicit_invocation(interface_path: Path) -> bool | None:
    text = interface_path.read_text(encoding="utf-8")
    matches = re.findall(
        r"(?m)^\s*allow_implicit_invocation:\s*(true|false)\s*$",
        text,
    )
    if len(matches) > 1:
        raise ValueError(f"{interface_path} declares allow_implicit_invocation more than once")
    if not matches:
        return None
    return matches[0] == "true"


def extract_default_prompt(interface_path: Path) -> str | None:
    text = interface_path.read_text(encoding="utf-8")
    match = re.search(r'(?m)^\s*default_prompt:\s*"(?P<value>.*)"\s*$', text)
    return match.group("value") if match else None


def find_cycle(graph: Mapping[str, Iterable[str]]) -> list[str] | None:
    visited: set[str] = set()
    active: set[str] = set()
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        if node in active:
            start = stack.index(node)
            return [*stack[start:], node]
        if node in visited:
            return None
        active.add(node)
        stack.append(node)
        for dependency in graph.get(node, ()):
            cycle = visit(dependency)
            if cycle is not None:
                return cycle
        stack.pop()
        active.remove(node)
        visited.add(node)
        return None

    for role in graph:
        cycle = visit(role)
        if cycle is not None:
            return cycle
    return None


def duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    repeated: set[str] = set()
    for value in values:
        if value in seen:
            repeated.add(value)
        seen.add(value)
    return repeated


def validate_repo(root: Path) -> list[str]:
    errors: list[str] = []
    plugin_root = root / "plugins" / "kite"
    skills_root = plugin_root / "skills"
    router_root = skills_root / "markeitech-advisor-router"
    references = router_root / "references"
    agent_root = root / ".codex" / "agents"

    required_paths = {
        "policy": references / "council-policy.toml",
        "cases": references / "routing-cases.toml",
        "guide": references / "council-routing-contracts.md",
        "acceptance": references / "routing-acceptance.md",
        "plugin": plugin_root / ".codex-plugin" / "plugin.json",
        "marketplace": root / ".agents" / "plugins" / "marketplace.json",
        "project_config": root / ".codex" / "config.toml",
        "router_skill": router_root / "SKILL.md",
        "router_interface": router_root / "agents" / "openai.yaml",
        "agents_md": root / "AGENTS.md",
    }
    for label, path in required_paths.items():
        if not path.is_file():
            errors.append(f"missing {label}: {path.relative_to(root)}")
    if errors:
        return errors

    try:
        policy = load_toml(required_paths["policy"])
        cases_doc = load_toml(required_paths["cases"])
        plugin = load_json(required_paths["plugin"])
        marketplace = load_json(required_paths["marketplace"])
        project_config = load_toml(required_paths["project_config"])
    except (OSError, ValueError, tomllib.TOMLDecodeError, json.JSONDecodeError) as exc:
        return [f"parse failure: {exc}"]

    advisors = policy.get("advisors")
    if not isinstance(advisors, list):
        return ["council policy must define [[advisors]] entries"]
    if len(advisors) != 20:
        errors.append(f"expected 20 policy advisors, found {len(advisors)}")
    if policy.get("schema_version") != 2:
        errors.append("council policy schema_version must be 2")

    policy_roles: list[str] = []
    policy_skills: list[str] = []
    advisor_by_role: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(advisors):
        if not isinstance(raw, dict):
            errors.append(f"policy advisor {index} is not a table")
            continue
        missing = sorted(REQUIRED_POLICY_FIELDS - raw.keys())
        if missing:
            errors.append(f"policy advisor {index} missing fields: {', '.join(missing)}")
            continue
        role = raw.get("role")
        skill = raw.get("skill")
        if not isinstance(role, str) or not isinstance(skill, str):
            errors.append(f"policy advisor {index} has invalid role or skill")
            continue
        policy_roles.append(role)
        policy_skills.append(skill)
        advisor_by_role[role] = raw
        if raw.get("model") not in ALLOWED_MODELS:
            errors.append(f"{role}: unsupported model {raw.get('model')!r}")
        if raw.get("reasoning") not in ALLOWED_REASONING:
            errors.append(f"{role}: unsupported reasoning {raw.get('reasoning')!r}")
        fresh_sources = raw.get("fresh_primary_sources")
        if not isinstance(fresh_sources, bool):
            errors.append(f"{role}: fresh_primary_sources must be boolean")
        cross_cutting = raw.get("cross_cutting", False)
        if not isinstance(cross_cutting, bool):
            errors.append(f"{role}: cross_cutting must be boolean when present")
        expected_network = "approved_public_read_only" if fresh_sources is True else "deny"
        if raw.get("network") != expected_network:
            errors.append(f"{role}: network must be {expected_network!r}")

    for duplicate in sorted(duplicates(policy_roles)):
        errors.append(f"duplicate policy role: {duplicate}")
    for duplicate in sorted(duplicates(policy_skills)):
        errors.append(f"duplicate policy skill: {duplicate}")
    if len(set(raw.get("domain") for raw in advisors if isinstance(raw, dict))) != len(advisors):
        errors.append("policy advisor domains must be unique")

    defaults = policy.get("defaults", {})
    expected_defaults = {
        "kite_activation": "explicit_task_only",
        "fresh_session": "normal_codex",
        "continuation": "direct_kite_task_followups_only",
        "casual_mention": "does_not_activate",
        "filesystem": "read_only_consultation",
        "mcp_servers": [],
        "network": "deny",
        "direct_primary_invocation": "custom_role_or_explicit_user_only",
        "direct_specialist_invocation": "narrow_override_no_kite_mode",
        "external_actions": "deny",
        "authenticated_sessions": "deny",
        "secrets": "deny",
        "failure": "stop_affected_conclusion",
        "selection": "smallest_sufficient_set",
        "ordering": "explicit_selected_role_dag",
    }
    for field, expected in expected_defaults.items():
        if defaults.get(field) != expected:
            errors.append(f"policy defaults.{field} must be {expected!r}")

    graph: dict[str, list[str]] = {}
    role_set = set(policy_roles)
    for role, advisor in advisor_by_role.items():
        dependencies = advisor.get("default_after", [])
        handoffs = advisor.get("handoffs", [])
        if not isinstance(dependencies, list) or not all(
            isinstance(item, str) for item in dependencies
        ):
            errors.append(f"{role}: default_after must be a string array")
            dependencies = []
        if not isinstance(handoffs, list) or not all(isinstance(item, str) for item in handoffs):
            errors.append(f"{role}: handoffs must be a string array")
            handoffs = []
        for target in [*dependencies, *handoffs]:
            if target not in role_set:
                errors.append(f"{role}: unknown role reference {target}")
        graph[role] = dependencies
    cycle = find_cycle(graph)
    if cycle:
        errors.append(f"default dependency cycle: {' -> '.join(cycle)}")

    agent_files = sorted(agent_root.glob("markeitech-*-advisor.toml"))
    if len(agent_files) != 20:
        errors.append(f"expected 20 custom-agent files, found {len(agent_files)}")
    agent_roles: set[str] = set()
    agent_role_names: list[str] = []
    project_mcp = project_config.get("mcp_servers", {})
    if not isinstance(project_mcp, dict):
        errors.append("project mcp_servers must be a table")
        project_mcp = {}
    for path in agent_files:
        try:
            agent = load_toml(path)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")
            continue
        role = agent.get("name")
        if not isinstance(role, str):
            errors.append(f"{path.relative_to(root)}: missing string name")
            continue
        agent_role_names.append(role)
        agent_roles.add(role)
        expected_filename = f"{role.replace('_', '-')}.toml"
        if path.name != expected_filename:
            errors.append(f"{role}: expected filename {expected_filename}, found {path.name}")
        policy_agent = advisor_by_role.get(role)
        if policy_agent is None:
            errors.append(f"{role}: custom role missing from policy")
            continue
        if agent.get("model") != policy_agent["model"]:
            errors.append(f"{role}: model differs from policy")
        if agent.get("model_reasoning_effort") != policy_agent["reasoning"]:
            errors.append(f"{role}: reasoning differs from policy")
        if agent.get("sandbox_mode") != "read-only":
            errors.append(f"{role}: sandbox_mode must be read-only")
        instructions = agent.get("developer_instructions")
        if not isinstance(instructions, str):
            errors.append(f"{role}: missing developer_instructions")
            continue
        skill_refs = re.findall(r"\$kite:([a-z0-9-]+)", instructions)
        if skill_refs != [policy_agent["skill"]]:
            errors.append(
                f"{role}: expected one $kite:{policy_agent['skill']} invocation, found {skill_refs}"
            )
        lowered = " ".join(instructions.lower().split())
        if "read-only" not in lowered:
            errors.append(f"{role}: safety kernel missing 'read-only'")
        if re.search(r"do not [^.]{0,500}\bedit\b", lowered) is None:
            errors.append(f"{role}: safety kernel does not prohibit editing")
        if re.search(r"do not [^.]{0,500}\bdelegate\b", lowered) is None:
            errors.append(f"{role}: safety kernel does not prohibit delegation")
        agent_mcp = agent.get("mcp_servers", {})
        if not isinstance(agent_mcp, dict):
            errors.append(f"{role}: mcp_servers must be a table")
            continue
        if set(agent_mcp) != set(project_mcp):
            errors.append(
                f"{role}: MCP override IDs must exactly match project MCP IDs; "
                f"found={sorted(agent_mcp)}, expected={sorted(project_mcp)}"
            )
        for server_id in project_mcp:
            override = agent_mcp.get(server_id)
            if not isinstance(override, dict) or override.get("enabled") is not False:
                errors.append(f"{role}: project MCP {server_id!r} must be explicitly disabled")
                continue
            project_server = project_mcp.get(server_id)
            if not isinstance(project_server, dict):
                errors.append(f"project MCP {server_id!r} must be a table")
                continue
            expected_override = {**project_server, "enabled": False}
            if override != expected_override:
                errors.append(
                    f"{role}: disabled MCP {server_id!r} must preserve the exact project "
                    "transport and configuration plus enabled = false"
                )

    for duplicate in sorted(duplicates(agent_role_names)):
        errors.append(f"duplicate custom-agent role name: {duplicate}")

    if agent_roles != role_set:
        errors.append(
            "custom-role/policy mismatch: "
            f"missing={sorted(role_set - agent_roles)}, extra={sorted(agent_roles - role_set)}"
        )

    skill_dirs = sorted(
        path for path in skills_root.glob("markeitech-*-expert") if (path / "SKILL.md").is_file()
    )
    skill_names: set[str] = set()
    for skill_dir in skill_dirs:
        name = extract_skill_name(skill_dir / "SKILL.md")
        if name is None:
            errors.append(f"{skill_dir.relative_to(root)}: invalid SKILL.md frontmatter")
            continue
        skill_names.add(name)
        if name != skill_dir.name:
            errors.append(
                f"{skill_dir.relative_to(root)}: frontmatter name {name!r} differs from folder"
            )
        interface_path = skill_dir / "agents" / "openai.yaml"
        if not interface_path.is_file():
            errors.append(f"{skill_dir.relative_to(root)}: missing agents/openai.yaml")
            continue
        try:
            implicit = extract_implicit_invocation(interface_path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if implicit is not False:
            errors.append(
                f"{skill_dir.name}: specialist skill must set allow_implicit_invocation false"
            )
        prompt = extract_default_prompt(interface_path)
        if prompt is None or f"$kite:{name}" not in prompt:
            errors.append(f"{skill_dir.name}: default_prompt must mention $kite:{name}")

    if skill_names != set(policy_skills):
        errors.append(
            "specialist-skill/policy mismatch: "
            f"missing={sorted(set(policy_skills) - skill_names)}, "
            f"extra={sorted(skill_names - set(policy_skills))}"
        )

    router_name = extract_skill_name(required_paths["router_skill"])
    if router_name != policy.get("router_skill"):
        errors.append("router skill name differs from council policy")
    try:
        router_implicit = extract_implicit_invocation(required_paths["router_interface"])
        if router_implicit is not False:
            errors.append("router skill must set allow_implicit_invocation false")
        router_prompt = extract_default_prompt(required_paths["router_interface"])
        if router_prompt is None or f"$kite:{router_name}" not in router_prompt:
            errors.append(f"router default_prompt must mention $kite:{router_name}")
    except ValueError as exc:
        errors.append(str(exc))

    cases = cases_doc.get("cases")
    if not isinstance(cases, list):
        errors.append("routing cases must define [[cases]] entries")
        cases = []
    if cases_doc.get("policy_version") != policy.get("policy_version"):
        errors.append("routing cases policy_version differs from council policy")
    if cases_doc.get("schema_version") != 2:
        errors.append("routing cases schema_version must be 2")

    activation_cases = cases_doc.get("activation_cases")
    if not isinstance(activation_cases, list):
        errors.append("routing cases must define [[activation_cases]] entries")
        activation_cases = []
    activation_ids: list[str] = []
    activation_classes: set[str] = set()
    for index, case in enumerate(activation_cases):
        if not isinstance(case, dict):
            errors.append(f"activation case {index} is not a table")
            continue
        case_id = case.get("id")
        case_class = case.get("class")
        prompt = case.get("prompt")
        source = case.get("activation_source")
        active = case.get("kite_active")
        router_expected = case.get("router_expected")
        advisors_expected = case.get("advisors_expected")
        specialist_skill = case.get("specialist_skill")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"activation case {index} has no string id")
            continue
        activation_ids.append(case_id)
        if not isinstance(case_class, str) or not case_class:
            errors.append(f"{case_id}: class must be a non-empty string")
        else:
            activation_classes.add(case_class)
        if not isinstance(prompt, str) or not prompt:
            errors.append(f"{case_id}: prompt must be a non-empty string")
        if source not in ACTIVATION_SOURCES:
            errors.append(f"{case_id}: invalid activation_source {source!r}")
        for field, value in (
            ("kite_active", active),
            ("router_expected", router_expected),
            ("advisors_expected", advisors_expected),
        ):
            if not isinstance(value, bool):
                errors.append(f"{case_id}: {field} must be boolean")
        if source in ACTIVATION_SOURCES and isinstance(active, bool):
            if active is not ACTIVATION_SOURCES[source]:
                errors.append(f"{case_id}: kite_active contradicts activation_source")
        if active is False and (router_expected is not False or advisors_expected is not False):
            errors.append(f"{case_id}: inactive Kite cannot route or invoke advisors")
        if router_expected is False and advisors_expected is True:
            errors.append(f"{case_id}: advisors require the Kite router")
        if case_class == "explicit_specialist":
            if specialist_skill not in policy_skills:
                errors.append(
                    f"{case_id}: explicit specialist must name one policy specialist skill"
                )
            elif isinstance(prompt, str) and f"$kite:{specialist_skill}" not in prompt:
                errors.append(
                    f"{case_id}: prompt must explicitly invoke $kite:{specialist_skill}"
                )
        elif specialist_skill is not None:
            errors.append(f"{case_id}: specialist_skill is only valid for explicit_specialist")
        expected_activation = ACTIVATION_CLASS_EXPECTATIONS.get(case_class)
        if expected_activation is not None:
            actual_activation = (source, active, router_expected, advisors_expected)
            if actual_activation != expected_activation:
                errors.append(
                    f"{case_id}: activation class {case_class} requires "
                    f"{expected_activation!r}, found {actual_activation!r}"
                )
    for duplicate in sorted(duplicates(activation_ids)):
        errors.append(f"duplicate activation case: {duplicate}")
    missing_activation_classes = set(ACTIVATION_CLASS_EXPECTATIONS) - activation_classes
    if missing_activation_classes:
        errors.append(
            "routing cases do not cover activation classes: "
            f"{sorted(missing_activation_classes)}"
        )
    case_ids: list[str] = []
    covered_roles: set[str] = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            errors.append(f"routing case {index} is not a table")
            continue
        case_id = case.get("id")
        if not isinstance(case_id, str):
            errors.append(f"routing case {index} has no string id")
            continue
        case_ids.append(case_id)
        for field in ("class", "prompt", "stop"):
            if not isinstance(case.get(field), str) or not case[field].strip():
                errors.append(f"{case_id}: {field} must be a non-empty string")
        if case.get("route_mode") not in ROUTE_MODES:
            errors.append(f"{case_id}: invalid route_mode {case.get('route_mode')!r}")
        expected = case.get("expected_roles")
        allowed = case.get("allowed_roles")
        for field, roles in (("expected_roles", expected), ("allowed_roles", allowed)):
            if not isinstance(roles, list) or not all(isinstance(item, str) for item in roles):
                errors.append(f"{case_id}: {field} must be a string array")
                continue
            for role in roles:
                if role not in role_set:
                    errors.append(f"{case_id}: unknown role {role}")
                covered_roles.add(role)
        if isinstance(expected, list) and isinstance(allowed, list):
            overlap = set(expected) & set(allowed)
            if overlap:
                errors.append(
                    f"{case_id}: expected_roles and allowed_roles overlap: {sorted(overlap)}"
                )
        if case.get("route_mode") == "SINGLE" and isinstance(expected, list) and len(expected) != 1:
            errors.append(f"{case_id}: SINGLE requires exactly one expected role")
        if case.get("route_mode") == "MULTI" and isinstance(expected, list) and len(expected) < 2:
            errors.append(f"{case_id}: MULTI requires at least two expected roles")
        if case.get("route_mode") == "NO_COUNCIL" and expected != []:
            errors.append(f"{case_id}: NO_COUNCIL requires no expected roles")
        if case.get("route_mode") == "BLOCKED" and case.get("stop") == "none":
            errors.append(f"{case_id}: BLOCKED requires a material stop reason")

        edges = case.get("edges")
        if case.get("route_mode") == "MULTI" and edges is None:
            errors.append(f"{case_id}: MULTI must declare explicit edges, including []")
        if edges is None:
            edges = []
        if not isinstance(edges, list):
            errors.append(f"{case_id}: edges must be an array")
            edges = []
        edge_graph: dict[str, list[str]] = {
            role: [] for role in expected if isinstance(role, str)
        } if isinstance(expected, list) else {}
        non_default_edges: list[tuple[str, str]] = []
        expected_index = {
            role: position for position, role in enumerate(expected)
        } if isinstance(expected, list) else {}
        for edge in edges:
            if (
                not isinstance(edge, list)
                or len(edge) != 2
                or not all(isinstance(role, str) for role in edge)
            ):
                errors.append(f"{case_id}: every edge must contain two role IDs")
                continue
            before, after = edge
            if before not in expected_index or after not in expected_index:
                errors.append(f"{case_id}: edge endpoints must both be expected roles: {edge}")
                continue
            edge_graph.setdefault(before, []).append(after)
            if expected_index[before] >= expected_index[after]:
                errors.append(f"{case_id}: expected_roles is not topological for edge {edge}")
            default_dependencies = advisor_by_role.get(after, {}).get("default_after", [])
            if before not in default_dependencies:
                non_default_edges.append((before, after))
        edge_cycle = find_cycle(edge_graph)
        if edge_cycle:
            errors.append(f"{case_id}: dependency cycle: {' -> '.join(edge_cycle)}")
        if non_default_edges and not isinstance(case.get("override_reason"), str):
            errors.append(
                f"{case_id}: non-default edges require override_reason: {non_default_edges}"
            )

        bypass = case.get("must_not_invoke_skill_directly")
        if bypass is not None and not isinstance(bypass, bool):
            errors.append(f"{case_id}: must_not_invoke_skill_directly must be boolean")
        if case.get("class") == "direct_skill_bypass" and bypass is not True:
            errors.append(f"{case_id}: direct_skill_bypass must assert custom-role invocation")
    for duplicate in sorted(duplicates(case_ids)):
        errors.append(f"duplicate routing case: {duplicate}")
    if covered_roles != role_set:
        errors.append(f"routing cases do not cover roles: {sorted(role_set - covered_roles)}")

    if plugin.get("version") != policy.get("plugin_version"):
        errors.append("plugin version differs from council policy")
    if plugin.get("skills") != "./skills/":
        errors.append("plugin manifest must expose ./skills/")
    interface = plugin.get("interface")
    default_prompts = interface.get("defaultPrompt") if isinstance(interface, dict) else None
    if not isinstance(default_prompts, list) or not default_prompts:
        errors.append("plugin manifest must declare defaultPrompt entries")
    elif not all(
        isinstance(prompt, str) and f"$kite:{router_name}" in prompt
        for prompt in default_prompts
    ):
        errors.append("every plugin defaultPrompt must explicitly invoke the Kite router")
    for forbidden_key in ("apps", "dependencies", "mcpServers", "mcp_servers", "runtime"):
        if forbidden_key in plugin:
            errors.append(f"plugin manifest unexpectedly declares {forbidden_key}")
    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or len(plugins) != 1:
        errors.append("local marketplace must contain exactly the Kite plugin entry")
    else:
        entry = plugins[0]
        source = entry.get("source", {}) if isinstance(entry, dict) else {}
        if (
            entry.get("name") != "kite"
            or source.get("source") != "local"
            or source.get("path") != "./plugins/kite"
        ):
            errors.append("local marketplace Kite source is not ./plugins/kite")

    agents_text = required_paths["agents_md"].read_text(encoding="utf-8")
    normalized_agents_text = " ".join(agents_text.split())
    required_activation_text = (
        "A fresh Codex task starts in normal Codex mode.",
        "Merely mentioning or discussing Kite is not activation.",
        "This section applies only while Kite mode is active.",
    )
    for statement in required_activation_text:
        if statement not in normalized_agents_text:
            errors.append(f"AGENTS.md missing Kite activation boundary: {statement}")
    if (
        "automatically invoke the bundled `$kite:markeitech-advisor-router`"
        in agents_text.lower()
    ):
        errors.append("AGENTS.md must not automatically invoke Kite from ordinary prompts")

    for path in plugin_root.rglob("*"):
        relative = path.relative_to(root)
        generated = (
            "__pycache__" in path.parts
            or path.suffix in {".pyc", ".pyo"}
            or path.name == ".DS_Store"
        )
        if generated:
            errors.append(f"plugin contains generated/cache artifact: {relative}")
        elif path.is_symlink():
            errors.append(f"plugin contains symlink: {path.relative_to(root)}")
        elif path.is_file() and stat.S_IMODE(path.stat().st_mode) & 0o111:
            errors.append(f"plugin contains executable file: {path.relative_to(root)}")

    guide = required_paths["guide"].read_text(encoding="utf-8")
    for role in role_set:
        if role not in guide:
            errors.append(f"human routing guide omits {role}")

    searchable = "\n".join(
        [
            required_paths["policy"].read_text(encoding="utf-8"),
            required_paths["cases"].read_text(encoding="utf-8"),
            *[path.name for path in agent_files],
            *[path.name for path in skill_dirs],
        ]
    )
    for identifier in DEPRECATED_IDENTIFIERS:
        if identifier in searchable:
            errors.append(f"deprecated identifier is callable or policy-visible: {identifier}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repository_root())
    args = parser.parse_args(argv)
    root = args.root.resolve()
    errors = validate_repo(root)
    if errors:
        print("Kite advisor council validation: FAIL", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    policy = load_toml(
        root
        / "plugins"
        / "kite"
        / "skills"
        / "markeitech-advisor-router"
        / "references"
        / "council-policy.toml"
    )
    cases = load_toml(
        root
        / "plugins"
        / "kite"
        / "skills"
        / "markeitech-advisor-router"
        / "references"
        / "routing-cases.toml"
    )
    print(
        "Kite advisor council validation: PASS "
        f"({len(policy['advisors'])} advisors, {len(cases['cases'])} routing cases, "
        f"{len(cases['activation_cases'])} activation cases)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
