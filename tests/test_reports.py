"""
Unit tests for ComdirectClient Reports and single-account balance operations.

Tests cover:
- get_account_balance() — single account by ID
- get_all_balances() — aggregated product balances (Reports API)
- revoke_access_token() — token revocation
"""

import time
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ==================== get_account_balance ====================

@pytest.mark.asyncio
async def test_get_account_balance_success(client_instance):
    """Test successful single account balance retrieval."""
    client_instance.banking_access_token = "banking_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() + 3600

    mock_response_data = {
        "account": {
            "accountId": "account_abc",
            "accountDisplayId": "1234567890",
            "currency": "EUR",
            "clientId": "client_123",
            "accountType": {"key": "GIRO", "text": "Girokonto"},
            "iban": "DE12345678901234567890",
            "bic": "COBADEFFXXX",
            "creditLimit": {"value": 0, "unit": "EUR"},
        },
        "accountId": "account_abc",
        "balance": {"value": "2500.00", "unit": "EUR"},
        "balanceEUR": {"value": "2500.00", "unit": "EUR"},
        "availableCashAmount": {"value": "2500.00", "unit": "EUR"},
        "availableCashAmountEUR": {"value": "2500.00", "unit": "EUR"},
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        result = await client_instance.get_account_balance("account_abc")

        assert result.account_id == "account_abc"
        assert result.balance.value == Decimal("2500.00")
        assert result.balance.unit == "EUR"

        called_url = mock_http_client.get.call_args[1]["url"]
        assert "account_abc" in called_url


@pytest.mark.asyncio
async def test_get_account_balance_no_token(client_instance):
    """Test single account balance retrieval without banking token."""
    client_instance.banking_access_token = None

    with pytest.raises(ValueError, match="No banking access token available"):
        await client_instance.get_account_balance("account_abc")


# ==================== get_all_balances ====================

@pytest.mark.asyncio
async def test_get_all_balances_success(client_instance):
    """Test successful all-balances retrieval."""
    client_instance.banking_access_token = "banking_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() + 3600

    mock_response_data = {
        "paging": {"index": 0, "matches": 2},
        "aggregated": {
            "balanceEUR": {"value": "190000.00", "unit": "EUR"},
            "availableCashAmountEUR": {"value": "190000.00", "unit": "EUR"},
        },
        "values": [
            {
                "productId": "product_uuid_1",
                "productType": "ACCOUNT",
                "targetClientId": "client_123",
                "clientConnectionType": "CURRENT_CLIENT",
                "balance": {
                    "account": {
                        "accountId": "account_abc",
                        "accountDisplayId": "1234567890",
                        "currency": "EUR",
                        "clientId": "client_123",
                        "accountType": {"key": "GIRO", "text": "Girokonto"},
                        "iban": "DE12345678901234567890",
                        "bic": "COBADEFFXXX",
                        "creditLimit": {"value": 0, "unit": "EUR"},
                    },
                    "accountId": "account_abc",
                    "balance": {"value": "106.03", "unit": "EUR"},
                    "balanceEUR": {"value": "106.03", "unit": "EUR"},
                    "availableCashAmount": {"value": "106.03", "unit": "EUR"},
                    "availableCashAmountEUR": {"value": "106.03", "unit": "EUR"},
                },
            },
            {
                "productId": "product_uuid_2",
                "productType": "DEPOT",
                "targetClientId": "client_123",
                "clientConnectionType": "CURRENT_CLIENT",
                "balance": None,
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

        result = await client_instance.get_all_balances()

        assert result.paging.matches == 2
        assert len(result.values) == 2
        assert result.values[0].product_type == "ACCOUNT"
        assert result.values[1].product_type == "DEPOT"
        assert result.aggregated is not None


@pytest.mark.asyncio
async def test_get_all_balances_with_product_type_filter(client_instance):
    """Test that product_type filter is passed as query parameter."""
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

        await client_instance.get_all_balances(product_type="ACCOUNT,DEPOT")

        call_kwargs = mock_http_client.get.call_args[1]
        assert call_kwargs["params"]["productType"] == "ACCOUNT,DEPOT"


@pytest.mark.asyncio
async def test_get_all_balances_no_token(client_instance):
    """Test all-balances retrieval without banking token."""
    client_instance.banking_access_token = None

    with pytest.raises(ValueError, match="No banking access token available"):
        await client_instance.get_all_balances()


# ==================== revoke_access_token ====================

@pytest.mark.asyncio
async def test_revoke_access_token_success(client_instance):
    """Test successful token revocation."""
    client_instance.banking_access_token = "banking_token"
    client_instance.primary_access_token = "primary_token"
    client_instance.refresh_token = "refresh_token"
    client_instance.token_expires_at = time.time() + 3600

    mock_response = MagicMock()
    mock_response.status_code = 204
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.delete.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        await client_instance.revoke_access_token()

        mock_http_client.delete.assert_called_once()
        called_url = mock_http_client.delete.call_args[0][0]
        assert "revoke" in called_url

    # Tokens should be cleared after revocation
    assert client_instance.banking_access_token == ""
    assert client_instance.primary_access_token == ""
    assert client_instance.refresh_token == ""
    assert client_instance.token_expires_at == 0.0


@pytest.mark.asyncio
async def test_revoke_access_token_no_token(client_instance):
    """Test token revocation without any token."""
    client_instance.banking_access_token = None
    client_instance.primary_access_token = None

    with pytest.raises(ValueError, match="No access token available"):
        await client_instance.revoke_access_token()
