import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

interface TestWebApp {
  initData: string;
  ready?: () => void;
  expand?: () => void;
  themeParams?: Record<string, string>;
  BackButton?: {
    show: () => void;
    hide: () => void;
    onClick: (callback: () => void) => void;
    offClick: (callback: () => void) => void;
  };
}

interface TelegramWindow extends Window {
  Telegram?: {
    WebApp?: TestWebApp;
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
      word_family: [],
      explanation: "example explanation",
      examples: ["e1", "e2", "e3"],
      frequency: 4,
      frequency_note: null,
      is_learning: true,
      srs_state: null,
      srs_due_at: null,
      llm_model: "test-model",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ],
  total: 1,
  offset: 0,
  limit: 50,
};

const settingsPayload = {
  timezone: "Europe/Moscow",
  reminder_hour: 10,
  reminder_anchor: null,
  new_per_day: 5,
  reviews_per_day: 50,
  desired_retention: 0.9,
  learn_threshold: 3,
};

const summaryPayload = {
  due_today: 0,
  new_today: 0,
  est_minutes: 0,
  backlog: 0,
  due_all: 0,
  retention_30d: null,
  learned_total: 0,
  learned_delta_7d: 0,
  streak_days: 0,
  best_streak_days: 0,
  heatmap: Array.from({ length: 98 }, () => 0),
  forecast_tomorrow: 0,
  forecast_week_avg: 0,
  days_away: null,
};

function setTelegramWebApp(initData = "signed-init-data", extra: Partial<TestWebApp> = {}): TestWebApp {
  const webApp: TestWebApp = {
    initData,
    ready: vi.fn(),
    expand: vi.fn(),
    ...extra,
  };
  (window as TelegramWindow).Telegram = { WebApp: webApp };
  return webApp;
}

