from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache

from aiogram import Bot, Dispatcher, F, Router

import app.models.anki_sync_attempt as anki_sync_attempt_model
import app.models.card as card_model
from app.bot.handler import TelegramTextHandler
from app.bot.rate_limiter import InMemoryRateLimiter
from app.clients.openrouter import OpenRouterClient
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.card_service import CardService, CardServiceResult

MODEL_MODULES = (anki_sync_attempt_model, card_model)


@dataclass(slots=True)
class BotRuntime:
    bot: Bot
    dispatcher: Dispatcher
    webhook_secret: str


def _build_apply_source_text(client: OpenRouterClient) -> Callable[[str], CardServiceResult]:
    def apply_source_text(source_text: str) -> CardServiceResult:
        with SessionLocal() as session:
            service = CardService(session=session, generator=client)
            return service.apply_source_text(source_text)

    return apply_source_text


def build_bot_router(handler: TelegramTextHandler) -> Router:
    router = Router()

    @router.message(F.text)
    async def handle_text_message(message) -> None:
        await handler.handle_message(message)

    return router


def build_bot_runtime() -> BotRuntime:
    settings = get_settings()
    settings.validate_runtime_config()
    settings.validate_webhook_config()
    assert settings.telegram_bot_token is not None
    assert settings.openrouter_api_key is not None
    assert settings.telegram_allowed_user_id is not None
    assert settings.telegram_webhook_secret is not None

    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher()
    openrouter_client = OpenRouterClient(
        api_key=settings.openrouter_api_key,
        model=settings.llm_model,
    )
    handler = TelegramTextHandler(
        allowed_user_id=settings.telegram_allowed_user_id,
        apply_source_text=_build_apply_source_text(openrouter_client),
        rate_limiter=InMemoryRateLimiter(limit=5, window_seconds=60.0),
    )
    dispatcher.include_router(build_bot_router(handler))

    return BotRuntime(
        bot=bot,
        dispatcher=dispatcher,
        webhook_secret=settings.telegram_webhook_secret,
    )


@lru_cache(maxsize=1)
def get_bot_runtime() -> BotRuntime:
    return build_bot_runtime()
