"""
Unit tests for ComdirectClient banking operations.

Tests cover:
- Account balance retrieval
- Account transaction retrieval with filters
- Automatic token refresh on expiry
"""

import time
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_account_balances_success(client_instance):
    """Test successful account balance retrieval."""
    client_instance.banking_access_token = "banking_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() + 3600  # Valid token

    mock_response_data = {
        "paging": {"index": 0, "matches": 1},
        "values": [
            {
                "account": {
                    "accountId": "account_123",
                    "accountDisplayId": "1234567890",
                    "currency": "EUR",
                    "clientId": "client_123",
                    "accountType": {"key": "GIRO", "text": "Girokonto"},
                    "iban": "DE12345678901234567890",
                    "bic": "COBADEFFXXX",
                    "creditLimit": {"value": 0, "unit": "EUR"},
                },
                "accountId": "account_123",
                "balance": {"value": 1000.50, "unit": "EUR"},
                "balanceEUR": {"value": 1000.50, "unit": "EUR"},
                "availableCashAmount": {"value": 1000.50, "unit": "EUR"},
                "availableCashAmountEUR": {"value": 1000.50, "unit": "EUR"},
            }
        ],
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        result = await client_instance.get_account_balances()

        assert result.paging.index == 0
        assert result.paging.matches == 1
        assert len(result.values) == 1
        assert result.values[0].account_id == "account_123"
        assert result.values[0].balance.value == Decimal("1000.50")


@pytest.mark.asyncio
async def test_get_account_balances_no_token(client_instance):
    """Test account balance retrieval without banking token."""
    client_instance.banking_access_token = None
    client_instance.token_expires_at = time.time() + 3600  # Valid token time

    with pytest.raises(ValueError, match="No banking access token available"):
        await client_instance.get_account_balances()


@pytest.mark.asyncio
async def test_get_account_balances_with_refresh(client_instance):
    """Test account balance retrieval with automatic token refresh."""
    client_instance.banking_access_token = "old_token"
    client_instance.refresh_token = "refresh_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() - 100  # Expired token

    # Mock refresh response
    mock_refresh_data = {
        "access_token": "new_token",
        "refresh_token": "new_refresh_token",
        "expires_in": 3600,
    }

    mock_refresh_response = MagicMock()
    mock_refresh_response.status_code = 200
    mock_refresh_response.json.return_value = mock_refresh_data
    mock_refresh_response.raise_for_status.return_value = None

    # Mock balances response
    mock_balances_data = {
        "paging": {"index": 0, "matches": 0},
        "values": [],
    }

    mock_balances_response = MagicMock()
    mock_balances_response.status_code = 200
    mock_balances_response.json.return_value = mock_balances_data
    mock_balances_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_refresh_response
    mock_http_client.get.return_value = mock_balances_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        _ = await client_instance.get_account_balances()

        # Verify token was refreshed
        mock_http_client.post.assert_called_once()
        # Verify balances were retrieved
        mock_http_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_account_transactions_success(client_instance):
    """Test successful account transaction retrieval."""
    client_instance.banking_access_token = "banking_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() + 3600

    mock_response_data = {
        "paging": {"index": 0, "matches": 2},
        "values": [
            {
                "bookingStatus": "BOOKED",
                "bookingDate": "2026-02-20",
                "valutaDate": "2026-02-20",
                "amount": {"value": 100.00, "unit": "EUR"},
                "remittanceInfo": "Payment 1",
                "transactionType": {"key": "CREDIT", "text": "Gutschrift"},
            },
            {
                "bookingStatus": "BOOKED",
                "bookingDate": "2026-02-19",
                "valutaDate": "2026-02-19",
                "amount": {"value": -50.00, "unit": "EUR"},
                "remittanceInfo": "Payment 2",
                "transactionType": {"key": "DEBIT", "text": "Belastung"},
            },
        ],
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        result = await client_instance.get_account_transactions(
            account_id="account_123",
            transaction_state="BOOKED",
            transaction_direction="CREDIT_AND_DEBIT",
        )

        assert result.paging["matches"] == 2
        assert len(result.values) == 2


@pytest.mark.asyncio
async def test_get_account_transactions_with_filters(client_instance):
    """Test account transaction retrieval with filters."""
    client_instance.banking_access_token = "banking_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() + 3600

    mock_response_data = {
        "paging": {"index": 0, "matches": 0},
        "values": [],
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        _ = await client_instance.get_account_transactions(
            account_id="account_123",
            transaction_state="NOTBOOKED",
            transaction_direction="CREDIT",
            paging_first=10,
            with_attr="account",
        )

        # Verify the request was made with correct parameters
        call_args = mock_http_client.get.call_args
        assert call_args.kwargs["params"]["transactionState"] == "NOTBOOKED"
        assert call_args.kwargs["params"]["transactionDirection"] == "CREDIT"
        assert call_args.kwargs["params"]["paging-first"] == 10
        assert call_args.kwargs["params"]["with-attr"] == "account"


@pytest.mark.asyncio
async def test_get_account_transactions_no_token(client_instance):
    """Test account transaction retrieval without banking token."""
    client_instance.banking_access_token = None
    client_instance.token_expires_at = time.time() + 3600  # Valid token time

    with pytest.raises(ValueError, match="No banking access token available"):
        await client_instance.get_account_transactions(account_id="account_123")
