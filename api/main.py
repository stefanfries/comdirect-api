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

    client = ComdirectClient(client_id=client_id, client_secret=client_secret)
    print(client)
    data = await client.authenticate(username=zugangsnummer, password=pin)
    print(data)
    data = await client.get_session_status()
    print(data)
    # data = await client.validate_session_tan()
    # print(data)


if __name__ == "__main__":
    asyncio.run(main())
