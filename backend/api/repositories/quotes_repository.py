"""Mongo queries and writes for the `quotes` collection. No rules, no HTTP.

Documents come back as plain dicts with `id` (a string) in place of `_id`. They include the
internal `file_path`, which the service uses and never exposes.
"""

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from geometry.models import GeometryResult
from pricing.models import CostBreakdown, LeadTime
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.asynchronous.database import AsyncDatabase

from api.types.quotes_types import ErrorDetail, QuoteStatus, QuoteSummary

COLLECTION = "quotes"

Document = dict[str, Any]

# Fields of a dashboard row. Taken from QuoteSummary so a new field is fetched automatically;
# its two prices live inside cost_breakdown, so only those are fetched (_id comes by default).
_COST_FIELDS = ("total_cost_per_unit", "total_order_cost")
_SUMMARY_PROJECTION: dict[str, int] = {
    **{name: 1 for name in QuoteSummary.model_fields if name != "id" and name not in _COST_FIELDS},
    **{f"cost_breakdown.{name}": 1 for name in _COST_FIELDS},
}


def _now() -> datetime:
    return datetime.now(UTC)


def _to_document(raw: Document | None) -> Document | None:
    if raw is None:
        return None
    doc = dict(raw)
    doc["id"] = str(doc.pop("_id"))
    return doc


def _object_id(quote_id: str) -> ObjectId | None:
    return ObjectId(quote_id) if ObjectId.is_valid(quote_id) else None


