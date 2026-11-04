import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from api.db.indexes import ensure_indexes
from api.repositories.quotes_repository import QuotesRepository
from api.types.quotes_types import ErrorDetail, QuoteStatus
from bson import ObjectId
from geometry.analyzer import analyze_file
from pricing import lead_time, price


@pytest.fixture
async def repo(mongo_db) -> QuotesRepository:
    await ensure_indexes(mongo_db)
    return QuotesRepository(mongo_db)


async def _insert(repo: QuotesRepository, name: str = "gear.step", quantity: int = 1) -> dict:
    return await repo.insert_queued(
        file_name=name,
        file_path=f"/uploads/{name}",
        file_hash="h",
        quantity=quantity,
        material="6061 Aluminum",
    )


async def test_insert_and_find(repo):
    created = await _insert(repo)
    assert created["status"] == "queued"
    assert "_id" not in created
    assert (await repo.find_by_id(created["id"]))["file_name"] == "gear.step"


async def test_find_unknown_or_malformed_id_returns_none(repo):
    assert await repo.find_by_id("not-an-object-id") is None
    assert await repo.find_by_id("0" * 24) is None


async def test_list_is_newest_first_filtered_and_paged(repo):
    ids = [(await _insert(repo, f"p{i}.step"))["id"] for i in range(5)]
    await repo.claim_next_queued()  # oldest becomes processing

    page = await repo.list_page(None, limit=2, skip=0)
    assert [q["id"] for q in page] == [ids[4], ids[3]]
    assert [q["id"] for q in await repo.list_page(None, limit=2, skip=2)] == [ids[2], ids[1]]
    assert await repo.count(None) == 5
    assert await repo.count(QuoteStatus.PROCESSING) == 1
    queued = await repo.list_page(QuoteStatus.QUEUED, limit=10, skip=0)
    assert ids[0] not in [q["id"] for q in queued]


async def test_claim_takes_oldest_first_and_marks_processing(repo):
    first = await _insert(repo, "a.step")
    await _insert(repo, "b.step")
    claimed = await repo.claim_next_queued()
    assert claimed["id"] == first["id"]
    assert claimed["status"] == "processing"
    assert claimed["started_at"] is not None


async def test_claim_returns_none_when_nothing_is_queued(repo):
    assert await repo.claim_next_queued() is None


async def test_concurrent_claims_never_return_the_same_quote(repo):
    for i in range(10):
        await _insert(repo, f"p{i}.step")
    claims = await asyncio.gather(*(repo.claim_next_queued() for _ in range(25)))
    claimed_ids = [c["id"] for c in claims if c is not None]
    assert len(claimed_ids) == 10
    assert len(set(claimed_ids)) == 10


async def test_save_result_stores_everything_and_sets_quoted(repo):
    quote = await _insert(repo, quantity=10)
    claimed = await repo.claim_next_queued()
    geometry = analyze_file("samples/vendra-gear.STEP")
    saved = await repo.save_result(
        claimed["id"], geometry, price(geometry, 10), lead_time(geometry, 10)
    )
    assert saved["status"] == "quoted"
    assert saved["lead_time_days"] == lead_time(geometry, 10).days
    assert saved["cost_breakdown"]["total_cost_per_unit"] == price(geometry, 10).total_cost_per_unit
    assert saved["geometry"]["features"]["setups"] == 2
    assert quote["id"] == saved["id"]


async def test_save_result_ignored_unless_processing(repo):
    quote = await _insert(repo)  # still queued
    geometry = analyze_file("samples/vendra-gear.STEP")
    assert (
        await repo.save_result(quote["id"], geometry, price(geometry, 1), lead_time(geometry, 1))
        is None
    )
    assert (await repo.find_by_id(quote["id"]))["status"] == "queued"


async def test_save_failure_keeps_the_reason(repo):
    await _insert(repo)
    claimed = await repo.claim_next_queued()
    failed = await repo.save_failure(
        claimed["id"], ErrorDetail(code="UNREADABLE_STEP", message="bad")
    )
    assert failed["status"] == "failed"
    assert failed["error"] == {"code": "UNREADABLE_STEP", "message": "bad"}


async def test_transition_status_is_compare_and_set(repo):
    quote = await _insert(repo)
    await repo.claim_next_queued()
    geometry = analyze_file("samples/vendra-gear.STEP")
    await repo.save_result(quote["id"], geometry, price(geometry, 1), lead_time(geometry, 1))

    reviewed = await repo.transition_status(quote["id"], QuoteStatus.QUOTED, QuoteStatus.REVIEWED)
    assert reviewed["status"] == "reviewed"
    # A second caller who still thinks it is `quoted` is refused.
    assert (
        await repo.transition_status(quote["id"], QuoteStatus.QUOTED, QuoteStatus.ARCHIVED) is None
    )


async def test_claim_counts_attempts_and_release_keeps_them(repo):
    quote = await _insert(repo)
    assert quote["attempts"] == 0
    assert (await repo.claim_next_queued())["attempts"] == 1
    released = await repo.release_for_retry(quote["id"])
    assert (released["status"], released["started_at"]) == ("queued", None)
    assert (await repo.claim_next_queued())["attempts"] == 2


async def test_release_for_retry_only_applies_to_processing(repo):
    quote = await _insert(repo)  # still queued
    assert await repo.release_for_retry(quote["id"]) is None


async def test_recover_stale_requeues_or_fails_by_attempts(repo, mongo_db):
    for name in ("fresh", "retry", "exhausted"):
        await _insert(repo, f"{name}.step")
    ids = {}
    for name in ("fresh", "retry", "exhausted"):
        ids[name] = (await repo.claim_next_queued())["id"]

    old = datetime.now(UTC) - timedelta(hours=1)
    quotes = mongo_db["quotes"]
    await quotes.update_one({"_id": ObjectId(ids["retry"])}, {"$set": {"started_at": old}})
    await quotes.update_one(
        {"_id": ObjectId(ids["exhausted"])}, {"$set": {"started_at": old, "attempts": 4}}
    )

    cutoff = datetime.now(UTC) - timedelta(minutes=5)
    abandoned = ErrorDetail(code="JOB_ABANDONED", message="gave up")
    assert await repo.recover_stale(cutoff, 4, abandoned) == (1, 1)

    assert (await repo.find_by_id(ids["fresh"]))["status"] == "processing"
    retry = await repo.find_by_id(ids["retry"])
    assert (retry["status"], retry["started_at"]) == ("queued", None)
    exhausted = await repo.find_by_id(ids["exhausted"])
    assert exhausted["status"] == "failed"
    assert exhausted["error"]["code"] == "JOB_ABANDONED"


async def test_indexes_exist(mongo_db):
    await ensure_indexes(mongo_db)
    names = {name async for name in _index_names(mongo_db)}
    assert any("created_at" in n for n in names)
    assert any("status" in n for n in names)


async def _index_names(db):
    for index in await (await db["quotes"].list_indexes()).to_list():
        yield index["name"]
