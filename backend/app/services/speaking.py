"""Speaking practice: a daily topic with deck words, feedback on voice messages and video notes.

The recording itself is never stored: the bytes go to the audio model and are dropped. What the
model found is kept in `speaking_sessions` / `speaking_issues` for later analysis.
"""

from __future__ import annotations

import json
import random
import re
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
from app.schemas.speaking import SpeakingFix, SpeakingRejected, SpeakingResult, SpeakingTopic
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
SHOWN_FIXES = 3  # the rest of the fixes go into a collapsed quote

# Hesitation sounds of any length ("ummm", "m-m-m", "эээ"); "uh-huh" (yes) is not one.
FILLER_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (name, re.compile(pattern))
    for name, pattern in (
        ("um", r"u+h*m+|э+м+"),
        ("uh", r"u+h+|э+"),
        ("erm", r"e+r+m+"),
        ("er", r"e+r+"),
        ("hmm", r"h+m+|х+м+"),
        ("mm", r"m{2,}|м{2,}"),
    )
)


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


def _filler(word: str) -> str | None:
    return next((name for name, pattern in FILLER_PATTERNS if pattern.fullmatch(word)), None)


def count_fillers(transcript: str) -> Counter[str]:
    words = (
        word.strip(".,!?;:…—-\"'()").replace("-", "").casefold() for word in transcript.split()
    )
    return Counter(name for name in map(_filler, words) if name)


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


def _fix_lines(index: int, fix: SpeakingFix) -> list[str]:
    if fix.wrong is None or fix.right is None:
        return [f"{index}. <i>{escape(fix.why)}</i>"]
    return [
        f"{index}. <s>{escape(fix.wrong)}</s> → <b>{escape(fix.right)}</b>",
        f"    <i>{escape(fix.why)}</i>",
    ]


def format_feedback(
    *,
    duration_seconds: int,
    fillers: Counter[str],
    words: list[dict[str, object]],
    result: SpeakingResult,
    last_focus: str | None = None,
) -> str:
    """Telegram HTML for the chat; the transcript and categories are not shown."""
    if isinstance(result, SpeakingRejected):
        return f"🤔 {escape(result.message_for_user)}"
    lines = [f"✅ <b>Feedback</b> · {_duration(duration_seconds)}", ""]
    if last_focus:
        lines.append(f"🎯 Last focus: <b>{result.focus_check or 'no chance to tell'}</b>")
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
    shown, rest = result.fixes[:SHOWN_FIXES], result.fixes[SHOWN_FIXES:]
    if shown:
        count = f" ({len(shown)} of {len(result.fixes)})" if rest else ""
        lines += ["", f"✏️ <b>{'Top fixes' if rest else 'Fixes'}</b>{count}"]
        for index, fix in enumerate(shown, 1):
            lines += _fix_lines(index, fix)
    if rest:
        more = [f"➕ <b>{len(rest)} more</b>"]
        for index, fix in enumerate(rest, SHOWN_FIXES + 1):
            more += _fix_lines(index, fix)
        lines.append(f"<blockquote expandable>{chr(10).join(more)}</blockquote>")
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
    telegram_message_id: int | None = None,
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
        telegram_message_id=telegram_message_id,
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
        duration_seconds=duration_seconds,
        fillers=fillers,
        words=words,
        result=result,
        last_focus=last_focus,
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


WEEKLY_HOUR = 10  # Monday morning: last week's summary, separate from the daily topic
CATEGORY_LABELS = {
    "article": "Articles",
    "tense": "Tenses",
    "verb_pattern": "Verb patterns",
    "preposition": "Prepositions",
    "collocation": "Collocations",
    "word_choice": "Word choice",
    "word_order": "Word order",
    "agreement": "Agreement",
    "grammar_other": "Other grammar",
}


@dataclass(frozen=True, slots=True)
class WeeklySummary:
    text: str
    forward_message_ids: list[int]  # the week's first and last recordings, to listen back


