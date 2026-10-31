# Comdirect API Client - Architecture Documentation

## Overview

This document describes the architecture, design patterns, and development guidelines for the Comdirect API Client. It serves as a reference for understanding the codebase structure and maintaining consistent development practices.

## Project Architecture

### High-Level Structure

```text
comdirect_api/
├── src/
│   └── comdirect_api/          # Main package
│       ├── __init__.py         # Package initialization
│       ├── client.py           # Main API client class
│       ├── main.py             # Example usage script
│       ├── settings.py         # Environment configuration (ClientSettings)
│       ├── utils.py            # Utility functions (timestamp)
│       └── models/             # Pydantic V2 data models
│           ├── __init__.py     # Public API exports
│           ├── base.py         # ComdirectBaseModel + AmountValue
│           ├── accounts.py     # Account & balance models
│           ├── auth.py         # Authentication models (internal)
│           ├── depots.py       # Depot & position models
│           ├── instruments.py  # Instrument data models + Price
│           ├── messages.py     # Documents & messages models
│           ├── orders.py      # Brokerage order and execution models
│           ├── reports.py      # Aggregated balance models
│           └── transactions.py # Transaction models
├── functions/
│   └── sync/                   # Sync package (runs via GitHub Actions)
│       ├── run.py              # GitHub Actions entrypoint (asyncio.run)
│       ├── sync_service.py     # Sync orchestration (testable)
│       ├── mongo_repo.py       # MongoDB Atlas read/write
│       ├── settings.py         # SyncSettings (extends ClientSettings)
│       └── function_app.py     # Legacy Azure Function entry point (unused)
├── tests/                      # Test suite (120 tests, 79% client-package coverage)
│   ├── __init__.py
│   ├── conftest.py             # Shared test fixtures
│   ├── test_auth.py            # Authentication tests
│   ├── test_banking.py         # Banking operations tests
│   ├── test_brokerage.py       # Brokerage operations tests
│   ├── test_client.py          # Client functionality tests
│   ├── test_factory.py         # Factory pattern tests
│   ├── test_messages.py        # Messages API tests
│   ├── test_orders.py          # Brokerage order read/model tests
│   ├── test_reports.py         # Reports tests
│   ├── test_sync_service.py    # Sync function tests
│   ├── test_tan_flow.py        # TAN workflow tests
│   ├── test_tan_polling.py     # TAN polling tests
│   ├── test_utils.py           # Utility function tests
│   └── test_validation_errors.py # Validation tests
├── docs/                       # Documentation
│   ├── ARCHITECTURE.md         # This file
│   ├── multi-account-settings.md # Multi-account configuration and sync behavior
│   ├── swagger.json            # Comdirect API specification
│   ├── comdirect_REST_API_Dokumentation.md
│   └── comdirect_REST_API_Dokumentation.pdf
├── examples/                   # Example scripts
│   └── logging_config.py       # Logging configuration example
├── .env.example                # Environment variable template
├── LICENSE                     # MIT License
├── README.md                   # Project documentation
├── pyproject.toml              # Project configuration & dependencies
└── uv.lock                     # Locked dependency versions
```

### Design Philosophy

1. **Async-First**: All API operations are asynchronous using `httpx` and `async/await`
2. **Type-Safe**: Comprehensive Pydantic V2 models for all API responses
3. **Pythonic**: Snake_case interface with automatic camelCase conversion for API calls
4. **Testable**: High test coverage with mocked HTTP responses
5. **Modular**: Clear separation of concerns with dedicated model files

## Authentication Architecture

### Multi-Step OAuth2 Flow

The Comdirect API requires a complex 5-step authentication sequence that **must** be followed in order:

```text
1. Primary OAuth         → primary_access_token (SESSION_RW scope)
2. Session Status        → session_id + 2FA state check
3. TAN Challenge         → Push TAN approval (2FA)
4. Secondary Token       → banking_access_token (cd_secondary grant)
5. API Operations        → Use banking token for all operations
```

### Token Management

The `ComdirectClient` stores these token values:

| Token Type | Purpose | Scope | Usage |
| ---------- | ------- | ----- | ----- |
| `primary_access_token` | Initial authentication | `SESSION_RW` | Session setup |
| `banking_access_token` | Banking/brokerage access | Account operations | All API calls |
| `refresh_token` | Refreshes the access token | OAuth refresh flow | Token renewal |

### State Flags

