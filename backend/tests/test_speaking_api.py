from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.speaking import SpeakingIssue, SpeakingSession

from .conftest import telegram_headers


def _add(session: Session, days_ago: float, seconds: int, fillers: int, issues: list[tuple]) -> int:
    row = SpeakingSession(
        recorded_at=datetime.now(UTC) - timedelta(days=days_ago),
        kind="voice",
        duration_seconds=seconds,
        prompt_text="Topic: a change in your life\n1. What?",
        words_json=json.dumps(
            [
                {"card_id": 1, "word": "prevail", "used": True},
                {"card_id": 2, "word": "try", "used": False},
            ]
        ),
        transcript="So, uh, I decided to change my job.",
        filler_count=fillers,
        natural_version="I decided to switch careers.",
        next_time="Use 'a' before jobs.",
        focus_check="better",
        llm_model="m",
    )
    session.add(row)
    session.flush()
    for category, wrong, right in issues:
        session.add(
            SpeakingIssue(session_id=row.id, category=category, wrong=wrong, right=right, why="w")
        )
    session.commit()
    return row.id


def test_stats_issues_and_detail(client: TestClient, session: Session) -> None:
    _add(session, 40, 120, 16, [("tense", "ride", "rode")])  # the 30 days before
    first = _add(
        session,
        2,
        60,
        6,
        [("article", "as engineer", "as an engineer"), ("preposition", "at China", "in China")],
    )
    _add(session, 1, 120, 6, [("article", "to IT specialist", "to an IT specialist")])

    stats = client.get("/api/speaking/stats", headers=telegram_headers()).json()
    assert stats["recordings"] == 2 and stats["minutes"] == 3
    assert stats["filler_rate"] == 4.0 and stats["filler_rate_prev"] == 8.0
    assert (stats["words_used"], stats["words_total"]) == (2, 4)
    assert stats["categories"] == [
        {"category": "article", "label": "Articles", "count": 2},
        {"category": "preposition", "label": "Prepositions", "count": 1},
    ]
    assert [row["fix_count"] for row in stats["sessions"]] == [1, 2, 1]
    assert stats["sessions"][0]["topic"] == "a change in your life"

    issues = client.get("/api/speaking/issues?category=article", headers=telegram_headers()).json()
    assert [(i["wrong"], i["right"]) for i in issues] == [
        ("to IT specialist", "to an IT specialist"),
        ("as engineer", "as an engineer"),
    ]
    assert (
        client.get("/api/speaking/issues?category=spelling", headers=telegram_headers()).status_code
        == 422
    )

    detail = client.get(f"/api/speaking/sessions/{first}", headers=telegram_headers()).json()
    assert detail["transcript"].startswith("So, uh")
    assert detail["words"] == [{"word": "prevail", "used": True}, {"word": "try", "used": False}]
    assert [i["label"] for i in detail["issues"]] == ["Articles", "Prepositions"]
    assert client.get("/api/speaking/sessions/999", headers=telegram_headers()).status_code == 404


def test_speaking_api_needs_web_app_auth(client: TestClient) -> None:
    assert client.get("/api/speaking/stats").status_code == 401
