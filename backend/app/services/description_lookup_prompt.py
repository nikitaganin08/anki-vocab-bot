from __future__ import annotations

SYSTEM_PROMPT = """You map a short free-form description or clue to a single English lexical unit.
Respond with a single JSON object only.
Do not include markdown, prose, code fences, or commentary.

Found contract:
{
  "found": true,
  "source_text": "..."
}

Rejected contract:
{
  "found": false,
  "message_for_user": "..."
}

Rules:
- source_text must be a single English word or stable English lexical unit.
- source_text must contain 1 to 8 tokens.
- For verbs and phrasal verbs, return the lemma-like form without the infinitive marker "to ".
- Prefer the most likely lexical unit that matches the description.
- If the description is ambiguous, too broad, or not enough to infer one lexical unit,
  return found=false.
- message_for_user must be brief, clear, and user-facing."""


def build_description_lookup_messages(description: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Infer the most likely English lexical unit from this description "
                "and return exactly one JSON object.\n"
                f"description: {description}"
            ),
        },
    ]
