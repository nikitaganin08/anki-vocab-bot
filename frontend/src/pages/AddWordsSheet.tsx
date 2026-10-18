import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, importCardsBatch } from "../api/client";
import type {
  CardBatchImportItemStatus,
  CardBatchImportResponse,
  CardBatchImportSummary,
} from "../api/types";
import { Sheet } from "../components/Sheet";

// Each item is a sequential LLM call; keep requests well under the proxy timeout.
const BATCH_CHUNK_SIZE = 5;

interface BatchProgress {
  processed: number;
  total: number;
}

interface BatchRunResult {
  response: CardBatchImportResponse;
  fatalErrorMessage: string | null;
}

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

export function AddWordsSheet({ onClose }: { onClose: () => void }): JSX.Element {
  const queryClient = useQueryClient();
  const [batchInput, setBatchInput] = useState("");
  const [batchValidationError, setBatchValidationError] = useState<string | null>(null);
  const [batchFatalError, setBatchFatalError] = useState<string | null>(null);
  const [batchProgress, setBatchProgress] = useState<BatchProgress | null>(null);
  const [batchResponse, setBatchResponse] = useState<CardBatchImportResponse | null>(null);

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
          const message = error instanceof ApiError ? error.message : "request failed";
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

  return (
    <Sheet label="Add words" onClose={onClose}>
      <div>
        <h3>Add words</h3>
        <p className="section-label">One word or expression per line, {BATCH_CHUNK_SIZE} per request</p>
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

      <div className="sheet-actions">
        <button type="button" className="secondary-button" onClick={onClose}>
          Close
        </button>
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

    </Sheet>
  );
}
