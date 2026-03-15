"""Sync orchestration logic — testable independently of the Azure Function trigger."""

import logging

from comdirect_api.client import ComdirectClient
from functions.sync.mongo_repo import MongoRepo

logger = logging.getLogger(__name__)


class SyncService:
    """
    Orchestrates fetching data from the Comdirect API and persisting it to Atlas.

    Sync rules:
    - account_balances  : insert a new snapshot when balance.value has changed.
      If unchanged, only last_synced_at is updated on the latest document.
      Full time series is retained for charting; last_synced_at acts as a heartbeat.
    - depot_snapshots   : insert a new snapshot of the ENTIRE depot when the
      composition changes (quantity change on any position, new position, or a
      position fully sold/closed). Otherwise only last_synced_at is updated.
      Latest state = most recent document for that depot_id.
    - transactions      : insert-only, idempotent (skipped if transaction_id exists).
    """

    def __init__(self, client: ComdirectClient, repo: MongoRepo) -> None:
        self._client = client
        self._repo = repo

    async def sync_account_balances(self) -> dict:
        """Fetch all account balances. Insert snapshot on change, touch timestamp otherwise."""
        balances = await self._client.get_account_balances()
        inserted = 0
        touched = 0

        for ab in balances.values:
            account_id = ab.account.account_id if ab.account else None
            if not account_id:
                continue

            new_value = ab.balance.value if ab.balance else None
            latest = self._repo.get_latest_balance(account_id)

            if latest and latest.get("balance", {}).get("value") == str(new_value):
                self._repo.touch_balance_last_synced(account_id)
                touched += 1
                continue

            self._repo.insert_balance(
                account_id=account_id,
                iban=ab.account.iban if ab.account else None,
                account_type=(
                    ab.account.account_type.text
                    if ab.account and ab.account.account_type
                    else None
                ),
                value=new_value,
                unit=ab.balance.unit if ab.balance else None,
            )
            inserted += 1
            logger.info("Balance snapshot inserted for account %s", account_id)

        return {"inserted": inserted, "touched": touched}

    async def sync_depot_positions(self, depot_id: str) -> dict:
        """
        Snapshot the entire depot.

        Insert a new snapshot document when the composition changes:
          - any position's quantity is different from the latest snapshot
          - a new position appears
          - a position is gone (fully sold)
        Otherwise only touch last_synced_at on the latest snapshot.
        """
        positions = await self._client.get_depot_positions(
            depot_id=depot_id, with_attr="instrument"
        )

        # Build current state as {position_id: quantity_str}
        current: dict[str, str] = {}
        for pos in positions.values:
            if pos.position_id:
                qty = pos.quantity.value if pos.quantity else None
                current[pos.position_id] = str(qty) if qty is not None else "None"

        # Compare against latest snapshot fingerprint
        latest = self._repo.get_latest_depot_snapshot(depot_id)
        if latest:
            previous: dict[str, str] = {
                p["position_id"]: p.get("quantity", {}).get("value", "None")
                for p in latest.get("positions", [])
            }
            changed = current != previous
        else:
            changed = True  # no snapshot yet

        if not changed:
            self._repo.touch_depot_last_synced(depot_id)
            logger.info("Depot %s unchanged — touched last_synced_at", depot_id)
            return {"inserted": 0, "touched": 1}

        # Build full position list for the new snapshot
        snapshot_positions = []
        for pos in positions.values:
            if not pos.position_id:
                continue
            snapshot_positions.append({
                "position_id": pos.position_id,
                "wkn": pos.wkn,
                "isin": pos.instrument.isin if pos.instrument else None,
                "instrument_name": pos.instrument.name if pos.instrument else None,
                "quantity": {
                    "value": str(pos.quantity.value) if pos.quantity and pos.quantity.value is not None else None,
                    "unit": pos.quantity.unit if pos.quantity else None,
                },
                "current_value": {
                    "value": str(pos.current_value.value) if pos.current_value and pos.current_value.value is not None else None,
                    "unit": pos.current_value.unit if pos.current_value else None,
                },
                "purchase_price": {
                    "value": str(pos.purchase_price.value) if pos.purchase_price and pos.purchase_price.value is not None else None,
                    "unit": pos.purchase_price.unit if pos.purchase_price else None,
                },
            })

        self._repo.insert_depot_snapshot(depot_id=depot_id, positions=snapshot_positions)
        logger.info(
            "Depot %s snapshot inserted — %d positions",
            depot_id, len(snapshot_positions),
        )
        return {"inserted": 1, "touched": 0}

    async def sync_depot_transactions(
        self, depot_id: str, min_booking_date: str = "-90d"
    ) -> dict:
        """Insert any new depot transactions (idempotent)."""
        txns = await self._client.get_depot_transactions(
            depot_id=depot_id, min_booking_date=min_booking_date
        )
        inserted = 0
        skipped = 0

        for txn in txns.values:
            if not txn.transaction_id:
                continue
            if self._repo.transaction_exists(txn.transaction_id):
                skipped += 1
                continue

            self._repo.insert_transaction(
                transaction_id=txn.transaction_id,
                depot_id=depot_id,
                wkn=(
                    txn.instrument.wkn
                    if txn.instrument and isinstance(txn.instrument, dict) is False
                    else None
                ),
                booking_date=txn.booking_date,
                transaction_type=txn.transaction_type,
                quantity=txn.quantity.value if txn.quantity else None,
                quantity_unit=txn.quantity.unit if txn.quantity else None,
                execution_price=(
                    txn.execution_price.value if txn.execution_price else None
                ),
                price_unit=(
                    txn.execution_price.unit if txn.execution_price else None
                ),
            )
            inserted += 1

        return {"inserted": inserted, "skipped": skipped}

    async def run_full_sync(self) -> dict:
        """Run a complete sync: balances + all depots (positions + transactions)."""
        result: dict = {"account_balances": {}, "depots": []}

        result["account_balances"] = await self.sync_account_balances()

        depots = await self._client.get_account_depots()
        for depot in depots.values:
            depot_id = depot.depot_id
            positions_result = await self.sync_depot_positions(depot_id)
            transactions_result = await self.sync_depot_transactions(depot_id)
            result["depots"].append({
                "depot_id": depot_id,
                "positions": positions_result,
                "transactions": transactions_result,
            })
            logger.info(
                "Depot %s synced: positions %s, %s new transactions",
                depot_id,
                positions_result,
                transactions_result["inserted"],
            )

        return result
