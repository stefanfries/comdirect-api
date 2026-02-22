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


def format_remittance_info(remittance_info: str | None) -> str:
    """Format remittance info by parsing line number markers (01, 02, 03, etc.).

    Banking systems use multi-line remittance info with prefixes like:
    '01Purpose line 1            02Purpose line 2'

    This function splits them into a cleaner format.

    Args:
        remittance_info: Raw remittance information string

    Returns:
        Formatted string with lines separated by ' | '
    """
    if not remittance_info:
        return "N/A"

    # Remove line number prefixes and split into parts
    # Pattern: 2 digits followed by non-digit content until next 2-digit prefix
    # This handles: "01Text here    02More text    03Even more"
    parts = re.split(r'\d{2}', remittance_info)

    # Filter out empty strings and clean whitespace
    cleaned_parts = [part.strip() for part in parts if part.strip()]

    # Limit to first 3 meaningful parts
    if cleaned_parts:
        return " | ".join(cleaned_parts[:3])

    # Fallback: just return cleaned string
    return remittance_info.strip()[:100]


async def main():
    """Example script to demonstrate simplified ComdirectClient usage."""

    # Simple factory pattern - one line authentication!
    # All authentication steps are handled automatically:
    # 1. Primary OAuth authentication
    # 2. Session status check
    # 3. TAN challenge (wait for push notification)
    # 4. Banking/brokerage access token

    client = await ComdirectClient.create()
    print(f"Client ready! ID: {client.client_id}\n")

    # ========== BANKING FEATURES ==========

    # Get account balances
    try:
        print("\n--- Account Balances ---")
        account_balances = await client.get_account_balances()

        for balance in account_balances.values:
            account_id = balance.account_id
            balance_value = balance.balance.value
            currency = balance.balance.unit
            print(f"Account ID: {account_id}, Balance: {balance_value} {currency}")

        # Get transactions for first account
        if account_balances.values:
            first_account_id = account_balances.values[0].account_id
            print(f"\n--- Transactions for Account {first_account_id} ---")
            try:
                transactions = await client.get_account_transactions(
                    account_id=first_account_id, paging_first=0
                )
                print(f"Number of transactions: {len(transactions.values)}")
                for txn in transactions.values[:5]:  # Show first 5
                    date_str = txn.booking_date if txn.booking_date else "N/A"
                    amount_val = txn.amount.get("value") if txn.amount else "N/A"
                    amount_unit = txn.amount.get("unit") if txn.amount else ""
                    info = format_remittance_info(txn.remittance_info)
                    print(f"  - {date_str}: {amount_val} {amount_unit} - {info}")
            except Exception as e:
                print(f"No transactions found: {e}")

    except Exception as e:
        print("Error retrieving account balances:", e)

    # ========== BROKERAGE FEATURES ==========

    # Get depot information
    try:
        print("\n--- Depots ---")
        account_depots = await client.get_account_depots()

        for depot in account_depots.values:
            depot_id = depot.depot_id
            depot_display_id = depot.depot_display_id
            depot_type = depot.depot_type

            print(f"Depot ID: {depot_id}")
            print(f"Depot Display ID: {depot_display_id}")
            print(f"Depot Type: {depot_type}")

            # Get depot positions
            print(f"\n--- Positions for Depot {depot_id} ---")
            try:
                positions = await client.get_depot_positions(
                    depot_id=depot_id, with_attr="instrument"
                )
                print(f"Number of positions: {len(positions.values)}")
                for pos in positions.values[:10]:  # Show first 10
                    wkn = pos.wkn or "N/A"
                    instrument_name = pos.instrument.name if pos.instrument else "N/A"
                    current_value = (
                        pos.current_value.get("value") if pos.current_value else "N/A"
                    )
                    current_unit = (
                        pos.current_value.get("unit") if pos.current_value else ""
                    )
                    print(
                        f"  - {wkn}: {instrument_name} - "
                        f"Value: {current_value} {current_unit}"
                    )
            except Exception as e:
                print(f"No positions found: {e}")

            # Get depot transactions
            print(f"\n--- Transactions for Depot {depot_id} ---")
            try:
                depot_txns = await client.get_depot_transactions(
                    depot_id=depot_id, min_booking_date="-90d"
                )
                print(f"Number of depot transactions: {len(depot_txns.values)}")
                for txn in depot_txns.values[:5]:  # Show first 5
                    date_str = txn.booking_date if txn.booking_date else "N/A"
                    txn_type = txn.transaction_type or "N/A"
                    qty_val = txn.quantity.get("value") if txn.quantity else "N/A"
                    price_val = (
                        txn.execution_price.get("value")
                        if txn.execution_price
                        else "N/A"
                    )
                    print(f"  - {date_str}: {txn_type} - {qty_val} @ {price_val}")
            except Exception as e:
                print(f"No depot transactions found: {e}")

            # Get instrument details (if positions available)
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

    except Exception as e:
        print("Error retrieving depots:", e)

    # ========== MESSAGES FEATURES ==========

    # Get documents
    try:
        print("\n--- Documents ---")
        documents = await client.get_documents(paging_count=10)
        print(f"Number of documents: {len(documents.values)}")

        for doc in documents.values[:5]:  # Show first 5
            name = doc.name
            date = doc.date_creation
            mime = doc.mime_type
            read = doc.document_meta_data.already_read if doc.document_meta_data else False
            print(f"  - {date}: {name} ({mime}) - Read: {read}")

            # Download first document as example (commented out to avoid downloading all)
            # if doc.document_id:
            #     print(f"\n--- Downloading Document {doc.document_id} ---")
            #     content = await client.get_document(doc.document_id)
            #     filename = f"{doc.name.replace(' ', '_')}.pdf"
            #     with open(filename, 'wb') as f:
            #         f.write(content)
            #     print(f"Saved to {filename} ({len(content)} bytes)")

    except Exception as e:
        print("Error retrieving documents:", e)


if __name__ == "__main__":
    asyncio.run(main())
