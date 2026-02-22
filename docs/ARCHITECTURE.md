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
│       ├── client.py           # Main API client class (978 lines)
│       ├── main.py             # Example usage script
│       ├── settings.py         # Environment configuration
│       ├── utils.py            # Utility functions (timestamp)
│       └── models/             # Pydantic V2 data models
│           ├── __init__.py     # Public API exports
│           ├── base.py         # ComdirectBaseModel + utilities
│           ├── accounts.py     # Account & balance models
│           ├── auth.py         # Authentication models (internal)
│           ├── depots.py       # Depot & position models
│           ├── instruments.py  # Instrument data models
│           ├── messages.py     # Documents & messages models
│           └── transactions.py # Transaction models
├── tests/                      # Test suite (78 tests, 83% coverage)
│   ├── __init__.py
│   ├── conftest.py             # Shared test fixtures
│   ├── test_auth.py            # Authentication tests
│   ├── test_banking.py         # Banking operations tests
│   ├── test_brokerage.py       # Brokerage operations tests
│   ├── test_client.py          # Client functionality tests
│   ├── test_factory.py         # Factory pattern tests
│   ├── test_messages.py        # Messages API tests
│   ├── test_reports.py         # Reports tests (placeholder)
│   ├── test_tan_flow.py        # TAN workflow tests
│   ├── test_tan_polling.py     # TAN polling tests
│   ├── test_utils.py           # Utility function tests
│   └── test_validation_errors.py # Validation tests
├── docs/                       # Documentation
│   ├── ARCHITECTURE.md         # This file
│   ├── swagger.json            # Comdirect API specification
│   ├── comdirect_REST_API_Dokumentation.md
│   └── comdirect_REST_API_Dokumentation.pdf
├── examples/                   # Example scripts
│   └── logging_config.py       # Logging configuration example
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

The `ComdirectClient` class maintains multiple token types:

| Token Type | Purpose | Scope | Usage |
| ---------- | ------- | ----- | ----- |
| `primary_access_token` | Initial authentication | `SESSION_RW` | Session setup |
| `session_access_token` | Post-TAN validation | Session operations | TAN activation |
| `banking_access_token` | Banking/brokerage access | Account operations | All API calls |

### State Flags

- `session_id` - Required for all session operations (extracted from headers)
- `activated_2fa` - Tracks 2FA state to prevent duplicate TAN challenges
- `token_expires_at` - Token expiration timestamp for automatic refresh

### Factory Pattern

The `ComdirectClient.create()` factory method encapsulates the entire authentication flow:

```python
client = await ComdirectClient.create()  # Fully authenticated in one call
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
| `base.py` | Base class and utilities | `ComdirectBaseModel`, `to_camel()` |
| `accounts.py` | Account and balance data | `AccountBalances`, `AccountBalance`, `Balance` |
| `auth.py` | Authentication responses | `AuthResponse`, `TokenState` (internal) |
| `depots.py` | Depot and position data | `AccountDepots`, `DepotPositions`, `DepotPosition` |
| `instruments.py` | Instrument/security data | `Instruments`, `Instrument`, `StaticData` |
| `messages.py` | Documents and messages | `Documents`, `Document`, `DocumentMetadata` |
| `transactions.py` | Transaction data | `AccountTransactions`, `DepotTransactions` |

### Public API Models

Only **top-level response models** are exposed in `models/__init__.py`:

```python
__all__ = [
    "AccountBalances",      # from get_account_balances()
    "AccountTransactions",  # from get_account_transactions()
    "AccountDepots",        # from get_account_depots()
    "DepotPositions",       # from get_depot_positions()
    "DepotPosition",        # from get_depot_position()
    "DepotTransactions",    # from get_depot_transactions()
    "Instruments",          # from get_instrument()
    "Documents",            # from get_documents()
]
```

**Design Principle**: Internal models (e.g., `Account`, `Balance`, `AuthResponse`) are not exposed. Users access nested data via properties of response objects.

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
- **ISO4217 Currency Codes**: Currency validation using standard codes
- **Proper Precision**: Maintains exact decimal precision for financial calculations

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

Use `httpx.MockTransport` for HTTP mocking:

```python
async def test_api_call(mock_credentials):
    def handler(request):
        return httpx.Response(200, json={...})
    
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = ComdirectClient(http_client=http_client, **mock_credentials)
        result = await client.api_call()
