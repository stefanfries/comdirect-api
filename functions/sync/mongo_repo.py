"""MongoDB Atlas repository for the Comdirect sync function."""

from datetime import UTC, date, datetime
from decimal import Decimal

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database


def _now() -> datetime:
    return datetime.now(UTC)


def _decimal_to_str(v: Decimal | None) -> str | None:
    return str(v) if v is not None else None


def _date_to_datetime(d: date | None) -> datetime | None:
    """Convert a bare date to midnight UTC datetime for native MongoDB storage."""
    if d is None:
        return None
    return datetime(d.year, d.month, d.day, tzinfo=UTC)


class MongoRepo:
    """All Atlas read/write operations for the sync service."""

    def __init__(self, connection_string: str, database: str) -> None:
        self._client = MongoClient(connection_string)
        self._db: Database = self._client[database]

        # Ensure indexes on first use
        self._db["account_balances"].create_index(
            [("account_id", ASCENDING), ("recorded_at", DESCENDING)]
        )
        self._db["depot_positions"].create_index("position_id", unique=True)
        self._db["transactions"].create_index("transaction_id", unique=True)

    def close(self) -> None:
        self._client.close()

    # ------------------------------------------------------------------
    # account_balances — insert-only time series
    # ------------------------------------------------------------------

    def get_latest_balance(self, account_id: str) -> dict | None:
        """Return the most recently inserted balance document for an account."""
        return self._db["account_balances"].find_one(
            {"account_id": account_id},
            sort=[("recorded_at", DESCENDING)],
        )

    def insert_balance(
        self,
        account_id: str,
        iban: str | None,
        account_type: str | None,
        value: Decimal | None,
        unit: str | None,
    ) -> None:
        """Insert a new balance snapshot. Sets both recorded_at and last_synced_at."""
        now = _now()
        self._db["account_balances"].insert_one({
            "account_id": account_id,
            "iban": iban,
            "account_type": account_type,
            "balance": {
                "value": _decimal_to_str(value),
                "unit": unit,
            },
            "recorded_at": now,
            "last_synced_at": now,
        })

    def touch_balance_last_synced(self, account_id: str) -> None:
        """Update last_synced_at on the latest balance doc without inserting a new one."""
        self._db["account_balances"].update_one(
            {"account_id": account_id},
            {"$set": {"last_synced_at": _now()}},
            sort=[("recorded_at", DESCENDING)],
        )

    # ------------------------------------------------------------------
    # depot_positions — upsert; quantity_history on quantity change
    # ------------------------------------------------------------------

    def get_position(self, position_id: str) -> dict | None:
        return self._db["depot_positions"].find_one({"position_id": position_id})

    def upsert_position(
        self,
        position_id: str,
        depot_id: str,
        wkn: str | None,
        isin: str | None,
        instrument_name: str | None,
        quantity_value: Decimal | None,
        quantity_unit: str | None,
        current_value: Decimal | None,
        current_value_unit: str | None,
        purchase_price: Decimal | None,
        purchase_price_unit: str | None,
        quantity_changed: bool,
    ) -> None:
        """
        Upsert a depot position.
        Appends to quantity_history only when quantity_changed is True.
        Always updates current_value and last_updated.
        """
        now = _now()
        col: Collection = self._db["depot_positions"]

        update: dict = {
            "$set": {
                "depot_id": depot_id,
                "wkn": wkn,
                "isin": isin,
                "instrument_name": instrument_name,
                "quantity": {
                    "value": _decimal_to_str(quantity_value),
                    "unit": quantity_unit,
                },
                "current_value": {
                    "value": _decimal_to_str(current_value),
                    "unit": current_value_unit,
                },
                "purchase_price": {
                    "value": _decimal_to_str(purchase_price),
                    "unit": purchase_price_unit,
                },
                "last_updated": now,
            }
        }

        if quantity_changed:
            update["$push"] = {
                "quantity_history": {
                    "quantity": _decimal_to_str(quantity_value),
                    "unit": quantity_unit,
                    "recorded_at": now,
                }
            }

        col.update_one({"position_id": position_id}, update, upsert=True)

    def get_position_ids_in_depot(self, depot_id: str) -> set[str]:
        """Return all known position_ids for a depot (to detect closed positions)."""
        docs = self._db["depot_positions"].find(
            {"depot_id": depot_id}, {"position_id": 1}
        )
        return {d["position_id"] for d in docs}

    # ------------------------------------------------------------------
    # transactions — insert-only, keyed by transaction_id
    # ------------------------------------------------------------------

    def transaction_exists(self, transaction_id: str) -> bool:
        return (
            self._db["transactions"].count_documents(
                {"transaction_id": transaction_id}, limit=1
            )
            > 0
        )

    def insert_transaction(
        self,
        transaction_id: str,
        depot_id: str,
        wkn: str | None,
        booking_date: date | None,
        transaction_type: str | None,
        quantity: Decimal | None,
        quantity_unit: str | None,
        execution_price: Decimal | None,
        price_unit: str | None,
    ) -> None:
        if self.transaction_exists(transaction_id):
            return
        self._db["transactions"].insert_one({
            "transaction_id": transaction_id,
            "depot_id": depot_id,
            "wkn": wkn,
            "booking_date": _date_to_datetime(booking_date),
            "transaction_type": transaction_type,
            "quantity": _decimal_to_str(quantity),
            "quantity_unit": quantity_unit,
            "execution_price": _decimal_to_str(execution_price),
            "price_unit": price_unit,
            "recorded_at": _now(),
        })
