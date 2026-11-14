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

from app.bot.handler import (
    RECORDING_FAILED,
    RETRY_KEYBOARD,
    TelegramRecordingHandler,
    TelegramSpeakHandler,
)
from app.bot.rate_limiter import InMemoryRateLimiter
from app.clients.openrouter import OpenRouterClient, OpenRouterError
from app.models.speaking import SpeakingIssue, SpeakingSession
from app.schemas.speaking import (
    SpeakingFeedback,
    SpeakingRejected,
    SpeakingTopic,
    parse_speaking_result,
    parse_speaking_topic,
)
from app.services.app_settings import get_app_settings
from app.services.speaking import (
    analyse_recording,
    count_fillers,
    pick_words,
    prepare_reminder,
    prepare_weekly_summary,
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


def test_count_fillers_of_any_length_and_script() -> None:
    text = "Ummm, uhhh... errr, m-m-m, Mmm. Uhm, эээ, ммм. Uh-huh, I'm mum, a summer term."
    assert count_fillers(text) == Counter({"um": 2, "uh": 2, "er": 1, "mm": 3})


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


def test_last_focus_line_stays_when_the_model_could_not_tell(session: Session) -> None:
    session.add(_session_row(next_time="Use articles with professions."))
    session.commit()

    reply = analyse_recording(
        session,
        lambda **_: _feedback(focus_check=None),
        audio=b"x",
        kind="voice",
        audio_format="ogg",
        duration_seconds=30,
        llm_model="m",
        now=_moscow(12, 17),
    )
    assert "🎯 Last focus: <b>no chance to tell</b>" in reply


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
        self.message_id = 555
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

    async def reply(self, text: str, **kwargs: Any) -> None:
        self.answers.append((text, {"reply": True, **kwargs}))


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
        (b"audio-bytes", "voice", "ogg", 47, 555),
        (b"audio-bytes", "video_note", "mp4", 42, 555),
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
    assert failed.answers == [("Timed out.", {"reply": True, "reply_markup": RETRY_KEYBOARD})]


class FakeCallback:
    def __init__(self, source: Any) -> None:
        self.from_user = SimpleNamespace(id=TELEGRAM_ALLOWED_USER_ID)
        self.message = SimpleNamespace(reply_to_message=source, delete=self._delete)
        self.answers: list[tuple[str, dict[str, Any]]] = []
        self.deleted = False

    async def _delete(self) -> None:
        self.deleted = True

    async def answer(self, text: str, **kwargs: Any) -> None:
        self.answers.append((text, kwargs))


def test_try_again_takes_the_recording_from_the_failure_reply() -> None:
    results = iter([RuntimeError("boom"), "<b>Feedback</b>"])

    def flaky(*_: Any) -> str:
        result = next(results)
        if isinstance(result, Exception):
            raise result
        return result

    handler = _recording_handler(flaky)
    voice = FakeMessage(voice=SimpleNamespace(duration=10, file_id="v"))
    _handle(handler, voice)
    assert voice.answers == [(RECORDING_FAILED, {"reply": True, "reply_markup": RETRY_KEYBOARD})]

    callback = FakeCallback(voice)

    async def retry() -> None:
        await handler.handle_retry(callback)
        await asyncio.gather(*handler.pending)

    asyncio.run(retry())
    assert callback.deleted and callback.answers == [("Checking again…", {})]
    assert voice.answers[-1] == ("<b>Feedback</b>", {"parse_mode": "HTML"})
    assert len(voice.downloads) == 2

    gone = FakeCallback(None)
    asyncio.run(handler.handle_retry(gone))
    assert gone.answers[0][1] == {"show_alert": True} and not gone.deleted


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


def test_top_three_fixes_shown_and_the_rest_collapsed_all_stored(session: Session) -> None:
    fixes = [
        {"wrong": f"w{n}", "right": f"r{n}", "why": f"y{n}", "category": "article"}
        for n in range(1, 6)
    ]
    reply = analyse_recording(
        session,
        lambda **_: _feedback(fixes=fixes, words_used=[]),
        audio=b"x",
        kind="voice",
        audio_format="ogg",
        duration_seconds=103,
        llm_model="m",
        now=_moscow(12, 9),
    )

    assert "✏️ <b>Top fixes</b> (3 of 5)\n1. <s>w1</s> → <b>r1</b>" in reply
    assert "3. <s>w3</s> → <b>r3</b>" in reply
    collapsed = reply[reply.index("<blockquote expandable>") :]
    assert collapsed.startswith("<blockquote expandable>➕ <b>2 more</b>\n4. <s>w4</s>")
    assert "5. <s>w5</s> → <b>r5</b>\n    <i>y5</i></blockquote>" in collapsed
    assert len(session.scalars(select(SpeakingIssue)).all()) == 5


def test_topic_that_gives_a_target_word_away_is_invalid() -> None:
    payload = {"topic": "your free evenings", "questions": ["What do you do?", "Was it worth it?"]}
    with pytest.raises(ValueError):
        parse_speaking_topic(json.dumps(payload), ["free"])
    with pytest.raises(ValueError):
        parse_speaking_topic(json.dumps(payload), ["worth it"])
    assert (
        parse_speaking_topic(json.dumps(payload), ["satellite", "it"]).topic == "your free evenings"
    )


def _recording(
    day: int,
    hour: int,
    *,
    seconds: int,
    fillers: int,
    message_id: int | None,
    words: list[dict[str, Any]],
    issues: list[tuple[str, str | None, str | None]],
) -> SpeakingSession:
    row = _session_row(
        recorded_at=_moscow(day, hour),
        duration_seconds=seconds,
        filler_count=fillers,
        words_json=json.dumps(words),
        telegram_message_id=message_id,
    )
    row.issues_for_test = issues  # type: ignore[attr-defined]
    return row


def _store(session: Session, rows: list[SpeakingSession]) -> None:
    for row in rows:
        session.add(row)
        session.flush()
        for category, wrong, right in row.issues_for_test:  # type: ignore[attr-defined]
            session.add(
                SpeakingIssue(
                    session_id=row.id, category=category, wrong=wrong, right=right, why="w"
                )
            )
    session.commit()


def test_weekly_summary_on_monday_morning_once(session: Session) -> None:
    # November 2026: Monday the 9th and 16th. Last week = Nov 9-15, the week before = Nov 2-8.
    _store(
        session,
        [
            _recording(3, 16, seconds=120, fillers=16, message_id=None, words=[], issues=[]),
            _recording(
                9,
                16,
                seconds=103,
                fillers=11,
                message_id=501,
                words=[
                    {"card_id": 1, "word": "free", "used": True},
                    {"card_id": 2, "word": "vivid", "used": False},
                ],
                issues=[
                    ("preposition", "at China", "in China"),
                    ("article", "at end of May", "at the end of May"),
                ],
            ),
            _recording(
                14,
                18,
                seconds=137,
                fillers=5,
                message_id=502,
                words=[],
                issues=[
                    ("preposition", None, None),
                    ("preposition", "in our trip", "on our trip"),
                    ("tense", "ride", "rode"),
                ],
            ),
        ],
    )
    assert prepare_weekly_summary(session, _moscow(16, 9, 55)) is None  # before 10:00
    summary = prepare_weekly_summary(session, _moscow(16, 10))
    assert summary is not None
    assert summary.text.splitlines()[:5] == [
        "📊 <b>Your speaking week</b> · Nov 9–15",
        "<blockquote>🗓 2 of 7 days · 4 min spoken",
        "🗣 Fillers: 8.0 → <b>4.0</b>/min 📉",
        "📚 Deck words used: 1 of 2</blockquote>",
        "",
    ]
    assert "<b>Prepositions</b> ×3 · <s>at China</s> → <b>in China</b>" in summary.text
    assert "<b>Articles</b> ×1" in summary.text and "<b>Tenses</b> ×1" in summary.text
    assert "🎧 <b>Before today's topic:</b>" in summary.text
    assert summary.text.endswith("👉 <b>Focus this week:</b> prepositions")
    assert summary.forward_message_ids == [501, 502]
    assert prepare_weekly_summary(session, _moscow(16, 12)) is None  # once a week


def test_no_weekly_summary_without_recordings_or_off_monday(session: Session) -> None:
    assert prepare_weekly_summary(session, _moscow(17, 10)) is None  # Tuesday
    assert prepare_weekly_summary(session, _moscow(16, 10)) is None  # no recordings last week
    assert get_app_settings(session).speaking_weekly_on is not None
