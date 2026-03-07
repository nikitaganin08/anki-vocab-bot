from fastapi.testclient import TestClient

from app.main import app


def test_healthcheck_endpoint_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_telegram_webapp_index_serves_spa() -> None:
    with TestClient(app) as client:
        response = client.get("/telegram/webapp/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert '<div id="root"></div>' in response.text


def test_telegram_webapp_deep_link_serves_spa_index() -> None:
    with TestClient(app) as client:
        response = client.get("/telegram/webapp/cards")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert '<div id="root"></div>' in response.text


def test_admin_route_is_unsupported() -> None:
    with TestClient(app) as client:
        response = client.get("/admin/")

    assert response.status_code == 404
