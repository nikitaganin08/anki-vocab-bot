import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getSpeakingIssues, getSpeakingSession, getSpeakingStats } from "../api/client";
import type { SpeakingIssue, SpeakingStats } from "../api/types";
import { SpeakingView } from "./SpeakingView";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return { ...actual, getSpeakingStats: vi.fn(), getSpeakingIssues: vi.fn(), getSpeakingSession: vi.fn() };
});

const issue: SpeakingIssue = {
  id: 7,
  session_id: 2,
  recorded_at: "2026-11-13T09:04:22Z",
  category: "article",
  label: "Articles",
  wrong: "worked as HVAC engineer",
  right: "worked as an HVAC engineer",
  why: "a/an before jobs",
};

const stats: SpeakingStats = {
  recordings: 2,
  minutes: 3,
  filler_rate: 4.3,
  filler_rate_prev: 7.1,
  words_used: 4,
  words_total: 6,
  categories: [
    { category: "article", label: "Articles", count: 5 },
    { category: "preposition", label: "Prepositions", count: 1 },
  ],
  sessions: [
    {
      id: 2,
      recorded_at: "2026-11-13T09:04:22Z",
      kind: "voice",
      duration_seconds: 102,
      topic: "a change in your life",
      filler_count: 12,
      fix_count: 6,
    },
  ],
};

function renderSpeaking(): void {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <SpeakingView />
    </QueryClientProvider>,
  );
}

describe("SpeakingView", () => {
  beforeEach(() => {
    vi.mocked(getSpeakingStats).mockReset().mockResolvedValue(stats);
    vi.mocked(getSpeakingIssues).mockReset().mockResolvedValue([issue]);
    vi.mocked(getSpeakingSession).mockReset().mockResolvedValue({
      id: 2,
      recorded_at: "2026-11-13T09:04:22Z",
      kind: "voice",
      duration_seconds: 102,
      topic: "a change in your life",
      words: [
        { word: "prevail", used: true },
        { word: "try", used: false },
      ],
      transcript: "So, uh, I decided to change my job.",
      filler_count: 12,
      natural_version: "I switched careers.",
      next_time: "Use a/an before jobs.",
      focus_check: "better",
      issues: [issue],
    });
  });

  it("shows stats, patterns and recordings, then drills down to a recording", async () => {
    renderSpeaking();

    expect(await screen.findByText("7.1 → 4.3")).toBeInTheDocument();
    expect(screen.getByText("4 of 6")).toBeInTheDocument();
    expect(screen.getByText("a change in your life")).toBeInTheDocument();
    expect(screen.getByText("6 fixes")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Articles/ }));
    const list = await screen.findByRole("dialog", { name: "Articles" });
    expect(vi.mocked(getSpeakingIssues)).toHaveBeenCalledWith("article");
    fireEvent.click(await within(list).findByRole("button", { name: /worked as an HVAC engineer/ }));

    const recording = await screen.findByRole("dialog", { name: "Recording" });
    expect(await within(recording).findByText("I switched careers.")).toBeInTheDocument();
    expect(within(recording).getByText(/last focus: better/)).toBeInTheDocument();
    expect(within(recording).getByText("✅ prevail")).toBeInTheDocument();
    expect(screen.queryByRole("dialog", { name: "Articles" })).not.toBeInTheDocument();
  });

  it("invites to record when there is nothing yet", async () => {
    vi.mocked(getSpeakingStats).mockResolvedValue({ ...stats, recordings: 0, categories: [], sessions: [] });
    renderSpeaking();

    expect(await screen.findByRole("heading", { name: "No recordings yet" })).toBeInTheDocument();
  });
});
