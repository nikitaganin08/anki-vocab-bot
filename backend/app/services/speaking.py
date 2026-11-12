"""Speaking practice: a daily topic with deck words, feedback on voice messages and video notes.

The recording itself is never stored: the bytes go to the audio model and are dropped. What the
model found is kept in `speaking_sessions` / `speaking_issues` for later analysis.
"""

from __future__ import annotations

import json
import random
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from functools import partial
from html import escape as html_escape
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.app_settings import AppSettings
from app.models.card import Card
from app.models.speaking import SpeakingIssue, SpeakingSession
from app.schemas.speaking import SpeakingRejected, SpeakingResult, SpeakingTopic
from app.services.app_settings import get_app_settings
from app.services.srs import DAY_START_HOUR, as_utc

FIRST_HOUR = 15
LAST_HOUR = 21  # no reminder at or after it
FOLLOW_UP_MINUTES = (90, 120)  # random gap after the previous reminder
BACKOFF_AFTER_IGNORED = 3
PAUSE_AFTER_IGNORED = 7
STORY_WEEKDAY = 5  # Saturday
WORDS_PER_PROMPT = 3
MAX_SECONDS = 15 * 60

FILLER_FORMS = {
    "um": "um",
    "umm": "um",
    "uh": "uh",
    "uhh": "uh",
    "er": "er",
    "erm": "erm",
    "hm": "hmm",
    "hmm": "hmm",
}


# Text nodes only: apostrophes stay readable in Telegram.
escape = partial(html_escape, quote=False)

GenerateTopic = Callable[[list[str], bool], SpeakingTopic]


@dataclass(frozen=True, slots=True)
class LocalDay:
    tz: ZoneInfo
    now_local: datetime
    today: date

    def start(self, day: date) -> datetime:
        return datetime.combine(day, time(DAY_START_HOUR), tzinfo=self.tz).astimezone(UTC)


def local_day(settings: AppSettings, now: datetime) -> LocalDay:
    tz = ZoneInfo(settings.timezone)
    now_local = as_utc(now).astimezone(tz)
    return LocalDay(tz, now_local, (now_local - timedelta(hours=DAY_START_HOUR)).date())


def count_fillers(transcript: str) -> Counter[str]:
    words = (word.strip(".,!?;:…—-\"'()").casefold() for word in transcript.split())
    return Counter(FILLER_FORMS[word] for word in words if word in FILLER_FORMS)


def pick_words(session: Session) -> list[dict[str, object]]:
    """Up to 3 learning cards, preferring ones in review (known well enough to use)."""
    learning = select(Card).where(Card.is_learning.is_(True)).order_by(func.random())
    cards = list(
        session.scalars(learning.where(Card.srs_state == "review").limit(WORDS_PER_PROMPT))
    )
    if len(cards) < WORDS_PER_PROMPT:
        taken = [card.id for card in cards]
        rest = learning.where(Card.id.not_in(taken)).limit(WORDS_PER_PROMPT - len(cards))
        cards += session.scalars(rest)
    return [
        {
            "card_id": card.id,
            "word": card.canonical_text,
            "translation": card.translation_variants_json[0]
            if card.translation_variants_json
            else None,
        }
        for card in cards
    ]


def latest_session(session: Session) -> SpeakingSession | None:
    query = select(SpeakingSession).order_by(SpeakingSession.recorded_at.desc()).limit(1)
    return session.scalar(query)


def _recorded_since(session: Session, since: datetime) -> bool:
    query = select(SpeakingSession.id).where(SpeakingSession.recorded_at >= since).limit(1)
    return session.scalar(query) is not None


def render_prompt(
    topic: SpeakingTopic,
    words: list[dict[str, object]],
    last_focus: str | None,
    *,
    follow_up: bool = False,
) -> str:
    """Telegram HTML for the reminder and `/speak`."""
    title = "⏰ <b>Still time for speaking today</b>" if follow_up else "🎙 <b>Speaking practice</b>"
    lines = [title, "", f"📌 <b>{escape(topic.topic[:1].upper() + topic.topic[1:])}</b>"]
    lines += [f"{index}. {escape(question)}" for index, question in enumerate(topic.questions, 1)]
    if words:
        lines += ["", "🎯 <b>Use these words</b>"]
        for word in words:
            translation = (
                f" — {escape(str(word['translation']))}" if word.get("translation") else ""
            )
            lines.append(f"• <b>{escape(str(word['word']))}</b>{translation}")
    if last_focus:
        lines += ["", f"💡 <b>Last time:</b> <i>{escape(last_focus)}</i>"]
    lines += ["", "⏱ 1–3 min · reply with a voice message or a video note"]
    return "\n".join(lines)


