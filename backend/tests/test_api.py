from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.deps import require_anki_token
from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.models.card import AnkiSyncStatus, Card

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def _session_override(session: Session):  # type: ignore[no-untyped-def]
    """Return a FastAPI dependency that always yields the given session."""

    def _override() -> Generator[Session, None, None]:
        yield session

    return _override


@pytest.fixture
def client(session: Session) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_session] = _session_override(session)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def authed_client(session: Session) -> Generator[TestClient, None, None]:
    """Client with both session and anki auth overridden."""
    app.dependency_overrides[get_session] = _session_override(session)
    app.dependency_overrides[require_anki_token] = lambda: None
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _make_card(**overrides: object) -> Card:
    defaults: dict[str, object] = dict(
        source_text="take off",
        source_language="en",
        entry_type="phrasal_verb",
        canonical_text="take off",
        canonical_text_normalized="take off",
        transcription="/teɪk ɒf/",
        translation_variants_json=["взлетать", "снимать", "резко начинаться"],
        explanation="To leave the ground, or to remove something.",
        examples_json=[
            "The plane took off at noon.",
            "Take off your shoes, please.",
            "Her career really took off last year.",
        ],
        frequency=5,
        frequency_note="Very common.",
        eligible_for_anki=True,
        anki_sync_status=AnkiSyncStatus.PENDING,
        llm_model="test-model",
    )
    defaults.update(overrides)
    return Card(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health(client: TestClient) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /api/cards
# ---------------------------------------------------------------------------


def test_list_cards_empty(client: TestClient) -> None:
    resp = client.get("/api/cards")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["offset"] == 0
    assert data["limit"] == 50


def test_list_cards_returns_card(client: TestClient, session: Session) -> None:
    session.add(_make_card())
    session.commit()

    resp = client.get("/api/cards")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["canonical_text"] == "take off"
    assert item["translation_variants"] == ["взлетать", "снимать", "резко начинаться"]
    assert item["examples"] == [
        "The plane took off at noon.",
        "Take off your shoes, please.",
        "Her career really took off last year.",
    ]


def test_list_cards_pagination(client: TestClient, session: Session) -> None:
    for i in range(5):
        session.add(_make_card(source_text=f"word{i}", canonical_text_normalized=f"word{i}"))
    session.commit()

    resp = client.get("/api/cards?limit=2&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["offset"] == 0
    assert data["limit"] == 2

    resp2 = client.get("/api/cards?limit=2&offset=2")
    assert resp2.json()["offset"] == 2
    assert len(resp2.json()["items"]) == 2


def test_list_cards_filter_source_language(client: TestClient, session: Session) -> None:
    session.add(_make_card(source_language="en", canonical_text_normalized="take off"))
    session.add(
        _make_card(
            source_text="снять",
            source_language="ru",
            canonical_text="take off ru",
            canonical_text_normalized="take off ru",
        )
    )
    session.commit()

    resp = client.get("/api/cards?source_language=ru")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["source_language"] == "ru"


def test_list_cards_filter_entry_type(client: TestClient, session: Session) -> None:
    session.add(_make_card(entry_type="word", canonical_text_normalized="word1"))
    session.add(_make_card(entry_type="idiom", canonical_text_normalized="idiom1"))
    session.commit()

    resp = client.get("/api/cards?entry_type=idiom")
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["entry_type"] == "idiom"


def test_list_cards_filter_anki_sync_status(client: TestClient, session: Session) -> None:
    session.add(_make_card(anki_sync_status=AnkiSyncStatus.PENDING, canonical_text_normalized="a"))
    session.add(_make_card(anki_sync_status=AnkiSyncStatus.SYNCED, canonical_text_normalized="b"))
    session.commit()

    resp = client.get("/api/cards?anki_sync_status=synced")
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["anki_sync_status"] == "synced"


def test_list_cards_filter_eligible_for_anki(client: TestClient, session: Session) -> None:
    session.add(_make_card(eligible_for_anki=True, canonical_text_normalized="a"))
    session.add(_make_card(eligible_for_anki=False, canonical_text_normalized="b"))
    session.commit()

    resp = client.get("/api/cards?eligible_for_anki=false")
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["eligible_for_anki"] is False


def test_list_cards_search(client: TestClient, session: Session) -> None:
    session.add(_make_card(canonical_text="take off", canonical_text_normalized="take off"))
    session.add(
        _make_card(
            source_text="run away",
            canonical_text="run away",
            canonical_text_normalized="run away",
        )
    )
    session.commit()

    resp = client.get("/api/cards?search=take")
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["canonical_text"] == "take off"


# ---------------------------------------------------------------------------
# DELETE /api/cards/{card_id}
# ---------------------------------------------------------------------------


def test_delete_card(client: TestClient, session: Session) -> None:
    card = _make_card()
    session.add(card)
    session.commit()
    session.refresh(card)

    resp = client.delete(f"/api/cards/{card.id}")
    assert resp.status_code == 204

    assert session.get(Card, card.id) is None


def test_delete_card_not_found(client: TestClient) -> None:
    resp = client.delete("/api/cards/9999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Anki auth guard
# ---------------------------------------------------------------------------


def test_anki_pending_no_token_is_401(client: TestClient) -> None:
    resp = client.get("/api/anki/pending")
    assert resp.status_code == 401


def test_anki_ack_no_token_is_401(client: TestClient) -> None:
    resp = client.post("/api/anki/ack", json={"card_id": 1, "anki_note_id": 123})
    assert resp.status_code == 401


def test_anki_fail_no_token_is_401(client: TestClient) -> None:
    resp = client.post("/api/anki/fail", json={"card_id": 1, "error_message": "oops"})
    assert resp.status_code == 401


def test_anki_wrong_token_is_403(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    import app.api.deps as deps_mod
    from app.core.config import get_settings

    monkeypatch.setattr(deps_mod, "get_settings", lambda: get_settings())
    # settings.anki_sync_token is None in test env; any Bearer value mismatches
    resp = client.get("/api/anki/pending", headers={"Authorization": "Bearer wrong-token"})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /api/anki/pending
# ---------------------------------------------------------------------------


def test_anki_pending_empty(authed_client: TestClient) -> None:
    resp = authed_client.get("/api/anki/pending")
    assert resp.status_code == 200
    assert resp.json() == []


def test_anki_pending_returns_eligible_cards(authed_client: TestClient, session: Session) -> None:
    session.add(_make_card(eligible_for_anki=True, anki_sync_status=AnkiSyncStatus.PENDING))
    # not eligible — should be excluded
    session.add(
        _make_card(
            eligible_for_anki=False,
            anki_sync_status=AnkiSyncStatus.PENDING,
            canonical_text_normalized="other",
        )
    )
    # already synced — should be excluded
    session.add(
        _make_card(
            eligible_for_anki=True,
            anki_sync_status=AnkiSyncStatus.SYNCED,
            canonical_text_normalized="synced",
        )
    )
    session.commit()

    resp = authed_client.get("/api/anki/pending")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["canonical_text"] == "take off"
    # Only Anki-relevant fields are exposed — no source_text
    assert "source_text" not in data[0]


def test_anki_pending_limit(authed_client: TestClient, session: Session) -> None:
    for i in range(5):
        session.add(
            _make_card(
                eligible_for_anki=True,
                anki_sync_status=AnkiSyncStatus.PENDING,
                canonical_text_normalized=f"word{i}",
            )
        )
    session.commit()

    resp = authed_client.get("/api/anki/pending?limit=3")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


# ---------------------------------------------------------------------------
# POST /api/anki/ack
# ---------------------------------------------------------------------------


def test_anki_ack_updates_card(authed_client: TestClient, session: Session) -> None:
    card = _make_card()
    session.add(card)
    session.commit()
    session.refresh(card)

    resp = authed_client.post(
        "/api/anki/ack",
        json={"card_id": card.id, "anki_note_id": 42},
    )
    assert resp.status_code == 204

    session.refresh(card)
    assert card.anki_sync_status == AnkiSyncStatus.SYNCED
    assert card.anki_note_id == 42
    assert len(card.sync_attempts) == 1
    assert card.sync_attempts[0].status == "synced"


def test_anki_ack_not_found(authed_client: TestClient) -> None:
    resp = authed_client.post(
        "/api/anki/ack",
        json={"card_id": 9999, "anki_note_id": 1},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/anki/fail
# ---------------------------------------------------------------------------


def test_anki_fail_updates_card(authed_client: TestClient, session: Session) -> None:
    card = _make_card()
    session.add(card)
    session.commit()
    session.refresh(card)

    resp = authed_client.post(
        "/api/anki/fail",
        json={"card_id": card.id, "error_message": "AnkiConnect refused"},
    )
    assert resp.status_code == 204

    session.refresh(card)
    assert card.anki_sync_status == AnkiSyncStatus.FAILED
    assert len(card.sync_attempts) == 1
    assert card.sync_attempts[0].status == "failed"
    assert card.sync_attempts[0].error_message == "AnkiConnect refused"


def test_anki_fail_not_found(authed_client: TestClient) -> None:
    resp = authed_client.post(
        "/api/anki/fail",
        json={"card_id": 9999, "error_message": "err"},
    )
    assert resp.status_code == 404