- `session_id` - Required for all session operations (extracted from headers)
- `session_tan_active` - Tracks whether a session TAN is active
- `activated_2fa` - Tracks 2FA state to prevent duplicate TAN challenges
- `token_expires_at` - Token expiration timestamp for automatic refresh

### Factory Pattern

The `ComdirectClient.create()` factory method encapsulates the entire authentication flow:

```python
from comdirect_api.settings import settings

account = settings.accounts["depot11"]
client = await ComdirectClient.create(
    zugangsnummer=account.zugangsnummer.get_secret_value(),
    pin=account.pin.get_secret_value(),
)
```

This provides a clean API while handling all authentication complexity internally.

## Data Models Architecture

### Base Model Pattern

All API response models inherit from `ComdirectBaseModel` defined in `models/base.py`:

```python
class ComdirectBaseModel(BaseModel):
    """Base model for all Comdirect API responses with automatic camelCase conversion."""
    
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
```

**Key Features**:

- **Automatic camelCase Conversion**: Python uses `snake_case`, API expects `camelCase`
- **Bi-directional Mapping**: Accepts both snake_case and camelCase in responses
- **Type Safety**: Full Pydantic validation and type checking

### Model Organization

Models are organized by domain in separate files:

| File | Purpose | Key Models |
| ---- | ------- | ---------- |
| `base.py` | Base class, utilities, shared value types | `ComdirectBaseModel`, `AmountValue`, `to_camel()` |
| `accounts.py` | Account and balance data | `AccountBalances`, `AccountBalance`, `Balance` |
| `auth.py` | Authentication responses | `AuthResponse`, `TokenState` (internal) |
| `depots.py` | Depot and position data | `AccountDepots`, `DepotPositions`, `DepotPosition` |
| `instruments.py` | Instrument/security data | `Instruments`, `Instrument`, `StaticData`, `Price` |
| `messages.py` | Documents and messages | `Documents`, `Document`, `DocumentMetadata` |
| `orders.py` | Order data | `Orders`, `Order`, `Execution`, `PercentageValue` |
| `reports.py` | Reports / all-product balances | `AllBalances`, `ProductBalance`, `BalanceAggregation` |
| `transactions.py` | Transaction data | `AccountTransactions`, `DepotTransactions` |

### Public API Models

Only **top-level response models** are exposed in `models/__init__.py`:

```python
__all__ = [
    # Shared value type used in response fields
    "AmountValue",          # monetary / quantity value with unit
    # Main response models returned by client methods
    "AccountBalance",       # from get_account_balance()
    "AccountBalances",      # from get_account_balances()
    "AccountTransactions",  # from get_account_transactions()
    "AccountDepots",        # from get_account_depots()
    "DepotPositions",       # from get_depot_positions()
    "DepotPosition",        # from get_depot_position()
    "DepotTransactions",    # from get_depot_transactions()
    "Instruments",          # from get_instrument()
    "Documents",            # from get_documents()
    "AllBalances",          # from get_all_balances()
    "Orders",               # from get_depot_orders()
    "Order",                # from get_order()
]
```

**Design Principle**: Internal models (e.g., `Account`, `Balance`, `AuthResponse`) are not exposed. Users access nested data via properties of response objects. `AmountValue` is an exception — it is exported because users regularly need to type-hint or inspect monetary and quantity fields.

Example:

```python
balances = await client.get_account_balances()
# Access nested models via properties
for balance in balances.values:
    account_type = balance.account.account_type  # Nested access
    amount = balance.balance.value               # Internal model
```

### Financial Data Types

- **Decimal for Money**: All financial amounts use `Decimal` (never `float`)
- **`AmountValue` model**: Monetary and quantity fields use `AmountValue` (defined in `base.py`) instead of raw `dict`. It has two attributes:
  - `value: Decimal | None` — the numeric amount
  - `unit: str | None` — ISO 4217 currency code (e.g. `EUR`) or a Comdirect quantity code (`XXX`, `XXC`, `XXP`, `XXU`)
- **`Price` model**: Defined in `instruments.py` and shared with `depots.py`. Wraps an `AmountValue` plus a `price_datetime` timestamp.
- **ISO4217 Currency Codes**: Standard currency codes used in `AmountValue.unit` for monetary fields; quantity fields use Comdirect-specific non-currency codes.
- **Proper Precision**: Maintains exact decimal precision for financial calculations.

## HTTP Request Pattern

### Standard Headers

All API requests use a consistent header structure via `_request_headers()`:

