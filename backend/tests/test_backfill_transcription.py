from __future__ import annotations

import argparse
import json

import httpx
import pytest
from sqlalchemy.orm import Session

from app.clients.openrouter import OpenRouterClient, OpenRouterError
from app.models.card import Card
from app.scripts.backfill_transcription import _positive_int, backfill_transcription
from app.services.transcription_prompt import SYSTEM_PROMPT

from .conftest import make_card

OTHER_COLUMNS = [
    c.name for c in Card.__table__.columns if c.name not in {"transcription", "updated_at"}
]


class StubClient:
    def __init__(self, ipa: dict[str, str], *, fail_batches: set[int] | None = None) -> None:
        self.ipa = ipa
        self.fail_batches = fail_batches or set()
        self.batches: list[list[tuple[int, str]]] = []

    def generate_transcriptions(self, items: list[tuple[int, str]]) -> dict[int, str]:
        self.batches.append(items)
        if len(self.batches) in self.fail_batches:
            raise OpenRouterError("boom", code="openrouter_timeout", user_message="timeout")
        return {i: self.ipa[t] for i, t in items if t in self.ipa}


def _add(session: Session, word: str, **overrides: object) -> Card:
    card = make_card(
        source_text=word,
        canonical_text=word,
        canonical_text_normalized=word,
        **overrides,
    )
    session.add(card)
    session.commit()
    return card


def _snapshot(card: Card) -> dict[str, object]:
    return {name: getattr(card, name) for name in OTHER_COLUMNS}


def _run(session: Session, client: StubClient, **kwargs: object) -> tuple[int, int, int]:
    return backfill_transcription(session, client, **kwargs)  # type: ignore[arg-type]


def test_updates_only_transcription(session: Session) -> None:
    card = _add(session, "take off", transcription="/teɪk ɒf/")
    before = _snapshot(card)

    result = _run(session, StubClient({"take off": "/ˈteɪk ˈɔf/"}))

    session.expire_all()
    assert result == (1, 0, 0)
    assert card.transcription == "/ˈteɪk ˈɔf/"
    assert _snapshot(card) == before


def test_unchanged_and_missing_items_are_counted(session: Session) -> None:
    same = _add(session, "give up", transcription="/ɡɪv ˈʌp/")
    skipped = _add(session, "hot", transcription="/hɒt/")

    result = _run(session, StubClient({"give up": "/ɡɪv ˈʌp/"}))  # no answer for "hot"

    session.expire_all()
    assert result == (0, 1, 1)
    assert same.transcription == "/ɡɪv ˈʌp/"
    assert skipped.transcription == "/hɒt/"


def test_batches_commit_each_and_failed_batch_is_left_untouched(session: Session) -> None:
    words = ["one", "two", "three", "four", "five"]
    cards = [_add(session, w, transcription="/old/") for w in words]
    client = StubClient({w: f"/{w}x/" for w in words}, fail_batches={2})
    commits = 0
    original_commit = session.commit

    def counting_commit() -> None:
        nonlocal commits
        commits += 1
        original_commit()

    session.commit = counting_commit  # type: ignore[method-assign]

    result = _run(session, client, batch_size=2)

    session.expire_all()
    assert [[w for _, w in b] for b in client.batches] == [
        ["one", "two"],
        ["three", "four"],
        ["five"],
    ]
    assert result == (3, 0, 2)
    assert commits == 2  # the failed batch is rolled back, not committed
    assert [c.transcription for c in cards] == ["/onex/", "/twox/", "/old/", "/old/", "/fivex/"]


def test_dry_run_writes_nothing_and_previews_30(
    session: Session, capsys: pytest.CaptureFixture[str]
) -> None:
    words = [f"w{i:02d}" for i in range(35)]
    cards = [_add(session, w, transcription="/old/") for w in words]

    result = _run(session, StubClient({w: f"/{w}x/" for w in words}), dry_run=True)

    session.expire_all()
    out = capsys.readouterr().out
    assert result == (35, 0, 0)
    assert all(c.transcription == "/old/" for c in cards)
    assert out.count(" -> ") == 30
    assert "w00: /old/ -> /w00x/" in out
    assert "w34:" not in out


def test_limit_is_respected_in_id_order(session: Session) -> None:
    cards = [_add(session, w, transcription="/old/") for w in ["a", "b", "c"]]
    client = StubClient({"a": "/ax/", "b": "/bx/", "c": "/cx/"})

    result = _run(session, client, limit=2)

    session.expire_all()
    assert result == (2, 0, 0)
    assert [c.transcription for c in cards] == ["/ax/", "/bx/", "/old/"]


def test_rerun_is_idempotent(session: Session) -> None:
    _add(session, "take off", transcription="/teɪk ɒf/")
    client = StubClient({"take off": "/ˈteɪk ˈɔf/"})

    assert _run(session, client) == (1, 0, 0)
    assert _run(session, client) == (0, 1, 0)


def _client(handler: httpx.MockTransport | None = None, **kwargs: object) -> OpenRouterClient:
    return OpenRouterClient(
        api_key="secret",
        model="test-model",
        http_client=httpx.Client(transport=handler),  # type: ignore[arg-type]
    )


def _completion(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def test_generate_transcriptions_sends_ids_and_words_and_filters_result() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.update(body)
        items = [
            {"id": 3, "transcription": "/ˈhɔːnt/"},
            {"id": 4, "transcription": "/ˈɔf/"},
            {"id": 9, "transcription": "/ˈfɔrɛɪn/"},  # not requested
        ]
        return _completion(json.dumps({"items": items}))

    client = _client(httpx.MockTransport(handler))

    result = client.generate_transcriptions([(3, "haunt"), (4, "take off")])

    assert result == {3: "/ˈhɔːnt/", 4: "/ˈɔf/"}
    assert seen["response_format"] == {"type": "json_object"}
    system, user = seen["messages"]  # type: ignore[misc]
    assert system["content"] == SYSTEM_PROMPT
    assert '"id": 3, "text": "haunt"' in user["content"]
    assert '"id": 4, "text": "take off"' in user["content"]


def test_generate_transcriptions_retries_once_on_contract_error() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return _completion(json.dumps({"oops": []}))
        return _completion(json.dumps({"items": [{"id": 1, "transcription": "/ɑn/"}]}))

    client = _client(httpx.MockTransport(handler))

    assert client.generate_transcriptions([(1, "on")]) == {1: "/ɑn/"}
    assert calls == 2


def test_generate_transcriptions_raises_after_second_contract_error() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _completion("not json")

    client = _client(httpx.MockTransport(handler))

    with pytest.raises(OpenRouterError) as exc_info:
        client.generate_transcriptions([(1, "on")])

    assert exc_info.value.code == "openrouter_invalid_contract"
    assert calls == 2


def test_cli_rejects_non_positive_numbers() -> None:
    assert _positive_int("5") == 5
    for bad in ("0", "-1"):
        with pytest.raises(argparse.ArgumentTypeError):
            _positive_int(bad)
