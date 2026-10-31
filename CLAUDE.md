# Comdirect API Client

Fully async Python client for the Comdirect banking/brokerage REST API.
Handles OAuth2 authentication including 2FA push-TAN, and exposes typed models for accounts,
depots, transactions, instruments, and documents.

## How to run / test

```bash
uv sync                         # Core client
uv sync --extra sync            # Add sync function dependencies (MongoDB, Azure)
uv run pytest tests/ -v         # 120 tests
uv run pytest --cov=src/comdirect_api --cov-report=term-missing -q  # 120 tests, 79% client-package coverage
uv run ruff check .             # Lint
```

## Architecture

- `src/comdirect_api/client.py` — main async client; use `ComdirectClient.create()` factory (handles full auth flow)
- `src/comdirect_api/models/` — Pydantic V2 response models; all use automatic camelCase → snake_case conversion
- `src/comdirect_api/settings.py` — credentials via pydantic-settings (`CLIENT_ID`, `CLIENT_SECRET`, and `ACCOUNTS__<NAME>__ZUGANGSNUMMER/PIN`)
- `src/comdirect_api/utils.py` — timestamp utilities
- `functions/sync/` — GitHub Actions entrypoint that syncs account snapshots to MongoDB Atlas

### Authentication flow

`OAuth2 token → session activation → TAN challenge (push) → banking token`

All steps handled by `ComdirectClient.create()`. Pass `zugangsnummer` and `pin` explicitly;
OAuth application credentials default to `settings`. Token refresh is automatic.

### API coverage (47% — 14 of 30 Swagger operations)

- Banking: accounts, balances, transactions ✓
- Brokerage: depots, positions, orders, instruments (partial)
- Messages: documents, predocuments ✓
- Reports: aggregated balances ✓

Order placement and the Livetrading quote flow are not implemented; order support is read-only.

## Key behaviours

- All models must use the camelCase alias config from Pydantic — don't add raw field names for API fields
- The sync function (`functions/sync/`) runs via GitHub Actions `workflow_dispatch` — no server infrastructure needed
- Sync inserts are idempotent; duplicate transactions are detected by ID before insert

## External dependencies

- Comdirect developer credentials (CLIENT_ID, CLIENT_SECRET) — obtained from Comdirect developer portal
- MongoDB Atlas — for the sync function
- See `docs/ARCHITECTURE.md` for full design documentation
