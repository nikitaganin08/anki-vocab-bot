from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.bot.formatter import (
    format_card_service_result,
    format_description_lookup_candidates,
    format_rare_word_prompt,
    format_rate_limit_message,
)
from app.bot.input_validation import validate_description_input, validate_source_input
from app.bot.rate_limiter import InMemoryRateLimiter
from app.clients.openrouter import OpenRouterError
from app.models.card import Card
from app.schemas.description_lookup import DescriptionLookupResponse, FoundDescriptionLookupResponse
from app.services.card_service import CardServiceResult


def build_learn_keyboard(card_id: int, synonym: str | None = None) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="Learn", callback_data=f"learn:{card_id}"),
            InlineKeyboardButton(text="Skip", callback_data=f"skip:{card_id}"),
        ]
    ]
    if synonym:
        rows.append([InlineKeyboardButton(text=f"Use “{synonym}”", callback_data=f"alt:{card_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _web_app_keyboard(text: str, url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, web_app=WebAppInfo(url=url))]]
    )


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

        if not self.rate_limiter.allow_request():
            await message.answer(format_rate_limit_message())
            return

        validation = validate_source_input(message.text or "")
        if validation.normalized_text is None:
            await message.answer(validation.error_message)
            return

        try:
            result = await asyncio.to_thread(self.apply_source_text, validation.normalized_text)
        except OpenRouterError as exc:
            await message.answer(exc.user_message)
            return

        text, parse_mode = format_card_service_result(result)
        await message.answer(text, parse_mode=parse_mode)
        if result.card is not None and not result.card.is_learning:
            await message.answer(
                format_rare_word_prompt(result.card),
                reply_markup=build_learn_keyboard(result.card.id, result.card.common_synonym),
            )

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


@dataclass
class TelegramDescriptionLookupHandler:
    allowed_user_id: int
    lookup_candidates_from_description: Callable[[str], DescriptionLookupResponse]
    rate_limiter: InMemoryRateLimiter

    async def handle_message(self, message: Any) -> None:
        user_id = TelegramTextHandler._extract_user_id(message)
        if user_id is None or user_id != self.allowed_user_id:
            return

        if not self.rate_limiter.allow_request():
            await message.answer(format_rate_limit_message())
            return

        description = self._extract_description_argument(getattr(message, "text", None))
        validation = validate_description_input(description)
        if validation.normalized_text is None:
            await message.answer(validation.error_message)
            return

        try:
            lookup_result = await asyncio.to_thread(
                self.lookup_candidates_from_description,
                validation.normalized_text,
            )
        except OpenRouterError as exc:
            await message.answer(exc.user_message)
            return

        if not isinstance(lookup_result, FoundDescriptionLookupResponse):
            await message.answer(lookup_result.message_for_user)
            return

        await message.answer(format_description_lookup_candidates(lookup_result.candidates))

    @staticmethod
    def _extract_description_argument(text: str | None) -> str:
        if text is None:
            return ""

        normalized = text.strip()
        if not normalized:
            return ""

        _, _, argument = normalized.partition(" ")
        return argument


@dataclass(slots=True)
class TelegramAdminWebAppHandler:
    allowed_user_id: int
    webapp_url: str

    async def handle_message(self, message: Any) -> None:
        user_id = TelegramTextHandler._extract_user_id(message)
        if user_id is None or user_id != self.allowed_user_id:
            return

        await message.answer(
            "Dictionary, stats and settings.",
            reply_markup=_web_app_keyboard("Open Wordloop", self.webapp_url),
        )


@dataclass(slots=True)
class TelegramReviewWebAppHandler:
    allowed_user_id: int
    webapp_url: str

    async def handle_message(self, message: Any) -> None:
        if TelegramTextHandler._extract_user_id(message) != self.allowed_user_id:
            return

        await message.answer(
            "Review",
            reply_markup=_web_app_keyboard("Review words", f"{self.webapp_url}?view=review"),
        )


@dataclass(slots=True)
class SynonymSwap:
    old: str
    result: CardServiceResult | None


@dataclass(slots=True)
class TelegramLearnCallbackHandler:
    allowed_user_id: int
    set_learning: Callable[[int, bool], Card | None]
    swap_for_synonym: Callable[[int], SynonymSwap | None] | None = None

    async def handle_callback(self, callback: Any) -> None:
        if TelegramTextHandler._extract_user_id(callback) != self.allowed_user_id:
            return

        action, _, raw_card_id = callback.data.partition(":")
        if action == "alt":
            await self._swap(callback, int(raw_card_id))
            return
        is_learning = action == "learn"
        card = await asyncio.to_thread(self.set_learning, int(raw_card_id), is_learning)
        if card is None:
            text = "Card not found"
        else:
            text = f"{'Learning' if is_learning else 'Not learning'}: {card.canonical_text}"
        await callback.message.edit_text(text)
        await callback.answer()

    async def _swap(self, callback: Any, card_id: int) -> None:
        try:
            swap = (
                await asyncio.to_thread(self.swap_for_synonym, card_id)
                if self.swap_for_synonym
                else None
            )
        except OpenRouterError as exc:
            await callback.answer(exc.user_message, show_alert=True)
            return
        if swap is None:
            text = "Card not found"
        elif swap.result is None or swap.result.card is None:
            text = f"Could not add the synonym. Kept “{swap.old}” as not learning."
        else:
            word = swap.result.card.canonical_text
            text = f"Learning “{word}”. “{swap.old}” stays in your dictionary as not learning."
            card_text, parse_mode = format_card_service_result(swap.result)
            await callback.message.answer(card_text, parse_mode=parse_mode)
        await callback.message.edit_text(text)
        await callback.answer()
