import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { deleteCard, getCards, importCardsBatch, setCardLearning } from "../api/client";
import type { Card } from "../api/types";
import { CardsPage } from "./CardsPage";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    getCards: vi.fn(),
    deleteCard: vi.fn(),
    importCardsBatch: vi.fn(),
    setCardLearning: vi.fn(),
  };
});

const mockedGetCards = vi.mocked(getCards);
const mockedDeleteCard = vi.mocked(deleteCard);
const mockedImportCardsBatch = vi.mocked(importCardsBatch);
const mockedSetCardLearning = vi.mocked(setCardLearning);

function renderCardsPage(): ReturnType<typeof render> {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <CardsPage />
    </QueryClientProvider>,
  );
}

describe("CardsPage", () => {
  beforeEach(() => {
    mockedGetCards.mockReset();
    mockedDeleteCard.mockReset();
    mockedImportCardsBatch.mockReset();
    mockedSetCardLearning.mockReset();
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
          word_family: [
            {
              word: "turn-down",
              part_of_speech: "noun",
              translation: "отказ",
            },
          ],
          explanation: "Refuse or reduce volume.",
          examples: ["She turned down the offer.", "Turn down the music.", "He turned down help."],
          chunks: [],
          frequency: 6,
          frequency_note: null,
          is_learning: true,
          anki_sync_status: "pending",
          anki_note_id: null,
          anki_sync_error: null,
          llm_model: "test-model",
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
      ],
      total: 1,
      offset: 0,
      limit: 20,
    });

    renderCardsPage();

    expect(await screen.findByRole("heading", { name: "Слова" })).toBeInTheDocument();
    expect((await screen.findAllByText("turn down")).length).toBeGreaterThan(0);
    expect(await screen.findByRole("button", { name: "Удалить" })).toBeInTheDocument();
    expect(await screen.findByText("1–1 из 1")).toBeInTheDocument();
    expect(screen.getByText("Импорт списком")).toBeInTheDocument();
    expect(screen.getByText("turn-down")).toBeInTheDocument();
    // One accent button per screen: Import; search is secondary.
    expect(document.querySelectorAll(".primary-button")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Импортировать" })).toHaveClass("primary-button");
    expect(screen.getByRole("button", { name: "Найти" })).toHaveClass("secondary-button");
    expect(screen.getByText("ждёт синхронизации", { selector: ".status-pill" })).toBeInTheDocument();
    expect(screen.getByText("фразовый глагол", { selector: "strong" })).toBeInTheDocument();
    expect(screen.getByText(/отказ/)).toBeInTheDocument();
  });

  it("splits large input into chunks of 5", async () => {
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

    renderCardsPage();

    await screen.findByRole("heading", { name: "Слова" });

    const lines = Array.from({ length: 12 }, (_, index) => `item-${index + 1}`).join("\n");
    fireEvent.change(screen.getByLabelText("Список"), { target: { value: lines } });
    fireEvent.click(screen.getByRole("button", { name: "Импортировать" }));

    await waitFor(() => {
      expect(mockedImportCardsBatch).toHaveBeenCalledTimes(3);
    });

    expect(mockedImportCardsBatch.mock.calls[0][0]).toHaveLength(5);
    expect(mockedImportCardsBatch.mock.calls[2][0]).toHaveLength(2);
    expect(await screen.findByText("Обработано 12/12")).toBeInTheDocument();
    expect(await screen.findByText("Всего обработано: 12")).toBeInTheDocument();
    expect(await screen.findByText("Добавлено: 12")).toBeInTheDocument();
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

    renderCardsPage();

    await screen.findByRole("heading", { name: "Слова" });
    fireEvent.change(screen.getByLabelText("Список"), {
      target: { value: "look up\nvery random sentence\none two three four five six seven eight nine" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Импортировать" }));

    expect(await screen.findByText("Всего обработано: 3")).toBeInTheDocument();
    expect(screen.getByText("Отклонено: 1")).toBeInTheDocument();
    expect(screen.getByText("Неверный ввод: 1")).toBeInTheDocument();
    expect(screen.getByText(/This does not look like a stable lexical unit\./)).toBeInTheDocument();
    expect(screen.getByText(/Please send up to 8 words\./)).toBeInTheDocument();
    expect(screen.getAllByText("look up").length).toBeGreaterThan(0);
    expect(screen.getByText("неверный ввод")).toBeInTheDocument();
  });

  it("stops on second chunk error and keeps partial results", async () => {
    mockedImportCardsBatch
      .mockResolvedValueOnce({
        items: Array.from({ length: 5 }, (_, index) => ({
          source_text: `item-${index + 1}`,
          status: "created" as const,
          card_id: index + 1,
          canonical_text: `item-${index + 1}`,
          message: null,
        })),
        summary: {
          total: 5,
          created: 5,
          duplicate_source: 0,
          duplicate_canonical: 0,
          rejected: 0,
          invalid_input: 0,
          upstream_error: 0,
        },
      })
      .mockRejectedValueOnce(new Error("network"));

    renderCardsPage();

    await screen.findByRole("heading", { name: "Слова" });
    const lines = Array.from({ length: 7 }, (_, index) => `item-${index + 1}`).join("\n");
    fireEvent.change(screen.getByLabelText("Список"), { target: { value: lines } });
    fireEvent.click(screen.getByRole("button", { name: "Импортировать" }));

    await waitFor(() => {
      expect(mockedImportCardsBatch).toHaveBeenCalledTimes(2);
    });

    expect(await screen.findByText("Импорт остановлен: ошибка запроса")).toBeInTheDocument();
    expect(screen.getByText("Всего обработано: 5")).toBeInTheDocument();
    expect(screen.getByText("Добавлено: 5")).toBeInTheDocument();
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
          word_family: [],
          explanation: "Refuse or reduce volume.",
          examples: ["She turned down the offer.", "Turn down the music.", "He turned down help."],
          chunks: [],
          frequency: 6,
          frequency_note: null,
          is_learning: true,
          anki_sync_status: "pending",
          anki_note_id: null,
          anki_sync_error: null,
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

    renderCardsPage();

    fireEvent.click(await screen.findByRole("button", { name: "Удалить" }));

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Удалить «turn down»?" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Удалить карточку" }));

    await waitFor(() => {
      expect(mockedDeleteCard).toHaveBeenCalled();
    });
    expect(mockedDeleteCard.mock.calls[0][0]).toBe(7);
  });

  it("toggle learning patches card", async () => {
    const card: Card = {
      id: 7,
      source_text: "turn down",
      source_language: "en",
      entry_type: "phrasal_verb",
      canonical_text: "turn down",
      canonical_text_normalized: "turn down",
      transcription: null,
      translation_variants: ["отклонять", "убавлять"],
      word_family: [],
      explanation: "Refuse or reduce volume.",
      examples: ["She turned down the offer.", "Turn down the music.", "He turned down help."],
      chunks: [],
      frequency: 6,
      frequency_note: null,
      is_learning: true,
      anki_sync_status: "pending",
      anki_note_id: null,
      anki_sync_error: null,
      llm_model: "test-model",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    mockedGetCards.mockResolvedValue({ items: [card], total: 1, offset: 0, limit: 20 });
    mockedSetCardLearning.mockResolvedValue({ ...card, is_learning: false });

    renderCardsPage();

    const toggle = await screen.findByRole("switch", { name: "Учим: turn down" });
    expect(toggle).toBeChecked();
    fireEvent.click(toggle);

    await waitFor(() => expect(toggle).not.toBeChecked());
    expect(mockedSetCardLearning).toHaveBeenCalledWith(7, false);
    expect(mockedGetCards).toHaveBeenCalledTimes(1);
  });
});
