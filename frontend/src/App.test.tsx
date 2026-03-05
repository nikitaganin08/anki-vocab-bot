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

function setupFetchMock(): void {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;

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

  it("renders cards list on index route", async () => {
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Cards" })).toBeInTheDocument();
    expect((await screen.findAllByText("take off")).length).toBeGreaterThan(0);
  });

  it("renders cards table on cards route", async () => {
    window.history.pushState({}, "", "/cards");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Cards" })).toBeInTheDocument();
    const [canonicalCell] = await screen.findAllByText("take off");
    const row = canonicalCell.closest("tr");
    expect(row).not.toBeNull();
    expect(within(row as HTMLTableRowElement).getByText("pending")).toBeInTheDocument();
  });
});
