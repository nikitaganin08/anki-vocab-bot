import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { ApiError, deleteCard, getCards, importCardsBatch, setCardLearning } from "../api/client";
import type {
  AnkiSyncStatus,
  Card,
  CardBatchImportItemStatus,
  CardBatchImportResponse,
  CardBatchImportSummary,
  CardListResponse,
  EntryType,
  SourceLanguage,
} from "../api/types";
import { EmptyState, ErrorState, LoadingState } from "../components/PageState";

const PAGE_SIZE = 20;
// Each item is a sequential LLM call; keep requests well under the proxy timeout.
const BATCH_CHUNK_SIZE = 5;

type LearningFilter = "all" | "true" | "false";

interface BatchProgress {
  processed: number;
  total: number;
}

interface BatchRunResult {
  response: CardBatchImportResponse;
  fatalErrorMessage: string | null;
}

function toPositiveInt(value: string | null, fallback: number): number {
  if (!value) {
    return fallback;
  }

  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 1) {
    return fallback;
  }

  return parsed;
}

const ENTRY_TYPES: Record<EntryType, string> = {
  word: "word",
  phrasal_verb: "phrasal verb",
  collocation: "collocation",
  idiom: "idiom",
  expression: "expression",
};

const ANKI_STATUSES: Record<AnkiSyncStatus, string> = {
  pending: "waiting for sync",
  synced: "in Anki",
  failed: "sync failed",
};

const BATCH_STATUSES: Record<CardBatchImportItemStatus, string> = {
  created: "added",
  duplicate_source: "already saved (same input)",
  duplicate_canonical: "already saved (same form)",
  rejected: "rejected",
  invalid_input: "invalid input",
  upstream_error: "LLM error",
};

