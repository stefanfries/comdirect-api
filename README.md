# Comdirect API Client

![License](https://img.shields.io/github/license/stefanfries/comdirect-api)
![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)
![Code Style](https://img.shields.io/badge/code%20style-ruff-black)
![Type Checked](https://img.shields.io/badge/type%20checked-pydantic-green)
![Tests](https://img.shields.io/badge/tests-120%20passed-success)
![Coverage](https://img.shields.io/badge/coverage-79%25-green)

A modern, fully asynchronous Python client for the [Comdirect REST API](https://www.comdirect.de). Access your banking and brokerage accounts programmatically with full OAuth2 authentication and 2FA support.

> **Acknowledgment**: This project is inspired by [Klaus Eisentraut's python-comdirect-api](https://github.com/keisentraut/python-comdirect-api). This implementation modernizes the approach with current best practices and libraries.

## ✨ Features

- 🔐 **Full OAuth2 Flow** - Complete authentication with 2FA (push TAN support)
- ⚡ **Fully Async** - Built on `httpx` for high-performance async operations
- 📊 **Read-focused API Coverage** - Banking, brokerage, depot positions, transactions, instruments, documents
- 🔒 **Type-Safe** - Pydantic V2 models for all API responses with automatic camelCase conversion
- 🐍 **Pythonic** - Clean snake_case interface with automatic camelCase for API calls
- 🧪 **Well Tested** - 120 tests with 79% client-package coverage
- 📦 **Modern Stack** - Python 3.11+, httpx, Pydantic V2, async/await
- ☁️ **GitHub Actions Sync** - Manual `workflow_dispatch` workflow that syncs Comdirect data to MongoDB Atlas on demand (unattended scheduling not possible due to interactive push TAN requirement)

## 🚀 Tech Stack

| Component | Technology |
| --------- | --------- |
| HTTP Client | `httpx` (async) |
| Data Validation | `pydantic` V2 |
| Configuration | `pydantic-settings` |
| Package Manager | `uv` |
| Testing | `pytest` + `pytest-asyncio` |
| Code Quality | `ruff` |
| Sync Storage | MongoDB Atlas via `pymongo` |
| Sync Runtime | GitHub Actions (`workflow_dispatch`) |

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/stefanfries/comdirect-api.git
cd comdirect-api

# Install core dependencies with uv (recommended)
uv sync

# Install sync dependencies (PyMongo and the legacy Azure Function entry point)
uv sync --extra sync
```

## 🔧 Configuration

Create a `.env` file in the project root (copy from `.env.example`):

```env
# Comdirect OAuth application credentials
CLIENT_ID = your_client_id
CLIENT_SECRET = your_client_secret

# Account credentials — one block per Comdirect login
# DISPLAY_NAME is an optional human-readable label stored in MongoDB
ACCOUNTS__DEPOT11__ZUGANGSNUMMER = your_zugangsnummer
ACCOUNTS__DEPOT11__PIN = your_pin
ACCOUNTS__DEPOT11__DISPLAY_NAME = "My Depot"

# Add more accounts as needed:
# ACCOUNTS__DEPOT21__ZUGANGSNUMMER = other_zugangsnummer
# ACCOUNTS__DEPOT21__PIN = other_pin
# ACCOUNTS__DEPOT21__DISPLAY_NAME = "Second Login Depot"

# MongoDB Atlas (required only for the sync function)
MONGODB_CONNECTION_STRING = "mongodb+srv://..."
MONGODB_DATABASE = finance

# Optional: how far back depot transactions are loaded for
# held_since_date / purchase_price_at_entry derivation
DEPOT_TRANSACTIONS_LOOKBACK_DAYS = 365
```

> **Important**: Never commit your `.env` file to version control!

The account key (e.g. `DEPOT11`) becomes the lowercase `account_name` (e.g. `depot11`) stored in MongoDB. You can define as many accounts as needed — each requires its own Comdirect login credentials. A single `CLIENT_ID` / `CLIENT_SECRET` covers all accounts.

## 💻 Usage

### Simple Example (Recommended)

```python
import asyncio
from comdirect_api.client import ComdirectClient
from comdirect_api.settings import settings

async def main():
    # The factory handles authentication; account login credentials are explicit.
    # 1. OAuth authentication
    # 2. Session setup
    # 3. TAN challenge (approve on your phone)
    # 4. Banking/brokerage token
    
    account = settings.accounts["depot11"]
    client = await ComdirectClient.create(
        zugangsnummer=account.zugangsnummer.get_secret_value(),
        pin=account.pin.get_secret_value(),
    )
    
    # Ready to use!
    balances = await client.get_account_balances()
    for balance in balances.values:
        print(f"Account: {balance.account_display_id}")
        print(f"Balance: {balance.balance.value} {balance.balance.unit}")
    
    # Get depot positions
    depots = await client.get_account_depots()
    for depot in depots.values:
        positions = await client.get_depot_positions(depot.depot_id)
        for position in positions.values:
            print(f"{position.wkn}: {position.current_value.value} {position.current_value.unit}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Advanced Example (Custom Credentials)

```python
import asyncio
from comdirect_api.client import ComdirectClient

async def main():
    # Provide OAuth application and Comdirect account credentials explicitly.
    client = await ComdirectClient.create(
        client_id="your_client_id",
        client_secret="your_client_secret",
        zugangsnummer="your_account_number",
        pin="your_pin",
    )

    # Client is already authenticated and ready.
    balances = await client.get_account_balances()
    for balance in balances.values:
        print(f"{balance.account_id}: {balance.balance.value} {balance.balance.unit}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Authentication Flow

The factory method ``ComdirectClient.create()`` handles the complete authentication automatically:

1. **Primary OAuth** - Authenticate with ``SESSION_RW`` scope
2. **Session Status** - Establish session ID
3. **TAN Challenge** - Initiate and wait for 2FA approval (push TAN)
4. **Banking Token** - Get banking/brokerage access via ``cd_secondary`` grant

**Result**: A fully authenticated client ready for API calls in one line!

> **Note**: You'll need to approve the push TAN notification on your phone during initialization.

### Sync to MongoDB (GitHub Actions)

The `functions/sync/` directory contains a standalone sync script triggered via a **GitHub Actions `workflow_dispatch`** workflow. Trigger it by clicking **"Run workflow"** in the [Actions tab](https://github.com/stefanfries/comdirect-api/actions) on GitHub — no infrastructure required.

The workflow installs dependencies, runs `python -m functions.sync.run --accounts "${{ inputs.accounts }}"`, and waits for you to approve push TANs sequentially (one per account, ~60 seconds each).

**Required GitHub Secrets** (Settings → Secrets and variables → Actions):

| Secret | Description |
| ------ | ----------- |
| `CLIENT_ID` | OAuth application client ID |
| `CLIENT_SECRET` | OAuth application client secret |
| `ACCOUNTS__DEPOT11__ZUGANGSNUMMER` | Account login number |
| `ACCOUNTS__DEPOT11__PIN` | Account PIN |
| `ACCOUNTS__DEPOT11__DISPLAY_NAME` | Human-readable label (optional) |
| `ACCOUNTS__DEPOT12__*`, `ACCOUNTS__DEPOT21__*`, `ACCOUNTS__DEPOT22__*` | Other account groups currently mapped in the workflow |
| `MONGODB_CONNECTION_STRING` | Atlas connection string |

The workflow maps four account prefixes: `DEPOT11`, `DEPOT12`, `DEPOT21`, and `DEPOT22`. Add the credentials for another account to the workflow's `Run sync` environment before using it in Actions. The optional **`accounts` input** accepts a comma-separated list (e.g. `DEPOT11,DEPOT22`, case-insensitive) to sync only specific mapped accounts. Leave blank to sync all mapped accounts.

The workflow does not currently pass `DEPOT_TRANSACTIONS_LOOKBACK_DAYS` to the sync process, so Actions uses the default of 365 days. For local runs, set the variable in `.env` or use `--lookback-days`.

#### Running the sync locally

```bash
uv run python -m functions.sync.run                          # all accounts
uv run python -m functions.sync.run --accounts DEPOT11       # one account
uv run python -m functions.sync.run --lookback-days 30       # override the history window
uv run python -m functions.sync.run --debug                  # raw Comdirect JSON payloads
```

| Flag | Description |
| ---- | ----------- |
| `--accounts` | Comma-separated account names; omit to sync all |
| `--lookback-days` | Overrides `DEPOT_TRANSACTIONS_LOOKBACK_DAYS` for this run |
| `--debug` | Enables DEBUG logging, including raw Comdirect depot-transaction payloads. Per-transaction summary lines are logged at INFO level on every run. |

Each account requires its own push TAN approval; authentication runs sequentially, then the syncs run in parallel.

The sync:

- **Snapshots account balances** — stores booked `balance` and `available_cash_amount` as `{value, unit}` objects (decimal-string values). Inserts a new document when either amount changes; updates `last_synced_at` otherwise. Older snapshots without available cash get a fresh snapshot on the next sync. Available cash includes any credit limit and reflects unbooked commitments; it is not necessarily owned cash.
- **Snapshots the entire depot** — inserts a new document (all positions) when composition changes (qty change, new position, sold position); updates `last_synced_at` heartbeat otherwise. Each position includes `current_price` (per-unit), `current_value` (total), `average_purchase_price`, `held_since_date`, and `purchase_price_at_entry`.
- **Backfills held-since on later syncs** — if Comdirect exposes the BUY/TRANSFER_IN transaction only on the next business day, a later depot sync can insert a new snapshot to populate `held_since_date` and `purchase_price_at_entry` even when quantity is unchanged.
- **Preserves existing held-since metadata** — if a later sync cannot derive entry metadata from the current transaction window, previously stored `held_since_date` and `purchase_price_at_entry` are retained when quantity is unchanged (no metadata regression to null).
- **Inserts depot transactions** — idempotent (skipped if already stored)

> **Breaking schema change (effective 2026-07-20):**
> `depot_snapshots.positions[]` no longer includes legacy fields `purchase_price` and `buy_price_at_entry`.
> Use `average_purchase_price` and `purchase_price_at_entry` instead.
> If you have historical data using the old fields, start with a fresh database or run a one-off migration.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#sync-function-architecture) for the full schema and design.

> **Depot transaction history limits.** The brokerage transactions endpoint returns only 20 records
> per request by default; the sync pages through all of them via the undocumented `paging-first` /
> `paging-count` parameters. Independently of that, Comdirect only serves roughly the last six months
> of depot transactions — raising `DEPOT_TRANSACTIONS_LOOKBACK_DAYS` beyond that returns no extra
> records. Positions bought before that horizon can never have `held_since_date` derived.
>
> Trades are booked at T+1 (`bookingDate = businessDate + 1`), so a freshly bought position has
> `held_since_date: null` on the trade day and is populated by the next day's sync.

### Recent Changes

- **2026-08-30 — Depot transaction pagination**: `get_depot_transactions()` now accepts `paging_first` / `paging_count`, and the sync pages through the full result set instead of silently receiving only the 20 most recent transactions. This restores reliable `held_since_date` derivation for positions bought more than a few trades ago.
- **2026-07-30 — Depot metadata preservation fix**: Depot sync no longer overwrites existing `held_since_date` / `purchase_price_at_entry` with null when the latest transaction window cannot derive entry metadata and quantity is unchanged.

## 📚 API Coverage

### ✅ Implemented (14 of 30 Swagger operations - 47%)

#### Banking (3/3)

- ✅ `GET /banking/clients/user/v2/accounts/balances` - Get all account balances
- ✅ `GET /banking/v2/accounts/{accountId}/balances` - Get a single account balance
- ✅ `GET /banking/v1/accounts/{accountId}/transactions` - Get account transactions with filters

#### Brokerage (6 operations)

- ✅ `GET /brokerage/clients/user/v3/depots` - Get all depots
- ✅ `GET /brokerage/v3/depots/{depotId}/positions` - Get all depot positions
- ✅ `GET /brokerage/v3/depots/{depotId}/positions/{positionId}` - Get single position details
- ✅ `GET /brokerage/v3/depots/{depotId}/transactions` - Get depot transactions
- ✅ `GET /brokerage/depots/{depotId}/v3/orders` - Get all orders for a depot (with filters)
- ✅ `GET /brokerage/v3/orders/{orderId}` - Get single order by ID

#### Instruments (1 operation)

- ✅ `GET /brokerage/v1/instruments/{instrumentId}` - Get instrument details (WKN/ISIN)

#### Messages (3/3)

- ✅ `GET /messages/clients/user/v2/documents` - List documents (statements, confirmations)
- ✅ `GET /messages/v2/documents/{documentId}` - Download document
- ✅ `GET /messages/v2/documents/{documentId}/predocument` - Download predocument

#### Reports (1/1)

- ✅ `GET /reports/participants/user/v1/allbalances` - Aggregated balances across all products (accounts, cards, depots, loans, savings)

#### Authentication

- ✅ OAuth2 authentication with SESSION_RW scope
- ✅ Session management and status checking
- ✅ 2FA (push TAN validation)
- ✅ Secondary banking token (cd_secondary grant)
- ✅ Automatic token refresh
- ✅ Token revocation (`DELETE /oauth/revoke`)

### 🚧 Planned

> **Current limitation**: Order placement, including Livetrading quote requests for warrants, is not implemented. The client can read depot order books and individual orders, but currently supports read-only account monitoring and analysis.

## 🛠️ Development

### Setup

```bash
# Clone and install
git clone https://github.com/stefanfries/comdirect-api.git
cd comdirect-api
uv sync                              # Core dependencies
uv sync --extra sync                 # Add sync function deps (pymongo, azure-functions)

# Run tests
uv run pytest tests/ -v              # Verbose output
uv run pytest tests/ -q              # Quick summary
uv run pytest tests/test_sync_service.py -v  # Sync function tests only

# Run tests with coverage
uv run pytest --cov=src/comdirect_api tests/

# Run linter
uv run ruff check .                  # Check for issues
uv run ruff check . --fix            # Auto-fix issues
```

### Quality Standards

- **Tests**: 120 passing tests
- **Coverage**: 79% client-package coverage (`uv run pytest --cov=src/comdirect_api --cov-report=term-missing -q`)
- **Linting**: Zero errors, zero warnings
- **Type Safety**: Full Pydantic V2 validation

See [ARCHITECTURE.md](docs/ARCHITECTURE.md#development-guidelines) for complete development guidelines.

### Project Structure

```text
comdirect_api/
├── src/
│   └── comdirect_api/          # Main package
│       ├── __init__.py         # Package initialization
│       ├── client.py           # Main API client class
│       ├── main.py             # Example usage script
│       ├── settings.py         # ClientSettings (pydantic-settings)
│       ├── utils.py            # Utility functions (timestamp)
│       └── models/             # Pydantic V2 data models
│           ├── __init__.py     # Public API exports (13 symbols)
│           ├── base.py         # ComdirectBaseModel + AmountValue
│           ├── accounts.py     # Account & balance models
│           ├── auth.py         # Authentication models (internal)
│           ├── depots.py       # Depot & position models
│           ├── instruments.py  # Instrument data models + Price
│           ├── messages.py     # Documents & messages models
│           ├── orders.py       # Brokerage order and execution models
│           ├── reports.py      # Reports & aggregated balance models
│           └── transactions.py # Transaction models
├── functions/
│   └── sync/                   # Sync package (runs via GitHub Actions)
│       ├── run.py              # GitHub Actions entrypoint (asyncio.run)
│       ├── sync_service.py     # Orchestration logic (testable)
│       ├── mongo_repo.py       # MongoDB Atlas read/write
│       └── settings.py         # SyncSettings (extends ClientSettings)
├── tests/                      # Test suite (120 tests, 79% client-package coverage)
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
│   ├── ARCHITECTURE.md         # Architecture & development guidelines ⭐
│   ├── multi-account-settings.md # Multi-account configuration and sync behavior
│   ├── swagger.json            # Comdirect API specification
│   ├── comdirect_REST_API_Dokumentation.md
│   └── comdirect_REST_API_Dokumentation.pdf
├── examples/                   # Example scripts
│   └── logging_config.py       # Logging configuration example
├── .env.example                # Environment variable template
├── LICENSE                     # MIT License
├── README.md                   # This file
├── pyproject.toml              # Project configuration & dependencies
└── uv.lock                     # Locked dependency versions
```

## 📖 Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Comprehensive architecture documentation and development guidelines ⭐
- **[Comdirect REST API](https://www.comdirect.de)** - Official API documentation
- **[API Specification](docs/swagger.json)** - OpenAPI/Swagger spec
- **Inline Docstrings** - Detailed docstrings in source code

### Quick Links

- **Architecture Overview**: See [ARCHITECTURE.md](docs/ARCHITECTURE.md#project-architecture)
- **Authentication Flow**: See [ARCHITECTURE.md](docs/ARCHITECTURE.md#authentication-architecture)
- **Data Models**: See [ARCHITECTURE.md](docs/ARCHITECTURE.md#data-models-architecture)
- **Development Guidelines**: See [ARCHITECTURE.md](docs/ARCHITECTURE.md#development-guidelines)
- **Adding New Endpoints**: See [ARCHITECTURE.md](docs/ARCHITECTURE.md#implementation-pattern-for-new-endpoints)

## ⚠️ Disclaimer

This is a **personal project** for educational and personal finance management purposes. It is **not affiliated with or endorsed by Comdirect Bank AG**.

- Use at your own risk
- Only use with your own accounts
- Be aware of API rate limits
- Follow Comdirect's terms of service
- Never share your credentials

## 🙏 Acknowledgments

- **Klaus Eisentraut** - Original [python-comdirect-api](https://github.com/keisentraut/python-comdirect-api) implementation that inspired this project
- **Comdirect Bank AG** - For providing the REST API

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

This is a personal project, but suggestions and bug reports are welcome! Feel free to open an issue or submit a pull request.

---

**Note**: This client requires valid Comdirect API credentials. You need to register as a developer with Comdirect to obtain `CLIENT_ID` and `CLIENT_SECRET`.
