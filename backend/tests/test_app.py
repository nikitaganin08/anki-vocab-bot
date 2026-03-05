from fastapi.testclient import TestClient

from app.main import app


def test_healthcheck_endpoint_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_admin_index_serves_spa() -> None:
    with TestClient(app) as client:
        response = client.get("/admin/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "anki-vocab-bot admin" in response.text


def test_admin_deep_link_serves_spa_index() -> None:
    with TestClient(app) as client:
        response = client.get("/admin/cards")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "anki-vocab-bot admin" in response.text
