from pathlib import Path

import pytest
from api.config import Settings
from api.errors.quotes_errors import (
    InvalidFile,
    InvalidQuantity,
    InvalidStatusTransition,
    QuoteNotFound,
    StatusConflict,
)
from api.repositories.quotes_repository import QuotesRepository
from api.services.quotes_service import ALLOWED_TRANSITIONS, QuotesService
from api.types.quotes_types import QuoteStatus
from bson import ObjectId

from tests.api.test_file_storage import STEP, FakeUpload


@pytest.fixture
def repo(mongo_db) -> QuotesRepository:
    return QuotesRepository(mongo_db)


@pytest.fixture
def service(repo, tmp_path) -> QuotesService:
    return QuotesService(repo, Settings(upload_dir=str(tmp_path / "uploads")))


async def _quote_with_status(repo, status: QuoteStatus) -> str:
    quote = await repo.insert_queued(
        file_name="a.step", file_path="x", file_hash="h", quantity=1, material="6061 Aluminum"
    )
    await repo._quotes.update_one(
        {"_id": ObjectId(quote["id"])}, {"$set": {"status": status.value}}
    )
    return quote["id"]


async def test_create_queues_a_quote_and_keeps_the_file(service, repo, tmp_path):
    quote = await service.create_quote(FakeUpload("gear.STEP", STEP), 5)
    assert quote.status is QuoteStatus.QUEUED
    assert (quote.quantity, quote.material, quote.file_name) == (5, "6061 Aluminum", "gear.STEP")
    stored = await repo.find_by_id(quote.id)
    assert stored["file_path"].startswith(str(tmp_path))
    assert len(list((tmp_path / "uploads").iterdir())) == 1


@pytest.mark.parametrize("quantity", [0, -1, 10_001])
async def test_create_rejects_bad_quantity_and_saves_nothing(service, repo, quantity, tmp_path):
    with pytest.raises(InvalidQuantity):
        await service.create_quote(FakeUpload("a.step", STEP), quantity)
    assert await repo.count(None) == 0
    assert not (tmp_path / "uploads").exists()


@pytest.mark.parametrize("quantity", [1, 10_000])
async def test_create_accepts_quantity_limits(service, quantity):
    quote = await service.create_quote(FakeUpload("a.step", STEP), quantity)
    assert quote.quantity == quantity


async def test_create_rejects_bad_file_and_saves_nothing(service, repo):
    with pytest.raises(InvalidFile):
        await service.create_quote(FakeUpload("a.txt", STEP), 1)
    assert await repo.count(None) == 0


async def test_create_removes_the_file_when_the_insert_fails(service, repo, tmp_path):
    async def broken(**_):
        raise RuntimeError("db down")

    repo.insert_queued = broken
    with pytest.raises(RuntimeError):
        await service.create_quote(FakeUpload("a.step", STEP), 1)
    assert list((tmp_path / "uploads").iterdir()) == []


async def test_get_and_not_found(service):
    created = await service.create_quote(FakeUpload("a.step", STEP), 1)
    assert (await service.get_quote(created.id)).id == created.id
    for bad_id in ["000000000000000000000000", "not-an-id"]:
        with pytest.raises(QuoteNotFound):
            await service.get_quote(bad_id)


async def test_list_pages_newest_first_with_total(service):
    ids = [(await service.create_quote(FakeUpload("a.step", STEP), q)).id for q in (1, 2, 3)]
    page = await service.list_quotes(None, limit=2, skip=0)
    assert [item.id for item in page.items] == [ids[2], ids[1]]
    assert (page.total, page.limit, page.skip) == (3, 2, 0)
    rest = await service.list_quotes(None, limit=2, skip=2)
    assert [item.id for item in rest.items] == [ids[0]]


async def test_list_filters_by_status(service, repo):
    await service.create_quote(FakeUpload("a.step", STEP), 1)
    quoted = await _quote_with_status(repo, QuoteStatus.QUOTED)
    page = await service.list_quotes(QuoteStatus.QUOTED, limit=20, skip=0)
    assert [item.id for item in page.items] == [quoted]
    assert page.total == 1


