from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from time import time
from urllib.parse import parse_qsl

from fastapi import HTTPException, status

AUTH_MAX_AGE_SECONDS = 3600


@dataclass(frozen=True, slots=True)
class TelegramWebAppUser:
    id: int


def _build_data_check_string(init_data: str) -> tuple[str, str]:
    items = dict(parse_qsl(init_data, strict_parsing=True))
    received_hash = items.pop("hash", None)
    if not received_hash:
        raise ValueError("Missing hash")

    data_check_string = "\n".join(
        f"{key}={value}"
        for key, value in sorted(items.items())
    )
    return data_check_string, received_hash


def _build_hash(data_check_string: str, bot_token: str) -> str:
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    return hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def parse_and_validate_init_data(
    init_data: str,
    *,
    bot_token: str,
    allowed_user_id: int,
    now: int | None = None,
) -> TelegramWebAppUser:
    try:
        data_check_string, received_hash = _build_data_check_string(init_data)
        parsed_data = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Telegram init data",
        ) from exc

    expected_hash = _build_hash(data_check_string, bot_token)
    if not hmac.compare_digest(received_hash, expected_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Telegram init data signature",
        )

    auth_date_raw = parsed_data.get("auth_date")
    if auth_date_raw is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Telegram init data",
        )

    try:
        auth_date = int(auth_date_raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Telegram init data",
        ) from exc

    current_timestamp = now if now is not None else int(time())
    if current_timestamp - auth_date > AUTH_MAX_AGE_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Telegram init data is stale",
        )

    user_raw = parsed_data.get("user")
    if user_raw is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Telegram init data",
        )

    try:
        user_payload = json.loads(user_raw)
        user_id = int(user_payload["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Telegram init data",
        ) from exc

    if user_id != allowed_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Telegram user is not allowed",
        )

    return TelegramWebAppUser(id=user_id)
