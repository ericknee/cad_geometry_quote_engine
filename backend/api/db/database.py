from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import PyMongoError

from api.config import Settings


def create_client(settings: Settings) -> AsyncMongoClient:
    """One client per process; it keeps its own connection pool. UTC-aware datetimes."""
    return AsyncMongoClient(settings.mongodb_uri, tz_aware=True, serverSelectionTimeoutMS=5000)


async def check_connection(client: AsyncMongoClient) -> None:
    """Fail at startup with a clear message if MongoDB is unreachable (5 s limit)."""
    try:
        await client.admin.command("ping")
    except PyMongoError as error:
        raise RuntimeError(f"Cannot reach MongoDB: {error}") from error


def get_database(client: AsyncMongoClient, settings: Settings) -> AsyncDatabase:
    return client[settings.mongodb_db]
