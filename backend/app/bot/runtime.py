from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command

from app.bot.handler import (
    SynonymSwap,
    TelegramAdminWebAppHandler,
    TelegramDescriptionLookupHandler,
    TelegramLearnCallbackHandler,
    TelegramReviewWebAppHandler,
    TelegramTextHandler,
)
from app.bot.rate_limiter import InMemoryRateLimiter
from app.clients.openrouter import OpenRouterClient
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.card import Card
from app.services.card_service import CardServiceResult, apply_source_text


@dataclass(slots=True)
class BotRuntime:
    bot: Bot
    dispatcher: Dispatcher
    webhook_secret: str


def _build_apply_source_text(client: OpenRouterClient) -> Callable[[str], CardServiceResult]:
    def process_source_text(source_text: str) -> CardServiceResult:
        with SessionLocal() as session:
            return apply_source_text(session, client, source_text)

    return process_source_text


def _set_learning(card_id: int, is_learning: bool) -> Card | None:
    with SessionLocal() as session:
        card = session.get(Card, card_id)
        if card is None:
            return None
        card.is_learning = is_learning
        session.commit()
        return card


def _build_swap_for_synonym(client: OpenRouterClient) -> Callable[[int], SynonymSwap | None]:
    def swap(card_id: int) -> SynonymSwap | None:
        with SessionLocal() as session:
            card = session.get(Card, card_id)
            if card is None or not card.common_synonym:
                return None
            old = card.canonical_text
            result = apply_source_text(session, client, card.common_synonym)
            if result.card is None:
                return SynonymSwap(old=old, result=None)
            # The user picked this word, so it is learned whatever its own frequency is;
            # the rare word stays in the dictionary as it was (not learning).
            result.card.is_learning = True
            session.commit()
            session.refresh(result.card)
            return SynonymSwap(old=old, result=result)

    return swap


def build_bot_router(
    text_handler: TelegramTextHandler,
    description_lookup_handler: TelegramDescriptionLookupHandler,
    admin_handler: TelegramAdminWebAppHandler,
    review_handler: TelegramReviewWebAppHandler,
    learn_callback_handler: TelegramLearnCallbackHandler,
) -> Router:
    router = Router()

    @router.message(Command("admin"))
    async def handle_admin_command(message) -> None:
        await admin_handler.handle_message(message)

    @router.message(Command("review"))
    async def handle_review_command(message) -> None:
        await review_handler.handle_message(message)

    @router.callback_query(F.data.regexp(r"^(learn|skip|alt):\d+$"))
    async def handle_learn_callback(callback) -> None:
        await learn_callback_handler.handle_callback(callback)

    @router.message(Command("find"))
    async def handle_find_command(message) -> None:
        await description_lookup_handler.handle_message(message)

    @router.message(F.text)
    async def handle_text_message(message) -> None:
        await text_handler.handle_message(message)

    return router


def build_bot_runtime() -> BotRuntime:
    settings = get_settings()
    settings.validate_runtime_config()
    settings.validate_webhook_config()
    assert settings.telegram_bot_token is not None
    assert settings.openrouter_api_key is not None
    assert settings.telegram_allowed_user_id is not None
    assert settings.telegram_webhook_secret is not None
    assert settings.resolved_telegram_webapp_url is not None

    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher()
    openrouter_client = OpenRouterClient(
        api_key=settings.openrouter_api_key,
        model=settings.llm_model,
    )
    rate_limiter = InMemoryRateLimiter(limit=5, window_seconds=60.0)
    text_handler = TelegramTextHandler(
        allowed_user_id=settings.telegram_allowed_user_id,
        apply_source_text=_build_apply_source_text(openrouter_client),
        rate_limiter=rate_limiter,
    )
    description_lookup_handler = TelegramDescriptionLookupHandler(
        allowed_user_id=settings.telegram_allowed_user_id,
        lookup_candidates_from_description=openrouter_client.lookup_candidates_from_description,
        rate_limiter=rate_limiter,
    )
    admin_handler = TelegramAdminWebAppHandler(
        allowed_user_id=settings.telegram_allowed_user_id,
        webapp_url=settings.resolved_telegram_webapp_url,
    )
    review_handler = TelegramReviewWebAppHandler(
        allowed_user_id=settings.telegram_allowed_user_id,
        webapp_url=settings.resolved_telegram_webapp_url,
    )
    learn_callback_handler = TelegramLearnCallbackHandler(
        allowed_user_id=settings.telegram_allowed_user_id,
        set_learning=_set_learning,
        swap_for_synonym=_build_swap_for_synonym(openrouter_client),
    )
    dispatcher.include_router(
        build_bot_router(
            text_handler,
            description_lookup_handler,
            admin_handler,
            review_handler,
            learn_callback_handler,
        )
    )

    return BotRuntime(
        bot=bot,
        dispatcher=dispatcher,
        webhook_secret=settings.telegram_webhook_secret,
    )


@lru_cache(maxsize=1)
def get_bot_runtime() -> BotRuntime:
    return build_bot_runtime()
