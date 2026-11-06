import asyncio
import logging

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import PyMongoError

from api.config import Settings

logger = logging.getLogger(__name__)


def create_client(settings: Settings) -> AsyncMongoClient:
    """One client per process; it keeps its own connection pool. UTC-aware datetimes."""
    return AsyncMongoClient(settings.mongodb_uri, tz_aware=True, serverSelectionTimeoutMS=5000)


async def check_connection(
    client: AsyncMongoClient, attempts: int = 6, delay_seconds: float = 2.0
) -> None:
    """Wait for MongoDB at startup: each try fails after 5 s, so about 40 s in total before
    giving up with a clear message. Covers `docker compose up` starting the API first."""
    for attempt in range(1, attempts + 1):
        try:
            await client.admin.command("ping")
            return
        except PyMongoError as error:
            if attempt == attempts:
                raise RuntimeError(f"Cannot reach MongoDB: {error}") from error
            logger.warning("MongoDB not ready (try %d of %d), retrying", attempt, attempts)
            await asyncio.sleep(delay_seconds)


def get_database(client: AsyncMongoClient, settings: Settings) -> AsyncDatabase:
    return client[settings.mongodb_db]
