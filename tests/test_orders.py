"""
Unit tests for ComdirectClient orders operations.

Tests cover:
- Depot orders retrieval (list with filters)
- Single order retrieval by ID
- Automatic token refresh on expiry
- Missing token validation
"""

import time
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from comdirect_api.models import Order, Orders

# ---------------------------------------------------------------------------
# Fixtures (shared mock responses)
# ---------------------------------------------------------------------------

SAMPLE_ORDER = {
    "orderId": "order_abc123",
    "depotId": "depot_123",
    "orderType": "LIMIT",
    "orderStatus": "OPEN",
    "side": "BUY",
    "instrumentId": "DE0005428007",
    "venueId": "venue_uuid_001",
    "quantity": {"value": "10", "unit": "XXC"},
    "openQuantity": {"value": "10", "unit": "XXC"},
    "limit": {"value": "50.00", "unit": "EUR"},
    "validityType": "GFD",
    "creationTimestamp": "2026-03-19T10:00:00,000000+01",
    "bestEx": False,
    "executions": [],
}

SAMPLE_ORDERS_LIST = {
    "paging": {"index": 0, "matches": 1},
    "values": [SAMPLE_ORDER],
}


# ---------------------------------------------------------------------------
# get_depot_orders
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_depot_orders_success(client_instance):
    """Test successful retrieval of orders for a depot."""
    client_instance.banking_access_token = "banking_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() + 3600

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_ORDERS_LIST
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        result = await client_instance.get_depot_orders(depot_id="depot_123")

        assert isinstance(result, Orders)
        assert len(result.values) == 1
        order = result.values[0]
        assert order.order_id == "order_abc123"
        assert order.order_type == "LIMIT"
        assert order.order_status == "OPEN"
        assert order.side == "BUY"
        assert order.limit.value == Decimal("50.00")
        assert order.limit.unit == "EUR"


@pytest.mark.asyncio
async def test_get_depot_orders_empty(client_instance):
    """Test retrieval when no orders exist."""
    client_instance.banking_access_token = "banking_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() + 3600

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"paging": {"index": 0, "matches": 0}, "values": []}
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        result = await client_instance.get_depot_orders(depot_id="depot_123")

        assert result.values == []


@pytest.mark.asyncio
async def test_get_depot_orders_with_filters(client_instance):
    """Test that filters are passed as correct query parameters."""
    client_instance.banking_access_token = "banking_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() + 3600

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"paging": {"index": 0, "matches": 0}, "values": []}
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        result = await client_instance.get_depot_orders(
            depot_id="depot_123",
            with_attr="instrument",
            without_attr="executions",
            isin="DE0005428007",
            wkn="542800",
            order_status="OPEN",
            order_type="LIMIT",
            side="BUY",
            venue_id="venue_uuid_001",
            min_creation_timestamp="2026-01-01T00:00:00,000000+01",
            max_creation_timestamp="2026-03-31T23:59:59,999999+01",
        )

        call_args = mock_http_client.get.call_args
        params = call_args.kwargs["params"]
        assert params["with-attr"] == "instrument"
        assert params["without-attr"] == "executions"
        assert params["isin"] == "DE0005428007"
        assert params["wkn"] == "542800"
        assert params["orderStatus"] == "OPEN"
        assert params["orderType"] == "LIMIT"
        assert params["side"] == "BUY"
        assert params["venueId"] == "venue_uuid_001"
        assert params["min-creationTimeStamp"] == "2026-01-01T00:00:00,000000+01"
        assert params["max-creationTimeStamp"] == "2026-03-31T23:59:59,999999+01"


@pytest.mark.asyncio
async def test_get_depot_orders_url(client_instance):
    """Test that the correct URL is called."""
    client_instance.banking_access_token = "banking_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() + 3600

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"paging": {"index": 0, "matches": 0}, "values": []}
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        await client_instance.get_depot_orders(depot_id="depot_abc")

        call_args = mock_http_client.get.call_args
        assert "brokerage/depots/depot_abc/v3/orders" in call_args.kwargs["url"]


