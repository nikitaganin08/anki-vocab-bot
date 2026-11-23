from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_openrouter_client, get_speaking_client
from app.clients.openrouter import OpenRouterError
from app.main import app
from app.schemas.sentence_check import (
    SentenceFeedback,
    SentenceIssue,
    parse_sentence_feedback,
    parse_word_translation,
)
from app.schemas.speaking import SpeakingRejected, SpokenSentence, parse_spoken_sentence
from app.services.llm_prompt import build_sentence_check_messages

from .conftest import make_card, telegram_headers


def test_parse_normalizes_and_validates_issues() -> None:
    feedback = parse_sentence_feedback(
        {
            "ok": False,
            "corrected": "  She pleaded   guilty. ",
            "issues": [
                {"wrong": " plead ", "right": "pleaded", "why": "Use  the past form."},
                {"why": "Not how people say it."},
            ],
        }
    )

    assert feedback == SentenceFeedback(
        ok=False,
        corrected="She pleaded guilty.",
        issues=[
            SentenceIssue(wrong="plead", right="pleaded", why="Use the past form."),
            SentenceIssue(why="Not how people say it."),
        ],
    )
    assert parse_sentence_feedback({"ok": True, "corrected": None, "issues": []}).issues == []


@pytest.mark.parametrize(
    "payload",
    [
        {"ok": False, "corrected": "x", "issues": []},
        {"ok": False, "corrected": "x", "issues": [{"wrong": "a", "why": "b"}]},
        {"ok": False, "corrected": "x", "issues": [{"wrong": "a", "right": "b", "why": " "}]},
        {"ok": True, "issues": [], "extra": 1},
    ],
)
def test_parse_rejects_bad_feedback(payload: dict) -> None:
    with pytest.raises(ValueError):
        parse_sentence_feedback(payload)


def test_prompt_names_the_target_and_the_sentence() -> None:
    messages = build_sentence_check_messages("plead", "He pleaded for help.")

    assert messages[0]["role"] == "system"
    assert messages[1]["content"] == "target: plead\nsentence: He pleaded for help."


@dataclass
class FakeClient:
    result: SentenceFeedback | Exception
    calls: list[tuple[str, str]] = field(default_factory=list)

    def check_sentence(self, target: str, sentence: str) -> SentenceFeedback:
        self.calls.append((target, sentence))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _card(session: Session):  # noqa: ANN202
    card = make_card(canonical_text="plead")
    session.add(card)
    session.commit()
    return card


def test_sentence_endpoint_returns_feedback(client: TestClient, session: Session) -> None:
    card = _card(session)
    fake = FakeClient(SentenceFeedback(ok=True, corrected=None))
    app.dependency_overrides[get_openrouter_client] = lambda: fake

    resp = client.post(
        f"/api/review/{card.id}/sentence",
        json={"sentence": "  He pleaded for help.  "},
        headers=telegram_headers(),
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "corrected": None, "issues": []}
    assert fake.calls == [("plead", "He pleaded for help.")]


def test_sentence_endpoint_errors(client: TestClient, session: Session) -> None:
    card = _card(session)
    url = f"/api/review/{card.id}/sentence"
    body = {"sentence": "x"}
    app.dependency_overrides[get_openrouter_client] = lambda: FakeClient(
        OpenRouterError("boom", code="x", user_message="Try again later.")
    )

    failed = client.post(url, json=body, headers=telegram_headers())
    missing = client.post("/api/review/999/sentence", json=body, headers=telegram_headers())
    empty = client.post(url, json={"sentence": ""}, headers=telegram_headers())
    anonymous = client.post(url, json=body)

    assert failed.status_code == 502 and failed.json() == {"detail": "Try again later."}
    assert missing.status_code == 404
    assert empty.status_code == 422
    assert anonymous.status_code == 401


@dataclass
class FakeTranscriber:
    result: SpokenSentence | SpeakingRejected
    calls: list[dict] = field(default_factory=list)

    def transcribe_sentence(self, **kwargs: object) -> SpokenSentence | SpeakingRejected:
        self.calls.append(kwargs)
        return self.result


