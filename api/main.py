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
    print(client)
    _ = input("Press Enter to continue...")
    data = await client.authenticate(username=zugangsnummer, password=pin)
    print(data)
    _ = input("Press Enter to continue...")
    data = await client.get_session_status()
    print(data)
    _ = input("Press Enter to continue...")
    data = await client.validate_session_tan()
    print(data)


if __name__ == "__main__":
    asyncio.run(main())