def task_text(topic: SpeakingTopic) -> str:
    """The task as the audio model sees it (and as stored with the recording)."""
    questions = [f"{index}. {question}" for index, question in enumerate(topic.questions, 1)]
    return "\n".join([f"Topic: {topic.topic}", *questions])


def _today_topic(settings: AppSettings, today: date) -> SpeakingTopic | None:
    if settings.speaking_prompt_on != today or not settings.speaking_prompt:
        return None
    return SpeakingTopic.model_validate_json(settings.speaking_prompt)


def today_prompt(
    session: Session, generate_topic: GenerateTopic, now: datetime, *, follow_up: bool = False
) -> str:
    """Today's prompt as HTML; the topic is generated once a day and kept as data."""
    settings = get_app_settings(session)
    day = local_day(settings, now)
    topic = _today_topic(settings, day.today)
    if topic is None:
        words = pick_words(session)
        topic = generate_topic(
            [str(w["word"]) for w in words], day.today.weekday() == STORY_WEEKDAY
        )
        settings.speaking_prompt = topic.model_dump_json()
        settings.speaking_prompt_words_json = json.dumps(words, ensure_ascii=False)
        settings.speaking_prompt_on = day.today
        session.commit()
    latest = latest_session(session)
    return render_prompt(
        topic,
        json.loads(settings.speaking_prompt_words_json),
        latest.next_time if latest else None,
        follow_up=follow_up,
    )


def prompt_for_speak_command(session: Session, generate_topic: GenerateTopic, now: datetime) -> str:
    """`/speak`: today's prompt; asking for it also lifts the reminder backoff."""
    text = today_prompt(session, generate_topic, now)
    get_app_settings(session).speaking_ignored = 0
    session.commit()
    return text


def _duration(seconds: int) -> str:
    return f"{seconds // 60}:{seconds % 60:02d}"


def format_feedback(
    *,
    duration_seconds: int,
    fillers: Counter[str],
    words: list[dict[str, object]],
    result: SpeakingResult,
) -> str:
    """Telegram HTML for the chat; the transcript and categories are not shown."""
    if isinstance(result, SpeakingRejected):
        return f"🤔 {escape(result.message_for_user)}"
    lines = [f"✅ <b>Feedback</b> · {_duration(duration_seconds)}", ""]
    if result.focus_check:
        lines.append(f"🎯 Last focus: <b>{result.focus_check}</b>")
    total = sum(fillers.values())
    if total:
        top = ", ".join(f"{word} ×{count}" for word, count in fillers.most_common())
        per_minute = f" · {total * 60 / duration_seconds:.1f}/min" if duration_seconds else ""
        lines.append(f"🗣 Fillers: <b>{total}</b>{per_minute} ({top})")
    else:
        lines.append("🗣 Fillers: <b>none</b>")
    if words:
        marks = " · ".join(f"{'✅' if w['used'] else '❌'} {escape(str(w['word']))}" for w in words)
        lines.append(f"📚 Words: {marks}")
    if result.fixes:
        lines += ["", "✏️ <b>Fixes</b>"]
        for index, fix in enumerate(result.fixes, 1):
            if fix.wrong is None or fix.right is None:
                lines.append(f"{index}. <i>{escape(fix.why)}</i>")
            else:
                lines.append(f"{index}. <s>{escape(fix.wrong)}</s> → <b>{escape(fix.right)}</b>")
                lines.append(f"    <i>{escape(fix.why)}</i>")
    if result.natural_version:
        lines += ["", "✨ <b>Say it like this</b>"]
        lines.append(f"<blockquote>{escape(result.natural_version)}</blockquote>")
    else:
        lines.append("")
    lines.append(f"👉 <b>Next time:</b> {escape(result.next_time)}")
    return "\n".join(lines)


