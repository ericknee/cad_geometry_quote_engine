from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from api.config import Settings


def create_client(settings: Settings) -> AsyncMongoClient:
    """One client per process; it keeps its own connection pool. UTC-aware datetimes."""
    return AsyncMongoClient(settings.mongodb_uri, tz_aware=True)


def get_database(client: AsyncMongoClient, settings: Settings) -> AsyncDatabase:
    return client[settings.mongodb_db]