@pytest.mark.asyncio
async def test_get_depot_orders_no_token(client_instance):
    """Test that ValueError is raised when banking token is missing."""
    client_instance.banking_access_token = None

    with pytest.raises(ValueError, match="No banking access token"):
        await client_instance.get_depot_orders(depot_id="depot_123")


@pytest.mark.asyncio
async def test_get_depot_orders_token_refresh(client_instance):
    """Test that expired token is refreshed before making the request."""
    client_instance.banking_access_token = "old_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() - 1  # expired

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"paging": {"index": 0, "matches": 0}, "values": []}
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client
        with patch.object(
            client_instance, "refresh_access_token", new_callable=AsyncMock
        ) as mock_refresh:
            await client_instance.get_depot_orders(depot_id="depot_123")
            mock_refresh.assert_called_once()


# ---------------------------------------------------------------------------
# get_order
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_order_success(client_instance):
    """Test successful retrieval of a single order."""
    client_instance.banking_access_token = "banking_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() + 3600

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_ORDER
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        result = await client_instance.get_order(order_id="order_abc123")

        assert isinstance(result, Order)
        assert result.order_id == "order_abc123"
        assert result.order_status == "OPEN"
        assert result.quantity.value == Decimal("10")
        assert result.quantity.unit == "XXC"


@pytest.mark.asyncio
async def test_get_order_without_attr(client_instance):
    """Test that without-attr parameter is passed correctly."""
    client_instance.banking_access_token = "banking_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() + 3600

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_ORDER
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        await client_instance.get_order(order_id="order_abc123", without_attr="executions")

        call_args = mock_http_client.get.call_args
        assert call_args.kwargs["params"]["without-attr"] == "executions"


@pytest.mark.asyncio
async def test_get_order_url(client_instance):
    """Test that the correct URL is called."""
    client_instance.banking_access_token = "banking_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() + 3600

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_ORDER
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        await client_instance.get_order(order_id="order_abc123")

        call_args = mock_http_client.get.call_args
        assert "brokerage/v3/orders/order_abc123" in call_args.kwargs["url"]


@pytest.mark.asyncio
async def test_get_order_no_token(client_instance):
    """Test that ValueError is raised when banking token is missing."""
    client_instance.banking_access_token = None

    with pytest.raises(ValueError, match="No banking access token"):
        await client_instance.get_order(order_id="order_abc123")


@pytest.mark.asyncio
async def test_get_order_token_refresh(client_instance):
    """Test that expired token is refreshed before making the request."""
    client_instance.banking_access_token = "old_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() - 1  # expired

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_ORDER
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client
        with patch.object(
            client_instance, "refresh_access_token", new_callable=AsyncMock
        ) as mock_refresh:
            await client_instance.get_order(order_id="order_abc123")
            mock_refresh.assert_called_once()


# ---------------------------------------------------------------------------
# Order model validation
# ---------------------------------------------------------------------------


def test_order_model_with_executions():
    """Test Order model parses executions list correctly."""
    data = {
        "orderId": "ord_001",
        "orderStatus": "EXECUTED",
        "executedQuantity": {"value": "10", "unit": "XXC"},
        "executions": [
            {
                "executionId": "exec_001",
                "executionNumber": 1,
                "executedQuantity": {"value": "10", "unit": "XXC"},
                "executionPrice": {"value": "52.50", "unit": "EUR"},
                "executionTimestamp": "2026-03-19T11:00:00,000000+01",
            }
        ],
    }
    order = Order(**data)
    assert order.order_id == "ord_001"
    assert len(order.executions) == 1
    assert order.executions[0].execution_id == "exec_001"
    assert order.executions[0].execution_price.value == Decimal("52.50")


def test_order_model_market_order():
    """Test Order model for a market order (no limit)."""
    data = {
        "orderId": "ord_002",
        "orderType": "MARKET",
        "orderStatus": "OPEN",
        "side": "SELL",
        "quantity": {"value": "5", "unit": "XXC"},
    }
    order = Order(**data)
    assert order.order_type == "MARKET"
    assert order.limit is None
    assert order.side == "SELL"


def test_orders_model_empty_values_default():
    """Test that Orders.values defaults to empty list."""
    orders = Orders()
    assert orders.values == []
