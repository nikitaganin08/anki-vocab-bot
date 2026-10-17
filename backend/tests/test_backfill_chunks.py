from __future__ import annotations

import json

import httpx
from sqlalchemy.orm import Session

from app.clients.openrouter import OpenRouterClient, OpenRouterError
from app.models.card import Card
from app.schemas.llm import CardChunk, ChunksResponse
from app.scripts.backfill_chunks import backfill_chunks

from .conftest import make_card

CHUNK = {"text": "take off your shoes", "target": "take off", "translation": "снять обувь"}
EXAMPLE = "The plane took off at noon."


class StubChunksClient:
    def __init__(self, *, fail_for: set[str] | None = None) -> None:
        self.fail_for = fail_for or set()
        self.calls: list[str] = []

    def generate_chunks(
        self, canonical_text: str, translation_variants: list[str], examples: list[str]
    ) -> ChunksResponse:
        self.calls.append(canonical_text)
        if canonical_text in self.fail_for:
            raise OpenRouterError("boom", code="openrouter_timeout", user_message="timeout")
        return ChunksResponse(chunks=[CardChunk(**CHUNK)], example=EXAMPLE)


def _add(session: Session, **overrides: object) -> Card:
    card = make_card(**overrides)
    session.add(card)
    session.commit()
    return card


def test_backfill_sets_chunks_and_single_example(session: Session) -> None:
    empty = _add(session)
    filled_chunks = [{"text": "look up a word", "target": "look up", "translation": "найти"}]
    filled = _add(
        session,
        source_text="look up",
        canonical_text="look up",
        canonical_text_normalized="look up",
        chunks_json=filled_chunks,
    )
    client = StubChunksClient()

    assert backfill_chunks(session, client, limit=10) == (1, 0)  # type: ignore[arg-type]

    session.expire_all()
    assert client.calls == ["take off"]
    assert empty.chunks_json == [CHUNK]
    assert empty.examples_json == [EXAMPLE]
    assert filled.chunks_json == filled_chunks
    assert len(filled.examples_json) == 3


def test_backfill_keeps_translations(session: Session) -> None:
    card = _add(session)
    before = (card.canonical_text, card.translation_variants_json, card.transcription)

    backfill_chunks(session, StubChunksClient(), limit=10)  # type: ignore[arg-type]

    session.expire_all()
    assert (card.canonical_text, card.translation_variants_json, card.transcription) == before


def test_backfill_continues_after_llm_error(session: Session) -> None:
    broken = _add(session)
    ok = _add(
        session,
        source_text="give up",
        canonical_text="give up",
        canonical_text_normalized="give up",
    )
    client = StubChunksClient(fail_for={"take off"})

    assert backfill_chunks(session, client, limit=10) == (1, 1)  # type: ignore[arg-type]

    session.expire_all()
    assert client.calls == ["take off", "give up"]
    assert broken.chunks_json == []
    assert len(broken.examples_json) == 3
    assert ok.chunks_json == [CHUNK]


def test_generate_chunks_parses_response() -> None:
    content = json.dumps({"chunks": [CHUNK], "example": EXAMPLE})

    def handler(request: httpx.Request) -> httpx.Response:
        assert "take off" in request.content.decode()
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    client = OpenRouterClient(
        api_key="secret",
        model="test-model",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    result = client.generate_chunks("take off", ["взлетать", "снимать"], ["Take it off."])

    assert result.chunks[0].target == "take off"
    assert result.example == EXAMPLE
