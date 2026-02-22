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

    # 6️⃣ Unkritische Banking-Anfrage (z. B. Kontostand)
    try:
        print("\nRufe Kontostände ab...")
        account_balances = await client.get_account_balances()
        account_balances_json = account_balances.model_dump_json(indent=4)
        print("Kontostände (JSON):\n", account_balances_json)
        print("\n")

        for balance in account_balances.values:
            account_id = balance.account_id
            balance_value = balance.balance.value
            currency = balance.balance.unit
            print(f"Account ID: {account_id}, Balance: {balance_value} {currency}")

    except Exception as e:
        print("Fehler beim Abrufen der Kontostände:", e)

    # 7️⃣ Depotinformationen abrufen
    try:
        print("\nRufe Depotinformationen ab...")
        account_depots = await client.get_account_depots()
        account_depots_json = account_depots.model_dump_json(indent=4)
        print("Depots:\n", account_depots_json)

        for depot in account_depots.values:
            print("Depotinformationen\n", depot)
            depot_id = depot.depot_id
            depot_display_id = depot.depot_display_id
            depot_type = depot.depot_type
            target_market = depot.target_market

            print(f"Depot ID: {depot_id}")
            print(f"Depot Display ID: {depot_display_id}")
            print(f"Depot Type: {depot_type}")
            print(f"Target Market: {target_market}")

    except Exception as e:
        print("Fehler beim Abrufen der Depots:", e)


if __name__ == "__main__":
    asyncio.run(main())
