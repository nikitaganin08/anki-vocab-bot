import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api import cards, review, settings, telegram_webhook
from app.bot.runtime import get_bot_runtime
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.reminders import run_reminder_loop

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    task = None
    if get_settings().telegram_bot_token and os.environ.get("DISABLE_REMINDERS") != "1":
        try:
            bot = get_bot_runtime().bot
        except ValueError as exc:  # partial bot config, e.g. local dev without a webhook
            logger.warning("Reminders disabled: %s", exc)
        else:
            task = asyncio.create_task(run_reminder_loop(SessionLocal, bot))
    yield
    if task is not None:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="anki-vocab-bot", lifespan=lifespan)

app.include_router(cards.router)
app.include_router(review.router)
app.include_router(settings.router)
app.include_router(telegram_webhook.router)


@app.get("/api/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
_FRONTEND_INDEX = _FRONTEND_DIST / "index.html"

if _FRONTEND_INDEX.exists():

    @app.get("/telegram/webapp")
    @app.get("/telegram/webapp/")
    def telegram_webapp_index() -> FileResponse:
        return FileResponse(_FRONTEND_INDEX)

    @app.get("/telegram/webapp/{path:path}")
    def telegram_webapp_spa(path: str) -> FileResponse:
        candidate = (_FRONTEND_DIST / path).resolve()
        if candidate.is_relative_to(_FRONTEND_DIST) and candidate.is_file():
            return FileResponse(candidate)

        return FileResponse(_FRONTEND_INDEX)
