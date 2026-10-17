import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getReviewSummary } from "../api/client";
import type { ReviewSummary } from "../api/types";
import { HomeView } from "./HomeView";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return { ...actual, getReviewSummary: vi.fn() };
});

const mockedGetReviewSummary = vi.mocked(getReviewSummary);

function summary(overrides: Partial<ReviewSummary> = {}): ReviewSummary {
  return {
    due_today: 12,
    new_today: 5,
    est_minutes: 6,
    backlog: 3,
    due_all: 15,
    retention_30d: 0.912,
    learned_total: 140,
    learned_delta_7d: 9,
    streak_days: 4,
    best_streak_days: 11,
    heatmap: Array.from({ length: 98 }, (_, i) => (i % 3 === 0 ? 0 : i % 9)),
    forecast_tomorrow: 14,
    forecast_week_avg: 11,
    days_away: 0,
    ...overrides,
  };
}

function renderHome(data: ReviewSummary): ReturnType<typeof vi.fn> {
  mockedGetReviewSummary.mockResolvedValue(data);
  const onStart = vi.fn();
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <HomeView onStart={onStart} />
    </QueryClientProvider>,
  );
  return onStart;
}

describe("HomeView", () => {
  beforeEach(() => {
    mockedGetReviewSummary.mockReset();
  });

  it("shows goal and minutes", async () => {
    const onStart = renderHome(summary());

    expect(await screen.findByText("Цель на сегодня: 17 карточек · ~6 мин")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Начать" })).toHaveClass("primary-button");
    expect(screen.getByText("91%")).toBeInTheDocument();
    expect(screen.getByText("цель 90%")).toBeInTheDocument();
    expect(screen.getByText("140")).toBeInTheDocument();
    expect(screen.getByText("+9 за неделю")).toBeInTheDocument();
    expect(screen.getByText("серия 4 дн. · лучшая 11")).toBeInTheDocument();
    expect(screen.getByText("Завтра ~14 · неделя ~11/день")).toBeInTheDocument();
    expect(screen.getByText("Отложено: 3")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Начать" }));
    expect(onStart).toHaveBeenLastCalledWith({});
    fireEvent.click(screen.getByRole("button", { name: "Быстро: 5 карточек" }));
    expect(onStart).toHaveBeenLastCalledWith({ capCards: 5 });
  });

  it("captions the heatmap and lays rows out Monday to Sunday", async () => {
    // 03:00 on Thursday 2026-10-22 still belongs to Wednesday's study day.
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 9, 22, 3, 0));
    renderHome(summary());

    expect(await screen.findByText("Активность")).toBeInTheDocument();
    const heatmap = screen.getByRole("img", { name: "Активность за 14 недель" });
    // Today (Wednesday, row 3) is the last of 98 cells, so the first one is a Thursday (row 4).
    expect((heatmap.children[0] as HTMLElement).style.gridRowStart).toBe("4");
    expect((heatmap.children[1] as HTMLElement).style.gridRowStart).toBe("");
    vi.useRealTimers();
  });

  it("hides streak below three days", async () => {
    renderHome(summary({ streak_days: 2, backlog: 0, retention_30d: null, due_today: 1, new_today: 0 }));

    expect(await screen.findByText("Цель на сегодня: 1 карточка · ~6 мин")).toBeInTheDocument();
    expect(screen.queryByText(/серия/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Отложено/)).not.toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("heatmap renders 98 cells without red", async () => {
    const data = summary();
    renderHome(data);

    const heatmap = await screen.findByRole("img", { name: "Активность за 14 недель" });
    const cells = Array.from(heatmap.children) as HTMLElement[];
    expect(cells).toHaveLength(98);
    cells.forEach((cell, i) => {
      const count = data.heatmap[i];
      // Missed days are neutral (level 0); only one accent hue at two strengths otherwise.
      expect(cell.dataset.level).toBe(count === 0 ? "0" : count < 5 ? "1" : "2");
      expect(cell.className).toBe("heatmap-cell");
    });
  });

  it("shows welcome back after three days away", async () => {
    const onStart = renderHome(
      summary({ days_away: 3, due_today: 50, new_today: 0, est_minutes: 27, due_all: 60 }),
    );

    expect(await screen.findByRole("heading", { name: "С возвращением" })).toBeInTheDocument();
    expect(screen.getByText("Как сегодня?")).toBeInTheDocument();
    expect(screen.queryByText(/Цель на сегодня/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Начать" })).not.toBeInTheDocument();

    const fiveMinutes = screen.getByRole("button", { name: "5 минут" });
    expect(fiveMinutes).toHaveClass("primary-button");
    fireEvent.click(fiveMinutes);
    // 27 min / 50 cards = 0.54 min per card -> 5 / 0.54 = 9.3, rounded up to 10 cards.
    expect(onStart).toHaveBeenLastCalledWith({ capCards: 10 });

    fireEvent.click(screen.getByRole("button", { name: "Обычная сессия" }));
    expect(onStart).toHaveBeenLastCalledWith({});
  });

  it("all-at-once starts with includeBacklog", async () => {
    const onStart = renderHome(summary({ days_away: 7, due_all: 60, backlog: 10 }));

    fireEvent.click(await screen.findByRole("button", { name: "Всё сразу (60)" }));

    expect(onStart).toHaveBeenLastCalledWith({ includeBacklog: true });
  });
});
