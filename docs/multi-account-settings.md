# Multi-Account Settings Design

## Background

The Comdirect API uses `CLIENT_ID` / `CLIENT_SECRET` as OAuth **application** credentials (registered once in the developer portal). `ZUGANGSNUMMER` + `PIN` are the **customer** login credentials.

- If all depots belong to the **same Comdirect login**, one set of credentials is enough — `get_account_depots()` returns all depots automatically.
- If depots belong to **different Comdirect accounts** (different logins), each account needs its own `ZUGANGSNUMMER` + `PIN`, but a single `CLIENT_ID` / `CLIENT_SECRET` is still sufficient.

## Planned Implementation

### Approach: `env_nested_delimiter="__"` (pydantic-settings v2)

The cleanest solution for multiple accounts uses pydantic-settings v2's nested delimiter support. The account name becomes the dict key automatically — no JSON strings, no hardcoded prefix lists, no separate `name` field needed.

### `.env` structure

```dotenv
CLIENT_ID = User_...
CLIENT_SECRET = ...

ACCOUNTS__FAMILIE__ZUGANGSNUMMER = 62823615
ACCOUNTS__FAMILIE__PIN = 499176

ACCOUNTS__FIRMA__ZUGANGSNUMMER = 45281501
ACCOUNTS__FIRMA__PIN = 242381
```

Adding a fifth account is just two new lines in `.env`.

### `src/comdirect_api/settings.py`

```python
from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AccountSettings(BaseModel):
    zugangsnummer: SecretStr
    pin: SecretStr


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

`AccountSettings` uses plain `BaseModel` (not `BaseSettings`) — simpler, no prefix tricks needed.

### `functions/sync/settings.py`

`SyncSettings` inherits from `ClientSettings` and picks up `accounts` automatically. The single `zugangsnummer` / `pin` fields are removed.

```python
class SyncSettings(ClientSettings):
    mongodb_connection_string: SecretStr
    mongodb_database: str = "finance"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )
```

### `functions/sync/run.py` — loop over accounts

```python
for name, account in settings.accounts.items():
    logger.info("Syncing account: %s", name)
    client = await ComdirectClient.create(
        zugangsnummer=account.zugangsnummer.get_secret_value(),
        pin=account.pin.get_secret_value(),
    )
    service = SyncService(client, repo)
    result = await service.run_full_sync()
    # Each account requires its own push TAN approval on the phone
```

## Notes

- `ComdirectClient.__init__` accepts `zugangsnummer` and `pin` as arguments, so no changes to the client class are required.
- Each account triggers a separate push TAN approval on the Comdirect mobile app.
- The current single-account code in `settings.py` and `run.py` must be replaced — this is a breaking change to the settings model.
- Tests in `tests/conftest.py` that patch `zugangsnummer` / `pin` directly will need updating to the new `accounts` dict structure.
