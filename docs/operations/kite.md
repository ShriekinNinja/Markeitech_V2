# Kite Operations

This runbook governs the development-time Kite plugin and its separate project advisor roles.
Installing Kite makes it available. A fresh task remains normal Codex until the user explicitly
selects Kite or invokes `$kite:markeitech-advisor-router`. Existing tasks retain loaded definitions.
Kite does not implement Sir Loke or activate runtime services.

Commands below were checked against `codex-cli 0.150.1`. Run from the intended Markeitech checkout.
Use `codex plugin --help` and the subcommand's `--help` if a later CLI rejects a flag; do not hand-edit
Codex marketplace registration or cache files. Source changes follow the
[GitHub workflow](github-workflow.md); package installation/removal is a separate authorized host
operation. A PR review request to install and test its candidate authorizes that bounded operation.

## What Is Installed And What Is Loaded

| Surface | Owner and lifecycle |
| --- | --- |
| `plugins/kite/` | Tracked source: manifest, bundled skills, policy, resolver, fixtures and validators. |
| `.agents/plugins/marketplace.json` | Tracked local marketplace definition pointing to the plugin source. Registration records the checkout's absolute path. |
| Codex installed plugin cache | CLI-managed copy of the bundle. Source edits do not update it automatically. |
| `.codex/agents/markeitech-*-advisor.toml` | Twenty tracked project roles, discovered separately from the plugin. They are not bundled by plugin installation. |
| Current task | A loaded snapshot of skills, role definitions, and host/tool capabilities; start a new task after changes. |

The plugin and role definitions must come from the same reviewed source revision. Opening an older
checkout can reload fixed model settings even when the new plugin is installed. Plugin uninstall
alone does not revoke project roles. Role read-only defaults do not prove effective host isolation.

## Inspect And Validate Before An Operation

```bash
git status --short --branch
git rev-parse HEAD
codex --version
codex plugin marketplace list
codex plugin list --marketplace markeitech --json
python3 -B plugins/kite/scripts/validate_advisor_council.py
python3 -B -m unittest discover -s plugins/kite/tests
python3 -B scripts/kite-package.py identity
```

Record the source revision, existing marketplace source path, installed version/enabled state, and
package identity before an update. Preserve unrelated changes. `identity` hashes every package
file by relative path and content; it never installs, writes cache files, or reads host credentials.
Unit tests use disposable fixtures and are source validation, not a read-only consultation command.

## Install From The Intended Checkout

```bash
codex plugin marketplace add "$PWD" --json
codex plugin marketplace list
codex plugin add kite@markeitech --json
codex plugin list --marketplace markeitech --json
```

Confirm that `markeitech` resolves to this checkout before installing. If an existing registration
points elsewhere and the CLI refuses to replace it, preserve its original path, then use the
marketplace removal/add procedure below to register the intended checkout. Registration removal
and plugin uninstall are different operations. Never update an unrelated marketplace.

Use the installation result's cache path for verification. On the inspected host the cache is
under `$CODEX_HOME/plugins/cache/markeitech/kite/VERSION` (normally `~/.codex/plugins/cache/...`).
`VERSION` means the exact installed manifest version, not the source path returned by `plugin list`.
Set the following variable to that observed cache directory:

```bash
KITE_INSTALLED_ROOT='/absolute/observed/cache/markeitech/kite/VERSION'
python3 -B scripts/kite-package.py verify --installed-root "$KITE_INSTALLED_ROOT"
```

Require `BYTE_IDENTICAL`, matching versions, file count, and SHA-256 identity. The verifier rejects
missing manifests, symlinks, extra/missing/changed files, and accidentally comparing source to itself.
A matching version string alone is insufficient. Installation success also does not establish
router invocation, effective allocation, or permission isolation.

## Update Or Reinstall

For an authorized source update, finish source validation, then use the tracked version procedure:

```bash
python3 -B scripts/kite-package.py bump
git diff -- plugins/kite/.codex-plugin/plugin.json \
  plugins/kite/skills/markeitech-advisor-router/references/council-policy.toml
python3 -B -m unittest discover -s plugins/kite/tests
```

`bump` validates before and after, replaces one `+codex.YYYYMMDDHHMMSS` UTC suffix, and updates
manifest and council `plugin_version` together. `--stamp YYYYMMDDHHMMSS` supplies an explicit UTC
stamp for reproducible operations. It changes only these two source fields; inspect and commit
both in the scoped PR. An unchanged stamp or inconsistent starting pair is rejected. If interrupted
between writes, inspect those two files and restore a matching pair from the intended revision
before retrying. No untracked helper or machine-specific skill script is required.

Register the intended checkout, run `codex plugin add kite@markeitech --json` again, then verify
byte identity as above. Local marketplaces read local source; `marketplace upgrade` refreshes Git
marketplace snapshots and is not a replacement for versioning/reinstalling a local bundle.
For a repair reinstall of unchanged source, first try `plugin add`; if it retains stale contents,
uninstall only Kite and add it again. Never repair by copying files into the installed cache.

