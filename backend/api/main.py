from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.config import Settings
from api.db.database import check_connection, create_client, get_database
from api.db.indexes import ensure_indexes
from api.errors.quotes_errors import QuoteError
from api.routers.quotes_router import router as quotes_router
from api.utils.body_limit import BodyLimitMiddleware

API_PREFIX = "/api"


def _error_response(
    status: int, code: str, message: str, headers: Mapping[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message}},
        headers=dict(headers) if headers else None,
    )


def _validation_message(error: RequestValidationError) -> str:
    """First problem only, as 'field: reason', so the UI can show one readable line."""
    first = error.errors()[0]
    field = ".".join(str(part) for part in first["loc"] if part not in ("body", "query", "path"))
    return f"{field}: {first['msg']}" if field else str(first["msg"])


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        client = create_client(settings)
        try:
            await check_connection(client)
            app.state.db = get_database(client, settings)
            await ensure_indexes(app.state.db)
            settings.upload_path.mkdir(parents=True, exist_ok=True)
            yield
        finally:
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
    app.add_middleware(BodyLimitMiddleware, max_bytes=settings.max_upload_mb * 1024 * 1024)

    # Every error leaves the API in one shape: { "error": { "code", "message" } }.
    @app.exception_handler(QuoteError)
    async def quote_error_handler(_: Request, error: QuoteError) -> JSONResponse:
        return _error_response(error.http_status, error.code, error.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, error: RequestValidationError) -> JSONResponse:
        return _error_response(422, "VALIDATION_ERROR", _validation_message(error))

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(_: Request, error: StarletteHTTPException) -> JSONResponse:
        # Keep the error's own headers, e.g. `Allow` on a 405.
        return _error_response(
            error.status_code, f"HTTP_{error.status_code}", str(error.detail), error.headers
        )

    @app.get(f"{API_PREFIX}/health")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    app.include_router(quotes_router, prefix=API_PREFIX)
    return app


app = create_app()
