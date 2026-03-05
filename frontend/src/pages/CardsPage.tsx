import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { ApiError, deleteCard, getCards, importCardsBatch } from "../api/client";
import type {
  AnkiSyncStatus,
  CardBatchImportItemStatus,
  CardBatchImportResponse,
  CardBatchImportSummary,
  EntryType,
  SourceLanguage,
} from "../api/types";
import { EmptyState, ErrorState, LoadingState } from "../components/PageState";

const PAGE_SIZE = 20;
const BATCH_CHUNK_SIZE = 50;

type EligibleFilter = "all" | "true" | "false";
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

function prettifyEntryType(entryType: EntryType): string {
  return entryType.replaceAll("_", " ");
}

function prettifyBatchStatus(status: CardBatchImportItemStatus): string {
  return status.replaceAll("_", " ");
}

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

export function CardsPage(): JSX.Element {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();

  const page = toPositiveInt(searchParams.get("page"), 1);
  const search = searchParams.get("search") ?? "";
  const sourceLanguage = (searchParams.get("source_language") ?? "") as SourceLanguage | "";
  const entryType = (searchParams.get("entry_type") ?? "") as EntryType | "";
  const ankiStatus = (searchParams.get("anki_sync_status") ?? "") as AnkiSyncStatus | "";
  const eligible = (searchParams.get("eligible_for_anki") ?? "all") as EligibleFilter;
  const [searchDraft, setSearchDraft] = useState(search);
  const [batchInput, setBatchInput] = useState("");
  const [batchValidationError, setBatchValidationError] = useState<string | null>(null);
  const [batchFatalError, setBatchFatalError] = useState<string | null>(null);
  const [batchProgress, setBatchProgress] = useState<BatchProgress | null>(null);
  const [batchResponse, setBatchResponse] = useState<CardBatchImportResponse | null>(null);

  useEffect(() => {
    setSearchDraft(search);
  }, [search]);

  const cardsQuery = useQuery({
    queryKey: ["cards", { page, search, sourceLanguage, entryType, ankiStatus, eligible }],
    queryFn: () =>
      getCards({
        offset: (page - 1) * PAGE_SIZE,
        limit: PAGE_SIZE,
        search: search || undefined,
        source_language: sourceLanguage || undefined,
        entry_type: entryType || undefined,
        anki_sync_status: ankiStatus || undefined,
        eligible_for_anki:
          eligible === "all" ? undefined : eligible === "true",
      }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteCard,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["cards"] });
    },
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
            error instanceof ApiError ? error.message : "Batch import failed due to request error.";
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
    onError: (error) => {
      const message =
        error instanceof ApiError ? error.message : "Batch import failed due to unexpected error.";
      setBatchFatalError(message);
    },
  });

  const startBatchImport = (): void => {
    const sourceTexts = parseBatchInput(batchInput);
    if (sourceTexts.length === 0) {
      setBatchValidationError("Please paste at least one lexical unit.");
      setBatchFatalError(null);
      setBatchResponse(null);
      setBatchProgress(null);
      return;
    }

    setBatchValidationError(null);
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

    setSearchParams(next, { replace: true });
  };

  const total = cardsQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <section className="cards-page">
      <header className="page-title-block">
        <h2>Cards</h2>
        <p>Search and delete generated lexical units.</p>
      </header>

      <section className="batch-panel">
        <div className="batch-panel-header">
          <h3>Batch Import</h3>
          <p>Paste one English lexical unit per line. Large lists are processed in chunks of 50.</p>
        </div>

        <label htmlFor="batch-import-input">Input list</label>
        <textarea
          id="batch-import-input"
          name="batch-import-input"
          rows={8}
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
            {batchImportMutation.isPending ? "Importing..." : "Import"}
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
          <p className="batch-message batch-message-error">
            Import stopped: {batchFatalError}
          </p>
        ) : null}

        {batchResponse ? (
          <div className="batch-results">
            <div className="batch-summary-grid">
              <p>Total processed: {batchResponse.summary.total}</p>
              <p>Created: {batchResponse.summary.created}</p>
              <p>Duplicate source: {batchResponse.summary.duplicate_source}</p>
              <p>Duplicate canonical: {batchResponse.summary.duplicate_canonical}</p>
              <p>Rejected: {batchResponse.summary.rejected}</p>
              <p>Invalid input: {batchResponse.summary.invalid_input}</p>
              <p>Upstream errors: {batchResponse.summary.upstream_error}</p>
            </div>

            {batchResponse.items.length > 0 ? (
              <div className="batch-table-wrap">
                <table className="batch-table">
                  <thead>
                    <tr>
                      <th>Input</th>
                      <th>Status</th>
                      <th>Canonical</th>
                      <th>Message</th>
                    </tr>
                  </thead>
                  <tbody>
                    {batchResponse.items.map((item, index) => (
                      <tr key={`${item.source_text}-${index}`}>
                        <td>{item.source_text}</td>
                        <td>{prettifyBatchStatus(item.status)}</td>
                        <td>{item.canonical_text ?? "-"}</td>
                        <td>{item.message ?? "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        ) : null}
      </section>

      <div className="filters-panel">
        <div className="search-row">
          <label htmlFor="cards-search">Search</label>
          <input
            id="cards-search"
            name="search"
            type="search"
            value={searchDraft}
            placeholder="Canonical text or source text"
            onChange={(event) => setSearchDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                updateParams({ search: searchDraft.trim() || null });
              }
            }}
          />
          <button
            type="button"
            className="primary-button"
            onClick={() => updateParams({ search: searchDraft.trim() || null })}
          >
            Apply
          </button>
        </div>

        <div className="filter-grid">
          <label>
            Source language
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
            Entry type
            <select
              value={entryType}
              onChange={(event) => updateParams({ entry_type: event.target.value || null })}
            >
              <option value="">All</option>
              <option value="word">word</option>
              <option value="phrasal_verb">phrasal_verb</option>
              <option value="collocation">collocation</option>
              <option value="idiom">idiom</option>
              <option value="expression">expression</option>
            </select>
          </label>

          <label>
            Anki status
            <select
              value={ankiStatus}
              onChange={(event) => updateParams({ anki_sync_status: event.target.value || null })}
            >
              <option value="">All</option>
              <option value="pending">pending</option>
              <option value="synced">synced</option>
              <option value="failed">failed</option>
            </select>
          </label>

          <label>
            Eligible for Anki
            <select
              value={eligible}
              onChange={(event) =>
                updateParams({
                  eligible_for_anki: event.target.value === "all" ? null : event.target.value,
                })
              }
            >
              <option value="all">All</option>
              <option value="true">true</option>
              <option value="false">false</option>
            </select>
          </label>
        </div>
      </div>

      {cardsQuery.isLoading ? (
        <LoadingState title="Loading cards" message="Fetching card list from the API." />
      ) : cardsQuery.isError ? (
        <ErrorState error={cardsQuery.error} onRetry={() => void cardsQuery.refetch()} />
      ) : cardsQuery.data && cardsQuery.data.items.length === 0 ? (
        <EmptyState title="No cards found" message="Try a different search term or remove filters." />
      ) : (
        <>
          {deleteMutation.isError ? (
            <ErrorState
              title="Delete failed"
              error={
                deleteMutation.error instanceof ApiError
                  ? new Error(deleteMutation.error.message)
                  : (deleteMutation.error as Error)
              }
            />
          ) : null}

          <div className="table-meta">
            <p>
              Showing {(page - 1) * PAGE_SIZE + 1}-{Math.min(page * PAGE_SIZE, total)} of {total}
            </p>
          </div>

          <div className="table-wrap">
            <table className="cards-table">
              <thead>
                <tr>
                  <th>Canonical</th>
                  <th>Source</th>
                  <th>Type</th>
                  <th>Lang</th>
                  <th>Frequency</th>
                  <th>Anki</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {cardsQuery.data?.items.map((card) => (
                  <tr key={card.id}>
                    <td>{card.canonical_text}</td>
                    <td>{card.source_text}</td>
                    <td>{prettifyEntryType(card.entry_type)}</td>
                    <td>{card.source_language.toUpperCase()}</td>
                    <td>{card.frequency}</td>
                    <td>
                      <span className={`status-pill status-${card.anki_sync_status}`}>
                        {card.anki_sync_status}
                      </span>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="danger-button"
                        disabled={deleteMutation.isPending}
                        onClick={() => {
                          if (!window.confirm(`Delete card "${card.canonical_text}"?`)) {
                            return;
                          }
                          deleteMutation.mutate(card.id);
                        }}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
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
            <p>
              Page {page} / {totalPages}
            </p>
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
    </section>
  );
}
