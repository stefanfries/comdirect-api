"""Unit tests for SyncService — all external dependencies are mocked."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from functions.sync.sync_service import SyncService

# ---------------------------------------------------------------------------
# Helpers to build lightweight mock Pydantic-like objects
# ---------------------------------------------------------------------------

def _account_balance(account_id: str, value: Decimal, unit: str = "EUR", iban: str = "DE00"):
    account = MagicMock()
    account.account_id = account_id
    account.iban = iban
    account.account_type.text = "Girokonto"

    balance = MagicMock()
    balance.value = value
    balance.unit = unit

    ab = MagicMock()
    ab.account = account
    ab.balance = balance
    return ab


def _position(
    position_id: str,
    wkn: str,
    quantity: Decimal,
    current_value: Decimal,
    purchase_price: Decimal = Decimal("1.00"),
    isin: str = "DE000TEST001",
    instrument_name: str = "Test Instrument",
):
    pos = MagicMock()
    pos.position_id = position_id
    pos.wkn = wkn
    pos.quantity.value = quantity
    pos.quantity.unit = "XXX"
    pos.current_value.value = current_value
    pos.current_value.unit = "EUR"
    pos.purchase_price.value = purchase_price
    pos.purchase_price.unit = "EUR"
    pos.instrument.name = instrument_name
    pos.instrument.isin = isin
    return pos


def _transaction(
    transaction_id: str,
    wkn: str = "A1B2C3",
    quantity: Decimal = Decimal("1000"),
    execution_price: Decimal = Decimal("5.00"),
    booking_date: date = date(2026, 3, 1),
    transaction_type: str = "BUY",
):
    txn = MagicMock()
    txn.transaction_id = transaction_id
    txn.quantity.value = quantity
    txn.quantity.unit = "XXX"
    txn.execution_price.value = execution_price
    txn.execution_price.unit = "EUR"
    txn.booking_date = booking_date
    txn.transaction_type = transaction_type
    txn.instrument.wkn = wkn
    return txn


# ---------------------------------------------------------------------------
# sync_account_balances
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sync_balances_new_account_inserts():
    """First sync for an account — no existing doc — should insert."""
    client = AsyncMock()
    repo = MagicMock()

    ab = _account_balance("ACC1", Decimal("100.00"))
    client.get_account_balances.return_value = MagicMock(values=[ab])
    repo.get_latest_balance.return_value = None  # no existing doc

    service = SyncService(client, repo)
    result = await service.sync_account_balances()

    repo.insert_balance.assert_called_once_with(
        account_id="ACC1",
        iban="DE00",
        account_type="Girokonto",
        value=Decimal("100.00"),
        unit="EUR",
    )
    repo.touch_balance_last_synced.assert_not_called()
    assert result == {"inserted": 1, "touched": 0}


@pytest.mark.asyncio
async def test_sync_balances_unchanged_touches():
    """Balance unchanged — should only touch last_synced_at, not insert."""
    client = AsyncMock()
    repo = MagicMock()

    ab = _account_balance("ACC1", Decimal("100.00"))
    client.get_account_balances.return_value = MagicMock(values=[ab])
    repo.get_latest_balance.return_value = {"balance": {"value": "100.00"}}

    service = SyncService(client, repo)
    result = await service.sync_account_balances()

    repo.insert_balance.assert_not_called()
    repo.touch_balance_last_synced.assert_called_once_with("ACC1")
    assert result == {"inserted": 0, "touched": 1}


@pytest.mark.asyncio
async def test_sync_balances_changed_inserts():
    """Balance changed — should insert a new snapshot."""
    client = AsyncMock()
    repo = MagicMock()

    ab = _account_balance("ACC1", Decimal("200.00"))
    client.get_account_balances.return_value = MagicMock(values=[ab])
    repo.get_latest_balance.return_value = {"balance": {"value": "100.00"}}

    service = SyncService(client, repo)
    result = await service.sync_account_balances()

    repo.insert_balance.assert_called_once()
    repo.touch_balance_last_synced.assert_not_called()
    assert result == {"inserted": 1, "touched": 0}


@pytest.mark.asyncio
async def test_sync_balances_multiple_accounts():
    """Multiple accounts: one changed, one unchanged."""
    client = AsyncMock()
    repo = MagicMock()

    ab1 = _account_balance("ACC1", Decimal("100.00"))
    ab2 = _account_balance("ACC2", Decimal("500.00"))
    client.get_account_balances.return_value = MagicMock(values=[ab1, ab2])

    repo.get_latest_balance.side_effect = lambda acc_id: (
        {"balance": {"value": "100.00"}} if acc_id == "ACC1"
        else None
    )

    service = SyncService(client, repo)
    result = await service.sync_account_balances()

    assert result == {"inserted": 1, "touched": 1}


# ---------------------------------------------------------------------------
# sync_depot_positions (snapshot design)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sync_positions_no_snapshot_inserts():
    """No existing snapshot — should insert a new one."""
    client = AsyncMock()
    repo = MagicMock()

    pos = _position("POS1", "A1B2C3", Decimal("1000"), Decimal("5000.00"))
    client.get_depot_positions.return_value = MagicMock(values=[pos])
    repo.get_latest_depot_snapshot.return_value = None

    service = SyncService(client, repo)
    result = await service.sync_depot_positions("DEPOT1")

    repo.insert_depot_snapshot.assert_called_once()
    repo.touch_depot_last_synced.assert_not_called()
    assert result == {"inserted": 1, "touched": 0}


@pytest.mark.asyncio
async def test_sync_positions_unchanged_touches():
    """Depot composition unchanged — should only touch last_synced_at."""
    client = AsyncMock()
    repo = MagicMock()

    pos = _position("POS1", "A1B2C3", Decimal("1000"), Decimal("6000.00"))
    client.get_depot_positions.return_value = MagicMock(values=[pos])
    repo.get_latest_depot_snapshot.return_value = {
        "positions": [{"position_id": "POS1", "quantity": {"value": "1000"}}]
    }

    service = SyncService(client, repo)
    result = await service.sync_depot_positions("DEPOT1")

    repo.insert_depot_snapshot.assert_not_called()
    repo.touch_depot_last_synced.assert_called_once_with("DEPOT1")
    assert result == {"inserted": 0, "touched": 1}


@pytest.mark.asyncio
async def test_sync_positions_quantity_changed_inserts():
    """Quantity changed — should insert a new snapshot."""
    client = AsyncMock()
    repo = MagicMock()

    pos = _position("POS1", "A1B2C3", Decimal("2000"), Decimal("10000.00"))
    client.get_depot_positions.return_value = MagicMock(values=[pos])
    repo.get_latest_depot_snapshot.return_value = {
        "positions": [{"position_id": "POS1", "quantity": {"value": "1000"}}]
    }

    service = SyncService(client, repo)
    result = await service.sync_depot_positions("DEPOT1")

    repo.insert_depot_snapshot.assert_called_once()
    repo.touch_depot_last_synced.assert_not_called()
    assert result == {"inserted": 1, "touched": 0}


@pytest.mark.asyncio
async def test_sync_positions_new_position_inserts():
    """New position appeared — should insert a new snapshot."""
    client = AsyncMock()
    repo = MagicMock()

    pos1 = _position("POS1", "A1B2C3", Decimal("1000"), Decimal("5000.00"))
    pos2 = _position("POS2", "X9Y8Z7", Decimal("500"), Decimal("2000.00"))
    client.get_depot_positions.return_value = MagicMock(values=[pos1, pos2])
    repo.get_latest_depot_snapshot.return_value = {
        "positions": [{"position_id": "POS1", "quantity": {"value": "1000"}}]
    }

    service = SyncService(client, repo)
    result = await service.sync_depot_positions("DEPOT1")

    repo.insert_depot_snapshot.assert_called_once()
    assert result == {"inserted": 1, "touched": 0}


@pytest.mark.asyncio
async def test_sync_positions_sold_position_inserts():
    """Position sold (gone from API response) — should insert a new snapshot."""
    client = AsyncMock()
    repo = MagicMock()

    # API now returns only POS1; POS2 was previously in snapshot (fully sold)
    pos1 = _position("POS1", "A1B2C3", Decimal("1000"), Decimal("5000.00"))
    client.get_depot_positions.return_value = MagicMock(values=[pos1])
    repo.get_latest_depot_snapshot.return_value = {
        "positions": [
            {"position_id": "POS1", "quantity": {"value": "1000"}},
            {"position_id": "POS2", "quantity": {"value": "500"}},
        ]
    }

    service = SyncService(client, repo)
    result = await service.sync_depot_positions("DEPOT1")

    repo.insert_depot_snapshot.assert_called_once()
    assert result == {"inserted": 1, "touched": 0}


# ---------------------------------------------------------------------------
# sync_depot_transactions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sync_transactions_new_inserts():
    """New transaction not yet in DB — should insert."""
    client = AsyncMock()
    repo = MagicMock()

    txn = _transaction("TXN1")
    client.get_depot_transactions.return_value = MagicMock(values=[txn])
    repo.transaction_exists.return_value = False

    service = SyncService(client, repo)
    result = await service.sync_depot_transactions("DEPOT1")

    repo.insert_transaction.assert_called_once()
    assert result == {"inserted": 1, "skipped": 0}


@pytest.mark.asyncio
async def test_sync_transactions_existing_skipped():
    """Transaction already in DB — should skip."""
    client = AsyncMock()
    repo = MagicMock()

    txn = _transaction("TXN1")
    client.get_depot_transactions.return_value = MagicMock(values=[txn])
    repo.transaction_exists.return_value = True

    service = SyncService(client, repo)
    result = await service.sync_depot_transactions("DEPOT1")

    repo.insert_transaction.assert_not_called()
    assert result == {"inserted": 0, "skipped": 1}


@pytest.mark.asyncio
async def test_sync_transactions_mixed():
    """One new, one existing — insert one, skip one."""
    client = AsyncMock()
    repo = MagicMock()

    txn1 = _transaction("TXN1")
    txn2 = _transaction("TXN2")
    client.get_depot_transactions.return_value = MagicMock(values=[txn1, txn2])
    repo.transaction_exists.side_effect = lambda txn_id: txn_id == "TXN2"

    service = SyncService(client, repo)
    result = await service.sync_depot_transactions("DEPOT1")

    assert result == {"inserted": 1, "skipped": 1}


# ---------------------------------------------------------------------------
# helpers in mongo_repo (pure functions, no DB needed)
# ---------------------------------------------------------------------------

from datetime import UTC

from functions.sync.mongo_repo import _date_to_datetime, _decimal_to_str


def test_decimal_to_str_none():
    assert _decimal_to_str(None) is None


def test_decimal_to_str_value():
    assert _decimal_to_str(Decimal("123.45")) == "123.45"


def test_date_to_datetime_none():
    assert _date_to_datetime(None) is None


def test_date_to_datetime_converts_to_midnight_utc():
    result = _date_to_datetime(date(2026, 3, 15))
    assert result.year == 2026
    assert result.month == 3
    assert result.day == 15
    assert result.hour == 0
    assert result.minute == 0
    assert result.tzinfo == UTC
