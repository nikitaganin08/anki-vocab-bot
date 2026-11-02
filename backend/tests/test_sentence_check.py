from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_openrouter_client
from app.clients.openrouter import OpenRouterError
from app.main import app
from app.schemas.sentence_check import SentenceFeedback, SentenceIssue, parse_sentence_feedback
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
