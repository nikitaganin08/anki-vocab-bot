from __future__ import annotations

import pytest

from app.schemas.description_lookup import (
    FoundDescriptionLookupResponse,
    RejectedDescriptionLookupResponse,
    parse_description_lookup_response,
)


def test_parse_description_lookup_response_accepts_found_payload() -> None:
    result = parse_description_lookup_response(
        {"found": True, "source_text": "shovel away"}
    )

    assert isinstance(result, FoundDescriptionLookupResponse)
    assert result.source_text == "shovel away"


def test_parse_description_lookup_response_accepts_rejected_payload() -> None:
    result = parse_description_lookup_response(
        {
            "found": False,
            "message_for_user": "I could not infer one clear lexical unit from that description.",
        }
    )

    assert isinstance(result, RejectedDescriptionLookupResponse)
    assert result.message_for_user.startswith("I could not infer")


def test_parse_description_lookup_response_rejects_cyrillic_source_text() -> None:
    with pytest.raises(ValueError):
        parse_description_lookup_response({"found": True, "source_text": "разгребать"})


def test_parse_description_lookup_response_rejects_more_than_eight_tokens() -> None:
    with pytest.raises(ValueError):
        parse_description_lookup_response(
            {
                "found": True,
                "source_text": (
                    "one two three four five six seven eight nine"
                ),
            }
        )
