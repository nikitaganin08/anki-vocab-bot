import type {
  CardBatchImportResponse,
  CardListResponse,
  CardsQuery,
  HealthResponse,
} from "./types";

type QueryValue = string | number | boolean | null | undefined;
type QueryParams = Record<string, QueryValue>;

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function toUrl(path: string, query?: QueryParams): string {
  if (!query) {
    return path;
  }

  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "") {
      continue;
    }
    params.set(key, String(value));
  }

  const queryString = params.toString();
  return queryString ? `${path}?${queryString}` : path;
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

async function getJson<T>(path: string, query?: QueryParams): Promise<T> {
  const response = await fetch(toUrl(path, query), {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response));
  }

  return (await response.json()) as T;
}

async function postJson<TResponse, TPayload>(path: string, payload: TPayload): Promise<TResponse> {
  const response = await fetch(path, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response));
  }

  return (await response.json()) as TResponse;
}

async function requestNoContent(path: string, method: "DELETE"): Promise<void> {
  const response = await fetch(path, {
    method,
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response));
  }
}

export function getHealth(): Promise<HealthResponse> {
  return getJson<HealthResponse>("/api/health");
}

export function getCards(query: CardsQuery): Promise<CardListResponse> {
  return getJson<CardListResponse>("/api/cards", {
    offset: query.offset,
    limit: query.limit,
    search: query.search,
    source_language: query.source_language,
    entry_type: query.entry_type,
    anki_sync_status: query.anki_sync_status,
    eligible_for_anki: query.eligible_for_anki,
  });
}

export function deleteCard(cardId: number): Promise<void> {
  return requestNoContent(`/api/cards/${cardId}`, "DELETE");
}

export function importCardsBatch(source_texts: string[]): Promise<CardBatchImportResponse> {
  return postJson<CardBatchImportResponse, { source_texts: string[] }>(
    "/api/cards/batch",
    { source_texts },
  );
}
