# Multi-Account Settings

## Background

The Comdirect API uses `CLIENT_ID` / `CLIENT_SECRET` as OAuth **application** credentials (registered once in the developer portal). `ZUGANGSNUMMER` + `PIN` are the **customer** login credentials.

- If all depots belong to the **same Comdirect login**, one set of credentials is enough — `get_account_depots()` returns all depots automatically.
- If depots belong to **different Comdirect accounts** (different logins), each account needs its own `ZUGANGSNUMMER` + `PIN`, but a single `CLIENT_ID` / `CLIENT_SECRET` is still sufficient.

## Implementation

Multi-account support uses pydantic-settings v2's nested delimiter (`env_nested_delimiter="__"`). The account name becomes the dict key automatically — no JSON strings, no hardcoded prefix lists, no separate `name` field needed.

### `.env` structure

```dotenv
CLIENT_ID = User_...
CLIENT_SECRET = ...

# DISPLAY_NAME is optional — a human-readable label stored in MongoDB
ACCOUNTS__DEPOT11__ZUGANGSNUMMER = 62823615
ACCOUNTS__DEPOT11__PIN = 499176
ACCOUNTS__DEPOT11__DISPLAY_NAME = "Megatrend Folger"

ACCOUNTS__DEPOT21__ZUGANGSNUMMER = 45281501
ACCOUNTS__DEPOT21__PIN = 242381
ACCOUNTS__DEPOT21__DISPLAY_NAME = "Quant System Development"
```

Adding another account is just three new lines in `.env`.

### `src/comdirect_api/settings.py`

```python
from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AccountSettings(BaseModel):
    zugangsnummer: SecretStr
    pin: SecretStr
    display_name: str | None = None   # Optional human-readable label


class ClientSettings(BaseSettings):
    client_id: SecretStr
    client_secret: SecretStr
    accounts: dict[str, AccountSettings]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )


settings = ClientSettings()
```

`AccountSettings` uses plain `BaseModel` (not `BaseSettings`) — simpler, no prefix tricks needed. The dict key (e.g. `depot11`) is normalised to lowercase by pydantic-settings and stored as `account_name` in every MongoDB document.

### `functions/sync/settings.py`

`SyncSettings` inherits from `ClientSettings` and picks up `accounts` (including `display_name`) automatically.

```python
class SyncSettings(ClientSettings):
    mongodb_connection_string: SecretStr
    mongodb_database: str = "finance"
    depot_transactions_lookback_days: int = 3650

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )
```

`depot_transactions_lookback_days` controls how far back depot transactions are loaded for deriving
`held_since_date` and `purchase_price_at_entry` in depot snapshots.

### `functions/sync/run.py` — loop over accounts

Accounts are synced sequentially (push TAN approval required for each), then all sync calls run in parallel via `asyncio.gather()`. An optional `--accounts` CLI argument (case-insensitive) limits the run to named accounts only:

```python
for name, account in settings.accounts.items():
    if accounts_filter and name.lower() not in accounts_filter:
        continue
    client = await ComdirectClient.create(
        zugangsnummer=account.zugangsnummer.get_secret_value(),
        pin=account.pin.get_secret_value(),
    )
    service = SyncService(
        client,
        repo,
        account_name=name,
        display_name=account.display_name,
        depot_transactions_lookback=settings.depot_transactions_lookback,
    )
    services.append(service)

results = await asyncio.gather(*[s.run_full_sync() for s in services])
```

### Rate limit handling

Comdirect throttles brokerage endpoints under parallel load. `sync_depot_positions` and `sync_depot_transactions` in `sync_service.py` retry on HTTP 429 up to 3 times with exponential backoff (2s → 4s → 8s).

### GitHub Actions secrets

Set one group of secrets per account under **Settings → Secrets and variables → Actions**:

```.env
ACCOUNTS__DEPOT11__ZUGANGSNUMMER
ACCOUNTS__DEPOT11__PIN
ACCOUNTS__DEPOT11__DISPLAY_NAME   ← optional but recommended
DEPOT_TRANSACTIONS_LOOKBACK_DAYS  ← optional (default: 3650)
```

Repeat the pattern for each additional account. The `workflow_dispatch` trigger exposes an optional `accounts` input field to sync specific accounts (e.g. `DEPOT11,DEPOT22`).

## Notes

- Each account triggers a separate push TAN approval on the Comdirect mobile app.
- `display_name` is stored in every document in `account_balances`, `depot_snapshots`, and `transactions` collections, making it easy to filter/display data per account in dashboards.
- Set `DEPOT_TRANSACTIONS_LOOKBACK_DAYS` (default: `3650`) to tune how reliably entry date/entry price can be derived for long-held positions.
- Idempotent transaction inserts skip documents with the same `transaction_id` — if `display_name` is added later, run a one-off backfill using `update_many({"account_name": ..., "display_name": None}, {"$set": {"display_name": ...}})`.
