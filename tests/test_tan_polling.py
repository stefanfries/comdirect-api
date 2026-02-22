"""Tests for TAN confirmation polling logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


@pytest.mark.asyncio
async def test_wait_for_tan_authenticated_immediately(client_instance):
    """Test TAN polling when status is AUTHENTICATED on first try."""
    client_instance.primary_access_token = "token"
    client_instance.session_id = "session123"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "AUTHENTICATED"}

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        result = await client_instance._wait_for_tan_confirmation("/auth/url")

        assert result["status"] == "AUTHENTICATED"
        mock_http_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_wait_for_tan_pending_then_authenticated(client_instance):
    """Test TAN polling with PENDING status then AUTHENTICATED."""
    client_instance.primary_access_token = "token"
    client_instance.session_id = "session123"

    # Create mock responses: first PENDING, then AUTHENTICATED
    pending_response = MagicMock()
    pending_response.status_code = 200
    pending_response.json.return_value = {"status": "PENDING"}

    authenticated_response = MagicMock()
    authenticated_response.status_code = 200
    authenticated_response.json.return_value = {"status": "AUTHENTICATED"}

    mock_http_client = AsyncMock()
    mock_http_client.get.side_effect = [pending_response, authenticated_response]

    with patch("httpx.AsyncClient") as mock_client_class, patch(
        "asyncio.sleep", new_callable=AsyncMock
    ):
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        result = await client_instance._wait_for_tan_confirmation(
            "/auth/url", max_attempts=5, delay=0.1
        )

        assert result["status"] == "AUTHENTICATED"
        assert mock_http_client.get.call_count == 2


@pytest.mark.asyncio
async def test_wait_for_tan_active_status(client_instance):
    """Test TAN polling with ACTIVE status (should continue polling)."""
    client_instance.primary_access_token = "token"
    client_instance.session_id = "session123"

    active_response = MagicMock()
    active_response.status_code = 200
    active_response.json.return_value = {"status": "ACTIVE"}

    authenticated_response = MagicMock()
    authenticated_response.status_code = 200
    authenticated_response.json.return_value = {"status": "AUTHENTICATED"}

    mock_http_client = AsyncMock()
    mock_http_client.get.side_effect = [active_response, authenticated_response]

    with patch("httpx.AsyncClient") as mock_client_class, patch(
        "asyncio.sleep", new_callable=AsyncMock
    ):
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        result = await client_instance._wait_for_tan_confirmation(
            "/auth/url", max_attempts=5, delay=0.1
        )

        assert result["status"] == "AUTHENTICATED"
        assert mock_http_client.get.call_count == 2


@pytest.mark.asyncio
async def test_wait_for_tan_timeout(client_instance):
    """Test TAN polling timeout after max attempts."""
    client_instance.primary_access_token = "token"
    client_instance.session_id = "session123"

    # Always return PENDING
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "PENDING"}

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class, patch(
        "asyncio.sleep", new_callable=AsyncMock
    ):
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        with pytest.raises(TimeoutError, match="TAN confirmation timed out"):
            await client_instance._wait_for_tan_confirmation(
                "/auth/url", max_attempts=3, delay=0.1
            )

        assert mock_http_client.get.call_count == 3


@pytest.mark.asyncio
async def test_wait_for_tan_not_found(client_instance):
    """Test TAN polling when challenge is not found (404)."""
    client_instance.primary_access_token = "token"
    client_instance.session_id = "session123"

    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class, patch(
        "asyncio.sleep", new_callable=AsyncMock
    ):
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        with pytest.raises(TimeoutError):
            await client_instance._wait_for_tan_confirmation(
                "/auth/url", max_attempts=3, delay=0.1
            )


@pytest.mark.asyncio
async def test_wait_for_tan_unexpected_status_code(client_instance):
    """Test TAN polling with unexpected HTTP status code."""
    client_instance.primary_access_token = "token"
    client_instance.session_id = "session123"

    error_response = MagicMock()
    error_response.status_code = 500
    error_response.text = "Internal Server Error"
    error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Server Error", request=MagicMock(), response=error_response
    )

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = error_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        with pytest.raises(httpx.HTTPStatusError):
            await client_instance._wait_for_tan_confirmation(
                "/auth/url", max_attempts=1, delay=0.1
            )


@pytest.mark.asyncio
async def test_wait_for_tan_http_error_retry(client_instance):
    """Test TAN polling retries on HTTP errors."""
    client_instance.primary_access_token = "token"
    client_instance.session_id = "session123"

    # First call raises error, second succeeds
    error_response = MagicMock()
    error_response.status_code = 503
    error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "503 Service Unavailable", request=MagicMock(), response=error_response
    )

    success_response = MagicMock()
    success_response.status_code = 200
    success_response.json.return_value = {"status": "AUTHENTICATED"}

    mock_http_client = AsyncMock()
    mock_http_client.get.side_effect = [
        httpx.HTTPError("Connection error"),
        success_response,
    ]

    with patch("httpx.AsyncClient") as mock_client_class, patch(
        "asyncio.sleep", new_callable=AsyncMock
    ):
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        result = await client_instance._wait_for_tan_confirmation(
            "/auth/url", max_attempts=5, delay=0.1
        )

        assert result["status"] == "AUTHENTICATED"
        assert mock_http_client.get.call_count == 2


@pytest.mark.asyncio
async def test_wait_for_tan_unexpected_status_raises_error(client_instance):
    """Test TAN polling raises error on unexpected status."""
    client_instance.primary_access_token = "token"
    client_instance.session_id = "session123"

    unknown_response = MagicMock()
    unknown_response.status_code = 200
    unknown_response.json.return_value = {"status": "UNKNOWN"}

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = unknown_response

    with patch("httpx.AsyncClient") as mock_client_class, patch(
        "asyncio.sleep", new_callable=AsyncMock
    ):
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        with pytest.raises(ValueError, match="Unexpected TAN status: UNKNOWN"):
            await client_instance._wait_for_tan_confirmation(
                "/auth/url", max_attempts=5, delay=0.1
            )

        # Should fail immediately on first attempt
        assert mock_http_client.get.call_count == 1
