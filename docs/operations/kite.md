# Kite Operations

Kite is a repository-owned library of focused skills. Installing it makes it available. Explicitly
select Kite or invoke `$kite:markeitech-advisor-router` to use it; the retained command now selects
guidance for the primary agent. A domain skill may also be invoked directly for one question.
Kite provides development guidance; it does not activate runtime services.

## Source, Installation, And Loaded Tasks

| Surface | Meaning |
| --- | --- |
| `plugins/kite/` | Manifest, skills, optional references, source validator, and package tests. |
| `.agents/plugins/marketplace.json` | Existing local marketplace definition pointing to the bundle. |
| Installed plugin cache | CLI-managed copy; source edits do not refresh it automatically. |
| Project `.codex/agents` | The old twenty Kite roles are retired in issue #63; unrelated roles/configuration are preserved. |
| Current task | Loaded definitions may be old. Start a fresh task after an authorized update. |

Existing tasks and older worktrees can still contain old definitions. Installation alone does not
remove roles in an older checkout. Use the reviewed source revision and fresh task together.
No global Codex settings, other worktrees, or installed caches are edited by source verification.

## Offline Source Checks

Run from the intended checkout:

```bash
git status --short --branch
git rev-parse HEAD
python3 -B plugins/kite/scripts/validate_skill_library.py
python3 -B -m unittest discover -s plugins/kite/tests
python3 -B scripts/kite-package.py identity
```

The validator checks library structure and links. The unit tests use disposable fixtures.
Neither invokes a model, installs a plugin, connects a service, or proves skill behavior. Use
[behavior checks](../../plugins/kite/skills/markeitech-advisor-router/references/behavior-checks.md)
when changing the instructions, and preserve the distinction between expected and observed results.

## Versioning And Authorized Installation

Source changes follow the [GitHub workflow](github-workflow.md). Installation is a separate host
operation; an explicit request to install and test a PR candidate authorizes that bounded operation.
The manifest is the sole package-version owner. Before committing changed package contents, use:

```bash
python3 -B scripts/kite-package.py bump
```

This validates the source and replaces the single UTC cachebuster suffix while preserving the base
version. `--stamp YYYYMMDDHHMMSS` supports reproducible versioning. The helper never installs or
edits host configuration. Review and commit the changed manifest with its source.

For an authorized install, inspect the actual CLI and marketplace registration first:

```bash
codex --version
codex plugin marketplace list
codex plugin list --marketplace markeitech --json
```

CLI forms were checked with version 0.150.1; use the current command's `--help` if it rejects a
flag. Confirm that the local `markeitech` registration points to the intended checkout. If it
already does, install with:

```bash
codex plugin add kite@markeitech --json
```

If an explicitly authorized install requires registering this repository's non-default local
marketplace, record the previous source path and use `codex plugin marketplace add "$PWD" --json`.
If the CLI refuses a conflicting registration, remove only the `markeitech` registration through
`codex plugin marketplace remove markeitech --json`, then add the intended checkout. Do not hand-edit
marketplace or host configuration, and do not change another marketplace.

Use the actual cache path returned by installation, not an assumed source or version directory:

```bash
KITE_INSTALLED_ROOT='/absolute/cache/path/returned/by/installation'
python3 -B scripts/kite-package.py verify --installed-root "$KITE_INSTALLED_ROOT"
```

Require `BYTE_IDENTICAL`; a matching version string is insufficient. Start a new task rooted in
the reviewed checkout. Verify explicit Kite activation and a narrow request from the behavior
checks. Report installed discovery separately from source-directed evaluation and human usefulness.
Do not invoke IB/TWS, Discord, databases, or live models to test development-time skills.

## Recovery, Removal, And Rollback

For stale contents, inspect source registration and byte identity first. For changed source,
version and reinstall it. For a repair of unchanged source, one authorized remove/add attempt may
be used through the CLI; do not loop reinstalls or copy files into the cache.

For an authorized uninstall:

```bash
codex plugin remove kite@markeitech --json
codex plugin list --marketplace markeitech --json
```

Kite may remain available through the marketplace after uninstall. Removing its marketplace
registration is a separate operation. Historical task records and other checkouts remain intact;
uninstall does not retroactively revoke already-loaded tasks. Report residual cache or old-role
state accurately and use CLI recovery, rather than deleting broad host directories.

Rollback uses a separate checkout of a reviewed revision, an authorized CLI registration/install,
byte verification, and a fresh task. Preserve failed candidates and unrelated work. A rollback to
the former council revision also restores its matching project roles and instructions in that
checkout; do not mix old roles with the new workflow or silently restore old host settings.
