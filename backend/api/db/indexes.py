from pymongo import ASCENDING, DESCENDING
from pymongo.asynchronous.database import AsyncDatabase

from api.repositories.quotes_repository import COLLECTION


async def ensure_indexes(db: AsyncDatabase) -> None:
    """Create indexes at startup (no migrations). Safe to run on every start."""
    quotes = db[COLLECTION]
    # Dashboard: newest first.
    await quotes.create_index([("created_at", DESCENDING)])
    # Status filter, and the worker's "oldest queued" lookup. Its prefix also serves
    # plain status filters, so no separate status-only index is needed.
    await quotes.create_index([("status", ASCENDING), ("created_at", ASCENDING)])