function parseBatchInput(rawValue: string): string[] {
  return rawValue
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

function toChunks<T>(items: T[], chunkSize: number): T[][] {
  const chunks: T[][] = [];

  for (let i = 0; i < items.length; i += chunkSize) {
    chunks.push(items.slice(i, i + chunkSize));
  }

  return chunks;
}

function createEmptyBatchSummary(): CardBatchImportSummary {
  return {
    total: 0,
    created: 0,
    duplicate_source: 0,
    duplicate_canonical: 0,
    rejected: 0,
    invalid_input: 0,
    upstream_error: 0,
  };
}

function createEmptyBatchResponse(): CardBatchImportResponse {
  return {
    items: [],
    summary: createEmptyBatchSummary(),
  };
}

function mergeBatchResponses(
  base: CardBatchImportResponse,
  incoming: CardBatchImportResponse,
): CardBatchImportResponse {
  return {
    items: [...base.items, ...incoming.items],
    summary: {
      total: base.summary.total + incoming.summary.total,
      created: base.summary.created + incoming.summary.created,
      duplicate_source: base.summary.duplicate_source + incoming.summary.duplicate_source,
      duplicate_canonical: base.summary.duplicate_canonical + incoming.summary.duplicate_canonical,
      rejected: base.summary.rejected + incoming.summary.rejected,
      invalid_input: base.summary.invalid_input + incoming.summary.invalid_input,
      upstream_error: base.summary.upstream_error + incoming.summary.upstream_error,
    },
  };
}

function formatCardTimestamp(value: string): string {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function hasActiveFilters(
  search: string,
  sourceLanguage: SourceLanguage | "",
  entryType: EntryType | "",
  ankiStatus: AnkiSyncStatus | "",
  learning: LearningFilter,
): boolean {
  return (
    search.length > 0 ||
    sourceLanguage.length > 0 ||
    entryType.length > 0 ||
    ankiStatus.length > 0 ||
    learning !== "all"
  );
}

// Filters live in the query string; replaceState keeps Telegram's back button out of it,
// and the hash (Telegram launch data) is kept.
function useSearchParams(): [URLSearchParams, (next: URLSearchParams) => void] {
  const [params, setParams] = useState(() => new URLSearchParams(window.location.search));
  const update = (next: URLSearchParams): void => {
    const query = next.toString();
    window.history.replaceState(
      null,
      "",
      `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`,
    );
    setParams(next);
  };
  return [params, update];
}

export function CardsPage(): JSX.Element {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();

  const page = toPositiveInt(searchParams.get("page"), 1);
  const search = searchParams.get("search") ?? "";
  const sourceLanguage = (searchParams.get("source_language") ?? "") as SourceLanguage | "";
  const entryType = (searchParams.get("entry_type") ?? "") as EntryType | "";
  const ankiStatus = (searchParams.get("anki_sync_status") ?? "") as AnkiSyncStatus | "";
  const learning = (searchParams.get("is_learning") ?? "all") as LearningFilter;
  const [searchDraft, setSearchDraft] = useState(search);
  const [batchInput, setBatchInput] = useState("");
  const [batchValidationError, setBatchValidationError] = useState<string | null>(null);
  const [batchFatalError, setBatchFatalError] = useState<string | null>(null);
  const [batchProgress, setBatchProgress] = useState<BatchProgress | null>(null);
  const [batchResponse, setBatchResponse] = useState<CardBatchImportResponse | null>(null);
  const [pendingDeleteCard, setPendingDeleteCard] = useState<Card | null>(null);
  const [filtersExpanded, setFiltersExpanded] = useState(
    hasActiveFilters(search, sourceLanguage, entryType, ankiStatus, learning),
  );

  useEffect(() => {
    setSearchDraft(search);
  }, [search]);

  const cardsQuery = useQuery({
    queryKey: ["cards", { page, search, sourceLanguage, entryType, ankiStatus, learning }],
    queryFn: () =>
      getCards({
        offset: (page - 1) * PAGE_SIZE,
        limit: PAGE_SIZE,
        search: search || undefined,
        source_language: sourceLanguage || undefined,
        entry_type: entryType || undefined,
        anki_sync_status: ankiStatus || undefined,
        is_learning: learning === "all" ? undefined : learning === "true",
      }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteCard,
    onSuccess: () => {
      setPendingDeleteCard(null);
      void queryClient.invalidateQueries({ queryKey: ["cards"] });
    },
  });

  // Patch the cached page in place: the card stays visible even if it no longer matches the filter.
  const learningMutation = useMutation({
    mutationFn: ({ id, isLearning }: { id: number; isLearning: boolean }) =>
      setCardLearning(id, isLearning),
    onSuccess: (updated) =>
      queryClient.setQueriesData<CardListResponse>({ queryKey: ["cards"] }, (list) =>
        list && { ...list, items: list.items.map((c) => (c.id === updated.id ? updated : c)) },
      ),
  });

  const batchImportMutation = useMutation({
    mutationFn: async (sourceTexts: string[]): Promise<BatchRunResult> => {
      const chunks = toChunks(sourceTexts, BATCH_CHUNK_SIZE);
      let aggregateResponse = createEmptyBatchResponse();
      let processed = 0;

      for (const chunk of chunks) {
        try {
          const chunkResponse = await importCardsBatch(chunk);
          aggregateResponse = mergeBatchResponses(aggregateResponse, chunkResponse);
          processed += chunk.length;
          setBatchProgress({ processed, total: sourceTexts.length });
        } catch (error) {
          const message =
            error instanceof ApiError ? error.message : "request failed";
          return { response: aggregateResponse, fatalErrorMessage: message };
        }
      }

      return { response: aggregateResponse, fatalErrorMessage: null };
    },
    onMutate: (sourceTexts) => {
      setBatchValidationError(null);
      setBatchFatalError(null);
      setBatchResponse(null);
      setBatchProgress({ processed: 0, total: sourceTexts.length });
    },
    onSuccess: (result) => {
      setBatchResponse(result.response);
      setBatchFatalError(result.fatalErrorMessage);
      void queryClient.invalidateQueries({ queryKey: ["cards"] });
    },
  });

  const startBatchImport = (): void => {
    const sourceTexts = parseBatchInput(batchInput);
    if (sourceTexts.length === 0) {
      setBatchValidationError("Paste at least one word or expression.");
      setBatchFatalError(null);
      setBatchResponse(null);
      setBatchProgress(null);
      return;
    }

    batchImportMutation.mutate(sourceTexts);
  };

  const updateParams = (updates: Record<string, string | null>, resetPage = true): void => {
    const next = new URLSearchParams(searchParams);

    for (const [key, value] of Object.entries(updates)) {
      if (value === null || value.trim() === "") {
        next.delete(key);
      } else {
        next.set(key, value);
      }
    }

    if (resetPage) {
      next.delete("page");
    }

    setSearchParams(next);
  };

  const total = cardsQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const filtersOpen = hasActiveFilters(search, sourceLanguage, entryType, ankiStatus, learning);

  return (
    <section className="cards-page">
      <header className="page-title-block">
        <h2>Words</h2>
        <p>Saved cards: import, search, filter, and delete.</p>
      </header>

      <section className="surface-panel batch-panel">
        <div className="section-heading">
          <div>
            <p className="section-label">Batch import</p>
            <h3>One word or expression per line</h3>
          </div>
          <span className="info-chip">{BATCH_CHUNK_SIZE} per request</span>
        </div>

        <label htmlFor="batch-import-input">List</label>
        <textarea
          id="batch-import-input"
          name="batch-import-input"
          rows={7}
          value={batchInput}
          placeholder={"take off\nlook up\nbreak down"}
          onChange={(event) => setBatchInput(event.target.value)}
        />

        <div className="batch-actions-row">
          <button
            type="button"
            className="primary-button"
            disabled={batchImportMutation.isPending}
            onClick={startBatchImport}
          >
            {batchImportMutation.isPending ? "Importing…" : "Import"}
          </button>
        </div>

        {batchValidationError ? (
          <p className="batch-message batch-message-error">{batchValidationError}</p>
        ) : null}

        {batchProgress ? (
          <p className="batch-message">
            Processed {batchProgress.processed}/{batchProgress.total}
          </p>
        ) : null}

        {batchFatalError ? (
          <p className="batch-message batch-message-error">Import stopped: {batchFatalError}</p>
        ) : null}

        {batchResponse ? (
          <div className="batch-results">
            <div className="batch-summary-grid">
              <p>Total processed: {batchResponse.summary.total}</p>
              <p>Added: {batchResponse.summary.created}</p>
              <p>Already saved (same input): {batchResponse.summary.duplicate_source}</p>
              <p>Already saved (same form): {batchResponse.summary.duplicate_canonical}</p>
              <p>Rejected: {batchResponse.summary.rejected}</p>
              <p>Invalid input: {batchResponse.summary.invalid_input}</p>
              <p>LLM errors: {batchResponse.summary.upstream_error}</p>
            </div>

            {batchResponse.items.length > 0 ? (
              <div className="batch-results-grid">
                {batchResponse.items.map((item, index) => (
                  <article className="batch-result-card" key={`${item.source_text}-${index}`}>
                    <div className="batch-result-topline">
                      <strong>{item.source_text}</strong>
                      <span className="info-chip">{BATCH_STATUSES[item.status]}</span>
                    </div>
                    <p>Form: {item.canonical_text ?? "—"}</p>
                    <p>Message: {item.message ?? "—"}</p>
                  </article>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
      </section>

      <details
        className="surface-panel filters-panel"
        open={filtersExpanded}
        onToggle={(event) => setFiltersExpanded(event.currentTarget.open)}
      >
        <summary>
          <div className="section-heading">
            <div>
              <p className="section-label">Search and filters</p>
              <h3>Narrow the list</h3>
            </div>
            <span className="info-chip">{filtersOpen ? "Filters on" : "All cards"}</span>
          </div>
        </summary>

        <div className="filters-panel-body">
          <div className="search-row">
            <label htmlFor="cards-search">Search</label>
            <input
              id="cards-search"
              name="search"
              type="search"
              value={searchDraft}
              placeholder="Word or source text"
              onChange={(event) => setSearchDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  updateParams({ search: searchDraft.trim() || null });
                }
              }}
            />
            <button
              type="button"
              className="secondary-button"
              onClick={() => updateParams({ search: searchDraft.trim() || null })}
            >
              Find
            </button>
          </div>

          <div className="filter-grid">
            <label>
              Input language
              <select
                value={sourceLanguage}
                onChange={(event) => updateParams({ source_language: event.target.value || null })}
              >
                <option value="">All</option>
                <option value="en">EN</option>
                <option value="ru">RU</option>
              </select>
            </label>

            <label>
              Type
              <select
                value={entryType}
                onChange={(event) => updateParams({ entry_type: event.target.value || null })}
              >
                <option value="">All</option>
                {Object.entries(ENTRY_TYPES).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Anki status
              <select
                value={ankiStatus}
                onChange={(event) => updateParams({ anki_sync_status: event.target.value || null })}
              >
                <option value="">All</option>
                {Object.entries(ANKI_STATUSES).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Learning
              <select
                value={learning}
                onChange={(event) =>
                  updateParams({
                    is_learning: event.target.value === "all" ? null : event.target.value,
                  })
                }
              >
                <option value="all">All</option>
                <option value="true">yes</option>
                <option value="false">no</option>
              </select>
            </label>
          </div>
        </div>
      </details>

      {cardsQuery.isLoading ? (
        <LoadingState message="Loading cards…" />
      ) : cardsQuery.isError ? (
        <ErrorState error={cardsQuery.error} onRetry={() => void cardsQuery.refetch()} />
      ) : cardsQuery.data && cardsQuery.data.items.length === 0 ? (
        <EmptyState title="Nothing found" message="Change the search or clear the filters." />
      ) : (
        <>
          {deleteMutation.isError ? (
            <ErrorState title="Couldn't delete" error={deleteMutation.error} />
          ) : null}
          {learningMutation.isError ? (
            <ErrorState title="Couldn't save “Learning”" error={learningMutation.error} />
          ) : null}

          <div className="list-header">
            <div>
              <p className="section-label">Cards</p>
              <h3>
                {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} of {total}
              </h3>
            </div>
            <span className="info-chip">
              Page {page} / {totalPages}
            </span>
          </div>

          <div className="card-list">
            {cardsQuery.data?.items.map((card) => (
              <article className="card-item" key={card.id}>
                <div className="card-item-topline">
                  <div className="card-heading">
                    <p className="section-label">Card</p>
                    <h3>{card.canonical_text}</h3>
                  </div>
                  <span className={`status-pill status-${card.anki_sync_status}`}>
                    {ANKI_STATUSES[card.anki_sync_status]}
                  </span>
                </div>

                {card.anki_sync_error ? <p className="batch-message-error">{card.anki_sync_error}</p> : null}

                <div className="card-meta-grid">
                  <p>
                    <span>Input</span>
                    <strong>{card.source_text}</strong>
                  </p>
                  <p>
                    <span>Type</span>
                    <strong>{ENTRY_TYPES[card.entry_type]}</strong>
                  </p>
                  <p>
                    <span>Language</span>
                    <strong>{card.source_language.toUpperCase()}</strong>
                  </p>
                  <p>
                    <span>Frequency</span>
                    <strong>{card.frequency}</strong>
                  </p>
                  <label className="learning-toggle">
                    <input
                      type="checkbox"
                      role="switch"
                      aria-label={`Learning: ${card.canonical_text}`}
                      checked={card.is_learning}
                      disabled={learningMutation.isPending}
                      onChange={(event) =>
                        learningMutation.mutate({ id: card.id, isLearning: event.target.checked })
                      }
                    />
                    Learning
                  </label>
                  <p>
                    <span>Added</span>
                    <strong>{formatCardTimestamp(card.created_at)}</strong>
                  </p>
                </div>

                <div className="card-content-grid">
                  <section className="card-content-panel">
                    <h4>Translations</h4>
                    <ul className="translation-list">
                      {card.translation_variants.map((translation) => (
                        <li key={translation}>{translation}</li>
                      ))}
                    </ul>
                  </section>

                  <section className="card-content-panel">
                    <h4>Word family</h4>
                    {card.word_family.length > 0 ? (
                      <ul className="word-family-list">
                        {card.word_family.map((item) => (
                          <li key={item.word}>
                            <strong>{item.word}</strong> ({item.part_of_speech}) — {item.translation}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p>—</p>
                    )}
                  </section>

                  <section className="card-content-panel">
                    <h4>Explanation</h4>
                    <p>{card.explanation}</p>
                  </section>

                  <section className="card-content-panel">
                    <h4>Examples</h4>
                    <ul className="example-list">
                      {card.examples.map((example) => (
                        <li key={example}>{example}</li>
                      ))}
                    </ul>
                  </section>
                </div>

                <div className="card-actions">
                  <button
                    type="button"
                    className="danger-button"
                    disabled={deleteMutation.isPending}
                    onClick={() => {
                      deleteMutation.reset();
                      setPendingDeleteCard(card);
                    }}
                  >
                    Delete
                  </button>
                </div>
              </article>
            ))}
          </div>

          <footer className="pagination-bar">
            <button
              type="button"
              className="secondary-button"
              disabled={page <= 1}
              onClick={() => updateParams({ page: String(page - 1) }, false)}
            >
              Previous
            </button>
            <button
              type="button"
              className="secondary-button"
              disabled={page >= totalPages}
              onClick={() => updateParams({ page: String(page + 1) }, false)}
            >
              Next
            </button>
          </footer>
        </>
      )}

      {pendingDeleteCard ? (
        <div className="modal-backdrop" role="presentation">
          <section className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="delete-card-title">
            <p className="section-label">Delete</p>
            <h3 id="delete-card-title">Delete “{pendingDeleteCard.canonical_text}”?</h3>
            <p>The card will be removed from your dictionary.</p>

            <div className="confirm-dialog-actions">
              <button
                type="button"
                className="secondary-button"
                disabled={deleteMutation.isPending}
                onClick={() => {
                  deleteMutation.reset();
                  setPendingDeleteCard(null);
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                className="danger-button"
                disabled={deleteMutation.isPending}
                onClick={() => deleteMutation.mutate(pendingDeleteCard.id)}
              >
                {deleteMutation.isPending ? "Deleting…" : "Delete card"}
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}
