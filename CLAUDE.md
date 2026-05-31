# Comdirect API Client

Fully async Python client for the Comdirect banking/brokerage REST API.
Handles OAuth2 authentication including 2FA push-TAN, and exposes typed models for accounts,
depots, transactions, instruments, and documents.

## How to run / test

```bash
uv sync                         # Core client
uv sync --extra sync            # Add sync function dependencies (MongoDB, Azure)
uv run pytest tests/ -v         # 115 tests, ~80% coverage
uv run ruff check .             # Lint
```

## Architecture

- `src/comdirect_api/client.py` — main async client; use `ComdirectClient.create()` factory (handles full auth flow)
- `src/comdirect_api/models/` — 11 Pydantic V2 models; all use automatic camelCase → snake_case conversion
- `src/comdirect_api/settings.py` — credentials via pydantic-settings (CLIENT_ID, CLIENT_SECRET, ZUGANGSNUMMER, PIN)
- `src/comdirect_api/utils.py` — timestamp utilities
- `functions/sync/` — GitHub Actions entrypoint that syncs account snapshots to MongoDB Atlas

### Authentication flow

`OAuth2 token → session activation → TAN challenge (push) → banking token`

All steps handled by `ComdirectClient.create()`. Token refresh is automatic.

### API coverage (43% — 13 of 30 endpoints)

- Banking: accounts, balances, transactions ✓
- Brokerage: depots, positions, orders, instruments (partial)
- Messages: documents, predocuments ✓
- Reports: aggregated balances ✓

## Key behaviours

- All models must use the camelCase alias config from Pydantic — don't add raw field names for API fields
- The sync function (`functions/sync/`) runs via GitHub Actions `workflow_dispatch` — no server infrastructure needed
- Sync inserts are idempotent; duplicate transactions are detected by ID before insert

## External dependencies

- Comdirect developer credentials (CLIENT_ID, CLIENT_SECRET) — obtained from Comdirect developer portal
- MongoDB Atlas — for the sync function
- See `docs/ARCHITECTURE.md` for full design documentation
