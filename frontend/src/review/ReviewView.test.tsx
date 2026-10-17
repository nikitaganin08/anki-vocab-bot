import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, checkAnswer, getReviewSession, getReviewSummary, gradeCard } from "../api/client";
import type { Card, CheckResponse, ReviewSessionItem, ReviewSummary } from "../api/types";
import type { ReviewMode } from "../home/HomeView";
import { formatInterval } from "./AnswerCard";
import { ReviewView } from "./ReviewView";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    getReviewSession: vi.fn(),
    getReviewSummary: vi.fn(),
    checkAnswer: vi.fn(),
    gradeCard: vi.fn(),
  };
});

const mockedSession = vi.mocked(getReviewSession);
const mockedSummary = vi.mocked(getReviewSummary);
const mockedCheck = vi.mocked(checkAnswer);
const mockedGrade = vi.mocked(gradeCard);

function card(id: number, word: string): Card {
  return {
    id,
    source_text: word,
    source_language: "en",
    entry_type: "word",
    canonical_text: word,
    canonical_text_normalized: word,
    transcription: "/ɡɪv/",
    translation_variants: ["давать", "дарить"],
    word_family: [{ word: "giver", part_of_speech: "noun", translation: "даритель" }],
    explanation: "To hand something to someone.",
    examples: ["She gave me a book.", "Give it back."],
    chunks: [{ text: `${word} up`, target: word, translation: "сдаться" }],
    frequency: 8,
    frequency_note: null,
    is_learning: true,
    anki_sync_status: "pending",
    anki_note_id: null,
    anki_sync_error: null,
    llm_model: "test-model",
    created_at: "2026-10-01T00:00:00Z",
    updated_at: "2026-10-01T00:00:00Z",
  };
}

function item(
  id: number,
  word: string,
  masked: string,
  overrides: Partial<ReviewSessionItem> = {},
): ReviewSessionItem {
  return {
    card: card(id, word),
    intro: false,
    prompt: {
      kind: "chunk",
      index: 0,
      masked,
      hint_translation: "сдаться",
    },
    srs_due_at: "2026-10-17T08:00:00.123456Z",
    ...overrides,
  };
}

function summary(overrides: Partial<ReviewSummary> = {}): ReviewSummary {
  return {
    due_today: 8,
    new_today: 2,
    est_minutes: 5,
    backlog: 0,
    due_all: 8,
    retention_30d: 0.9,
    learned_total: 10,
    learned_delta_7d: 1,
    streak_days: 0,
    best_streak_days: 0,
    heatmap: Array.from({ length: 98 }, () => 0),
    forecast_tomorrow: 14,
    forecast_week_avg: 9,
    days_away: 0,
    ...overrides,
  };
}

function checked(overrides: Partial<CheckResponse> = {}): CheckResponse {
  return {
    verdict: "correct",
    expected: "give",
    auto_rating: 3,
    intervals: { "1": 30, "2": 360, "3": 600, "4": 345600 },
    ...overrides,
  };
}

function renderReview(mode: ReviewMode = {}): ReturnType<typeof vi.fn> {
  const onExit = vi.fn();
  render(<ReviewView mode={mode} onExit={onExit} />);
  return onExit;
}

// Clicks that start a request: act flushes the mocked response and the resulting state.
async function press(element: HTMLElement): Promise<void> {
  await act(async () => {
    fireEvent.click(element);
  });
}

async function answer(typed: string): Promise<void> {
  fireEvent.change(await screen.findByRole("textbox", { name: "Answer" }), {
    target: { value: typed },
  });
  await press(screen.getByRole("button", { name: "Check" }));
}

async function grade(label: RegExp): Promise<void> {
  await press(await screen.findByRole("button", { name: label }));
}

