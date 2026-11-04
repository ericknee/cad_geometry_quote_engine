from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.config import Settings
from api.db.database import create_client, get_database
from api.db.indexes import ensure_indexes
from api.routers.quotes_router import router as quotes_router

API_PREFIX = "/api"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        client = create_client(settings)
        app.state.db = get_database(client, settings)
        await ensure_indexes(app.state.db)
        yield
        await client.close()

    prod = settings.environment == "prod"
    app = FastAPI(
        title="Vendra Quoting Engine",
        lifespan=lifespan,
        docs_url=None if prod else "/docs",
        redoc_url=None if prod else "/redoc",
        openapi_url=None if prod else "/openapi.json",
    )
    app.state.settings = settings

    @app.get(f"{API_PREFIX}/health")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    app.include_router(quotes_router, prefix=API_PREFIX)
    return app


app = create_app()