```python
{
    "Authorization": f"Bearer {token}",
    "x-http-request-info": json.dumps({
        "clientRequestId": {
            "sessionId": self.session_id,
            "requestId": timestamp()
        }
    }),
    "Content-Type": "application/json"
}
```

### Request ID Generation

Each request gets a unique ID using `timestamp()` from `utils.py`:

```python
def timestamp() -> str:
    """Generate timestamp string for request IDs."""
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")[:-3]
```

### Token Refresh Logic

Before each banking operation, the client checks token expiration:

```python
if self.is_token_expired():
    await self.refresh_access_token()
```

This ensures seamless operation without manual token management.

## Development Guidelines

### Code Style

| Aspect | Standard | Tool |
| ------ | -------- | ---- |
| Code Formatting | PEP 8 | `ruff` |
| Import Sorting | isort-compatible | `ruff` |
| Type Hints | Mandatory for public methods | `pydantic` |
| Docstrings | Google style | Manual |
| Line Length | 100 characters | `ruff` |

### Naming Conventions

- **Classes**: `PascalCase` (e.g., `ComdirectClient`)
- **Functions/Methods**: `snake_case` (e.g., `get_account_balances`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `BASE_URL`)
- **Private Methods**: `_leading_underscore` (e.g., `_request_headers`)
- **Pydantic Fields**: `snake_case` in Python, auto-converted to `camelCase` for API

### Testing Standards

#### Test Organization

- One test file per module (e.g., `test_banking.py` for banking operations)
- Use descriptive test names: `test_get_account_balances_success()`
- Group related tests in classes when beneficial

#### Test Structure (AAA Pattern)

```python
async def test_operation_scenario():
    # Arrange - Set up test data
    mock_response = {...}
    
    # Act - Execute operation
    result = await client.operation()
    
    # Assert - Verify results
    assert result.field == expected_value
```

#### Mocking Pattern

Client methods create their own `httpx.AsyncClient`, so tests patch that class and
configure its async context manager. See `tests/test_banking.py` for a complete example:

```python
with patch("httpx.AsyncClient") as mock_client_class:
    mock_client_class.return_value.__aenter__.return_value = mock_http_client
    result = await client.get_account_balances()
```

#### Coverage Standards

- **Coverage target**: 80% for the client package; the current package test command reports 79%
- **Critical Paths**: Prioritize comprehensive authentication-flow coverage
- **Test Types**: Unit tests only (no integration tests with real API)

### Error Handling

#### Error Reporting

Client requests call `raise_for_status()`, so HTTP failures propagate as `httpx.HTTPStatusError`.
Authentication code logs diagnostics through the module logger; sync retry warnings are also
logged rather than printed.

#### Exception Strategy

- **Preconditions**: Missing credentials or access tokens raise `ValueError`; HTTP and network failures propagate from `httpx`
- **Token Expiration**: Automatic refresh before operations
- **Rate Limiting**: The sync retries HTTP 429 responses for depot positions and transactions up to three times (2, 4, and 8 second waits); the client has no general retry policy

### Commit Conventions

Follow Conventional Commits format:

```text
<type>(<scope>): <description>

[optional body]
```

**Types**:

- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructuring
- `docs`: Documentation changes
- `test`: Test additions/changes
- `chore`: Maintenance tasks

**Examples**:

```text
feat(messages): implement Messages API endpoints
fix(auth): correct token refresh timing
refactor(models): extract ComdirectBaseModel to base.py
docs: update README with Messages API
test(banking): add transaction filter tests
```

### Environment Configuration

#### Required Environment Variables

Create `.env` file in project root:

```env
# Comdirect OAuth application credentials
CLIENT_ID = your_client_id
CLIENT_SECRET = your_client_secret

# Account credentials — one block per Comdirect login
# DISPLAY_NAME is an optional human-readable label stored in MongoDB
ACCOUNTS__DEPOT11__ZUGANGSNUMMER = your_zugangsnummer
ACCOUNTS__DEPOT11__PIN = your_pin
ACCOUNTS__DEPOT11__DISPLAY_NAME = "My First Depot"

# ACCOUNTS__DEPOT21__ZUGANGSNUMMER = other_zugangsnummer
# ACCOUNTS__DEPOT21__PIN = other_pin
# ACCOUNTS__DEPOT21__DISPLAY_NAME = "Second Login Depot"

# MongoDB Atlas (sync function only)
MONGODB_CONNECTION_STRING = "mongodb+srv://..."
MONGODB_DATABASE = finance
```

#### Settings Management

Settings are managed via Pydantic Settings in a two-level hierarchy using `env_nested_delimiter="__"`:

