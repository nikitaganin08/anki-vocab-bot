from __future__ import annotations

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.telegram_webapp_auth import parse_and_validate_init_data
from app.main import app
from .telegram_webapp_test_helpers import build_telegram_init_data

BOT_TOKEN = "telegram-bot-token"
ALLOWED_USER_ID = 42


def test_parse_and_validate_init_data_accepts_allowed_user() -> None:
    init_data = build_telegram_init_data(
        bot_token=BOT_TOKEN,
        user_id=ALLOWED_USER_ID,
        auth_date=1_700_000_000,
        query_id="AAEAAAE",
    )

    user = parse_and_validate_init_data(
        init_data,
        bot_token=BOT_TOKEN,
        allowed_user_id=ALLOWED_USER_ID,
        now=1_700_000_100,
    )

    assert user.id == ALLOWED_USER_ID


def test_parse_and_validate_init_data_rejects_bad_signature() -> None:
    init_data = build_telegram_init_data(
        bot_token=BOT_TOKEN,
        user_id=ALLOWED_USER_ID,
        auth_date=1_700_000_000,
    ).replace("hash=", "hash=broken")

    try:
        parse_and_validate_init_data(
            init_data,
            bot_token=BOT_TOKEN,
            allowed_user_id=ALLOWED_USER_ID,
            now=1_700_000_100,
        )
    except HTTPException as exc:
        assert exc.status_code == 403
        assert exc.detail == "Invalid Telegram init data signature"
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected invalid signature to be rejected")


def test_parse_and_validate_init_data_rejects_stale_auth() -> None:
    init_data = build_telegram_init_data(
        bot_token=BOT_TOKEN,
        user_id=ALLOWED_USER_ID,
        auth_date=1_700_000_000,
    )

    try:
        parse_and_validate_init_data(
            init_data,
            bot_token=BOT_TOKEN,
            allowed_user_id=ALLOWED_USER_ID,
            now=1_700_003_700,
        )
    except HTTPException as exc:
        assert exc.status_code == 403
        assert exc.detail == "Telegram init data is stale"
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected stale auth data to be rejected")


def test_parse_and_validate_init_data_rejects_wrong_user() -> None:
    init_data = build_telegram_init_data(
        bot_token=BOT_TOKEN,
        user_id=7,
        auth_date=1_700_000_000,
    )

    try:
        parse_and_validate_init_data(
            init_data,
            bot_token=BOT_TOKEN,
            allowed_user_id=ALLOWED_USER_ID,
            now=1_700_000_100,
        )
    except HTTPException as exc:
        assert exc.status_code == 403
        assert exc.detail == "Telegram user is not allowed"
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected wrong Telegram user to be rejected")


def test_cards_api_requires_telegram_init_data() -> None:
    with TestClient(app) as client:
        response = client.get("/api/cards")

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing Telegram init data"}
