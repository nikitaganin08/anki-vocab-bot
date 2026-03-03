import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getStats } from "../api/client";
import { DashboardPage } from "./DashboardPage";
import { renderWithProviders } from "../test/renderWithProviders";

vi.mock("../api/client", () => ({
  getStats: vi.fn(),
}));

const mockedGetStats = vi.mocked(getStats);

describe("DashboardPage", () => {
  beforeEach(() => {
    mockedGetStats.mockReset();
  });

  it("renders stats cards", async () => {
    mockedGetStats.mockResolvedValue({
      total_cards: 21,
      eligible_for_anki: 9,
      anki_pending: 4,
      anki_synced: 16,
      anki_failed: 1,
      by_entry_type: {
        word: 10,
        phrasal_verb: 4,
        collocation: 3,
        idiom: 2,
        expression: 2,
      },
      by_source_language: {
        en: 14,
        ru: 7,
      },
    });

    renderWithProviders(<DashboardPage />);

    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByText("Total cards")).toBeInTheDocument();
    expect(screen.getByText("21")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Cards by entry type" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Cards by source language" })).toBeInTheDocument();
  });
});