ReviewSpeaking = Callable[..., SpeakingResult]


def analyse_recording(
    session: Session,
    review_speaking: ReviewSpeaking,
    *,
    audio: bytes,
    kind: str,
    audio_format: str,
    duration_seconds: int,
    llm_model: str,
    now: datetime,
) -> str:
    """Send the recording to the audio model, store what it found, return the chat reply."""
    settings = get_app_settings(session)
    day = local_day(settings, now)
    topic = _today_topic(settings, day.today)
    prompt_text = task_text(topic) if topic else None
    words: list[dict[str, object]] = (
        json.loads(settings.speaking_prompt_words_json) if topic else []
    )
    latest = latest_session(session)
    last_focus = latest.next_time if latest else None

    result = review_speaking(
        audio=audio,
        audio_format=audio_format,
        prompt_text=prompt_text,
        words=[str(w["word"]) for w in words],
        last_focus=last_focus,
    )
    if isinstance(result, SpeakingRejected):
        return format_feedback(
            duration_seconds=duration_seconds, fillers=Counter(), words=[], result=result
        )

    if not last_focus:
        result.focus_check = None
    used = {item.word.casefold(): item.used for item in result.words_used}
    words = [
        {
            "card_id": w["card_id"],
            "word": w["word"],
            "used": used.get(str(w["word"]).casefold(), False),
        }
        for w in words
    ]
    fillers = count_fillers(result.transcript)
    row = SpeakingSession(
        recorded_at=as_utc(now),
        kind=kind,
        duration_seconds=duration_seconds,
        prompt_text=prompt_text,
        words_json=json.dumps(words, ensure_ascii=False),
        transcript=result.transcript,
        filler_count=sum(fillers.values()),
        natural_version=result.natural_version,
        next_time=result.next_time,
        focus_check=result.focus_check,
        llm_model=llm_model,
    )
    session.add(row)
    session.flush()
    session.add_all(
        SpeakingIssue(
            session_id=row.id, category=fix.category, wrong=fix.wrong, right=fix.right, why=fix.why
        )
        for fix in result.fixes
    )
    session.commit()
    return format_feedback(
        duration_seconds=duration_seconds, fillers=fillers, words=words, result=result
    )


def should_send(settings: AppSettings, now: datetime, day: LocalDay, recorded_today: bool) -> bool:
    if not settings.speaking_enabled or recorded_today:
        return False
    if settings.speaking_ignored >= PAUSE_AFTER_IGNORED:
        return False
    if not FIRST_HOUR <= day.now_local.hour < LAST_HOUR:
        return False
    if settings.speaking_reminder_on != day.today:
        return settings.speaking_ignored < BACKOFF_AFTER_IGNORED or day.today.toordinal() % 2 == 0
    # Follow-ups only for someone who keeps answering reminders.
    if settings.speaking_ignored >= BACKOFF_AFTER_IGNORED or not settings.speaking_next_reminder_at:
        return False
    return as_utc(now) >= as_utc(settings.speaking_next_reminder_at)


def prepare_reminder(
    session: Session,
    generate_topic: GenerateTopic,
    now: datetime,
    rng: random.Random | None = None,
) -> str | None:
    """The reminder text to send now, or None. Marks it sent before sending (a failed send
    waits for the next follow-up instead of retrying every tick)."""
    rng = rng or random.Random()
    settings = get_app_settings(session)
    day = local_day(settings, now)
    last = settings.speaking_reminder_on
    answered = last is not None and _recorded_since(session, day.start(last))
    if answered:
        settings.speaking_ignored = 0
    elif last is not None and last < day.today:
        # Saved only together with a new reminder, so idle ticks never count it twice.
        settings.speaking_ignored += 1

    if not should_send(settings, now, day, _recorded_since(session, day.start(day.today))):
        if answered:
            session.commit()
        else:
            session.rollback()
        return None

    text = today_prompt(session, generate_topic, now, follow_up=last == day.today)
    settings.speaking_reminder_on = day.today
    settings.speaking_next_reminder_at = as_utc(now) + timedelta(
        minutes=rng.randint(*FOLLOW_UP_MINUTES)
    )
    session.commit()
    return text