## Fresh-Task Acceptance

Start a new task rooted in the same reviewed checkout after installation and role changes. Official
[plugin guidance](https://learn.chatgpt.com/docs/plugins) also requires a new chat or CLI session to
load newly installed skills. For a bounded read-only CLI check, use `codex exec -C "$PWD" -s read-only`
with an explicit Kite invocation and the authorized consultation question. A task launched before
the change is not acceptance evidence, including this task's already-loaded child-role schema.

Check the actual task can discover the installed router and exact project role, has no fixed role
model/effort overrides, and supports the chosen pair/context mode. Perform router selection, run
the resolver through the [stdin control-record protocol](../../plugins/kite/skills/markeitech-advisor-router/references/resource-allocation.md),
then spawn the exact role using its validated model, effort, and fork mode. Capture the decision ID,
child execution ID, completion, and effective settings from host metadata. A child repeating a
model name is insufficient. Keep acceptance records outside the plugin so recording results does
not change the package that was tested.

Issue #39 requires two materially different questions producing different real model/effort
allocations for the same unchanged advisor. Record the role file hash before and after. Confirm
that negative allocation gates stop before spawning; do not spend model calls on invalid requests.
The [acceptance record](../development/kite-allocation-acceptance.md) states observed scope and
remaining gates. Keep issue #39 open until its acceptance conditions pass; source tests alone are
insufficient. This is execution acceptance, not a comparative quality, latency, or cost benchmark.

## Uninstall, Purge, And Marketplace Removal

These are operator procedures, not steps performed during ordinary verification. For an authorized
Kite bundle uninstall:

```bash
codex plugin remove kite@markeitech --json
codex plugin list --marketplace markeitech --json
```

Require Kite absent from `installed`; it may remain `available` through the marketplace. Check the
previously recorded cache path. The CLI owns its cleanup; if a residual directory remains, record
it as a failed cache-purge check and use the CLI recovery path/support rather than deleting a broad
cache tree. This removes the installed plugin registration/bundle; it does not delete source,
project roles, marketplaces, past task records, or unrelated configuration.

To additionally remove the local marketplace registration:

```bash
codex plugin marketplace remove markeitech --json
codex plugin marketplace list
```

If removing both, uninstall the plugin first. Require the named registration absent. This does not
delete the repository or its `.agents/plugins/marketplace.json`, and does not retroactively change
loaded tasks. Restore availability by registering the recorded source path and installing again.

A **complete Kite capability purge for a project** means both bundle uninstall and removing that
project's twenty role definitions. Since those roles are tracked project source, removal requires
an explicitly authorized scoped PR that removes the policy-listed role files and reconciles the
entry-point/council documents and validators. Review the exact list first:

```bash
git ls-files '.codex/agents/markeitech-*-advisor.toml'
```

Do not delete all `.codex`, generic agents, another checkout's files, user settings, or credentials.
Removing roles from one checkout does not remove them from other worktrees. If roles are retained,
report **bundle uninstalled, project roles retained**; never call that complete revocation. For an
immediate local session without these roles, start outside every checkout containing them, after
bundle uninstall. Validate fresh discovery there. A source removal PR becomes project-wide policy
only after review/merge and checkout updates. Already-loaded tasks must be ended; historical task
records are retained and are outside the capability-purge scope.

## Recovery And Rollback

| Symptom | Bounded recovery |
| --- | --- |
| Wrong source path/version | Inspect registration and git revision, repoint only `markeitech` via CLI to the intended checkout, install, and verify bytes. |
| Cache differs despite matching version | Validate source, create a new version for changed source, install again; for unchanged source use the repair reinstall above. |
| Missing/malformed custom role | Check that task cwd is the reviewed project and role TOML parses; fix source through its PR, then start a new task. Do not substitute a generic agent. |
| Fixed overrides in the live role | The task or checkout is stale; load the matching role source in a fresh task. Do not declare an allocation pass. |
| Resolver reports blocked | Preserve the sanitized reason and stop that consultation; correct evidence/requirements through the normal workflow. Do not invent host capacity or silently switch models. |
| Candidate cache disappears or an older version returns | Preserve initial/final identities and check registration again. One repair reinstall can restore current bytes, but stop installed-behavior acceptance until host replacement behavior is resolved; do not loop reinstalls or edit cache files. |
| Installation partially fails | Inspect CLI listing and the recorded cache path before retrying; never assume a failed response means no mutation occurred. |

Rollback uses a known reviewed revision containing a coherent bundle **and** project-role set.
Use a separate checkout of that revision (or a reviewed source restoration PR), register its path,
reinstall via CLI, verify against that checkout, and start a new task there. Preserve the failed
candidate for review; do not reset user work. Restoring an older plugin beside newer roles, or older
fixed roles beside the dynamic router, is not a valid rollback. To undo only a temporary marketplace
repoint, register its recorded previous path through the CLI and verify the restored package/roles
before starting work. Do not silently switch back to an older source after accepting a new package.
