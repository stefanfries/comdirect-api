from api.client import ComdirectClient
import asyncio
import dotenv
import os   


async def main():
    dotenv.load_dotenv()
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    zugangsnummer = os.getenv("ZUGANGSNUMMER")
    pin = os.getenv("PIN")

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