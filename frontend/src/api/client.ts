import type {
  CardBatchImportResponse,
  CardListResponse,
  CardsQuery,
} from "./types";
import { resolveApiPath } from "../routing";
import { getTelegramInitData } from "../telegram";

export class ApiError extends Error {}

function buildHeaders(headers: Record<string, string>): Record<string, string> {
  const telegramInitData = getTelegramInitData();
  if (!telegramInitData) {
    return headers;
  }

  return {
    ...headers,
    "X-Telegram-Init-Data": telegramInitData,
  };
}

async function readErrorMessage(response: Response): Promise<string> {
  const contentType = response.headers.get("Content-Type") ?? "";

  if (contentType.includes("application/json")) {
    const payload = (await response.json()) as { detail?: string };
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return payload.detail;
    }
  }

  const text = await response.text();
  if (text.length > 0) {
    return text;
  }

  return `Request failed with status ${response.status}`;
}

export async function getCards(query: CardsQuery): Promise<CardListResponse> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries({
    offset: query.offset,
    limit: query.limit,
    search: query.search,
    source_language: query.source_language,
    entry_type: query.entry_type,
    anki_sync_status: query.anki_sync_status,
    eligible_for_anki: query.eligible_for_anki,
  })) {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  }

  const response = await fetch(`${resolveApiPath("/api/cards")}?${params}`, {
    headers: buildHeaders({
      Accept: "application/json",
    }),
  });

  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response));
  }

  return (await response.json()) as CardListResponse;
}

export async function importCardsBatch(
  source_texts: string[],
): Promise<CardBatchImportResponse> {
  const response = await fetch(resolveApiPath("/api/cards/batch"), {
    method: "POST",
    headers: buildHeaders({
      Accept: "application/json",
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({ source_texts }),
  });

  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response));
  }

  return (await response.json()) as CardBatchImportResponse;
}

export async function deleteCard(cardId: number): Promise<void> {
  const response = await fetch(resolveApiPath(`/api/cards/${cardId}`), {
    method: "DELETE",
    headers: buildHeaders({
      Accept: "application/json",
    }),
  });

  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response));
  }
}
