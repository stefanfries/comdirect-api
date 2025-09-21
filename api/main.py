import asyncio
import os

import dotenv

from api.client import ComdirectClient


async def main():
    dotenv.load_dotenv()
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    zugangsnummer = os.getenv("ZUGANGSNUMMER")
    pin = os.getenv("PIN")

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

    """
    Hinweis: Der Banking/Brokerage Access Token (cd_secondary) wird benötigt für
    unkritische Banking-Anfragen (z. B. Kontostand abfragen). Kritische Aktionen (z. B. Überweisung)
    benötigen zusätzlich eine TAN (2FA).
    """

    # 4️⃣ TAN (2FA) aktivieren – optional für kritische Aktionen
    if not client.activated_2FA:
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
        account_balances = await client.get_account_balances()
        print("Kontostände:\n", account_balances)
    except Exception as e:
        print("Fehler beim Abrufen der Kontostände:", e)

    for account_balance in account_balances.get("values", []):
        account_id = account_balance.get("accountId")
        balance = account_balance.get("balance", {}).get("value")
        currency = account_balance.get("balance", {}).get("unit")
        print(f"Account ID: {account_id}, Balance: {balance} {currency}")


if __name__ == "__main__":
    asyncio.run(main())
