import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";

import { App } from "./App";

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "Content-Type": "application/json",
    },
  });
}

const cardsPayload = {
  items: [
    {
      id: 1,
      source_text: "take off",
      source_language: "en",
      entry_type: "phrasal_verb",
      canonical_text: "take off",
      canonical_text_normalized: "take off",
      transcription: "/teik of/",
      translation_variants: ["v1", "v2"],
      explanation: "example explanation",
      examples: ["e1", "e2", "e3"],
      frequency: 4,
      frequency_note: null,
      eligible_for_anki: true,
      anki_sync_status: "pending",
      anki_note_id: null,
      llm_model: "test-model",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ],
  total: 1,
  offset: 0,
  limit: 20,
};

const cardPayload = cardsPayload.items[0];

const statsPayload = {
  total_cards: 12,
  eligible_for_anki: 5,
  anki_pending: 3,
  anki_synced: 8,
  anki_failed: 1,
  by_entry_type: {
    word: 6,
    phrasal_verb: 2,
    collocation: 2,
    idiom: 1,
    expression: 1,
  },
  by_source_language: {
    en: 9,
    ru: 3,
  },
};

function setupFetchMock(): void {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;

    if (url.startsWith("/api/stats")) {
      return jsonResponse(statsPayload);
    }

    if (url.startsWith("/api/cards/1")) {
      return jsonResponse(cardPayload);
    }

    if (url.startsWith("/api/cards")) {
      return jsonResponse(cardsPayload);
    }

    return jsonResponse({ detail: "Not found" }, 404);
  });

  vi.stubGlobal("fetch", fetchMock);
}

describe("App", () => {
  beforeEach(() => {
    setupFetchMock();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    window.history.pushState({}, "", "/");
  });

  it("renders the dashboard with stats", async () => {
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByText("Total cards")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
  });

  it("renders cards table on cards route", async () => {
    window.history.pushState({}, "", "/cards");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Cards" })).toBeInTheDocument();
    const canonicalLink = await screen.findByRole("link", { name: "take off" });
    expect(canonicalLink).toBeInTheDocument();

    const row = canonicalLink.closest("tr");
    expect(row).not.toBeNull();
    expect(within(row as HTMLTableRowElement).getByText("pending")).toBeInTheDocument();
  });

  it("renders card detail route", async () => {
    window.history.pushState({}, "", "/cards/1");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "take off" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Translations" })).toBeInTheDocument();
  });
});
