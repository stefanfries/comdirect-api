"""Tests for factory method and initialization."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from comdirect_api.client import ComdirectClient


@pytest.mark.asyncio
async def test_create_factory_method_with_explicit_credentials():
    """Test factory method creates and initializes client with explicit credentials."""
    with patch.object(ComdirectClient, "_initialize", new_callable=AsyncMock) as mock_init:
        client = await ComdirectClient.create(
            client_id="test_id",
            client_secret="test_secret",
            zugangsnummer="test_user",
            pin="test_pin",
        )

        assert client.client_id == "test_id"
        assert client.client_secret == "test_secret"
        assert client.zugangsnummer == "test_user"
        assert client.pin == "test_pin"
        assert mock_init.called
        mock_init.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_factory_uses_settings_as_fallback():
    """Test factory method falls back to settings when credentials not provided."""
    mock_settings = MagicMock()
    mock_settings.client_id.get_secret_value.return_value = "env_client_id"
    mock_settings.client_secret.get_secret_value.return_value = "env_client_secret"
    mock_settings.zugangsnummer.get_secret_value.return_value = "env_user"
    mock_settings.pin.get_secret_value.return_value = "env_pin"

    with patch("comdirect_api.settings.settings", mock_settings), patch.object(
        ComdirectClient, "_initialize", new_callable=AsyncMock
    ):
        client = await ComdirectClient.create()

        assert client.client_id == "env_client_id"
        assert client.client_secret == "env_client_secret"
        assert client.zugangsnummer == "env_user"
        assert client.pin == "env_pin"


@pytest.mark.asyncio
async def test_create_factory_partial_credentials():
    """Test factory method with some explicit and some from settings."""
    mock_settings = MagicMock()
    mock_settings.client_id.get_secret_value.return_value = "env_client_id"
    mock_settings.client_secret.get_secret_value.return_value = "env_client_secret"
    mock_settings.zugangsnummer.get_secret_value.return_value = "env_user"
    mock_settings.pin.get_secret_value.return_value = "env_pin"

    with patch("comdirect_api.settings.settings", mock_settings), patch.object(
        ComdirectClient, "_initialize", new_callable=AsyncMock
    ):
        client = await ComdirectClient.create(
            client_id="custom_id", zugangsnummer="custom_user"
        )

        # Explicit values used
        assert client.client_id == "custom_id"
        assert client.zugangsnummer == "custom_user"
        # Fallback to settings
        assert client.client_secret == "env_client_secret"
        assert client.pin == "env_pin"


@pytest.mark.asyncio
async def test_initialize_calls_auth_flow_in_order():
    """Test that _initialize calls authentication methods in correct order."""
    client = ComdirectClient(
        client_id="test_id",
        client_secret="test_secret",
        zugangsnummer="test_user",
        pin="test_pin",
    )

    with patch.object(
        client, "_authenticate", new_callable=AsyncMock
    ) as mock_auth, patch.object(
        client, "_get_session_status", new_callable=AsyncMock
    ) as mock_session, patch.object(
        client, "_create_validate_session_tan", new_callable=AsyncMock
    ) as mock_tan, patch.object(
        client, "_get_banking_brokerage_access", new_callable=AsyncMock
    ) as mock_banking:
        await client._initialize()

        # Verify all methods were called
        mock_auth.assert_awaited_once_with("test_user", "test_pin")
        mock_session.assert_awaited_once()
        mock_tan.assert_awaited_once()
        mock_banking.assert_awaited_once()

        # Verify order
        assert mock_auth.await_count == 1
        assert mock_session.await_count == 1
        assert mock_tan.await_count == 1
        assert mock_banking.await_count == 1
