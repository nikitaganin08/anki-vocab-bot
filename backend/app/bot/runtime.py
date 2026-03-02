from __future__ import annotations

from aiogram import Bot, Dispatcher, F, Router

from app.bot.handler import TelegramTextHandler
from app.bot.rate_limiter import InMemoryRateLimiter
from app.clients.openrouter import OpenRouterClient
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.card_service import CardService, CardServiceResult


def _build_apply_source_text(client: OpenRouterClient):
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


async def run_polling_bot() -> None:
    settings = get_settings()
    settings.validate_runtime_config()
    assert settings.telegram_bot_token is not None
    assert settings.openrouter_api_key is not None
    assert settings.telegram_allowed_user_id is not None

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

    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()
