from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.api.deps as deps_mod
from app.api.deps import get_card_generator, require_anki_token
from app.clients.openrouter import OpenRouterTimeoutError
from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.models.card import AnkiSyncStatus, Card
from app.schemas.llm import AcceptedLlmResponse, RejectedLlmResponse

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


def _make_accepted_llm_response(
    source_text: str,
    *,
    canonical_text: str | None = None,
    entry_type: str = "phrasal_verb",
) -> AcceptedLlmResponse:
    canonical = canonical_text or source_text
    return AcceptedLlmResponse.model_validate(
        {
            "accepted": True,
            "source_text": source_text,
            "source_language": "en",
            "entry_type": entry_type,
            "canonical_text": canonical,
            "canonical_text_normalized": canonical.lower(),
            "transcription": "/test/",
            "translation_variants": ["пример один", "пример два"],
            "explanation": "A stable lexical unit used in English.",
            "examples": [
                "This is the first example.",
                "This is the second example.",
                "This is the third example.",
            ],
            "frequency": 4,
            "frequency_note": "Common enough.",
            "llm_model": "test-model",
        }
    )


@dataclass
class FakeBatchGenerator:
    outcomes: dict[str, AcceptedLlmResponse | RejectedLlmResponse | Exception]
    calls: list[str] = field(default_factory=list)

    def generate_card(self, source_text: str) -> AcceptedLlmResponse | RejectedLlmResponse:
        self.calls.append(source_text)
        outcome = self.outcomes[source_text]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


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
# POST /api/cards/batch
# ---------------------------------------------------------------------------


def test_batch_import_mixed_statuses(client: TestClient, session: Session) -> None:
    session.add(
        _make_card(
            source_text="turn down",
            canonical_text="turn down",
            canonical_text_normalized="turn down",
        )
    )
    session.add(
        _make_card(
            source_text="seed source",
            canonical_text="break down",
            canonical_text_normalized="break down",
        )
    )
    session.commit()

    fake_generator = FakeBatchGenerator(
        outcomes={
            "look up": _make_accepted_llm_response("look up", entry_type="phrasal_verb"),
            "decompose": _make_accepted_llm_response(
                "decompose",
                canonical_text="break down",
                entry_type="expression",
            ),
            "very random sentence": RejectedLlmResponse.model_validate(
                {
                    "accepted": False,
                    "reason": "not_lexical_unit",
                    "message_for_user": "This does not look like a stable lexical unit.",
                }
            ),
        }
    )
    app.dependency_overrides[get_card_generator] = lambda: fake_generator

    resp = client.post(
        "/api/cards/batch",
        json={
            "source_texts": [
                "look up",
                "turn down",
                "decompose",
                "very random sentence",
                "one two three four five six seven eight nine",
            ]
        },
    )

    assert resp.status_code == 200
    data = resp.json()

    assert [item["status"] for item in data["items"]] == [
        "created",
        "duplicate_source",
        "duplicate_canonical",
        "rejected",
        "invalid_input",
    ]
    assert data["items"][0]["canonical_text"] == "look up"
    assert data["items"][1]["canonical_text"] == "turn down"
    assert data["items"][2]["canonical_text"] == "break down"
    assert data["items"][3]["message"] == "This does not look like a stable lexical unit."
    assert data["items"][4]["message"] == "Please send up to 8 words."
    assert data["summary"] == {
        "total": 5,
        "created": 1,
        "duplicate_source": 1,
        "duplicate_canonical": 1,
        "rejected": 1,
        "invalid_input": 1,
        "upstream_error": 0,
    }
    assert fake_generator.calls == ["look up", "decompose", "very random sentence"]


def test_batch_import_rejects_more_than_fifty_items(client: TestClient) -> None:
    fake_generator = FakeBatchGenerator(outcomes={})
    app.dependency_overrides[get_card_generator] = lambda: fake_generator

    resp = client.post(
        "/api/cards/batch",
        json={"source_texts": [f"word-{i}" for i in range(51)]},
    )

    assert resp.status_code == 422


def test_batch_import_marks_invalid_rows_without_llm_call(client: TestClient) -> None:
    fake_generator = FakeBatchGenerator(
        outcomes={
            "take off": _make_accepted_llm_response("take off"),
        }
    )
    app.dependency_overrides[get_card_generator] = lambda: fake_generator

    resp = client.post(
        "/api/cards/batch",
        json={
            "source_texts": [
                "take off",
                "one two three four five six seven eight nine",
            ]
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert [item["status"] for item in data["items"]] == ["created", "invalid_input"]
    assert data["summary"]["created"] == 1
    assert data["summary"]["invalid_input"] == 1
    assert fake_generator.calls == ["take off"]


def test_batch_import_continues_after_upstream_error(client: TestClient) -> None:
    fake_generator = FakeBatchGenerator(
        outcomes={
            "look up": OpenRouterTimeoutError(
                "timeout",
                code="openrouter_timeout",
                user_message="The language model timed out. Please try again.",
            ),
            "break down": _make_accepted_llm_response("break down", entry_type="expression"),
        }
    )
    app.dependency_overrides[get_card_generator] = lambda: fake_generator

    resp = client.post(
        "/api/cards/batch",
        json={"source_texts": ["look up", "break down"]},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert [item["status"] for item in data["items"]] == ["upstream_error", "created"]
    assert data["items"][0]["message"] == "The language model timed out. Please try again."
    assert data["summary"]["upstream_error"] == 1
    assert data["summary"]["created"] == 1


def test_batch_import_returns_503_when_llm_not_configured(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @dataclass
    class SettingsStub:
        openrouter_api_key: str | None = None
        llm_model: str = "test-model"

    monkeypatch.setattr(deps_mod, "get_settings", lambda: SettingsStub())

    resp = client.post("/api/cards/batch", json={"source_texts": ["look up"]})

    assert resp.status_code == 503
    assert resp.json()["detail"] == "LLM is not configured"


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
    assert data[0]["canonical_text_normalized"] == "take off"
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
