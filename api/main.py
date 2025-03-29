from api.auth import ComdirectAuth
import asyncio
import dotenv
import os   


async def main():
    dotenv.load_dotenv()
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    username = os.getenv("ZUGANGSNUMMER")
    password = os.getenv("PASSWORD")
    print(f"Client ID: {client_id}")
    print(f"Client Secret: {client_secret}")
    print(f"Username: {username}")
    print(f"Password: {password}")
    auth = ComdirectAuth(client_id, client_secret)
    data = await auth.authenticate()
    print(data)


if __name__ == "__main__":
    asyncio.run(main())