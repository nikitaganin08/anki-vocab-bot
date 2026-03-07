import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

interface TelegramWindow extends Window {
  Telegram?: {
    WebApp?: {
      initData: string;
      ready?: () => void;
      expand?: () => void;
    };
  };
}

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

function setTelegramWebApp(initData = "signed-init-data"): void {
  const telegramWindow = window as TelegramWindow;
  telegramWindow.Telegram = {
    WebApp: {
      initData,
      ready: vi.fn(),
      expand: vi.fn(),
    },
  };
}

function clearTelegramWebApp(): void {
  delete (window as TelegramWindow).Telegram;
}

function setupFetchMock(): void {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;

    if (url.includes("/api/cards")) {
      return jsonResponse(cardsPayload);
    }

    return jsonResponse({ detail: "Not found" }, 404);
  });

  vi.stubGlobal("fetch", fetchMock);
}

describe("App", () => {
  beforeEach(() => {
    setupFetchMock();
    clearTelegramWebApp();
  });

  afterEach(() => {
    clearTelegramWebApp();
    vi.unstubAllGlobals();
    window.history.pushState({}, "", "/");
  });

  it("blocks boot outside Telegram", async () => {
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Open This Panel From Telegram" })).toBeInTheDocument();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("renders cards list on the webapp index route", async () => {
    setTelegramWebApp();
    window.history.pushState({}, "", "/telegram/webapp/");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Cards" })).toBeInTheDocument();
    expect((await screen.findAllByText("take off")).length).toBeGreaterThan(0);
  });

  it("keeps cards route working behind an external prefix and sends Telegram auth", async () => {
    setTelegramWebApp("telegram-init-data");
    window.history.pushState({}, "", "/anki/telegram/webapp/cards");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Cards" })).toBeInTheDocument();
    expect(global.fetch).toHaveBeenCalledWith(
      "/anki/api/cards?offset=0&limit=20",
      expect.objectContaining({
        headers: {
          Accept: "application/json",
          "X-Telegram-Init-Data": "telegram-init-data",
        },
      }),
    );
  });
});
