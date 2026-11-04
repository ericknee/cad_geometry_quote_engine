from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/quotes", tags=["quotes"])

_NOT_IMPLEMENTED = HTTPException(status_code=501, detail="Not implemented yet")


@router.post("", status_code=201)
async def create_quote() -> None:
    raise _NOT_IMPLEMENTED


@router.get("")
async def list_quotes() -> None:
    raise _NOT_IMPLEMENTED


@router.get("/{quote_id}")
async def get_quote(quote_id: str) -> None:
    raise _NOT_IMPLEMENTED


@router.patch("/{quote_id}/status")
async def update_quote_status(quote_id: str) -> None:
    raise _NOT_IMPLEMENTED
