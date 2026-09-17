"""Check the focused Kite package offline; does not evaluate instruction-following behavior."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ENTRYPOINT = "markeitech-advisor-router"


def validate(root: Path) -> list[str]:
    """Return structural defects without importing runtime code or reading host settings."""
    errors: list[str] = []
    plugin = root / "plugins/kite"
    try:
        manifest = json.loads((plugin / ".codex-plugin/plugin.json").read_text())
    except (OSError, ValueError):
        return ["Kite manifest is missing or invalid"]
    if manifest.get("name") != "kite" or manifest.get("skills") != "./skills/":
        errors.append("Manifest must expose the Kite skill library")
    if not isinstance(manifest.get("version"), str) or not manifest["version"]:
        errors.append("Manifest version is required")
    if any(key in manifest for key in ("mcpServers", "apps", "hooks", "agents")):
        errors.append("Kite is a skill-only package; additional capabilities need explicit review")

    roles = list((root / ".codex/agents").glob("markeitech-*-advisor.toml"))
    if roles:
        errors.append("Retired Kite project advisor roles are still discoverable")
    for retired in ("resolve_advisor_allocation.py", "resolve_advisor_dispatch.py"):
        if (plugin / "scripts" / retired).exists():
            errors.append(f"Retired council resolver remains: {retired}")

    entries = sorted((plugin / "skills").glob("*/SKILL.md"))
    if not (plugin / "skills" / ENTRYPOINT / "SKILL.md").is_file():
        errors.append("Compatible Kite entrypoint is missing")
    names: set[str] = set()
    for entry in entries:
        content = entry.read_text()
        front = re.match(r"\A---\n(.*?)\n---\n", content, re.DOTALL)
        fields = (
            dict(re.findall(r"^(name|description): (.+)$", front[1], re.MULTILINE))
            if front else {}
        )
        name = fields.get("name", "")
        if name != entry.parent.name or not re.fullmatch(r"[a-z0-9-]{1,64}", name):
            errors.append(f"Invalid skill identity: {entry.parent.name}")
        if name in names:
            errors.append(f"Duplicate skill identity: {name}")
        names.add(name)
        if not fields.get("description"):
            errors.append(f"Missing skill description: {entry.parent.name}")
        metadata = entry.parent / "agents/openai.yaml"
        text = metadata.read_text() if metadata.is_file() else ""
        # The supported local metadata uses one policy mapping, not arbitrary YAML features.
        policies = re.findall(r"^policy:\n((?:[ \t]+[^\n]*\n|\n)*)", text, re.MULTILINE)
        if len(policies) != 1 or not re.search(
            r"^  allow_implicit_invocation: false$", policies[0], re.MULTILINE
        ):
            errors.append(f"Explicit-only policy missing: {entry.parent.name}")
        if f"$kite:{name}" not in text:
            errors.append(f"Qualified invocation missing: {entry.parent.name}")

    for path in plugin.rglob("*"):
        if path.is_symlink():
            errors.append(f"Package symlink: {path.relative_to(plugin)}")
            continue
        if path.suffix != ".md" or not path.is_file():
            continue
        # Check local Markdown destinations; external sources and anchors are not fetched.
        for target in re.findall(r"\[[^\]\n]*\]\(([^)\s]+)\)", path.read_text()):
            if "://" in target or target.startswith(("#", "mailto:")):
                continue
            target = target.split("#", 1)[0]
            if target and not (path.parent / target).exists():
                errors.append(f"Broken local link: {path.relative_to(plugin)} -> {target}")
    return errors


def main() -> int:
    errors = validate(ROOT)
    if errors:
        print("FAIL\n" + "\n".join(errors))
        return 1
    count = len(list((ROOT / "plugins/kite/skills").glob("*/SKILL.md")))
    print(f"PASS ({count} skill entrypoints; no retired project advisors; local links valid)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