async def test_list_can_hide_archived_and_keeps_the_total_in_step(service, repo):
    kept = await _quote_with_status(repo, QuoteStatus.QUOTED)
    await _quote_with_status(repo, QuoteStatus.ARCHIVED)

    hidden = await service.list_quotes(None, limit=20, skip=0, exclude_archived=True)
    assert [item.id for item in hidden.items] == [kept]
    assert hidden.total == 1
    assert (await service.list_quotes(None, limit=20, skip=0)).total == 2
    # An explicit status wins, so the archived list is still reachable.
    archived = await service.list_quotes(
        QuoteStatus.ARCHIVED, limit=20, skip=0, exclude_archived=True
    )
    assert archived.total == 1


@pytest.mark.parametrize(
    ("current", "new"),
    [(c, n) for n, sources in ALLOWED_TRANSITIONS.items() for c in sources],
)
async def test_allowed_transitions(service, repo, current, new):
    quote_id = await _quote_with_status(repo, current)
    assert (await service.update_status(quote_id, new)).status is new


@pytest.mark.parametrize("current", list(QuoteStatus))
@pytest.mark.parametrize("new", list(QuoteStatus))
async def test_every_other_transition_is_rejected(service, repo, current, new):
    if current in ALLOWED_TRANSITIONS.get(new, ()):
        pytest.skip("allowed")
    if current is new and new in ALLOWED_TRANSITIONS:
        pytest.skip("idempotent, see test_repeating_a_reviewer_status_is_a_no_op")
    quote_id = await _quote_with_status(repo, current)
    with pytest.raises(InvalidStatusTransition):
        await service.update_status(quote_id, new)
    assert (await service.get_quote(quote_id)).status is current


@pytest.mark.parametrize("status", list(ALLOWED_TRANSITIONS))
async def test_repeating_a_reviewer_status_is_a_no_op(service, repo, status):
    quote_id = await _quote_with_status(repo, status)
    assert (await service.update_status(quote_id, status)).status is status


async def test_archiving_deletes_the_file_but_keeps_the_record(service, repo):
    quote = await service.create_quote(FakeUpload("a.step", STEP), 1)
    stored = await repo.find_by_id(quote.id)
    await repo._quotes.update_one({"_id": ObjectId(quote.id)}, {"$set": {"status": "quoted"}})
    assert Path(stored["file_path"]).exists()

    await service.update_status(quote.id, QuoteStatus.ARCHIVED)

    assert not Path(stored["file_path"]).exists()
    assert (await repo.find_by_id(quote.id))["file_hash"] == stored["file_hash"]


async def test_reviewing_keeps_the_file(service, repo):
    quote = await service.create_quote(FakeUpload("a.step", STEP), 1)
    path = Path((await repo.find_by_id(quote.id))["file_path"])
    await repo._quotes.update_one({"_id": ObjectId(quote.id)}, {"$set": {"status": "quoted"}})
    await service.update_status(quote.id, QuoteStatus.REVIEWED)
    assert path.exists()


async def test_archiving_survives_a_file_that_cannot_be_deleted(service, repo, monkeypatch):
    def boom(_path):
        raise PermissionError("locked")

    monkeypatch.setattr("api.services.quotes_service.delete_file", boom)
    quote_id = await _quote_with_status(repo, QuoteStatus.QUOTED)
    assert (
        await service.update_status(quote_id, QuoteStatus.ARCHIVED)
    ).status is QuoteStatus.ARCHIVED


async def test_update_status_not_found(service):
    with pytest.raises(QuoteNotFound):
        await service.update_status("000000000000000000000000", QuoteStatus.ARCHIVED)


async def test_update_status_lost_race_is_a_conflict(service, repo):
    quote_id = await _quote_with_status(repo, QuoteStatus.QUOTED)

    real = repo.transition_status

    async def raced(quote_id, current, new):
        await real(quote_id, current, QuoteStatus.ARCHIVED)  # someone else got there first
        return await real(quote_id, current, new)

    repo.transition_status = raced
    with pytest.raises(StatusConflict):
        await service.update_status(quote_id, QuoteStatus.REVIEWED)