```

#### Coverage Standards

- **Minimum Coverage**: 80% overall
- **Critical Paths**: 100% coverage for authentication flow
- **Test Types**: Unit tests only (no integration tests with real API)

### Error Handling

#### Debug Logging

On HTTP errors, log diagnostic information:

```python
except httpx.HTTPStatusError as e:
    print(f"❌ HTTP {e.response.status_code} Error")
    print(f"Response: {e.response.text}")
    raise
```

#### Exception Strategy

- **Specific Exceptions**: Different exceptions for auth vs network failures
- **Token Expiration**: Automatic refresh before operations
- **Rate Limiting**: Respect API limits (not currently implemented)

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
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
ZUGANGSNUMMER=your_account_number
PIN=your_pin
```

#### Settings Management

Settings are managed via Pydantic Settings in `settings.py`:

```python
class Settings(BaseSettings):
    client_id: str
    client_secret: str
    zugangsnummer: str
    pin: str
    
    model_config = SettingsConfigDict(env_file=".env")
```

**Never commit** `.env` files or credentials to version control.

## API Coverage Strategy

### Current Coverage (7/30 endpoints - 23%)

#### Implemented Endpoints

**Banking (2/3)**:

- ✅ `GET /accounts/balances` - All account balances
- ✅ `GET /accounts/{accountId}/transactions` - Account transactions with filters

**Brokerage (2/20)**:

- ✅ `GET /depot` - All depots
- ✅ `GET /depot/{depotId}/positions` - All depot positions
- ✅ `GET /depot/{depotId}/positions/{positionId}` - Single position details
- ✅ `GET /depot/{depotId}/transactions` - Depot transactions

**Instruments (1/1)**:

- ✅ `GET /instruments/{instrumentId}` - Instrument details (WKN/ISIN)

**Messages (3/3)**:

- ✅ `GET /messages/documents` - List documents (statements, confirmations)
- ✅ `GET /messages/documents/{documentId}` - Download document
- ✅ `GET /messages/predocuments/{documentId}` - Download predocument

#### Focus Areas

**Priority 1**: GET-only endpoints for read operations (monitoring/analysis)
**Excluded**: POST/PATCH/DELETE endpoints (order placement, modifications)

**User Requirement**: No active trading via API - focus on account monitoring and data retrieval only.

### Implementation Pattern for New Endpoints

When adding new API endpoints:

1. **Create Pydantic Models** in appropriate `models/` file
2. **Add Client Method** to `ComdirectClient` class
3. **Use Standard Pattern**:

   ```python
   async def get_resource(self, resource_id: str) -> ResourceModel:
       """Brief description of operation."""
       if self.is_token_expired():
           await self.refresh_access_token()
       
       headers = self._request_headers(self.banking_access_token)
       response = await self.http_client.get(
           f"{BASE_URL}/resource/{resource_id}",
           headers=headers
       )
       response.raise_for_status()
       return ResourceModel(**response.json())
   ```

4. **Add Tests** in corresponding `tests/test_*.py` file
5. **Update Public API** in `models/__init__.py` if exposing new top-level model
6. **Document** in README.md API coverage section

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

## Integration Points

### External Dependencies

- **Comdirect REST API** - OAuth2-protected financial API
- **Push TAN App** - Mobile app for 2FA approval
- **Environment Variables** - Credential management via `.env`

### API Constraints

- **Rate Limiting**: Not documented by Comdirect (best practice: conservative usage)
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

- ✅ **Read-only focus** - minimize write operations
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

### Current Version

- Messages API implementation (3 GET endpoints)
- Base model architecture with automatic camelCase conversion
- 78 tests with 83% coverage
- Public API refinement (8 top-level models)
- Comprehensive error handling and token management

### Next Steps

- Implement remaining GET endpoints (Orders, Reports)
- Add rate limiting support
- Consider modularization of `client.py`
- Enhanced logging and debugging capabilities

---

**Last Updated**: February 22, 2026