def _sessions_between(session: Session, start: datetime, end: datetime) -> list[SpeakingSession]:
    query = (
        select(SpeakingSession)
        .where(SpeakingSession.recorded_at >= start, SpeakingSession.recorded_at < end)
        .order_by(SpeakingSession.recorded_at)
    )
    return list(session.scalars(query))


def _filler_rate(rows: list[SpeakingSession]) -> float | None:
    seconds = sum(row.duration_seconds for row in rows)
    return sum(row.filler_count for row in rows) * 60 / seconds if seconds else None


def _week_label(start: date) -> str:
    end = start + timedelta(days=6)
    if start.month == end.month:
        return f"{start:%b} {start.day}–{end.day}"
    return f"{start:%b} {start.day} – {end:%b} {end.day}"


def build_weekly_summary(session: Session, day: LocalDay, week_start: date) -> WeeklySummary | None:
    """Last week's speaking: days, minutes, filler trend, deck words, recurring mistakes."""
    start, end = day.start(week_start), day.start(week_start + timedelta(days=7))
    rows = _sessions_between(session, start, end)
    if not rows:
        return None
    days = {
        (as_utc(row.recorded_at).astimezone(day.tz) - timedelta(hours=DAY_START_HOUR)).date()
        for row in rows
    }
    minutes = max(1, round(sum(row.duration_seconds for row in rows) / 60))
    stats = [f"🗓 {len(days)} of 7 days · {minutes} min spoken"]
    rate = _filler_rate(rows)
    previous = _filler_rate(
        _sessions_between(session, day.start(week_start - timedelta(days=7)), start)
    )
    if rate is not None and previous is not None:
        trend = "📉" if rate < previous else "📈" if rate > previous else ""
        stats.append(f"🗣 Fillers: {previous:.1f} → <b>{rate:.1f}</b>/min {trend}".rstrip())
    elif rate is not None:
        stats.append(f"🗣 Fillers: <b>{rate:.1f}</b>/min")
    words = [word for row in rows for word in json.loads(row.words_json)]
    if words:
        stats.append(f"📚 Deck words used: {sum(bool(w['used']) for w in words)} of {len(words)}")
    lines = [f"📊 <b>Your speaking week</b> · {_week_label(week_start)}"]
    lines.append(f"<blockquote>{chr(10).join(stats)}</blockquote>")

    issues = session.scalars(
        select(SpeakingIssue)
        .where(SpeakingIssue.session_id.in_([row.id for row in rows]))
        .order_by(SpeakingIssue.id)
    ).all()
    counts = Counter(issue.category for issue in issues)
    if counts:
        lines += ["", "🔁 <b>What keeps coming back</b>"]
        for category, count in counts.most_common(3):
            example = next(
                (i for i in issues if i.category == category and i.wrong and i.right), None
            )
            line = f"<b>{CATEGORY_LABELS[category]}</b> ×{count}"
            if example is not None:
                line += (
                    f" · <s>{escape(str(example.wrong))}</s> → <b>{escape(str(example.right))}</b>"
                )
            lines.append(line)

    forward = [row.telegram_message_id for row in (rows[0], rows[-1]) if row.telegram_message_id]
    if len(rows) < 2 or len(forward) < 2:
        forward = []
    else:
        lines += [
            "",
            "🎧 <b>Before today's topic:</b> play your first recording of last week, "
            "then the last one.",
        ]
    if counts:
        focus = CATEGORY_LABELS[counts.most_common(1)[0][0]].lower()
        lines += ["", f"👉 <b>Focus this week:</b> {focus}"]
    return WeeklySummary("\n".join(lines), forward)


def prepare_weekly_summary(session: Session, now: datetime) -> WeeklySummary | None:
    """Monday from WEEKLY_HOUR, once: the summary of the week before (None without recordings)."""
    settings = get_app_settings(session)
    day = local_day(settings, now)
    if (
        not settings.speaking_enabled
        or day.today.weekday() != 0
        or day.now_local.hour < WEEKLY_HOUR
        or settings.speaking_weekly_on == day.today
    ):
        return None
    settings.speaking_weekly_on = day.today
    session.commit()
    return build_weekly_summary(session, day, day.today - timedelta(days=7))
