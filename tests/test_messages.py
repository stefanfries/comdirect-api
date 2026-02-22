"""
Unit tests for ComdirectClient messages operations.

Tests cover:
- Document list retrieval with pagination
- Document download
- Predocument download
- Error handling for missing tokens
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_documents_success(client_instance):
    """Test successful document list retrieval."""
    client_instance.banking_access_token = "banking_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() + 3600  # Valid token

    mock_response_data = {
        "paging": {"index": 0, "matches": 2},
        "values": [
            {
                "documentId": "doc_123",
                "name": "Account Statement January 2024",
                "dateCreation": "2024-01-31",
                "mimeType": "application/pdf",
                "deletable": False,
                "advertisement": False,
                "documentMetaData": {
                    "archived": False,
                    "alreadyRead": True,
                    "dateRead": "2024-02-01",
                    "predocumentExists": False,
                },
            },
            {
                "documentId": "doc_456",
                "name": "Trade Confirmation",
                "dateCreation": "2024-02-15",
                "mimeType": "application/pdf",
                "deletable": True,
                "advertisement": False,
                "documentMetaData": {
                    "archived": False,
                    "alreadyRead": False,
                    "predocumentExists": True,
                },
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

        result = await client_instance.get_documents()

        assert result.paging["index"] == 0
        assert result.paging["matches"] == 2
        assert len(result.values) == 2
        assert result.values[0].document_id == "doc_123"
        assert result.values[0].name == "Account Statement January 2024"
        assert result.values[0].mime_type == "application/pdf"
        assert result.values[0].document_meta_data.already_read is True
        assert result.values[1].document_id == "doc_456"
        assert result.values[1].document_meta_data.predocument_exists is True


@pytest.mark.asyncio
async def test_get_documents_with_pagination(client_instance):
    """Test document list retrieval with custom pagination."""
    client_instance.banking_access_token = "banking_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() + 3600

    mock_response_data = {
        "paging": {"index": 10, "matches": 100},
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

        _ = await client_instance.get_documents(
            paging_first=10, paging_count=50
        )

        # Verify the request was made with correct parameters
        call_args = mock_http_client.get.call_args
        assert call_args.kwargs["params"]["paging-first"] == 10
        assert call_args.kwargs["params"]["paging-count"] == 50


@pytest.mark.asyncio
async def test_get_documents_max_count_limit(client_instance):
    """Test that paging_count is capped at API maximum of 1000."""
    client_instance.banking_access_token = "banking_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() + 3600

    mock_response_data = {"paging": {"index": 0, "matches": 0}, "values": []}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        await client_instance.get_documents(paging_count=5000)

        # Verify the count was capped at 1000
        call_args = mock_http_client.get.call_args
        assert call_args.kwargs["params"]["paging-count"] == 1000


@pytest.mark.asyncio
async def test_get_documents_no_token(client_instance):
    """Test document retrieval without banking token."""
    client_instance.banking_access_token = None

    with pytest.raises(ValueError, match="No banking access token available"):
        await client_instance.get_documents()


@pytest.mark.asyncio
async def test_get_document_success(client_instance):
    """Test successful document download."""
    client_instance.banking_access_token = "banking_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() + 3600

    # Mock PDF content
    mock_pdf_content = b"%PDF-1.4\n%mock pdf content"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = mock_pdf_content
    mock_response.headers = {"content-type": "application/pdf"}
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        result = await client_instance.get_document("doc_123")

        assert result == mock_pdf_content
        assert isinstance(result, bytes)


@pytest.mark.asyncio
async def test_get_document_no_token(client_instance):
    """Test document download without banking token."""
    client_instance.banking_access_token = None

    with pytest.raises(ValueError, match="No banking access token available"):
        await client_instance.get_document("doc_123")


@pytest.mark.asyncio
async def test_get_predocument_success(client_instance):
    """Test successful predocument download."""
    client_instance.banking_access_token = "banking_token"
    client_instance.session_id = "session_123"
    client_instance.token_expires_at = time.time() + 3600

    mock_html_content = b"<html><body>Predocument preview</body></html>"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = mock_html_content
    mock_response.headers = {"content-type": "text/html"}
    mock_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        result = await client_instance.get_predocument("doc_456")

        assert result == mock_html_content
        assert isinstance(result, bytes)


@pytest.mark.asyncio
async def test_get_predocument_no_token(client_instance):
    """Test predocument download without banking token."""
    client_instance.banking_access_token = None

    with pytest.raises(ValueError, match="No banking access token available"):
        await client_instance.get_predocument("doc_456")


@pytest.mark.asyncio
async def test_get_documents_with_token_refresh(client_instance):
    """Test document retrieval with automatic token refresh."""
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

    # Mock documents response
    mock_documents_data = {"paging": {"index": 0, "matches": 0}, "values": []}

    mock_documents_response = MagicMock()
    mock_documents_response.status_code = 200
    mock_documents_response.json.return_value = mock_documents_data
    mock_documents_response.raise_for_status.return_value = None

    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_refresh_response
    mock_http_client.get.return_value = mock_documents_response

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_http_client

        _ = await client_instance.get_documents()

        # Verify refresh was called
        mock_http_client.post.assert_called_once()
        # Verify documents endpoint was called
        mock_http_client.get.assert_called_once()
