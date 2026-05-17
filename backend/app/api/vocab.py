from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_card_generator, get_telegram_sender, require_anki_token
from app.api.schemas import MobileCardPreview, MobileLookupRequest, MobileLookupResponse
from app.bot.formatter import format_card_service_result, format_rate_limit_message
from app.bot.input_validation import validate_source_input
from app.bot.rate_limiter import InMemoryRateLimiter
from app.clients.telegram import TelegramBotSender, TelegramSendError
from app.db.session import get_session
from app.services.card_service import CardGenerator, CardService, CardServiceUpstreamError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/vocab",
    tags=["vocab"],
    dependencies=[Depends(require_anki_token)],
)

SessionDep = Annotated[Session, Depends(get_session)]
CardGeneratorDep = Annotated[CardGenerator, Depends(get_card_generator)]
TelegramSenderDep = Annotated[TelegramBotSender, Depends(get_telegram_sender)]

_mobile_rate_limiter = InMemoryRateLimiter(limit=5, window_seconds=60.0)
_MOBILE_RATE_LIMIT_KEY = 0


@router.post("/mobile-lookup", response_model=MobileLookupResponse)
def mobile_lookup(
    payload: MobileLookupRequest,
    session: SessionDep,
    generator: CardGeneratorDep,
    telegram_sender: TelegramSenderDep,
) -> MobileLookupResponse:
    if not _mobile_rate_limiter.allow_request(_MOBILE_RATE_LIMIT_KEY):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=format_rate_limit_message(),
        )

    validation = validate_source_input(payload.text)
    if not validation.ok or validation.normalized_text is None:
        message = validation.error_message or "Invalid input."
        logger.info("mobile lookup rejected invalid input")
        return MobileLookupResponse(
            status="invalid_input",
            message=message,
            preview=None,
            telegram_sent=False,
        )

    service = CardService(session=session, generator=generator)
    try:
        result = service.apply_source_text(validation.normalized_text)
    except CardServiceUpstreamError as exc:
        logger.warning("mobile lookup upstream error: %s", exc.code)
        return MobileLookupResponse(
            status="upstream_error",
            message=exc.user_message,
            preview=None,
            telegram_sent=False,
        )

    message, parse_mode = format_card_service_result(result)
    if result.card is None:
        logger.info("mobile lookup finished without card: %s", result.status)
        return MobileLookupResponse(
            status=result.status,
            message=message,
            preview=None,
            telegram_sent=False,
        )

    telegram_sent = False
    if payload.send_to_telegram:
        try:
            telegram_sender.send_message(message, parse_mode=parse_mode)
        except TelegramSendError as exc:
            logger.warning("mobile lookup telegram send failed")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Telegram send failed",
            ) from exc
        telegram_sent = True

    logger.info("mobile lookup finished: %s", result.status)
    preview = MobileCardPreview.from_card(result.card) if payload.return_preview else None
    return MobileLookupResponse(
        status=result.status,
        message=message,
        preview=preview,
        telegram_sent=telegram_sent,
    )
