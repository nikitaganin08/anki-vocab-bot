from __future__ import annotations

import hashlib
import hmac
import json
from time import time
from urllib.parse import urlencode


def build_telegram_init_data(
    *,
    bot_token: str,
    user_id: int,
    auth_date: int | None = None,
    **extra: str,
) -> str:
    normalized_auth_date = auth_date if auth_date is not None else int(time())
    payload = {
        "auth_date": str(normalized_auth_date),
        "user": json.dumps(
            {
                "id": user_id,
                "first_name": "Test",
            },
            separators=(",", ":"),
        ),
        **extra,
    }
    data_check_string = "\n".join(
        f"{key}={value}"
        for key, value in sorted(payload.items())
    )
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    payload["hash"] = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return urlencode(payload)
