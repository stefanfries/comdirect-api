import asyncio
import os

import dotenv

from .client import ComdirectClient
from .core.settings import settings


async def main():

    client_id = settings.CLIENT_ID.get_secret_value()
    client_secret = settings.CLIENT_SECRET.get_secret_value()
    zugangsnummer = settings.ZUGANGSNUMMER.get_secret_value()
    pin = settings.PIN.get_secret_value()

    if not all([client_id, client_secret, zugangsnummer, pin]):
        raise ValueError(
            "Missing required environment variables: CLIENT_ID, CLIENT_SECRET, ZUGANGSNUMMER, or PIN"
        )

    # Use type assertions to inform the type checker that these are not None
    assert client_id is not None
    assert client_secret is not None
    assert zugangsnummer is not None
    assert pin is not None

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

    except Exception as e:
        print("Fehler beim Abrufen der Kontostände:", e)

    for balance in account_balances.values:
        account_id = balance.accountId
        balance_value = balance.balance.value
        currency = balance.balance.unit
        print(f"Account ID: {account_id}, Balance: {balance_value} {currency}")

    # 7️⃣ Depotinformationen abrufen
    try:
        print("\nRufe Depotinformationen ab...")
        account_depots = await client.get_account_depots()
        account_depots_json = account_depots.model_dump_json(indent=4)
        print("Depots:\n", account_depots_json)
    except Exception as e:
        print("Fehler beim Abrufen der Depots:", e)

    for depot in account_depots.values:
        print("Depotinformationen\n", depot)
        depot_id = depot.depotId
        depot_display_id = depot.depotDisplayId
        depot_type = depot.depotType
        target_market = depot.targetMarket

        print(f"Depot ID: {depot_id}")
        print(f"Depot Display ID: {depot_display_id}")
        print(f"Depot Type: {depot_type}")
        print(f"Target Market: {target_market}")


if __name__ == "__main__":
    asyncio.run(main())
