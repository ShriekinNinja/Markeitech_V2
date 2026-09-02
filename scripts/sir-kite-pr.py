#!/usr/bin/env python3
"""Publish a Markeitech PR using a locally configured GitHub App installation.

Uses Python's standard library, curl's verified TLS, and OpenSSL. Credentials stay
outside Git; tokens travel through stdin, are never printed, and are revoked on exit.
"""

import argparse
import base64
import json
import os
import stat
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlencode

EXPECTED_PERMISSIONS = {"contents": "read", "metadata": "read", "pull_requests": "write"}


def load_config(path):
    """Load private local configuration without admitting a repository-local key."""
    config = json.loads(path.read_text())
    required = {
        "app_id",
        "client_id",
        "installation_id",
        "repository_id",
        "repository",
        "owner",
        "slug",
        "private_key",
    }
    if set(config) != required:
        raise ValueError("Unexpected Sir Kite configuration fields")
    for name in ("app_id", "installation_id", "repository_id"):
        if type(config[name]) is not int or config[name] <= 0:
            raise ValueError("App, installation, and repository IDs must be positive integers")
    for name in required - {"app_id", "installation_id", "repository_id"}:
        if not isinstance(config[name], str) or not config[name].strip():
            raise ValueError("Configuration strings must be non-empty")
    if config["repository"] != "ShriekinNinja/Markeitech_V2":
        raise ValueError("This command is restricted to ShriekinNinja/Markeitech_V2")
    if config["owner"] != "ShriekinNinja" or config["slug"] != "sir-kite":
        raise ValueError("Unexpected GitHub App owner or slug")
    key = Path(config["private_key"]).expanduser().resolve()
    if key.is_relative_to(Path(__file__).resolve().parents[1]):
        raise ValueError("The private key must be outside the repository")
    mode = key.stat().st_mode
    if not stat.S_ISREG(mode) or mode & 0o077:
        raise ValueError("The private key must be a regular file accessible only to its owner")
    config["private_key"] = str(key)
    return config


def request(path, token, method="GET", payload=None):
    """Call only GitHub's HTTPS API; do not follow redirects or expose credentials."""
    if not path.startswith("/") or "\n" in path or "\r" in path:
        raise ValueError("Invalid GitHub API path")
    command = [
        "curl",
        "--disable",
        "--silent",
        "--show-error",
        "--fail",
        "--max-time",
        "30",
        "--proto",
        "=https",
        "--request",
        method,
        "--header",
        "@-",
        "https://api.github.com" + path,
    ]
    if payload is not None:
        command += ["--data-binary", json.dumps(payload)]
    headers = (
        f"Authorization: Bearer {token}\nAccept: application/vnd.github+json\n"
        "X-GitHub-Api-Version: 2022-11-28\nContent-Type: application/json\n"
        "User-Agent: Sir-Kite-PR\n"
    )
    result = subprocess.run(command, input=headers.encode(), capture_output=True, timeout=40)
    if result.returncode:
        # Neither API bodies nor subprocess diagnostics are safe credential output.
        raise RuntimeError(f"GitHub {method} failed (curl exit {result.returncode})")
    return json.loads(result.stdout) if result.stdout else None


def make_jwt(config):
    """Sign a five-minute app JWT locally; the PEM is never passed as an argument."""

    def encode(value):
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode()

    now = int(time.time())
    claims = {"iat": now - 60, "exp": now + 300, "iss": config["client_id"]}
    message = encode(b'{"alg":"RS256","typ":"JWT"}') + "." + encode(json.dumps(claims).encode())
    result = subprocess.run(
        ["openssl", "dgst", "-sha256", "-sign", config["private_key"]],
        input=message.encode(),
        capture_output=True,
        timeout=10,
    )
    if result.returncode:
        raise RuntimeError("Could not sign the GitHub App token")
    return message + "." + encode(result.stdout)


