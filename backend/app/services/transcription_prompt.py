from __future__ import annotations

import json

# Shared by the card prompt (llm_prompt.py) and the one-off backfill below.
IPA_RULES = """- Write the pronunciation as General American (US) IPA, always wrapped in slashes
  like /ˈhɔːnt/; never use square brackets or parentheses (write optional sounds out in
  full) and never put syllable dots in it.
- Include primary (ˈ) and secondary (ˌ) stress marks.
- Use US vowels: ɑ for the LOT and PALM vowels, oʊ (not əʊ), and r-coloured vowels
  (ɝ or ɜːr, ɚ or ər, ɔːr, ɪr, ɛr, ʊr); never the British non-rhotic forms
  ɒ, əʊ, ɪə, eə, ʊə.
- For a multi-word unit transcribe each word and join the words with single spaces
  inside one pair of slashes."""

SYSTEM_PROMPT = f"""You transcribe English words and expressions into IPA.
Respond with a single JSON object only.
Do not include markdown, prose, code fences, or commentary.

Contract:
{{"items": [{{"id": 1, "transcription": "/.../"}}]}}

Rules:
- Return exactly one item per requested id, in any order, using the id you were given.
- transcription is the pronunciation of the given English text, never of a translation.
{IPA_RULES}"""


def build_transcription_messages(items: list[tuple[int, str]]) -> list[dict[str, str]]:
    requested = json.dumps(
        [{"id": item_id, "text": text} for item_id, text in items], ensure_ascii=False
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Transcribe each text and return exactly one JSON object "
                f"using the contract above.\nitems: {requested}"
            ),
        },
    ]
