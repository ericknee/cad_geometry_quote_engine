from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from api.config import Settings
from api.errors.quotes_errors import AnalysisCrashed, AnalysisFailed
from api.repositories.quotes_repository import QuotesRepository
from api.services.quotes_service import QuotesService
from bson import ObjectId
from geometry.analyzer import analyze_file

GEAR = Path(__file__).resolve().parents[3] / "samples" / "vendra-gear.STEP"
SETTINGS = Settings(max_job_retries=3, stale_job_minutes=5)


class ScriptedAnalyzer:
    """Plays back a list of outcomes (exceptions are raised), then crashes forever."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    async def __call__(self, path, timeout):
        self.calls += 1
        outcome = self.outcomes.pop(0) if self.outcomes else AnalysisCrashed("boom")
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@pytest.fixture
async def repo(mongo_db) -> QuotesRepository:
    return QuotesRepository(mongo_db)


def _service(repo, analyzer) -> QuotesService:
    return QuotesService(repo, SETTINGS, analyze=analyzer)


async def _queue(repo, quantity=10) -> str:
    quote = await repo.insert_queued(
        file_name="gear.step",
        file_path=str(GEAR),
        file_hash="h",
        quantity=quantity,
        material="6061 Aluminum",
    )
    return quote["id"]


async def test_nothing_queued_returns_false(repo):
    assert await _service(repo, ScriptedAnalyzer()).process_next_job() is False


async def test_success_prices_and_stores_the_quote(repo):
    quote_id = await _queue(repo, quantity=10)
    analyzer = ScriptedAnalyzer(analyze_file(GEAR))
    assert await _service(repo, analyzer).process_next_job() is True

    quote = await repo.find_by_id(quote_id)
    assert quote["status"] == "quoted"
    assert quote["attempts"] == 1
    assert quote["cost_breakdown"]["quantity"] == 10
    assert quote["cost_breakdown"]["discount"]["rate"] == 0.10
    assert quote["lead_time_days"] == quote["lead_time"]["days"]


async def test_bad_file_fails_immediately_without_retry(repo):
    quote_id = await _queue(repo)
    analyzer = ScriptedAnalyzer(AnalysisFailed("NO_SOLIDS", "no solids"))
    await _service(repo, analyzer).process_next_job()

    quote = await repo.find_by_id(quote_id)
    assert (quote["status"], quote["attempts"], analyzer.calls) == ("failed", 1, 1)
    assert quote["error"] == {"code": "NO_SOLIDS", "message": "no solids"}


async def test_crash_is_retried_until_three_retries_are_used_up(repo):
    quote_id = await _queue(repo)
    analyzer = ScriptedAnalyzer()  # crashes every time
    service = _service(repo, analyzer)

    for expected_attempt in (1, 2, 3):  # first try and two retries: back in the queue
        await service.process_next_job()
        quote = await repo.find_by_id(quote_id)
        assert (quote["status"], quote["attempts"]) == ("queued", expected_attempt)

    await service.process_next_job()  # third retry (4th attempt) crashes too
    quote = await repo.find_by_id(quote_id)
    assert (quote["status"], quote["attempts"], analyzer.calls) == ("failed", 4, 4)
    assert quote["error"]["code"] == "ANALYSIS_CRASHED"
    assert "4 attempts" in quote["error"]["message"]
    assert await service.process_next_job() is False  # nothing left to retry


async def test_crash_then_success_is_quoted(repo):
    quote_id = await _queue(repo)
    analyzer = ScriptedAnalyzer(AnalysisCrashed("one-off"), analyze_file(GEAR))
    service = _service(repo, analyzer)
    await service.process_next_job()
    await service.process_next_job()

    quote = await repo.find_by_id(quote_id)
    assert (quote["status"], quote["attempts"]) == ("quoted", 2)


async def test_unexpected_error_fails_the_quote_instead_of_leaving_it_processing(repo):
    quote_id = await _queue(repo)
    await _service(repo, ScriptedAnalyzer(RuntimeError("bug"))).process_next_job()

    quote = await repo.find_by_id(quote_id)
    assert quote["status"] == "failed"
    assert quote["error"]["code"] == "INTERNAL_ERROR"


async def test_recover_stale_jobs_uses_the_retry_limit(repo, mongo_db):
    keep, lost = await _queue(repo), await _queue(repo)
    await repo.claim_next_queued()
    await repo.claim_next_queued()
    old = datetime.now(UTC) - timedelta(hours=1)
    quotes = mongo_db["quotes"]
    await quotes.update_one({"_id": ObjectId(keep)}, {"$set": {"started_at": old}})
    await quotes.update_one({"_id": ObjectId(lost)}, {"$set": {"started_at": old, "attempts": 4}})

    assert await _service(repo, ScriptedAnalyzer()).recover_stale_jobs() == (1, 1)
    assert (await repo.find_by_id(keep))["status"] == "queued"
    failed = await repo.find_by_id(lost)
    assert (failed["status"], failed["error"]["code"]) == ("failed", "JOB_ABANDONED")


async def test_end_to_end_with_a_real_child_process(repo):
    quote_id = await _queue(repo, quantity=1)
    await QuotesService(repo, SETTINGS).process_next_job()  # default analyzer = real subprocess

    quote = await repo.find_by_id(quote_id)
    assert quote["status"] == "quoted"
    assert quote["cost_breakdown"]["total_cost_per_unit"] == pytest.approx(204.38, abs=0.01)
