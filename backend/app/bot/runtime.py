from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command

import app.models.anki_sync_attempt as anki_sync_attempt_model
import app.models.card as card_model
from app.bot.handler import (
    TelegramAdminWebAppHandler,
    TelegramDescriptionLookupHandler,
    TelegramTextHandler,
)
from app.bot.rate_limiter import InMemoryRateLimiter
from app.clients.openrouter import (
    OpenRouterClient,
    OpenRouterError,
    OpenRouterProtocolError,
    OpenRouterTimeoutError,
    OpenRouterTransportError,
)
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.schemas.description_lookup import DescriptionLookupResponse
from app.services.card_service import CardService, CardServiceResult, CardServiceUpstreamError

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


def _build_lookup_source_text_from_description(
    client: OpenRouterClient,
) -> Callable[[str], DescriptionLookupResponse]:
    def lookup_source_text_from_description(description: str) -> DescriptionLookupResponse:
        try:
            return client.lookup_source_text_from_description(description)
        except OpenRouterTimeoutError as exc:
            raise _as_upstream_error("LLM lookup timed out", exc) from exc
        except OpenRouterTransportError as exc:
            raise _as_upstream_error("LLM lookup transport failed", exc) from exc
        except OpenRouterProtocolError as exc:
            raise _as_upstream_error("LLM lookup returned invalid payload", exc) from exc
        except OpenRouterError as exc:
            raise _as_upstream_error("LLM lookup failed", exc) from exc

    return lookup_source_text_from_description


def _as_upstream_error(message: str, exc: OpenRouterError) -> CardServiceUpstreamError:
    return CardServiceUpstreamError(
        message,
        code=exc.code,
        user_message=exc.user_message,
    )


def build_bot_router(
    text_handler: TelegramTextHandler,
    description_lookup_handler: TelegramDescriptionLookupHandler,
    admin_handler: TelegramAdminWebAppHandler,
) -> Router:
    router = Router()

    @router.message(Command("admin"))
    async def handle_admin_command(message) -> None:
        await admin_handler.handle_message(message)

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
    assert settings.telegram_webapp_url is not None

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
        lookup_source_text_from_description=_build_lookup_source_text_from_description(
            openrouter_client
        ),
        apply_source_text=_build_apply_source_text(openrouter_client),
        rate_limiter=rate_limiter,
    )
    admin_handler = TelegramAdminWebAppHandler(
        allowed_user_id=settings.telegram_allowed_user_id,
        webapp_url=settings.telegram_webapp_url,
    )
    dispatcher.include_router(
        build_bot_router(text_handler, description_lookup_handler, admin_handler)
    )

    return BotRuntime(
        bot=bot,
        dispatcher=dispatcher,
        webhook_secret=settings.telegram_webhook_secret,
    )


@lru_cache(maxsize=1)
def get_bot_runtime() -> BotRuntime:
    return build_bot_runtime()
