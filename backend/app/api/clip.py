from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.cards import import_source_text
from app.api.deps import get_openrouter_client, require_clip_token
from app.api.schemas import CardBatchImportItemResponse
from app.clients.openrouter import OpenRouterClient
from app.db.session import get_session

router = APIRouter(prefix="/api/clip", tags=["clip"], dependencies=[Depends(require_clip_token)])


class ClipRequest(BaseModel):
    text: str = Field(max_length=200)


@router.post("", response_model=CardBatchImportItemResponse)
def clip(
    body: ClipRequest,
    session: Annotated[Session, Depends(get_session)],
    openrouter_client: Annotated[OpenRouterClient, Depends(get_openrouter_client)],
) -> CardBatchImportItemResponse:
    """Adds the text selected in the browser, like sending it to the bot."""
    return import_source_text(session, openrouter_client, body.text)
