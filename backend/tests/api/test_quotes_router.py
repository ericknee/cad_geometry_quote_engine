from collections.abc import Iterator
from pathlib import Path

import pytest
from api.config import Settings
from api.errors.quotes_errors import AnalysisFailed
from api.main import create_app
from api.repositories.quotes_repository import QuotesRepository
from api.services.quotes_service import QuotesService
from fastapi.testclient import TestClient
from geometry.analyzer import analyze_file
from geometry.errors import GeometryError

from tests.api.test_file_storage import STEP

GEAR = Path(__file__).resolve().parents[3] / "samples" / "vendra-gear.STEP"


@pytest.fixture
def settings(mongo_db, tmp_path) -> Settings:
    return Settings(mongodb_db=mongo_db.name, upload_dir=str(tmp_path / "uploads"))


@pytest.fixture
def client(settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:  # `with` runs startup (Mongo ping)
        yield test_client


def _upload(client, name="part.step", content=STEP, quantity="3"):
    return client.post("/api/quotes", files={"file": (name, content)}, data={"quantity": quantity})


def _assert_error(response, status, code):
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    assert body["error"]["message"]


def test_create_returns_202_queued_without_the_file_path(client):
    response = _upload(client)
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["quantity"] == 3
    assert body["file_name"] == "part.step"
    assert body["geometry"] is None and body["cost_breakdown"] is None
    assert "file_path" not in body


@pytest.mark.parametrize("quantity", ["0", "10001", "-2"])
def test_create_rejects_quantity_out_of_range(client, quantity):
    _assert_error(_upload(client, quantity=quantity), 422, "INVALID_QUANTITY")


def test_oversized_request_is_rejected_before_the_file_is_saved(mongo_db, tmp_path):
    settings = Settings(
        mongodb_db=mongo_db.name, upload_dir=str(tmp_path / "uploads"), max_upload_mb=1
    )
    with TestClient(create_app(settings)) as small_client:
        too_big = _upload(small_client, content=b"x" * (1024 * 1024 + 128 * 1024))
        _assert_error(too_big, 413, "FILE_TOO_LARGE")
        assert not list((tmp_path / "uploads").glob("*"))  # nothing was stored
        assert _upload(small_client).status_code == 202  # a normal request still works


def test_create_rejects_non_integer_quantity(client):
    _assert_error(_upload(client, quantity="abc"), 422, "VALIDATION_ERROR")


def test_create_rejects_missing_file(client):
    _assert_error(client.post("/api/quotes", data={"quantity": "1"}), 422, "VALIDATION_ERROR")


def test_create_rejects_bad_extension_and_content(client):
    _assert_error(_upload(client, name="part.txt"), 422, "INVALID_FILE")
    _assert_error(_upload(client, content=b"not a step file"), 422, "INVALID_FILE")
    assert client.get("/api/quotes").json()["total"] == 0


def test_get_returns_the_quote_and_404_otherwise(client):
    created = _upload(client).json()
    assert client.get(f"/api/quotes/{created['id']}").json()["id"] == created["id"]
    _assert_error(client.get("/api/quotes/000000000000000000000000"), 404, "QUOTE_NOT_FOUND")
    _assert_error(client.get("/api/quotes/nope"), 404, "QUOTE_NOT_FOUND")


def test_list_envelope_paging_and_filter(client):
    ids = [_upload(client, quantity=str(q)).json()["id"] for q in (1, 2, 3)]
    body = client.get("/api/quotes", params={"limit": 2}).json()
    assert [i["id"] for i in body["items"]] == [ids[2], ids[1]]
    assert (body["total"], body["limit"], body["skip"]) == (3, 2, 0)
    assert client.get("/api/quotes", params={"skip": 2}).json()["items"][0]["id"] == ids[0]
    assert client.get("/api/quotes", params={"status": "quoted"}).json()["total"] == 0
    oldest = client.get("/api/quotes", params={"sort": "oldest"}).json()
    assert [i["id"] for i in oldest["items"]] == ids
    # Nothing is archived yet, so the flag changes nothing; the service test covers hiding.
    assert client.get("/api/quotes", params={"exclude_archived": "true"}).json()["total"] == 3


@pytest.mark.parametrize(
    "params", [{"limit": 0}, {"limit": 101}, {"skip": -1}, {"status": "x"}, {"sort": "x"}]
)
def test_list_rejects_bad_params(client, params):
    _assert_error(client.get("/api/quotes", params=params), 422, "VALIDATION_ERROR")


def test_patch_rejects_unknown_status_and_forbidden_move(client):
    quote_id = _upload(client).json()["id"]  # queued
    url = f"/api/quotes/{quote_id}/status"
    _assert_error(client.patch(url, json={"status": "bogus"}), 422, "VALIDATION_ERROR")
    _assert_error(client.patch(url, json={"status": "reviewed"}), 422, "INVALID_STATUS_TRANSITION")
    _assert_error(
        client.patch("/api/quotes/000000000000000000000000/status", json={"status": "archived"}),
        404,
        "QUOTE_NOT_FOUND",
    )


def test_unknown_route_uses_the_error_shape(client):
    _assert_error(client.get("/api/nope"), 404, "HTTP_404")


async def _run_worker_once(settings, mongo_db) -> None:
    """Run the real geometry engine in-process (the subprocess path has its own tests)."""

    async def analyze(path, _timeout):
        try:
            return analyze_file(path)
        except GeometryError as error:
            raise AnalysisFailed(error.code.value, error.message) from error

    service = QuotesService(QuotesRepository(mongo_db), settings, analyze=analyze)
    assert await service.process_next_job() is True


async def test_upload_to_quote_to_review_end_to_end(client, settings, mongo_db):
    created = client.post(
        "/api/quotes",
        files={"file": ("vendra-gear.STEP", GEAR.read_bytes())},
        data={"quantity": "10"},
    )
    assert created.status_code == 202
    quote_id = created.json()["id"]

    await _run_worker_once(settings, mongo_db)

    quote = client.get(f"/api/quotes/{quote_id}").json()
    assert quote["status"] == "quoted"
    assert quote["geometry"]["bounding_box_mm"]["length"] == pytest.approx(23.368, abs=0.001)
    assert quote["cost_breakdown"]["total_cost_per_unit"] == pytest.approx(44.08, abs=0.02)
    assert quote["lead_time_days"] == 6 == quote["lead_time"]["days"]

    row = client.get("/api/quotes", params={"status": "quoted"}).json()["items"][0]
    assert row["total_cost_per_unit"] == quote["cost_breakdown"]["total_cost_per_unit"]

    url = f"/api/quotes/{quote_id}/status"
    assert client.patch(url, json={"status": "reviewed"}).json()["status"] == "reviewed"
    assert client.patch(url, json={"status": "archived"}).json()["status"] == "archived"
    _assert_error(client.patch(url, json={"status": "quoted"}), 422, "INVALID_STATUS_TRANSITION")


async def test_unreadable_step_is_stored_as_failed(client, settings, mongo_db):
    quote_id = _upload(client).json()["id"]  # passes the header check, has no solid

    await _run_worker_once(settings, mongo_db)

    quote = client.get(f"/api/quotes/{quote_id}").json()
    assert quote["status"] == "failed"
    assert quote["error"]["code"] in {"UNREADABLE_STEP", "NO_SOLIDS"}
    assert quote["cost_breakdown"] is None
    # A failed quote can be cleared from the dashboard.
    archived = client.patch(f"/api/quotes/{quote_id}/status", json={"status": "archived"})
    assert archived.json()["status"] == "archived"
