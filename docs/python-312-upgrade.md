# Python 3.12 Environment Upgrade

## Current State

- `.python-version` is set to `3.12`; the project environment uses Python `3.12.12`.
- `.venv` was rebuilt with `uv sync --python 3.12 --extra sync`.
- The previous `.venv-py311-backup` environment has been deleted and its `.gitignore` entry removed.
- `.vscode/settings.json` points VS Code to `.venv\Scripts\python.exe` and enables activation in new terminals and the current terminal when the Python extension starts.
- `pyproject.toml` continues to support Python `>=3.11`; only the local environment pin changed.

## Verification

- `uv run python --version` reports Python `3.12.12`.
- `uv run pytest tests/ -q` passes: 125 tests, including the available-cash sync regression tests.
- `uv run ruff check .` passes.
- PowerShell activation was verified to resolve Python to `.venv\Scripts\python.exe`; automatic startup activation still requires a VS Code reload to confirm.

## Repository State

- The `.python-version` pin to `3.12` and the upgrade/order-placement documents were committed in `15f7e47`.
- The VS Code current-terminal activation setting was committed in `42bd637`.
- `.venv` remains ignored by Git; the deleted backup is no longer needed.
- [Order placement planning](order-placement-plan.md) is separate from the Python upgrade. The available-cash snapshot schema and sync behavior are documented in [the architecture guide](ARCHITECTURE.md#mongodb-collections).
