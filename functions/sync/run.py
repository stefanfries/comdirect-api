"""Standalone entrypoint for the Comdirect → MongoDB Atlas sync.

Run from the project root:
    uv run python -m functions.sync.run

Required environment variables (or .env file):
    CLIENT_ID, CLIENT_SECRET, ZUGANGSNUMMER, PIN
    MONGODB_CONNECTION_STRING, MONGODB_DATABASE (default: finance)
"""

import asyncio
import json
import logging
import sys

from comdirect_api.client import ComdirectClient
from functions.sync.mongo_repo import MongoRepo
from functions.sync.settings import settings
from functions.sync.sync_service import SyncService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    repo = MongoRepo(
        connection_string=settings.mongodb_connection_string.get_secret_value(),
        database=settings.mongodb_database,
    )
    try:
        logger.info("Authenticating with Comdirect API (approve push TAN on your phone)...")
        client = await ComdirectClient.create()
        service = SyncService(client, repo)
        result = await service.run_full_sync()
        print(json.dumps(result, default=str, indent=2))
        logger.info("Sync completed successfully")
    finally:
        repo.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        logger.exception("Sync failed: %s", exc)
        sys.exit(1)
