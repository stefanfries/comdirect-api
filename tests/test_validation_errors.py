"""Tests for error validations and edge cases."""

import pytest


@pytest.mark.asyncio
async def test_create_validate_session_tan_no_session_id(client_instance):
    """Test TAN validation fails without session ID."""
    client_instance.session_id = None
    client_instance.primary_access_token = "token"

    with pytest.raises(ValueError, match="No session ID available"):
        await client_instance._create_validate_session_tan()


@pytest.mark.asyncio
async def test_create_validate_session_tan_no_token(client_instance):
    """Test TAN validation fails without access token."""
    client_instance.session_id = "session123"
    client_instance.primary_access_token = None

    with pytest.raises(ValueError, match="No access token available"):
        await client_instance._create_validate_session_tan()


@pytest.mark.asyncio
async def test_activate_session_tan_no_session_id(client_instance):
    """Test session TAN activation fails without session ID."""
    client_instance.session_id = None
    client_instance.primary_access_token = "token"

    with pytest.raises(ValueError, match="No session ID available"):
        await client_instance._activate_session_tan("challenge123")


@pytest.mark.asyncio
async def test_activate_session_tan_no_token(client_instance):
    """Test session TAN activation fails without access token."""
    client_instance.session_id = "session123"
    client_instance.primary_access_token = None

    with pytest.raises(ValueError, match="No access token available"):
        await client_instance._activate_session_tan("challenge123")


@pytest.mark.asyncio
async def test_initiate_tan_challenge_no_session_id(client_instance):
    """Test TAN challenge initiation fails without session ID."""
    client_instance.session_id = None
    client_instance.primary_access_token = "token"

    with pytest.raises(ValueError, match="No session ID available"):
        await client_instance._initiate_tan_challenge()


@pytest.mark.asyncio
async def test_initiate_tan_challenge_no_token(client_instance):
    """Test TAN challenge initiation fails without access token."""
    client_instance.session_id = "session123"
    client_instance.primary_access_token = None

    with pytest.raises(ValueError, match="No access token available"):
        await client_instance._initiate_tan_challenge()


@pytest.mark.asyncio
async def test_wait_for_tan_confirmation_no_token(client_instance):
    """Test TAN confirmation wait fails without access token."""
    client_instance.primary_access_token = None

    with pytest.raises(ValueError, match="No access token available"):
        await client_instance._wait_for_tan_confirmation("/auth/url")


@pytest.mark.asyncio
async def test_get_session_status_no_token(client_instance):
    """Test session status retrieval fails without primary token."""
    client_instance.primary_access_token = None

    with pytest.raises(ValueError, match="No access token available"):
        await client_instance._get_session_status()


@pytest.mark.asyncio
async def test_get_banking_brokerage_access_no_primary_token(client_instance):
    """Test banking access fails without primary token."""
    client_instance.primary_access_token = None

    with pytest.raises(ValueError, match="No base access token available"):
        await client_instance._get_banking_brokerage_access()


@pytest.mark.asyncio
async def test_refresh_access_token_no_refresh_token(client_instance):
    """Test token refresh fails without refresh token."""
    client_instance.refresh_token = None

    with pytest.raises(ValueError, match="No refresh token available"):
        await client_instance.refresh_access_token()


@pytest.mark.asyncio
async def test_get_account_balances_no_banking_token(client_instance):
    """Test account balances fails without banking token."""
    client_instance.banking_access_token = None

    with pytest.raises(ValueError, match="No banking access token available"):
        await client_instance.get_account_balances()


@pytest.mark.asyncio
async def test_get_account_transactions_no_banking_token(client_instance):
    """Test account transactions fails without banking token."""
    client_instance.banking_access_token = None

    with pytest.raises(ValueError, match="No banking access token available"):
        await client_instance.get_account_transactions(account_id="acc123")


@pytest.mark.asyncio
async def test_get_account_depots_no_banking_token(client_instance):
    """Test depot retrieval fails without banking token."""
    client_instance.banking_access_token = None

    with pytest.raises(ValueError, match="No banking access token available"):
        await client_instance.get_account_depots()


@pytest.mark.asyncio
async def test_get_depot_positions_no_banking_token(client_instance):
    """Test depot positions fails without banking token."""
    client_instance.banking_access_token = None

    with pytest.raises(ValueError, match="No banking access token available"):
        await client_instance.get_depot_positions(depot_id="depot123")


@pytest.mark.asyncio
async def test_get_depot_transactions_no_banking_token(client_instance):
    """Test depot transactions fails without banking token."""
    client_instance.banking_access_token = None

    with pytest.raises(ValueError, match="No banking access token available"):
        await client_instance.get_depot_transactions(depot_id="depot123")


@pytest.mark.asyncio
async def test_get_instrument_no_banking_token(client_instance):
    """Test instrument retrieval fails without banking token."""
    client_instance.banking_access_token = None

    with pytest.raises(ValueError, match="No banking access token available"):
        await client_instance.get_instrument(instrument_id="inst123")
