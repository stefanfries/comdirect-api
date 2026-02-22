import asyncio

from .client import ComdirectClient
from .core.settings import settings


async def main():
    """Example script to demonstrate ComdirectClient usage."""

    # 0️⃣ Lade Zugangsdaten aus Umgebungsvariablen
    client_id = settings.client_id.get_secret_value()
    client_secret = settings.client_secret.get_secret_value()
    zugangsnummer = settings.zugangsnummer.get_secret_value()
    pin = settings.pin.get_secret_value()

    # 1️⃣ Client initialisieren
    client = ComdirectClient(client_id=client_id, client_secret=client_secret)
    print(f"Client initialized with ID: {client.client_id}\n")

    # 2️⃣ Authentifizieren (primary access token, nur SESSION_RW Scope)
    primary_tokens = await client.authenticate(
        username=zugangsnummer, password=pin, scope="SESSION_RW"
    )
    print(f"Primary OAuth token erhalten: {primary_tokens}")

    # 3️⃣ Session prüfen
    session_status = await client.get_session_status()
    print(f"Session Status: {session_status}\n")

    # 4️⃣ TAN (2FA) aktivieren – optional für kritische Aktionen
    if not client.activated_2fa:
        tan_response = await client.create_validate_session_tan()
        print(f"Session TAN validated: {tan_response}\n")
    else:
        print("2FA already activated for this session\n")

    # 5️⃣ Banking/Brokerage access token holen (cd_secondary)
    try:
        banking_tokens = await client.get_banking_brokerage_access()
        print("Banking/Brokerage token erhalten:", banking_tokens)
    except Exception as e:
        print("Fehler beim Banking/Brokerage Access:", e)

    # ========== BANKING FEATURES ==========

    # 6️⃣ Kontostände abrufen
    try:
        print("\n--- Kontostände ---")
        account_balances = await client.get_account_balances()

        for balance in account_balances.values:
            account_id = balance.account_id
            balance_value = balance.balance.value
            currency = balance.balance.unit
            print(f"Account ID: {account_id}, Balance: {balance_value} {currency}")

        # Get transactions for first account
        if account_balances.values:
            first_account_id = account_balances.values[0].account_id
            print(f"\n--- Transaktionen für Account {first_account_id} ---")
            try:
                transactions = await client.get_account_transactions(
                    account_id=first_account_id, paging_first=0
                )
                print(f"Anzahl Transaktionen: {len(transactions.values)}")
                for txn in transactions.values[:5]:  # Show first 5
                    date_str = txn.booking_date if txn.booking_date else "N/A"
                    amount_val = txn.amount.get("value") if txn.amount else "N/A"
                    amount_unit = txn.amount.get("unit") if txn.amount else ""
                    info = (txn.remittance_info[:50] if txn.remittance_info else "N/A")
                    print(f"  - {date_str}: {amount_val} {amount_unit} - {info}")
            except Exception as e:
                print(f"Keine Transaktionen gefunden: {e}")

    except Exception as e:
        print("Fehler beim Abrufen der Kontostände:", e)

    # ========== BROKERAGE FEATURES ==========

    # 7️⃣ Depotinformationen abrufen
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
            print(f"\n--- Positionen für Depot {depot_id} ---")
            try:
                positions = await client.get_depot_positions(
                    depot_id=depot_id, with_attr="instrument"
                )
                print(f"Anzahl Positionen: {len(positions.values)}")
                for pos in positions.values[:10]:  # Show first 10
                    wkn = pos.wkn or "N/A"
                    instrument_name = (
                        pos.instrument.name if pos.instrument else "N/A"
                    )
                    current_value = (
                        pos.current_value.get("value")
                        if pos.current_value
                        else "N/A"
                    )
                    current_unit = (
                        pos.current_value.get("unit") if pos.current_value else ""
                    )
                    print(
                        f"  - {wkn}: {instrument_name} - "
                        f"Value: {current_value} {current_unit}"
                    )
            except Exception as e:
                print(f"Keine Positionen gefunden: {e}")

            # Get depot transactions
            print(f"\n--- Transaktionen für Depot {depot_id} ---")
            try:
                depot_txns = await client.get_depot_transactions(
                    depot_id=depot_id, min_booking_date="-90d"
                )
                print(f"Anzahl Depot-Transaktionen: {len(depot_txns.values)}")
                for txn in depot_txns.values[:5]:  # Show first 5
                    date_str = txn.booking_date if txn.booking_date else "N/A"
                    txn_type = txn.transaction_type or "N/A"
                    qty_val = (
                        txn.quantity.get("value") if txn.quantity else "N/A"
                    )
                    price_val = (
                        txn.execution_price.get("value")
                        if txn.execution_price
                        else "N/A"
                    )
                    print(
                        f"  - {date_str}: {txn_type} - {qty_val} @ {price_val}"
                    )
            except Exception as e:
                print(f"Keine Depot-Transaktionen gefunden: {e}")

            # Get instrument details (if positions available)
            if positions and positions.values and positions.values[0].wkn:
                wkn = positions.values[0].wkn
                print(f"\n--- Instrument-Details für WKN {wkn} ---")
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
                            print(
                                f"Type: {instrument.static_data.instrument_type}"
                            )
                            print(
                                f"Currency: {instrument.static_data.currency}"
                            )
                except Exception as e:
                    print(f"Instrument-Details nicht verfügbar: {e}")

    except Exception as e:
        print("Fehler beim Abrufen der Depots:", e)


if __name__ == "__main__":
    asyncio.run(main())
