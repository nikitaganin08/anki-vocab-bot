from __future__ import annotations

import asyncio
import json
import random
from collections import Counter
from datetime import UTC, datetime
from io import BytesIO
from types import SimpleNamespace
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bot.handler import TelegramRecordingHandler, TelegramSpeakHandler
from app.bot.rate_limiter import InMemoryRateLimiter
from app.clients.openrouter import OpenRouterClient, OpenRouterError
from app.models.speaking import SpeakingIssue, SpeakingSession
from app.schemas.speaking import (
    SpeakingFeedback,
    SpeakingRejected,
    SpeakingTopic,
    parse_speaking_result,
)
from app.services.app_settings import get_app_settings
from app.services.speaking import (
    analyse_recording,
    count_fillers,
    pick_words,
    prepare_reminder,
    prompt_for_speak_command,
    today_prompt,
)

from .conftest import TELEGRAM_ALLOWED_USER_ID, make_card

MOSCOW = ZoneInfo("Europe/Moscow")
TOPIC = SpeakingTopic(topic="a place you'd like to go back to", questions=["Where?", "Why?"])


def _moscow(day: int, hour: int, minute: int = 0) -> datetime:
    """November 2026: the 12th is a Thursday, the 14th a Saturday."""
    return datetime(2026, 11, day, hour, minute, tzinfo=MOSCOW).astimezone(UTC)


class TopicStub:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], bool]] = []

    def __call__(self, words: list[str], story_day: bool) -> SpeakingTopic:
        self.calls.append((words, story_day))
        return TOPIC


def _feedback(**overrides: Any) -> SpeakingFeedback:
    raw: dict[str, Any] = {
        "ok": True,
        "transcript": "Um, I suggested to go there. Uh, it was <great>. Umm, yes.",
        "words_used": [{"word": "Linger", "used": True}],
        "fixes": [
            {
                "wrong": "suggested to go",
                "right": "suggested going",
                "why": "suggest + -ing",
                "category": "verb_pattern",
            },
            {
                "wrong": None,
                "right": None,
                "why": "Not how people say it.",
                "category": "word_choice",
            },
        ],
        "natural_version": "I suggested going there.",
        "next_time": "Say 'let me think' instead of 'um'.",
        "focus_check": "better",
    }
    raw.update(overrides)
    return SpeakingFeedback.model_validate(raw)


def _cards(session: Session) -> list[int]:
    cards = [
        make_card(canonical_text=word, canonical_text_normalized=word, srs_state=state)
        for word, state in [("linger", "review"), ("vivid", "review"), ("fresh", None)]
    ]
    session.add_all(cards)
    session.commit()
    return [card.id for card in cards]


def test_count_fillers_counts_whole_words_only() -> None:
    text = "Um, so umm I uh went... Er, the umbrella, hmm. UH! summer erm"
    assert count_fillers(text) == Counter({"um": 2, "uh": 2, "er": 1, "hmm": 1, "erm": 1})


def test_pick_words_prefers_review_cards_and_fills_up(session: Session) -> None:
    assert pick_words(session) == []
    session.add(
        make_card(canonical_text="paused", canonical_text_normalized="paused", is_learning=False)
    )
    _cards(session)

    words = pick_words(session)
    assert {w["word"] for w in words} == {"linger", "vivid", "fresh"}
    session.add(
        make_card(canonical_text="eager", canonical_text_normalized="eager", srs_state="review")
    )
    session.commit()
    assert {w["word"] for w in pick_words(session)} == {"linger", "vivid", "eager"}


def test_today_prompt_is_generated_once_with_words_and_last_focus(session: Session) -> None:
    _cards(session)
    session.add(_session_row(next_time="Fewer fillers."))
    session.commit()
    topic = TopicStub()

    text = today_prompt(session, topic, _moscow(12, 15))
    assert text.startswith(
        "🎙 <b>Speaking practice</b>\n\n📌 <b>A place you'd like to go back to</b>\n1. Where?"
    )
    assert "• <b>linger</b> — взлетать" in text
    assert "💡 <b>Last time:</b> <i>Fewer fillers.</i>" in text
    assert today_prompt(session, topic, _moscow(12, 20)) == text
    assert len(topic.calls) == 1 and topic.calls[0][1] is False

    today_prompt(session, topic, _moscow(14, 15))  # Saturday: story day
    assert topic.calls[1][1] is True


def test_speak_command_lifts_the_backoff(session: Session) -> None:
    get_app_settings(session).speaking_ignored = 7
    session.commit()
    assert prompt_for_speak_command(session, TopicStub(), _moscow(12, 9)).startswith("🎙")
    assert get_app_settings(session).speaking_ignored == 0


def _session_row(**overrides: Any) -> SpeakingSession:
    values: dict[str, Any] = dict(
        recorded_at=_moscow(11, 16),
        kind="voice",
        duration_seconds=60,
        transcript="Hello.",
        filler_count=0,
        next_time="Slow down.",
        llm_model="m",
    )
    values.update(overrides)
    return SpeakingSession(**values)


