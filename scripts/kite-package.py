"""Version and verify the local Kite package; never install or edit host configuration."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/kite"


def inventory(root: Path) -> dict[str, str]:
    if not root.is_dir() or root.is_symlink():
        raise ValueError("PACKAGE_DIRECTORY_REQUIRED")
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("PACKAGE_SYMLINK")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    if ".codex-plugin/plugin.json" not in result:
        raise ValueError("PLUGIN_MANIFEST_REQUIRED")
    return result


def identity(root: Path) -> dict:
    files = inventory(root)
    return {
        "version": json.loads((root / ".codex-plugin/plugin.json").read_text())["version"],
        "files": len(files),
        "sha256": hashlib.sha256(
            json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }


def bump(root: Path, stamp: str) -> str:
    if not re.fullmatch(r"\d{14}", stamp):
        raise ValueError("STAMP_MUST_BE_UTC_YYYYMMDDHHMMSS")
    datetime.strptime(stamp, "%Y%m%d%H%M%S")
    manifest = root / ".codex-plugin/plugin.json"
    policy = root / "skills/markeitech-advisor-router/references/council-policy.toml"
    data = json.loads(manifest.read_text())
    old = data["version"]
    content = policy.read_text()
    if tomllib.loads(content)["plugin_version"] != old:
        raise ValueError("SOURCE_VERSION_MISMATCH")
    version = old.split("+", 1)[0] + "+codex." + stamp
    if version == old:
        raise ValueError("VERSION_UNCHANGED")
    line = f'plugin_version = "{old}"'
    if content.count(line) != 1:
        raise ValueError("POLICY_VERSION_LINE_AMBIGUOUS")
    data["version"] = version
    manifest.write_text(json.dumps(data, indent=2) + "\n")
    policy.write_text(content.replace(line, f'plugin_version = "{version}"'))
    return version


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    version = commands.add_parser("bump")
    version.add_argument("--stamp", default=datetime.now(UTC).strftime("%Y%m%d%H%M%S"))
    commands.add_parser("identity")
    verify = commands.add_parser("verify")
    verify.add_argument("--installed-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "bump":
            validator = [sys.executable, "-B", str(PLUGIN / "scripts/validate_advisor_council.py")]
            subprocess.run(validator, check=True, cwd=ROOT)
            bump(PLUGIN, args.stamp)
            subprocess.run(validator, check=True, cwd=ROOT)
        result = identity(PLUGIN)
        if args.command == "verify":
            if PLUGIN.resolve() == args.installed_root.resolve():
                raise ValueError("INSTALLED_ROOT_IS_SOURCE")
            cached = identity(args.installed_root)
            if inventory(PLUGIN) != inventory(args.installed_root):
                raise ValueError("PACKAGE_CONTENT_MISMATCH")
            result["installed"] = cached
            result["status"] = "BYTE_IDENTICAL"
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        reason = str(exc) if type(exc) is ValueError else "PACKAGE_OPERATION_FAILED"
        print(json.dumps({"status": "BLOCKED", "reason": reason}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