class QuotesRepository:
    def __init__(self, db: AsyncDatabase) -> None:
        self._quotes = db[COLLECTION]

    async def insert_queued(
        self, *, file_name: str, file_path: str, file_hash: str, quantity: int, material: str
    ) -> Document:
        now = _now()
        doc = {
            "file_name": file_name,
            "file_path": file_path,
            "file_hash": file_hash,
            "quantity": quantity,
            "material": material,
            "status": QuoteStatus.QUEUED.value,
            "geometry": None,
            "cost_breakdown": None,
            "lead_time": None,
            "lead_time_days": None,
            "error": None,
            "attempts": 0,
            "created_at": now,
            "updated_at": now,
            "started_at": None,
        }
        result = await self._quotes.insert_one(doc)
        return _with_id(doc, result.inserted_id)

    async def find_by_id(self, quote_id: str) -> Document | None:
        oid = _object_id(quote_id)
        if oid is None:
            return None
        return _to_document(await self._quotes.find_one({"_id": oid}))

    async def list_page(self, status: QuoteStatus | None, limit: int, skip: int) -> list[Document]:
        """One page of quotes, newest first. Slim documents: only what a QuoteSummary needs
        (see _SUMMARY_PROJECTION), so the large geometry is never sent. Use find_by_id for all."""
        # _id breaks ties so pages stay stable when several quotes share a timestamp.
        cursor = (
            self._quotes.find(_status_filter(status), _SUMMARY_PROJECTION)
            .sort([("created_at", DESCENDING), ("_id", DESCENDING)])
            .skip(skip)
            .limit(limit)
        )
        return [_to_document(raw) async for raw in cursor]

    async def count(self, status: QuoteStatus | None) -> int:
        return await self._quotes.count_documents(_status_filter(status))

    async def transition_status(
        self, quote_id: str, current: QuoteStatus, new: QuoteStatus
    ) -> Document | None:
        """Change status only if it is still `current`. None: it changed meanwhile, or is gone."""
        oid = _object_id(quote_id)
        if oid is None:
            return None
        raw = await self._quotes.find_one_and_update(
            {"_id": oid, "status": current.value},
            {"$set": {"status": new.value, "updated_at": _now()}},
            return_document=ReturnDocument.AFTER,
        )
        return _to_document(raw)

    async def claim_next_queued(self) -> Document | None:
        """Take the quote that has waited longest in the queue and mark it processing, in one
        atomic step so two workers can never get the same one. Each claim counts as one attempt.

        Ordered by `updated_at` (equal to `created_at` for a new quote), so a quote released for
        retry goes to the back of the line instead of blocking the ones behind it."""
        now = _now()
        raw = await self._quotes.find_one_and_update(
            {"status": QuoteStatus.QUEUED.value},
            {
                "$set": {
                    "status": QuoteStatus.PROCESSING.value,
                    "started_at": now,
                    "updated_at": now,
                },
                "$inc": {"attempts": 1},
            },
            sort=[("updated_at", ASCENDING), ("_id", ASCENDING)],
            return_document=ReturnDocument.AFTER,
        )
        return _to_document(raw)

    async def save_result(
        self,
        quote_id: str,
        geometry: GeometryResult,
        cost_breakdown: CostBreakdown,
        lead_time: LeadTime,
        *,
        attempt: int,
    ) -> Document | None:
        """Store a finished quote. Only applies while the quote is still processing under the
        claim numbered `attempt` (a later claim by another worker is left alone)."""
        return await self._finish_job(
            quote_id,
            attempt,
            {
                "status": QuoteStatus.QUOTED.value,
                "geometry": geometry.model_dump(),
                "cost_breakdown": cost_breakdown.model_dump(),
                "lead_time": lead_time.model_dump(),
                "lead_time_days": lead_time.days,
                "error": None,
            },
        )

    async def save_failure(
        self, quote_id: str, error: ErrorDetail, *, attempt: int
    ) -> Document | None:
        return await self._finish_job(
            quote_id, attempt, {"status": QuoteStatus.FAILED.value, "error": error.model_dump()}
        )

    async def release_for_retry(self, quote_id: str, *, attempt: int) -> Document | None:
        """Put a processing quote back in the queue (its attempts so far are kept). Only applies
        under the claim numbered `attempt`."""
        oid = _object_id(quote_id)
        if oid is None:
            return None
        raw = await self._quotes.find_one_and_update(
            {"_id": oid, "status": QuoteStatus.PROCESSING.value, "attempts": attempt},
            {
                "$set": {
                    "status": QuoteStatus.QUEUED.value,
                    "started_at": None,
                    "updated_at": _now(),
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return _to_document(raw)

    async def recover_stale(
        self, started_before: datetime, max_attempts: int, abandoned: ErrorDetail
    ) -> tuple[int, int]:
        """Recover jobs that have been processing since before `started_before` (their worker
        most likely died). Jobs with attempts left go back in the queue; the rest are failed
        so a job that keeps killing its worker cannot loop forever. Returns (requeued, failed)."""
        stale = {"status": QuoteStatus.PROCESSING.value, "started_at": {"$lt": started_before}}
        now = _now()
        failed = await self._quotes.update_many(
            {**stale, "attempts": {"$gte": max_attempts}},
            {
                "$set": {
                    "status": QuoteStatus.FAILED.value,
                    "error": abandoned.model_dump(),
                    "updated_at": now,
                }
            },
        )
        requeued = await self._quotes.update_many(
            {**stale, "attempts": {"$lt": max_attempts}},
            {"$set": {"status": QuoteStatus.QUEUED.value, "started_at": None, "updated_at": now}},
        )
        return requeued.modified_count, failed.modified_count

    async def _finish_job(self, quote_id: str, attempt: int, fields: Document) -> Document | None:
        oid = _object_id(quote_id)
        if oid is None:
            return None
        raw = await self._quotes.find_one_and_update(
            {"_id": oid, "status": QuoteStatus.PROCESSING.value, "attempts": attempt},
            {"$set": {**fields, "updated_at": _now()}},
            return_document=ReturnDocument.AFTER,
        )
        return _to_document(raw)


def _status_filter(status: QuoteStatus | None) -> Document:
    return {} if status is None else {"status": status.value}


def _with_id(doc: Document, inserted_id: ObjectId) -> Document:
    result = dict(doc)
    result.pop("_id", None)  # insert_one adds _id to the dict it was given
    result["id"] = str(inserted_id)
    return result
