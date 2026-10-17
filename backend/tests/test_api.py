from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.api.deps as deps_mod
from app.api.deps import get_openrouter_client, get_pronunciation_generator
from app.clients.openrouter import OpenRouterError
from app.main import app
from app.models.card import AnkiSyncStatus, Card
from app.schemas.llm import AcceptedLlmResponse, RejectedLlmResponse
from app.services.pronunciation import PronunciationAudioError

from .conftest import (
    TELEGRAM_ALLOWED_USER_ID,
    TELEGRAM_BOT_TOKEN,
    make_card,
    telegram_headers,
)


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
            "source_language": "en",
            "entry_type": entry_type,
            "canonical_text": canonical,
            "transcription": "/test/",
            "translation_variants": ["пример один", "пример два"],
            "explanation": "A stable lexical unit used in English.",
            "examples": [
                f"Speakers use {canonical} in the first example.",
                f"Students can see {canonical} in the second example.",
                "This is the third example.",
            ],
            "frequency": 4,
            "frequency_note": "Common enough.",
        }
    )


@dataclass
class FakeBatchGenerator:
    outcomes: dict[str, AcceptedLlmResponse | RejectedLlmResponse | Exception]
    calls: list[str] = field(default_factory=list)
    model: str = "test-model"

    def generate_card(self, source_text: str) -> AcceptedLlmResponse | RejectedLlmResponse:
        self.calls.append(source_text)
        outcome = self.outcomes[source_text]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


# ---------------------------------------------------------------------------
# GET /api/cards
# ---------------------------------------------------------------------------


