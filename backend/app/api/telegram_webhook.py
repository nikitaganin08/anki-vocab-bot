from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.bot.runtime import get_bot_runtime

router = APIRouter(tags=["telegram"])


@router.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    telegram_secret: str | None = Header(
        default=None,
        alias="X-Telegram-Bot-Api-Secret-Token",
    ),
) -> dict[str, bool]:
    runtime = get_bot_runtime()
    if telegram_secret != runtime.webhook_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook secret")

    try:
        payload = await request.json()
    except Exception as exc:  # defensive: invalid JSON should return 400
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook payload",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook payload",
        )

    await runtime.dispatcher.feed_raw_update(runtime.bot, payload)
    return {"ok": True}
