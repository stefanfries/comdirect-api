# Comdirect API Client - AI Coding Agent Instructions

## Project Overview
This is a Python client for the Comdirect REST API that handles banking and brokerage account access through a complex OAuth2 flow with 2FA authentication. The API requires a multi-step authentication process involving primary tokens, session management, TAN validation, and secondary banking tokens.

## Architecture & Key Components

### Authentication Flow (Critical)
The Comdirect API requires a **5-step authentication sequence** that must be followed precisely:

1. **Primary OAuth** (`authenticate()`) - Gets base token with SESSION_RW scope
2. **Session Status** (`get_session_status()`) - Establishes session ID and checks 2FA state  
3. **TAN Challenge** (`create_validate_session_tan()`) - Initiates and waits for push TAN approval
4. **Secondary Token** (`get_banking_brokerage_access()`) - Gets banking/brokerage permissions via `cd_secondary` grant
5. **API Calls** - Use banking token for account/depot operations

**Never skip steps or reorder** - each step depends on the previous one's state.

### Client State Management
The `ComdirectClient` class maintains multiple token types and state flags:
- `primary_access_token` - Initial OAuth token
- `session_access_token` - Token after TAN validation  
- `banking_access_token` - Token for banking/brokerage operations
- `session_id` - Required for all session operations
- `activated_2fa` - Tracks 2FA state to avoid duplicate TAN challenges

### Request Headers Pattern
All API requests use a standardized header structure via `_request_headers()`:
```python
{
    "Authorization": f"Bearer {token}",
    "x-http-request-info": json.dumps({
        "clientRequestId": {
            "sessionId": self.session_id,
            "requestId": timestamp()
        }
    })
}
```

### Models & Data Flow
- **Pydantic models** in `src/comdirect_api/models/` define API response structures
- **Decimal types** for financial amounts (never floats)
- **ISO4217 currency codes** for currency validation
- **Pagination objects** for list responses

## Development Patterns

### Environment Configuration
Uses `python-dotenv` for credentials. Required env vars:
- `CLIENT_ID` - OAuth client ID
- `CLIENT_SECRET` - OAuth client secret  
- `ZUGANGSNUMMER` - Account login number
- `PIN` - Account PIN

### Testing Approach
- **Async pytest** with `pytest-asyncio`
- **Mock HTTP responses** using `httpx` mocks in `tests/`
- **Fixtures** in `conftest.py` provide test credentials and client instances
- Import path uses `api.client` (not `src.comdirect_api.client`)

### Error Handling Strategy
- **Debug prints** on HTTP errors showing status codes and response text
- **Specific exceptions** for authentication failures vs network issues
- **Token expiration checks** before API calls with automatic refresh

## Critical Implementation Details

### TAN Challenge Workflow
The `create_validate_session_tan()` method orchestrates a complex 3-part flow:
1. Initiate challenge via POST to `/sessions/{id}/validate`
2. Poll authentication URL from `x-once-authentication-info` header
3. Activate session TAN with challenge ID

**Key**: The authentication URL is extracted from response headers, not the JSON body.

### Token Refresh Logic
- Tokens expire after ~30 minutes
- `is_token_expired()` checks against stored `token_expires_at` 
- `refresh_access_token()` uses refresh token to get new access token
- Banking operations auto-refresh before API calls

### Module Organization
- `client.py` - Main client class with all API operations
- `models/` - Pydantic response models (accounts, depots, auth)
- `clients/` - Empty placeholder files for future modularization
- `utils.py` - Timestamp utility for request IDs

## Commands & Workflows

### Running Tests
```bash
pytest tests/ -v --tb=short
```

### Environment Setup
```bash
pip install -r requirements.txt
# Create .env file with required credentials
python -m src.comdirect_api.main
```

### Adding New API Endpoints
1. Add Pydantic model in appropriate `models/` file
2. Add method to `ComdirectClient` class
3. Use `banking_access_token` for banking/brokerage endpoints
4. Follow existing header pattern with `_request_headers()`
5. Add corresponding test in `tests/`

## Integration Points
- **Comdirect REST API** - External banking API with proprietary OAuth flow
- **Push TAN authentication** - Mobile app approval required for 2FA
- **Session management** - Time-limited sessions requiring periodic renewal
- **Multi-scope tokens** - Different permissions for session vs banking operations

This client is specifically designed for personal account monitoring and follows Comdirect's stringent security requirements for financial API access.