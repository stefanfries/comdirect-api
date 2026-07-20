"""Sync orchestration logic — testable independently of the Azure Function trigger."""

import asyncio
import logging
from datetime import date, datetime
from decimal import Decimal

import httpx

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

    def __init__(
        self,
        client: ComdirectClient,
        repo: MongoRepo,
        account_name: str,
        display_name: str | None = None,
        depot_transactions_lookback: str = "-3650d",
    ) -> None:
        self._client = client
        self._repo = repo
        self._account_name = account_name
        self._display_name = display_name
        self._depot_transactions_lookback = depot_transactions_lookback

    @staticmethod
    def _extract_instrument_identifiers(txn) -> tuple[str | None, str | None]:
        """Return (wkn, isin) from transaction instrument payload/object."""
        instrument = getattr(txn, "instrument", None)
        if not instrument:
            return (None, None)
        if isinstance(instrument, dict):
            return (instrument.get("wkn"), instrument.get("isin"))
        return (getattr(instrument, "wkn", None), getattr(instrument, "isin", None))

    @staticmethod
    def _booking_date_key(txn) -> tuple[date, str]:
        """Sorting key for transactions: booking date ascending, then transaction id."""
        value = getattr(txn, "booking_date", None)
        if isinstance(value, datetime):
            d = value.date()
        elif isinstance(value, date):
            d = value
        else:
            d = date.min
        return d, getattr(txn, "transaction_id", "") or ""

    @staticmethod
    def _signed_quantity(txn) -> Decimal | None:
        """Return signed quantity for a depot transaction."""
        quantity = getattr(txn, "quantity", None)
        value = getattr(quantity, "value", None) if quantity else None
        if value is None:
            return None

        txn_type = getattr(txn, "transaction_type", None)
        if txn_type in {"BUY", "TRANSFER_IN"}:
            return Decimal(value)
        if txn_type in {"SELL", "TRANSFER_OUT"}:
            return Decimal(value) * Decimal("-1")
        return None

    def _derive_entry_metadata(self, position, transactions) -> dict[str, dict | str | None]:
        """
        Derive held_since_date and purchase_price_at_entry for current holding.

        The algorithm walks matching transactions backwards from the current quantity
        and finds the BUY/TRANSFER_IN event where the previous balance was <= 0.
        """
        quantity = getattr(position, "quantity", None)
        current_qty_raw = getattr(quantity, "value", None) if quantity else None
        if current_qty_raw is None:
            return {
                "held_since_date": None,
                "purchase_price_at_entry": {"value": None, "unit": None},
            }

        current_qty = Decimal(current_qty_raw)
        if current_qty <= 0:
            return {
                "held_since_date": None,
                "purchase_price_at_entry": {"value": None, "unit": None},
            }

        pos_wkn = getattr(position, "wkn", None)
        pos_isin = getattr(getattr(position, "instrument", None), "isin", None)

        matching = []
        for txn in transactions:
            signed_qty = self._signed_quantity(txn)
            if signed_qty is None:
                continue

            txn_wkn, txn_isin = self._extract_instrument_identifiers(txn)
            if pos_isin and txn_isin == pos_isin:
                matching.append(txn)
                continue
            if pos_wkn and txn_wkn == pos_wkn:
                matching.append(txn)

        if not matching:
            return {
                "held_since_date": None,
                "purchase_price_at_entry": {"value": None, "unit": None},
            }

        balance_after = current_qty
        for txn in sorted(matching, key=self._booking_date_key, reverse=True):
            signed_qty = self._signed_quantity(txn)
            if signed_qty is None:
                continue

            balance_before = balance_after - signed_qty
            if signed_qty > 0 and balance_before <= 0 < balance_after:
                execution_price = getattr(txn, "execution_price", None)
                booking_date = getattr(txn, "booking_date", None)
                held_since_date = booking_date.isoformat() if booking_date else None
                return {
                    "held_since_date": held_since_date,
                    "purchase_price_at_entry": {
                        "value": (
                            str(execution_price.value)
                            if execution_price and execution_price.value is not None
                            else None
                        ),
                        "unit": execution_price.unit if execution_price else None,
                    },
                }
            balance_after = balance_before

        return {
            "held_since_date": None,
            "purchase_price_at_entry": {"value": None, "unit": None},
        }

    async def _fetch_depot_transactions_with_retry(
        self,
        depot_id: str,
        min_booking_date: str,
    ):
        """Fetch depot transactions with retry on 429."""
        for attempt in range(4):
            try:
                return await self._client.get_depot_transactions(
                    depot_id=depot_id,
                    min_booking_date=min_booking_date,
                )
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429 and attempt < 3:
                    wait = 2 ** (attempt + 1)
                    logger.warning(
                        (
                            "Rate limited fetching depot %s transactions, "
                            "retrying in %ds (attempt %d/3)…"
                        ),
                        depot_id,
                        wait,
                        attempt + 1,
                    )
                    await asyncio.sleep(wait)
                else:
                    raise

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
            latest = await self._repo.get_latest_balance(account_id)

            if latest and latest.get("balance", {}).get("value") == str(new_value):
                await self._repo.touch_balance_last_synced(account_id)
                touched += 1
                continue

            await self._repo.insert_balance(
                account_id=account_id,
                account_name=self._account_name,
                display_name=self._display_name,
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

    async def sync_depot_positions(self, depot_id: str, depot_transactions=None) -> dict:
        """
        Snapshot the entire depot.

        Insert a new snapshot document when the composition changes:
          - any position's quantity is different from the latest snapshot
          - a new position appears
          - a position is gone (fully sold)
        Otherwise only touch last_synced_at on the latest snapshot.
        """
        for attempt in range(4):
            try:
                positions = await self._client.get_depot_positions(
                    depot_id=depot_id, with_attr="instrument"
                )
                break
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429 and attempt < 3:
                    wait = 2 ** (attempt + 1)  # 2, 4, 8 seconds
                    logger.warning(
                        "Rate limited fetching depot %s positions, retrying in %ds (attempt %d/3)…",
                        depot_id, wait, attempt + 1,
                    )
                    await asyncio.sleep(wait)
                else:
                    raise

        # Build current state as {position_id: quantity_str}
        current: dict[str, str] = {}
        for pos in positions.values:
            if pos.position_id:
                qty = pos.quantity.value if pos.quantity else None
                current[pos.position_id] = str(qty) if qty is not None else "None"

        # Compare against latest snapshot fingerprint
        latest = await self._repo.get_latest_depot_snapshot(depot_id)
        if latest:
            previous: dict[str, str] = {
                p["position_id"]: p.get("quantity", {}).get("value", "None")
                for p in latest.get("positions", [])
            }
            changed = current != previous
        else:
            changed = True  # no snapshot yet

        if not changed:
            await self._repo.touch_depot_last_synced(depot_id)
            logger.info("Depot %s unchanged — touched last_synced_at", depot_id)
            return {"inserted": 0, "touched": 1}

        # Build full position list for the new snapshot
        def _v(amount_value) -> str | None:
            """Return str(value) or None from an AmountValue-like object."""
            if amount_value and amount_value.value is not None:
                return str(amount_value.value)
            return None

        def _u(amount_value) -> str | None:
            """Return unit or None from an AmountValue-like object."""
            return amount_value.unit if amount_value else None

        tx_values = depot_transactions.values if depot_transactions else []

        snapshot_positions = []
        for pos in positions.values:
            if not pos.position_id:
                continue
            cp = pos.current_price  # shorthand to keep lines short
            entry_metadata = self._derive_entry_metadata(pos, tx_values)
            snapshot_positions.append({
                "position_id": pos.position_id,
                "wkn": pos.wkn,
                "isin": pos.instrument.isin if pos.instrument else None,
                "instrument_name": pos.instrument.name if pos.instrument else None,
                "quantity": {
                    "value": _v(pos.quantity),
                    "unit": _u(pos.quantity),
                },
                "current_price": {
                    "value": _v(cp.price) if cp else None,
                    "unit": _u(cp.price) if cp else None,
                    "price_datetime": cp.price_datetime if cp else None,
                },
                "current_value": {
                    "value": _v(pos.current_value),
                    "unit": _u(pos.current_value),
                },
                # Explicit average cost basis from Comdirect position payload.
                "average_purchase_price": {
                    "value": _v(pos.purchase_price),
                    "unit": _u(pos.purchase_price),
                },
                "held_since_date": entry_metadata["held_since_date"],
                # First BUY price of the current holding period.
                "purchase_price_at_entry": entry_metadata[
                    "purchase_price_at_entry"
                ],
            })

        await self._repo.insert_depot_snapshot(
            depot_id=depot_id,
            account_name=self._account_name,
            display_name=self._display_name,
            positions=snapshot_positions,
        )
        logger.info(
            "Depot %s snapshot inserted — %d positions",
            depot_id, len(snapshot_positions),
        )
        return {"inserted": 1, "touched": 0}

    async def sync_depot_transactions(
        self,
        depot_id: str,
        min_booking_date: str | None = None,
        depot_transactions=None,
    ) -> dict:
        """Insert any new depot transactions (idempotent)."""
        booking_date_filter = min_booking_date or self._depot_transactions_lookback
        txns = depot_transactions or await self._fetch_depot_transactions_with_retry(
            depot_id=depot_id,
            min_booking_date=booking_date_filter,
        )
        inserted = 0
        skipped = 0

        for txn in txns.values:
            if not txn.transaction_id:
                continue
            if await self._repo.transaction_exists(txn.transaction_id):
                skipped += 1
                continue

            await self._repo.insert_transaction(
                transaction_id=txn.transaction_id,
                depot_id=depot_id,
                account_name=self._account_name,
                display_name=self._display_name,
                wkn=self._extract_instrument_identifiers(txn)[0],
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
            depot_transactions = await self._fetch_depot_transactions_with_retry(
                depot_id=depot_id,
                min_booking_date=self._depot_transactions_lookback,
            )
            positions_result = await self.sync_depot_positions(
                depot_id,
                depot_transactions=depot_transactions,
            )
            transactions_result = await self.sync_depot_transactions(
                depot_id,
                depot_transactions=depot_transactions,
            )
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
