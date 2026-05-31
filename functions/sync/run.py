"""Standalone entrypoint for the Comdirect → MongoDB Atlas sync.

Run from the project root:
    uv run python -m functions.sync.run
    uv run python -m functions.sync.run --accounts DEPOT11,DEPOT22

Required environment variables (or .env file):
    CLIENT_ID, CLIENT_SECRET
    ACCOUNTS__<NAME>__ZUGANGSNUMMER, ACCOUNTS__<NAME>__PIN  (one pair per account)
    MONGODB_CONNECTION_STRING, MONGODB_DATABASE (default: finance)
"""

import argparse
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


def _parse_args() -> set[str] | None:
    """Return the set of account names to sync, or None to sync all."""
    parser = argparse.ArgumentParser(description="Comdirect → MongoDB Atlas sync")
    parser.add_argument(
        "--accounts",
        default="",
        help="Comma-separated account names to sync (e.g. DEPOT11,DEPOT22). "
             "Omit or leave blank to sync all configured accounts.",
    )
    args = parser.parse_args()
    if args.accounts.strip():
        return {name.strip() for name in args.accounts.split(",")}
    return None  # all accounts


async def main() -> None:
    selected = _parse_args()

    repo = MongoRepo(
        connection_string=settings.mongodb_connection_string.get_secret_value(),
        database=settings.mongodb_database,
    )
    await repo.initialize()

    try:
        # --- Sequential authentication (one push TAN approval at a time) ---
        clients: dict[str, ComdirectClient] = {}
        for name, account in settings.accounts.items():
            if selected is not None and name not in selected:
                logger.info("Skipping %s (not in --accounts filter)", name)
                continue
            logger.info("Authenticating %s — approve push TAN on your phone...", name)
            client = await ComdirectClient.create(
                zugangsnummer=account.zugangsnummer.get_secret_value(),
                pin=account.pin.get_secret_value(),
            )
            clients[name] = client
            logger.info("%s authenticated.", name)

        if not clients:
            logger.warning("No accounts matched. Check --accounts filter or .env configuration.")
            return

        # --- Parallel sync (all authenticated clients run concurrently) ---
        logger.info("Starting parallel sync for: %s", ", ".join(clients))
        tasks = [
            SyncService(client, repo, account_name=name).run_full_sync()
            for name, client in clients.items()
        ]
        results_list = await asyncio.gather(*tasks)
        result = dict(zip(clients.keys(), results_list))

        print(json.dumps(result, default=str, indent=2))
        logger.info("Sync completed successfully")
    finally:
        await repo.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        logger.exception("Sync failed: %s", exc)
        sys.exit(1)