def test_analyse_recording_stores_findings_not_media(session: Session) -> None:
    ids = _cards(session)
    today_prompt(session, TopicStub(), _moscow(12, 15))
    session.add(_session_row(next_time="Slow down."))
    session.commit()
    calls: list[dict[str, Any]] = []

    def review(**kwargs: Any) -> SpeakingFeedback:
        calls.append(kwargs)
        return _feedback()

    reply = analyse_recording(
        session,
        review,
        audio=b"OggS...",
        kind="voice",
        audio_format="ogg",
        duration_seconds=47,
        llm_model="google/gemini-3.8-flash",
        now=_moscow(12, 17),
    )

    assert calls[0]["audio"] == b"OggS..." and calls[0]["audio_format"] == "ogg"
    assert calls[0]["last_focus"] == "Slow down."
    assert calls[0]["prompt_text"] == "Topic: a place you'd like to go back to\n1. Where?\n2. Why?"
    assert reply.splitlines()[:5] == [
        "✅ <b>Feedback</b> · 0:47",
        "",
        "🎯 Last focus: <b>better</b>",
        "🗣 Fillers: <b>3</b> · 3.8/min (um ×2, uh ×1)",
        "📚 Words: " + reply.splitlines()[4].removeprefix("📚 Words: "),
    ]
    assert "✅ linger" in reply and "❌ vivid" in reply
    assert "1. <s>suggested to go</s> → <b>suggested going</b>\n    <i>suggest + -ing</i>" in reply
    assert "2. <i>Not how people say it.</i>" in reply
    assert "<blockquote>I suggested going there.</blockquote>" in reply
    assert reply.endswith("👉 <b>Next time:</b> Say 'let me think' instead of 'um'.")

    row = session.scalars(select(SpeakingSession).order_by(SpeakingSession.id.desc())).first()
    assert row is not None and row.kind == "voice" and row.duration_seconds == 47
    assert row.filler_count == 3 and row.focus_check == "better"
    assert "<great>" in row.transcript
    words = json.loads(row.words_json)
    assert {w["card_id"] for w in words} == set(ids)
    assert all(set(w) == {"card_id", "word", "used"} for w in words)
    assert [w["used"] for w in words if w["word"] == "linger"] == [True]
    assert sum(w["used"] for w in words) == 1
    issues = session.scalars(select(SpeakingIssue).where(SpeakingIssue.session_id == row.id)).all()
    assert [(i.category, i.wrong) for i in issues] == [
        ("verb_pattern", "suggested to go"),
        ("word_choice", None),
    ]


def test_free_speech_without_prompt_or_focus(session: Session) -> None:
    def review(**kwargs: Any) -> SpeakingFeedback:
        assert kwargs["prompt_text"] is None and kwargs["words"] == []
        assert kwargs["last_focus"] is None
        return _feedback(words_used=[], fixes=[])

    reply = analyse_recording(
        session,
        review,
        audio=b"x",
        kind="video_note",
        audio_format="mp4",
        duration_seconds=30,
        llm_model="m",
        now=_moscow(12, 9),
    )
    assert "Last focus" not in reply and "Words:" not in reply and "Fixes" not in reply
    row = session.scalars(select(SpeakingSession)).one()
    assert row.focus_check is None and row.prompt_text is None and row.words_json == "[]"


def test_rejected_recording_is_not_stored(session: Session) -> None:
    reply = analyse_recording(
        session,
        lambda **_: SpeakingRejected(ok=False, message_for_user="No English <speech>."),
        audio=b"x",
        kind="voice",
        audio_format="ogg",
        duration_seconds=5,
        llm_model="m",
        now=_moscow(12, 9),
    )
    assert reply == "🤔 No English &lt;speech&gt;."
    assert session.scalars(select(SpeakingSession)).all() == []


def test_contract_rejects_unknown_category_and_parses_rejection() -> None:
    raw = _feedback().model_dump()
    raw["fixes"][0]["category"] = "spelling"
    with pytest.raises(ValueError):
        parse_speaking_result(json.dumps(raw))
    rejected = parse_speaking_result('{"ok": false, "message_for_user": "Silence."}')
    assert isinstance(rejected, SpeakingRejected)


def _remind(session: Session, now: datetime, seed: int = 1) -> str | None:
    return prepare_reminder(session, TopicStub(), now, random.Random(seed))


def test_reminders_from_15_with_random_follow_ups_until_21(session: Session) -> None:
    assert _remind(session, _moscow(12, 14, 55)) is None
    first = _remind(session, _moscow(12, 15))
    assert first is not None and first.startswith("🎙 <b>Speaking practice</b>")
    next_at = get_app_settings(session).speaking_next_reminder_at
    assert next_at is not None
    gap = (next_at.replace(tzinfo=UTC) - _moscow(12, 15)).total_seconds() / 60
    assert 90 <= gap <= 120

    assert _remind(session, _moscow(12, 16, 25)) is None
    follow_up = _remind(session, _moscow(12, 17))
    assert follow_up is not None and follow_up.startswith("⏰ <b>Still time for speaking today</b>")
    assert "📌 <b>A place you'd like to go back to</b>" in follow_up
    assert _remind(session, _moscow(12, 21, 30)) is None


