import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { deleteCard, getCards, importCardsBatch } from "../api/client";
import { renderRouteWithProviders } from "../test/renderWithProviders";
import { CardsPage } from "./CardsPage";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    getCards: vi.fn(),
    deleteCard: vi.fn(),
    importCardsBatch: vi.fn(),
  };
});

const mockedGetCards = vi.mocked(getCards);
const mockedDeleteCard = vi.mocked(deleteCard);
const mockedImportCardsBatch = vi.mocked(importCardsBatch);

describe("CardsPage", () => {
  beforeEach(() => {
    mockedGetCards.mockReset();
    mockedDeleteCard.mockReset();
    mockedImportCardsBatch.mockReset();
    mockedGetCards.mockResolvedValue({
      items: [],
      total: 0,
      offset: 0,
      limit: 20,
    });
  });

  it("renders batch panel and cards list", async () => {
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
    expect(screen.getByText("Batch Import")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Import" })).toBeInTheDocument();
  });

  it("splits large input into chunks of 50 and 5", async () => {
    mockedImportCardsBatch.mockImplementation(async (sourceTexts) => ({
      items: sourceTexts.map((sourceText, index) => ({
        source_text: sourceText,
        status: "created",
        card_id: index + 1,
        canonical_text: sourceText,
        message: null,
      })),
      summary: {
        total: sourceTexts.length,
        created: sourceTexts.length,
        duplicate_source: 0,
        duplicate_canonical: 0,
        rejected: 0,
        invalid_input: 0,
        upstream_error: 0,
      },
    }));

    renderRouteWithProviders(<CardsPage />, {
      path: "/cards",
      route: "/cards",
    });

    await screen.findByRole("heading", { name: "Cards" });

    const lines = Array.from({ length: 55 }, (_, index) => `item-${index + 1}`).join("\n");
    fireEvent.change(screen.getByLabelText("Input list"), { target: { value: lines } });
    fireEvent.click(screen.getByRole("button", { name: "Import" }));

    await waitFor(() => {
      expect(mockedImportCardsBatch).toHaveBeenCalledTimes(2);
    });

    expect(mockedImportCardsBatch.mock.calls[0][0]).toHaveLength(50);
    expect(mockedImportCardsBatch.mock.calls[1][0]).toHaveLength(5);
    expect(await screen.findByText("Processed 55/55")).toBeInTheDocument();
    expect(await screen.findByText("Total processed: 55")).toBeInTheDocument();
    expect(await screen.findByText("Created: 55")).toBeInTheDocument();
  });

  it("shows mixed statuses in batch results table", async () => {
    mockedImportCardsBatch.mockResolvedValue({
      items: [
        {
          source_text: "look up",
          status: "created",
          card_id: 1,
          canonical_text: "look up",
          message: null,
        },
        {
          source_text: "very random sentence",
          status: "rejected",
          card_id: null,
          canonical_text: null,
          message: "This does not look like a stable lexical unit.",
        },
        {
          source_text: "one two three four five six seven eight nine",
          status: "invalid_input",
          card_id: null,
          canonical_text: null,
          message: "Please send up to 8 words.",
        },
      ],
      summary: {
        total: 3,
        created: 1,
        duplicate_source: 0,
        duplicate_canonical: 0,
        rejected: 1,
        invalid_input: 1,
        upstream_error: 0,
      },
    });

    renderRouteWithProviders(<CardsPage />, {
      path: "/cards",
      route: "/cards",
    });

    await screen.findByRole("heading", { name: "Cards" });
    fireEvent.change(screen.getByLabelText("Input list"), {
      target: { value: "look up\nvery random sentence\none two three four five six seven eight nine" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Import" }));

    expect(await screen.findByText("Total processed: 3")).toBeInTheDocument();
    expect(screen.getByText("Rejected: 1")).toBeInTheDocument();
    expect(screen.getByText("Invalid input: 1")).toBeInTheDocument();
    expect(screen.getByText(/This does not look like a stable lexical unit\./)).toBeInTheDocument();
    expect(screen.getByText(/Please send up to 8 words\./)).toBeInTheDocument();
    expect(screen.getAllByText("look up").length).toBeGreaterThan(0);
    expect(screen.getByText("invalid input")).toBeInTheDocument();
  });

  it("stops on second chunk error and keeps partial results", async () => {
    mockedImportCardsBatch
      .mockResolvedValueOnce({
        items: Array.from({ length: 50 }, (_, index) => ({
          source_text: `item-${index + 1}`,
          status: "created" as const,
          card_id: index + 1,
          canonical_text: `item-${index + 1}`,
          message: null,
        })),
        summary: {
          total: 50,
          created: 50,
          duplicate_source: 0,
          duplicate_canonical: 0,
          rejected: 0,
          invalid_input: 0,
          upstream_error: 0,
        },
      })
      .mockRejectedValueOnce(new Error("network"));

    renderRouteWithProviders(<CardsPage />, {
      path: "/cards",
      route: "/cards",
    });

    await screen.findByRole("heading", { name: "Cards" });
    const lines = Array.from({ length: 55 }, (_, index) => `item-${index + 1}`).join("\n");
    fireEvent.change(screen.getByLabelText("Input list"), { target: { value: lines } });
    fireEvent.click(screen.getByRole("button", { name: "Import" }));

    await waitFor(() => {
      expect(mockedImportCardsBatch).toHaveBeenCalledTimes(2);
    });

    expect(await screen.findByText("Import stopped: Batch import failed due to request error.")).toBeInTheDocument();
    expect(screen.getByText("Total processed: 50")).toBeInTheDocument();
    expect(screen.getByText("Created: 50")).toBeInTheDocument();
    expect(screen.getAllByText("item-1").length).toBeGreaterThan(0);
  });

  it("confirms deletion inside an in-app dialog", async () => {
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
    mockedDeleteCard.mockResolvedValue(undefined);

    renderRouteWithProviders(<CardsPage />, {
      path: "/cards",
      route: "/cards",
    });

    fireEvent.click(await screen.findByRole("button", { name: "Delete" }));

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Delete turn down?" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Delete card" }));

    await waitFor(() => {
      expect(mockedDeleteCard).toHaveBeenCalled();
    });
    expect(mockedDeleteCard.mock.calls[0][0]).toBe(7);
  });
});
