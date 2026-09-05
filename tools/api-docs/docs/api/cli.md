# Command-Line Entry Point

The unified Python CLI is the closed command surface for the Markeitech runtime and supported
repository tools. It is independent of PyCharm and other IDEs: an IDE launcher may call the same
entry point, but it does not own a command, argument, environment rule, or safety policy.

## Invocation

Provision the root environment explicitly with `uv sync --locked --dev`. Routine commands then use
the already-provisioned entry point:

```bash
.venv/bin/markeitech --help
```

When `.venv/bin` is already on `PATH`, `markeitech --help` is equivalent. The Python module form is
also equivalent:

```bash
.venv/bin/python -m markeitech --help
```

Do not put `uv run` in front of routine operations. It may create or synchronize the root
environment before the CLI can enforce its offline and tool-isolation checks. Dependency
provisioning remains a separate, explicit operation.

## Command hierarchy

```text
markeitech
├── system
│   ├── build
│   └── run
├── docs
│   ├── validate
│   ├── check
│   ├── generate
│   └── test
├── diagrams
│   ├── validate
│   ├── check
│   ├── generate
│   └── test
├── verify
│   ├── lint
│   ├── test
│   ├── all
│   └── postgres
└── environment
    └── check
```

Use nested help for current arguments and defaults, for example
`.venv/bin/markeitech system run --help`.

## Operations and side effects

| Command | Environment | Effect and prerequisites |
| --- | --- | --- |
| `system build` | Root | Constructs the configured Nautilus node without running it or connecting to a provider. |
| `system run` | Root, PostgreSQL, IB | Runs the connected system only after the exact `I_UNDERSTAND_THIS_CONNECTS_TO_IB` confirmation. It never supplies the confirmation or starts PostgreSQL automatically. |
| `docs validate` | API-doc tool | Validates the static documentation inputs and locked tool environment without generating output. |
| `docs check` | API-doc tool | Builds a temporary candidate and compares it with the tracked `docs/api` artifact set. |
| `docs generate` | API-doc tool | Atomically replaces the complete tracked `docs/api` artifact set after all safeguards pass. |
| `docs test` | API-doc tool | Runs the isolated suite, whose generation tests can rewrite tracked `docs/api`; inspect scoped diffs, untracked files, and worktree status afterward. |
| `diagrams validate` | Diagram tool | Validates the canonical TOML manifest without generating output. |
| `diagrams check` | Diagram tool | Validates the manifest plus the supported source/configuration drift census. |
| `diagrams generate` | Diagram tool | Regenerates the canonical complete diagram package with drift checking. |
| `diagrams test` | Diagram tool | Runs the isolated diagram test suite. |
| `verify lint` | Root | Runs Ruff over the authoritative source, tests, and tracked Python publishing helper. |
| `verify test` | Root | Runs the offline non-PostgreSQL pytest suite. |
| `verify all` | Root | Runs lint and then offline tests, stopping on the first failure. |
| `verify postgres` | Root, PostgreSQL | Runs only PostgreSQL-marked tests against the explicitly configured test database; it is excluded from `verify all`. |
| `environment check` | Root | Runs the setup doctor without starting services; `--with-ib` explicitly adds an IB listener check. |

The API-doc and diagram commands use separately locked environments. Provision them explicitly
when needed:

```bash
uv sync --project tools/api-docs --locked
uv sync --project tools/system-diagram --locked
```

The CLI diagnoses a missing or invalid tool environment and exits non-zero; it never provisions or
updates either environment itself.

## Process and authority boundaries

Fixed child processes run from the repository root and return their child exit codes. Interrupts
are forwarded to the owned process group, and cancellation returns the corresponding
shell-compatible status. The isolated tools receive deterministic Python and locale controls, not
the caller's runtime, provider, database, Discord, GitHub, proxy, or cloud environment variables.

The CLI contains no shell interpolation, command registry, arbitrary-command escape hatch, or
automatic service lifecycle. Runtime configuration supplies typed data; it does not define
executable commands. Connected runs, PostgreSQL service lifecycle, dependency installation,
GitHub publication, backups, restores, and connected acceptance remain explicit operations under
their dedicated procedures.

See the
[developer setup](https://github.com/ShriekinNinja/Markeitech_V2/blob/master/docs/operations/developer-setup.md),
[Interactive Brokers setup](https://github.com/ShriekinNinja/Markeitech_V2/blob/master/docs/operations/ib-setup.md),
[API-documentation procedure](https://github.com/ShriekinNinja/Markeitech_V2/blob/master/docs/operations/v2-api-documentation.md),
and
[system-diagram maintenance procedure](https://github.com/ShriekinNinja/Markeitech_V2/blob/master/tools/system-diagram/docs/maintenance.md)
for detailed prerequisites, configuration, generation, review, and safety requirements.

## Public Python entry point

### ::: markeitech.cli.main
