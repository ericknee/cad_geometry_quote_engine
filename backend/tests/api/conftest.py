import uuid
from collections.abc import AsyncIterator

import pytest
from api.config import Settings
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import PyMongoError


@pytest.fixture
async def mongo_db() -> AsyncIterator[AsyncDatabase]:
    """A throwaway database on the real MongoDB (`docker compose up -d mongo`).
    Tests that use it are skipped when MongoDB is not reachable."""
    client = AsyncMongoClient(Settings().mongodb_uri, tz_aware=True, serverSelectionTimeoutMS=500)
    try:
        await client.admin.command("ping")
    except PyMongoError:
        await client.close()
        pytest.skip("MongoDB is not running (start it with: docker compose up -d mongo)")
    db = client[f"vendra_test_{uuid.uuid4().hex[:8]}"]
    yield db
    await client.drop_database(db.name)
    await client.close()
