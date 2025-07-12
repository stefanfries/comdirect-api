import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from api.client import ComdirectClient


@pytest.fixture
def client_creds():
    """Fixture providing test client credentials."""
    return {
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "username": "test_username",
        "password": "test_password",
    }


@pytest.fixture
def client(client_creds):
    """Fixture providing a ComdirectClient instance."""
    return ComdirectClient(
        client_id=client_creds["client_id"], client_secret=client_creds["client_secret"]
    )


@pytest.mark.asyncio
async def test_authenticate_success(client, client_creds):
    """Test successful authentication."""
    # Mock successful response data
    mock_response_data = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "expires_in": 3600,
        "token_type": "Bearer",
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
        result = await client.authenticate(
            client_creds["username"], client_creds["password"]
        )

        # Verify the result
        assert result == mock_response_data
        assert client.access_token == "test_access_token"
        assert client.refresh_token == "test_refresh_token"
        assert client.token_expires_at > time.time()

        # Verify the HTTP call was made correctly
        mock_http_client.post.assert_called_once_with(
            "https://api.comdirect.de/oauth/token",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "client_id": client_creds["client_id"],
                "client_secret": client_creds["client_secret"],
                "username": client_creds["username"],
                "password": client_creds["password"],
                "grant_type": "password",
            },
        )


@pytest.mark.asyncio
async def test_authenticate_http_error(client, client_creds):
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
            await client.authenticate(
                client_creds["username"], client_creds["password"]
            )

        # Verify tokens are not set on error
        assert client.access_token is None
        assert client.refresh_token is None
        assert client.token_expires_at == 0


@pytest.mark.asyncio
async def test_authenticate_invalid_credentials(client, client_creds):
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
            await client.authenticate(
                client_creds["username"], client_creds["password"]
            )


@pytest.mark.asyncio
async def test_authenticate_network_error(client, client_creds):
    """Test authentication with network connectivity issues."""
    # Mock the HTTP client to raise a network error
    mock_http_client = AsyncMock()
    mock_http_client.post.side_effect = httpx.ConnectError("Connection failed")

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        # Call authenticate and expect it to raise a ConnectError
        with pytest.raises(httpx.ConnectError):
            await client.authenticate(
                client_creds["username"], client_creds["password"]
            )


@pytest.mark.asyncio
async def test_authenticate_missing_tokens_in_response(client, client_creds):
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

        # Call authenticate and expect it to raise a KeyError
        with pytest.raises(KeyError):
            await client.authenticate(
                client_creds["username"], client_creds["password"]
            )


@pytest.mark.asyncio
async def test_authenticate_malformed_json_response(client, client_creds):
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
            await client.authenticate(
                client_creds["username"], client_creds["password"]
            )


@pytest.mark.asyncio
async def test_authenticate_token_expiration_calculation(client, client_creds):
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

        await client.authenticate(client_creds["username"], client_creds["password"])

        # Record time after call
        after_time = time.time()

        # Verify token expiration is set correctly (within reasonable bounds)
        expected_min = before_time + expires_in
        expected_max = after_time + expires_in

        assert expected_min <= client.token_expires_at <= expected_max


@pytest.mark.asyncio
async def test_authenticate_debug_output_on_error(client, client_creds):
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
            await client.authenticate(
                client_creds["username"], client_creds["password"]
            )

        # Verify debug output was printed
        mock_print.assert_called_with("Error: 500, response: Internal Server Error")


def test_client_initialization():
    """Test that client is initialized with correct values."""
    test_client = ComdirectClient("test_id", "test_secret")

    assert test_client.client_id == "test_id"
    assert test_client.client_secret == "test_secret"
    assert test_client.access_token is None
    assert test_client.refresh_token is None
    assert test_client.token_expires_at == 0
    assert test_client.session_id is None


@pytest.mark.asyncio
async def test_authenticate_with_empty_credentials(client):
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
            await client.authenticate("", "")

        # Verify the call was made with empty credentials
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        assert call_args[1]["data"]["username"] == ""
        assert call_args[1]["data"]["password"] == ""
