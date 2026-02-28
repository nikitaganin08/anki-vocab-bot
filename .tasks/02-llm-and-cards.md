# Phase 2 - LLM Integration and Card Service

## Objective
Implement robust LLM contract handling and the core card creation pipeline with two-step deduplication.

## Tasks
Status is tracked in `bd`; the list below is reference-only.

- 2.1 Define Pydantic schemas for LLM accepted/rejected responses.
- 2.2 Enforce validation rules: `source_language`, `entry_type`, translations count, examples count, frequency range.
- 2.3 Implement OpenRouter client (`httpx`) with configurable model and timeout.
- 2.4 Create prompt/template that forces strict JSON contract.
- 2.5 Implement card application service:
- 2.5.1 Normalize input text and tokenization helper.
- 2.5.2 Deduplicate by exact `source_text` before LLM call.
- 2.5.3 Deduplicate by `canonical_text_normalized` after LLM call.
- 2.5.4 Persist accepted card and set `eligible_for_anki = frequency > 2`.
- 2.6 Return unified service result states: `created`, `duplicate_source`, `duplicate_canonical`, `rejected`.
- 2.7 Add backend unit tests for all service states and validation branches.
- 2.8 Handle OpenRouter transport, timeout, and malformed-JSON failures with explicit user-facing behavior and test coverage.

## Deliverables
- Stable service API used by both Telegram bot and HTTP API.
- Deterministic behavior for duplicate handling.

## Exit Criteria
- Unit tests cover happy path + key edge cases.
- Rejected inputs are never persisted.
