# Comdirect API Client

![License](https://img.shields.io/github/license/stefanfries/comdirect-api)
![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)
![Code Style](https://img.shields.io/badge/code%20style-ruff-black)
![Type Checked](https://img.shields.io/badge/type%20checked-pydantic-green)

A modern, fully asynchronous Python client for the [Comdirect REST API](https://www.comdirect.de). Access your banking and brokerage accounts programmatically with full OAuth2 authentication and 2FA support.

> **Acknowledgment**: This project is inspired by [Klaus Eisentraut's python-comdirect-api](https://github.com/keisentraut/python-comdirect-api). This implementation modernizes the approach with current best practices and libraries.

## ✨ Features

- 🔐 **Full OAuth2 Flow** - Complete authentication with 2FA (push TAN support)
- ⚡ **Fully Async** - Built on `httpx` for high-performance async operations
- 📊 **Comprehensive API Coverage** - Banking, brokerage, depot positions, transactions, instruments
- 🔒 **Type-Safe** - Pydantic V2 models for all API responses
- 🐍 **Pythonic** - Snake_case interface with automatic camelCase conversion for API calls
- 🧪 **Well Tested** - Comprehensive test suite with pytest
- 📦 **Modern Stack** - Python 3.11+, httpx, Pydantic V2, async/await

## 🚀 Tech Stack

| Component | Technology |
|-----------|-----------|
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

### Basic Example

```python
import asyncio
from comdirect_api.client import ComdirectClient
from comdirect_api.settings import settings

async def main():
    # Initialize client
    client = ComdirectClient(
        client_id=settings.client_id.get_secret_value(),
        client_secret=settings.client_secret.get_secret_value()
    )
    
    # Authenticate
    await client.authenticate(
        username=settings.zugangsnummer.get_secret_value(),
        password=settings.pin.get_secret_value()
    )
    
    # Get session and activate 2FA
    await client.get_session_status()
    await client.create_validate_session_tan()  # Approve on your phone
    
    # Get banking access token
    await client.get_banking_brokerage_access()
    
    # Fetch account balances
    balances = await client.get_account_balances()
    for balance in balances.values:
        print(f"Account: {balance.account_display_id}")
        print(f"Balance: {balance.balance.value} {balance.balance.unit}")
    
    # Get depot positions
    depots = await client.get_account_depots()
    for depot in depots.values:
        positions = await client.get_depot_positions(depot.depot_id)
        for position in positions.values:
            print(f"Position: {position.position_id}")
            print(f"Quantity: {position.quantity}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Authentication Flow

The Comdirect API requires a multi-step authentication process:

1. **Primary OAuth** - Get base token with `SESSION_RW` scope
2. **Session Status** - Establish session ID
3. **TAN Challenge** - Initiate and confirm 2FA (push TAN)
4. **Secondary Token** - Get banking/brokerage access via `cd_secondary` grant
5. **API Calls** - Use banking token for operations

## 📚 API Coverage

### ✅ Implemented

#### Banking
- ✅ Get account balances
- ✅ Get account transactions (with filters)

#### Brokerage
- ✅ Get depots
- ✅ Get depot positions (all or single)
- ✅ Get depot transactions
- ✅ Get instrument details (by WKN/ISIN)

#### Authentication
- ✅ OAuth2 authentication
- ✅ Session management
- ✅ 2FA (push TAN)
- ✅ Token refresh

### 🚧 Planned

- Documents API
- Messages API
- Reports API
- Order placement (requires additional security measures)

## 🛠️ Development

### Setup

```bash
# Clone and install
git clone https://github.com/stefanfries/comdirect-api.git
cd comdirect-api
uv sync

# Run tests
uv run pytest tests/ -v

# Run linter
uv run ruff check .

# Auto-fix linting issues
uv run ruff check . --fix
```

### Project Structure

```
comdirect_api/
├── src/comdirect_api/
│   ├── client.py          # Main client class
│   ├── settings.py        # Configuration management
│   ├── utils.py           # Utility functions
│   ├── models/            # Pydantic models
│   │   ├── accounts.py
│   │   ├── depots.py
│   │   ├── transactions.py
│   │   └── instruments.py
│   └── main.py            # Example script
├── tests/                 # Test suite
├── docs/                  # API documentation
└── pyproject.toml         # Project metadata
```

## 📖 Documentation

For detailed API documentation, see the [Comdirect REST API documentation](https://www.comdirect.de) and the inline docstrings in the code.

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
