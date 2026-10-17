from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import fsrs
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_openrouter_client
from app.api.schemas import AnkiImportRequest
from app.main import app
from app.models.card import AnkiSyncStatus, Card
from app.schemas.llm import AcceptedLlmResponse
from app.scripts.import_anki import collect_import_items
from app.services.anki_import import fsrs_card_from_anki, import_anki_note

from .conftest import anki_headers, make_card

NOW = datetime(2026, 10, 20, 9, 0, tzinfo=UTC)
LAST_REVIEW = datetime(2026, 10, 10, 9, 0, tzinfo=UTC)


@dataclass
class StubGenerator:
    calls: list[str] = field(default_factory=list)
    model: str = "test-model"

    def generate_card(self, source_text: str) -> AcceptedLlmResponse:
        self.calls.append(source_text)
        return AcceptedLlmResponse.model_validate(
            {
                "accepted": True,
                "source_language": "en",
                "entry_type": "phrasal_verb",
                "canonical_text": "give up",
                "transcription": "/ɡɪv ʌp/",
                "translation_variants": ["сдаваться", "бросать"],
                "explanation": "To stop trying.",
                "examples": ["Never give up on your dreams."],
                "frequency": 1,
                "frequency_note": "Common.",
            }
        )


def _item(**overrides: object) -> AnkiImportRequest:
    data: dict[str, object] = dict(
        word="take off",
        translation="взлетать",
        anki_note_id=1_700_000_000_000,
        backend_card_id=None,
        suspended=False,
        card_type=2,
        interval_days=20,
        ease=2.5,
        last_review_at=LAST_REVIEW,
        reps=7,
        lapses=1,
    )
    data.update(overrides)
    return AnkiImportRequest.model_validate(data)


def _add(session: Session, **overrides: object) -> Card:
    card = make_card(**overrides)
    session.add(card)
    session.commit()
    return card


def test_fsrs_card_from_anki_review_state() -> None:
    card = fsrs_card_from_anki(_item(), 5, NOW)

    assert card is not None
    assert card.state == fsrs.State.Review
    assert card.stability == 20
    assert card.difficulty == 5
    assert card.last_review == LAST_REVIEW
    assert card.due == LAST_REVIEW + timedelta(days=20)


def test_new_anki_card_has_no_srs_state(session: Session) -> None:
    card = _add(session)

    assert fsrs_card_from_anki(_item(card_type=0), card.id, NOW) is None
    status, imported = import_anki_note(
        session,
        StubGenerator(),  # type: ignore[arg-type]
        _item(card_type=0, backend_card_id=card.id),
        NOW,
    )

    assert status == "linked"
    assert imported is card
    assert (card.srs_card_json, card.srs_state, card.srs_due_at) == (None, None, None)


def test_import_links_existing_by_tag(session: Session) -> None:
    card = _add(session)
    generator = StubGenerator()

    status, imported = import_anki_note(
        session,
        generator,  # type: ignore[arg-type]
        _item(word="something else", backend_card_id=card.id),
        NOW,
    )

    assert status == "linked"
    assert imported is card
    assert generator.calls == []
    assert card.srs_state == "review"
    assert (card.srs_reps, card.srs_lapses) == (7, 1)
    assert card.srs_due_at is not None
    assert card.srs_due_at.replace(tzinfo=UTC) == LAST_REVIEW + timedelta(days=20)


def test_import_links_existing_by_word(session: Session) -> None:
    card = _add(session)
    generator = StubGenerator()

    status, imported = import_anki_note(
        session,
        generator,  # type: ignore[arg-type]
        _item(word="<b>Take&nbsp;Off</b>"),
        NOW,
    )

    assert (status, imported) == ("linked", card)
    assert generator.calls == []


def test_import_creates_card_via_pipeline(session: Session) -> None:
    generator = StubGenerator()

    status, card = import_anki_note(
        session,
        generator,  # type: ignore[arg-type]
        _item(word="give up", translation="<i>отказываться</i>", card_type=1),
        NOW,
    )

    assert status == "created"
    assert card is not None
    assert generator.calls == ["give up"]
    assert card.translation_variants_json == ["отказываться", "сдаваться", "бросать"]
    # Rare by LLM frequency, but the owner already learns it in Anki.
    assert card.is_learning is True
    assert card.srs_state == "learning"


def test_import_marks_card_synced_with_note_id(session: Session, authed_client: TestClient) -> None:
    card = _add(session)

    import_anki_note(
        session,
        StubGenerator(),  # type: ignore[arg-type]
        _item(backend_card_id=card.id),
        NOW,
    )

    assert card.anki_sync_status == AnkiSyncStatus.SYNCED
    assert card.anki_note_id == 1_700_000_000_000
    assert authed_client.get("/api/anki/pending").json() == []


def test_suspended_note_not_learning(session: Session) -> None:
    card = _add(session)

    import_anki_note(
        session,
        StubGenerator(),  # type: ignore[arg-type]
        _item(backend_card_id=card.id, suspended=True),
        NOW,
    )

    assert card.is_learning is False


def test_import_endpoint_requires_token(client: TestClient, session: Session) -> None:
    card = _add(session)
    app.dependency_overrides[get_openrouter_client] = lambda: StubGenerator()
    payload = _item(backend_card_id=card.id).model_dump(mode="json")

    assert client.post("/api/anki/import", json=payload).status_code == 401
    resp = client.post("/api/anki/import", json=payload, headers=anki_headers())

    assert resp.status_code == 200
    assert resp.json() == {"status": "linked", "card_id": card.id}


class FakeAnkiClient:
    def find_notes(self, query: str) -> list[int]:
        assert query == 'deck:"English::Inbox"'
        return [11, 12]

    def notes_info(self, ids: list[int]) -> list[dict]:
        return [
            {
                "noteId": 11,
                "tags": ["avb-card-5", "leech"],
                "fields": {"Word": {"value": "take off"}, "Translation": {"value": "взлетать"}},
                "cards": [101],
            },
            {
                "noteId": 12,
                "tags": [],
                "fields": {"Word": {"value": "give up"}, "Translation": {"value": "сдаваться"}},
                "cards": [102],
            },
        ]

    def cards_info(self, ids: list[int]) -> list[dict]:
        assert ids == [101, 102]
        return [
            {
                "cardId": 101,
                "type": 2,
                "queue": 2,
                "interval": 20,
                "factor": 2500,
                "reps": 7,
                "lapses": 1,
            },
            {
                "cardId": 102,
                "type": 0,
                "queue": -1,
                "interval": 0,
                "factor": 0,
                "reps": 0,
                "lapses": 0,
            },
        ]

    def reviews_of_cards(self, card_ids: list[int]) -> dict[str, list[dict]]:
        stamp = int(LAST_REVIEW.timestamp() * 1000)
        return {"101": [{"id": stamp - 1000}, {"id": stamp}], "102": []}


def test_collect_import_items_maps_anki_fields() -> None:
    first, second = collect_import_items(FakeAnkiClient())  # type: ignore[arg-type]

    assert first == {
        "word": "take off",
        "translation": "взлетать",
        "anki_note_id": 11,
        "backend_card_id": 5,
        "suspended": False,
        "card_type": 2,
        "interval_days": 20,
        "ease": 2.5,
        "last_review_at": LAST_REVIEW.isoformat(),
        "reps": 7,
        "lapses": 1,
    }
    assert second["backend_card_id"] is None
    assert second["suspended"] is True
    assert second["last_review_at"] is None
