import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { deleteCard, getCards } from "../api/client";
import { renderRouteWithProviders } from "../test/renderWithProviders";
import { CardsPage } from "./CardsPage";

vi.mock("../api/client", () => ({
  getCards: vi.fn(),
  deleteCard: vi.fn(),
}));

const mockedGetCards = vi.mocked(getCards);
const mockedDeleteCard = vi.mocked(deleteCard);

describe("CardsPage", () => {
  beforeEach(() => {
    mockedGetCards.mockReset();
    mockedDeleteCard.mockReset();
  });

  it("renders card rows and pagination info", async () => {
    mockedGetCards.mockResolvedValue({
      items: [
        {
          id: 7,
          source_text: "turn down",
          source_language: "en",
          entry_type: "phrasal_verb",
          canonical_text: "turn down",
          canonical_text_normalized: "turn down",
          transcription: "/t3:n daun/",
          translation_variants: ["отклонять", "убавлять"],
          explanation: "Refuse or reduce volume.",
          examples: ["She turned down the offer.", "Turn down the music.", "He turned down help."],
          frequency: 6,
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
    });

    renderRouteWithProviders(<CardsPage />, {
      path: "/cards",
      route: "/cards",
    });

    expect(await screen.findByRole("heading", { name: "Cards" })).toBeInTheDocument();
    expect((await screen.findAllByText("turn down")).length).toBeGreaterThan(0);
    expect(await screen.findByRole("button", { name: "Delete" })).toBeInTheDocument();
    expect(await screen.findByText("Showing 1-1 of 1")).toBeInTheDocument();
  });
});
