import type {
  AppSettings,
  Card,
  CardBatchImportResponse,
  CardListResponse,
  CardsQuery,
  CheckRequest,
  CheckResponse,
  GradeRequest,
  GradeResponse,
  ReviewSessionItem,
  ReviewSessionResponse,
  ReviewSummary,
} from "./types";
import { getTelegramInitData } from "../telegram";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

const WEBAPP_PREFIX_PATTERN = /^(.*)\/telegram\/webapp(?:\/.*)?$/;

function resolveApiPath(path: string): string {
  return (window.location.pathname.match(WEBAPP_PREFIX_PATTERN)?.[1] ?? "") + path;
}

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

// The body is read once: FastAPI sends {detail: string} or, on 422, {detail: [{msg}]}.
async function readErrorMessage(response: Response): Promise<string> {
  const text = await response.text();
  try {
    const detail = (JSON.parse(text) as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail.length > 0) {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail.map((item: { msg?: string }) => item.msg).join("; ");
    }
  } catch {
    // Not JSON: fall through to the raw text.
  }

  return text.length > 0 ? text : `Request failed (${response.status})`;
}

async function request<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(resolveApiPath(path), {
    ...(method === "GET" ? {} : { method }),
    headers: buildHeaders(headers),
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });

  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response), response.status);
  }

  return (response.status === 204 ? undefined : await response.json()) as T;
}

export async function getCards(query: CardsQuery): Promise<CardListResponse> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries({
    offset: query.offset,
    limit: query.limit,
    search: query.search,
    source_language: query.source_language,
    entry_type: query.entry_type,
    is_learning: query.is_learning,
  })) {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  }

  return request(`/api/cards?${params}`);
}

export async function importCardsBatch(
  source_texts: string[],
): Promise<CardBatchImportResponse> {
  return request("/api/cards/batch", "POST", { source_texts });
}

export async function deleteCard(cardId: number): Promise<void> {
  return request(`/api/cards/${cardId}`, "DELETE");
}

export async function setCardLearning(cardId: number, isLearning: boolean): Promise<Card> {
  return request(`/api/cards/${cardId}`, "PATCH", { is_learning: isLearning });
}

// `version` (the word) only busts the HTTP cache: card ids can be reused after a delete and
// the audio is cached for a year; the backend ignores it.
// `phrase` asks for a usage chunk or example of the card instead of the word.
export async function getCardAudio(cardId: number, version: string, phrase?: string): Promise<Blob> {
  const query = new URLSearchParams({ v: version });
  if (phrase !== undefined) {
    query.set("text", phrase);
  }
  const url = `${resolveApiPath(`/api/cards/${cardId}/audio`)}?${query}`;
  const response = await fetch(url, {
    headers: buildHeaders({}),
  });
  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response), response.status);
  }
  return response.blob();
}

export async function getReviewSummary(): Promise<ReviewSummary> {
  return request("/api/review/summary");
}

export async function getReviewSession(opts: {
  size: number;
  includeBacklog?: boolean;
}): Promise<ReviewSessionItem[]> {
  const params = new URLSearchParams({
    size: String(opts.size),
    include_backlog: String(opts.includeBacklog ?? false),
  });
  const response = await request<ReviewSessionResponse>(`/api/review/session?${params}`);
  return response.items;
}

export async function checkAnswer(cardId: number, body: CheckRequest): Promise<CheckResponse> {
  return request(`/api/review/${cardId}/check`, "POST", body);
}

export async function gradeCard(cardId: number, body: GradeRequest): Promise<GradeResponse> {
  return request(`/api/review/${cardId}/grade`, "POST", body);
}

export async function getSettings(): Promise<AppSettings> {
  return request("/api/settings");
}

export async function saveSettings(body: AppSettings): Promise<AppSettings> {
  return request("/api/settings", "PUT", body);
}
