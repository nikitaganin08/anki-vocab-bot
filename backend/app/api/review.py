from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.deps import (
    get_openrouter_client,
    get_speaking_client,
    require_telegram_webapp_user,
)
from app.api.schemas import (
    CardResponse,
    ReviewCheckRequest,
    ReviewCheckResponse,
    ReviewGradeRequest,
    ReviewGradeResponse,
    ReviewPromptResponse,
    ReviewSessionItemResponse,
    ReviewSessionResponse,
    ReviewUndoResponse,
    SentenceFeedbackResponse,
    SentenceRequest,
    TranscriptResponse,
    TranslateRequest,
    TranslateResponse,
)
from app.clients.openrouter import OpenRouterClient, OpenRouterError
from app.db.session import get_session
from app.models.card import Card
from app.schemas.speaking import SpeakingRejected
from app.services.answer_check import auto_rating, build_prompt, check_answer
from app.services.app_settings import get_app_settings
from app.services.card_service import normalize_canonical_text
from app.services.review_stats import ReviewSummary, build_summary, record_goal_if_closed
from app.services.srs import (
    GradeInput,
    StaleReviewError,
    as_utc,
    build_scheduler,
    build_session,
    grade_card,
    preview_intervals,
    undo_last,
)

router = APIRouter(
    prefix="/api/review",
    tags=["review"],
    dependencies=[Depends(require_telegram_webapp_user)],
)

SessionDep = Annotated[Session, Depends(get_session)]

TRANSLATION_OPTIONAL_PREFIXES = ("to ", "a ", "an ", "the ")


def _get_card(session: Session, card_id: int) -> Card:
    card = session.get(Card, card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    return card


@router.get("/summary", response_model=ReviewSummary)
def get_summary(session: SessionDep) -> ReviewSummary:
    return build_summary(session, get_app_settings(session), datetime.now(UTC))


@router.get("/session", response_model=ReviewSessionResponse)
def get_review_session(
    session: SessionDep,
    size: Annotated[int, Query(ge=1, le=200)] = 10,
    include_backlog: bool = False,
    only_new: bool = False,
) -> ReviewSessionResponse:
    items = build_session(
        session, get_app_settings(session), datetime.now(UTC), size, include_backlog, only_new
    )
    return ReviewSessionResponse(
        items=[
            ReviewSessionItemResponse(
                card=CardResponse.from_card(item.card),
                intro=item.intro,
                # The expected answer stays on the server; /check reveals it.
                prompt=ReviewPromptResponse(
                    kind=item.prompt.kind,
                    index=item.prompt.index,
                    masked=item.prompt.masked,
                    hint_translation=item.prompt.hint_translation,
                ),
                srs_due_at=as_utc(item.card.srs_due_at) if item.card.srs_due_at else None,
            )
            for item in items
        ]
    )


@router.post("/{card_id}/check", response_model=ReviewCheckResponse)
def check(card_id: int, body: ReviewCheckRequest, session: SessionDep) -> ReviewCheckResponse:
    settings = get_app_settings(session)
    card = _get_card(session, card_id)
    # Rebuild the prompt the client was shown: prompt_index picks the chunk.
    chunks = card.chunks_json if body.prompt_kind == "chunk" else []
    prompt = build_prompt(
        chunks, card.translation_variants_json, card.canonical_text, body.prompt_index
    )
    prefixes = TRANSLATION_OPTIONAL_PREFIXES if prompt.kind == "translation" else ()
    result = check_answer(
        body.typed,
        prompt.expected,
        optional_prefixes=prefixes,
        base_form=card.canonical_text if prompt.kind == "chunk" else None,
    )
    intervals = preview_intervals(build_scheduler(settings), card, datetime.now(UTC))
    return ReviewCheckResponse(
        verdict=result.verdict,
        expected=result.expected,
        auto_rating=auto_rating(result.verdict, body.hint_used),
        intervals=intervals,
    )


@router.post("/{card_id}/sentence", response_model=SentenceFeedbackResponse)
def check_sentence(
    card_id: int,
    body: SentenceRequest,
    session: SessionDep,
    openrouter_client: Annotated[OpenRouterClient, Depends(get_openrouter_client)],
) -> SentenceFeedbackResponse:
    """Feedback on the learner's own sentence with the card's word; logs nothing, no grading."""
    card = _get_card(session, card_id)
    try:
        feedback = openrouter_client.check_sentence(card.canonical_text, body.sentence.strip())
    except OpenRouterError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.user_message
        ) from exc
    return SentenceFeedbackResponse.model_validate(feedback.model_dump())


