from typing import Annotated

from fastapi import Depends, Request
from pymongo.asynchronous.database import AsyncDatabase

from api.config import Settings
from api.repositories.quotes_repository import QuotesRepository
from api.services.quotes_service import QuotesService


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> AsyncDatabase:
    return request.app.state.db


def get_quotes_service(
    db: Annotated[AsyncDatabase, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> QuotesService:
    return QuotesService(QuotesRepository(db), settings)
