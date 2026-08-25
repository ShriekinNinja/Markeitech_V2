# Primary Source Census

Research snapshot: 2026-08-25. Refresh the subset relevant to each consultation; URLs and versions
can drift. This census records why a source belongs in the workflow, not permanent conclusions.

## Local Authority And Executable Contract

| Source | Snapshot | Use | Boundary |
|---|---|---|---|
| `AGENTS.md`, `markeitech.md`, `docs/current-status.md`, `docs/development-guidelines.md`, `docs/README.md` | commit `c6af7a59f33700f5f1c263f38dc41a835fe59981` | Permissions, evidence bar, current implementation, authority order | Repository authority; refresh in current checkout |
| `docs/architecture/v2-runtime-control-plane.md` | same commit | Health ownership and lifecycle history | Later accepted documents and status can supersede it |
| `docs/operations/v2-runtime-resource-telemetry.md` | same commit | Current measurement meanings and resource-policy separation | Correlation is not causation |
| `v2/pyproject.toml`, `v2/uv.lock` | same commit | Python pin, dependencies, build, tests, lint target | Lockfile does not prove runtime behavior |
| Relevant `v2/src/markeitech` and `v2/tests` | task-specific | Exact implementation and exercised behavior | Inspect narrowly; tests prove only covered paths |

At this snapshot the project declares Python `>=3.13,<3.14` and the lock declares `==3.13.*`.
Reinspect rather than carrying that fact forward.

## CPython And Language Authorities

| Primary source | Version/access | What it supports | Guardrail |
|---|---|---|---|
| [Python 3.13 asyncio overview](https://docs.python.org/3.13/library/asyncio.html) | 3.13.15; accessed 2026-08-25 | High- and low-level async API families | Overview is not an application lifecycle guarantee |
| [Coroutines and tasks](https://docs.python.org/3.13/library/asyncio-task.html) | 3.13.15; accessed 2026-08-25 | Task ownership, cancellation, `TaskGroup`, timeouts, threads, eager execution | Match exact 3.13 semantics; do not swallow cancellation |
| [Developing with asyncio](https://docs.python.org/3.13/library/asyncio-dev.html) | 3.13 series; accessed 2026-08-25 | Debug mode, thread safety, blocking-code diagnostics, never-awaited work | Development diagnostics have runtime overhead |
| [Asyncio queues](https://docs.python.org/3.13/library/asyncio-queue.html) | 3.13 series; accessed 2026-08-25 | Queue capacity and task accounting | Capacity alone does not define admission or loss policy |
| [Concurrent futures](https://docs.python.org/3.13/library/concurrent.futures.html) | 3.13.15; accessed 2026-08-25 | Executor lifecycle, deadlock cases, process pickling/start rules | `asyncio.Future` and concurrent futures are distinct; platform behavior varies |
| [Concurrent execution index](https://docs.python.org/3.13/library/concurrency.html) | 3.13.15; accessed 2026-08-25 | Threads/processes/event-driven choice families | Select from workload and ownership evidence |
| [Context variables](https://docs.python.org/3.13/library/contextvars.html) | 3.13 series; accessed 2026-08-25 | Context-local state across async tasks | Not a substitute for explicit ownership or synchronization |
| [PEP 654](https://peps.python.org/pep-0654/) | final; accessed 2026-08-25 | Exception groups and `except*` semantics | Raising grouped exceptions can be an API change |
| [Python 3.13 free-threading HOWTO](https://docs.python.org/3.13/howto/free-threading-python.html) and [PEP 703](https://peps.python.org/pep-0703/) | experimental 3.13 support; accessed 2026-08-25 | Detecting and reasoning about no-GIL builds | Never infer build mode from `3.13`; extension support and memory behavior matter |

## Typing And Packaging Authorities

| Primary source | Access | What it supports | Guardrail |
|---|---|---|---|
| [Python typing specification](https://typing.python.org/en/latest/spec/) | accessed 2026-08-25 | Assignability, generics, protocols, narrowing, type information | Static typing is not runtime validation |
| [Protocol specification](https://typing.python.org/en/latest/spec/protocol.html) | accessed 2026-08-25 | Structural subtyping and generic protocols | Check variance and actual checker behavior |
| [Type narrowing specification](https://typing.python.org/en/latest/spec/narrowing.html) | accessed 2026-08-25 | `TypeGuard` and `TypeIs` contracts | Guard correctness is a runtime responsibility |
| [PyPA `pyproject.toml` specification](https://packaging.python.org/en/latest/specifications/pyproject-toml/) | accessed 2026-08-25 | Build-system, project, and tool metadata | Do not change packaging/dependencies without approval |
| [PyPA packaging flow](https://packaging.python.org/en/latest/flow/) | accessed 2026-08-25 | Source tree, metadata, sdist, and wheel roles | Markeitech is not presumed to publish to PyPI |

## Profiling And Resource Authorities

| Primary source | Version/access | What it supports | Guardrail |
|---|---|---|---|
| [Python profilers](https://docs.python.org/3.13/library/profile.html) | 3.13 series; accessed 2026-08-25 | `cProfile`, `pstats`, call counts, deterministic profiling | Profiling is not benchmarking and biases Python/native comparisons |
| [tracemalloc](https://docs.python.org/3.13/library/tracemalloc.html) | 3.13 series; accessed 2026-08-25 | Python allocation tracebacks and snapshot differences | Does not equal total RSS or prove causality |
| [resource](https://docs.python.org/3.13/library/resource.html) | 3.13 series; accessed 2026-08-25 | Unix process/thread resource usage and limits | Availability and units are platform-dependent |

## Rejected As Authority

- Search snippets, generic production-Python blogs, benchmark leaderboards, and remembered framework
  behavior: useful only for discovering primary sources.
- Python 3.14/3.15 facilities as current-pin contracts: they may inform explicit upgrade research,
  never 3.13 implementation advice.
- Public agent skills: useful for instruction packaging only, not concurrency, performance, or
  Markeitech architecture conclusions.
- Current custom implementation as proof that its architecture is optimal.
