from __future__ import annotations

SYSTEM_PROMPT = """You identify established English word-family forms for a saved vocabulary card.
Respond with a single JSON object only.
Do not include markdown, prose, code fences, or commentary.

Contract:
{
  "word_family": [
    {
      "word": "...",
      "part_of_speech": "...",
      "translation": "..."
    }
  ]
}

Rules:
- Return 0 to 3 established English derivational forms related to canonical_text.
- Use the explanation and Russian translations to keep the forms relevant to this sense.
- Do not include canonical_text itself, ordinary tense/plural forms, invented forms,
  or weakly related words.
- Each item must contain an English word, an English part of speech, and a Russian translation.
- Return an empty list when there are no useful established forms.
"""


def build_word_family_messages(
    canonical_text: str,
    *,
    explanation: str,
    translation_variants: list[str],
) -> list[dict[str, str]]:
    translations = ", ".join(translation_variants)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Find the established English word-family forms for this saved card and "
                "return exactly one JSON object.\n"
                f"canonical_text: {canonical_text}\n"
                f"translation_variants: {translations}\n"
                f"explanation: {explanation}"
            ),
        },
    ]
