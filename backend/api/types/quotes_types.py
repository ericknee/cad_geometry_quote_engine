"""Request/response models for the quotes endpoints."""

from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum
from typing import Any, Self

from geometry.models import GeometryResult
from pricing.models import CostBreakdown, LeadTime
from pydantic import BaseModel, ConfigDict, Field

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


class QuoteStatus(StrEnum):
    # Set by the system while a job runs.
    QUEUED = "queued"
    PROCESSING = "processing"
    FAILED = "failed"
    # quoted is set by the worker; reviewed and archived are set by a reviewer.
    QUOTED = "quoted"
    REVIEWED = "reviewed"
    ARCHIVED = "archived"


class SortOrder(StrEnum):
    """Order of the quote list, by creation time."""

    NEWEST = "newest"
    OLDEST = "oldest"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class ErrorDetail(_Frozen):
    """The `error` object of every error response, and the reason a quote `failed`."""

    code: str
    message: str


class ErrorResponse(_Frozen):
    error: ErrorDetail


class QuoteDetail(_Frozen):
    """One quote. Geometry, cost and lead time exist only once the quote is `quoted`
    (or later); `error` exists only when it `failed`."""

    id: str
    file_name: str
    file_hash: str
    quantity: int = Field(ge=1)
    material: str
    status: QuoteStatus
    geometry: GeometryResult | None = None
    cost_breakdown: CostBreakdown | None = None
    lead_time: LeadTime | None = None
    # Same value as lead_time.days, kept top-level for the dashboard (PRD field name).
    lead_time_days: int | None = None
    error: ErrorDetail | None = None
    created_at: datetime
    updated_at: datetime


class QuoteSummary(_Frozen):
    """One dashboard row."""

    id: str
    file_name: str
    quantity: int
    status: QuoteStatus
    total_cost_per_unit: float | None = None
    total_order_cost: float | None = None
    lead_time_days: int | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_document(cls, doc: Mapping[str, Any]) -> Self:
        """Build a row from a stored quote (a full one or the slim list projection), so the
        list never has to parse geometry. Only `cost_breakdown`'s two totals are read."""
        cost = doc.get("cost_breakdown") or {}
        return cls(
            id=doc["id"],
            file_name=doc["file_name"],
            quantity=doc["quantity"],
            status=doc["status"],
            total_cost_per_unit=cost.get("total_cost_per_unit"),
            total_order_cost=cost.get("total_order_cost"),
            lead_time_days=doc.get("lead_time_days"),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
        )


class QuoteList(_Frozen):
    items: list[QuoteSummary]
    total: int  # all quotes matching the filter, not just this page
    limit: int
    skip: int


class StatusUpdate(_Frozen):
    # Any QuoteStatus parses; the service rejects ones a user may not set (see transitions).
    status: QuoteStatus
