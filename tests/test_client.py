"""
Unit tests for the ComdirectClient authentication logic.
This module contains pytest-based asynchronous tests for the ComdirectClient class,
focusing on the authentication workflow. It covers scenarios such as successful
authentication, HTTP errors, invalid credentials, network issues, malformed responses,
token expiration calculation, and debug output on errors. Fixtures are provided for
client credentials and client instantiation.
Tested behaviors include:
- Successful authentication and token storage.
- Handling of HTTP and network errors.
- Handling of invalid or missing credentials.
- Response parsing errors (malformed JSON, missing fields).
- Token expiration time calculation.
- Debug output on authentication errors.
- Client initialization state.
"""

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from comdirect_api.client import ComdirectClient


@pytest.mark.asyncio
async def test_authenticate_success(client_instance, creds):
    """Test successful authentication."""
    # Mock successful response data
    mock_response_data = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "expires_in": 3600,
        "token_type": "Bearer",
        "scope": "read write",
    }

    # Mock the HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status.return_value = None

    # Mock the HTTP client
    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        # Call the authenticate method
        result = await client_instance._authenticate(
            creds["username"], creds["password"]
        )

        # Verify the result
        assert result == mock_response_data
        assert client_instance.primary_access_token == "test_access_token"
        assert client_instance.refresh_token == "test_refresh_token"
        assert client_instance.token_expires_at > time.time()
        assert client_instance.scope == "read write"

        # Verify the HTTP call was made correctly
        mock_http_client.post.assert_called_once_with(
            "https://api.comdirect.de/oauth/token",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "client_id": creds["client_id"],
                "client_secret": creds["client_secret"],
                "username": creds["username"],
                "password": creds["password"],
                "grant_type": "password",
                "scope": "SESSION_RW",
            },
        )


@pytest.mark.asyncio
async def test_authenticate_http_error(client_instance, creds):
    """Test authentication with HTTP error response."""
    # Mock error response
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401 Unauthorized", request=MagicMock(), response=mock_response
    )

    # Mock the HTTP client
    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        # Call authenticate and expect it to raise an exception
        with pytest.raises(httpx.HTTPStatusError):
            await client_instance._authenticate(creds["username"], creds["password"])

        # Verify tokens are not set on error
        assert client_instance.primary_access_token is None
        assert client_instance.refresh_token is None
        assert client_instance.token_expires_at == 0


@pytest.mark.asyncio
async def test_authenticate_invalid_credentials(client_instance, creds):
    """Test authentication with invalid credentials (400 error)."""
    # Mock error response for invalid credentials
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = (
        '{"error": "invalid_grant", "error_description": "Invalid credentials"}'
    )
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "400 Bad Request", request=MagicMock(), response=mock_response
    )

    # Mock the HTTP client
    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        # Call authenticate and expect it to raise an exception
        with pytest.raises(httpx.HTTPStatusError):
            await client_instance._authenticate(creds["username"], creds["password"])


@pytest.mark.asyncio
async def test_authenticate_network_error(client_instance, creds):
    """Test authentication with network connectivity issues."""
    # Mock the HTTP client to raise a network error
    mock_http_client = AsyncMock()
    mock_http_client.post.side_effect = httpx.ConnectError("Connection failed")

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        # Call authenticate and expect it to raise a ConnectError
        with pytest.raises(httpx.ConnectError):
            await client_instance._authenticate(creds["username"], creds["password"])


@pytest.mark.asyncio
async def test_authenticate_missing_tokens_in_response(client_instance, creds):
    """Test authentication when response is missing required tokens."""
    # Mock response with missing tokens
    mock_response_data = {
        "token_type": "Bearer",
        "expires_in": 3600,
        # Missing access_token and refresh_token
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status.return_value = None

    # Mock the HTTP client
    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        # Call authenticate and check that tokens are not set due to missing fields
        await client_instance._authenticate(creds["username"], creds["password"])
        assert client_instance.primary_access_token is None
        assert client_instance.refresh_token is None


@pytest.mark.asyncio
async def test_authenticate_malformed_json_response(client_instance, creds):
    """Test authentication with malformed JSON response."""
    # Mock response that returns invalid JSON
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
    mock_response.raise_for_status.return_value = None

    # Mock the HTTP client
    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        # Call authenticate and expect it to raise a JSONDecodeError
        with pytest.raises(json.JSONDecodeError):
            await client_instance._authenticate(creds["username"], creds["password"])


@pytest.mark.asyncio
async def test_authenticate_token_expiration_calculation(client_instance, creds):
    """Test that token expiration time is calculated correctly."""
    expires_in = 7200  # 2 hours
    mock_response_data = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "expires_in": expires_in,
        "token_type": "Bearer",
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        # Record time before call
        before_time = time.time()

        await client_instance._authenticate(creds["username"], creds["password"])

        # Record time after call
        after_time = time.time()

        # Verify token expiration is set correctly (within reasonable bounds)
        # Note: Client subtracts 30 seconds for safety margin
        expected_min = before_time + expires_in - 30
        expected_max = after_time + expires_in - 30

        assert expected_min <= client_instance.token_expires_at <= expected_max


@pytest.mark.asyncio
async def test_authenticate_debug_output_on_error(client_instance, creds):
    """Test that debug information is printed on HTTP errors."""
    # Mock error response
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Internal Server Error", request=MagicMock(), response=mock_response
    )

    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class, patch(
        "builtins.print"
    ) as mock_print:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        # Call authenticate and expect it to raise an exception
        with pytest.raises(httpx.HTTPStatusError):
            await client_instance._authenticate(creds["username"], creds["password"])

        # Verify debug output was printed
        mock_print.assert_called_with(
            "Authentication failed. Status code: 500, response: Internal Server Error"
        )


def test_client_initialization():
    """Test that client is initialized with correct values."""
    test_client = ComdirectClient("test_id", "test_secret", "test_user", "test_pin")

    assert test_client.client_id == "test_id"
    assert test_client.client_secret == "test_secret"
    assert test_client.zugangsnummer == "test_user"
    assert test_client.pin == "test_pin"
    assert test_client.primary_access_token is None
    assert test_client.refresh_token is None
    assert test_client.token_expires_at == 0
    assert test_client.session_id is None


@pytest.mark.asyncio
async def test_authenticate_with_empty_credentials(client_instance):
    """Test authentication with empty username and password."""
    # This should still make the HTTP call, but the server will likely reject it
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "400 Bad Request", request=MagicMock(), response=mock_response
    )

    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        with pytest.raises(httpx.HTTPStatusError):
            await client_instance._authenticate("", "")

        # Verify the call was made with empty credentials
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        assert call_args[1]["data"]["username"] == ""
        assert call_args[1]["data"]["password"] == ""