def test_transcribe_endpoint_turns_dictation_into_text(
    client: TestClient, session: Session
) -> None:
    card = _card(session)
    fake = FakeTranscriber(SpokenSentence(ok=True, text="He pleaded for help."))
    app.dependency_overrides[get_speaking_client] = lambda: fake
    headers = {**telegram_headers(), "Content-Type": "audio/mp4; codecs=mp4a.40.2"}

    resp = client.post(f"/api/review/{card.id}/transcribe", content=b"m4a", headers=headers)

    assert resp.status_code == 200 and resp.json() == {"text": "He pleaded for help."}
    assert fake.calls == [{"audio": b"m4a", "audio_format": "mp4", "word": "plead"}]


def test_transcribe_endpoint_errors(client: TestClient, session: Session) -> None:
    card = _card(session)
    url = f"/api/review/{card.id}/transcribe"
    app.dependency_overrides[get_speaking_client] = lambda: FakeTranscriber(
        SpeakingRejected(ok=False, message_for_user="I couldn't hear any English.")
    )
    mp4 = {**telegram_headers(), "Content-Type": "audio/mp4"}

    silent = client.post(url, content=b"x", headers=mp4)
    wav = client.post(
        url, content=b"x", headers={**telegram_headers(), "Content-Type": "audio/x-foo"}
    )
    empty = client.post(url, content=b"", headers=mp4)
    huge = client.post(url, content=b"x" * 2_000_001, headers=mp4)

    assert silent.status_code == 422
    assert silent.json() == {"detail": "I couldn't hear any English."}
    assert (wav.status_code, empty.status_code, huge.status_code) == (415, 400, 413)


def test_parse_spoken_sentence() -> None:
    assert parse_spoken_sentence({"ok": True, "text": " He  pleaded. "}).text == "He pleaded."
    with pytest.raises(ValueError):
        parse_spoken_sentence({"ok": True, "text": ""})


@dataclass
class FakeTranslator:
    result: str | None | Exception
    calls: list[str] = field(default_factory=list)

    def translate_word(self, text: str) -> str | None:
        self.calls.append(text)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_translate_takes_the_deck_card_first(client: TestClient, session: Session) -> None:
    session.add(
        make_card(
            canonical_text="insist",
            canonical_text_normalized="insist",
            translation_variants_json=["настаивать, требовать", "настаивать", "упорствовать"],
        )
    )
    session.commit()
    fake = FakeTranslator("x")
    app.dependency_overrides[get_openrouter_client] = lambda: fake

    resp = client.post(
        "/api/review/translate", json={"text": " Insist "}, headers=telegram_headers()
    )

    assert resp.json() == {"translation": "настаивать, требовать"} and fake.calls == []


def test_translate_asks_the_model_for_other_words(client: TestClient, session: Session) -> None:
    url = "/api/review/translate"
    app.dependency_overrides[get_openrouter_client] = lambda: FakeTranslator("убеждать")
    assert client.post(url, json={"text": "persuade"}, headers=telegram_headers()).json() == {
        "translation": "убеждать"
    }

    app.dependency_overrides[get_openrouter_client] = lambda: FakeTranslator(
        OpenRouterError("x", code="x", user_message="Couldn't translate this word.")
    )
    failed = client.post(url, json={"text": "persuade"}, headers=telegram_headers())
    too_long = client.post(url, json={"text": "x" * 61}, headers=telegram_headers())
    assert failed.status_code == 502 and too_long.status_code == 422
    assert client.post(url, json={"text": "persuade"}).status_code == 401


def test_parse_word_translation() -> None:
    assert parse_word_translation({"translation": " убеждать,  уговаривать "}) == (
        "убеждать, уговаривать"
    )
    assert parse_word_translation({"translation": None}) is None
    with pytest.raises(ValueError):
        parse_word_translation({"translation": "x", "note": "y"})
