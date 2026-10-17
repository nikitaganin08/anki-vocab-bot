from __future__ import annotations

SYSTEM_PROMPT = """You add usage chunks and one example to a saved English vocabulary card.
Respond with a single JSON object only.
Do not include markdown, prose, code fences, or commentary.

Contract:
{
  "chunks": [
    {
      "text": "...",
      "target": "...",
      "translation": "..."
    }
  ],
  "example": "..."
}

Rules:
- Use the Russian translations and current examples to keep the same meaning of canonical_text.
- chunks must contain 0 to 5 frequent natural usages of canonical_text in that meaning
  (collocation, typical object or complement, fixed frame), most frequent first.
- Each chunk text must be 2 to 6 English words.
- Each chunk target must be the exact contiguous substring of its text that realises
  canonical_text; it may be inflected (e.g. text "gave up on him", target "gave up").
- Each chunk translation must be the Russian translation of the whole chunk text.
- Return "chunks": [] when canonical_text has no frequent chunks (rare or technical words).
- example must be one English sentence that illustrates the meaning of canonical_text
  and explicitly includes canonical_text or its inflected form; prefer the best current example.
"""


def build_chunks_messages(
    canonical_text: str,
    translation_variants: list[str],
    examples: list[str],
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Add usage chunks and the best single example for this saved card and "
                "return exactly one JSON object.\n"
                f"canonical_text: {canonical_text}\n"
                f"translation_variants: {', '.join(translation_variants)}\n"
                f"examples: {' | '.join(examples)}"
            ),
        },
    ]
