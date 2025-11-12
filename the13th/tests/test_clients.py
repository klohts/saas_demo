import pytest
from fastapi.testclient import TestClient
from client_customization_app import app, init_db, API_KEY

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()
    yield

def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
