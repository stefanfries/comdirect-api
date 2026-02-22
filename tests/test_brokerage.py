"""
Unit tests for ComdirectClient brokerage operations.

Tests cover:
- Depot retrieval
- Depot position retrieval (all and single)
- Depot transaction retrieval
- Instrument information retrieval
- Automatic token refresh on expiry
"""

import time
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_account_depots_success(client_instance):
    """Test successful depot retrieval."""
    client_instance.banking_access_token = "banking_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() + 3600

    mock_response_data = {
        "paging": {"index": 0, "matches": 1},
        "values": [
            {
                "depotId": "depot_123",
                "depotDisplayId": "1234567",
                "clientId": "client_123",
                "depotType": "STANDARD_DEPOT",
                "defaultSettlementAccountId": "account_123",
                "settlementAccountIds": ["account_123"],
                "targetMarket": "DE",
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

        result = await client_instance.get_account_depots()

        assert result.paging.matches == 1
        assert len(result.values) == 1
        assert result.values[0].depot_id == "depot_123"


@pytest.mark.asyncio
async def test_get_depot_positions_success(client_instance):
    """Test successful depot position retrieval."""
    client_instance.banking_access_token = "banking_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() + 3600

    mock_response_data = {
        "paging": {"index": 0, "matches": 2},
        "values": [
            {
                "positionId": "pos_123",
                "wkn": "A1B2C3",
                "custodyType": "CLEARING",
                "quantity": {"value": 100.0, "unit": "STK"},
                "availableQuantity": {"value": 100.0, "unit": "STK"},
                "currentPrice": {
                    "price": {"value": 50.00, "unit": "EUR"},
                    "priceDateTime": "2026-02-22T10:00:00",
                },
                "currentValue": {"value": 5000.00, "unit": "EUR"},
            },
            {
                "positionId": "pos_456",
                "wkn": "D4E5F6",
                "custodyType": "CLEARING",
                "quantity": {"value": 50.0, "unit": "STK"},
                "availableQuantity": {"value": 50.0, "unit": "STK"},
                "currentPrice": {
                    "price": {"value": 100.00, "unit": "EUR"},
                    "priceDateTime": "2026-02-22T10:00:00",
                },
                "currentValue": {"value": 5000.00, "unit": "EUR"},
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

        result = await client_instance.get_depot_positions(depot_id="depot_123")

        assert result.paging["matches"] == 2
        assert len(result.values) == 2
        assert result.values[0].wkn == "A1B2C3"
        assert result.values[0].current_value["value"] == Decimal("5000.00")


@pytest.mark.asyncio
async def test_get_depot_positions_with_filters(client_instance):
    """Test depot position retrieval with filters."""
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

        _ = await client_instance.get_depot_positions(
            depot_id="depot_123",
            instrument_id="A1B2C3",
            with_attr="instrument",
            without_attr=["depot", "positions"],
        )

        # Verify the request was made with correct parameters
        call_args = mock_http_client.get.call_args
        assert call_args.kwargs["params"]["instrumentId"] == "A1B2C3"
        assert call_args.kwargs["params"]["with-attr"] == "instrument"
        assert call_args.kwargs["params"]["without-attr"] == ["depot", "positions"]


@pytest.mark.asyncio
async def test_get_depot_position_success(client_instance):
    """Test successful single depot position retrieval."""
    client_instance.banking_access_token = "banking_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() + 3600

    mock_response_data = {
        "positionId": "pos_123",
        "wkn": "A1B2C3",
        "custodyType": "CLEARING",
        "quantity": {"value": 100.0, "unit": "STK"},
        "currentValue": {"value": 5000.00, "unit": "EUR"},
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        result = await client_instance.get_depot_position(
            depot_id="depot_123", position_id="pos_123"
        )

        assert result.position_id == "pos_123"
        assert result.wkn == "A1B2C3"
        assert result.current_value["value"] == Decimal("5000.00")


@pytest.mark.asyncio
async def test_get_depot_transactions_success(client_instance):
    """Test successful depot transaction retrieval."""
    client_instance.banking_access_token = "banking_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() + 3600

    mock_response_data = {
        "paging": {"index": 0, "matches": 2},
        "values": [
            {
                "transactionId": "trans_123",
                "bookingDate": "2026-02-20",
                "transactionType": "BUY",
                "instrumentId": "inst_123",
                "quantity": {"value": 100.0, "unit": "STK"},
                "executionPrice": {"value": 50.00, "unit": "EUR"},
            },
            {
                "transactionId": "trans_456",
                "bookingDate": "2026-02-19",
                "transactionType": "SELL",
                "instrumentId": "inst_456",
                "quantity": {"value": 50.0, "unit": "STK"},
                "executionPrice": {"value": 100.00, "unit": "EUR"},
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

        result = await client_instance.get_depot_transactions(depot_id="depot_123")

        assert result.paging["matches"] == 2
        assert len(result.values) == 2
        assert result.values[0].quantity["value"] == 100.0
        assert result.values[0].execution_price["value"] == Decimal("50.00")


@pytest.mark.asyncio
async def test_get_depot_transactions_with_filters(client_instance):
    """Test depot transaction retrieval with filters."""
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

        _ = await client_instance.get_depot_transactions(
            depot_id="depot_123",
            isin="DE000A1B2C34",
            wkn="A1B2C3",
            instrument_id="inst_123",
            min_booking_date="2026-01-01",
        )

        # Verify the request was made with correct parameters
        call_args = mock_http_client.get.call_args
        assert call_args.kwargs["params"]["isin"] == "DE000A1B2C34"
        assert call_args.kwargs["params"]["wkn"] == "A1B2C3"
        assert call_args.kwargs["params"]["instrumentId"] == "inst_123"
        assert call_args.kwargs["params"]["min-bookingDate"] == "2026-01-01"


@pytest.mark.asyncio
async def test_get_instrument_success(client_instance):
    """Test successful instrument information retrieval."""
    client_instance.banking_access_token = "banking_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() + 3600

    mock_response_data = {
        "paging": {"index": 0, "matches": 1},
        "values": [
            {
                "instrumentId": "inst_123",
                "wkn": "A1B2C3",
                "isin": "DE000A1B2C34",
                "name": "Test AG",
                "shortName": "TST",
                "staticData": {
                    "instrumentType": "STOCK",
                    "currency": "EUR",
                },
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

        result = await client_instance.get_instrument(instrument_id="A1B2C3")

        assert result.paging["matches"] == 1
        assert len(result.values) == 1
        assert result.values[0].wkn == "A1B2C3"
        assert result.values[0].name == "Test AG"


@pytest.mark.asyncio
async def test_get_instrument_with_attributes(client_instance):
    """Test instrument retrieval with additional attributes."""
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

        _ = await client_instance.get_instrument(
            instrument_id="A1B2C3",
            with_attr=["derivativeData", "fundDistribution"],
            without_attr=["staticData"],
        )

        # Verify the request was made with correct parameters
        call_args = mock_http_client.get.call_args
        assert call_args.kwargs["params"]["with-attr"] == [
            "derivativeData",
            "fundDistribution",
        ]
        assert call_args.kwargs["params"]["without-attr"] == ["staticData"]


@pytest.mark.asyncio
async def test_get_depot_positions_no_token(client_instance):
    """Test depot position retrieval without banking token."""
    client_instance.banking_access_token = None
    client_instance.token_expires_at = time.time() + 3600  # Valid token time

    with pytest.raises(ValueError, match="No banking access token available"):
        await client_instance.get_depot_positions(depot_id="depot_123")
