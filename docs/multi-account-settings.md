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
ACCOUNTS__DEPOT11__ZUGANGSNUMMER = your_depot11_zugangsnummer
ACCOUNTS__DEPOT11__PIN = your_depot11_pin
ACCOUNTS__DEPOT11__DISPLAY_NAME = "Megatrend Folger"

ACCOUNTS__DEPOT21__ZUGANGSNUMMER = your_depot21_zugangsnummer
ACCOUNTS__DEPOT21__PIN = your_depot21_pin
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
    depot_transactions_lookback_days: int = 365

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
```

The GitHub workflow currently maps only `DEPOT11`, `DEPOT12`, `DEPOT21`, and `DEPOT22`. Add an account's environment variables to the workflow before using another account in Actions; local runs can use any number of configured accounts. The `workflow_dispatch` trigger exposes an optional `accounts` input field to sync specific mapped accounts (e.g. `DEPOT11,DEPOT22`).

The workflow does not currently pass `DEPOT_TRANSACTIONS_LOOKBACK_DAYS` to the sync process, so
GitHub Actions uses the default of 365 days. For local runs, set it in `.env` or use
`--lookback-days`.

## Booked Balance and Available Cash

Each configured login syncs both amounts for every bank account returned by
`get_account_balances()`, including its Verrechnungskonto. No additional credentials,
settings, or API request are needed.

The `account_balances` collection stores:

```json
{
    "balance": { "value": "1000.00", "unit": "EUR" },
    "available_cash_amount": { "value": "1500.00", "unit": "EUR" }
}
```

`balance` is the booked balance. `available_cash_amount` comes from API
`availableCashAmount` and represents the available spending limit, including any
credit limit and adjustments for unbooked commitments. It is not necessarily owned
cash. Trades may affect availability before the booked balance changes; exact
intraday API timing has not yet been verified against a live response.

A booked-balance value change or available-cash value/currency change inserts a
snapshot. Otherwise only `last_synced_at` is updated. An older latest snapshot
without `available_cash_amount` gets a new snapshot at the next successful sync;
historical documents are not backfilled.

Downstream applications should select the latest snapshot by `account_id` and
`recorded_at` descending, parse monetary strings as decimals, and use
`last_synced_at` to assess freshness. Missing availability in older documents means
unknown, not zero. Sync runs are snapshots, not a continuously updated cash feed.
See [collection details](ARCHITECTURE.md#mongodb-collections).

## Notes

- Each account triggers a separate push TAN approval on the Comdirect mobile app.
- `display_name` is stored in every document in `account_balances`, `depot_snapshots`, and `transactions` collections, making it easy to filter/display data per account in dashboards.
- For local runs, set `DEPOT_TRANSACTIONS_LOOKBACK_DAYS` (default: `365`) to tune how reliably entry date/entry price can be derived for long-held positions.
- Idempotent transaction inserts skip documents with the same `transaction_id` — if `display_name` is added later, run a one-off backfill using `update_many({"account_name": ..., "display_name": None}, {"$set": {"display_name": ...}})`.
