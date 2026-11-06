"""Quote workflow: validate, store file, analyze, price, save. Owns the rules."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from geometry.models import GeometryResult
from pricing import PricingConfig, lead_time, price

from api.config import Settings
from api.errors.quotes_errors import (
    AnalysisCrashed,
    AnalysisFailed,
    InvalidQuantity,
    InvalidStatusTransition,
    QuoteNotFound,
    StatusConflict,
)
from api.repositories.quotes_repository import Document, QuotesRepository
from api.types.quotes_types import (
    ErrorDetail,
    QuoteDetail,
    QuoteList,
    QuoteStatus,
    QuoteSummary,
    SortOrder,
)
from api.utils.file_storage import Upload, delete_file, save_upload
from api.utils.geometry_runner import analyze_in_subprocess

logger = logging.getLogger(__name__)

Analyzer = Callable[[Path, float], Awaitable[GeometryResult]]

CRASHED = "ANALYSIS_CRASHED"
ABANDONED = "JOB_ABANDONED"
INTERNAL = "INTERNAL_ERROR"

MATERIAL = "6061 Aluminum"
MIN_QUANTITY = 1
MAX_QUANTITY = 10_000

# New status -> statuses it may be set from. Only a reviewer's choices appear here; queued,
# processing, failed and quoted are set by the system. A quote mid-job cannot be archived.
ALLOWED_TRANSITIONS: dict[QuoteStatus, frozenset[QuoteStatus]] = {
    QuoteStatus.REVIEWED: frozenset({QuoteStatus.QUOTED}),
    QuoteStatus.ARCHIVED: frozenset({QuoteStatus.QUOTED, QuoteStatus.REVIEWED, QuoteStatus.FAILED}),
}


class QuotesService:
    def __init__(
        self,
        repo: QuotesRepository,
        settings: Settings,
        pricing_config: PricingConfig | None = None,
        analyze: Analyzer = analyze_in_subprocess,
    ) -> None:
        self._repo = repo
        self._settings = settings
        self._pricing = pricing_config or PricingConfig()
        self._analyze = analyze  # replaceable in tests

    async def create_quote(self, upload: Upload, quantity: int) -> QuoteDetail:
        """Check the request, keep the file and queue the quote. The worker does the rest.
        Cheap checks fail here and save nothing."""
        if not MIN_QUANTITY <= quantity <= MAX_QUANTITY:
            raise InvalidQuantity(f"Quantity must be between {MIN_QUANTITY} and {MAX_QUANTITY}.")
        stored = await save_upload(
            upload, self._settings.upload_path, self._settings.max_upload_mb * 1024 * 1024
        )
        try:
            doc = await self._repo.insert_queued(
                file_name=stored.file_name,
                file_path=stored.file_path,
                file_hash=stored.file_hash,
                quantity=quantity,
                material=MATERIAL,
            )
        except BaseException:
            delete_file(stored.file_path)  # no quote points at the file, so do not keep it
            raise
        return QuoteDetail.model_validate(doc)

    async def get_quote(self, quote_id: str) -> QuoteDetail:
        doc = await self._repo.find_by_id(quote_id)
        if doc is None:
            raise QuoteNotFound("Quote not found.")
        return QuoteDetail.model_validate(doc)

    async def list_quotes(
        self,
        status: QuoteStatus | None,
        limit: int,
        skip: int,
        *,
        exclude_archived: bool = False,
        sort: SortOrder = SortOrder.NEWEST,
    ) -> QuoteList:
        # The page and the total are independent queries, so run them together.
        docs, total = await asyncio.gather(
            self._repo.list_page(status, limit, skip, exclude_archived=exclude_archived, sort=sort),
            self._repo.count(status, exclude_archived=exclude_archived),
        )
        items = [QuoteSummary.from_document(doc) for doc in docs]
        return QuoteList(items=items, total=total, limit=limit, skip=skip)

    async def update_status(self, quote_id: str, new: QuoteStatus) -> QuoteDetail:
        """A reviewer's status change, limited to ALLOWED_TRANSITIONS."""
        quote = await self._repo.find_by_id(quote_id)
        if quote is None:
            raise QuoteNotFound("Quote not found.")
        current = QuoteStatus(quote["status"])
        if current is new and new in ALLOWED_TRANSITIONS:
            return QuoteDetail.model_validate(quote)  # already there: a retried request is a no-op
        if current not in ALLOWED_TRANSITIONS.get(new, frozenset()):
            raise InvalidStatusTransition(f"A {current.value} quote cannot be set to {new.value}.")
        updated = await self._repo.transition_status(quote_id, current, new)
        if updated is None:
            # The status moved on since we read it (e.g. a reviewer in another tab).
            if await self._repo.find_by_id(quote_id) is None:
                raise QuoteNotFound("Quote not found.")
            raise StatusConflict("The quote changed while you were updating it. Reload and retry.")
        if new is QuoteStatus.ARCHIVED:
            self._discard_file(quote_id, quote["file_path"])
        return QuoteDetail.model_validate(updated)

    @staticmethod
    def _discard_file(quote_id: str, file_path: str) -> None:
        """Archiving ends the quote, so its STEP file is no longer needed. Best effort: a file
        that cannot be removed is logged and left behind, it must not fail the status change.
        Failed quotes keep their file so they can be retried. The path and hash stay in the
        database."""
        try:
            delete_file(file_path)
        except OSError:
            logger.exception("Quote %s: could not delete %s", quote_id, file_path)

    @property
    def _max_attempts(self) -> int:
        # The first try plus up to max_job_retries retries.
        return 1 + self._settings.max_job_retries

    async def process_next_job(self) -> bool:
        """Take the oldest queued quote and finish it. Returns False if nothing was queued.

        Every outcome leaves the quote in a final or queued state, never stuck in `processing`:
        - priced             -> quoted
        - bad file           -> failed (not retried: it would fail the same way again)
        - analysis crashed   -> back in the queue, or failed once the retries are used up
        - unexpected error   -> failed
        """
        quote = await self._repo.claim_next_queued()
        if quote is None:
            return False
        quote_id = quote["id"]
        attempt = quote["attempts"]
        try:
            geometry = await self._analyze(
                Path(quote["file_path"]), self._settings.analysis_timeout_seconds
            )
            cost = price(geometry, quote["quantity"], self._pricing)
            lead = lead_time(geometry, quote["quantity"], self._pricing)
        except AnalysisFailed as error:
            self._log_if_lost(
                quote_id,
                await self._repo.save_failure(
                    quote_id, ErrorDetail(code=error.code, message=error.message), attempt=attempt
                ),
            )
        except AnalysisCrashed as error:
            await self._handle_crash(quote, error)
        except Exception as error:  # Anything unexpected still ends the job cleanly.
            logger.exception("Unexpected error while processing quote %s", quote_id)
            self._log_if_lost(
                quote_id,
                await self._repo.save_failure(
                    quote_id,
                    ErrorDetail(code=INTERNAL, message=f"{type(error).__name__}: {error}"),
                    attempt=attempt,
                ),
            )
        else:
            self._log_if_lost(
                quote_id,
                await self._repo.save_result(quote_id, geometry, cost, lead, attempt=attempt),
            )
        return True

    @staticmethod
    def _log_if_lost(quote_id: str, saved: Document | None) -> None:
        """Log a write that was refused because the job is no longer ours."""
        if saved is None:
            logger.warning("Quote %s: result discarded, the job was taken over meanwhile", quote_id)

    async def _handle_crash(self, quote: Document, error: AnalysisCrashed) -> None:
        attempts = quote["attempts"]
        if attempts < self._max_attempts:
            logger.warning(
                "Quote %s: analysis crashed (attempt %d of %d), retrying: %s",
                quote["id"],
                attempts,
                self._max_attempts,
                error,
            )
            saved = await self._repo.release_for_retry(quote["id"], attempt=attempts)
        else:
            saved = await self._repo.save_failure(
                quote["id"],
                ErrorDetail(
                    code=CRASHED,
                    message=f"The file could not be analyzed after {attempts} attempts. {error}",
                ),
                attempt=attempts,
            )
        self._log_if_lost(quote["id"], saved)

    async def recover_stale_jobs(self) -> tuple[int, int]:
        """Recover jobs whose worker died. Returns (requeued, failed)."""
        cutoff = datetime.now(UTC) - timedelta(minutes=self._settings.stale_job_minutes)
        return await self._repo.recover_stale(
            cutoff,
            self._max_attempts,
            ErrorDetail(
                code=ABANDONED,
                message="The analysis kept being interrupted before it could finish.",
            ),
        )
