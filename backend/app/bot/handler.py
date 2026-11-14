from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any

from aiogram.exceptions import TelegramAPIError
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
from app.services.speaking import MAX_SECONDS as SPEAKING_MAX_SECONDS

logger = logging.getLogger(__name__)


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


ADD_PREFIX = "add:"
CALLBACK_DATA_LIMIT = 64  # bytes, a Telegram limit


def build_candidates_keyboard(candidates: list[str]) -> InlineKeyboardMarkup | None:
    """One "Add" button per /find candidate; the word itself travels in the callback data."""
    rows = [
        [InlineKeyboardButton(text=f"Add “{word}”", callback_data=f"{ADD_PREFIX}{word}")]
        for word in candidates
        if len(f"{ADD_PREFIX}{word}".encode()) <= CALLBACK_DATA_LIMIT
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


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

        await message.answer(
            format_description_lookup_candidates(lookup_result.candidates),
            reply_markup=build_candidates_keyboard(lookup_result.candidates),
        )

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


@dataclass(slots=True)
class TelegramAddCallbackHandler:
    """The "Add" buttons under /find: adds the candidate like a message with that word would."""

    allowed_user_id: int
    apply_source_text: Callable[[str], CardServiceResult]
    rate_limiter: InMemoryRateLimiter

    async def handle_callback(self, callback: Any) -> None:
        if TelegramTextHandler._extract_user_id(callback) != self.allowed_user_id:
            return

        if not self.rate_limiter.allow_request():
            await callback.answer(format_rate_limit_message(), show_alert=True)
            return

        validation = validate_source_input(callback.data.removeprefix(ADD_PREFIX))
        if validation.normalized_text is None:
            await callback.answer(validation.error_message, show_alert=True)
            return

        # Acknowledge first: the card takes a few seconds and the button would spin meanwhile.
        await callback.answer("Adding…")
        try:
            result = await asyncio.to_thread(self.apply_source_text, validation.normalized_text)
        except OpenRouterError as exc:
            await callback.message.answer(exc.user_message)
            return

        text, parse_mode = format_card_service_result(result)
        await callback.message.answer(text, parse_mode=parse_mode)
        if result.card is not None and not result.card.is_learning:
            await callback.message.answer(
                format_rare_word_prompt(result.card),
                reply_markup=build_learn_keyboard(result.card.id, result.card.common_synonym),
            )


@dataclass(slots=True)
class TelegramSpeakHandler:
    """`/speak`: today's speaking topic (generated on first request of the day)."""

    allowed_user_id: int
    get_prompt: Callable[[], str]

    async def handle_message(self, message: Any) -> None:
        if TelegramTextHandler._extract_user_id(message) != self.allowed_user_id:
            return
        try:
            text = await asyncio.to_thread(self.get_prompt)
        except OpenRouterError as exc:
            await message.answer(exc.user_message)
            return
        await message.answer(text, parse_mode="HTML")


RECORDING_FORMATS = {"voice": "ogg", "video_note": "mp4"}
RECORDING_FAILED = "Couldn't check this recording. Please try again."
RETRY_SPEAKING = "retry_speaking"
RETRY_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Try again", callback_data=RETRY_SPEAKING)]]
)


def _recording(message: Any) -> tuple[str, Any] | None:
    if getattr(message, "voice", None):
        return "voice", message.voice
    if getattr(message, "video_note", None):
        return "video_note", message.video_note
    return None


@dataclass
class TelegramRecordingHandler:
    """Voice messages and video notes: feedback from the audio model; the file is not kept.

    A failure is a reply to the recording with "Try again": the retry takes the recording
    from that reply, so nothing has to be stored to download it again."""

    allowed_user_id: int
    # (audio bytes, kind, audio format, duration in seconds, message id) -> Telegram HTML reply
    analyse: Callable[[bytes, str, str, int, int], str]
    rate_limiter: InMemoryRateLimiter
    max_seconds: int = SPEAKING_MAX_SECONDS
    pending: set[asyncio.Task[None]] = field(default_factory=set)

    async def handle_message(self, message: Any) -> None:
        if TelegramTextHandler._extract_user_id(message) != self.allowed_user_id:
            return
        kind = "voice" if getattr(message, "voice", None) else "video_note"
        media = message.voice if kind == "voice" else message.video_note
        if media.duration > self.max_seconds:
            await message.answer(
                f"That's longer than {self.max_seconds // 60} minutes. "
                "Please send a shorter recording."
            )
            return
        if not self.rate_limiter.allow_request():
            await message.answer(format_rate_limit_message())
            return
        self._start(message, media, kind)

    async def handle_retry(self, callback: Any) -> None:
        if TelegramTextHandler._extract_user_id(callback) != self.allowed_user_id:
            return
        source = getattr(callback.message, "reply_to_message", None)
        recording = _recording(source) if source else None
        if recording is None:
            await callback.answer("Recording not found. Please send it again.", show_alert=True)
            return
        if not self.rate_limiter.allow_request():
            await callback.answer(format_rate_limit_message(), show_alert=True)
            return
        await callback.answer("Checking again…")
        with suppress(TelegramAPIError):
            await callback.message.delete()
        kind, media = recording
        self._start(source, media, kind)

    def _start(self, message: Any, media: Any, kind: str) -> None:
        # Not awaited: a long recording takes longer than Telegram waits for the webhook reply.
        task = asyncio.create_task(self._analyse_and_reply(message, media, kind))
        self.pending.add(task)
        task.add_done_callback(self.pending.discard)

    async def _analyse_and_reply(self, message: Any, media: Any, kind: str) -> None:
        try:
            await message.bot.send_chat_action(message.chat.id, "typing")
            buffer = await message.bot.download(media)
            text = await asyncio.to_thread(
                self.analyse,
                buffer.getvalue(),
                kind,
                RECORDING_FORMATS[kind],
                media.duration,
                message.message_id,
            )
        except OpenRouterError as exc:
            await message.reply(exc.user_message, reply_markup=RETRY_KEYBOARD)
            return
        except Exception:
            logger.exception("Speaking analysis failed")
            await message.reply(RECORDING_FAILED, reply_markup=RETRY_KEYBOARD)
            return
        await message.answer(text, parse_mode="HTML")