def test_no_reminder_after_a_recording_or_when_disabled(session: Session) -> None:
    assert _remind(session, _moscow(12, 15)) is not None
    session.add(_session_row(recorded_at=_moscow(12, 15, 30)))
    session.commit()
    assert _remind(session, _moscow(12, 18)) is None

    get_app_settings(session).speaking_enabled = False
    session.commit()
    assert _remind(session, _moscow(13, 15)) is None


def test_ignored_days_back_off_then_pause_and_a_recording_resets(session: Session) -> None:
    settings = get_app_settings(session)
    for day in (9, 10, 11):
        assert _remind(session, _moscow(day, 15)) is not None
    assert settings.speaking_ignored == 2
    assert _remind(session, _moscow(12, 15)) is not None  # Thursday: ignored becomes 3
    assert settings.speaking_ignored == 3
    assert _remind(session, _moscow(12, 18)) is None  # no follow-ups in backoff

    settings.speaking_ignored = 7
    session.commit()
    assert _remind(session, _moscow(13, 15)) is None

    session.add(_session_row(recorded_at=_moscow(13, 9)))  # after the last reminder day
    session.commit()
    assert _remind(session, _moscow(14, 15)) is not None
    assert settings.speaking_ignored == 0


class FakeMessage:
    def __init__(self, user_id: int = TELEGRAM_ALLOWED_USER_ID, **media: Any) -> None:
        self.from_user = SimpleNamespace(id=user_id)
        self.chat = SimpleNamespace(id=user_id)
        self.voice = media.get("voice")
        self.video_note = media.get("video_note")
        self.answers: list[tuple[str, dict[str, Any]]] = []
        self.downloads: list[Any] = []

        async def send_chat_action(_chat_id: int, _action: str) -> None:
            return None

        async def download(file: Any) -> BytesIO:
            self.downloads.append(file)
            return BytesIO(b"audio-bytes")

        self.bot = SimpleNamespace(send_chat_action=send_chat_action, download=download)

    async def answer(self, text: str, **kwargs: Any) -> None:
        self.answers.append((text, kwargs))


def _handle(handler: TelegramRecordingHandler, message: FakeMessage) -> None:
    async def run() -> None:
        await handler.handle_message(message)
        await asyncio.gather(*handler.pending)

    asyncio.run(run())


def _recording_handler(analyse: Any) -> TelegramRecordingHandler:
    return TelegramRecordingHandler(
        allowed_user_id=TELEGRAM_ALLOWED_USER_ID,
        analyse=analyse,
        rate_limiter=InMemoryRateLimiter(limit=5, window_seconds=60.0),
    )


def test_voice_and_video_note_are_analysed_in_memory() -> None:
    calls: list[tuple[Any, ...]] = []

    def analyse(*args: Any) -> str:
        calls.append(args)
        return "<b>Feedback</b>"

    handler = _recording_handler(analyse)
    voice = FakeMessage(voice=SimpleNamespace(duration=47, file_id="v"))
    _handle(handler, voice)
    note = FakeMessage(video_note=SimpleNamespace(duration=42, file_id="n"))
    _handle(handler, note)

    assert calls == [
        (b"audio-bytes", "voice", "ogg", 47),
        (b"audio-bytes", "video_note", "mp4", 42),
    ]
    assert voice.answers == [("<b>Feedback</b>", {"parse_mode": "HTML"})]


def test_long_foreign_or_failed_recordings() -> None:
    def failing(*_: Any) -> str:
        raise OpenRouterError("x", code="openrouter_timeout", user_message="Timed out.")

    handler = _recording_handler(failing)
    long = FakeMessage(voice=SimpleNamespace(duration=15 * 60 + 1))
    _handle(handler, long)
    assert long.downloads == [] and "longer than 15 minutes" in long.answers[0][0]

    foreign = FakeMessage(user_id=7, voice=SimpleNamespace(duration=10))
    _handle(handler, foreign)
    assert foreign.answers == []

    failed = FakeMessage(voice=SimpleNamespace(duration=10))
    _handle(handler, failed)
    assert failed.answers == [("Timed out.", {})]


def test_speak_command_replies_with_the_prompt() -> None:
    message = FakeMessage()
    asyncio.run(
        TelegramSpeakHandler(TELEGRAM_ALLOWED_USER_ID, lambda: "Speaking practice").handle_message(
            message
        )
    )
    assert message.answers == [("Speaking practice", {"parse_mode": "HTML"})]


def test_client_sends_audio_with_no_data_collection() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        content = json.dumps(_feedback().model_dump())
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    client = OpenRouterClient(
        api_key="k",
        model="google/gemini-3.8-flash",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    result = client.review_speaking(
        audio=b"abc", audio_format="ogg", prompt_text=None, words=["linger"], last_focus=None
    )

    assert isinstance(result, SpeakingFeedback)
    assert seen["provider"] == {"data_collection": "deny"}
    audio_part = seen["messages"][1]["content"][1]
    assert audio_part == {"type": "input_audio", "input_audio": {"data": "YWJj", "format": "ogg"}}
    assert "words: linger" in seen["messages"][1]["content"][0]["text"]
