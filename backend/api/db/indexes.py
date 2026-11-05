from pymongo import ASCENDING, DESCENDING
from pymongo.asynchronous.database import AsyncDatabase

from api.repositories.quotes_repository import COLLECTION


async def ensure_indexes(db: AsyncDatabase) -> None:
    """Create indexes at startup (no migrations). Safe to run on every start."""
    quotes = db[COLLECTION]
    # Dashboard: newest first.
    await quotes.create_index([("created_at", DESCENDING)])
    # Status filter with newest-first listing. Its prefix also serves plain status filters.
    await quotes.create_index([("status", ASCENDING), ("created_at", ASCENDING)])
    # The worker's "longest waiting queued quote" lookup.
    await quotes.create_index([("status", ASCENDING), ("updated_at", ASCENDING)])
