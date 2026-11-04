"""Quote workflow: validate, store file, analyze, price, save. Owns the rules."""

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from geometry.models import GeometryResult
from pricing import PricingConfig, lead_time, price

from api.config import Settings
from api.errors.quotes_errors import AnalysisCrashed, AnalysisFailed
from api.repositories.quotes_repository import Document, QuotesRepository
from api.types.quotes_types import ErrorDetail
from api.utils.geometry_runner import analyze_in_subprocess

logger = logging.getLogger(__name__)

Analyzer = Callable[[Path, float], Awaitable[GeometryResult]]

CRASHED = "ANALYSIS_CRASHED"
ABANDONED = "JOB_ABANDONED"
INTERNAL = "INTERNAL_ERROR"


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
        try:
            geometry = await self._analyze(
                Path(quote["file_path"]), self._settings.analysis_timeout_seconds
            )
            cost = price(geometry, quote["quantity"], self._pricing)
            lead = lead_time(geometry, quote["quantity"], self._pricing)
        except AnalysisFailed as error:
            await self._repo.save_failure(
                quote_id, ErrorDetail(code=error.code, message=error.message)
            )
        except AnalysisCrashed as error:
            await self._handle_crash(quote, error)
        except Exception as error:  # Anything unexpected still ends the job cleanly.
            logger.exception("Unexpected error while processing quote %s", quote_id)
            await self._repo.save_failure(
                quote_id, ErrorDetail(code=INTERNAL, message=f"{type(error).__name__}: {error}")
            )
        else:
            await self._repo.save_result(quote_id, geometry, cost, lead)
        return True

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
            await self._repo.release_for_retry(quote["id"])
            return
        await self._repo.save_failure(
            quote["id"],
            ErrorDetail(
                code=CRASHED,
                message=f"The file could not be analyzed after {attempts} attempts. {error}",
            ),
        )

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
