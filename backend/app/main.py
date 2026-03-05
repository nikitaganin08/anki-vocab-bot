from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import anki, cards, stats, telegram_webhook

app = FastAPI(title="anki-vocab-bot")

app.include_router(cards.router)
app.include_router(stats.router)
app.include_router(anki.router)
app.include_router(telegram_webhook.router)


@app.get("/api/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if _FRONTEND_DIST.exists():
    app.mount("/admin", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="admin")
