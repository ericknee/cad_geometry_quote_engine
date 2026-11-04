from api.config import Settings
from api.main import create_app
from fastapi.testclient import TestClient


def test_health() -> None:
    # Lifespan is not entered (no `with`), so no Mongo connection is needed.
    client = TestClient(create_app(Settings(mongodb_db="vendra_test")))
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
