from __future__ import annotations

from dataclasses import dataclass

import httpx


class TelegramSendError(RuntimeError):
    pass


@dataclass(slots=True)
class TelegramBotSender:
    bot_token: str
    chat_id: int
    timeout_seconds: float = 10.0
    base_url: str = "https://api.telegram.org"

    def send_message(self, text: str, parse_mode: str | None = None) -> None:
        payload: dict[str, object] = {
            "chat_id": self.chat_id,
            "text": text,
        }
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode

        url = f"{self.base_url}/bot{self.bot_token}/sendMessage"
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise TelegramSendError("Telegram sendMessage request failed") from exc

        if not isinstance(body, dict) or body.get("ok") is not True:
            raise TelegramSendError("Telegram sendMessage returned a non-ok response")
