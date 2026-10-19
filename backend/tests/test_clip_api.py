from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.api.deps as deps_mod
from app.api.deps import get_openrouter_client
from app.main import app
from app.models.card import Card

from .conftest import TelegramSettingsStub
from .test_api import FakeBatchGenerator, _make_accepted_llm_response


def _post(client: TestClient, text: str, token: str | None = "secret"):  # noqa: ANN202
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.post("/api/clip", json={"text": text}, headers=headers)


def test_clip_creates_a_card(client: TestClient, session: Session) -> None:
    app.dependency_overrides[get_openrouter_client] = lambda: FakeBatchGenerator(
        {"look up": _make_accepted_llm_response("look up")}
    )

    resp = _post(client, "  look   up ")

    assert resp.status_code == 200
    assert resp.json()["status"] == "created"
    assert resp.json()["canonical_text"] == "look up"
    assert session.query(Card).count() == 1


def test_clip_rejects_a_sentence_without_calling_the_llm(client: TestClient) -> None:
    generator = FakeBatchGenerator({})
    app.dependency_overrides[get_openrouter_client] = lambda: generator

    resp = _post(client, "this is far too many words to be a single stable expression")

    assert resp.json()["status"] == "invalid_input"
    assert generator.calls == []


def test_clip_needs_the_right_token(client: TestClient) -> None:
    assert _post(client, "look up", token=None).status_code == 401
    assert _post(client, "look up", token="wrong").status_code == 401


def test_clip_is_off_without_a_configured_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(deps_mod, "get_settings", lambda: TelegramSettingsStub(clip_token=None))

    assert _post(client, "look up", token="").status_code == 503
