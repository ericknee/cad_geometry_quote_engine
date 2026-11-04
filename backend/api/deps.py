from fastapi import Request
from pymongo.asynchronous.database import AsyncDatabase

from api.config import Settings


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> AsyncDatabase:
    return request.app.state.db
