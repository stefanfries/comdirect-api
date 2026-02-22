"""
Unit tests for ComdirectClient session management and 2FA authentication.

Tests cover:
- Session status retrieval
- TAN challenge initiation
- TAN confirmation waiting
- Session TAN activation
- Banking/brokerage access token retrieval
- Token refresh
- Token expiration checks
"""

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from comdirect_api.client import ComdirectClient


@pytest.mark.asyncio
async def test_get_session_status_success(client_instance):
    """Test successful session status retrieval."""
    client_instance.primary_access_token = "test_token"

    mock_response_data = [
        {
            "identifier": "test_session_id",
            "sessionTanActive": False,
            "activated2FA": False,
        }
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        result = await client_instance._get_session_status()

        assert result == mock_response_data
        assert client_instance.session_id == "test_session_id"
        assert client_instance.session_tan_active is False
        assert client_instance.activated_2fa is False


@pytest.mark.asyncio
async def test_get_session_status_no_token(client_instance):
    """Test session status retrieval without access token."""
    client_instance.primary_access_token = None

    with pytest.raises(ValueError, match="No access token available"):
        await client_instance._get_session_status()


@pytest.mark.asyncio
async def test_get_banking_brokerage_access_success(client_instance):
    """Test successful banking/brokerage access token retrieval."""
    client_instance.primary_access_token = "primary_token"

    mock_response_data = {
        "access_token": "banking_token",
        "refresh_token": "refresh_token",
        "expires_in": 3600,
        "scope": "BANKING_RW BROKERAGE_RW SESSION_RW",
        "kdnr": "123456",
        "bpid": 789,
        "kontaktId": 1011,
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        result = await client_instance._get_banking_brokerage_access()

        assert result == mock_response_data
        assert client_instance.banking_access_token == "banking_token"
        assert client_instance.scope == "BANKING_RW BROKERAGE_RW SESSION_RW"
        assert client_instance.kdnr == "123456"


@pytest.mark.asyncio
async def test_get_banking_brokerage_access_no_primary_token(client_instance):
    """Test banking/brokerage access without primary token."""
    client_instance.primary_access_token = None

    with pytest.raises(ValueError, match="No base access token available"):
        await client_instance._get_banking_brokerage_access()


@pytest.mark.asyncio
async def test_refresh_access_token_success(client_instance):
    """Test successful token refresh."""
    client_instance.refresh_token = "old_refresh_token"

    mock_response_data = {
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_in": 3600,
        "scope": "BANKING_RW",
        "kdnr": "123456",
        "bpid": 789,
        "kontaktId": 1011,
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        result = await client_instance.refresh_access_token()

        assert result == mock_response_data
        assert client_instance.primary_access_token == "new_access_token"
        assert client_instance.refresh_token == "new_refresh_token"


@pytest.mark.asyncio
async def test_is_token_expired_true(client_instance):
    """Test token expiration check when token is expired."""
    client_instance.token_expires_at = time.time() - 100  # Expired 100 seconds ago

    assert client_instance.is_token_expired() is True


@pytest.mark.asyncio
async def test_is_token_expired_false(client_instance):
    """Test token expiration check when token is valid."""
    client_instance.token_expires_at = time.time() + 100  # Expires in 100 seconds

    assert client_instance.is_token_expired() is False


@pytest.mark.asyncio
async def test_activate_session_tan_success(client_instance):
    """Test successful session TAN activation."""
    client_instance.session_id = "test_session_id"
    client_instance.primary_access_token = "test_token"

    mock_response_data = {
        "identifier": "test_session_id",
        "sessionTanActive": True,
        "activated2FA": True,
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.patch.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        result = await client_instance._activate_session_tan("challenge_123")

        assert result == mock_response_data
        mock_http_client.patch.assert_called_once()


@pytest.mark.asyncio
async def test_wait_for_tan_confirmation_authenticated(client_instance):
    """Test TAN confirmation when user approves quickly."""
    client_instance.primary_access_token = "test_token"
    client_instance.session_id = "test_session_id"

    mock_response_data = {"status": "AUTHENTICATED", "id": "tan_123"}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        result = await client_instance._wait_for_tan_confirmation(
            "/api/session/v1/authentications/ABC123", max_attempts=1
        )

        assert result == mock_response_data
        assert result["status"] == "AUTHENTICATED"


@pytest.mark.asyncio
async def test_wait_for_tan_confirmation_timeout(client_instance):
    """Test TAN confirmation timeout."""
    client_instance.primary_access_token = "test_token"
    client_instance.session_id = "test_session_id"

    mock_response_data = {"status": "PENDING", "id": "tan_123"}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        with pytest.raises(TimeoutError, match="TAN confirmation timed out"):
            await client_instance._wait_for_tan_confirmation(
                "/api/session/v1/authentications/ABC123", max_attempts=2, delay=0.1
            )
