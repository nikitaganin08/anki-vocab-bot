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
    done_today: 0,
    due_today: 12,
    new_today: 5,
    est_minutes: 6,
    backlog: 3,
    due_all: 15,
    retention_30d: 0.912,
    hard_share_30d: 0.18,
    again_share_30d: 0.088,
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

    expect(await screen.findByText("0 of 17 done today")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start" })).toHaveClass("primary-button");
    expect(screen.getByText("91%")).toBeInTheDocument();
    expect(screen.getByText("goal 90%")).toBeInTheDocument();
    expect(screen.getByText("140")).toBeInTheDocument();
    expect(screen.getByText("+9 this week")).toBeInTheDocument();
    expect(screen.getByText("streak 4 days · best 11")).toBeInTheDocument();
    expect(screen.getByText("Tomorrow ~14 · week ~11/day")).toBeInTheDocument();
    expect(screen.getByText("Postponed: 3")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Start" }));
    expect(onStart).toHaveBeenLastCalledWith({});
    fireEvent.click(screen.getByRole("button", { name: "Quick: 5 cards" }));
    expect(onStart).toHaveBeenLastCalledWith({ capCards: 5 });
  });

  it("shows the goal as a progress bar with left and minutes on one row", async () => {
    renderHome(summary({ done_today: 4, due_today: 6, new_today: 2 }));

    expect(await screen.findByText("4 of 12 done today")).toBeInTheDocument();
    const bar = screen.getByRole("progressbar", { name: "Today's progress" });
    expect(bar).toHaveAttribute("value", "4");
    expect(bar).toHaveAttribute("max", "12");
    const left = screen.getByText("8 left");
    const minutes = screen.getByText("~6 min");
    expect(left.parentElement).toBe(minutes.parentElement);
    expect(left.parentElement).toHaveTextContent("8 left~6 min");
    expect(screen.queryByText(/·/, { selector: ".home-card *" })).not.toBeInTheDocument();
  });

  it("says done for today when nothing is done or due", async () => {
    renderHome(summary({ done_today: 0, due_today: 0, new_today: 0 }));

    expect(await screen.findByRole("heading", { name: "Done for today" })).toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  });

  it("says all done instead of 0 left when everything is finished", async () => {
    renderHome(summary({ done_today: 12, due_today: 0, new_today: 0 }));

    expect(await screen.findByRole("heading", { name: "12 of 12 done today" })).toBeInTheDocument();
    expect(screen.getByText("All done")).toBeInTheDocument();
    expect(screen.queryByText(/left/)).not.toBeInTheDocument();
    expect(screen.queryByText(/~\d+ min/)).not.toBeInTheDocument();
  });

  it("shows the Hard and Again shares under the retention goal", async () => {
    renderHome(summary());

    expect(await screen.findByText("91%")).toBeInTheDocument();
    expect(screen.getByText("Hard 18% · Again 9%")).toBeInTheDocument();
  });

  it("captions the heatmap and lays rows out Monday to Sunday", async () => {
    // 00:30 on Thursday 2026-10-22 already belongs to Thursday's study day (starts at midnight).
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 9, 22, 0, 30));
    renderHome(summary());

    expect(await screen.findByText("Activity")).toBeInTheDocument();
    const heatmap = screen.getByRole("img", { name: "Activity over 14 weeks" });
    // Today (Thursday, row 4) is the last of 98 cells, so the first one is a Friday (row 5).
    expect((heatmap.children[0] as HTMLElement).style.gridRowStart).toBe("5");
    expect((heatmap.children[1] as HTMLElement).style.gridRowStart).toBe("");
    vi.useRealTimers();
  });

  it("hides streak below three days", async () => {
    renderHome(
      summary({
        streak_days: 2,
        backlog: 0,
        retention_30d: null,
        hard_share_30d: null,
        again_share_30d: null,
        due_today: 1,
        new_today: 0,
      }),
    );

    expect(await screen.findByText("0 of 1 done today")).toBeInTheDocument();
    expect(screen.queryByText(/streak/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Hard \d+%/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Postponed/)).not.toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("heatmap renders 98 cells without red", async () => {
    const data = summary();
    renderHome(data);

    const heatmap = await screen.findByRole("img", { name: "Activity over 14 weeks" });
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

    expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
    expect(screen.getByText("How about today?")).toBeInTheDocument();
    expect(screen.queryByText(/done today/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Start" })).not.toBeInTheDocument();

    const fiveMinutes = screen.getByRole("button", { name: "5 minutes" });
    expect(fiveMinutes).toHaveClass("primary-button");
    fireEvent.click(fiveMinutes);
    // 27 min / 50 cards = 0.54 min per card -> 5 / 0.54 = 9.3, rounded up to 10 cards.
    expect(onStart).toHaveBeenLastCalledWith({ capCards: 10 });

    fireEvent.click(screen.getByRole("button", { name: "Regular session" }));
    expect(onStart).toHaveBeenLastCalledWith({});
  });

  it("all-at-once starts with includeBacklog", async () => {
    const onStart = renderHome(summary({ days_away: 7, due_all: 60, backlog: 10 }));

    fireEvent.click(await screen.findByRole("button", { name: "All at once (60)" }));

    expect(onStart).toHaveBeenLastCalledWith({ includeBacklog: true });
  });
});
