import {
  keepPreviousData,
  useInfiniteQuery,
  useQueryClient,
  type InfiniteData,
} from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { getCards } from "../api/client";
import type { Card, CardListResponse } from "../api/types";
import { ENTRY_TYPES } from "../entryTypes";
import { EmptyState, ErrorState, LoadingState } from "../components/PageState";
import { AddWordsSheet } from "./AddWordsSheet";
import { CardSheet } from "./CardSheet";
import { EntryTypesSheet } from "./EntryTypesSheet";

const PAGE_SIZE = 50;
const SEARCH_DEBOUNCE_MS = 300;
const DAY_MS = 24 * 60 * 60 * 1000;

const FILTERS = [
  { value: "all", label: "All", isLearning: undefined },
  { value: "learning", label: "Learning", isLearning: true },
  { value: "not_learning", label: "Not learning", isLearning: false },
] as const;

export interface RowStatus {
  kind: "new" | "learning" | "review" | "off";
  label: string;
}

// The right-hand label: "off", "new" (learning, never reviewed), "today" (due by the end of the
// local day, overdue included) or "N d" (local calendar days until the due day).
export function rowStatus(card: Card, now: Date): RowStatus {
  if (!card.is_learning) {
    return { kind: "off", label: "off" };
  }
  if (card.srs_state === null || card.srs_due_at === null) {
    return { kind: "new", label: "new" };
  }

  const kind = card.srs_state === "review" ? "review" : "learning";
  const due = new Date(card.srs_due_at);
  // UTC on the local date parts: whole days apart, whatever DST does in between.
  const day = (date: Date): number => Date.UTC(date.getFullYear(), date.getMonth(), date.getDate());
  const days = (day(due) - day(now)) / DAY_MS;
  return { kind, label: days <= 0 ? "today" : `${days} d` };
}

