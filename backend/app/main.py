from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api import anki, cards, telegram_webhook

app = FastAPI(title="anki-vocab-bot")

app.include_router(cards.router)
app.include_router(anki.router)
app.include_router(telegram_webhook.router)


@app.get("/api/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
_FRONTEND_INDEX = _FRONTEND_DIST / "index.html"

if _FRONTEND_INDEX.exists():

    @app.get("/admin")
    @app.get("/admin/")
    def admin_index() -> FileResponse:
        return FileResponse(_FRONTEND_INDEX)


    @app.get("/admin/{path:path}")
    def admin_spa(path: str) -> FileResponse:
        candidate = _FRONTEND_DIST / path
        if candidate.is_file():
            return FileResponse(candidate)

        return FileResponse(_FRONTEND_INDEX)
