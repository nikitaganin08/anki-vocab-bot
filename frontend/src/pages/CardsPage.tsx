import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { getCards } from "../api/client";
import type { AnkiSyncStatus, EntryType, SourceLanguage } from "../api/types";
import { EmptyState, ErrorState, LoadingState } from "../components/PageState";

const PAGE_SIZE = 20;

type EligibleFilter = "all" | "true" | "false";

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

export function CardsPage(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();

  const page = toPositiveInt(searchParams.get("page"), 1);
  const search = searchParams.get("search") ?? "";
  const sourceLanguage = (searchParams.get("source_language") ?? "") as SourceLanguage | "";
  const entryType = (searchParams.get("entry_type") ?? "") as EntryType | "";
  const ankiStatus = (searchParams.get("anki_sync_status") ?? "") as AnkiSyncStatus | "";
  const eligible = (searchParams.get("eligible_for_anki") ?? "all") as EligibleFilter;
  const [searchDraft, setSearchDraft] = useState(search);

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
        <p>Search and inspect generated lexical units.</p>
      </header>

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
                </tr>
              </thead>
              <tbody>
                {cardsQuery.data?.items.map((card) => (
                  <tr key={card.id}>
                    <td>
                      <Link to={`/cards/${card.id}`} className="table-link">
                        {card.canonical_text}
                      </Link>
                    </td>
                    <td>{card.source_text}</td>
                    <td>{prettifyEntryType(card.entry_type)}</td>
                    <td>{card.source_language.toUpperCase()}</td>
                    <td>{card.frequency}</td>
                    <td>
                      <span className={`status-pill status-${card.anki_sync_status}`}>
                        {card.anki_sync_status}
                      </span>
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
