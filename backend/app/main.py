from fastapi import FastAPI

app = FastAPI(title="anki-vocab-bot")


@app.get("/api/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
