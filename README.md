# Comdirect API Client

![License](https://img.shields.io/github/license/stefanfries/comdirect-api)
![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)
![Code Style](https://img.shields.io/badge/code%20style-ruff-black)
![Type Checked](https://img.shields.io/badge/type%20checked-pydantic-green)
![Tests](https://img.shields.io/badge/tests-78%20passed-success)
![Coverage](https://img.shields.io/badge/coverage-83%25-green)

A modern, fully asynchronous Python client for the [Comdirect REST API](https://www.comdirect.de). Access your banking and brokerage accounts programmatically with full OAuth2 authentication and 2FA support.

> **Acknowledgment**: This project is inspired by [Klaus Eisentraut's python-comdirect-api](https://github.com/keisentraut/python-comdirect-api). This implementation modernizes the approach with current best practices and libraries.

## ✨ Features

- 🔐 **Full OAuth2 Flow** - Complete authentication with 2FA (push TAN support)
- ⚡ **Fully Async** - Built on `httpx` for high-performance async operations
- 📊 **Comprehensive API Coverage** - Banking, brokerage, depot positions, transactions, instruments, documents
- 🔒 **Type-Safe** - Pydantic V2 models for all API responses with automatic camelCase conversion
- 🐍 **Pythonic** - Clean snake_case interface with automatic camelCase for API calls
- 🧪 **Well Tested** - 78 tests with 83% code coverage
- 📦 **Modern Stack** - Python 3.11+, httpx, Pydantic V2, async/await

## 🚀 Tech Stack

| Component | Technology |
| --------- | --------- |
| HTTP Client | `httpx` (async) |
| Data Validation | `pydantic` V2 |
| Configuration | `pydantic-settings` |
| Package Manager | `uv` |
| Testing | `pytest` + `pytest-asyncio` |
| Code Quality | `ruff` |

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/stefanfries/comdirect-api.git
cd comdirect-api

# Install with uv (recommended)
uv sync

# Or with pip
pip install -r requirements.txt
```

## 🔧 Configuration

Create a `.env` file in the project root:

```env
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
ZUGANGSNUMMER=your_account_number
PIN=your_pin
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
            print(f"{position.wkn}: {position.current_value}")

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
        print(f"{balance.account_id}: {balance.balance.value}")

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

## 📚 API Coverage

### ✅ Implemented (7 of 30 endpoints - 23%)

#### Banking (2/3)

- ✅ `GET /accounts/balances` - Get all account balances
- ✅ `GET /accounts/{accountId}/transactions` - Get account transactions with filters

#### Brokerage (5/20)

- ✅ `GET /depot` - Get all depots
- ✅ `GET /depot/{depotId}/positions` - Get all depot positions
- ✅ `GET /depot/{depotId}/positions/{positionId}` - Get single position details
- ✅ `GET /depot/{depotId}/transactions` - Get depot transactions
- ✅ `GET /instruments/{instrumentId}` - Get instrument details (WKN/ISIN)

#### Messages (3/3)

- ✅ `GET /messages/documents` - List documents (statements, confirmations)
- ✅ `GET /messages/documents/{documentId}` - Download document
- ✅ `GET /messages/predocuments/{documentId}` - Download predocument

#### Authentication

- ✅ OAuth2 authentication with SESSION_RW scope
- ✅ Session management and status checking
- ✅ 2FA (push TAN validation)
- ✅ Secondary banking token (cd_secondary grant)
- ✅ Automatic token refresh

### 🚧 Planned

- **Orders API** - View existing orders (read-only)
- **Reports API** - Comprehensive balance reports
- **Banking** - Single account balance details

> **Note**: Order placement (POST/PATCH/DELETE operations) is intentionally excluded. This client focuses on read-only operations for account monitoring and analysis.

## 🛠️ Development

### Setup

```bash
# Clone and install
git clone https://github.com/stefanfries/comdirect-api.git
cd comdirect-api
uv sync

# Run tests
uv run pytest tests/ -v              # Verbose output
uv run pytest tests/ -q              # Quick summary

# Run tests with coverage
uv run pytest --cov=src/comdirect_api tests/

# Run linter
uv run ruff check .                  # Check for issues
uv run ruff check . --fix            # Auto-fix issues
```

### Quality Standards

- **Tests**: 78 passing tests
- **Coverage**: 83% code coverage
- **Linting**: Zero errors, zero warnings
- **Type Safety**: Full Pydantic V2 validation

See [ARCHITECTURE.md](docs/ARCHITECTURE.md#development-guidelines) for complete development guidelines.

### Project Structure

```text
comdirect_api/
├── src/comdirect_api/
│   ├── client.py          # Main client class (978 lines)
│   ├── main.py            # Example usage script
│   ├── utils.py           # Utility functions (timestamp)
│   ├── core/
│   │   └── settings.py    # Environment configuration
│   ├── clients/           # Future modular clients
│   │   ├── auth.py        # (planned)
│   │   ├── banking.py     # (planned)
│   │   ├── brokerage.py   # (planned)
│   │   └── session.py     # (planned)
│   └── models/            # Pydantic V2 models
│       ├── base.py        # ComdirectBaseModel + utilities
│       ├── accounts.py    # Account & balance models
│       ├── depots.py      # Depot & position models
│       ├── transactions.py # Transaction models
│       ├── instruments.py # Instrument data models
│       ├── messages.py    # Documents & messages models
│       └── auth.py        # Authentication models
├── tests/                 # Test suite (78 tests, 83% coverage)
│   ├── test_auth.py
│   ├── test_banking.py
│   ├── test_brokerage.py
│   ├── test_messages.py
│   └── ...
├── docs/
│   ├── swagger.json       # Comdirect API specification
│   └── ARCHITECTURE.md    # Architecture & development guidelines ⭐
├── README.md              # This file
└── pyproject.toml         # Project configuration
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
