import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getCard } from "../api/client";
import { renderRouteWithProviders } from "../test/renderWithProviders";
import { CardDetailPage } from "./CardDetailPage";

vi.mock("../api/client", () => ({
  getCard: vi.fn(),
}));

const mockedGetCard = vi.mocked(getCard);

describe("CardDetailPage", () => {
  beforeEach(() => {
    mockedGetCard.mockReset();
  });

  it("renders card detail fields", async () => {
    mockedGetCard.mockResolvedValue({
      id: 12,
      source_text: "come across",
      source_language: "en",
      entry_type: "phrasal_verb",
      canonical_text: "come across",
      canonical_text_normalized: "come across",
      transcription: "/kam akros/",
      translation_variants: ["наталкиваться", "производить впечатление"],
      explanation: "Meet by chance or appear to others in a certain way.",
      examples: [
        "I came across this article yesterday.",
        "He comes across as confident.",
        "We came across an old photo.",
      ],
      frequency: 5,
      frequency_note: null,
      eligible_for_anki: true,
      anki_sync_status: "synced",
      anki_note_id: 223,
      llm_model: "test-model",
      created_at: "2026-02-11T12:00:00Z",
      updated_at: "2026-02-11T12:30:00Z",
    });

    renderRouteWithProviders(<CardDetailPage />, {
      path: "/cards/:cardId",
      route: "/cards/12",
    });

    expect(await screen.findByRole("heading", { name: "come across" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Translations" })).toBeInTheDocument();
    expect(screen.getByText("phrasal verb")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to cards" })).toBeInTheDocument();
  });
});
