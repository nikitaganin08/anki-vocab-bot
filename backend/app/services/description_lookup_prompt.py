from __future__ import annotations

SYSTEM_PROMPT = """You map a short free-form description or clue to likely English lexical units.
Respond with a single JSON object only.
Do not include markdown, prose, code fences, or commentary.

Found contract:
{
  "found": true,
  "candidates": ["...", "...", "..."]
}

Rejected contract:
{
  "found": false,
  "message_for_user": "..."
}

Rules:
- candidates must contain 3 to 5 items.
- each candidate must be a single English word, collocation, or phrasal verb.
- each candidate must contain 1 to 8 tokens.
- Do not return a definition, explanation, or translation gloss instead of the lexical unit itself.
- Prefer established lexical units over literal paraphrases.
- For verbs and phrasal verbs, return the lemma-like form without the infinitive marker "to ".
- Order candidates from most likely to less likely.
- If the description is too vague or you cannot infer at least 3 plausible lexical units,
  return found=false.
- message_for_user must be brief, clear, and user-facing."""


def build_description_lookup_messages(description: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Infer 3 to 5 likely English lexical units from this description "
                "without returning explanations or translation glosses, "
                "and return exactly one JSON object.\n"
                f"description: {description}"
            ),
        },
    ]