@router.post("/translate", response_model=TranslateResponse)
def translate_typed(
    body: TranslateRequest,
    session: SessionDep,
    openrouter_client: Annotated[OpenRouterClient, Depends(get_openrouter_client)],
) -> TranslateResponse:
    """What a wrong answer means: the deck's translation when it is a card, else the LLM's."""
    text = body.text.strip()
    card = session.scalar(
        select(Card).where(Card.canonical_text_normalized == normalize_canonical_text(text))
    )
    if card is not None and card.translation_variants_json:
        return TranslateResponse(translation=", ".join(card.translation_variants_json[:2]))
    try:
        return TranslateResponse(translation=openrouter_client.translate_word(text))
    except OpenRouterError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.user_message
        ) from exc


# MediaRecorder output: iOS records AAC in MP4, Chrome Opus in WebM.
AUDIO_FORMATS = {"audio/mp4": "mp4", "audio/webm": "webm", "audio/ogg": "ogg", "audio/aac": "aac"}
MAX_DICTATION_BYTES = 2_000_000  # about two minutes of AAC; a sentence takes seconds


@router.post("/{card_id}/transcribe", response_model=TranscriptResponse)
async def transcribe_sentence(
    card_id: int,
    request: Request,
    session: SessionDep,
    speaking_client: Annotated[OpenRouterClient, Depends(get_speaking_client)],
) -> TranscriptResponse:
    """A dictated sentence (raw audio body) as text for the sentence practice; nothing is kept."""
    card = _get_card(session, card_id)
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    audio_format = AUDIO_FORMATS.get(content_type)
    if audio_format is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported audio format"
        )
    audio = await request.body()
    if not audio:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty recording")
    if len(audio) > MAX_DICTATION_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Recording is too long"
        )
    try:
        result = await run_in_threadpool(
            speaking_client.transcribe_sentence,
            audio=audio,
            audio_format=audio_format,
            word=card.canonical_text,
        )
    except OpenRouterError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.user_message
        ) from exc
    if isinstance(result, SpeakingRejected):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=result.message_for_user
        )
    return TranscriptResponse(text=result.text)


@router.post("/{card_id}/grade", response_model=ReviewGradeResponse)
def grade(card_id: int, body: ReviewGradeRequest, session: SessionDep) -> ReviewGradeResponse:
    settings = get_app_settings(session)
    card = _get_card(session, card_id)
    grade_input = GradeInput(
        rating=body.rating,
        auto_rating=body.auto_rating,
        overridden=body.overridden,
        typed_answer=body.typed,
        prompt_kind=body.prompt_kind,
        prompt_index=body.prompt_index,
        verdict=body.verdict,
        hint_used=body.hint_used,
        response_ms=body.response_ms,
        expected_due_at=body.expected_due_at,
    )
    try:
        card = grade_card(session, settings, card, grade_input, datetime.now(UTC))
    except StaleReviewError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    record_goal_if_closed(session, settings, datetime.now(UTC))
    return ReviewGradeResponse(srs_due_at=as_utc(card.srs_due_at), srs_state=card.srs_state)


@router.post("/undo", response_model=ReviewUndoResponse)
def undo(session: SessionDep) -> ReviewUndoResponse:
    card = undo_last(session)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nothing to undo")
    return ReviewUndoResponse(card_id=card.id)
