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

    client = ComdirectClient(client_id=client_id, client_secret=client_secret)
    data = await client.authenticate(username=zugangsnummer, password=pin)
    data = await client.get_session_status()
    data = await client.validate_session_tan()
    print(f"Validated session TAN: {data}")
    print(f"Session ID: {client.session_id}")
    print(f"Access Token: {client.access_token}")
    print(f"Refresh Token: {client.refresh_token}")
    print(f"Token Expires At: {client.token_expires_at}")
    print(f"Token Expired: {client.is_token_expired()}")


if __name__ == "__main__":
    asyncio.run(main())
