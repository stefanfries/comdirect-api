"""Report held_since_date per depot position from the latest snapshot in Atlas.

Positions without a date are listed with their stored transactions, which shows
whether the entry event is simply outside the API's retrievable history window.

    uv run --extra sync python -m examples.check_held_since
"""

import asyncio

from pymongo.asynchronous.mongo_client import AsyncMongoClient

from functions.sync.settings import settings


async def main() -> None:
    client = AsyncMongoClient(settings.mongodb_connection_string.get_secret_value())
    db = client[settings.mongodb_database]

    cursor = await db["depot_snapshots"].aggregate([
        {"$sort": {"recorded_at": -1}},
        {"$group": {"_id": "$depot_id", "doc": {"$first": "$$ROOT"}}},
    ])
    async for snap in cursor:
        doc = snap["doc"]
        print(
            f"\n=== depot {doc['depot_id']} ({doc.get('display_name')}) "
            f"recorded_at={doc.get('recorded_at')} last_synced_at={doc.get('last_synced_at')}"
        )
        for pos in doc.get("positions", []):
            print(
                f"  {pos.get('wkn'):<8} held_since={str(pos.get('held_since_date')):<12} "
                f"entry_price={pos.get('purchase_price_at_entry', {}).get('value')} "
                f"qty={pos.get('quantity', {}).get('value')}"
            )
            if pos.get("held_since_date") is None:
                txns = await db["transactions"].find(
                    {"wkn": pos.get("wkn")}
                ).sort("booking_date", 1).to_list(length=None)
                for txn in txns:
                    print(
                        f"      stored txn: {txn.get('booking_date')} "
                        f"{txn.get('transaction_type')} qty={txn.get('quantity')}"
                    )

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
