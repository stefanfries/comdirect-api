# Comdirect API Client

![License](https://img.shields.io/github/license/stefanfries/comdirect-api)
![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)
![Code Style](https://img.shields.io/badge/code%20style-ruff-black)
![Type Checked](https://img.shields.io/badge/type%20checked-pydantic-green)
![Tests](https://img.shields.io/badge/tests-115%20passed-success)
![Coverage](https://img.shields.io/badge/coverage-80%25-green)

A modern, fully asynchronous Python client for the [Comdirect REST API](https://www.comdirect.de). Access your banking and brokerage accounts programmatically with full OAuth2 authentication and 2FA support.

> **Acknowledgment**: This project is inspired by [Klaus Eisentraut's python-comdirect-api](https://github.com/keisentraut/python-comdirect-api). This implementation modernizes the approach with current best practices and libraries.

## ✨ Features

- 🔐 **Full OAuth2 Flow** - Complete authentication with 2FA (push TAN support)
- ⚡ **Fully Async** - Built on `httpx` for high-performance async operations
- 📊 **Comprehensive API Coverage** - Banking, brokerage, depot positions, transactions, instruments, documents
- 🔒 **Type-Safe** - Pydantic V2 models for all API responses with automatic camelCase conversion
- 🐍 **Pythonic** - Clean snake_case interface with automatic camelCase for API calls
- 🧪 **Well Tested** - 115 tests with 80% code coverage
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

# Install sync function dependencies (Azure Functions + pymongo)
uv sync --extra sync
```

## 🔧 Configuration

Create a `.env` file in the project root (copy from `.env.example`):

```env
# Comdirect credentials (required for all usage)
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
ZUGANGSNUMMER=your_account_number
PIN=your_pin

# MongoDB Atlas (required only for the sync function)
MONGODB_CONNECTION_STRING=mongodb+srv://...
MONGODB_DATABASE=finance
```

> **Important**: Never commit your `.env` file to version control!

## 💻 Usage

### Simple Example (Recommended)

```python
import asyncio
from comdirect_api.client import ComdirectClient

async def main():
    # One-line authentication! Factory method handles everything:
    # 1. OAuth authentication
    # 2. Session setup
    # 3. TAN challenge (approve on your phone)
    # 4. Banking/brokerage token
    
    client = await ComdirectClient.create()
    
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
    # Provide custom credentials (or uses .env by default)
    client = await ComdirectClient.create(
        client_id="your_client_id",
        client_secret="your_client_secret",
        zugangsnummer="your_account_number",
        pin="your_pin"
    )
    
    # Client is already authenticated and ready!
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

The workflow installs dependencies, runs `python -m functions.sync.run`, and waits for you to approve the push TAN on your phone (~60 seconds). Required GitHub Secrets: `CLIENT_ID`, `CLIENT_SECRET`, `ZUGANGSNUMMER`, `PIN`, `MONGODB_CONNECTION_STRING`.

The sync:

- **Snapshots account balances** — inserts a new document on value change; updates `last_synced_at` heartbeat otherwise
- **Snapshots the entire depot** — inserts a new document (all positions) when composition changes (qty change, new position, sold position); updates `last_synced_at` heartbeat otherwise. Each position includes `current_price` (per-unit), `current_value` (total), and `purchase_price`.
- **Inserts depot transactions** — idempotent (skipped if already stored)

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#sync-function-architecture) for the full schema and design.

## 📚 API Coverage

### ✅ Implemented (13 of 30 endpoints - 43%)

#### Banking (3/3)

- ✅ `GET /accounts/balances` - Get all account balances
- ✅ `GET /accounts/{accountId}/balances` - Get single account balance
- ✅ `GET /accounts/{accountId}/transactions` - Get account transactions with filters

#### Brokerage (7/20)

- ✅ `GET /depot` - Get all depots
- ✅ `GET /depot/{depotId}/positions` - Get all depot positions
- ✅ `GET /depot/{depotId}/positions/{positionId}` - Get single position details
- ✅ `GET /depot/{depotId}/transactions` - Get depot transactions
- ✅ `GET /instruments/{instrumentId}` - Get instrument details (WKN/ISIN)
- ✅ `GET /brokerage/depots/{depotId}/v3/orders` - Get all orders for a depot (with filters)
- ✅ `GET /brokerage/v3/orders/{orderId}` - Get single order by ID

#### Messages (3/3)

- ✅ `GET /messages/documents` - List documents (statements, confirmations)
- ✅ `GET /messages/documents/{documentId}` - Download document
- ✅ `GET /messages/predocuments/{documentId}` - Download predocument

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

> **Note**: Order placement (POST/PATCH/DELETE operations) is intentionally excluded. This client focuses on read-only operations for account monitoring and analysis.

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

- **Tests**: 115 passing tests
- **Coverage**: 80% code coverage
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
│           ├── __init__.py     # Public API exports (11 symbols)
│           ├── base.py         # ComdirectBaseModel + AmountValue
│           ├── accounts.py     # Account & balance models
│           ├── auth.py         # Authentication models (internal)
│           ├── depots.py       # Depot & position models
│           ├── instruments.py  # Instrument data models + Price
│           ├── messages.py     # Documents & messages models
│           ├── reports.py      # Reports & aggregated balance models
│           └── transactions.py # Transaction models
├── functions/
│   └── sync/                   # Sync package (runs via GitHub Actions)
│       ├── run.py              # GitHub Actions entrypoint (asyncio.run)
│       ├── sync_service.py     # Orchestration logic (testable)
│       ├── mongo_repo.py       # MongoDB Atlas read/write
│       └── settings.py         # SyncSettings (extends ClientSettings)
├── tests/                      # Test suite (115 tests, 80% coverage)
│   ├── conftest.py             # Shared test fixtures
│   ├── test_auth.py            # Authentication tests
│   ├── test_banking.py         # Banking operations tests
│   ├── test_brokerage.py       # Brokerage operations tests
│   ├── test_client.py          # Client functionality tests
│   ├── test_factory.py         # Factory pattern tests
│   ├── test_messages.py        # Messages API tests
│   ├── test_reports.py         # Reports tests
│   ├── test_sync_service.py    # Sync function tests
│   ├── test_tan_flow.py        # TAN workflow tests
│   ├── test_tan_polling.py     # TAN polling tests
│   ├── test_utils.py           # Utility function tests
│   └── test_validation_errors.py # Validation tests
├── docs/                       # Documentation
│   ├── ARCHITECTURE.md         # Architecture & development guidelines ⭐
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
