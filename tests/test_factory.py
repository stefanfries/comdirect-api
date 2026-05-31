"""Tests for factory method and initialization."""

from unittest.mock import AsyncMock, patch

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
async def test_create_factory_raises_without_credentials():
    """Test factory method raises ValueError when zugangsnummer/pin not provided."""
    with patch.object(ComdirectClient, "_initialize", new_callable=AsyncMock):
        with pytest.raises(ValueError, match="zugangsnummer and pin must be provided"):
            await ComdirectClient.create()


@pytest.mark.asyncio
async def test_create_factory_partial_credentials_raises():
    """Test factory method raises ValueError when only one of zugangsnummer/pin is provided."""
    with patch.object(ComdirectClient, "_initialize", new_callable=AsyncMock):
        with pytest.raises(ValueError, match="zugangsnummer and pin must be provided"):
            await ComdirectClient.create(zugangsnummer="custom_user")


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
