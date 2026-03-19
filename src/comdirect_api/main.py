import asyncio
import logging
import re
import sys

from .client import ComdirectClient

# Ensure UTF-8 encoding for console output (Windows compatibility)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more detailed output
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def format_iban(iban: str) -> str:
    """Format raw IBAN string with spaces every 4 characters."""
    iban = iban.replace(" ", "")
    return " ".join(iban[i:i+4] for i in range(0, len(iban), 4))


def format_remittance_info(remittance_info: str | None) -> str:
    """Format remittance info by parsing line number markers (01, 02, 03, etc.)."""
    if not remittance_info:
        return "N/A"
    parts = re.split(r'\d{2}', remittance_info)
    cleaned_parts = [part.strip() for part in parts if part.strip()]
    if cleaned_parts:
        return " | ".join(cleaned_parts[:3])
    return remittance_info.strip()[:100]


async def main():
    """Example script to demonstrate ComdirectClient usage."""

    client = await ComdirectClient.create()
    print(f"Client ready! ID: {client.client_id}\n")

    # ========== BANKING FEATURES ==========

    try:
        print("\n--- Account Balances ---")
        account_balances = await client.get_account_balances()

        for balance in account_balances.values:
            print(
                f"Account ID: {balance.account_id}, "
                f"Balance: {balance.balance.value} {balance.balance.unit}"
            )

        if account_balances.values:
            first_account_id = account_balances.values[0].account_id
            print(f"\n--- Transactions for Account {first_account_id} ---")
            try:
                transactions = await client.get_account_transactions(
                    account_id=first_account_id, paging_first=0
                )
                print(f"Number of transactions: {len(transactions.values)}")
                for txn in transactions.values[:5]:
                    date_str = txn.booking_date if txn.booking_date else "N/A"
                    amount_val = txn.amount.value if txn.amount else "N/A"
                    amount_unit = txn.amount.unit if txn.amount else ""
                    info = format_remittance_info(txn.remittance_info)
                    print(f"  - {date_str}: {amount_val} {amount_unit} - {info}")
            except Exception as e:
                print(f"No transactions found: {e}")

    except Exception as e:
        print("Error retrieving account balances:", e)

    # ========== BROKERAGE FEATURES ==========

    try:
        print("\n--- Depots ---")
        account_depots = await client.get_account_depots()

        for depot in account_depots.values:
            depot_id = depot.depot_id
            print(f"Depot ID: {depot_id}")
            print(f"Depot Display ID: {depot.depot_display_id}")
            print(f"Depot Type: {depot.depot_type}")

            print(f"\n--- Positions for Depot {depot_id} ---")
            try:
                positions = await client.get_depot_positions(
                    depot_id=depot_id, with_attr="instrument"
                )
                print(f"Number of positions: {len(positions.values)}")
                for pos in positions.values[:10]:
                    wkn = pos.wkn or "N/A"
                    instrument_name = pos.instrument.name if pos.instrument else "N/A"
                    quantity_val = pos.quantity.value if pos.quantity else "N/A"
                    quantity_unit = pos.quantity.unit if pos.quantity else ""
                    current_value = pos.current_value.value if pos.current_value else "N/A"
                    current_unit = pos.current_value.unit if pos.current_value else ""
                    print(
                        f"  - {wkn}: {instrument_name} - "
                        f"Qty: {quantity_val} {quantity_unit} - "
                        f"Value: {current_value} {current_unit}"
                    )
            except Exception as e:
                print(f"No positions found: {e}")

            print(f"\n--- Transactions for Depot {depot_id} ---")
            try:
                depot_txns = await client.get_depot_transactions(
                    depot_id=depot_id, min_booking_date="-90d"
                )
                print(f"Number of depot transactions: {len(depot_txns.values)}")
                for txn in depot_txns.values[:5]:
                    date_str = txn.booking_date if txn.booking_date else "N/A"
                    txn_type = txn.transaction_type or "N/A"
                    qty_val = txn.quantity.value if txn.quantity else "N/A"
                    price_val = txn.execution_price.value if txn.execution_price else "N/A"
                    print(f"  - {date_str}: {txn_type} - {qty_val} @ {price_val}")
            except Exception as e:
                print(f"No depot transactions found: {e}")

            if positions and positions.values and positions.values[0].wkn:
                wkn = positions.values[0].wkn
                print(f"\n--- Instrument Details for WKN {wkn} ---")
                try:
                    instruments = await client.get_instrument(
                        instrument_id=wkn,
                        with_attr=["orderDimensions", "derivativeData"],
                    )
                    if instruments.values:
                        instrument = instruments.values[0]
                        print(f"Name: {instrument.name}")
                        print(f"ISIN: {instrument.isin}")
                        print(f"WKN: {instrument.wkn}")
                        if instrument.static_data:
                            print(f"Type: {instrument.static_data.instrument_type}")
                            print(f"Currency: {instrument.static_data.currency}")
                except Exception as e:
                    print(f"Instrument details not available: {e}")

            print(f"\n--- Orders for Depot {depot_id} ---")
            try:
                orders = await client.get_depot_orders(depot_id=depot_id)
                print(f"Number of orders: {len(orders.values)}")
                for order in orders.values[:10]:
                    order_id = order.order_id or "N/A"
                    order_type = order.order_type or "N/A"
                    status = order.order_status or "N/A"
                    side = order.side or "N/A"
                    instrument = order.instrument_id or "N/A"
                    qty_val = order.quantity.value if order.quantity else "N/A"
                    qty_unit = order.quantity.unit if order.quantity else ""
                    limit_val = order.limit.value if order.limit else "MARKET"
                    limit_unit = order.limit.unit if order.limit else ""
                    created = order.creation_timestamp or "N/A"
                    print(
                        f"  - [{status}] {side} {order_type}: {instrument} "
                        f"Qty: {qty_val} {qty_unit} @ {limit_val} {limit_unit} "
                        f"(ID: {order_id}, Created: {created})"
                    )
                    # Fetch full order details including executions for executed orders
                    if status == "EXECUTED" and order.order_id:
                        try:
                            full_order = await client.get_order(order_id=order.order_id)
                            executions = full_order.executions or []
                            if executions:
                                for ex in executions:
                                    ex_qty = (
                                        ex.executed_quantity.value
                                        if ex.executed_quantity
                                        else "N/A"
                                    )
                                    ex_price = (
                                        ex.execution_price.value
                                        if ex.execution_price
                                        else "N/A"
                                    )
                                    ex_unit = ex.execution_price.unit if ex.execution_price else ""
                                    print(
                                        f"      Execution: {ex_qty} @ {ex_price} {ex_unit} "
                                        f"on {ex.execution_timestamp}"
                                    )
                        except Exception:
                            pass  # execution details optional
            except Exception as e:
                print(f"No orders found: {e}")

    except Exception as e:
        print("Error retrieving depots:", e)

    # ========== MESSAGES FEATURES ==========

    try:
        print("\n--- Documents ---")
        documents = await client.get_documents(paging_count=10)
        print(f"Number of documents: {len(documents.values)}")

        for doc in documents.values[:5]:
            read = doc.document_meta_data.already_read if doc.document_meta_data else False
            print(f"  - {doc.date_creation}: {doc.name} ({doc.mime_type}) - Read: {read}")

    except Exception as e:
        print("Error retrieving documents:", e)

    # ========== REPORTS FEATURES ==========

    try:
        print("\n--- All Product Balances (Reports) ---")
        all_balances = await client.get_all_balances()
        print(f"Total products: {all_balances.paging.matches}")
        if all_balances.aggregated and all_balances.aggregated.balance_eur:
            agg_val = all_balances.aggregated.balance_eur.value
            agg_unit = all_balances.aggregated.balance_eur.unit or "EUR"
            print(f"Aggregated balance: {agg_val} {agg_unit}")
        for pb in all_balances.values:
            print(f"  - {pb.product_type}: {pb.product_id}")
    except Exception as e:
        print("Error retrieving all balances:", e)

    # ========== PORTFOLIO SUMMARY TABLE ==========

    from decimal import Decimal

    col_name  = 26
    col_ident = 33
    col_value = 16

    def row(name: str, ident: str, value: Decimal | None) -> str:
        val_str = f"{value:,.2f}" if value is not None else ""
        return f"│ {name:<{col_name}} │ {ident:<{col_ident}} │ {val_str:>{col_value}} │"

    top    = f"┌{'─'*(col_name+2)}┬{'─'*(col_ident+2)}┬{'─'*(col_value+2)}┐"
    mid    = f"├{'─'*(col_name+2)}┼{'─'*(col_ident+2)}┼{'─'*(col_value+2)}┤"
    bot    = f"└{'─'*(col_name+2)}┴{'─'*(col_ident+2)}┴{'─'*(col_value+2)}┘"
    header = (
        f"│ {'Product':<{col_name}} │ {'IBAN / Number':<{col_ident}} │"
        f" {'Value (EUR)':>{col_value}} │"
    )

    # Collect all data before printing anything
    total = Decimal(0)
    table_rows = []

    for ab in account_balances.values:
        name  = ab.account.account_type.text
        iban  = format_iban(ab.account.iban)
        value = ab.balance_eur.value
        total += value
        table_rows.append((name, iban, value))

    for depot in account_depots.values:
        positions = await client.get_depot_positions(depot_id=depot.depot_id)
        depot_total = sum(
            Decimal(str(pos.current_value.value))
            for pos in positions.values
            if pos.current_value and pos.current_value.value is not None
        )
        total += depot_total
        table_rows.append(("Depot", depot.depot_display_id, depot_total))

    print("\n--- Portfolio Summary ---")
    print(top)
    print(header)
    print(mid)
    for name, ident, value in table_rows:
        print(row(name, ident, value))
    print(mid)
    print(row("Total", "", total))
    print(bot)


if __name__ == "__main__":
    asyncio.run(main())