def test_list_cards_empty(client: TestClient) -> None:
    resp = client.get("/api/cards", headers=telegram_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["offset"] == 0
    assert data["limit"] == 50


def test_list_cards_returns_card(client: TestClient, session: Session) -> None:
    session.add(make_card())
    session.commit()

    resp = client.get("/api/cards", headers=telegram_headers())
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
        session.add(make_card(source_text=f"word{i}", canonical_text_normalized=f"word{i}"))
    session.commit()

    resp = client.get("/api/cards?limit=2&offset=0", headers=telegram_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["offset"] == 0
    assert data["limit"] == 2

    resp2 = client.get("/api/cards?limit=2&offset=2", headers=telegram_headers())
    assert resp2.json()["offset"] == 2
    assert len(resp2.json()["items"]) == 2


def test_list_cards_filter_source_language(client: TestClient, session: Session) -> None:
    session.add(make_card(source_language="en", canonical_text_normalized="take off"))
    session.add(
        make_card(
            source_text="снять",
            source_language="ru",
            canonical_text="take off ru",
            canonical_text_normalized="take off ru",
        )
    )
    session.commit()

    resp = client.get("/api/cards?source_language=ru", headers=telegram_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["source_language"] == "ru"


def test_list_cards_filter_entry_type(client: TestClient, session: Session) -> None:
    session.add(make_card(entry_type="word", canonical_text_normalized="word1"))
    session.add(make_card(entry_type="idiom", canonical_text_normalized="idiom1"))
    session.commit()

    resp = client.get("/api/cards?entry_type=idiom", headers=telegram_headers())
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["entry_type"] == "idiom"


def test_list_cards_filter_anki_sync_status(client: TestClient, session: Session) -> None:
    session.add(make_card(anki_sync_status=AnkiSyncStatus.PENDING, canonical_text_normalized="a"))
    session.add(make_card(anki_sync_status=AnkiSyncStatus.SYNCED, canonical_text_normalized="b"))
    session.commit()

    resp = client.get("/api/cards?anki_sync_status=synced", headers=telegram_headers())
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["anki_sync_status"] == "synced"


def test_list_cards_filter_is_learning(client: TestClient, session: Session) -> None:
    session.add(make_card(is_learning=True, canonical_text_normalized="a"))
    session.add(make_card(is_learning=False, canonical_text_normalized="b"))
    session.commit()

    resp = client.get("/api/cards?is_learning=false", headers=telegram_headers())
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["is_learning"] is False


def test_list_cards_search(client: TestClient, session: Session) -> None:
    session.add(make_card(canonical_text="take off", canonical_text_normalized="take off"))
    session.add(
        make_card(
            source_text="run away",
            canonical_text="run away",
            canonical_text_normalized="run away",
        )
    )
    session.commit()

    resp = client.get("/api/cards?search=take", headers=telegram_headers())
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["canonical_text"] == "take off"


# ---------------------------------------------------------------------------
# POST /api/cards/batch
# ---------------------------------------------------------------------------


def test_batch_import_mixed_statuses(client: TestClient, session: Session) -> None:
    session.add(
        make_card(
            source_text="turn down",
            canonical_text="turn down",
            canonical_text_normalized="turn down",
        )
    )
    session.add(
        make_card(
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
                    "message_for_user": "This does not look like a stable lexical unit.",
                }
            ),
        }
    )
    app.dependency_overrides[get_openrouter_client] = lambda: fake_generator

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
        headers=telegram_headers(),
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
    app.dependency_overrides[get_openrouter_client] = lambda: fake_generator

    resp = client.post(
        "/api/cards/batch",
        json={"source_texts": [f"word-{i}" for i in range(51)]},
        headers=telegram_headers(),
    )

    assert resp.status_code == 422


def test_batch_import_continues_after_upstream_error(client: TestClient) -> None:
    fake_generator = FakeBatchGenerator(
        outcomes={
            "look up": OpenRouterError(
                "timeout",
                code="openrouter_timeout",
                user_message="The language model timed out. Please try again.",
            ),
            "break down": _make_accepted_llm_response("break down", entry_type="expression"),
        }
    )
    app.dependency_overrides[get_openrouter_client] = lambda: fake_generator

    resp = client.post(
        "/api/cards/batch",
        json={"source_texts": ["look up", "break down"]},
        headers=telegram_headers(),
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
        telegram_bot_token: str = TELEGRAM_BOT_TOKEN
        telegram_allowed_user_id: int = TELEGRAM_ALLOWED_USER_ID
        openrouter_api_key: str | None = None

    monkeypatch.setattr(deps_mod, "get_settings", lambda: SettingsStub())

    resp = client.post(
        "/api/cards/batch",
        json={"source_texts": ["look up"]},
        headers=telegram_headers(),
    )

    assert resp.status_code == 503
    assert resp.json()["detail"] == "LLM is not configured"


# ---------------------------------------------------------------------------
# DELETE /api/cards/{card_id}
# ---------------------------------------------------------------------------


def test_delete_card(client: TestClient, session: Session) -> None:
    card = make_card()
    session.add(card)
    session.commit()
    session.refresh(card)

    resp = client.delete(f"/api/cards/{card.id}", headers=telegram_headers())
    assert resp.status_code == 204

    assert session.get(Card, card.id) is None


def test_delete_card_not_found(client: TestClient) -> None:
    resp = client.delete("/api/cards/9999", headers=telegram_headers())
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/cards/{card_id}/audio
# ---------------------------------------------------------------------------


@dataclass
class FakePronunciationGenerator:
    error: Exception | None = None
    calls: list[str] = field(default_factory=list)

    def generate_audio(self, text: str) -> bytes:
        self.calls.append(text)
        if self.error is not None:
            raise self.error
        return b"mp3:" + text.encode()


def _use_generator(generator: FakePronunciationGenerator) -> None:
    app.dependency_overrides[get_pronunciation_generator] = lambda: generator


def _add_card(session: Session) -> Card:
    card = make_card()
    session.add(card)
    session.commit()
    return card


def test_card_audio_generates_then_serves_cache(
    client: TestClient, session: Session, tmp_path: Path
) -> None:
    card = _add_card(session)
    generator = FakePronunciationGenerator()
    _use_generator(generator)

    first = client.get(f"/api/cards/{card.id}/audio", headers=telegram_headers())
    second = client.get(f"/api/cards/{card.id}/audio", headers=telegram_headers())

    for resp in (first, second):
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "audio/mpeg"
        assert resp.content == b"mp3:take off"
    assert generator.calls == ["take off"]
    assert (tmp_path / "audio" / f"{card.id}.mp3").read_bytes() == b"mp3:take off"
    assert [p.name for p in (tmp_path / "audio").iterdir()] == [f"{card.id}.mp3"]


def test_card_audio_requires_telegram_auth(client: TestClient, session: Session) -> None:
    card = _add_card(session)
    _use_generator(FakePronunciationGenerator())

    assert client.get(f"/api/cards/{card.id}/audio").status_code == 401


def test_card_audio_unknown_card_is_404(client: TestClient) -> None:
    generator = FakePronunciationGenerator()
    _use_generator(generator)

    resp = client.get("/api/cards/9999/audio", headers=telegram_headers())

    assert resp.status_code == 404
    assert generator.calls == []


def test_card_audio_generation_failure_is_502(
    client: TestClient, session: Session, tmp_path: Path
) -> None:
    card = _add_card(session)
    _use_generator(
        FakePronunciationGenerator(
            error=PronunciationAudioError("boom", user_message="Pronunciation audio failed.")
        )
    )

    resp = client.get(f"/api/cards/{card.id}/audio", headers=telegram_headers())

    assert resp.status_code == 502
    assert resp.json()["detail"] == "Pronunciation audio failed."
    assert not (tmp_path / "audio" / f"{card.id}.mp3").exists()


def test_delete_card_removes_cached_audio(
    client: TestClient, session: Session, tmp_path: Path
) -> None:
    card = _add_card(session)
    _use_generator(FakePronunciationGenerator())
    client.get(f"/api/cards/{card.id}/audio", headers=telegram_headers())
    cached = tmp_path / "audio" / f"{card.id}.mp3"
    assert cached.exists()

    assert client.delete(f"/api/cards/{card.id}", headers=telegram_headers()).status_code == 204

    assert not cached.exists()


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


def test_anki_pending_returns_learning_cards(authed_client: TestClient, session: Session) -> None:
    session.add(make_card(is_learning=True, anki_sync_status=AnkiSyncStatus.PENDING))
    session.add(
        make_card(
            is_learning=True,
            anki_sync_status=AnkiSyncStatus.FAILED,
            canonical_text="failed word",
            canonical_text_normalized="failed word",
        )
    )
    # not learning — should be excluded
    session.add(
        make_card(
            is_learning=False,
            anki_sync_status=AnkiSyncStatus.PENDING,
            canonical_text_normalized="other",
        )
    )
    # already synced — should be excluded
    session.add(
        make_card(
            is_learning=True,
            anki_sync_status=AnkiSyncStatus.SYNCED,
            canonical_text_normalized="synced",
        )
    )
    session.commit()

    resp = authed_client.get("/api/anki/pending")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["canonical_text"] == "take off"
    assert data[0]["canonical_text_normalized"] == "take off"
    assert data[1]["canonical_text"] == "failed word"
    # Only Anki-relevant fields are exposed — no source_text
    assert "source_text" not in data[0]


def test_anki_pending_puts_new_cards_before_failed_ones(
    authed_client: TestClient,
    session: Session,
) -> None:
    session.add(
        make_card(
            anki_sync_status=AnkiSyncStatus.FAILED,
            canonical_text="old failure",
            canonical_text_normalized="old failure",
        )
    )
    session.commit()
    session.add(make_card(canonical_text="fresh", canonical_text_normalized="fresh"))
    session.commit()

    resp = authed_client.get("/api/anki/pending?limit=1")

    assert [item["canonical_text"] for item in resp.json()] == ["fresh"]


def test_anki_pending_limit(authed_client: TestClient, session: Session) -> None:
    for i in range(5):
        session.add(
            make_card(
                is_learning=True,
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
    card = make_card()
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
    assert card.anki_sync_error is None


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
    card = make_card()
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
    assert card.anki_sync_error == "AnkiConnect refused"


def test_anki_fail_not_found(authed_client: TestClient) -> None:
    resp = authed_client.post(
        "/api/anki/fail",
        json={"card_id": 9999, "error_message": "err"},
    )
    assert resp.status_code == 404