```python
# src/comdirect_api/settings.py
class AccountSettings(BaseModel):
    zugangsnummer: SecretStr
    pin: SecretStr
    display_name: str | None = None  # Optional human-readable label

class ClientSettings(BaseSettings):
    client_id: SecretStr
    client_secret: SecretStr
    accounts: dict[str, AccountSettings]   # key = account name (e.g. "depot11")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )


# functions/sync/settings.py
class SyncSettings(ClientSettings):
    mongodb_connection_string: SecretStr
    mongodb_database: str = "finance"
    depot_transactions_lookback_days: int = 365
```

The account key (e.g. `depot11`) becomes the `account_name` stored in every MongoDB document. Each account requires its own Comdirect login credentials; a single `CLIENT_ID`/`CLIENT_SECRET` covers all accounts.

**Never commit** `.env` files or credentials to version control.

## API Coverage Strategy

### Current Coverage (14 of 30 Swagger operations — 47%)

The client currently implements 14 Comdirect data operations: 3 banking, 6 brokerage, 1
instrument, 3 messages, and 1 reports operation. The endpoint list with full paths is maintained
in the [README API coverage section](../README.md#api-coverage). `revoke_access_token()` is an
additional OAuth operation and is not included in that count.

### Current Scope

Data retrieval is implemented; order placement, order changes/cancellation, and the Livetrading
quote flow are not. The stated future goal is automated Livetrading BUY/SELL support for warrants.
Order placement and its safety controls remain unimplemented; this is not a current client capability.

### Implementation Pattern for New Endpoints

When adding new API endpoints:

1. **Create Pydantic Models** in appropriate `models/` file
2. **Add Client Method** to `ComdirectClient` class
3. **Use Standard Pattern**:

   ```python
   async def get_resource(self, resource_id: str) -> ResourceModel:
       """Brief description of operation."""
       if not self.banking_access_token:
           raise ValueError("No banking access token available.")
       if self.is_token_expired():
           await self.refresh_access_token()
       
       headers = self._request_headers(self.banking_access_token)
       async with httpx.AsyncClient() as client:
           response = await client.get(
               f"{self.BASE_URL}/resource/{resource_id}",
               headers=headers,
           )
       response.raise_for_status()
       return ResourceModel(**response.json())
   ```

4. **Add Tests** in corresponding `tests/test_*.py` file
5. **Update Public API** in `models/__init__.py` if exposing new top-level model
6. **Document** in README.md API coverage section

## Sync Function Architecture

The `functions/sync/` package syncs Comdirect data to MongoDB Atlas. It is triggered manually via a **GitHub Actions `workflow_dispatch`** workflow — fully automated/unattended scheduling is not supported because the Comdirect API requires an interactive push TAN approval on every authentication.

### Deployment

The sync runs on GitHub Actions (`.github/workflows/sync.yml`). Trigger it by clicking **"Run workflow"** in the Actions tab on GitHub. The optional **`accounts` input** accepts a comma-separated list (e.g. `DEPOT11,DEPOT22`, case-insensitive) to sync only specific accounts; leave blank to sync all.

The runner:

1. Checks out the repo and installs Python 3.12 + `uv`
2. Installs dependencies: `uv sync --extra sync`
3. Runs `uv run python -m functions.sync.run --accounts "${{ inputs.accounts }}"`
4. Secrets are injected as environment variables

Approve each push TAN on your phone within ~60 seconds of triggering the workflow (one TAN per account, sequential).

**Required GitHub Secrets** (Settings → Secrets and variables → Actions):

| Secret | Description |
| ------ | ----------- |
| `CLIENT_ID` | OAuth application client ID |
| `CLIENT_SECRET` | OAuth application client secret |
| `ACCOUNTS__DEPOT11__ZUGANGSNUMMER` | Account login number |
| `ACCOUNTS__DEPOT11__PIN` | Account PIN |
| `ACCOUNTS__DEPOT11__DISPLAY_NAME` | Human-readable label (optional, stored in MongoDB) |
| Additional account prefixes | `DEPOT12`, `DEPOT21`, and `DEPOT22` are also mapped by the current workflow |
| `MONGODB_CONNECTION_STRING` | Atlas connection string |

The workflow maps only `DEPOT11`, `DEPOT12`, `DEPOT21`, and `DEPOT22`. Add environment entries
for any additional account before using it in Actions; local configuration can include more.

The workflow does not currently pass `DEPOT_TRANSACTIONS_LOOKBACK_DAYS` to the sync process, so
GitHub Actions uses the default of 365 days. Local runs can set it in `.env` or override it with
`--lookback-days`.

### Component Overview

| File | Responsibility |
| ---- | -------------- |
| `run.py` | GitHub Actions entrypoint; `asyncio.run(main())`; creates `ComdirectClient` + `MongoRepo`, calls `SyncService.run_full_sync()`, exits 1 on failure |
| `sync_service.py` | Orchestration logic; fully testable; depends on `ComdirectClient` and `MongoRepo` abstractions |
| `mongo_repo.py` | All MongoDB Atlas reads and writes; no Comdirect knowledge |
| `settings.py` | `SyncSettings(ClientSettings)` — adds `mongodb_connection_string`, `mongodb_database`, and `depot_transactions_lookback_days` |
| `function_app.py` | Legacy Azure Function entry point — kept for reference, not actively used |

### Module-Level Singleton (Connection Pool)

```python
# function_app.py — created once per cold start, reused across warm invocations
_repo = MongoRepo(
    connection_string=settings.mongodb_connection_string.get_secret_value(),
    database=settings.mongodb_database,
)
```

`PyMongoClient` manages an internal connection pool; creating it per request would be wasteful. The singleton follows MongoDB's own guidance for serverless runtimes.

### MongoDB Collections

#### `account_balances` — Insert-only time series

```json
{
  "account_id": "DE89370400440532013000",
  "account_name": "depot11",
  "display_name": "Megatrend Folger",
  "iban": "DE89370400440532013000",
  "account_type": "Girokonto",
  "balance": { "value": "1234.56", "unit": "EUR" },
  "recorded_at": "<UTC datetime — immutable, when value first appeared>",
  "last_synced_at": "<UTC datetime — updated every sync run>"
}
```

- `recorded_at` is **immutable** — it marks the first time this exact balance was observed.
- `last_synced_at` acts as a **heartbeat** — updated on every sync, even when balance is unchanged.
- Full history is retained for charting.

#### `depot_snapshots` — Insert-only; one document = entire depot state

```json
{
  "depot_id": "67890",
  "account_name": "depot11",
  "display_name": "Megatrend Folger",
  "positions": [
    {
      "position_id": "12345",
      "wkn": "A1C34X",
      "isin": "DE000A1C34X7",
      "instrument_name": "Acme Corp",
      "quantity": { "value": "50", "unit": "XXC" },
      "current_price": { "value": "86.42", "unit": "EUR", "price_datetime": "2026-03-15T21:58:00" },
      "current_value": { "value": "4321.00", "unit": "EUR" },
    "average_purchase_price": { "value": "80.00", "unit": "EUR" },
    "held_since_date": "2026-03-10",
    "purchase_price_at_entry": { "value": "78.50", "unit": "EUR" }
    }
  ],
  "recorded_at": "<UTC datetime — immutable, when this composition first appeared>",
  "last_synced_at": "<UTC datetime — updated every sync run>"
}
```

- One document captures **all positions** of the depot at a point in time.
- A **new snapshot is inserted** when the composition changes: any quantity change, new position, or a position fully sold/closed.
- A later sync can also insert a new snapshot when `held_since_date` / `purchase_price_at_entry` becomes available from newly visible transaction history, even if quantity is unchanged.
- If a later sync cannot derive entry metadata (for example due to lookback/window gaps), existing `held_since_date` / `purchase_price_at_entry` are preserved from the latest snapshot when quantity is unchanged.
- When neither composition nor entry metadata changed, only `last_synced_at` is touched (heartbeat).
- Latest depot state = `find_one({"depot_id": ...}, sort=[("recorded_at", -1)])`.
- `current_price` is the market price **per unit** with its timestamp; `current_value` is the total position value (qty × price).
- `average_purchase_price` is persisted from Comdirect `DepotPosition.purchase_price` as the primary average cost basis field.
- `purchase_price_at_entry` is derived from the first BUY/TRANSFER_IN of the **current holding period** (after the position last returned to zero or below).
- `held_since_date` is derived from transaction history and may be `null` if the configured lookback does not reach the current entry transaction; however, an already stored value is retained when quantity is unchanged.

#### `transactions` — Insert-only, idempotent

```json
{
  "transaction_id": "TXN-98765",
  "depot_id": "67890",
  "account_name": "depot11",
  "display_name": "Megatrend Folger",
  "wkn": "A1C34X",
  "transaction_type": "BUY",
  "quantity": "10",
  "price": { "value": "82.00", "unit": "EUR" },
  "booking_date": "<midnight UTC datetime>",
  "recorded_at": "<UTC datetime>"
}
```

- Transactions are never modified after insertion.
- `transaction_exists(transaction_id)` prevents duplicate inserts.
- `booking_date` is stored as a native UTC `datetime` (midnight) for MongoDB date indexing.
- During full sync, depot transactions are fetched once per depot and reused for both snapshot enrichment and transaction persistence.

### Helper Functions (`mongo_repo.py`)

| Helper | Purpose |
| ------ | ------- |
| `_now()` | `datetime.now(UTC)` — Python 3.11+ `UTC` constant |
| `_decimal_to_str(v)` | Converts `Decimal \| None` → `str \| None` for MongoDB storage |
| `_date_to_datetime(d)` | Converts `date \| None` → midnight UTC `datetime \| None` for MongoDB |

### Sync Rules Summary

| Collection | On new data | When unchanged |
| ---------- | ----------- | -------------- |
| `account_balances` | Insert new snapshot | Touch `last_synced_at` only |
| `depot_snapshots` | Insert new full-depot snapshot | Touch `last_synced_at` only |
| `transactions` | Insert | Skip (idempotent) |

### Recent Changes

- **2026-07-30 — Depot metadata preservation fix**: Depot sync no longer overwrites existing `held_since_date` / `purchase_price_at_entry` with null when the latest transaction window cannot derive entry metadata and quantity is unchanged.

### Installing Sync Dependencies

```bash
uv sync --extra sync   # adds azure-functions, pymongo, dnspython
```

### Running Sync Tests

```bash
uv run pytest tests/test_sync_service.py -v
```

Tests use `unittest.mock.AsyncMock` for the Comdirect client and `MagicMock` for `MongoRepo` — no real network or database calls.

---

## Critical Implementation Details

### TAN Challenge Workflow

The `create_validate_session_tan()` method orchestrates a 3-part flow:

1. **Initiate Challenge**: POST to `/sessions/{id}/validate`
2. **Poll Authentication**: Extract URL from `x-once-authentication-info` header
3. **Activate Session**: POST challenge ID to complete TAN

**Key Detail**: Authentication URL is in response **headers**, not JSON body.

### Session Management

- Sessions are time-limited (~30 minutes)
- `session_id` extracted from `x-http-request-info` header in session status response
- Required in all subsequent requests
- Automatic refresh on expiration

### Pagination Pattern

List endpoints support pagination via `Paging` model:

```python
class Paging(ComdirectBaseModel):
    index: int          # Current page index
    matches: int        # Total matching records
```

Clients can request specific pages using query parameters or limit result count.

### Depot transaction paging

`GET /brokerage/v3/depots/{depotId}/transactions` is documented without paging parameters, but it
accepts `paging-first` and `paging-count` and defaults to **20 records per page**. Unknown query
parameters are ignored rather than rejected, so the truncation is silent — only `paging.matches`
reveals it. `get_depot_transactions()` exposes both parameters and `SyncService` pages through the
full set using `PAGE_SIZE = 500` (values of 1000+ return HTTP 422 `ERROR_VALIDATION_PAGING_INVALID`).

`min-bookingDate` accepts `YYYY-MM-DD` or a short negative offset such as `-180d`; long offsets like
`-3650d` are rejected with HTTP 422, so the sync always sends an explicit date.

## Integration Points

### External Dependencies

- **Comdirect REST API** - OAuth2-protected financial API
- **Push TAN App** - Mobile app for 2FA approval
- **Environment Variables** - Credential management via `.env`

### API Constraints

- **Rate Limiting**: Comdirect enforces a rate limit on brokerage endpoints. The sync function retries 429 responses up to 3 times with exponential backoff (2s, 4s, 8s) for both `get_depot_positions` and `get_depot_transactions`.
- **Depot transaction history**: Comdirect serves only about the last six months of depot transactions, regardless of `min-bookingDate`. Positions entered before that horizon cannot have `held_since_date` / `purchase_price_at_entry` derived, and no lookback setting changes this.
- **T+1 booking**: Depot transactions are booked with `bookingDate = businessDate + 1`, and `settlementDate` is not populated for warrants. A position therefore appears in the depot one day before its transaction becomes visible, so entry metadata is filled in by the following sync.
- **Session Duration**: ~30 minutes before token refresh required
- **TAN Approval**: Requires physical mobile device access
- **Scope Permissions**: Different tokens for session vs banking operations

## Development Workflow

### Daily Development

```bash
# Start development
cd comdirect_api
uv sync                              # Sync dependencies

# Make changes
# ... edit code ...

# Run tests
uv run pytest tests/ -v              # Verbose test run
uv run pytest tests/ -q              # Quick test run
uv run pytest --cov=src/comdirect_api tests/  # With coverage

# Check code quality
uv run ruff check .                  # Lint check
uv run ruff check . --fix            # Auto-fix issues

# Commit changes
git add .
git commit -m "feat(scope): description"
git push
```

### Adding New Features

1. **Plan**: Review `docs/swagger.json` for API endpoint details
2. **Model**: Create Pydantic models in `models/`
3. **Implement**: Add method to `client.py`
4. **Test**: Create comprehensive tests in `tests/`
5. **Document**: Update README.md API coverage
6. **Commit**: Use conventional commit format

### Testing Best Practices

- **Run tests frequently** during development
- **Aim for 100% coverage** of new code
- **Mock all HTTP requests** - never hit real API in tests
- **Test error paths** including token expiration, HTTP errors
- **Use fixtures** from `conftest.py` for common test data

## Security Considerations

### Credential Management

- ✅ **Use `.env` files** for local development
- ✅ **Never commit credentials** to version control
- ✅ **Use environment variables** in production
- ✅ **Rotate credentials** periodically

### API Access

- ✅ **Current scope is read-only** - order placement is not implemented
- ✅ **Own accounts only** - never access others' data
- ✅ **Rate limit awareness** - conservative API usage
- ✅ **Follow ToS** - comply with Comdirect terms of service

### Token Security

- Tokens stored in memory only (not persisted)
- Automatic token refresh prevents exposure of expired tokens
- Factory pattern limits token scope exposure

## Troubleshooting

### Common Issues

**Issue**: "Session TAN activation failed"

- **Cause**: TAN not approved on mobile device
- **Solution**: Check mobile app, approve push notification

**Issue**: "Token expired" errors

- **Cause**: Token refresh failed or session timeout
- **Solution**: Re-authenticate using `ComdirectClient.create()`

**Issue**: "HTTP 401 Unauthorized"

- **Cause**: Invalid credentials or session expired
- **Solution**: Verify `.env` credentials, check session state

**Issue**: Import errors for models

- **Cause**: Importing internal models not in `__all__`
- **Solution**: Import top-level response models only

## Resources

- **Comdirect API Documentation**: <https://www.comdirect.de>
- **API Specification**: `docs/swagger.json`
- **Original Implementation**: <https://github.com/keisentraut/python-comdirect-api>
- **Pydantic Documentation**: <https://docs.pydantic.dev/>
- **httpx Documentation**: <https://www.python-httpx.org/>

## Changelog

### August 2026

- **Depot transaction pagination (2026-08-30)**: `get_depot_transactions()` gained `paging_first` / `paging_count`, and `SyncService` now pages through the full result set (`PAGE_SIZE = 500`). Previously every sync silently received only the 20 most recent transactions, so `held_since_date` and `purchase_price_at_entry` could not be derived for positions bought more than a few trades earlier.
- **Sync diagnostics**: `--debug` and `--lookback-days` flags on `functions.sync.run`; depot transaction fetches log the returned count, `paging` object and booking-date range, plus one summary line per transaction. Raw JSON payloads are logged at DEBUG level in the client, which is the only way to see fields the Pydantic models drop.
- **Documented API constraints**: ~6 month server-side depot transaction history, T+1 booking dates, unpopulated `settlementDate` for warrants, and rejection of long `min-bookingDate` offsets. See *API Constraints*.
- **120 tests passing** across the full suite.

### July 2026

- **Breaking schema change (2026-07-20)**: Removed legacy `depot_snapshots.positions[]` fields `purchase_price` and `buy_price_at_entry`. Canonical fields are now `average_purchase_price` and `purchase_price_at_entry`.
- **Entry/average purchase price fields in snapshots**: `depot_snapshots.positions[]` includes `average_purchase_price`, `purchase_price_at_entry`, and `held_since_date` as canonical fields.
- **Current-holding entry logic**: `purchase_price_at_entry` is derived from the first BUY/TRANSFER_IN of the current holding period (after last full close), not simply the oldest historical BUY.
- **Configurable depot transaction history window**: Added `DEPOT_TRANSACTIONS_LOOKBACK_DAYS` (default `365`) in `SyncSettings` to control how far back transactions are loaded for entry-date/entry-price derivation; value is converted to an earliest booking date (`YYYY-MM-DD`) for API requests.
- **Transaction fetch optimization**: Full sync now fetches depot transactions once per depot and reuses the payload for both position enrichment and transaction inserts.
- **117 tests passing** across the full suite.

### May 2026

- **Multi-account `display_name` support**: `AccountSettings` now has an optional `display_name: str | None` field. Set via `ACCOUNTS__<NAME>__DISPLAY_NAME` in `.env` or GitHub Secrets. Stored in every MongoDB document (`account_balances`, `depot_snapshots`, `transactions`) alongside `account_name`.
- **`--accounts` CLI filter** (case-insensitive): `python -m functions.sync.run --accounts DEPOT11,DEPOT22` syncs only the specified accounts. The GitHub Actions `workflow_dispatch` exposes this as an optional input field.
- **429 retry with exponential backoff**: Parallel sync of multiple accounts was hitting Comdirect's rate limit. `sync_depot_positions` and `sync_depot_transactions` now retry on HTTP 429 up to 3 times (waits: 2s, 4s, 8s).
- **`DISPLAY_NAME` secrets added to workflow**: `.github/workflows/sync.yml` now injects `ACCOUNTS__<NAME>__DISPLAY_NAME` secrets for all 4 accounts.

### March 2026

- **GitHub Actions deployment** (`workflow_dispatch`): Sync is now triggered manually from the GitHub Actions UI — no Azure infrastructure required. Secrets are injected as environment variables. The runner authenticates, waits for push TAN approval, syncs all data, and exits.
- **`functions/sync/run.py`**: Standalone async entrypoint (`python -m functions.sync.run`) used by GitHub Actions. Creates `MongoRepo` and `ComdirectClient`, calls `SyncService.run_full_sync()`, prints JSON result, exits 1 on failure.
- **Bug fix — `touch` methods**: `touch_balance_last_synced()` and `touch_depot_last_synced()` in `mongo_repo.py` rewritten to use `find_one(..., sort=...)` + `update_one({"_id": ...})` instead of passing `sort` to `update_one` directly (the `sort` parameter on `update_one` rejects list-of-tuples on MongoDB Atlas).
- **115 tests** passing (all sync + client tests green).
- **Sync Function**: `functions/sync/` package writing Comdirect data to MongoDB Atlas
  - `MongoRepo` with insert-only balance snapshots, insert-only depot snapshots, idempotent transaction inserts
  - `SyncService` orchestration (testable independently of Azure runtime)
  - Module-level `MongoRepo` singleton for connection pool reuse across warm invocations
  - `last_synced_at` heartbeat timestamp alongside immutable `recorded_at`
  - `_date_to_datetime()` helper for native MongoDB date storage
- **`depot_snapshots` collection**: Replaced per-position upsert design with insert-only whole-depot snapshots. Detects composition changes via `{position_id → quantity}` fingerprint comparison. Handles new positions, quantity changes, and sold/closed positions correctly.
- **`current_price` in snapshots**: Each position in a snapshot stores `current_price` (per-unit market price + timestamp) alongside `current_value` (total position value).
- **`AmountValue` model**: Replaced all `dict | None # AmountValue` placeholders with `AmountValue(ComdirectBaseModel)` carrying `value: Decimal | None` and `unit: str | None`. Exported from `models/__init__.py`
- **`Price` de-duplicated**: Removed duplicate `Price` class from `depots.py`; single definition lives in `instruments.py`
- **`ClientSettings`**: Renamed `Settings` → `ClientSettings` in `src/comdirect_api/settings.py` to support the settings inheritance hierarchy. Added `extra="ignore"` to tolerate MongoDB fields in shared `.env`.
- **`SyncSettings`**: New `functions/sync/settings.py` extending `ClientSettings` with MongoDB credentials
- **101 tests**: 85 client tests + 16 sync function tests (all passing)

### Previous Version (February 2026)

- Messages API implementation (3 GET endpoints)
- Base model architecture with automatic camelCase conversion
- 85 tests with 83% coverage
- Public API refinement (`AmountValue` + 10 top-level response models)
- Comprehensive error handling and token management

### Next Steps

- ✅ ~~Deploy sync function~~ — deployed via GitHub Actions `workflow_dispatch` (March 2026)
- Implement price history job (FinHub `/v1/history/{wkn}` → MongoDB time series)
- Add rate limiting support

---

**Last Updated**: October 31, 2026