describe("ReviewView", () => {
  beforeEach(() => {
    mockedSession.mockReset();
    mockedSummary.mockReset().mockResolvedValue(summary());
    mockedCheck.mockReset().mockResolvedValue(checked());
    mockedGrade.mockReset().mockResolvedValue({
      srs_due_at: "2026-10-18T08:00:00Z",
      srs_state: "review",
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("intro then typed question later in round", async () => {
    mockedSession.mockResolvedValue([
      item(1, "give", "___ up", { intro: true, srs_due_at: null }),
      item(2, "take", "___ off"),
      item(3, "make", "___ sense"),
    ]);
    renderReview();

    expect(await screen.findByText("New word")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "give" })).toBeInTheDocument();
    expect(screen.getByText("давать, дарить")).toBeInTheDocument();
    expect(screen.getByText("To hand something to someone.")).toBeInTheDocument();
    expect(screen.getByText("give up")).toBeInTheDocument();
    expect(screen.getByText("She gave me a book.")).toBeInTheDocument();
    expect(screen.getByText("giver (noun) — даритель")).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    const remembered = screen.getByRole("button", { name: "Got it" });
    expect(remembered).toHaveClass("primary-button");
    fireEvent.click(remembered);

    expect(await screen.findByText("___ off")).toBeInTheDocument();
    expect(screen.getByText("Round 1 · 1 of 3")).toBeInTheDocument();
    await answer("take");
    await grade(/^Good/);

    // The intro card comes back as a typed question two positions after its intro.
    expect(await screen.findByText("___ up")).toBeInTheDocument();
    expect(screen.getByText("Round 1 · 2 of 3")).toBeInTheDocument();
    await answer("give");
    await grade(/^Good/);
    expect(mockedGrade).toHaveBeenLastCalledWith(1, expect.objectContaining({ expected_due_at: null }));

    expect(await screen.findByText("___ sense")).toBeInTheDocument();
    expect(screen.getByText("Round 1 · 3 of 3")).toBeInTheDocument();
  });

  it("check shows diff and highlights auto rating", async () => {
    mockedSession.mockResolvedValue([item(1, "give", "___ up")]);
    mockedCheck.mockResolvedValue(checked({ verdict: "wrong", auto_rating: 1 }));
    renderReview();

    expect(await screen.findByText("сдаться")).toBeInTheDocument();
    expect(screen.getByText("~5 min")).toBeInTheDocument();
    await answer("gve");

    const diff = (await screen.findByText(/^You:/)).closest("p");
    expect(diff).toHaveTextContent("You: gve → correct: give");
    expect(screen.getByText("gve")).toHaveClass("verdict-typed");
    expect(screen.getByText("gve").tagName).toBe("S");
    expect(screen.getByText("give", { selector: "span" })).toHaveClass("verdict-expected");
    expect(mockedCheck).toHaveBeenCalledWith(1, {
      typed: "gve",
      prompt_kind: "chunk",
      prompt_index: 0,
      hint_used: false,
    });

    const again = screen.getByRole("button", { name: /^Again/ });
    expect(again).toHaveClass("primary-button");
    expect(again).toHaveTextContent("<1m");
    expect(screen.getByRole("button", { name: /^Hard/ })).toHaveClass("secondary-button");
    expect(screen.getByRole("button", { name: /^Good/ })).toHaveTextContent("10m");
    expect(screen.getByRole("button", { name: /^Easy/ })).toHaveTextContent("4d");
    expect(screen.getByText("Rating picked automatically — you can change it")).toBeInTheDocument();
    expect(screen.getByText("Usage")).toBeInTheDocument();
    expect(screen.getByText("giver (noun) — даритель")).toBeInTheDocument();
    expect(screen.getByText("To hand something to someone.")).toBeInTheDocument();
  });

  it("grade advances to next card", async () => {
    mockedSession.mockResolvedValue([item(1, "give", "___ up"), item(2, "take", "___ off")]);
    renderReview();

    await answer("give");
    expect(await screen.findByText("✓ correct")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "My answer was right" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Good/ })).toHaveClass("primary-button");
    await grade(/^Good/);

    expect(mockedGrade).toHaveBeenCalledWith(
      1,
      expect.objectContaining({
        rating: 3,
        auto_rating: 3,
        overridden: false,
        typed: "give",
        prompt_kind: "chunk",
        prompt_index: 0,
        verdict: "correct",
        hint_used: false,
      }),
    );
    expect(await screen.findByText("___ off")).toBeInTheDocument();
    expect(screen.getByText("Round 1 · 2 of 2")).toBeInTheDocument();
  });

  it("sends srs_due_at verbatim", async () => {
    const dueAt = "2026-10-17T08:00:00.123456+00:00";
    mockedSession.mockResolvedValue([item(1, "give", "___ up", { srs_due_at: dueAt })]);
    renderReview();

    await answer("give");
    await grade(/^Easy/);

    const body = mockedGrade.mock.calls[0][1];
    expect(body.expected_due_at).toBe(dueAt);
    expect(body.rating).toBe(4);
    expect(body.response_ms).toBeGreaterThanOrEqual(0);
  });

  it("refetches session on 409", async () => {
    mockedSession
      .mockResolvedValueOnce([item(1, "give", "___ up"), item(2, "take", "___ off")])
      .mockResolvedValueOnce([item(2, "take", "___ off")]);
    mockedGrade.mockRejectedValueOnce(new ApiError("card 1 was already graded", 409));
    renderReview({ includeBacklog: true });

    await answer("give");
    await grade(/^Good/);

    expect(await screen.findByText("___ off")).toBeInTheDocument();
    expect(screen.getByText("Round 1 · 1 of 1")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(mockedSession).toHaveBeenCalledTimes(2);
    expect(mockedSession).toHaveBeenLastCalledWith({ size: 10, includeBacklog: true });
  });

  it("empty session shows done screen", async () => {
    mockedSession.mockResolvedValue([]);
    const onExit = renderReview();

    expect(await screen.findByRole("heading", { name: "Done for today" })).toBeInTheDocument();
    expect(screen.getByText("Tomorrow ~14 cards")).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    const close = screen.getByRole("button", { name: "Close" });
    expect(close).toHaveClass("primary-button");
    expect(screen.getAllByRole("button")).toHaveLength(1);
    fireEvent.click(close);
    expect(onExit).toHaveBeenCalled();
  });

  it("round end shows progress to goal", async () => {
    mockedSession
      .mockResolvedValueOnce([item(1, "give", "___ up")])
      .mockResolvedValueOnce([item(2, "take", "___ off")]);
    const heatmap = Array.from({ length: 98 }, (_, i) => (i === 97 ? 12 : 3));
    mockedSummary
      .mockResolvedValueOnce(summary())
      .mockResolvedValueOnce(summary({ heatmap, due_today: 6, new_today: 2, est_minutes: 4 }));
    const onExit = renderReview();

    await answer("give");
    await grade(/^Good/);

    expect(await screen.findByRole("heading", { name: "✓ Round complete" })).toBeInTheDocument();
    expect(screen.getByText("Today 12 of 20")).toBeInTheDocument();
    const progress = screen.getByRole("progressbar");
    expect(progress).toHaveAttribute("value", "12");
    expect(progress).toHaveAttribute("max", "20");
    expect(screen.getByText("~4 min left")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Done for today" })).toHaveClass("secondary-button");
    expect(mockedSession).toHaveBeenLastCalledWith({ size: 10, includeBacklog: false });

    fireEvent.click(screen.getByRole("button", { name: "Another round" }));
    expect(await screen.findByText("___ off")).toBeInTheDocument();
    expect(screen.getByText("Round 2 · 1 of 1")).toBeInTheDocument();
    expect(onExit).not.toHaveBeenCalled();
  });

  it("stops after capCards graded cards", async () => {
    mockedSession
      .mockResolvedValueOnce([item(1, "give", "___ up"), item(2, "take", "___ off")])
      .mockResolvedValueOnce([item(2, "take", "___ off")]);
    const onExit = renderReview({ capCards: 1 });

    await answer("give");
    await grade(/^Good/);

    expect(await screen.findByRole("heading", { name: "✓ Round complete" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Done for today" }));
    expect(onExit).toHaveBeenCalled();
  });

  it("capped session asks only for what is left of the cap", async () => {
    mockedSession
      .mockResolvedValueOnce([item(1, "give", "___ up"), item(2, "take", "___ off")])
      .mockResolvedValueOnce([item(3, "make", "___ sense")])
      .mockResolvedValueOnce([item(4, "keep", "___ calm")]);
    renderReview({ capCards: 3 });

    expect(await screen.findByText("Round 1 · 1 of 2")).toBeInTheDocument();
    expect(mockedSession).toHaveBeenLastCalledWith({ size: 3, includeBacklog: false });
    await answer("give");
    await grade(/^Good/);
    await answer("take");
    await grade(/^Good/);

    expect(await screen.findByRole("heading", { name: "✓ Round complete" })).toBeInTheDocument();
    expect(mockedSession).toHaveBeenLastCalledWith({ size: 1, includeBacklog: false });
    fireEvent.click(screen.getByRole("button", { name: "Another round" }));
    expect(await screen.findByText("Round 2 · 1 of 1")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("max", "1");
    await answer("make");
    await grade(/^Good/);

    // The cap is reached: the round ends, and any further round is a regular one.
    expect(await screen.findByRole("heading", { name: "✓ Round complete" })).toBeInTheDocument();
    expect(mockedSession).toHaveBeenLastCalledWith({ size: 10, includeBacklog: false });
  });

  it("override grades good", async () => {
    mockedSession.mockResolvedValue([item(1, "give", "___ up")]);
    mockedCheck.mockResolvedValue(checked({ verdict: "wrong", auto_rating: 1 }));
    renderReview();

    await answer("giv");
    await press(await screen.findByRole("button", { name: "My answer was right" }));

    expect(mockedGrade).toHaveBeenCalledWith(
      1,
      expect.objectContaining({ rating: 3, auto_rating: 1, overridden: true, verdict: "wrong" }),
    );
  });

  it("explanation on demand marks hint_used", async () => {
    mockedSession.mockResolvedValue([item(1, "give", "___ up")]);
    mockedCheck.mockResolvedValue(checked({ auto_rating: 2 }));
    renderReview();

    const input = await screen.findByRole("textbox", { name: "Answer" });
    expect(input).toHaveAttribute("maxlength", "200");
    expect(input).toHaveAttribute("placeholder", "Type the missing part");
    expect(screen.queryByText(/first letter/i)).not.toBeInTheDocument();
    expect(screen.queryByText("g___")).not.toBeInTheDocument();
    expect(screen.queryByText("To hand something to someone.")).not.toBeInTheDocument();
    const reveal = screen.getByRole("button", { name: "What's this word?" });
    reveal.focus();
    fireEvent.click(reveal);
    expect(screen.getByText("To hand something to someone.")).toBeInTheDocument();
    expect(input).toHaveFocus();
    await answer("give");
    expect(mockedCheck).toHaveBeenCalledWith(1, expect.objectContaining({ hint_used: true }));

    const hard = await screen.findByRole("button", { name: /^Hard/ });
    expect(hard).toHaveClass("primary-button");
    await press(hard);
    expect(mockedGrade).toHaveBeenCalledWith(
      1,
      expect.objectContaining({ rating: 2, auto_rating: 2, hint_used: true }),
    );
  });

  it("sends cyrillic answer unchanged", async () => {
    mockedSession.mockResolvedValue([item(1, "give", "___ up")]);
    renderReview();

    const input = await screen.findByRole("textbox", { name: "Answer" });
    expect(input).toHaveFocus();
    expect(input).toHaveAttribute("autocomplete", "off");
    expect(input).toHaveAttribute("autocapitalize", "none");
    expect(input).toHaveAttribute("spellcheck", "false");
    fireEvent.change(input, { target: { value: "пшму" } });
    // Enter submits the form.
    await act(async () => {
      fireEvent.submit(input.closest("form")!);
    });

    expect(mockedCheck).toHaveBeenCalledWith(1, expect.objectContaining({ typed: "пшму" }));
    await grade(/^Good/);
    expect(mockedGrade).toHaveBeenCalledWith(1, expect.objectContaining({ typed: "пшму" }));
  });

  it("full card order: translations, explanation, usage, example, one line per family form", async () => {
    const family = [
      { word: "distinguishable", part_of_speech: "adjective", translation: "различимый" },
      { word: "distinction", part_of_speech: "noun", translation: "различие" },
    ];
    const reviewItem = item(1, "distinguish", "___ up");
    reviewItem.card.word_family = family;
    mockedSession.mockResolvedValue([reviewItem]);
    renderReview();

    await answer("distinguish");
    const panel = (await screen.findByRole("heading", { name: "distinguish" })).closest("div.review-card");
    const text = panel!.textContent!;
    const order = ["давать, дарить", "To hand something to someone.", "Usage", "She gave me a book.", "distinguishable"];
    const positions = order.map((part) => text.indexOf(part));
    expect(positions.every((pos) => pos >= 0)).toBe(true);
    expect([...positions].sort((a, b) => a - b)).toEqual(positions);

    const lines = within(panel as HTMLElement).getAllByRole("listitem").slice(-2);
    expect(lines.map((line) => line.textContent)).toEqual([
      "distinguishable (adjective) — различимый",
      "distinction (noun) — различие",
    ]);
    expect(text).not.toContain("·");
  });

  it("asks for English on a translation prompt", async () => {
    mockedSession.mockResolvedValue([
      item(1, "give", "давать", { prompt: { kind: "translation", index: 0, masked: "давать", hint_translation: "" } }),
    ]);
    renderReview();

    expect(await screen.findByRole("textbox", { name: "Answer" })).toHaveAttribute("placeholder", "Type in English");
  });
});

interface TelegramWindow extends Window {
  Telegram?: { WebApp?: { initData: string } };
}

// pronounce() caches object URLs per card id for the page's lifetime: each test uses its own id.
describe("pronunciation", () => {
  const fetchMock = vi.fn();
  const playMock = vi.fn();
  const audioSources: string[] = [];
  const createObjectURL = URL.createObjectURL;

  beforeEach(() => {
    mockedSummary.mockReset().mockResolvedValue(summary());
    (window as TelegramWindow).Telegram = { WebApp: { initData: "signed-init-data" } };
    fetchMock.mockReset().mockResolvedValue(new Response("mp3", { headers: { "Content-Type": "audio/mpeg" } }));
    playMock.mockReset().mockResolvedValue(undefined);
    audioSources.length = 0;
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal(
      "Audio",
      class {
        play = playMock;
        constructor(src: string) {
          audioSources.push(src);
        }
      },
    );
    URL.createObjectURL = vi.fn(() => "blob:give-audio");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    URL.createObjectURL = createObjectURL;
    delete (window as TelegramWindow).Telegram;
  });

  function renderIntro(cardId: number): void {
    mockedSession.mockResolvedValue([item(cardId, "give", "___ up", { intro: true, srs_due_at: null })]);
    renderReview();
  }

  it("shows the speaker without speechSynthesis and plays cached server audio on tap only", async () => {
    expect("speechSynthesis" in window).toBe(false);
    renderIntro(21);

    const speaker = await screen.findByRole("button", { name: "Play pronunciation" });
    // No autoplay.
    expect(fetchMock).not.toHaveBeenCalled();
    expect(playMock).not.toHaveBeenCalled();

    fireEvent.click(speaker);
    await waitFor(() => expect(playMock).toHaveBeenCalledTimes(1));
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/cards/21/audio",
      expect.objectContaining({
        headers: expect.objectContaining({ "X-Telegram-Init-Data": "signed-init-data" }),
      }),
    );

    fireEvent.click(speaker);
    await waitFor(() => expect(playMock).toHaveBeenCalledTimes(2));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(audioSources).toEqual(["blob:give-audio", "blob:give-audio"]);
  });

  it("falls back to speechSynthesis when the audio request fails", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ detail: "boom" }), { status: 502 }));
    const speak = vi.fn();
    vi.stubGlobal("speechSynthesis", { speak, cancel: vi.fn() });
    vi.stubGlobal(
      "SpeechSynthesisUtterance",
      class {
        lang = "";
        constructor(readonly text: string) {}
      },
    );
    renderIntro(22);

    fireEvent.click(await screen.findByRole("button", { name: "Play pronunciation" }));

    await waitFor(() =>
      expect(speak).toHaveBeenCalledWith(expect.objectContaining({ text: "give", lang: "en-US" })),
    );
    expect(playMock).not.toHaveBeenCalled();
  });
});

describe("formatInterval", () => {
  it("rounds before picking the unit", () => {
    expect(formatInterval(30)).toBe("<1m");
    expect(formatInterval(600)).toBe("10m");
    expect(formatInterval(3570)).toBe("1h");
    expect(formatInterval(43200)).toBe("12h");
    expect(formatInterval(86000)).toBe("1d");
    expect(formatInterval(345600)).toBe("4d");
  });
});
