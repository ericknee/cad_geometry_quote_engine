from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from api.deps import get_quotes_service
from api.services.quotes_service import QuotesService
from api.types.quotes_types import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    ErrorResponse,
    QuoteDetail,
    QuoteList,
    QuoteStatus,
    StatusUpdate,
)

router = APIRouter(prefix="/quotes", tags=["quotes"])

Service = Annotated[QuotesService, Depends(get_quotes_service)]

_ERRORS = {"model": ErrorResponse}


@router.post(
    "",
    status_code=202,
    response_model=QuoteDetail,
    responses={422: _ERRORS},
    summary="Upload a STEP file and queue a quote (poll GET /quotes/{id} for the result)",
)
async def create_quote(
    service: Service,
    file: Annotated[UploadFile, File()],
    # The range is checked in the service so a bad quantity gets the INVALID_QUANTITY code.
    quantity: Annotated[int, Form()],
) -> QuoteDetail:
    return await service.create_quote(file, quantity)


@router.get("", response_model=QuoteList, responses={422: _ERRORS})
async def list_quotes(
    service: Service,
    status: QuoteStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    skip: Annotated[int, Query(ge=0)] = 0,
    # Hides archived quotes from the unfiltered list; ignored when `status` is given.
    exclude_archived: bool = False,
) -> QuoteList:
    return await service.list_quotes(status, limit, skip, exclude_archived=exclude_archived)


@router.get("/{quote_id}", response_model=QuoteDetail, responses={404: _ERRORS})
async def get_quote(quote_id: str, service: Service) -> QuoteDetail:
    return await service.get_quote(quote_id)


@router.patch(
    "/{quote_id}/status",
    response_model=QuoteDetail,
    responses={404: _ERRORS, 409: _ERRORS, 422: _ERRORS},
)
async def update_quote_status(quote_id: str, body: StatusUpdate, service: Service) -> QuoteDetail:
    return await service.update_status(quote_id, body.status)
