from __future__ import annotations

import logging
from typing import Any

import httpx

from app.bot.formatter import format_card_service_result, format_rare_word_prompt
from app.bot.handler import build_learn_keyboard
from app.core.config import get_settings
from app.services.card_service import CardServiceResult

logger = logging.getLogger(__name__)


def send_card_result(result: CardServiceResult) -> None:
    """Sends the same messages the bot replies with, for a word added outside the chat."""
    settings = get_settings()
    if not settings.telegram_bot_token or settings.telegram_allowed_user_id is None:
        return
    text, parse_mode = format_card_service_result(result)
    _send(settings.telegram_bot_token, settings.telegram_allowed_user_id, text, parse_mode)
    card = result.card
    if card is not None and not card.is_learning:
        keyboard = build_learn_keyboard(card.id, card.common_synonym)
        _send(
            settings.telegram_bot_token,
            settings.telegram_allowed_user_id,
            format_rare_word_prompt(card),
            None,
            keyboard.model_dump(exclude_none=True),
        )


def _send(
    token: str,
    chat_id: int,
    text: str,
    parse_mode: str | None,
    reply_markup: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage", json=payload, timeout=10
        ).raise_for_status()
    except httpx.HTTPError as exc:
        # The card is already saved; a missing Telegram message must not fail the request.
        logger.warning("Telegram message failed: %s", exc)
