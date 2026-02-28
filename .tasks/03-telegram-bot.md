# Phase 3 - Telegram Bot

## Objective
Deliver a production-ready single-user bot flow from message intake to formatted card response.

## Tasks
Status is tracked in `bd`; the list below is reference-only.

- 3.1 Set up aiogram bot bootstrap and long-polling runner.
- 3.2 Implement allowed-user guard based on `TELEGRAM_ALLOWED_USER_ID`.
- 3.3 Implement per-user rate limiter: max 5 requests/minute.
- 3.4 Build text intake handler:
- 3.4.1 Normalize whitespace.
- 3.4.2 Validate token count (`1..8`) before LLM call.
- 3.4.3 Return friendly validation message for invalid input.
- 3.5 Integrate with card service and map service states to Telegram responses.
- 3.6 Add formatter for accepted card payload (canonical text, transcription, translations, explanation, examples, frequency).
- 3.7 Ensure duplicate responses return the existing card with "already in dictionary" note.
- 3.8 Add tests for rate limit and input validation behavior.

## Deliverables
- Bot accepts only authorized user messages.
- Full request flow works end-to-end against service layer.

## Exit Criteria
- Invalid/too-long input never triggers LLM request.
- Duplicate and newly created paths return consistent message structure.
