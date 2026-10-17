from __future__ import annotations

import json

import pytest

from app.schemas.transcription import parse_transcriptions_response


def _payload(*items: dict[str, object]) -> str:
    return json.dumps({"items": list(items)}, ensure_ascii=False)


def test_parser_returns_valid_items_stripped() -> None:
    result = parse_transcriptions_response(
        _payload(
            {"id": 1, "transcription": " /ˈhɔːnt/ "},
            {"id": 2, "transcription": "/ˈteɪk ˈɔf/"},
        ),
        {1, 2},
    )

    assert result == {1: "/ˈhɔːnt/", 2: "/ˈteɪk ˈɔf/"}


@pytest.mark.parametrize(
    "bad",
    [
        "[ˈhɔːnt]",  # square brackets, no slashes
        "/ˈhɔːnt]/",  # bracket inside
        "/(ə)ˈhɔːnt/",  # parentheses
        "ˈhɔːnt",  # bare
        "/ˈhɔːnt",  # one slash
        "/хɔːnt/",  # Cyrillic
        "/ˈhɔːnt2/",  # digit
        "//",  # too short
        "/" + "a" * 119 + "/",  # too long
    ],
)
def test_parser_drops_invalid_transcriptions(bad: str) -> None:
    result = parse_transcriptions_response(
        _payload({"id": 1, "transcription": bad}, {"id": 2, "transcription": "/ˈɔf/"}), {1, 2}
    )

    assert result == {2: "/ˈɔf/"}


def test_parser_drops_foreign_ids_and_malformed_items() -> None:
    result = parse_transcriptions_response(
        _payload(
            {"id": 99, "transcription": "/ˈɔf/"},
            {"id": "x", "transcription": "/ˈɔf/"},
            {"id": 1},
            {"id": 1, "transcription": 5},
            "junk",
            {"id": 1, "transcription": "/ˈfɝst/"},
            {"id": 1, "transcription": "/ˈsɛkənd/"},
        ),
        {1},
    )

    assert result == {1: "/ˈfɝst/"}  # first valid item wins


def test_parser_accepts_any_id_without_allowed_ids() -> None:
    assert parse_transcriptions_response({"items": [{"id": 7, "transcription": "/ɑn/"}]}) == {
        7: "/ɑn/"
    }


@pytest.mark.parametrize("payload", ["not json", "[]", '{"items": "x"}', '{"data": []}'])
def test_parser_rejects_broken_payload(payload: str) -> None:
    with pytest.raises(ValueError):
        parse_transcriptions_response(payload)