function rootVar(name: string): string {
  return document.documentElement.style.getPropertyValue(name);
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
    if (url.includes("/api/review/summary")) {
      return jsonResponse(summaryPayload);
    }
    if (url.includes("/api/settings")) {
      return jsonResponse(init?.method === "PUT" ? JSON.parse(String(init.body)) : settingsPayload);
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
    vi.restoreAllMocks();
    document.documentElement.removeAttribute("style");
    window.history.pushState({}, "", "/");
  });

  it("blocks boot outside Telegram", async () => {
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Open the app from Telegram" })).toBeInTheDocument();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("renders tab bar with four tabs", () => {
    setTelegramWebApp();
    window.history.pushState({}, "", "/telegram/webapp/");

    render(<App />);

    const tabs = within(screen.getByRole("navigation", { name: "Sections" })).getAllByRole("button");
    expect(tabs.map((tab) => tab.textContent)).toEqual(["Home", "Review", "Words", "Settings"]);
    expect(screen.getByRole("button", { name: "Home" })).toHaveAttribute("aria-current", "page");
  });

  it("switches view and updates query", async () => {
    setTelegramWebApp();
    window.history.pushState({}, "", "/telegram/webapp/?x=1#tgWebAppData=signed");

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Words" }));

    expect(await screen.findByRole("searchbox", { name: "Search words" })).toBeInTheDocument();
    const params = new URLSearchParams(window.location.search);
    expect(params.get("view")).toBe("cards");
    expect(params.get("x")).toBe("1");
    expect(window.location.pathname).toBe("/telegram/webapp/");
    expect(window.location.hash).toBe("#tgWebAppData=signed");
    expect(screen.getByRole("button", { name: "Words" })).toHaveAttribute("aria-current", "page");
  });

  it("opens review view from ?view=review without tab bar", () => {
    let backCallback: (() => void) | null = null;
    const backButton = {
      show: vi.fn(),
      hide: vi.fn(),
      onClick: vi.fn((callback: () => void) => {
        backCallback = callback;
      }),
      offClick: vi.fn(),
    };
    setTelegramWebApp("signed-init-data", { BackButton: backButton });
    window.history.pushState({}, "", "/telegram/webapp/?view=review");

    render(<App />);

    expect(screen.getByRole("heading", { name: "Review" })).toBeInTheDocument();
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
    expect(backButton.show).toHaveBeenCalled();

    act(() => backCallback?.());

    expect(screen.getByRole("navigation")).toBeInTheDocument();
    expect(new URLSearchParams(window.location.search).get("view")).toBe("home");
    expect(backButton.hide).toHaveBeenCalled();
    expect(backButton.offClick).toHaveBeenCalledWith(backCallback);
  });

  it("falls back without theme params", () => {
    setTelegramWebApp();
    window.history.pushState({}, "", "/telegram/webapp/");

    render(<App />);

    expect(rootVar("--tg-bg")).toBe("");
    expect(screen.getByRole("navigation")).toBeInTheDocument();
  });

  it("applies telegram theme params", () => {
    setTelegramWebApp("signed-init-data", {
      themeParams: { bg_color: "#17212b", button_color: "#5288c1" },
    });
    window.history.pushState({}, "", "/telegram/webapp/");

    render(<App />);

    expect(rootVar("--tg-bg")).toBe("#17212b");
    expect(rootVar("--tg-accent")).toBe("#5288c1");
    expect(rootVar("--tg-text")).toBe("");
  });

  it("renders cards list on the cards view", async () => {
    setTelegramWebApp();
    window.history.pushState({}, "", "/telegram/webapp/?view=cards");

    render(<App />);

    expect(await screen.findByRole("searchbox", { name: "Search words" })).toBeInTheDocument();
    expect((await screen.findAllByText("take off")).length).toBeGreaterThan(0);
  });

  it("renders the cards page at any path behind an external prefix and sends Telegram auth", async () => {
    setTelegramWebApp("telegram-init-data");
    window.history.pushState({}, "", "/anki/telegram/webapp/anything?view=cards");

    render(<App />);

    expect(await screen.findByRole("searchbox", { name: "Search words" })).toBeInTheDocument();
    expect(global.fetch).toHaveBeenCalledWith(
      "/anki/api/cards?offset=0&limit=50",
      expect.objectContaining({
        headers: {
          Accept: "application/json",
          "X-Telegram-Init-Data": "telegram-init-data",
        },
      }),
    );
  });

  describe("device timezone", () => {
    function mockDeviceTimeZone(timeZone: string | undefined): void {
      vi.spyOn(Intl, "DateTimeFormat").mockReturnValue({
        resolvedOptions: () => ({ timeZone }),
      } as Intl.DateTimeFormat);
    }

    function calls(path: string, method = "GET"): RequestInit[] {
      return vi
        .mocked(global.fetch)
        .mock.calls.filter(([url, init]) => String(url).includes(path) && (init?.method ?? "GET") === method)
        .map(([, init]) => init ?? {});
    }

    function renderHome(): void {
      setTelegramWebApp();
      window.history.pushState({}, "", "/telegram/webapp/");
      render(<App />);
    }

    it("saves the device timezone when it differs and refreshes the summary", async () => {
      mockDeviceTimeZone("Asia/Almaty");
      renderHome();

      await waitFor(() => expect(calls("/api/settings", "PUT")).toHaveLength(1));
      expect(JSON.parse(String(calls("/api/settings", "PUT")[0].body))).toEqual({
        ...settingsPayload,
        timezone: "Asia/Almaty",
      });
      // The dashboard refetches its summary once the new timezone is stored.
      await waitFor(() => expect(calls("/api/review/summary")).toHaveLength(2));
    });

    it("leaves settings alone when the timezone matches", async () => {
      mockDeviceTimeZone("Europe/Moscow");
      renderHome();

      await waitFor(() => expect(calls("/api/settings")).toHaveLength(1));
      await act(() => new Promise((resolve) => setTimeout(resolve, 0)));
      expect(calls("/api/settings", "PUT")).toHaveLength(0);
      expect(calls("/api/review/summary")).toHaveLength(1);
    });

    it.each(["", undefined])("skips the sync when the device timezone is %j", async (timeZone) => {
      mockDeviceTimeZone(timeZone);
      renderHome();

      await waitFor(() => expect(calls("/api/review/summary").length).toBeGreaterThan(0));
      expect(calls("/api/settings")).toHaveLength(0);
      expect(calls("/api/settings", "PUT")).toHaveLength(0);
    });
  });
});
