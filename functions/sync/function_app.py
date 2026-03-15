"""Azure HTTP-triggered Function — Comdirect sync entry point."""

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
        client = await ComdirectClient.create()
        service = SyncService(client, _repo)
        result = await service.run_full_sync()
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
