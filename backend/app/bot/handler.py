from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.bot.formatter import (
    format_created_message,
    format_duplicate_message,
    format_rate_limit_message,
)
from app.bot.input_validation import validate_source_input
from app.bot.rate_limiter import InMemoryRateLimiter
from app.services.card_service import CardServiceResult, CardServiceUpstreamError


@dataclass(slots=True)
class TelegramTextHandler:
    allowed_user_id: int
    apply_source_text: Callable[[str], CardServiceResult]
    rate_limiter: InMemoryRateLimiter

    async def handle_message(self, message: Any) -> None:
        user_id = self._extract_user_id(message)
        if user_id is None or user_id != self.allowed_user_id:
            return

        if self._is_command_text(getattr(message, "text", None)):
            return

        if not self.rate_limiter.allow_request(user_id):
            await message.answer(format_rate_limit_message())
            return

        validation = validate_source_input(message.text or "")
        if not validation.ok or validation.normalized_text is None:
            await message.answer(validation.error_message or "Invalid input.")
            return

        try:
            result = await asyncio.to_thread(self.apply_source_text, validation.normalized_text)
        except CardServiceUpstreamError as exc:
            await message.answer(exc.user_message)
            return

        await self._reply_from_result(message, result)

    @staticmethod
    def _is_command_text(text: str | None) -> bool:
        if text is None:
            return False
        return text.lstrip().startswith("/")

    @staticmethod
    def _extract_user_id(message: Any) -> int | None:
        from_user = getattr(message, "from_user", None)
        if from_user is None:
            return None
        return getattr(from_user, "id", None)

    @staticmethod
    async def _reply_from_result(message: Any, result: CardServiceResult) -> None:
        if result.status == "rejected" and result.rejection is not None:
            await message.answer(result.rejection.message_for_user)
            return

        if result.card is None:
            await message.answer("Unexpected bot response state.")
            return

        if result.status == "created":
            await message.answer(format_created_message(result.card), parse_mode="HTML")
            return

        if result.status in {"duplicate_source", "duplicate_canonical"}:
            await message.answer(format_duplicate_message(result.card), parse_mode="HTML")
            return

        await message.answer("Unexpected bot response state.")


@dataclass(slots=True)
class TelegramAdminWebAppHandler:
    allowed_user_id: int
    webapp_url: str

    async def handle_message(self, message: Any) -> None:
        user_id = TelegramTextHandler._extract_user_id(message)
        if user_id is None or user_id != self.allowed_user_id:
            return

        await message.answer(
            "Open the dictionary panel inside Telegram.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Open admin panel",
                            web_app=WebAppInfo(url=self.webapp_url),
                        )
                    ]
                ]
            ),
        )
