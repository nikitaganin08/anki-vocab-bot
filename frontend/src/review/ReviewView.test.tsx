import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, checkAnswer, getReviewSession, getReviewSummary, gradeCard } from "../api/client";
import type { Card, CheckResponse, ReviewSessionItem, ReviewSummary } from "../api/types";
import type { ReviewMode } from "../home/HomeView";
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
      expected_length: word.length,
      hint_letter: word[0],
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
  fireEvent.change(await screen.findByRole("textbox", { name: "Ответ" }), {
    target: { value: typed },
  });
  await press(screen.getByRole("button", { name: "Проверить" }));
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

    expect(await screen.findByText("Новое")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "give" })).toBeInTheDocument();
    expect(screen.getByText("давать, дарить")).toBeInTheDocument();
    expect(screen.getByText("give up")).toBeInTheDocument();
    expect(screen.getByText("She gave me a book.")).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    const remembered = screen.getByRole("button", { name: "Запомнил" });
    expect(remembered).toHaveClass("primary-button");
    fireEvent.click(remembered);

    expect(await screen.findByText("___ off")).toBeInTheDocument();
    expect(screen.getByText("Раунд 1 · 1 из 3")).toBeInTheDocument();
    await answer("take");
    await grade(/^Хорошо/);

    // The intro card comes back as a typed question two positions after its intro.
    expect(await screen.findByText("___ up")).toBeInTheDocument();
    expect(screen.getByText("Раунд 1 · 2 из 3")).toBeInTheDocument();
    await answer("give");
    await grade(/^Хорошо/);
    expect(mockedGrade).toHaveBeenLastCalledWith(1, expect.objectContaining({ expected_due_at: null }));

    expect(await screen.findByText("___ sense")).toBeInTheDocument();
    expect(screen.getByText("Раунд 1 · 3 из 3")).toBeInTheDocument();
  });

  it("check shows diff and highlights auto rating", async () => {
    mockedSession.mockResolvedValue([item(1, "give", "___ up")]);
    mockedCheck.mockResolvedValue(checked({ verdict: "wrong", auto_rating: 1 }));
    renderReview();

    expect(await screen.findByText("сдаться")).toBeInTheDocument();
    expect(screen.getByText("~5 мин")).toBeInTheDocument();
    await answer("gve");

    const diff = (await screen.findByText(/^Ты:/)).closest("p");
    expect(diff).toHaveTextContent("Ты: gve → верно: give");
    expect(mockedCheck).toHaveBeenCalledWith(1, {
      typed: "gve",
      prompt_kind: "chunk",
      prompt_index: 0,
      hint_used: false,
    });

    const again = screen.getByRole("button", { name: /^Снова/ });
    expect(again).toHaveClass("primary-button");
    expect(again).toHaveTextContent("<1 м");
    expect(screen.getByRole("button", { name: /^Трудно/ })).toHaveClass("secondary-button");
    expect(screen.getByRole("button", { name: /^Хорошо/ })).toHaveTextContent("10 м");
    expect(screen.getByRole("button", { name: /^Легко/ })).toHaveTextContent("4 д");
    expect(screen.getByText("Оценка выбрана автоматически, можно поменять")).toBeInTheDocument();
    expect(screen.getByText("Как используется")).toBeInTheDocument();
    expect(screen.getByText(/giver/)).toBeInTheDocument();
    expect(screen.getByText("To hand something to someone.")).toBeInTheDocument();
  });

  it("grade advances to next card", async () => {
    mockedSession.mockResolvedValue([item(1, "give", "___ up"), item(2, "take", "___ off")]);
    renderReview();

    await answer("give");
    expect(await screen.findByText("✓ верно")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Мой ответ верный" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Хорошо/ })).toHaveClass("primary-button");
    await grade(/^Хорошо/);

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
    expect(screen.getByText("Раунд 1 · 2 из 2")).toBeInTheDocument();
  });

  it("sends srs_due_at verbatim", async () => {
    const dueAt = "2026-10-17T08:00:00.123456+00:00";
    mockedSession.mockResolvedValue([item(1, "give", "___ up", { srs_due_at: dueAt })]);
    renderReview();

    await answer("give");
    await grade(/^Легко/);

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
    await grade(/^Хорошо/);

    expect(await screen.findByText("___ off")).toBeInTheDocument();
    expect(screen.getByText("Раунд 1 · 1 из 1")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(mockedSession).toHaveBeenCalledTimes(2);
    expect(mockedSession).toHaveBeenLastCalledWith({ size: 10, includeBacklog: true });
  });

  it("empty session shows done screen", async () => {
    mockedSession.mockResolvedValue([]);
    const onExit = renderReview();

    expect(await screen.findByRole("heading", { name: "Готово на сегодня" })).toBeInTheDocument();
    expect(screen.getByText("Завтра ~14 карточек")).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    const close = screen.getByRole("button", { name: "Закрыть" });
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
    const onExit = renderReview({ size: 5 });

    await answer("give");
    await grade(/^Хорошо/);

    expect(await screen.findByRole("heading", { name: "✓ Раунд готов" })).toBeInTheDocument();
    expect(screen.getByText("Сегодня 12 из 20")).toBeInTheDocument();
    const progress = screen.getByRole("progressbar");
    expect(progress).toHaveAttribute("value", "12");
    expect(progress).toHaveAttribute("max", "20");
    expect(screen.getByText("Осталось ~4 мин")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "На сегодня хватит" })).toHaveClass("secondary-button");
    expect(mockedSession).toHaveBeenLastCalledWith({ size: 5, includeBacklog: false });

    fireEvent.click(screen.getByRole("button", { name: "Ещё раунд" }));
    expect(await screen.findByText("___ off")).toBeInTheDocument();
    expect(screen.getByText("Раунд 2 · 1 из 1")).toBeInTheDocument();
    expect(onExit).not.toHaveBeenCalled();
  });

  it("stops after capCards graded cards", async () => {
    mockedSession
      .mockResolvedValueOnce([item(1, "give", "___ up"), item(2, "take", "___ off")])
      .mockResolvedValueOnce([item(2, "take", "___ off")]);
    const onExit = renderReview({ capCards: 1 });

    await answer("give");
    await grade(/^Хорошо/);

    expect(await screen.findByRole("heading", { name: "✓ Раунд готов" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "На сегодня хватит" }));
    expect(onExit).toHaveBeenCalled();
  });

  it("override grades good", async () => {
    mockedSession.mockResolvedValue([item(1, "give", "___ up")]);
    mockedCheck.mockResolvedValue(checked({ verdict: "wrong", auto_rating: 1 }));
    renderReview();

    await answer("giv");
    await press(await screen.findByRole("button", { name: "Мой ответ верный" }));

    expect(mockedGrade).toHaveBeenCalledWith(
      1,
      expect.objectContaining({ rating: 3, auto_rating: 1, overridden: true, verdict: "wrong" }),
    );
  });

  it("hint reveals first letter and marks hint_used", async () => {
    mockedSession.mockResolvedValue([item(1, "give", "___ up")]);
    mockedCheck.mockResolvedValue(checked({ auto_rating: 2 }));
    renderReview();

    fireEvent.click(await screen.findByRole("button", { name: "Подсказка: первая буква" }));
    expect(screen.getByText("g___")).toBeInTheDocument();
    await answer("give");
    expect(mockedCheck).toHaveBeenCalledWith(1, expect.objectContaining({ hint_used: true }));

    const hard = await screen.findByRole("button", { name: /^Трудно/ });
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

    const input = await screen.findByRole("textbox", { name: "Ответ" });
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
    await grade(/^Хорошо/);
    expect(mockedGrade).toHaveBeenCalledWith(1, expect.objectContaining({ typed: "пшму" }));
  });

  it("hides audio without speechSynthesis", async () => {
    mockedSession.mockResolvedValue([item(1, "give", "___ up", { intro: true, srs_due_at: null })]);
    renderReview();

    expect(await screen.findByRole("heading", { name: "give" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Произнести" })).not.toBeInTheDocument();
    cleanup();

    const speak = vi.fn();
    vi.stubGlobal("speechSynthesis", { speak, cancel: vi.fn() });
    vi.stubGlobal(
      "SpeechSynthesisUtterance",
      class {
        lang = "";
        constructor(readonly text: string) {}
      },
    );
    renderReview();

    fireEvent.click(await screen.findByRole("button", { name: "Произнести" }));
    expect(speak).toHaveBeenCalledWith(expect.objectContaining({ text: "give", lang: "en-US" }));
  });
});