@contextmanager
def installation_token(config):
    """Validate app/installation identity, narrow scope, and revoke the issued token."""
    jwt = make_jwt(config)
    app = request("/app", jwt)
    if (app["id"], app["slug"], app["owner"]["login"]) != (
        config["app_id"],
        config["slug"],
        config["owner"],
    ):
        raise ValueError("The key belongs to a different GitHub App")
    installation = request(f"/app/installations/{config['installation_id']}", jwt)
    if (
        installation["app_id"] != config["app_id"]
        or installation["account"]["login"] != config["owner"]
        or installation["repository_selection"] != "selected"
        or installation["permissions"] != EXPECTED_PERMISSIONS
    ):
        raise ValueError("Installation identity or permissions differ from the approved scope")
    result = request(
        f"/app/installations/{config['installation_id']}/access_tokens",
        jwt,
        "POST",
        {"repository_ids": [config["repository_id"]], "permissions": EXPECTED_PERMISSIONS},
    )
    token = result["token"]
    try:
        repositories = request("/installation/repositories", token)
        if (
            result["permissions"] != EXPECTED_PERMISSIONS
            or repositories["total_count"] != 1
            or [(r["id"], r["full_name"]) for r in repositories["repositories"]]
            != [(config["repository_id"], config["repository"])]
        ):
            raise ValueError("Installation token has an unexpected repository or permission scope")
        yield token
    finally:
        try:
            request("/installation/token", token, "DELETE")
        except (RuntimeError, subprocess.TimeoutExpired):
            print("Warning: token revocation failed; it expires within one hour.", file=sys.stderr)


def publish(config, token, args):
    """Create or update this branch's bot PR and explicitly request owner review."""
    root = f"/repos/{config['repository']}"
    query = urlencode({"state": "open", "base": "master", "head": f"{config['owner']}:{args.head}"})
    existing = request(root + "/pulls?" + query, token)
    if len(existing) > 1 or (existing and existing[0]["user"]["login"] != config["slug"] + "[bot]"):
        raise ValueError("An existing PR has a different author; resolve it before publishing")
    payload = {"title": args.title, "body": args.body_file.read_text()}
    if existing:
        pr = request(root + f"/pulls/{existing[0]['number']}", token, "PATCH", payload)
    else:
        payload.update(head=args.head, base="master", draft=args.draft)
        pr = request(root + "/pulls", token, "POST", payload)
    # Report the resource before dependent operations, so a partial failure is recoverable.
    print(pr["html_url"], flush=True)
    if pr["user"]["login"] != config["slug"] + "[bot]":
        raise ValueError("GitHub returned an unexpected PR author")
    number = pr["number"]
    if not pr["draft"]:
        requested = request(root + f"/pulls/{number}/requested_reviewers", token)
        if config["owner"] not in [user["login"] for user in requested["users"]]:
            request(
                root + f"/pulls/{number}/requested_reviewers",
                token,
                "POST",
                {"reviewers": [config["owner"]]},
            )
    if args.label:
        request(root + f"/issues/{number}/labels", token, "POST", {"labels": args.label})
    print(f"Author: {pr['user']['login']}; head: {pr['head']['sha']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(
            os.environ.get(
                "SIR_KITE_CONFIG",
                "~/.config/markeitech/sir-kite/config.json",
            )
        ).expanduser(),
    )
    parser.add_argument("--verify", action="store_true", help="Verify credentials/scope only")
    parser.add_argument("--head", help="Published branch; master is the fixed PR base")
    parser.add_argument("--title")
    parser.add_argument("--body-file", type=Path)
    parser.add_argument("--label", action="append", default=[])
    parser.add_argument(
        "--draft", action="store_true", help="Create as draft without a review request"
    )
    args = parser.parse_args()
    if not args.verify and not all((args.head, args.title, args.body_file)):
        parser.error("Publishing requires --head, --title, and --body-file")
    try:
        config = load_config(args.config)
        with installation_token(config) as token:
            if args.verify:
                print(f"Verified {config['slug']} on {config['repository']}")
            else:
                publish(config, token, args)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        # Do not print arbitrary exception text: JSON/subprocess errors may contain credentials.
        print(
            f"Sir Kite operation failed ({type(exc).__name__}); "
            "check configuration and GitHub state.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