// Search and filter live in the query string; replaceState keeps Telegram's back button out of
// it, and the hash (Telegram launch data) is kept. Updates start from the live URL, so a
// debounced one cannot overwrite a newer change.
function useQueryState(): [URLSearchParams, (updates: Record<string, string | null>) => void] {
  const [params, setParams] = useState(() => new URLSearchParams(window.location.search));
  const update = (updates: Record<string, string | null>): void => {
    const next = new URLSearchParams(window.location.search);
    for (const [key, value] of Object.entries(updates)) {
      if (value) {
        next.set(key, value);
      } else {
        next.delete(key);
      }
    }
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

function WordRow({ card, now, onOpen }: { card: Card; now: Date; onOpen: () => void }): JSX.Element {
  const { kind, label } = rowStatus(card, now);
  return (
    <button type="button" className="word-row" onClick={onOpen}>
      <span className={`status-dot status-dot-${kind}`} aria-hidden="true" />
      <span className="word-row-text">
        <strong>{card.canonical_text}</strong>
        <span className="word-row-translation">{card.translation_variants[0]}</span>
      </span>
      <span className="word-row-label">{label}</span>
    </button>
  );
}

export function CardsPage(): JSX.Element {
  const queryClient = useQueryClient();
  const [params, updateParams] = useQueryState();
  const search = params.get("q") ?? "";
  const filter = FILTERS.find((f) => f.value === params.get("filter")) ?? FILTERS[0];

  const entryType = ENTRY_TYPES.find((t) => t.value === params.get("type"));
  const [showTypes, setShowTypes] = useState(false);

  const [searchDraft, setSearchDraft] = useState(search);
  const [adding, setAdding] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  useEffect(() => {
    const next = searchDraft.trim();
    if (next === search) {
      return;
    }
    const timer = setTimeout(() => updateParams({ q: next }), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [searchDraft, search]);

  const cardsQuery = useInfiniteQuery({
    queryKey: ["cards", { search, filter: filter.value, type: entryType?.value }],
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      getCards({
        offset: pageParam,
        limit: PAGE_SIZE,
        search: search || undefined,
        is_learning: filter.isLearning,
        entry_type: entryType?.value,
      }),
    getNextPageParam: (last, pages) => {
      const loaded = pages.reduce((count, page) => count + page.items.length, 0);
      return last.items.length > 0 && loaded < last.total ? loaded : undefined;
    },
    placeholderData: keepPreviousData,
  });

  // A card added while paging can show up on two pages; keep the first.
  const seen = new Set<number>();
  const items = (cardsQuery.data?.pages.flatMap((page) => page.items) ?? []).filter((card) => {
    if (seen.has(card.id)) {
      return false;
    }
    seen.add(card.id);
    return true;
  });
  const selected = items.find((card) => card.id === selectedId) ?? null;
  const now = new Date();

  // Patch the cached pages in place: the card stays in the list even if it no longer matches the filter.
  const patchCard = (updated: Card): void => {
    queryClient.setQueriesData<InfiniteData<CardListResponse, number>>(
      { queryKey: ["cards"] },
      (data) =>
        data && {
          ...data,
          pages: data.pages.map((page) => ({
            ...page,
            items: page.items.map((card) => (card.id === updated.id ? updated : card)),
          })),
        },
    );
  };

  let list: JSX.Element;
  if (cardsQuery.isPending) {
    list = <LoadingState message="Loading words…" />;
  } else if (!cardsQuery.data) {
    list = <ErrorState error={cardsQuery.error} onRetry={() => void cardsQuery.refetch()} />;
  } else if (items.length === 0) {
    list =
      search || filter.value !== "all" || entryType ? (
        <EmptyState title="Nothing found" message="Change the search or the filter." />
      ) : (
        <EmptyState title="No words yet" message="Tap + to add some." />
      );
  } else {
    list = (
      <>
        <ul className="word-list">
          {items.map((card) => (
            <li key={card.id}>
              <WordRow card={card} now={now} onOpen={() => setSelectedId(card.id)} />
            </li>
          ))}
        </ul>
        {cardsQuery.isFetchNextPageError ? (
          <ErrorState title="Couldn't load more" error={cardsQuery.error} />
        ) : null}
        {cardsQuery.hasNextPage ? (
          <button
            type="button"
            className="secondary-button"
            disabled={cardsQuery.isFetchingNextPage}
            onClick={() => void cardsQuery.fetchNextPage()}
          >
            {cardsQuery.isFetchingNextPage ? "Loading…" : "Load more"}
          </button>
        ) : null}
      </>
    );
  }

  return (
    <section className="cards-page">
      <div className="words-toolbar">
        <input
          type="search"
          name="search"
          aria-label="Search words"
          placeholder="Search words"
          value={searchDraft}
          onChange={(event) => setSearchDraft(event.target.value)}
        />
        <button
          type="button"
          className="primary-button add-button"
          aria-label="Add words"
          onClick={() => setAdding(true)}
        >
          +
        </button>
      </div>

      <div className="filter-chips" role="group" aria-label="Filter">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            className="filter-chip"
            aria-pressed={f.value === filter.value}
            onClick={() => updateParams({ filter: f.value === "all" ? null : f.value })}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="filter-chips" role="group" aria-label="Type">
        {[{ value: null, label: "All types" }, ...ENTRY_TYPES].map((t) => (
          <button
            key={t.value ?? "all"}
            type="button"
            className="filter-chip"
            aria-pressed={(t.value ?? undefined) === entryType?.value}
            onClick={() => updateParams({ type: t.value })}
          >
            {t.label}
          </button>
        ))}
        <button type="button" className="link-button" onClick={() => setShowTypes(true)}>
          What are these types?
        </button>
      </div>

      {list}

      {showTypes ? <EntryTypesSheet onClose={() => setShowTypes(false)} /> : null}

      {adding ? <AddWordsSheet onClose={() => setAdding(false)} /> : null}
      {selected ? (
        <CardSheet
          card={selected}
          onClose={() => setSelectedId(null)}
          onLearningSaved={patchCard}
          onDeleted={() => {
            setSelectedId(null);
            void queryClient.invalidateQueries({ queryKey: ["cards"] });
          }}
        />
      ) : null}
    </section>
  );
}
