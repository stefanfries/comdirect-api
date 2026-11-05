# Python 3.12 Environment Upgrade

## Current State

- `.python-version` is set to `3.12`; the project environment uses Python `3.12.12`.
- `.venv` was rebuilt with `uv sync --python 3.12 --extra sync`.
- `.venv-py311-backup` preserves the previous Python 3.11 environment.
- `.vscode/settings.json` points VS Code to `.venv\Scripts\python.exe`.
- `pyproject.toml` continues to support Python `>=3.11`; only the local environment pin changed.

## Verification

- `uv run python --version` reports Python `3.12.12`.
- `uv run pytest tests/ -q` passes: 120 tests.
- `uv run ruff check .` passes.

## Repository Changes To Preserve

- Keep the `.python-version` change to `3.12`; it is an uncommitted tracked change for this upgrade.
- Keep `.venv-py311-backup` until you no longer need the old environment; `.venv` and the backup are ignored by Git.
- `docs/order-placement-plan.md` is an existing untracked plan file and is unrelated to this upgrade.
