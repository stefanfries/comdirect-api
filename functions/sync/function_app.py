"""Azure HTTP-triggered Function — Comdirect sync entry point."""

import asyncio
import json
import logging

import azure.functions as func

from comdirect_api.client import ComdirectClient
from functions.sync.mongo_repo import MongoRepo
from functions.sync.settings import settings
from functions.sync.sync_service import SyncService

logger = logging.getLogger(__name__)

# Module-level singleton — connection pool is created once per cold start
# and reused across all warm invocations (recommended by MongoDB).
_repo = MongoRepo(
    connection_string=settings.mongodb_connection_string.get_secret_value(),
    database=settings.mongodb_database,
)

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="sync", methods=["POST"])
async def comdirect_sync(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP POST /api/sync

    Triggers a full Comdirect → MongoDB Atlas sync:
      - Account balances (insert snapshot if changed, touch last_synced_at otherwise)
      - Depot positions (upsert, quantity_history on buy/sell)
      - Depot transactions (insert-only, idempotent)

    Returns a JSON summary of what was synced.
    Authentication requires the Function key in the `x-functions-key` header
    or `code` query parameter (Azure default for AuthLevel.FUNCTION).
    """
    logger.info("Sync triggered")

    try:
        await _repo.initialize()

        # Sequential authentication — one push TAN approval per account
        clients: dict[str, ComdirectClient] = {}
        for name, account in settings.accounts.items():
            logger.info("Authenticating %s...", name)
            client = await ComdirectClient.create(
                zugangsnummer=account.zugangsnummer.get_secret_value(),
                pin=account.pin.get_secret_value(),
            )
            clients[name] = client

        # Parallel sync across all authenticated clients
        tasks = [
            SyncService(
                client,
                _repo,
                account_name=name,
                display_name=settings.accounts[name].display_name,
            ).run_full_sync()
            for name, client in clients.items()
        ]
        results_list = await asyncio.gather(*tasks)
        result = dict(zip(clients.keys(), results_list))

    except Exception as exc:
        logger.exception("Sync failed: %s", exc)
        return func.HttpResponse(
            json.dumps({"error": str(exc)}),
            status_code=500,
            mimetype="application/json",
        )

    return func.HttpResponse(
        json.dumps(result, default=str),
        status_code=200,
        mimetype="application/json",
    )
