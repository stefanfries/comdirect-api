import asyncio

from .client import ComdirectClient


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
                    info = txn.remittance_info[:50] if txn.remittance_info else "N/A"
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


if __name__ == "__main__":
    asyncio.run(main())
