import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, deleteCard, getCards, importCardsBatch, setCardLearning } from "../api/client";
import type { Card, CardBatchImportResponse, CardListResponse } from "../api/types";
import { CardsPage, rowStatus } from "./CardsPage";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    getCards: vi.fn(),
    deleteCard: vi.fn(),
    importCardsBatch: vi.fn(),
    setCardLearning: vi.fn(),
    getSettings: vi.fn().mockResolvedValue({ tts_enabled: false }),
  };
});

const mockedGetCards = vi.mocked(getCards);
const mockedDeleteCard = vi.mocked(deleteCard);
const mockedImportCardsBatch = vi.mocked(importCardsBatch);
const mockedSetCardLearning = vi.mocked(setCardLearning);

function makeCard(overrides: Partial<Card> = {}): Card {
  return {
    id: 7,
    source_text: "turn down",
    source_language: "en",
    entry_type: "phrasal_verb",
    canonical_text: "turn down",
    canonical_text_normalized: "turn down",
    transcription: "/tɝn daʊn/",
    translation_variants: ["отклонять", "убавлять"],
    word_family: [{ word: "turn-down", part_of_speech: "noun", translation: "отказ" }],
    explanation: "Refuse or reduce volume.",
    examples: ["She turned down the offer.", "Turn down the music.", "He turned down help."],
    chunks: [{ text: "turn down an offer", target: "turn down", translation: "отклонить предложение" }],
    frequency: 6,
    frequency_note: null,
    is_learning: true,
    srs_state: null,
    srs_due_at: null,
    llm_model: "test-model",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function listOf(items: Card[], total = items.length, offset = 0): CardListResponse {
  return { items, total, offset, limit: 50 };
}

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

function rowOf(word: string): HTMLElement {
  return screen.getByText(word, { selector: "strong" }).closest("button") as HTMLElement;
}

function importResponse(sourceTexts: string[]): CardBatchImportResponse {
  return {
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
  };
}

function openAddWords(): void {
  fireEvent.click(screen.getByRole("button", { name: "Add words" }));
}

describe("rowStatus", () => {
  // Local time on purpose: the label follows the browser's day.
  const now = new Date(2026, 9, 18, 15, 0, 0);
  const scheduled = (state: string, due: Date): Card =>
    makeCard({ srs_state: state, srs_due_at: due.toISOString() });

  it("is off for a card that is not learning, whatever its schedule", () => {
    expect(rowStatus(makeCard({ is_learning: false, srs_state: "review", srs_due_at: now.toISOString() }), now)).toEqual({
      kind: "off",
      label: "off",
    });
  });

  it("is new for a learning card without a schedule", () => {
    expect(rowStatus(makeCard(), now)).toEqual({ kind: "new", label: "new" });
  });

  it("says today for anything due before local midnight, overdue included", () => {
    expect(rowStatus(scheduled("review", new Date(2026, 9, 10, 8, 0)), now).label).toBe("today");
    expect(rowStatus(scheduled("review", new Date(2026, 9, 18, 23, 59, 59)), now).label).toBe("today");
  });

  it("counts local calendar days until the due day, whatever the time of day", () => {
    const justAfterMidnight = new Date(2026, 9, 18, 0, 1);
    for (const due of [new Date(2026, 9, 19, 0, 2), new Date(2026, 9, 19, 23, 59)]) {
      expect(rowStatus(scheduled("review", due), justAfterMidnight).label).toBe("1 d");
      expect(rowStatus(scheduled("review", due), now).label).toBe("1 d");
    }
    expect(rowStatus(scheduled("review", new Date(2026, 9, 20, 0, 2)), justAfterMidnight).label).toBe("2 d");
    expect(rowStatus(scheduled("review", new Date(2026, 9, 20, 23, 59)), now).label).toBe("2 d");
    expect(rowStatus(scheduled("review", new Date(2026, 9, 17, 23, 59)), justAfterMidnight).label).toBe("today");
  });

  it("maps the FSRS state to the dot kind", () => {
    const due = new Date(2026, 9, 25);
    expect(rowStatus(scheduled("review", due), now).kind).toBe("review");
    expect(rowStatus(scheduled("learning", due), now).kind).toBe("learning");
    expect(rowStatus(scheduled("relearning", due), now).kind).toBe("learning");
  });
});

describe("CardsPage", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", "/");
    mockedGetCards.mockReset();
    mockedDeleteCard.mockReset();
    mockedImportCardsBatch.mockReset();
    mockedSetCardLearning.mockReset();
    mockedGetCards.mockResolvedValue(listOf([]));
  });

  it("renders a compact row per card with word, translation, status dot and label", async () => {
    const threeDaysAhead = new Date();
    threeDaysAhead.setDate(threeDaysAhead.getDate() + 3);
    threeDaysAhead.setHours(12, 0, 0, 0);
    mockedGetCards.mockResolvedValue(
      listOf([
        makeCard({ id: 1, canonical_text: "fresh", translation_variants: ["свежий", "новый"] }),
        makeCard({
          id: 2,
          canonical_text: "overdue",
          translation_variants: ["просроченный"],
          srs_state: "relearning",
          srs_due_at: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
        }),
        makeCard({
          id: 3,
          canonical_text: "later",
          translation_variants: ["позже"],
          srs_state: "review",
          srs_due_at: threeDaysAhead.toISOString(),
        }),
        makeCard({ id: 4, canonical_text: "parked", translation_variants: ["отложенный"], is_learning: false }),
      ]),
    );

    renderCardsPage();

    await screen.findByText("fresh", { selector: "strong" });
    const expected: [string, string, string, string][] = [
      ["fresh", "свежий", "new", "new"],
      ["overdue", "просроченный", "today", "learning"],
      ["later", "позже", "3 d", "review"],
      ["parked", "отложенный", "off", "off"],
    ];
    for (const [word, translation, label, kind] of expected) {
      const row = within(rowOf(word));
      expect(row.getByText(translation)).toBeInTheDocument();
      expect(row.getByText(label)).toBeInTheDocument();
      expect(rowOf(word).querySelector(".status-dot")).toHaveClass(`status-dot-${kind}`);
    }
    // Only the primary translation is shown.
    expect(screen.queryByText("новый")).not.toBeInTheDocument();
    // One accent button per screen: "+".
    expect(document.querySelectorAll(".primary-button")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Add words" })).toHaveClass("primary-button");
  });

  it("shows an empty state for an empty dictionary and for an empty search", async () => {
    renderCardsPage();
    expect(await screen.findByText("No words yet")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Learning" }));
    expect(await screen.findByText("Nothing found")).toBeInTheDocument();
  });

  it("filters by card type and explains the types", async () => {
    window.history.replaceState(null, "", "/telegram/webapp/?view=cards");
    renderCardsPage();
    await waitFor(() => expect(mockedGetCards).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Idiom" }));

    await waitFor(() => expect(mockedGetCards).toHaveBeenLastCalledWith(expect.objectContaining({ entry_type: "idiom" })));
    expect(new URLSearchParams(window.location.search).get("type")).toBe("idiom");

    fireEvent.click(screen.getByRole("button", { name: "All types" }));
    await waitFor(() => expect(mockedGetCards).toHaveBeenLastCalledWith(expect.objectContaining({ entry_type: undefined })));

    fireEvent.click(screen.getByRole("button", { name: "What are these types?" }));
    expect(await screen.findByText("A proverb or saying")).toBeInTheDocument();
  });

  it("maps the filter chips to is_learning and keeps the choice in the URL", async () => {
    window.history.replaceState(null, "", "/telegram/webapp/?view=cards#tgWebAppData=signed");
    renderCardsPage();

    await waitFor(() => expect(mockedGetCards).toHaveBeenCalledTimes(1));
    expect(mockedGetCards).toHaveBeenLastCalledWith({
      offset: 0,
      limit: 50,
      search: undefined,
      is_learning: undefined,
    });
    expect(screen.getByRole("button", { name: "All" })).toHaveAttribute("aria-pressed", "true");

    fireEvent.click(screen.getByRole("button", { name: "Learning" }));
    await waitFor(() => expect(mockedGetCards).toHaveBeenLastCalledWith(expect.objectContaining({ is_learning: true })));
    expect(screen.getByRole("button", { name: "Learning" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "All" })).toHaveAttribute("aria-pressed", "false");
    const params = new URLSearchParams(window.location.search);
    expect(params.get("filter")).toBe("learning");
    expect(params.get("view")).toBe("cards");
    expect(window.location.hash).toBe("#tgWebAppData=signed");

    fireEvent.click(screen.getByRole("button", { name: "Not learning" }));
    await waitFor(() => expect(mockedGetCards).toHaveBeenLastCalledWith(expect.objectContaining({ is_learning: false })));

    fireEvent.click(screen.getByRole("button", { name: "All" }));
    await waitFor(() => expect(mockedGetCards).toHaveBeenLastCalledWith(expect.objectContaining({ is_learning: undefined })));
    expect(new URLSearchParams(window.location.search).has("filter")).toBe(false);
  });

  it("starts from the filter and the search in the URL", async () => {
    window.history.replaceState(null, "", "/?q=turn&filter=not_learning");
    renderCardsPage();

    await waitFor(() =>
      expect(mockedGetCards).toHaveBeenLastCalledWith(
        expect.objectContaining({ search: "turn", is_learning: false }),
      ),
    );
    expect(screen.getByRole("searchbox", { name: "Search words" })).toHaveValue("turn");
    expect(screen.getByRole("button", { name: "Not learning" })).toHaveAttribute("aria-pressed", "true");
  });

  it("debounces the search and keeps it in the URL next to the filter", async () => {
    renderCardsPage();
    await waitFor(() => expect(mockedGetCards).toHaveBeenCalledTimes(1));

    const input = screen.getByRole("searchbox", { name: "Search words" });
    fireEvent.change(input, { target: { value: "tu" } });
    fireEvent.change(input, { target: { value: " turn " } });
    // A chip tapped while the debounce is pending must survive the search update.
    fireEvent.click(screen.getByRole("button", { name: "Learning" }));

    await waitFor(() =>
      expect(mockedGetCards).toHaveBeenLastCalledWith(
        expect.objectContaining({ search: "turn", is_learning: true }),
      ),
    );
    const searchCalls = mockedGetCards.mock.calls.filter(([query]) => query.search !== undefined);
    expect(searchCalls.map(([query]) => query.search)).toEqual(["turn"]);
    const params = new URLSearchParams(window.location.search);
    expect(params.get("q")).toBe("turn");
    expect(params.get("filter")).toBe("learning");

    fireEvent.change(input, { target: { value: "" } });
    await waitFor(() => expect(new URLSearchParams(window.location.search).has("q")).toBe(false));
  });

  it("loads more cards 50 at a time", async () => {
    const cards = (from: number, count: number): Card[] =>
      Array.from({ length: count }, (_, index) =>
        makeCard({
          id: from + index,
          canonical_text: `word-${from + index}`,
          canonical_text_normalized: `word-${from + index}`,
        }),
      );
    mockedGetCards.mockImplementation(async ({ offset = 0 }) =>
      offset === 0 ? listOf(cards(0, 50), 60, 0) : listOf(cards(50, 10), 60, 50),
    );

    renderCardsPage();

    await screen.findByText("word-0", { selector: "strong" });
    expect(screen.getAllByRole("listitem")).toHaveLength(50);
    fireEvent.click(screen.getByRole("button", { name: "Load more" }));

    await screen.findByText("word-59", { selector: "strong" });
    expect(mockedGetCards).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 50, limit: 50 }));
    expect(screen.getAllByRole("listitem")).toHaveLength(60);
    expect(screen.queryByRole("button", { name: "Load more" })).not.toBeInTheDocument();
  });

  it("shows a card once when it appears on two pages, without a duplicate key warning", async () => {
    const errors = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const card = (id: number): Card =>
      makeCard({ id, canonical_text: `word-${id}`, canonical_text_normalized: `word-${id}` });
    mockedGetCards.mockImplementation(async ({ offset = 0 }) =>
      offset === 0 ? listOf([card(1), card(2)], 4, 0) : listOf([card(2), card(3)], 4, 2),
    );

    renderCardsPage();
    await screen.findByText("word-1", { selector: "strong" });
    fireEvent.click(screen.getByRole("button", { name: "Load more" }));

    await screen.findByText("word-3", { selector: "strong" });
    expect(screen.getAllByText("word-2", { selector: "strong" })).toHaveLength(1);
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
    expect(errors).not.toHaveBeenCalled();
    errors.mockRestore();
  });

  describe("card sheet", () => {
    beforeEach(() => {
      mockedGetCards.mockResolvedValue(listOf([makeCard()]));
    });

    it("opens the full card on a row tap, with focus inside, and closes on Close", async () => {
      renderCardsPage();
      const row = (await screen.findByText("turn down", { selector: "strong" })).closest("button") as HTMLElement;
      row.focus();
      fireEvent.click(row);

      const sheet = screen.getByRole("dialog", { name: "turn down" });
      expect(sheet).toHaveFocus();
      const inside = within(sheet);
      expect(inside.getByRole("heading", { name: "turn down" })).toBeInTheDocument();
      expect(inside.getByText("/tɝn daʊn/")).toBeInTheDocument();
      expect(inside.getByText("отклонять, убавлять")).toBeInTheDocument();
      expect(inside.getByText("Refuse or reduce volume.")).toBeInTheDocument();
      expect(inside.getByText("turn down an offer")).toBeInTheDocument();
      expect(inside.getByText("She turned down the offer.")).toBeInTheDocument();
      expect(inside.getByText("turn-down", { selector: "strong" }).closest("li")).toHaveTextContent(
        "turn-down (noun) — отказ",
      );
      expect(inside.getByRole("switch", { name: "Learning" })).toBeChecked();

      fireEvent.click(inside.getByRole("button", { name: "Close" }));

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
      expect(row).toHaveFocus();
    });

    it("closes on Escape and on a backdrop tap, but not on a tap inside", async () => {
      renderCardsPage();
      fireEvent.click(await screen.findByText("turn down", { selector: "strong" }));
      const sheet = screen.getByRole("dialog", { name: "turn down" });

      fireEvent.click(sheet);
      expect(screen.getByRole("dialog", { name: "turn down" })).toBeInTheDocument();

      fireEvent.keyDown(document, { key: "Escape" });
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

      fireEvent.click(screen.getByText("turn down", { selector: "strong" }));
      fireEvent.click(screen.getByRole("dialog", { name: "turn down" }).parentElement as HTMLElement);
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("keeps Tab inside the sheet, wrapping at both ends", async () => {
      renderCardsPage();
      fireEvent.click(await screen.findByText("turn down", { selector: "strong" }));
      const sheet = screen.getByRole("dialog", { name: "turn down" });
      const controls = sheet.querySelectorAll<HTMLElement>("button, input");
      const first = controls[0];
      const last = controls[controls.length - 1];
      expect(last).toBe(within(sheet).getByRole("button", { name: "Close" }));

      last.focus();
      expect(fireEvent.keyDown(last, { key: "Tab" })).toBe(false);
      expect(first).toHaveFocus();

      expect(fireEvent.keyDown(first, { key: "Tab", shiftKey: true })).toBe(false);
      expect(last).toHaveFocus();

      // From the sheet itself (where focus starts) Shift+Tab also wraps; Tab in the middle is left alone.
      sheet.focus();
      expect(fireEvent.keyDown(sheet, { key: "Tab", shiftKey: true })).toBe(false);
      expect(last).toHaveFocus();
      first.focus();
      expect(fireEvent.keyDown(first, { key: "Tab" })).toBe(true);
    });

    it("returns focus to Delete when the confirmation closes, and keeps Tab inside it", async () => {
      renderCardsPage();
      fireEvent.click(await screen.findByText("turn down", { selector: "strong" }));
      const deleteButton = screen.getByRole("button", { name: "Delete" });

      fireEvent.click(deleteButton);
      const confirm = screen.getByRole("dialog", { name: "Delete “turn down”?" });
      const cancel = within(confirm).getByRole("button", { name: "Cancel" });
      const confirmDelete = within(confirm).getByRole("button", { name: "Delete card" });
      expect(cancel).toHaveFocus();

      expect(fireEvent.keyDown(cancel, { key: "Tab", shiftKey: true })).toBe(false);
      expect(confirmDelete).toHaveFocus();
      expect(fireEvent.keyDown(confirmDelete, { key: "Tab" })).toBe(false);
      expect(cancel).toHaveFocus();

      fireEvent.click(cancel);
      expect(confirm).not.toBeInTheDocument();
      expect(deleteButton).toHaveFocus();

      fireEvent.click(deleteButton);
      fireEvent.keyDown(document, { key: "Escape" });
      expect(screen.queryByRole("dialog", { name: "Delete “turn down”?" })).not.toBeInTheDocument();
      expect(deleteButton).toHaveFocus();
    });

    it("toggles learning from the sheet and updates the row without reloading the list", async () => {
      mockedSetCardLearning.mockResolvedValue(makeCard({ is_learning: false }));
      renderCardsPage();
      const row = (await screen.findByText("turn down", { selector: "strong" })).closest("button") as HTMLElement;
      expect(within(row).getByText("new")).toBeInTheDocument();
      fireEvent.click(row);

      const toggle = within(screen.getByRole("dialog", { name: "turn down" })).getByRole("switch", { name: "Learning" });
      fireEvent.click(toggle);

      await waitFor(() => expect(toggle).not.toBeChecked());
      expect(mockedSetCardLearning).toHaveBeenCalledWith(7, false);
      expect(within(row).getByText("off")).toBeInTheDocument();
      expect(row.querySelector(".status-dot")).toHaveClass("status-dot-off");
      expect(mockedGetCards).toHaveBeenCalledTimes(1);
    });

    it("asks for confirmation before deleting, then closes the sheet and reloads", async () => {
      mockedDeleteCard.mockResolvedValue(undefined);
      mockedGetCards.mockResolvedValueOnce(listOf([makeCard()])).mockResolvedValue(listOf([]));
      renderCardsPage();
      fireEvent.click(await screen.findByText("turn down", { selector: "strong" }));

      fireEvent.click(screen.getByRole("button", { name: "Delete" }));
      const confirm = screen.getByRole("dialog", { name: "Delete “turn down”?" });
      expect(mockedDeleteCard).not.toHaveBeenCalled();

      // Escape cancels the confirmation first and leaves the sheet open.
      fireEvent.keyDown(document, { key: "Escape" });
      expect(confirm).not.toBeInTheDocument();
      expect(screen.getByRole("dialog", { name: "turn down" })).toBeInTheDocument();
      expect(mockedDeleteCard).not.toHaveBeenCalled();

      fireEvent.click(screen.getByRole("button", { name: "Delete" }));
      fireEvent.click(screen.getByRole("button", { name: "Delete card" }));

      await waitFor(() => expect(mockedDeleteCard).toHaveBeenCalledWith(7));
      expect(await screen.findByText("No words yet")).toBeInTheDocument();
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
      expect(mockedGetCards).toHaveBeenCalledTimes(2);
    });

    it("keeps the confirmation open and shows the error when deleting fails", async () => {
      mockedDeleteCard.mockRejectedValue(new Error("Card not found"));
      renderCardsPage();
      fireEvent.click(await screen.findByText("turn down", { selector: "strong" }));

      fireEvent.click(screen.getByRole("button", { name: "Delete" }));
      fireEvent.click(screen.getByRole("button", { name: "Delete card" }));

      expect(await screen.findByText("Card not found")).toBeInTheDocument();
      expect(screen.getByRole("dialog", { name: "Delete “turn down”?" })).toBeInTheDocument();
    });
  });

  describe("add words sheet", () => {
    it("opens from + with the batch form and closes on Close", async () => {
      renderCardsPage();
      await screen.findByText("No words yet");

      openAddWords();
      const sheet = screen.getByRole("dialog", { name: "Add words" });
      expect(sheet).toHaveFocus();
      expect(within(sheet).getByLabelText("List")).toBeInTheDocument();
      expect(within(sheet).getByRole("button", { name: "Import" })).toHaveClass("primary-button");

      fireEvent.click(within(sheet).getByRole("button", { name: "Close" }));
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("keeps a typed list on Escape and a backdrop tap, but Close still closes", async () => {
      renderCardsPage();
      await screen.findByText("No words yet");
      openAddWords();
      const sheet = screen.getByRole("dialog", { name: "Add words" });

      fireEvent.change(within(sheet).getByLabelText("List"), { target: { value: "look up" } });
      fireEvent.keyDown(document, { key: "Escape" });
      fireEvent.click(sheet.parentElement as HTMLElement);
      expect(screen.getByRole("dialog", { name: "Add words" })).toBeInTheDocument();
      expect(within(sheet).getByLabelText("List")).toHaveValue("look up");

      // Nothing to lose once the list is empty again.
      fireEvent.change(within(sheet).getByLabelText("List"), { target: { value: "  " } });
      fireEvent.keyDown(document, { key: "Escape" });
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

      openAddWords();
      fireEvent.change(screen.getByLabelText("List"), { target: { value: "look up" } });
      fireEvent.click(screen.getByRole("button", { name: "Close" }));
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("stays open while importing and may be dismissed once the import has finished", async () => {
      let finish: (response: CardBatchImportResponse) => void = () => undefined;
      mockedImportCardsBatch.mockReturnValue(new Promise((resolve) => (finish = resolve)));
      renderCardsPage();
      await screen.findByText("No words yet");
      openAddWords();
      const sheet = screen.getByRole("dialog", { name: "Add words" });

      fireEvent.change(within(sheet).getByLabelText("List"), { target: { value: "look up" } });
      fireEvent.click(within(sheet).getByRole("button", { name: "Import" }));
      fireEvent.change(within(sheet).getByLabelText("List"), { target: { value: "" } });
      fireEvent.keyDown(document, { key: "Escape" });
      fireEvent.click(sheet.parentElement as HTMLElement);
      expect(screen.getByRole("dialog", { name: "Add words" })).toBeInTheDocument();

      fireEvent.change(within(sheet).getByLabelText("List"), { target: { value: "look up" } });
      finish(importResponse(["look up"]));
      expect(await screen.findByText("Total processed: 1")).toBeInTheDocument();
      expect(within(sheet).getByLabelText("List")).toHaveValue("look up");

      // The finished list may go; a new one is a draft again.
      fireEvent.change(within(sheet).getByLabelText("List"), { target: { value: "look up\nbreak down" } });
      fireEvent.keyDown(document, { key: "Escape" });
      expect(screen.getByRole("dialog", { name: "Add words" })).toBeInTheDocument();
      fireEvent.change(within(sheet).getByLabelText("List"), { target: { value: "look up" } });
      fireEvent.keyDown(document, { key: "Escape" });
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("keeps the list when an import fails: Escape and a backdrop tap do not drop it", async () => {
      mockedImportCardsBatch.mockRejectedValue(new ApiError("boom", 500));
      renderCardsPage();
      await screen.findByText("No words yet");
      openAddWords();
      const sheet = screen.getByRole("dialog", { name: "Add words" });

      fireEvent.change(within(sheet).getByLabelText("List"), { target: { value: "look up" } });
      fireEvent.click(within(sheet).getByRole("button", { name: "Import" }));
      expect(await screen.findByText(/boom/)).toBeInTheDocument();

      fireEvent.keyDown(document, { key: "Escape" });
      fireEvent.click(sheet.parentElement as HTMLElement);
      expect(screen.getByRole("dialog", { name: "Add words" })).toBeInTheDocument();
      expect(within(sheet).getByLabelText("List")).toHaveValue("look up");
    });

    it("asks for input when the list is empty", async () => {
      renderCardsPage();
      await screen.findByText("No words yet");

      openAddWords();
      fireEvent.click(screen.getByRole("button", { name: "Import" }));

      expect(screen.getByText("Paste at least one word or expression.")).toBeInTheDocument();
      expect(mockedImportCardsBatch).not.toHaveBeenCalled();
    });

    it("splits large input into chunks of 5, shows the results and reloads the list", async () => {
      mockedImportCardsBatch.mockImplementation(async (sourceTexts) => importResponse(sourceTexts));
      renderCardsPage();
      await waitFor(() => expect(mockedGetCards).toHaveBeenCalledTimes(1));

      openAddWords();
      const lines = Array.from({ length: 12 }, (_, index) => `item-${index + 1}`).join("\n");
      fireEvent.change(screen.getByLabelText("List"), { target: { value: lines } });
      fireEvent.click(screen.getByRole("button", { name: "Import" }));

      await waitFor(() => expect(mockedImportCardsBatch).toHaveBeenCalledTimes(3));
      expect(mockedImportCardsBatch.mock.calls[0][0]).toHaveLength(5);
      expect(mockedImportCardsBatch.mock.calls[2][0]).toHaveLength(2);
      expect(await screen.findByText("Processed 12/12")).toBeInTheDocument();
      expect(await screen.findByText("Total processed: 12")).toBeInTheDocument();
      expect(await screen.findByText("Added: 12")).toBeInTheDocument();
      await waitFor(() => expect(mockedGetCards).toHaveBeenCalledTimes(2));
    });

    it("shows mixed statuses in the batch results", async () => {
      mockedImportCardsBatch.mockResolvedValue({
        items: [
          { source_text: "look up", status: "created", card_id: 1, canonical_text: "look up", message: null },
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

      openAddWords();
      fireEvent.change(screen.getByLabelText("List"), {
        target: { value: "look up\nvery random sentence\none two three four five six seven eight nine" },
      });
      fireEvent.click(screen.getByRole("button", { name: "Import" }));

      expect(await screen.findByText("Total processed: 3")).toBeInTheDocument();
      expect(screen.getByText("Rejected: 1")).toBeInTheDocument();
      expect(screen.getByText("Invalid input: 1")).toBeInTheDocument();
      expect(screen.getByText(/This does not look like a stable lexical unit\./)).toBeInTheDocument();
      expect(screen.getByText(/Please send up to 8 words\./)).toBeInTheDocument();
      expect(screen.getByText("invalid input")).toBeInTheDocument();
    });

    it("stops on a failed chunk and keeps the partial results", async () => {
      mockedImportCardsBatch
        .mockResolvedValueOnce(importResponse(Array.from({ length: 5 }, (_, index) => `item-${index + 1}`)))
        .mockRejectedValueOnce(new Error("network"));
      renderCardsPage();

      openAddWords();
      const lines = Array.from({ length: 7 }, (_, index) => `item-${index + 1}`).join("\n");
      fireEvent.change(screen.getByLabelText("List"), { target: { value: lines } });
      fireEvent.click(screen.getByRole("button", { name: "Import" }));

      await waitFor(() => expect(mockedImportCardsBatch).toHaveBeenCalledTimes(2));
      expect(await screen.findByText("Import stopped: request failed")).toBeInTheDocument();
      expect(screen.getByText("Total processed: 5")).toBeInTheDocument();
      expect(screen.getByText("Added: 5")).toBeInTheDocument();
    });
  });
});
