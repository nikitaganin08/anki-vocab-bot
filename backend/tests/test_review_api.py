from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from fsrs import Card as FsrsCard
from fsrs import State
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.card import Card
from app.models.review_log import ReviewLogEntry
from app.services.app_settings import get_app_settings

from .conftest import make_card, telegram_headers

CHUNKS = [{"text": "give up smoking", "target": "give up", "translation": "бросить курить"}]


def _add_card(session: Session, **overrides: object) -> Card:
    card = make_card(
        canonical_text="give up",
        canonical_text_normalized="give up",
        chunks_json=CHUNKS,
        **overrides,
    )
    session.add(card)
    session.commit()
    return card


def _grade_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "rating": 3,
        "auto_rating": 3,
        "overridden": False,
        "typed": "give up",
        "prompt_kind": "chunk",
        "prompt_index": 0,
        "verdict": "correct",
        "hint_used": False,
        "response_ms": 4200,
        "expected_due_at": None,
    }
    body.update(overrides)
    return body


def test_review_requires_telegram_auth(client: TestClient) -> None:
    for path in ("/api/review/summary", "/api/review/session", "/api/settings"):
        assert client.get(path).status_code == 401
    assert client.post("/api/review/undo").status_code == 401
    assert client.patch("/api/cards/1", json={"is_learning": False}).status_code == 401

    resp = client.get("/api/review/summary", headers=telegram_headers())
    assert resp.status_code == 200
    assert resp.json()["due_today"] == 0
    assert len(resp.json()["heatmap"]) == 98


def test_session_hides_expected_answer(client: TestClient, session: Session) -> None:
    card = _add_card(session)

    resp = client.get("/api/review/session?size=5", headers=telegram_headers())

    assert resp.status_code == 200
    [item] = resp.json()["items"]
    assert item["card"]["id"] == card.id
    assert item["intro"] is True
    assert item["srs_due_at"] is None
    assert item["prompt"] == {
        "kind": "chunk",
        "index": 0,
        "masked": "___ smoking",
        "hint_translation": "бросить курить",
        "first_letter_hint": "g___ __",
    }
    assert client.get("/api/review/session?size=21", headers=telegram_headers()).status_code == 422


def test_session_endpoint_include_backlog(client: TestClient, session: Session) -> None:
    get_app_settings(session).reviews_per_day = 0
    due = datetime.now(UTC) - timedelta(days=1)
    card = _add_card(session, srs_state="review", srs_due_at=due)
    card.srs_card_json = FsrsCard(
        card_id=card.id,
        state=State.Review,
        step=None,
        stability=10.0,
        difficulty=5.0,
        due=due,
        last_review=due - timedelta(days=10),
    ).to_json()
    session.commit()

    capped = client.get("/api/review/session", headers=telegram_headers())
    backlog = client.get("/api/review/session?include_backlog=true", headers=telegram_headers())

    assert capped.json()["items"] == []
    assert [item["card"]["id"] for item in backlog.json()["items"]] == [card.id]


def test_check_then_grade_flow(client: TestClient, session: Session) -> None:
    card = _add_card(session)

    check = client.post(
        f"/api/review/{card.id}/check",
        json={"typed": "Give  up", "prompt_kind": "chunk", "prompt_index": 0, "hint_used": True},
        headers=telegram_headers(),
    )
    assert check.status_code == 200
    data = check.json()
    assert data["verdict"] == "correct"
    assert data["expected"] == "give up"
    assert data["auto_rating"] == 2
    assert set(data["intervals"]) == {"1", "2", "3", "4"}
    assert data["intervals"]["1"] <= data["intervals"]["4"]

    wrong = client.post(
        f"/api/review/{card.id}/check",
        json={
            "typed": "take off",
            "prompt_kind": "translation",
            "prompt_index": 0,
            "hint_used": False,
        },
        headers=telegram_headers(),
    )
    assert wrong.json()["verdict"] == "wrong"
    assert wrong.json()["expected"] == "give up"

    grade = client.post(
        f"/api/review/{card.id}/grade", json=_grade_body(), headers=telegram_headers()
    )
    assert grade.status_code == 200
    assert grade.json()["srs_state"] == "learning"
    assert grade.json()["srs_due_at"] is not None

    # The due returned by grade is what the next grade must echo back.
    again = client.post(
        f"/api/review/{card.id}/grade",
        json=_grade_body(expected_due_at=grade.json()["srs_due_at"]),
        headers=telegram_headers(),
    )
    assert again.status_code == 200
    assert (
        client.post(
            "/api/review/999/grade", json=_grade_body(), headers=telegram_headers()
        ).status_code
        == 404
    )


def test_grade_rejects_stale_due(client: TestClient, session: Session) -> None:
    card = _add_card(session)

    first = client.post(
        f"/api/review/{card.id}/grade", json=_grade_body(), headers=telegram_headers()
    )
    second = client.post(
        f"/api/review/{card.id}/grade", json=_grade_body(), headers=telegram_headers()
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert session.scalar(select(func.count()).select_from(ReviewLogEntry)) == 1


def test_undo_endpoint(client: TestClient, session: Session) -> None:
    card = _add_card(session)
    assert client.post("/api/review/undo", headers=telegram_headers()).status_code == 404

    client.post(f"/api/review/{card.id}/grade", json=_grade_body(), headers=telegram_headers())
    resp = client.post("/api/review/undo", headers=telegram_headers())

    assert resp.status_code == 200
    assert resp.json() == {"card_id": card.id}
    session.refresh(card)
    assert card.srs_state is None
    assert card.srs_card_json is None
    assert session.scalar(select(func.count()).select_from(ReviewLogEntry)) == 0


def test_settings_roundtrip_and_validation(client: TestClient) -> None:
    defaults = client.get("/api/settings", headers=telegram_headers())
    assert defaults.status_code == 200
    assert defaults.json() == {
        "timezone": "Europe/Moscow",
        "reminder_hour": 10,
        "reminder_anchor": None,
        "new_per_day": 5,
        "reviews_per_day": 50,
        "desired_retention": 0.9,
        "learn_threshold": 3,
    }

    updated = {
        "timezone": "Asia/Tbilisi",
        "reminder_hour": 8,
        "reminder_anchor": "после кофе",
        "new_per_day": 10,
        "reviews_per_day": 100,
        "desired_retention": 0.85,
        "learn_threshold": 4,
    }
    put = client.put("/api/settings", json=updated, headers=telegram_headers())
    assert put.status_code == 200
    assert put.json() == updated
    assert client.get("/api/settings", headers=telegram_headers()).json() == updated

    for bad in (
        {"timezone": "Mars/Olympus"},
        {"timezone": "../etc/passwd"},
        {"timezone": "Europe"},
        {"reminder_hour": 24},
        {"new_per_day": 101},
        {"reviews_per_day": 1001},
        {"desired_retention": 0.99},
        {"learn_threshold": 11},
    ):
        resp = client.put("/api/settings", json={**updated, **bad}, headers=telegram_headers())
        assert resp.status_code == 422, bad
    assert client.get("/api/settings", headers=telegram_headers()).json() == updated


def test_patch_is_learning(client: TestClient, session: Session) -> None:
    card = _add_card(session)

    resp = client.patch(
        f"/api/cards/{card.id}", json={"is_learning": False}, headers=telegram_headers()
    )

    assert resp.status_code == 200
    assert resp.json()["is_learning"] is False
    session.refresh(card)
    assert card.is_learning is False
    assert (
        client.patch(
            "/api/cards/999", json={"is_learning": True}, headers=telegram_headers()
        ).status_code
        == 404
    )
