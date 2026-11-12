"""LLM prompts for speaking practice: today's topic (text model) and feedback (audio model)."""

from __future__ import annotations

import base64
from typing import Any

from app.schemas.speaking import ISSUE_CATEGORIES

TOPIC_PROMPT = """You write a short daily speaking task for an adult English learner (B1-B2,
first language Russian) who records a 1-3 minute voice message.
Respond with a single JSON object only: {"topic": "...", "questions": ["...", "..."]}.
- topic: a few plain words about everyday life, work, plans, memories or opinions, e.g.
  "a place you'd like to go back to". No exam-style or abstract philosophical topics.
- questions: 2 or 3 short open questions that lead from easy to a bit deeper.
- When words are given, choose a topic where they fit naturally; do not mention the words.
- When it is a story day, the topic asks for a personal story and the questions guide its
  beginning, middle and end.
- Do not add other fields."""


def build_speaking_topic_messages(words: list[str], story_day: bool) -> list[dict[str, Any]]:
    lines = [f"words: {', '.join(words) if words else 'none'}"]
    lines.append(f"story day: {'yes' if story_day else 'no'}")
    return [
        {"role": "system", "content": TOPIC_PROMPT},
        {"role": "user", "content": "\n".join(lines)},
    ]


FEEDBACK_PROMPT = f"""You are a friendly, precise English speaking coach. The learner (first
language Russian, B1-B2) recorded a voice message answering a speaking task. Listen to it.
Respond with a single JSON object only:
{{"ok": true, "transcript": "...", "words_used": [{{"word": "...", "used": true}}],
"fixes": [{{"wrong": "..." | null, "right": "..." | null, "why": "...", "category": "..."}}],
"natural_version": "..." | null, "next_time": "...",
"focus_check": "better" | "same" | "worse" | null}}
- transcript: verbatim, exactly as spoken, keeping fillers (um, uh, er) and repetitions.
- words_used: one item per given word, in the given order; used is true when the learner said
  it in any inflected form. [] when no words are given.
- fixes: only real mistakes, at most 4, the most useful first; never praise. wrong is the exact
  fragment as spoken, right is the corrected fragment, why is a few words in English (up to 8).
  For "grammatical but not how people say it", give the natural wording as right. Only when the
  problem has no fragment to point at, wrong and right are both null.
  category is one of: {", ".join(ISSUE_CATEGORIES)} (verb_pattern: gerund vs infinitive and
  verb + preposition patterns).
- natural_version: 1-3 sentences rewriting the weakest part the way a native speaker would say
  it, not the whole answer; null when there is nothing to improve.
- next_time: exactly one concrete thing to work on in the next recording, under 150 characters.
  Pick the most useful one. Instead of "stop saying um", suggest a thinking phrase such as
  "let me think" or "the thing is".
- focus_check: whether the learner followed last time's focus: better, same or worse; null when
  there is no last focus or the recording gives no chance to tell.
- If there is no English speech in the recording (silence, noise, another language), respond
  {{"ok": false, "message_for_user": "..."}} with one short English sentence.
- Do not add other fields."""


def build_speaking_feedback_messages(
    *,
    audio: bytes,
    audio_format: str,
    prompt_text: str | None,
    words: list[str],
    last_focus: str | None,
) -> list[dict[str, Any]]:
    context = [
        f"task: {prompt_text}" if prompt_text else "task: free speech, no task was given",
        f"words: {', '.join(words) if words else 'none'}",
        f"last focus: {last_focus or 'none'}",
    ]
    return [
        {"role": "system", "content": FEEDBACK_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "\n".join(context)},
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": base64.b64encode(audio).decode(),
                        "format": audio_format,
                    },
                },
            ],
        },
    ]
