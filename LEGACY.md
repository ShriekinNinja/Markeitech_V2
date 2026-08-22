# Preserved V1 Project

Markeitech V2 is the only active runtime. V1 remains in this repository as historical source and
design evidence; it is not installed, tested, or launched by the V2 workflow.

Preserved V1 surfaces include:

- `backend/`
- `config/`
- `frontend/`
- root `tests/`
- root `pyproject.toml` and `uv.lock`
- V1 architecture, operations, roadmap, research, notes, and archive documents
- archived PyCharm launchers under `docs/archive/v1-run-configurations/`

Do not run root `uv sync`, V1 console scripts, or archived launchers when developing V2. Use the
commands in the root `README.md` and the `v2/` project. The root `scripts/check-env` command is the
active V2 setup doctor.

Nothing in this preservation boundary is implicitly active. Moving or deleting V1 requires a
separate reviewed migration with an explicit recovery point.
