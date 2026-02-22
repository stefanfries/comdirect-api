"""Tests for TAN challenge initiation and flow."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_initiate_tan_challenge_success(client_instance):
    """Test successful TAN challenge initiation."""
    client_instance.session_id = "session123"
    client_instance.primary_access_token = "token"

    auth_info = {
        "id": "challenge123",
        "typ": "P_TAN_PUSH",
        "availableTypes": ["P_TAN_PUSH", "M_TAN"],
        "link": {"href": "/auth/challenge123"},
    }

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "challenge123"}
    mock_response.headers = {
        "x-once-authentication-info": json.dumps(auth_info)
    }
    mock_response.raise_for_status = MagicMock()

    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        result = await client_instance._initiate_tan_challenge()

        assert result["id"] == "challenge123"
        assert result["typ"] == "P_TAN_PUSH"
        assert result["auth_url"] == "/auth/challenge123"
        assert client_instance.challenge_id == "challenge123"
        assert client_instance.tan_type == "P_TAN_PUSH"
        assert "P_TAN_PUSH" in client_instance.available_tan_types


@pytest.mark.asyncio
async def test_initiate_tan_challenge_missing_header(client_instance):
    """Test error when x-once-authentication-info header is missing."""
    client_instance.session_id = "session123"
    client_instance.primary_access_token = "token"

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "challenge123"}
    mock_response.headers = {}  # Missing required header!
    mock_response.raise_for_status = MagicMock()

    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        with pytest.raises(ValueError, match="Missing 'x-once-authentication-info'"):
            await client_instance._initiate_tan_challenge()


@pytest.mark.asyncio
async def test_initiate_tan_challenge_invalid_json_header(client_instance):
    """Test error when auth header contains invalid JSON."""
    client_instance.session_id = "session123"
    client_instance.primary_access_token = "token"

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "challenge123"}
    mock_response.headers = {"x-once-authentication-info": "invalid json{"}
    mock_response.raise_for_status = MagicMock()

    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        with pytest.raises(ValueError, match="Invalid JSON"):
            await client_instance._initiate_tan_challenge()


@pytest.mark.asyncio
async def test_initiate_tan_challenge_missing_auth_url(client_instance):
    """Test error when authentication URL is missing from response."""
    client_instance.session_id = "session123"
    client_instance.primary_access_token = "token"

    auth_info = {
        "id": "challenge123",
        "typ": "P_TAN_PUSH",
        # Missing 'link' field!
    }

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "challenge123"}
    mock_response.headers = {
        "x-once-authentication-info": json.dumps(auth_info)
    }
    mock_response.raise_for_status = MagicMock()

    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        with pytest.raises(ValueError, match="Missing authentication URL"):
            await client_instance._initiate_tan_challenge()


@pytest.mark.asyncio
async def test_create_validate_session_tan_missing_challenge_id(client_instance):
    """Test error when TAN challenge doesn't return challenge ID."""
    client_instance.session_id = "session123"
    client_instance.primary_access_token = "token"

    auth_info = {
        # Missing 'id' field!
        "typ": "P_TAN_PUSH",
        "link": {"href": "/auth/url"},
    }

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {}
    mock_response.headers = {
        "x-once-authentication-info": json.dumps(auth_info)
    }
    mock_response.raise_for_status = MagicMock()

    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        with pytest.raises(ValueError, match="No challenge ID received"):
            await client_instance._create_validate_session_tan()


@pytest.mark.asyncio
async def test_create_validate_session_tan_unexpected_status(client_instance):
    """Test error when TAN confirmation returns unexpected status."""
    client_instance.session_id = "session123"
    client_instance.primary_access_token = "token"

    # Mock initiate_tan_challenge
    auth_info = {
        "id": "challenge123",
        "typ": "P_TAN_PUSH",
        "link": {"href": "/auth/url"},
        "auth_url": "/auth/url",
        "availableTypes": ["P_TAN_PUSH"],
    }

    initiate_response = MagicMock()
    initiate_response.status_code = 201
    initiate_response.json.return_value = auth_info
    initiate_response.headers = {
        "x-once-authentication-info": json.dumps(auth_info)
    }
    initiate_response.raise_for_status = MagicMock()

    # Mock wait_for_tan_confirmation with unexpected status
    wait_response = MagicMock()
    wait_response.status_code = 200
    wait_response.json.return_value = {"status": "FAILED"}

    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = initiate_response
    mock_http_client.get.return_value = wait_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        with pytest.raises(ValueError, match="Unexpected TAN status"):
            await client_instance._create_validate_session_tan()
